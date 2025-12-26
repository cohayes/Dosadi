from dosadi.agents.core import AgentState, Attributes
from dosadi.runtime.corridor_risk import CorridorRiskLedger
from dosadi.runtime.suit_wear import run_suit_wear_for_day
from dosadi.state import WorldState
from dosadi.world.construction import apply_project_work
from dosadi.world.corridor_infrastructure import (
    CorridorInfraEdge,
    ensure_infra_config,
    ensure_infra_edges,
    level_for_edge,
    run_corridor_improvement_planner,
)
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, LogisticsLedger
from dosadi.world.materials import Material, ensure_inventory_registry
from dosadi.world.routing import compute_route
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key
from dosadi.world.workforce import Assignment, AssignmentKind, ensure_workforce


def _basic_world() -> WorldState:
    world = WorldState(seed=7)
    world.survey_map = SurveyMap(
        nodes={
            "A": SurveyNode(node_id="A", kind="hub"),
            "B": SurveyNode(node_id="B", kind="hub"),
        },
        edges={edge_key("A", "B"): SurveyEdge(a="A", b="B", distance_m=10.0, travel_cost=10.0)},
    )
    ensure_infra_config(world).enabled = True
    return world


def test_planner_spawns_project_and_upgrade_applies() -> None:
    world = _basic_world()
    ensure_infra_edges(world)[edge_key("A", "B")] = CorridorInfraEdge(edge_key=edge_key("A", "B"), level=0)

    world.risk_ledger = CorridorRiskLedger()

    # Seed a risk record so the planner considers the edge.
    world.risk_ledger.edges[edge_key("A", "B")] = world.risk_ledger.record(edge_key("A", "B"))
    world.risk_ledger.edges[edge_key("A", "B")].risk = 0.9

    created = run_corridor_improvement_planner(world, day=0)
    assert created
    project_id = created[0]
    project = world.projects.get(project_id)

    # Deliver materials and staff so the project can complete.
    inv = ensure_inventory_registry(world).inv(project.staging_owner_id)
    inv.add(Material.SCRAP_METAL, 10)
    inv.add(Material.FASTENERS, 10)
    inv.add(Material.FABRIC, 10)
    project.materials_delivered = {mat.name: qty for mat, qty in project.cost.materials.items()}
    project.bom_consumed = True
    agent = AgentState(agent_id="agent-1", name="agent-1", attributes=Attributes(INT=12, END=12))
    world.agents[agent.agent_id] = agent
    ensure_workforce(world).assign(
        Assignment(
            agent_id=agent.agent_id,
            kind=AssignmentKind.PROJECT_WORK,
            target_id=project_id,
            start_day=0,
        )
    )

    apply_project_work(world, elapsed_hours=24.0, tick=0)

    assert project.status.name == "COMPLETE"
    assert level_for_edge(world, edge_key("A", "B")) == 1
    assert any(evt.get("type") == "CORRIDOR_UPGRADE_DONE" for evt in world.runtime_events)


def test_travel_time_and_wear_benefit_from_infrastructure() -> None:
    baseline = _basic_world()
    improved = _basic_world()
    ensure_infra_edges(improved)[edge_key("A", "B")] = CorridorInfraEdge(edge_key=edge_key("A", "B"), level=2)

    route0 = compute_route(baseline, from_node="A", to_node="B", perspective_agent_id=None)
    assert route0 is not None

    improved.day = 1  # Avoid route cache reuse
    route1 = compute_route(improved, from_node="A", to_node="B", perspective_agent_id=None)
    assert route1 is not None
    assert route1.total_cost < route0.total_cost

    # Wear check: courier on improved corridor should lose less integrity.
    for world, expected_order in ((baseline, "baseline"), (improved, "improved")):
        ensure_infra_config(world).enabled = True
        world.suit_cfg.enabled = True
        delivery = DeliveryRequest(
            delivery_id=f"d-{expected_order}",
            project_id="proj-1",
            origin_node_id="A",
            dest_node_id="B",
            items={},
            status=DeliveryStatus.IN_TRANSIT,
            created_tick=0,
            route_edge_keys=[edge_key("A", "B")],
        )
        ledger = LogisticsLedger(deliveries={delivery.delivery_id: delivery}, active_ids=[delivery.delivery_id])
        world.logistics = ledger
        agent = AgentState(agent_id=f"agent-{expected_order}", name="agent", attributes=Attributes(INT=10, END=10))
        world.agents[agent.agent_id] = agent
        ensure_workforce(world).assign(
            Assignment(
                agent_id=agent.agent_id,
                kind=AssignmentKind.LOGISTICS_COURIER,
                target_id=delivery.delivery_id,
                start_day=0,
            )
        )
        run_suit_wear_for_day(world, day=world.day)

    base_agent = baseline.agents["agent-baseline"]
    improved_agent = improved.agents["agent-improved"]
    assert improved_agent.suit.integrity > base_agent.suit.integrity
