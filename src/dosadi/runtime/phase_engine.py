from __future__ import annotations

from dataclasses import asdict

from dosadi.world.construction import ProjectLedger, ProjectStatus
from dosadi.world.events import EventKind, WorldEvent, WorldEventLog
from dosadi.world.facilities import FacilityLedger, get_facility_behavior
from dosadi.world.logistics import DeliveryStatus, LogisticsLedger
from dosadi.world.phases import KPISnapshot, PhaseConfig, PhaseState, WorldPhase
from dosadi.world.workforce import AssignmentKind, WorkforceLedger


def compute_kpis(world, *, day: int) -> KPISnapshot:
    stockpiles = getattr(world, "stockpiles", {}) or {}
    water_total = float(stockpiles.get("water", 0.0))
    population = len(getattr(world, "agents", {}))
    water_per_capita = water_total / max(1, population)

    logistics = getattr(world, "logistics", None)
    logistics_backlog = 0
    if isinstance(logistics, LogisticsLedger):
        backlog_status = {
            DeliveryStatus.REQUESTED.value,
            DeliveryStatus.ASSIGNED.value,
            DeliveryStatus.PICKED_UP.value,
            DeliveryStatus.IN_TRANSIT.value,
        }
        logistics_backlog = 0
        for delivery in logistics.deliveries.values():
            status = getattr(delivery, "status", None)
            status_label = status.value if isinstance(status, DeliveryStatus) else str(status)
            if status_label in backlog_status:
                logistics_backlog += 1

    projects = getattr(world, "projects", None)
    workforce = getattr(world, "workforce", None)
    maintenance_backlog = 0
    if isinstance(projects, ProjectLedger):
        for project in projects.projects.values():
            status = getattr(project, "status", None)
            status_label = status.value if isinstance(status, ProjectStatus) else str(status)
            if status_label == ProjectStatus.APPROVED.value:
                maintenance_backlog += 1
            elif status_label == ProjectStatus.BUILDING.value:
                if isinstance(workforce, WorkforceLedger):
                    staffed = any(
                        assignment.kind is AssignmentKind.PROJECT_WORK
                        and assignment.target_id == project.project_id
                        for assignment in workforce.assignments.values()
                    )
                    if not staffed:
                        maintenance_backlog += 1
                else:
                    maintenance_backlog += 1

    facilities = getattr(world, "facilities", None)
    if isinstance(facilities, FacilityLedger):
        maintenance_backlog += sum(1 for facility in facilities.values() if facility.status != "ACTIVE")

    return KPISnapshot(
        day=day,
        water_total=water_total,
        population=population,
        water_per_capita=water_per_capita,
        logistics_backlog=logistics_backlog,
        maintenance_backlog=maintenance_backlog,
    )


def update_kpi_ring(state: PhaseState, snap: KPISnapshot, *, max_len: int = 120) -> None:
    state.kpi_ring.append(snap)
    if len(state.kpi_ring) > max_len:
        state.kpi_ring[:] = state.kpi_ring[-max_len:]


def _ensure_event_log(world) -> WorldEventLog:
    log: WorldEventLog | None = getattr(world, "event_log", None)
    if not isinstance(log, WorldEventLog):
        log = WorldEventLog(max_len=5000)
        world.event_log = log
    return log


def _signals_for_phase0(cfg: PhaseConfig, snap: KPISnapshot) -> list[str]:
    signals: list[str] = []
    if snap.water_per_capita < cfg.water_per_capita_p0_to_p1:
        signals.append("water")
    if snap.logistics_backlog >= cfg.logistics_backlog_p0_to_p1:
        signals.append("logistics")
    return signals


def _signals_for_phase1(cfg: PhaseConfig, snap: KPISnapshot) -> list[str]:
    signals: list[str] = []
    if snap.water_per_capita < cfg.water_per_capita_p1_to_p2:
        signals.append("water")
    if snap.logistics_backlog >= cfg.logistics_backlog_p1_to_p2:
        signals.append("logistics")
    if snap.maintenance_backlog >= cfg.maintenance_backlog_p1_to_p2:
        signals.append("maintenance")
    return signals


def _apply_phase_policies(world, *, phase: WorldPhase) -> None:
    apply_phase_to_planner(getattr(world, "expansion_planner_cfg", None), phase)
    staffing_cfg = getattr(world, "staffing_cfg", None) or getattr(world, "staffing_config", None)
    apply_phase_to_staffing(
        staffing_cfg,
        phase,
        council_cfg=getattr(world, "council_staffing_config", None),
    )
    apply_phase_to_logistics(world, phase)
    apply_phase_to_facilities(world, phase)


def _emit_phase_event(world, *, day: int, prior: WorldPhase, new: WorldPhase) -> None:
    log = _ensure_event_log(world)
    event = WorldEvent(
        event_id="",
        day=day,
        kind=EventKind.PHASE_TRANSITION,
        subject_kind="phase",
        subject_id=f"{int(prior)}->{int(new)}",
        severity=0.0,
        payload={"from": int(prior), "to": int(new)},
    )
    log.append(event)


def maybe_advance_phase(world, *, day: int) -> KPISnapshot:
    state = getattr(world, "phase_state", PhaseState())
    cfg = getattr(world, "phase_cfg", PhaseConfig())

    if day == state.last_eval_day:
        return state.kpi_ring[-1] if state.kpi_ring else compute_kpis(world, day=day)

    snap = compute_kpis(world, day=day)
    update_kpi_ring(state, snap)
    state.last_eval_day = day

    current_phase = state.phase
    signals: list[str] = []
    if current_phase is WorldPhase.PHASE0:
        if day - state.phase_day >= cfg.min_days_in_phase0:
            signals = _signals_for_phase0(cfg, snap)
            if signals:
                state.phase = WorldPhase.PHASE1
    elif current_phase is WorldPhase.PHASE1:
        if day - state.phase_day >= cfg.min_days_in_phase1:
            signals = _signals_for_phase1(cfg, snap)
            required = 2 if cfg.require_multiple_signals else 1
            if len(signals) >= required:
                state.phase = WorldPhase.PHASE2

    if state.phase != current_phase:
        state.history.append({
            "day": day,
            "from": int(current_phase),
            "to": int(state.phase),
            "reasons": list(signals),
            "kpi": asdict(snap),
        })
        state.phase_day = day
        _apply_phase_policies(world, phase=state.phase)
        _emit_phase_event(world, day=day, prior=current_phase, new=state.phase)

    world.phase_state = state
    return snap


def apply_phase_to_planner(cfg, phase: WorldPhase) -> None:
    if cfg is None:
        return

    if phase is WorldPhase.PHASE0:
        cfg.max_new_projects_per_cycle += 1
        cfg.max_active_projects += 1
    elif phase is WorldPhase.PHASE1:
        cfg.min_site_confidence = min(1.0, cfg.min_site_confidence + 0.1)
    elif phase is WorldPhase.PHASE2:
        cfg.max_new_projects_per_cycle = max(0, cfg.max_new_projects_per_cycle - 1)
        cfg.max_active_projects = max(1, cfg.max_active_projects - 1)
        cfg.project_kinds = tuple(sorted(set(cfg.project_kinds) & {"pump_station", "outpost"})) or cfg.project_kinds
        cfg.min_idle_agents = max(cfg.min_idle_agents, 15)


def apply_phase_to_staffing(cfg, phase: WorldPhase, *, council_cfg=None) -> None:
    if cfg is None:
        return

    if phase is WorldPhase.PHASE0:
        cfg.project_workers_default = max(1, cfg.project_workers_default + 1)
        cfg.min_idle_agents = max(5, cfg.min_idle_agents - 2)
    elif phase is WorldPhase.PHASE1:
        cfg.min_idle_agents = max(cfg.min_idle_agents, 10)
    elif phase is WorldPhase.PHASE2:
        cfg.project_workers_default = max(1, cfg.project_workers_default - 1)
        cfg.facility_staff_default = max(cfg.facility_staff_default, 3)
        cfg.min_idle_agents = max(cfg.min_idle_agents, 15)

    if council_cfg is not None and hasattr(council_cfg, "min_idle_agents"):
        council_cfg.min_idle_agents = max(council_cfg.min_idle_agents, cfg.min_idle_agents)


def apply_phase_to_logistics(world, phase: WorldPhase) -> None:
    if not hasattr(world, "logistics_loss_rate"):
        return

    if phase is WorldPhase.PHASE0:
        world.logistics_loss_rate = 0.0
    elif phase is WorldPhase.PHASE1:
        world.logistics_loss_rate = max(0.0, min(0.02, getattr(world, "logistics_loss_rate", 0.0)))
    elif phase is WorldPhase.PHASE2:
        world.logistics_loss_rate = max(0.05, getattr(world, "logistics_loss_rate", 0.0))


def apply_phase_to_facilities(world, phase: WorldPhase) -> None:
    facilities = getattr(world, "facilities", None)
    if not isinstance(facilities, FacilityLedger):
        return

    if phase is not WorldPhase.PHASE2:
        return

    for facility in facilities.values():
        try:
            behavior = get_facility_behavior(facility.kind)
        except KeyError:
            continue
        behavior.requires_labor = True
        behavior.labor_agents = max(behavior.labor_agents, 2)


__all__ = [
    "apply_phase_to_facilities",
    "apply_phase_to_logistics",
    "apply_phase_to_planner",
    "apply_phase_to_staffing",
    "compute_kpis",
    "maybe_advance_phase",
    "update_kpi_ring",
]
