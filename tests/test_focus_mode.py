from dataclasses import replace

from dosadi.agents.core import AgentState
from dosadi.runtime.focus_mode import (
    FocusConfig,
    FocusSession,
    FocusTarget,
    FocusTargetKind,
    run_ambient_substep,
    run_focus_session,
    select_awake_agents,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.runtime.timewarp import TimewarpConfig, step_day
from dosadi.state import WorldState
from dosadi.world.construction import (
    ConstructionProject,
    ProjectCost,
    ProjectLedger,
    ProjectStatus,
    stage_project_if_ready,
)
from dosadi.world.logistics import DeliveryStatus, LogisticsConfig, process_logistics_until
from dosadi.world.survey_map import SurveyEdge
from dosadi.world.workforce import Assignment, AssignmentKind, ensure_workforce


def _make_project(project_id: str = "proj-focus") -> ConstructionProject:
    cost = ProjectCost(materials={"polymer": 10.0}, labor_hours=1.0)
    return ConstructionProject(
        project_id=project_id,
        site_node_id="loc:site-1",
        kind="outpost",
        status=ProjectStatus.APPROVED,
        created_tick=0,
        last_tick=0,
        cost=cost,
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
    )


def _seed_focus_world() -> WorldState:
    world = WorldState(seed=123)
    world.focus_cfg = FocusConfig(enabled=True, ambient_step_granularity_ticks=25)
    world.projects = ProjectLedger()
    world.stockpiles = {"polymer": 20.0}
    world.central_depot_node_id = "loc:depot"
    world.logistics_cfg = LogisticsConfig(use_agent_couriers=True)
    world.survey_map.upsert_edge(
        SurveyEdge(a="loc:depot", b="loc:site-1", distance_m=1.0, travel_cost=1.0)
    )
    world.agents["agent-1"] = AgentState(agent_id="agent-1", name="Agent One")
    return world


def _prepare_delivery(world: WorldState, project_id: str = "proj-focus") -> str:
    project = _make_project(project_id)
    world.projects.add_project(project)
    stage_project_if_ready(world, project, getattr(world, "tick", 0))
    process_logistics_until(world, target_tick=world.tick, current_tick=world.tick)
    logistics = world.logistics
    delivery = logistics.deliveries[f"delivery:{project_id}:v1"]
    ledger = ensure_workforce(world)
    existing = ledger.get("agent-1")
    if existing.kind is AssignmentKind.IDLE:
        ledger.assign(
            Assignment(
                agent_id="agent-1",
                kind=AssignmentKind.LOGISTICS_COURIER,
                target_id=delivery.delivery_id,
                start_day=getattr(world, "day", 0),
            )
        )
    delivery.assigned_carrier_id = delivery.assigned_carrier_id or "agent-1"
    delivery.status = DeliveryStatus.IN_TRANSIT
    return delivery.delivery_id


def test_focus_session_determinism() -> None:
    world_a = _seed_focus_world()
    delivery_id = _prepare_delivery(world_a, "proj-determinism")

    session = FocusSession(
        session_id="sess-1",
        start_tick=world_a.tick,
        end_tick=world_a.tick + 200,
        target=FocusTarget(kind=FocusTargetKind.DELIVERY, id=delivery_id),
        awake_agent_ids=select_awake_agents(
            world_a, FocusTarget(FocusTargetKind.DELIVERY, delivery_id), day=world_a.day, max_n=3
        ),
    )

    world_b = restore_world(snapshot_world(world_a, scenario_id="focus"))

    run_focus_session(world_a, session)
    run_focus_session(world_b, session)

    assert world_signature(world_a) == world_signature(world_b)
    assert world_a.logistics.signature() == world_b.logistics.signature()


def test_awake_cohort_selection_deterministic() -> None:
    world = _seed_focus_world()
    delivery_id = _prepare_delivery(world, "proj-cohort")
    target = FocusTarget(FocusTargetKind.DELIVERY, delivery_id)

    cohort_first = select_awake_agents(world, target, day=0, max_n=5)
    cohort_second = select_awake_agents(world, target, day=0, max_n=5)

    assert cohort_first == cohort_second == sorted(cohort_first)


def test_ambient_substep_processes_deliveries_without_full_scan() -> None:
    world = _seed_focus_world()
    world.logistics_cfg = LogisticsConfig(use_agent_couriers=False)
    delivery_id = _prepare_delivery(world, "proj-ambient")
    world.logistics.deliveries[delivery_id].deliver_tick = world.tick
    container = {}

    class AgentContainer(dict):
        iterated = False

        def __iter__(self):
            AgentContainer.iterated = True
            return super().__iter__()

    world.agents = AgentContainer(container)
    run_ambient_substep(world, tick=world.tick)
    assert not AgentContainer.iterated
    assert world.logistics.deliveries[delivery_id].status in {
        DeliveryStatus.IN_TRANSIT,
        DeliveryStatus.DELIVERED,
    }


def test_daily_pipeline_runs_on_day_transition() -> None:
    world_focus = _seed_focus_world()
    world_focus.ticks_per_day = 50
    world_focus.focus_cfg.ambient_step_granularity_ticks = 10
    delivery_id = _prepare_delivery(world_focus, "proj-day")
    session = FocusSession(
        session_id="sess-day",
        start_tick=0,
        end_tick=125,
        target=FocusTarget(FocusTargetKind.DELIVERY, delivery_id),
        awake_agent_ids=[],
    )

    world_macro = restore_world(snapshot_world(world_focus, scenario_id="baseline"))
    step_day(world_macro, days=2, cfg=TimewarpConfig(physiology_enabled=False))

    run_focus_session(world_focus, session)

    assert world_focus.day == world_macro.day == 2
    assert world_focus.metrics.get("focus", {}).get("day_transitions") == 2


def test_snapshot_mid_focus_roundtrip() -> None:
    world = _seed_focus_world()
    delivery_id = _prepare_delivery(world, "proj-snapshot")
    session_a = FocusSession(
        session_id="sess-snap",
        start_tick=0,
        end_tick=80,
        target=FocusTarget(FocusTargetKind.DELIVERY, delivery_id),
        awake_agent_ids=["agent-1"],
    )
    session_b = replace(session_a, start_tick=40, end_tick=160)

    run_focus_session(world, session_a)
    snapshot = snapshot_world(world, scenario_id="focus-mid")
    restored = restore_world(snapshot)

    world_full = _seed_focus_world()
    _prepare_delivery(world_full, "proj-snapshot")
    full_session = replace(session_a, end_tick=160)
    run_focus_session(world_full, full_session)

    run_focus_session(restored, session_b)

    assert world_signature(world_full) == world_signature(restored)
    assert world_full.logistics.signature() == restored.logistics.signature()
