from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Dict, Mapping

from dosadi.runtime.local_interactions import hashed_unit_float
from dosadi.world.facilities import Facility, FacilityKind, FacilityLedger, coerce_facility_kind, ensure_facility_ledger
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, ensure_logistics
from dosadi.world.materials import InventoryRegistry, Material, ensure_inventory_registry
from dosadi.world.workforce import Assignment, AssignmentKind, WorkforceLedger, ensure_workforce
from dosadi.world.phases import WorldPhase


@dataclass(slots=True)
class MaintenanceConfig:
    enabled: bool = False
    wear_per_day_base: float = 0.003
    wear_per_day_phase2_mult: float = 1.25
    threshold_warn: float = 0.60
    threshold_required: float = 0.80
    threshold_shutdown: float = 0.95
    max_jobs_per_day: int = 10
    job_duration_days: int = 2
    auto_request_parts: bool = True
    auto_assign_crew: bool = True
    crew_kind: str = "MAINTENANCE_CREW"
    parts_source_policy: str = "nearest_depot_then_any"
    deterministic_salt: str = "maint-v1"


@dataclass(slots=True)
class MaintenanceState:
    last_run_day: int = -1
    jobs_open_today: int = 0


@dataclass(slots=True)
class MaintenanceJob:
    job_id: str
    facility_id: str
    owner_id: str
    created_day: int
    due_day: int
    status: str
    bom: Dict[Material, int]
    pending_delivery_ids: list[str] = field(default_factory=list)
    assigned_agent_ids: list[str] = field(default_factory=list)
    progress_days: int = 0
    notes: Dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class MaintenanceLedger:
    jobs: Dict[str, MaintenanceJob] = field(default_factory=dict)
    open_jobs_by_facility: Dict[str, str] = field(default_factory=dict)

    def signature(self) -> str:
        canonical = {
            job_id: {
                "facility_id": job.facility_id,
                "owner_id": job.owner_id,
                "created_day": job.created_day,
                "due_day": job.due_day,
                "status": job.status,
                "bom": {material.name: qty for material, qty in sorted(job.bom.items(), key=lambda i: i[0].name)},
                "pending_delivery_ids": list(sorted(job.pending_delivery_ids)),
                "assigned_agent_ids": list(sorted(job.assigned_agent_ids)),
                "progress_days": job.progress_days,
            }
            for job_id, job in sorted(self.jobs.items())
        }
        return sha256(str(canonical).encode("utf-8")).hexdigest()


def _maintenance_metrics(world: Any) -> Dict[str, float]:
    metrics: Dict[str, Any] = getattr(world, "metrics", None) or {}
    world.metrics = metrics
    bucket = metrics.get("maintenance")
    if not isinstance(bucket, dict):
        bucket = {}
        metrics["maintenance"] = bucket
    return bucket  # type: ignore[return-value]


def _emit_event(world: Any, event: Mapping[str, object]) -> None:
    log = getattr(world, "runtime_events", None)
    if not isinstance(log, list):
        log = []
    payload = dict(event)
    payload.setdefault("day", getattr(world, "day", 0))
    log.append(payload)
    world.runtime_events = log


def ensure_maintenance_config(world: Any) -> MaintenanceConfig:
    cfg = getattr(world, "maint_cfg", None)
    if not isinstance(cfg, MaintenanceConfig):
        cfg = MaintenanceConfig()
        setattr(world, "maint_cfg", cfg)
    return cfg


def ensure_maintenance_state(world: Any) -> MaintenanceState:
    state = getattr(world, "maint_state", None)
    if not isinstance(state, MaintenanceState):
        state = MaintenanceState()
        setattr(world, "maint_state", state)
    return state


def ensure_maintenance_ledger(world: Any) -> MaintenanceLedger:
    ledger = getattr(world, "maintenance", None)
    if not isinstance(ledger, MaintenanceLedger):
        ledger = MaintenanceLedger()
        setattr(world, "maintenance", ledger)
    return ledger


def _phase_multiplier(world: Any, cfg: MaintenanceConfig) -> float:
    phase_state = getattr(world, "phase_state", None)
    phase = getattr(phase_state, "phase", None)
    if phase is None:
        return 1.0
    if phase == WorldPhase.PHASE2:
        return cfg.wear_per_day_phase2_mult
    return 1.0


def _kind_multiplier(kind: FacilityKind) -> float:
    table = {
        FacilityKind.DEPOT: 0.6,
        FacilityKind.WORKSHOP: 1.0,
        FacilityKind.RECYCLER: 1.2,
        FacilityKind.REFINERY: 1.1,
    }
    return table.get(kind, 1.0)


def update_facility_wear(world: Any, *, day: int) -> None:
    cfg = ensure_maintenance_config(world)
    state = ensure_maintenance_state(world)
    ledger = ensure_maintenance_ledger(world)
    facilities: FacilityLedger = ensure_facility_ledger(world)

    if not getattr(cfg, "enabled", False):
        return

    if state.last_run_day == day:
        return

    phase_mult = _phase_multiplier(world, cfg)
    metrics = _maintenance_metrics(world)

    for facility_id in sorted(facilities.keys()):
        facility: Facility = facilities[facility_id]
        facility.kind = coerce_facility_kind(getattr(facility, "kind", FacilityKind.DEPOT))

        delta = cfg.wear_per_day_base * _kind_multiplier(facility.kind) * phase_mult
        jitter = hashed_unit_float(cfg.deterministic_salt, "wear", facility_id, str(day))
        delta *= 0.9 + 0.2 * jitter
        facility.wear = min(1.0, max(0.0, getattr(facility, "wear", 0.0) + delta))

        if facility.wear >= cfg.threshold_warn:
            _emit_event(
                world,
                {
                    "type": "FACILITY_WEAR_WARN",
                    "facility_id": facility_id,
                    "wear": facility.wear,
                },
            )

        if facility.wear >= cfg.threshold_required:
            facility.maintenance_due = True

        if facility.wear >= cfg.threshold_shutdown:
            facility.is_operational = False
            facility.down_until_day = max(getattr(facility, "down_until_day", -1), day)
            metrics["facilities_shutdown"] = metrics.get("facilities_shutdown", 0.0) + 1.0
            _emit_event(
                world,
                {
                    "type": "FACILITY_SHUTDOWN_WEAR",
                    "facility_id": facility_id,
                    "wear": facility.wear,
                },
            )

    state.jobs_open_today = 0
    state.last_run_day = day

    maybe_open_maintenance_jobs(world, day=day)
    process_maintenance_jobs(world, day=day)


def _bom_for_facility(facility: Facility) -> Dict[Material, int]:
    table: Dict[FacilityKind, Dict[Material, int]] = {
        FacilityKind.DEPOT: {Material.FASTENERS: 2, Material.SEALANT: 1},
        FacilityKind.WORKSHOP: {
            Material.FASTENERS: 4,
            Material.SEALANT: 2,
            Material.SCRAP_METAL: 5,
        },
        FacilityKind.RECYCLER: {
            Material.FASTENERS: 5,
            Material.SEALANT: 2,
            Material.PLASTICS: 3,
        },
    }
    return dict(table.get(facility.kind, {}))


def maybe_open_maintenance_jobs(world: Any, *, day: int) -> None:
    cfg = ensure_maintenance_config(world)
    state = ensure_maintenance_state(world)
    ledger = ensure_maintenance_ledger(world)
    facilities: FacilityLedger = ensure_facility_ledger(world)

    if not getattr(cfg, "enabled", False):
        return

    for facility_id in sorted(facilities.keys()):
        facility = facilities[facility_id]
        if state.jobs_open_today >= max(0, int(cfg.max_jobs_per_day)):
            break
        if not getattr(facility, "maintenance_due", False):
            continue
        if ledger.open_jobs_by_facility.get(facility_id):
            continue

        bom = _bom_for_facility(facility)
        job_id = f"maint:{facility_id}:{day}"
        job = MaintenanceJob(
            job_id=job_id,
            facility_id=facility_id,
            owner_id=f"facility:{facility_id}",
            created_day=day,
            due_day=day + max(1, int(cfg.job_duration_days)),
            status="OPEN",
            bom=bom,
        )

        ledger.jobs[job_id] = job
        ledger.open_jobs_by_facility[facility_id] = job_id
        facility.maintenance_job_id = job_id
        state.jobs_open_today += 1

        metrics = _maintenance_metrics(world)
        metrics["jobs_opened"] = metrics.get("jobs_opened", 0.0) + 1.0
        _emit_event(world, {"type": "MAINT_JOB_OPENED", "job_id": job_id, "facility_id": facility_id})


def _ensure_job_delivery(world: Any, job: MaintenanceJob, *, cfg: MaintenanceConfig) -> None:
    if not getattr(cfg, "auto_request_parts", False):
        return

    if job.pending_delivery_ids:
        return

    logistics = ensure_logistics(world)
    delivery_id = f"delivery:{job.job_id}"
    if delivery_id in logistics.deliveries:
        job.pending_delivery_ids.append(delivery_id)
        return

    items = {material.name: int(qty) for material, qty in job.bom.items() if qty > 0}
    if not items:
        return

    delivery = DeliveryRequest(
        delivery_id=delivery_id,
        project_id=job.job_id,
        origin_node_id=getattr(world, "central_depot_node_id", "loc:depot"),
        dest_node_id=getattr(world, "facility_node_lookup", {}).get(job.facility_id, ""),
        items=items,
        status=DeliveryStatus.REQUESTED,
        created_tick=getattr(world, "tick", 0),
        origin_owner_id=getattr(cfg, "default_depot_owner_id", "ward:0"),
        dest_owner_id=job.owner_id,
        notes={"priority": "maintenance", "job_id": job.job_id},
    )

    logistics.add(delivery)
    job.pending_delivery_ids.append(delivery_id)
    metrics = _maintenance_metrics(world)
    metrics["parts_deliveries_requested"] = metrics.get("parts_deliveries_requested", 0.0) + 1.0
    _emit_event(world, {"type": "MAINT_PARTS_REQUESTED", "job_id": job.job_id, "delivery_id": delivery_id})


def _assign_crew(world: Any, job: MaintenanceJob, *, day: int, cfg: MaintenanceConfig) -> None:
    if not getattr(cfg, "auto_assign_crew", False):
        return

    if job.assigned_agent_ids:
        return

    workforce: WorkforceLedger = ensure_workforce(world)
    candidates = []
    for agent_id in sorted(getattr(world, "agents", {}).keys()):
        assignment = workforce.get(agent_id)
        if assignment.kind is AssignmentKind.IDLE:
            candidates.append(agent_id)
    if not candidates:
        return

    agent_id = candidates[0]
    workforce.assign(
        Assignment(
            agent_id=agent_id,
            kind=AssignmentKind.MAINTENANCE,
            target_id=job.job_id,
            start_day=day,
            notes={"crew_kind": cfg.crew_kind},
        )
    )
    job.assigned_agent_ids.append(agent_id)
    metrics = _maintenance_metrics(world)
    metrics["crew_assigned"] = metrics.get("crew_assigned", 0.0) + 1.0


def _delivery_ready(delivery: DeliveryRequest) -> bool:
    return delivery.status in {DeliveryStatus.DELIVERED}


def _apply_deliveries(world: Any, job: MaintenanceJob) -> None:
    registry: InventoryRegistry = ensure_inventory_registry(world)
    logistics = ensure_logistics(world)
    for delivery_id in list(job.pending_delivery_ids):
        delivery = logistics.deliveries.get(delivery_id)
        if delivery is None or not _delivery_ready(delivery):
            continue
        inv = registry.inv(job.owner_id)
        for item, qty in delivery.items.items():
            material = Material[item] if isinstance(item, str) else item
            inv.add(material, int(qty))
        job.pending_delivery_ids.remove(delivery_id)


def _job_ready(job: MaintenanceJob, inventory: InventoryRegistry) -> bool:
    inv = inventory.inv(job.owner_id)
    if job.bom and not inv.can_afford(job.bom):
        return False
    return True


def _complete_job(world: Any, job: MaintenanceJob, *, day: int) -> None:
    registry = ensure_inventory_registry(world)
    facilities: FacilityLedger = ensure_facility_ledger(world)
    workforce: WorkforceLedger = ensure_workforce(world)
    facility = facilities.get(job.facility_id)
    inv = registry.inv(job.owner_id)

    inv.apply_bom(job.bom)
    if facility is not None:
        facility.wear = 0.0
        facility.maintenance_due = False
        facility.maintenance_job_id = None
        facility.is_operational = True
        facility.down_until_day = -1
    for agent_id in list(job.assigned_agent_ids):
        workforce.unassign(agent_id)
    job.assigned_agent_ids.clear()
    job.status = "DONE"
    metrics = _maintenance_metrics(world)
    metrics["jobs_done"] = metrics.get("jobs_done", 0.0) + 1.0
    _emit_event(world, {"type": "MAINT_JOB_DONE", "job_id": job.job_id, "facility_id": job.facility_id})
    _emit_event(
        world,
        {"type": "FACILITY_MAINTENANCE_COMPLETE", "facility_id": job.facility_id, "day": day},
    )
    ledger = ensure_maintenance_ledger(world)
    ledger.open_jobs_by_facility.pop(job.facility_id, None)


def process_maintenance_jobs(world: Any, *, day: int) -> None:
    cfg = ensure_maintenance_config(world)
    if not getattr(cfg, "enabled", False):
        return

    ledger = ensure_maintenance_ledger(world)
    inventory = ensure_inventory_registry(world)
    for job_id in sorted(ledger.jobs.keys()):
        job = ledger.jobs[job_id]
        _ensure_job_delivery(world, job, cfg=cfg)
        _assign_crew(world, job, day=day, cfg=cfg)
        _apply_deliveries(world, job)

        if job.status in {"OPEN", "WAITING_PARTS"}:
            job.status = "IN_PROGRESS" if _job_ready(job, inventory) and (job.assigned_agent_ids or not cfg.auto_assign_crew) else "WAITING_PARTS"
            if job.status == "IN_PROGRESS":
                _emit_event(world, {"type": "MAINT_JOB_STARTED", "job_id": job.job_id, "facility_id": job.facility_id})

        if job.status == "IN_PROGRESS":
            job.progress_days += 1
            if job.progress_days >= max(1, int(cfg.job_duration_days)):
                _complete_job(world, job, day=day)

