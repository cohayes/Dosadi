from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Dict, List, Mapping

from dosadi.agent.suits import SuitState
from dosadi.runtime.local_interactions import hashed_unit_float
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.world.events import EventKind, WorldEvent, WorldEventLog
from dosadi.world.facilities import Facility, FacilityKind, FacilityLedger, ensure_facility_ledger
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, LogisticsLedger, ensure_logistics
from dosadi.world.materials import (
    InventoryRegistry,
    Material,
    ensure_inventory_registry,
    material_from_key,
)
from dosadi.world.workforce import Assignment, AssignmentKind, WorkforceLedger, ensure_workforce


@dataclass(slots=True)
class SuitWearConfig:
    enabled: bool = False
    wear_per_day_base: float = 0.0025
    wear_per_day_courier_mult: float = 1.4
    wear_per_day_worker_mult: float = 1.2
    threshold_warn: float = 0.60
    threshold_repair: float = 0.40
    threshold_critical: float = 0.25
    max_repairs_per_day: int = 8
    repair_duration_days: int = 1
    repair_facility_kind: str = "WORKSHOP"
    deterministic_salt: str = "suit-wear-v1"
    apply_physio_penalties: bool = True
    warn_event_enabled: bool = True


@dataclass(slots=True)
class SuitWearState:
    last_run_day: int = -1
    repairs_started_today: int = 0


@dataclass(slots=True)
class SuitRepairJob:
    job_id: str
    agent_id: str
    facility_id: str | None
    created_day: int
    due_day: int
    status: str
    bom: Dict[Material, int]
    pending_delivery_ids: list[str] = field(default_factory=list)
    assigned_agent_ids: list[str] = field(default_factory=list)
    progress_days: int = 0
    notes: Dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SuitRepairLedger:
    jobs: Dict[str, SuitRepairJob] = field(default_factory=dict)
    open_jobs_by_agent: Dict[str, str] = field(default_factory=dict)

    def signature(self) -> str:
        def _material_name(material: object) -> str:
            if isinstance(material, Material):
                return material.name
            return str(material)

        canonical = {
            job_id: {
                "agent": job.agent_id,
                "facility": job.facility_id,
                "created": job.created_day,
                "due": job.due_day,
                "status": job.status,
                "bom": {
                    _material_name(material): qty
                    for material, qty in sorted(_normalize_bom(job.bom).items(), key=lambda i: _material_name(i[0]))
                },
                "pending": sorted(job.pending_delivery_ids),
                "assigned": sorted(job.assigned_agent_ids),
                "progress": job.progress_days,
            }
            for job_id, job in sorted(self.jobs.items())
        }
        return sha256(str(canonical).encode("utf-8")).hexdigest()


def ensure_suit_config(world: Any) -> SuitWearConfig:
    cfg = getattr(world, "suit_cfg", None)
    if not isinstance(cfg, SuitWearConfig):
        cfg = SuitWearConfig()
        setattr(world, "suit_cfg", cfg)
    return cfg


def ensure_suit_state(world: Any) -> SuitWearState:
    state = getattr(world, "suit_state", None)
    if not isinstance(state, SuitWearState):
        state = SuitWearState()
        setattr(world, "suit_state", state)
    return state


def ensure_suit_ledger(world: Any) -> SuitRepairLedger:
    ledger = getattr(world, "suit_repairs", None)
    if not isinstance(ledger, SuitRepairLedger):
        ledger = SuitRepairLedger()
        setattr(world, "suit_repairs", ledger)
    for job in ledger.jobs.values():
        job.bom = _normalize_bom(job.bom)
    return ledger


def _suit_metrics(world: Any) -> Dict[str, Any]:
    telemetry = ensure_metrics(world)
    bucket = telemetry.gauges.get("suits")
    if not isinstance(bucket, dict):
        bucket = {}
        telemetry.gauges["suits"] = bucket
    return bucket


def _event_log(world: Any) -> WorldEventLog:
    log = getattr(world, "event_log", None)
    if not isinstance(log, WorldEventLog):
        log = WorldEventLog(max_len=5000)
        setattr(world, "event_log", log)
    return log


def _normalize_bom(bom: Mapping[object, object]) -> Dict[Material, int]:
    normalized: Dict[Material, int] = {}
    for material, qty in bom.items():
        mat = material if isinstance(material, Material) else material_from_key(material)
        if mat is None:
            continue
        try:
            amount = int(qty)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        normalized[mat] = normalized.get(mat, 0) + amount
    return normalized


def _emit_event(
    world: Any, *, day: int, kind: EventKind, subject_id: str, severity: float, payload: Mapping[str, object]
) -> None:
    event = WorldEvent(
        event_id="",
        day=day,
        kind=kind,
        subject_kind="agent",
        subject_id=subject_id,
        severity=severity,
        payload=dict(payload),
    )
    _event_log(world).append(event)


def _ensure_agent_suit(agent: Any) -> SuitState:
    suit = getattr(agent, "suit", None)
    if not isinstance(suit, SuitState):
        suit = SuitState()
        setattr(agent, "suit", suit)
    return suit


def suit_decay_multiplier(agent: Any, *, cfg: SuitWearConfig | None = None) -> float:
    cfg = cfg or SuitWearConfig()
    suit = _ensure_agent_suit(agent)
    if not getattr(cfg, "enabled", False) or not getattr(cfg, "apply_physio_penalties", False):
        return 1.0
    if suit.integrity < cfg.threshold_critical:
        return 1.25
    if suit.integrity < cfg.threshold_warn:
        return 1.1
    return 1.0


def _assignment_multiplier(assignment: Assignment, cfg: SuitWearConfig) -> float:
    courier_kinds = {AssignmentKind.LOGISTICS_COURIER, AssignmentKind.LOGISTICS_ESCORT}
    worker_kinds = {AssignmentKind.PROJECT_WORK, AssignmentKind.FACILITY_STAFF, AssignmentKind.MAINTENANCE}
    if assignment.kind in courier_kinds:
        return cfg.wear_per_day_courier_mult
    if assignment.kind in worker_kinds:
        return cfg.wear_per_day_worker_mult
    return 1.0


def _candidate_agents(world: Any, workforce: WorkforceLedger) -> List[str]:
    candidates = set()
    for agent_id, assignment in sorted(workforce.assignments.items()):
        if assignment.kind is AssignmentKind.IDLE:
            continue
        candidates.add(agent_id)
    if not candidates:
        candidates.update(getattr(world, "agents", {}).keys())
    return sorted(candidates)


def _apply_wear(world: Any, *, day: int, cfg: SuitWearConfig, state: SuitWearState) -> None:
    workforce = ensure_workforce(world)
    metrics = _suit_metrics(world)
    telemetry = ensure_metrics(world)
    candidates = _candidate_agents(world, workforce)
    metrics["wear_candidates"] = float(len(candidates))
    warn_count = 0
    repair_count = 0
    critical_count = 0

    for agent_id in candidates:
        agent = getattr(world, "agents", {}).get(agent_id)
        if agent is None:
            continue
        suit = _ensure_agent_suit(agent)
        assignment = workforce.get(agent_id)
        delta = cfg.wear_per_day_base * _assignment_multiplier(assignment, cfg)
        jitter = hashed_unit_float(cfg.deterministic_salt, agent_id, str(day))
        delta *= 0.9 + 0.2 * jitter
        prior = suit.integrity
        suit.integrity = max(0.0, min(1.0, suit.integrity - delta))
        if suit.integrity >= cfg.threshold_warn:
            suit.notes.pop("warn_emitted", None)
        if suit.integrity >= cfg.threshold_repair:
            suit.notes.pop("repair_emitted", None)
        if suit.integrity >= cfg.threshold_critical:
            suit.notes.pop("critical_emitted", None)

        if cfg.warn_event_enabled and prior >= cfg.threshold_warn > suit.integrity:
            suit.notes["warn_emitted"] = True
            metrics["warnings"] = metrics.get("warnings", 0.0) + 1.0
            _emit_event(
                world,
                day=day,
                kind=EventKind.SUIT_WEAR_WARN,
                subject_id=agent_id,
                severity=0.3,
                payload={"integrity": suit.integrity},
            )

        if prior >= cfg.threshold_repair > suit.integrity:
            suit.repair_needed = True
            suit.notes["repair_emitted"] = True
            metrics["repairs_needed"] = metrics.get("repairs_needed", 0.0) + 1.0
            _emit_event(
                world,
                day=day,
                kind=EventKind.SUIT_REPAIR_NEEDED,
                subject_id=agent_id,
                severity=0.5,
                payload={"integrity": suit.integrity},
            )
        elif suit.integrity >= cfg.threshold_repair and suit.repair_needed:
            suit.repair_needed = False

        if prior >= cfg.threshold_critical > suit.integrity and not suit.notes.get("critical_emitted"):
            suit.notes["critical_emitted"] = True
            _emit_event(
                world,
                day=day,
                kind=EventKind.SUIT_CRITICAL,
                subject_id=agent_id,
                severity=0.8,
                payload={"integrity": suit.integrity},
            )

        if suit.integrity < cfg.threshold_warn:
            warn_count += 1
        if suit.integrity < cfg.threshold_repair:
            repair_count += 1
        if suit.integrity < cfg.threshold_critical:
            critical_count += 1

    state.last_run_day = day
    state.repairs_started_today = 0
    total = max(1, len(getattr(world, "agents", {})) or len(candidates) or 1)
    telemetry.set_gauge("suits.percent_warn", 100.0 * warn_count / total)
    telemetry.set_gauge("suits.percent_repair", 100.0 * repair_count / total)
    telemetry.set_gauge("suits.percent_critical", 100.0 * critical_count / total)


def _bom_for_repair() -> Dict[Material, int]:
    return _normalize_bom({Material.FASTENERS: 1, Material.SEALANT: 1, Material.FABRIC: 1})


def _choose_facility(world: Any, cfg: SuitWearConfig) -> Facility | None:
    facilities: FacilityLedger = ensure_facility_ledger(world)
    target_kind = FacilityKind[cfg.repair_facility_kind] if cfg.repair_facility_kind in FacilityKind.__members__ else FacilityKind.WORKSHOP
    candidates = [fac for fac in facilities.values() if fac.kind is target_kind]
    if not candidates:
        return None
    return sorted(candidates, key=lambda fac: fac.facility_id)[0]


def _ensure_job_delivery(world: Any, *, job: SuitRepairJob, cfg: SuitWearConfig) -> None:
    job.bom = _normalize_bom(job.bom)
    if job.pending_delivery_ids:
        return
    logistics = ensure_logistics(world)
    delivery_id = f"delivery:{job.job_id}"
    if delivery_id in logistics.deliveries:
        job.pending_delivery_ids.append(delivery_id)
        return

    items = {material.name: int(qty) for material, qty in job.bom.items() if qty > 0}
    if not items or job.facility_id is None:
        return
    dest_lookup = getattr(world, "facility_node_lookup", {}) or {}
    facilities: FacilityLedger = ensure_facility_ledger(world)
    facility = facilities.get(job.facility_id) if isinstance(facilities, FacilityLedger) else None
    dest_node_id = dest_lookup.get(job.facility_id, getattr(facility, "site_node_id", ""))
    origin_node = getattr(world, "central_depot_node_id", "loc:depot")
    delivery = DeliveryRequest(
        delivery_id=delivery_id,
        project_id=job.job_id,
        origin_node_id=origin_node,
        dest_node_id=dest_node_id,
        items=items,
        status=DeliveryStatus.REQUESTED,
        created_tick=getattr(world, "tick", 0),
        origin_owner_id=getattr(cfg, "default_depot_owner_id", "ward:0"),
        dest_owner_id=job.agent_id,
        notes={"priority": "suit-repair", "job_id": job.job_id},
    )
    logistics.add(delivery)
    job.pending_delivery_ids.append(delivery_id)


def _assign_repairer(world: Any, *, job: SuitRepairJob, day: int, cfg: SuitWearConfig) -> None:
    if job.assigned_agent_ids:
        return
    workforce: WorkforceLedger = ensure_workforce(world)
    candidates = []
    for agent_id in sorted(getattr(world, "agents", {}).keys()):
        if agent_id == job.agent_id:
            continue
        assignment = workforce.get(agent_id)
        if assignment.kind is AssignmentKind.IDLE:
            candidates.append(agent_id)
    if not candidates:
        return
    repairer = candidates[0]
    workforce.assign(
        Assignment(
            agent_id=repairer,
            kind=AssignmentKind.MAINTENANCE,
            target_id=job.job_id,
            start_day=day,
            notes={"crew_kind": "suit_repair"},
        )
    )
    job.assigned_agent_ids.append(repairer)


def _apply_deliveries(world: Any, job: SuitRepairJob) -> None:
    registry: InventoryRegistry = ensure_inventory_registry(world)
    logistics: LogisticsLedger = ensure_logistics(world)
    for delivery_id in list(job.pending_delivery_ids):
        delivery = logistics.deliveries.get(delivery_id)
        if delivery is None or delivery.status is not DeliveryStatus.DELIVERED:
            continue
        inv = registry.inv(job.agent_id)
        for item, qty in delivery.items.items():
            material = Material[item] if isinstance(item, str) else item
            inv.add(material, int(qty))
        job.pending_delivery_ids.remove(delivery_id)


def _job_ready(job: SuitRepairJob, inventory: InventoryRegistry) -> bool:
    job.bom = _normalize_bom(job.bom)
    inv = inventory.inv(job.agent_id)
    return inv.can_afford(job.bom)


def _complete_job(world: Any, *, job: SuitRepairJob, day: int) -> None:
    registry = ensure_inventory_registry(world)
    workforce: WorkforceLedger = ensure_workforce(world)
    agent = getattr(world, "agents", {}).get(job.agent_id)
    job.bom = _normalize_bom(job.bom)
    inv = registry.inv(job.agent_id)
    inv.apply_bom(job.bom)
    if agent is not None:
        suit = _ensure_agent_suit(agent)
        suit.integrity = 1.0
        suit.repair_needed = False
        suit.last_repair_day = day
        suit.reset_flags()
    for agent_id in list(job.assigned_agent_ids):
        workforce.unassign(agent_id)
    job.assigned_agent_ids.clear()
    job.status = "DONE"
    metrics = _suit_metrics(world)
    metrics["repairs_done"] = metrics.get("repairs_done", 0.0) + 1.0
    ensure_metrics(world).inc("suits.repairs_done", 1)
    _emit_event(
        world,
        day=day,
        kind=EventKind.SUIT_REPAIRED,
        subject_id=job.agent_id,
        severity=0.2,
        payload={"facility_id": job.facility_id or "", "job_id": job.job_id},
    )
    ledger = ensure_suit_ledger(world)
    ledger.open_jobs_by_agent.pop(job.agent_id, None)


def _open_repair_jobs(world: Any, *, day: int, cfg: SuitWearConfig, state: SuitWearState) -> None:
    if state.repairs_started_today >= max(0, int(cfg.max_repairs_per_day)):
        return
    ledger = ensure_suit_ledger(world)
    facility = _choose_facility(world, cfg)
    agents = getattr(world, "agents", {})
    for agent_id in sorted(agents.keys()):
        if state.repairs_started_today >= max(0, int(cfg.max_repairs_per_day)):
            break
        agent = agents[agent_id]
        suit = _ensure_agent_suit(agent)
        if not suit.repair_needed:
            continue
        if ledger.open_jobs_by_agent.get(agent_id):
            continue
        if facility is None:
            continue
        job_id = f"suit:{agent_id}:{day}"
        job = SuitRepairJob(
            job_id=job_id,
            agent_id=agent_id,
            facility_id=facility.facility_id,
            created_day=day,
            due_day=day + max(1, int(cfg.repair_duration_days)),
            status="OPEN",
            bom=_bom_for_repair(),
        )
        ledger.jobs[job_id] = job
        ledger.open_jobs_by_agent[agent_id] = job_id
        state.repairs_started_today += 1
        metrics = _suit_metrics(world)
        metrics["repairs_started"] = metrics.get("repairs_started", 0.0) + 1.0
        ensure_metrics(world).inc("suits.repairs_started", 1)
        _emit_event(
            world,
            day=day,
            kind=EventKind.SUIT_REPAIR_STARTED,
            subject_id=agent_id,
            severity=0.4,
            payload={"job_id": job_id, "facility_id": facility.facility_id},
        )
        _ensure_job_delivery(world, job=job, cfg=cfg)


def _process_jobs(world: Any, *, day: int, cfg: SuitWearConfig) -> None:
    ledger = ensure_suit_ledger(world)
    inventory = ensure_inventory_registry(world)
    for job_id in sorted(ledger.jobs.keys()):
        job = ledger.jobs[job_id]
        _ensure_job_delivery(world, job=job, cfg=cfg)
        _assign_repairer(world, job=job, day=day, cfg=cfg)
        _apply_deliveries(world, job)
        if job.status in {"OPEN", "WAITING_PARTS"}:
            job.status = "IN_PROGRESS" if _job_ready(job, inventory) else "WAITING_PARTS"
        if job.status == "IN_PROGRESS":
            job.progress_days += 1
            if job.progress_days >= max(1, int(cfg.repair_duration_days)):
                _complete_job(world, job=job, day=day)


def run_suit_wear_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_suit_config(world)
    state = ensure_suit_state(world)
    ensure_suit_ledger(world)

    if not getattr(cfg, "enabled", False):
        return

    if state.last_run_day != day:
        _apply_wear(world, day=day, cfg=cfg, state=state)
    _open_repair_jobs(world, day=day, cfg=cfg, state=state)
    _process_jobs(world, day=day, cfg=cfg)


__all__ = [
    "SuitWearConfig",
    "SuitWearState",
    "SuitRepairJob",
    "SuitRepairLedger",
    "ensure_suit_config",
    "ensure_suit_state",
    "ensure_suit_ledger",
    "run_suit_wear_for_day",
    "suit_decay_multiplier",
]
