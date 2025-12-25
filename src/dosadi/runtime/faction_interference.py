from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable

from dosadi.runtime.corridor_risk import observe_edge_incident, risk_for_edge
from dosadi.runtime.market_signals import current_signal_urgency
from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.world.construction import (
    BlockReason,
    ConstructionProject,
    ProjectLedger,
    ProjectStatus,
    StageState,
)
from dosadi.world.incidents import Incident, IncidentKind, IncidentLedger
from dosadi.world.materials import ensure_inventory_registry, material_from_key
from dosadi.world.phases import WorldPhase
from dosadi.world.routing import edge_key
from dosadi.world.survey_map import SurveyMap
from dosadi.world.events import EventKind, WorldEvent, WorldEventLog
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, LogisticsLedger


@dataclass(slots=True)
class InterferenceConfig:
    enabled: bool = False
    base_events_per_day: float = 0.1
    phase_multiplier: dict[str, float] = field(
        default_factory=lambda: {"P0": 0.2, "P1": 1.0, "P2": 2.5}
    )
    max_events_per_day: int = 3
    target_cap: int = 30
    min_days_between_hits_same_target: int = 7
    escort_mitigation_per_guard: float = 0.20
    deterministic_salt: str = "interference-v1"


@dataclass(slots=True)
class InterferenceState:
    last_run_day: int = -1
    events_spawned_today: int = 0
    recent_target_hits: dict[str, int] = field(default_factory=dict)
    next_incident_seq: int = 0


@dataclass(slots=True)
class Target:
    kind: str
    target_id: str
    value: float
    payload: dict[str, object] = field(default_factory=dict)


def pseudo_rand01(key: str) -> float:
    digest = sha256(key.encode("utf-8")).digest()
    sample = int.from_bytes(digest[:8], "big")
    return sample / float(2**64)


def _phase(world: Any) -> WorldPhase:
    phase_state = getattr(world, "phase_state", None)
    phase = getattr(phase_state, "phase", WorldPhase.PHASE0)
    try:
        return WorldPhase(phase)
    except Exception:
        return WorldPhase.PHASE0


def _clamp01(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


def _ensure_config(world: Any) -> InterferenceConfig:
    cfg = getattr(world, "intf_cfg", None)
    if not isinstance(cfg, InterferenceConfig):
        cfg = InterferenceConfig()
        world.intf_cfg = cfg
    return cfg


def _ensure_state(world: Any) -> InterferenceState:
    state = getattr(world, "intf_state", None)
    if not isinstance(state, InterferenceState):
        state = InterferenceState()
        world.intf_state = state
    return state


def _ensure_incident_ledger(world: Any) -> IncidentLedger:
    ledger = getattr(world, "incidents", None)
    if not isinstance(ledger, IncidentLedger):
        ledger = IncidentLedger()
        world.incidents = ledger
    return ledger


def _ensure_event_log(world: Any) -> WorldEventLog:
    log = getattr(world, "event_log", None)
    if not isinstance(log, WorldEventLog):
        log = WorldEventLog(max_len=5000)
        world.event_log = log
    return log


def _add_target(targets: list[Target], *, kind: str, target_id: str, value: float, payload: dict[str, object]) -> None:
    targets.append(Target(kind=kind, target_id=str(target_id), value=float(value), payload=payload))


def _delivery_targets(world: Any) -> list[Target]:
    ledger: LogisticsLedger | None = getattr(world, "logistics", None)
    if not isinstance(ledger, LogisticsLedger):
        return []
    targets: list[Target] = []
    for delivery_id in ledger.active_ids:
        delivery = ledger.deliveries.get(delivery_id)
        if delivery is None:
            continue
        if delivery.status not in {
            DeliveryStatus.REQUESTED,
            DeliveryStatus.ASSIGNED,
            DeliveryStatus.PICKED_UP,
            DeliveryStatus.IN_TRANSIT,
        }:
            continue
        urgency = 0.0
        for mat_key, qty in delivery.items.items():
            if qty <= 0:
                continue
            urgency = max(urgency, current_signal_urgency(world, str(mat_key)))
        _add_target(
            targets,
            kind="delivery",
            target_id=delivery_id,
            value=_clamp01(urgency),
            payload={"delivery": delivery},
        )
    return targets


def _depot_targets(world: Any, *, day: int) -> list[Target]:
    policies = getattr(world, "stock_policies", None)
    if policies is None or not hasattr(policies, "profiles"):
        return []
    registry = ensure_inventory_registry(world)
    targets: list[Target] = []
    for depot_id, profile in sorted(getattr(policies, "profiles", {}).items()):
        worst_gap = 0.0
        worst_material = None
        for mat_name, threshold in getattr(profile, "thresholds", {}).items():
            material = material_from_key(mat_name)
            if material is None:
                continue
            qty = registry.inv(depot_id).get(material)
            if qty <= 0:
                continue
            gap = max(0.0, float(getattr(threshold, "min_level", 0)) - qty)
            if gap > worst_gap:
                worst_gap = gap
                worst_material = material.name
        if worst_gap <= 0:
            continue
        value = _clamp01(worst_gap / (worst_gap + 50.0))
        _add_target(
            targets,
            kind="depot",
            target_id=depot_id,
            value=value,
            payload={"material": worst_material, "gap": worst_gap},
        )
    return targets


def _project_targets(world: Any) -> list[Target]:
    ledger: ProjectLedger | None = getattr(world, "projects", None)
    if not isinstance(ledger, ProjectLedger):
        return []
    targets: list[Target] = []
    for project_id, project in sorted(ledger.projects.items()):
        if project.status not in {ProjectStatus.APPROVED, ProjectStatus.STAGED, ProjectStatus.BUILDING}:
            continue
        progress = getattr(project, "progress_days_in_stage", 0)
        value = _clamp01(0.3 + 0.05 * progress)
        _add_target(
            targets,
            kind="project",
            target_id=project_id,
            value=value,
            payload={"project": project},
        )
    return targets


def _corridor_targets(world: Any) -> list[Target]:
    ledger = getattr(world, "risk_ledger", None)
    if ledger is None or not hasattr(ledger, "edges"):
        return []
    targets: list[Target] = []
    for edge_key_id, record in sorted(getattr(ledger, "edges", {}).items()):
        value = getattr(record, "risk", 0.0)
        if value <= 0:
            continue
        _add_target(
            targets,
            kind="corridor",
            target_id=edge_key_id,
            value=_clamp01(value),
            payload={"risk": value},
        )
    return targets


def _target_basket(world: Any, *, cfg: InterferenceConfig, day: int) -> list[Target]:
    targets: list[Target] = []
    targets.extend(_delivery_targets(world))
    targets.extend(_depot_targets(world, day=day))
    targets.extend(_project_targets(world))
    targets.extend(_corridor_targets(world))

    order = {"delivery": 0, "depot": 1, "project": 2, "corridor": 3}
    targets.sort(key=lambda t: (-t.value, order.get(t.kind, 99), t.target_id))
    return targets[: max(0, int(cfg.target_cap))]


def _cooldown_ok(state: InterferenceState, target: Target, *, cfg: InterferenceConfig, day: int) -> bool:
    last_hit = state.recent_target_hits.get(f"{target.kind}:{target.target_id}")
    if last_hit is None:
        return True
    return day - last_hit >= cfg.min_days_between_hits_same_target


def _update_cooldown(state: InterferenceState, target: Target, *, day: int) -> None:
    state.recent_target_hits[f"{target.kind}:{target.target_id}"] = day


def _edge_for_delivery(world: Any, delivery: DeliveryRequest) -> str | None:
    if getattr(delivery, "route_edge_keys", None):
        ranked = sorted(
            delivery.route_edge_keys,
            key=lambda e: (-round(risk_for_edge(world, e), 6), e),
        )
        return ranked[0]
    if delivery.route_nodes:
        if len(delivery.route_nodes) >= 2:
            return edge_key(delivery.route_nodes[0], delivery.route_nodes[1])
    return None


def _apply_incident(world: Any, incident: Incident, *, severity: float, edge_key_ref: str | None) -> None:
    ledger = _ensure_incident_ledger(world)
    ledger.add(incident)
    incident.resolved = True
    incident.resolved_day = incident.day
    ledger.history.append(incident.incident_id)

    log = _ensure_event_log(world)
    log.append(
        WorldEvent(
            event_id="",
            day=incident.day,
            kind=EventKind.INCIDENT,
            subject_kind=incident.target_kind,
            subject_id=incident.target_id,
            severity=severity,
            payload=dict(incident.payload),
        )
    )

    if edge_key_ref:
        observe_edge_incident(world, edge_key_ref, day=incident.day, severity=severity)
        record_event(world, {"kind": "interference.edge", "day": incident.day, "edge_key": edge_key_ref})


def _spawn_theft_cargo(world: Any, *, day: int, target: Target, cfg: InterferenceConfig, state: InterferenceState) -> None:
    delivery: DeliveryRequest | None = target.payload.get("delivery") if isinstance(target.payload, dict) else None
    if delivery is None:
        return
    if not isinstance(delivery.items, dict):
        return
    escorts = len(getattr(delivery, "escort_agent_ids", []) or [])
    mitigation = max(0.2, 1.0 - escorts * cfg.escort_mitigation_per_guard)
    severity = _clamp01(max(target.value, 0.2) * mitigation)

    chosen_mat = None
    chosen_qty = 0.0
    for mat_key, qty in delivery.items.items():
        if qty <= 0:
            continue
        urgency = current_signal_urgency(world, str(mat_key))
        score = urgency + qty / (qty + 100.0)
        if score > chosen_qty:
            chosen_qty = score
            chosen_mat = mat_key

    if chosen_mat is None:
        return
    available = max(0.0, float(delivery.items.get(chosen_mat, 0.0)))
    stolen = min(available, max(1.0, round(available * 0.25 * (0.5 + severity))))
    delivery.items[chosen_mat] = max(0.0, available - stolen)

    metrics = ensure_metrics(world)
    metrics.inc("interference.spawned", 1.0)
    metrics.inc("interference.theft_units_total", stolen)
    metrics.topk_add(
        "interference.targets_hit",
        f"delivery:{delivery.delivery_id}",
        target.value,
        payload={"stolen": stolen, "material": chosen_mat},
    )

    edge_ref = _edge_for_delivery(world, delivery)
    incident_id = f"inc:intf:{day}:{state.next_incident_seq}"
    state.next_incident_seq += 1
    payload = {
        "incident_id": incident_id,
        "incident_kind": IncidentKind.THEFT_CARGO.value,
        "target_kind": "delivery",
        "target_id": delivery.delivery_id,
        "severity": severity,
        "stolen_qty": stolen,
        "material": chosen_mat,
        "edge_key": edge_ref,
    }
    incident = Incident(
        incident_id=incident_id,
        kind=IncidentKind.THEFT_CARGO,
        day=day,
        target_kind="delivery",
        target_id=delivery.delivery_id,
        severity=severity,
        payload=payload,
    )
    _apply_incident(world, incident, severity=severity, edge_key_ref=edge_ref)


def _spawn_theft_depot(world: Any, *, day: int, target: Target, cfg: InterferenceConfig, state: InterferenceState) -> None:
    registry = ensure_inventory_registry(world)
    material = material_from_key(target.payload.get("material") if isinstance(target.payload, dict) else None)
    inventory = registry.inv(target.target_id)
    if material is None:
        return
    available = float(inventory.get(material))
    if available <= 0:
        return
    severity = _clamp01(max(target.value, 0.2))
    stolen = min(available, max(1.0, round(available * 0.2 * (0.5 + severity))))
    inventory.remove(material, int(stolen))

    metrics = ensure_metrics(world)
    metrics.inc("interference.spawned", 1.0)
    metrics.inc("interference.theft_units_total", stolen)
    metrics.topk_add(
        "interference.targets_hit",
        f"depot:{target.target_id}",
        target.value,
        payload={"stolen": stolen, "material": material.name},
    )

    incident_id = f"inc:intf:{day}:{state.next_incident_seq}"
    state.next_incident_seq += 1
    payload = {
        "incident_id": incident_id,
        "incident_kind": IncidentKind.THEFT_DEPOT.value,
        "target_kind": "depot",
        "target_id": target.target_id,
        "severity": severity,
        "stolen_qty": stolen,
        "material": material.name,
        "node_id": target.target_id,
    }
    incident = Incident(
        incident_id=incident_id,
        kind=IncidentKind.THEFT_DEPOT,
        day=day,
        target_kind="depot",
        target_id=target.target_id,
        severity=severity,
        payload=payload,
    )
    _apply_incident(world, incident, severity=severity, edge_key_ref=None)


def _spawn_sabotage_project(world: Any, *, day: int, target: Target, cfg: InterferenceConfig, state: InterferenceState) -> None:
    project: ConstructionProject | None = target.payload.get("project") if isinstance(target.payload, dict) else None
    if project is None:
        return
    downtime_days = max(1, int(round(1 + target.value * 2)))
    project.incident_paused = True
    project.stage_state = StageState.PAUSED_INCIDENT
    project.block_reason = BlockReason(code="INCIDENT", msg="Sabotage downtime", details={"days": downtime_days})
    project.notes["incident_pause_until_day"] = day + downtime_days
    project.progress_days_in_stage = max(0, project.progress_days_in_stage - 1)

    metrics = ensure_metrics(world)
    metrics.inc("interference.spawned", 1.0)
    metrics.inc("interference.sabotage_days_total", downtime_days)
    metrics.topk_add(
        "interference.targets_hit",
        f"project:{project.project_id}",
        target.value,
        payload={"downtime": downtime_days},
    )

    incident_id = f"inc:intf:{day}:{state.next_incident_seq}"
    state.next_incident_seq += 1
    payload = {
        "incident_id": incident_id,
        "incident_kind": IncidentKind.SABOTAGE_PROJECT.value,
        "target_kind": "project",
        "target_id": project.project_id,
        "severity": _clamp01(target.value),
        "downtime_days": downtime_days,
        "node_id": project.site_node_id,
    }
    incident = Incident(
        incident_id=incident_id,
        kind=IncidentKind.SABOTAGE_PROJECT,
        day=day,
        target_kind="project",
        target_id=project.project_id,
        severity=_clamp01(target.value),
        payload=payload,
    )
    _apply_incident(world, incident, severity=_clamp01(target.value), edge_key_ref=None)


def _maybe_release_project_pauses(world: Any, *, day: int) -> None:
    ledger: ProjectLedger | None = getattr(world, "projects", None)
    if not isinstance(ledger, ProjectLedger):
        return
    for project in ledger.projects.values():
        until_day = None
        if isinstance(project.notes, dict):
            until_day = project.notes.get("incident_pause_until_day")
        try:
            until_day_int = int(until_day) if until_day is not None else None
        except Exception:
            until_day_int = None
        if until_day_int is not None and day >= until_day_int:
            project.incident_paused = False
            project.notes.pop("incident_pause_until_day", None)
            if project.stage_state is StageState.PAUSED_INCIDENT:
                project.stage_state = StageState.READY


def _spawn_for_target(world: Any, *, target: Target, cfg: InterferenceConfig, state: InterferenceState, day: int) -> None:
    if target.kind == "delivery":
        _spawn_theft_cargo(world, day=day, target=target, cfg=cfg, state=state)
    elif target.kind == "depot":
        _spawn_theft_depot(world, day=day, target=target, cfg=cfg, state=state)
    elif target.kind == "project":
        _spawn_sabotage_project(world, day=day, target=target, cfg=cfg, state=state)


def run_faction_interference_for_day(world: Any, *, day: int) -> None:
    cfg = _ensure_config(world)
    state = _ensure_state(world)
    _ensure_incident_ledger(world)
    _ensure_event_log(world)

    if not cfg.enabled:
        return
    if state.last_run_day == day:
        return

    if state.last_run_day != day:
        state.events_spawned_today = 0

    _maybe_release_project_pauses(world, day=day)

    phase = _phase(world)
    multiplier = cfg.phase_multiplier.get(phase.name, 1.0)
    rate = cfg.base_events_per_day * multiplier
    targets = _target_basket(world, cfg=cfg, day=day)

    for slot in range(max(0, int(cfg.max_events_per_day))):
        threshold = rate / max(1, cfg.max_events_per_day)
        key = f"{cfg.deterministic_salt}|day:{day}|slot:{slot}"
        if pseudo_rand01(key) >= threshold:
            continue
        target: Target | None = None
        for candidate in targets:
            if _cooldown_ok(state, candidate, cfg=cfg, day=day):
                target = candidate
                break
        if target is None:
            break
        _spawn_for_target(world, target=target, cfg=cfg, state=state, day=day)
        _update_cooldown(state, target, day=day)
        state.events_spawned_today += 1
    state.last_run_day = day

