from dataclasses import replace

from dosadi.agents.core import AgentState
from dosadi.runtime.escort_protocols import EscortConfig, ensure_escort_config, has_escort
from dosadi.runtime.local_interactions import (
    InteractionConfig,
    InteractionKind,
    InteractionOpportunity,
    enqueue_interaction_opportunity,
    ensure_interaction_config,
    run_interactions_for_day,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.state import WorldState
from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus, stage_project_if_ready
from dosadi.world.logistics import (
    DeliveryRequest,
    DeliveryStatus,
    LogisticsConfig,
    LogisticsLedger,
    process_logistics_until,
)
from dosadi.world.survey_map import SurveyEdge
from dosadi.world.workforce import Assignment, AssignmentKind, ensure_workforce


def _make_project(project_id: str = "proj-escort") -> ConstructionProject:
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


def _seed_world(hazard: float = 0.9, *, agent_count: int = 3) -> WorldState:
    world = WorldState(seed=24)
    world.logistics_cfg = LogisticsConfig(use_agent_couriers=True)
    world.projects = ProjectLedger()
    world.stockpiles = {"polymer": 20.0}
    world.central_depot_node_id = "loc:depot"
    world.survey_map.upsert_edge(
        SurveyEdge(a="loc:depot", b="loc:site-1", distance_m=1.0, travel_cost=1.0, hazard=hazard)
    )
    world.agents = {f"a-{idx}": AgentState(agent_id=f"a-{idx}", name=f"Agent {idx}") for idx in range(1, agent_count + 1)}
    ensure_escort_config(world)
    return world


def test_flag_off_baseline_behavior() -> None:
    world = _seed_world()
    project = _make_project("proj-baseline")
    world.projects.add_project(project)
    world.escort_cfg.enabled = False

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)

    delivery = world.logistics.deliveries["delivery:proj-baseline:v1"]
    assert not delivery.escort_agent_ids

    ledger = ensure_workforce(world)
    assert all(assignment.kind is not AssignmentKind.LOGISTICS_ESCORT for assignment in ledger.assignments.values())


def test_risk_threshold_triggers_escort() -> None:
    world = _seed_world()
    project = _make_project("proj-escort")
    world.projects.add_project(project)
    world.escort_cfg = EscortConfig(enabled=True, min_idle_reserve=1)

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)

    delivery = world.logistics.deliveries["delivery:proj-escort:v1"]
    assert delivery.escort_agent_ids
    assert has_escort(world, delivery.delivery_id)

    ledger = ensure_workforce(world)
    escort_id = delivery.escort_agent_ids[0]
    assert ledger.get(escort_id).kind is AssignmentKind.LOGISTICS_ESCORT


def test_idle_reserve_prevents_consumption() -> None:
    world = _seed_world(agent_count=2)
    project = _make_project("proj-reserve")
    world.projects.add_project(project)
    world.escort_cfg = EscortConfig(enabled=True, min_idle_reserve=2)

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)

    delivery = world.logistics.deliveries["delivery:proj-reserve:v1"]
    assert not delivery.escort_agent_ids

    ledger = ensure_workforce(world)
    assert all(assignment.kind is not AssignmentKind.LOGISTICS_ESCORT for assignment in ledger.assignments.values())


def test_interactions_shift_with_escort() -> None:
    base_world = _seed_world(hazard=0.5)
    cfg = ensure_interaction_config(base_world)
    cfg.enabled = True
    base_world.escort_cfg.enabled = True
    base_world.survey_map.edges["edge-1"] = SurveyEdge(
        a="loc:depot", b="loc:site-1", distance_m=1.0, travel_cost=1.0, hazard=0.5
    )

    delivery = DeliveryRequest(
        delivery_id="delivery:test",
        project_id="proj-x",
        origin_node_id="loc:depot",
        dest_node_id="loc:site-1",
        items={"polymer": 1.0},
        status=DeliveryStatus.IN_TRANSIT,
        created_tick=0,
        route_nodes=["loc:depot", "loc:site-1"],
        route_edge_keys=["edge-1"],
    )
    base_world.logistics = LogisticsLedger(deliveries={delivery.delivery_id: delivery}, active_ids=[delivery.delivery_id])

    ledger = ensure_workforce(base_world)
    ledger.assign(
        Assignment(agent_id="a-1", kind=AssignmentKind.LOGISTICS_COURIER, target_id=delivery.delivery_id, start_day=0)
    )

    opp = InteractionOpportunity(
        day=0,
        tick=0,
        kind="courier_edge",
        node_id="loc:site-1",
        edge_key="edge-1",
        primary_agent_id="a-1",
        subject_id=delivery.delivery_id,
        severity=0.0,
        payload={},
    )
    enqueue_interaction_opportunity(base_world, opp)

    escorted_world = restore_world(snapshot_world(base_world, scenario_id="escort-interaction"))
    ensure_interaction_config(escorted_world).enabled = True
    escorted_ledger = ensure_workforce(escorted_world)
    escorted_delivery = escorted_world.logistics.deliveries[delivery.delivery_id]
    escorted_delivery.escort_agent_ids = ["a-2"]
    escorted_ledger.assign(
        Assignment(agent_id="a-2", kind=AssignmentKind.LOGISTICS_ESCORT, target_id=delivery.delivery_id, start_day=0)
    )
    enqueue_interaction_opportunity(
        escorted_world,
        InteractionOpportunity(
            day=0,
            tick=0,
            kind="courier_edge",
            node_id="loc:site-1",
            edge_key="edge-1",
            primary_agent_id="a-1",
            subject_id=delivery.delivery_id,
            severity=0.0,
            payload={},
        ),
    )

    run_interactions_for_day(base_world, day=0)
    run_interactions_for_day(escorted_world, day=0)

    base_event = base_world.event_log.events[-1]
    escorted_event = escorted_world.event_log.events[-1]

    assert base_event.payload["interaction_kind"] == InteractionKind.SABOTAGE.value
    assert escorted_event.payload["interaction_kind"] == InteractionKind.CONFLICT.value


def test_escorts_released_on_delivery_completion() -> None:
    world = _seed_world()
    project = _make_project("proj-release")
    world.projects.add_project(project)
    world.escort_cfg.enabled = True

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)
    delivery = world.logistics.deliveries["delivery:proj-release:v1"]

    deliver_tick = delivery.deliver_tick or 0
    process_logistics_until(world, target_tick=deliver_tick, current_tick=0)

    ledger = ensure_workforce(world)
    assert all(assignment.kind is not AssignmentKind.LOGISTICS_ESCORT for assignment in ledger.assignments.values())
    assert not delivery.escort_agent_ids


def test_snapshot_roundtrip_with_escort_assignment() -> None:
    world = _seed_world()
    project = _make_project("proj-snap-escort")
    world.projects.add_project(project)
    world.escort_cfg.enabled = True

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)

    delivery = world.logistics.deliveries["delivery:proj-snap-escort:v1"]
    mid_tick = max(0, (delivery.deliver_tick or 1) - 1)

    snapshot = snapshot_world(world, scenario_id="escort-snap")
    restored = restore_world(snapshot)

    process_logistics_until(world, target_tick=delivery.deliver_tick or 0, current_tick=mid_tick)
    process_logistics_until(restored, target_tick=delivery.deliver_tick or 0, current_tick=mid_tick)

    assert world_signature(world) == world_signature(restored)
    assert world.logistics.signature() == restored.logistics.signature()
