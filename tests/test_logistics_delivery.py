from dataclasses import replace

from dosadi.agents.core import AgentState
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.runtime.timewarp import TimewarpConfig, step_day
from dosadi.state import WorldState
from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus, stage_project_if_ready
from dosadi.world.logistics import DeliveryStatus, LogisticsConfig, process_logistics_until
from dosadi.world.survey_map import SurveyEdge
from dosadi.world.workforce import AssignmentKind, ensure_workforce


def _make_project(project_id: str = "proj-1") -> ConstructionProject:
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


def _seed_world() -> WorldState:
    world = WorldState(seed=42)
    world.projects = ProjectLedger()
    world.stockpiles = {"polymer": 20.0}
    world.central_depot_node_id = "loc:depot"
    world.survey_map.upsert_edge(
        SurveyEdge(a="loc:depot", b="loc:site-1", distance_m=1.0, travel_cost=1.0)
    )
    return world


def test_deterministic_delivery_schedule() -> None:
    world_a = _seed_world()
    world_b = replace(world_a)
    world_b.projects = ProjectLedger()
    world_b.stockpiles = dict(world_a.stockpiles)

    project_a = _make_project("proj-a")
    project_b = _make_project("proj-a")
    world_a.projects.add_project(project_a)
    world_b.projects.add_project(project_b)

    stage_project_if_ready(world_a, project_a, 0)
    stage_project_if_ready(world_b, project_b, 0)
    process_logistics_until(world_a, target_tick=0, current_tick=0)
    process_logistics_until(world_b, target_tick=0, current_tick=0)

    delivery_a = world_a.logistics.deliveries["delivery:proj-a:v1"]
    delivery_b = world_b.logistics.deliveries["delivery:proj-a:v1"]
    assert delivery_a.deliver_tick == delivery_b.deliver_tick
    assert delivery_a.status == delivery_b.status

    process_logistics_until(world_a, target_tick=delivery_a.deliver_tick or 0, current_tick=0)
    process_logistics_until(world_b, target_tick=delivery_b.deliver_tick or 0, current_tick=0)

    assert world_a.logistics.deliveries[delivery_a.delivery_id].status == DeliveryStatus.DELIVERED
    assert world_b.logistics.deliveries[delivery_b.delivery_id].status == DeliveryStatus.DELIVERED


def test_conservation_and_failure() -> None:
    world = _seed_world()
    world.stockpiles = {"polymer": 5.0}
    project = _make_project("proj-fail")
    world.projects.add_project(project)

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)
    delivery = world.logistics.deliveries["delivery:proj-fail:v1"]
    assert delivery.status == DeliveryStatus.FAILED
    assert world.stockpiles["polymer"] == 5.0
    assert project.materials_delivered.get("polymer", 0.0) == 0.0


def test_project_stages_on_delivery() -> None:
    world = _seed_world()
    project = _make_project("proj-stage")
    world.projects.add_project(project)

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)
    deliver_tick = world.logistics.deliveries["delivery:proj-stage:v1"].deliver_tick or 0
    process_logistics_until(world, target_tick=deliver_tick, current_tick=0)

    assert stage_project_if_ready(world, project, deliver_tick)
    assert project.status == ProjectStatus.STAGED
    assert project.materials_delivered.get("polymer") == 10.0


def test_macrostep_processes_deliveries() -> None:
    world = _seed_world()
    project = _make_project("proj-macro")
    world.projects.add_project(project)

    stage_project_if_ready(world, project, 0)
    step_day(world, days=1, cfg=TimewarpConfig(physiology_enabled=False))

    assert project.status == ProjectStatus.STAGED
    assert project.materials_delivered.get("polymer") == 10.0


def test_snapshot_roundtrip_delivery() -> None:
    world = _seed_world()
    project = _make_project("proj-snap")
    world.projects.add_project(project)

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)
    deliver_tick = world.logistics.deliveries["delivery:proj-snap:v1"].deliver_tick or 0
    mid_tick = max(0, deliver_tick - 1)
    process_logistics_until(world, target_tick=mid_tick, current_tick=0)

    snapshot = snapshot_world(world, scenario_id="logistics-test")
    restored = restore_world(snapshot)

    process_logistics_until(restored, target_tick=deliver_tick, current_tick=mid_tick)
    assert restored.logistics.deliveries["delivery:proj-snap:v1"].status == DeliveryStatus.DELIVERED
    assert restored.projects.get(project.project_id).materials_delivered.get("polymer") == 10.0


def test_agent_courier_assignment_deterministic() -> None:
    world = _seed_world()
    world.logistics_cfg = LogisticsConfig(use_agent_couriers=True)
    world.agents = {
        f"a-{idx}": AgentState(agent_id=f"a-{idx}", name=f"Agent {idx}") for idx in range(1, 4)
    }
    project = _make_project("proj-agent")
    world.projects.add_project(project)

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)

    delivery = world.logistics.deliveries["delivery:proj-agent:v1"]
    assert delivery.assigned_carrier_id == "a-1"

    ledger = ensure_workforce(world)
    assignment = ledger.get("a-1")
    assert assignment.kind is AssignmentKind.LOGISTICS_COURIER
    assert assignment.target_id == delivery.delivery_id


def test_agent_courier_released_after_delivery() -> None:
    world = _seed_world()
    world.logistics_cfg = LogisticsConfig(use_agent_couriers=True)
    world.agents["a-1"] = AgentState(agent_id="a-1", name="Agent One")
    project = _make_project("proj-agent-release")
    world.projects.add_project(project)

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)
    delivery = world.logistics.deliveries["delivery:proj-agent-release:v1"]
    deliver_tick = delivery.deliver_tick or 0

    ledger = ensure_workforce(world)
    assert ledger.get("a-1").kind is AssignmentKind.LOGISTICS_COURIER

    process_logistics_until(world, target_tick=deliver_tick, current_tick=0)

    assert delivery.status == DeliveryStatus.DELIVERED
    assert ledger.is_idle("a-1")


def test_fallback_to_abstract_carrier_when_no_agents() -> None:
    world = _seed_world()
    world.logistics_cfg = LogisticsConfig(use_agent_couriers=True)
    world.agents.clear()
    project = _make_project("proj-fallback")
    world.projects.add_project(project)

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)
    delivery = world.logistics.deliveries["delivery:proj-fallback:v1"]
    assert delivery.assigned_carrier_id is not None
    assert delivery.assigned_carrier_id.startswith("carrier:")
    assert world.carriers_available == 0

    process_logistics_until(world, target_tick=delivery.deliver_tick or 0, current_tick=0)
    assert world.carriers_available == 1


def test_snapshot_roundtrip_with_agent_courier() -> None:
    world = _seed_world()
    world.logistics_cfg = LogisticsConfig(use_agent_couriers=True)
    world.agents["a-1"] = AgentState(agent_id="a-1", name="Agent One")
    project = _make_project("proj-snap-agent")
    world.projects.add_project(project)

    stage_project_if_ready(world, project, 0)
    process_logistics_until(world, target_tick=0, current_tick=0)
    deliver_tick = world.logistics.deliveries["delivery:proj-snap-agent:v1"].deliver_tick or 0

    snapshot = snapshot_world(world, scenario_id="logistics-agent")
    restored = restore_world(snapshot)

    process_logistics_until(world, target_tick=deliver_tick, current_tick=0)
    process_logistics_until(restored, target_tick=deliver_tick, current_tick=0)

    assert world_signature(world) == world_signature(restored)
    assert world.logistics.signature() == restored.logistics.signature()
