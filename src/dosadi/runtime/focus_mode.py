from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List

from dosadi.world.construction import process_projects
from dosadi.world.events import EventKind, WorldEvent
from dosadi.world.logistics import (
    DeliveryRequest,
    DeliveryStatus,
    advance_delivery_along_route,
    ensure_logistics,
    process_logistics_until,
    release_courier,
)
from dosadi.world.workforce import AssignmentKind, WorkforceLedger, ensure_workforce


DEFAULT_TICKS_PER_DAY = 144_000


@dataclass(slots=True)
class FocusConfig:
    enabled: bool = False
    max_awake_agents: int = 40
    max_focus_ticks: int = 50_000
    default_focus_ticks: int = 10_000
    awake_action_budget_per_tick: int = 3
    ambient_step_granularity_ticks: int = 1_000
    emit_focus_events: bool = True


class FocusTargetKind(Enum):
    WARD = "WARD"
    NODE = "NODE"
    PROJECT = "PROJECT"
    DELIVERY = "DELIVERY"
    COURIER_MISSION = "COURIER_MISSION"


@dataclass(slots=True)
class FocusTarget:
    kind: FocusTargetKind
    id: str
    radius: int = 0


@dataclass(slots=True)
class FocusSession:
    session_id: str
    start_tick: int
    end_tick: int
    target: FocusTarget
    awake_agent_ids: list[str]
    seed_salt: str = "focus-v1"
    done_reason: str = ""


@dataclass(slots=True)
class FocusState:
    active: bool = False
    session: FocusSession | None = None
    last_tick: int = 0
    last_ambient_step_tick: int = 0


def _ticks_per_day(world: Any) -> int:
    ticks_per_day = getattr(world, "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", None)
    try:
        ticks_per_day = int(ticks_per_day) if ticks_per_day is not None else None
    except (TypeError, ValueError):
        ticks_per_day = None
    if ticks_per_day is None or ticks_per_day <= 0:
        return DEFAULT_TICKS_PER_DAY
    return ticks_per_day


def tick_to_day(world: Any, tick: int) -> int:
    return max(0, int(tick)) // max(1, _ticks_per_day(world))


def _focus_metrics(world: Any) -> dict:
    metrics = getattr(world, "metrics", {})
    world.metrics = metrics
    return metrics.setdefault("focus", {})  # type: ignore[arg-type]


def select_awake_agents(world, target: FocusTarget, *, day: int, max_n: int) -> list[str]:
    ledger: WorkforceLedger = ensure_workforce(world)
    agents = getattr(world, "agents", {}) or {}
    selected: list[str] = []

    if target.kind in {FocusTargetKind.DELIVERY, FocusTargetKind.COURIER_MISSION}:
        logistics = ensure_logistics(world)
        delivery = logistics.deliveries.get(target.id)
        if delivery is not None and delivery.assigned_carrier_id:
            if delivery.assigned_carrier_id in agents:
                selected.append(delivery.assigned_carrier_id)
        if delivery is not None:
            for agent_id, assignment in ledger.assignments.items():
                if (
                    assignment.kind is AssignmentKind.PROJECT_WORK
                    and assignment.target_id == delivery.project_id
                ):
                    selected.append(agent_id)

    if target.kind is FocusTargetKind.PROJECT:
        for agent_id, assignment in ledger.assignments.items():
            if assignment.kind is AssignmentKind.PROJECT_WORK and assignment.target_id == target.id:
                selected.append(agent_id)

    if target.kind is FocusTargetKind.WARD:
        for agent_id, agent in agents.items():
            if getattr(agent, "ward", None) == target.id:
                selected.append(agent_id)

    if target.kind is FocusTargetKind.NODE:
        for agent_id, agent in agents.items():
            if getattr(agent, "location_id", None) == target.id:
                selected.append(agent_id)

    selected = sorted({*selected})
    return selected[: max(0, int(max_n))]


def _mark_awake_flags(world: Any, awake_ids: list[str], *, awake: bool) -> None:
    for agent_id in awake_ids:
        agent = getattr(world, "agents", {}).get(agent_id)
        if agent is None:
            continue
        setattr(agent, "is_awake", awake)
        setattr(agent, "sim_mode", "AWAKE" if awake else "AMBIENT")


def _run_daily_pipeline(world: Any, *, day: int) -> None:
    from dosadi.runtime.belief_formation import run_belief_formation_for_day
    from dosadi.runtime.event_to_memory_router import run_router_for_day
    from dosadi.runtime.facility_updates import update_facilities_for_day
    from dosadi.runtime.incident_engine import run_incident_engine_for_day
    from dosadi.runtime.maintenance import update_facility_wear
    from dosadi.runtime.local_interactions import run_interactions_for_day
    from dosadi.runtime.materials_economy import (
        evaluate_project_materials,
        run_materials_production_for_day,
    )
    from dosadi.runtime.extraction_runtime import run_extraction_for_day
    from dosadi.runtime.scouting import maybe_create_scout_missions, step_scout_missions_for_day
    from dosadi.runtime.staffing import StaffingConfig, StaffingState, run_staffing_policy
    from dosadi.world.expansion_planner import (
        ExpansionPlannerConfig,
        ExpansionPlannerState,
        maybe_plan,
    )

    world.day = day
    planner_cfg = getattr(world, "expansion_planner_cfg", None) or ExpansionPlannerConfig()
    planner_state = getattr(world, "expansion_planner_state", None) or ExpansionPlannerState(next_plan_day=0)
    world.expansion_planner_cfg = planner_cfg
    world.expansion_planner_state = planner_state
    staffing_cfg = getattr(world, "staffing_cfg", None) or StaffingConfig()
    staffing_state = getattr(world, "staffing_state", None) or StaffingState()
    world.staffing_cfg = staffing_cfg
    world.staffing_state = staffing_state
    scout_cfg = getattr(world, "scout_cfg", None)
    run_materials_production_for_day(world, day=day)
    evaluate_project_materials(world, day=day)
    maybe_create_scout_missions(world, cfg=scout_cfg)
    step_scout_missions_for_day(world, day=day, cfg=scout_cfg)
    update_facilities_for_day(world, day=day, days=1)
    update_facility_wear(world, day=day)
    run_extraction_for_day(world, day=day)
    run_incident_engine_for_day(world, day=day)
    run_interactions_for_day(world, day=day)
    run_router_for_day(world, day=day)
    run_belief_formation_for_day(world, day=day)
    maybe_plan(world, cfg=planner_cfg, state=planner_state)
    run_staffing_policy(world, day=day, cfg=staffing_cfg, state=staffing_state)


def _deliver(world: Any, delivery: DeliveryRequest, tick: int) -> None:
    delivery.status = DeliveryStatus.DELIVERED
    delivery.deliver_tick = tick
    release_courier(world, delivery.assigned_carrier_id)

    agent = getattr(world, "agents", {}).get(delivery.assigned_carrier_id)
    if agent is not None:
        agent.location_id = delivery.dest_node_id

    mat_enabled = bool(getattr(getattr(world, "mat_cfg", None), "enabled", False))
    dest_owner_id = getattr(delivery, "dest_owner_id", None)
    if mat_enabled and dest_owner_id:
        from dosadi.world.materials import ensure_inventory_registry, normalize_bom

        inventory = ensure_inventory_registry(world)
        bom = normalize_bom(delivery.items)
        inv = inventory.inv(dest_owner_id)
        for material, qty in bom.items():
            inv.add(material, qty)
        metrics = getattr(world, "metrics", {})
        if isinstance(metrics, dict):
            mat_metrics = metrics.setdefault("materials", {})
            if isinstance(mat_metrics, dict):
                mat_metrics["deliveries_completed"] = mat_metrics.get("deliveries_completed", 0.0) + 1.0

    projects = getattr(world, "projects", None)
    if projects and delivery.project_id in projects.projects:
        project = projects.projects[delivery.project_id]
        for item, qty in delivery.items.items():
            project.materials_delivered[item] = project.materials_delivered.get(item, 0.0) + qty
        if mat_enabled and delivery.delivery_id in project.pending_material_delivery_ids:
            project.pending_material_delivery_ids = [
                pid for pid in project.pending_material_delivery_ids if pid != delivery.delivery_id
            ]


def _awake_agent_step(world: Any, agent_id: str, tick: int, *, budget: int) -> None:
    ledger = ensure_workforce(world)
    assignment = ledger.get(agent_id)
    if assignment.kind is not AssignmentKind.LOGISTICS_COURIER:
        return

    logistics = ensure_logistics(world)
    delivery = logistics.deliveries.get(assignment.target_id or "")
    if delivery is None or delivery.status not in {DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT}:
        return

    advance_delivery_along_route(world, delivery, tick=tick, step_ticks=max(1, budget))


def run_ambient_substep(world, *, tick: int) -> None:
    state: FocusState = getattr(world, "focus_state", None) or FocusState()
    ensure_logistics(world)
    process_logistics_until(world, target_tick=tick, current_tick=state.last_ambient_step_tick)
    process_projects(world, tick=tick)


def run_focus_session(world, session: FocusSession) -> None:
    cfg: FocusConfig = getattr(world, "focus_cfg", None) or FocusConfig()
    world.focus_cfg = cfg
    if not cfg.enabled:
        return

    state: FocusState = getattr(world, "focus_state", None) or FocusState()
    world.focus_state = state
    metrics = _focus_metrics(world)

    start_tick = session.start_tick
    if state.session and state.session.session_id == session.session_id:
        start_tick = max(start_tick, state.last_tick)
    world.tick = start_tick
    state.active = True
    state.session = session
    state.last_tick = start_tick
    if state.last_ambient_step_tick <= 0:
        state.last_ambient_step_tick = start_tick

    if cfg.emit_focus_events:
        event_log = getattr(world, "event_log", None)
        if event_log is not None:
            event_log.append(
                WorldEvent(
                    event_id="",
                    day=tick_to_day(world, session.start_tick),
                    kind=EventKind.FOCUS_SESSION_START,
                    subject_kind="focus",
                    subject_id=session.session_id,
                    payload={"target": session.target.id},
                )
            )

    _mark_awake_flags(world, session.awake_agent_ids, awake=True)
    ticks_per_day = _ticks_per_day(world)
    current_day = tick_to_day(world, world.tick)
    world.day = current_day

    while world.tick < session.end_tick and (world.tick - session.start_tick) < cfg.max_focus_ticks:
        for agent_id in session.awake_agent_ids:
            _awake_agent_step(world, agent_id, world.tick, budget=cfg.awake_action_budget_per_tick)
            metrics["awake_agent_ticks"] = metrics.get("awake_agent_ticks", 0.0) + 1.0

        if world.tick - state.last_ambient_step_tick >= cfg.ambient_step_granularity_ticks:
            run_ambient_substep(world, tick=world.tick)
            state.last_ambient_step_tick = world.tick
            metrics["ambient_substeps"] = metrics.get("ambient_substeps", 0.0) + 1.0

        next_tick = world.tick + 1
        next_day = next_tick // max(1, ticks_per_day)
        if next_day > current_day:
            _run_daily_pipeline(world, day=next_day)
            current_day = next_day
            metrics["day_transitions"] = metrics.get("day_transitions", 0.0) + 1.0
            if cfg.emit_focus_events:
                event_log = getattr(world, "event_log", None)
                if event_log is not None:
                    event_log.append(
                        WorldEvent(
                            event_id="",
                            day=next_day,
                            kind=EventKind.FOCUS_DAY_TRANSITION,
                            subject_kind="focus",
                            subject_id=session.session_id,
                        )
                    )

        world.tick = next_tick
        state.last_tick = world.tick

    state.active = False
    _mark_awake_flags(world, session.awake_agent_ids, awake=False)
    if cfg.emit_focus_events:
        event_log = getattr(world, "event_log", None)
        if event_log is not None:
            event_log.append(
                WorldEvent(
                    event_id="",
                    day=tick_to_day(world, world.tick),
                    kind=EventKind.FOCUS_SESSION_END,
                    subject_kind="focus",
                    subject_id=session.session_id,
                    payload={"done": session.done_reason},
                )
            )
