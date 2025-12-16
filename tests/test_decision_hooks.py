import pytest

from dosadi.agent.beliefs import Belief, BeliefStore
from dosadi.agents.core import AgentState
from dosadi.runtime.staffing import StaffingConfig, StaffingState, run_staffing_policy
from dosadi.state import WorldState
from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectStatus
from dosadi.world.expansion_planner import ExpansionPlannerConfig, ExpansionPlannerState, maybe_plan
from dosadi.world.logistics import estimate_travel_ticks
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key


def _planner_agent(agent_id: str = "agent-1") -> AgentState:
    agent = AgentState(agent_id=agent_id, name=agent_id)
    agent.beliefs = BeliefStore(max_items=16)
    return agent


def _basic_world() -> WorldState:
    world = WorldState()
    world.agents = {f"agent-{i}": _planner_agent(f"agent-{i}") for i in range(12)}
    world.stockpiles = {"polymer": 50.0, "metal": 50.0}
    world.survey_map = SurveyMap()
    world.day = 1
    return world


def test_planner_prefers_lower_risk_site():
    world = _basic_world()
    origin = SurveyNode(node_id="loc:well-core", kind="well", confidence=1.0)
    site_a = SurveyNode(node_id="loc:a", kind="outpost", confidence=1.0, water=1.0)
    site_b = SurveyNode(node_id="loc:b", kind="outpost", confidence=1.0, water=1.0)
    world.survey_map.nodes = {
        origin.node_id: origin,
        site_a.node_id: site_a,
        site_b.node_id: site_b,
    }
    world.survey_map.edges = {
        edge_key(origin.node_id, site_a.node_id): SurveyEdge(
            a=origin.node_id,
            b=site_a.node_id,
            distance_m=10.0,
            travel_cost=10.0,
            confidence=1.0,
        ),
        edge_key(origin.node_id, site_b.node_id): SurveyEdge(
            a=origin.node_id,
            b=site_b.node_id,
            distance_m=10.0,
            travel_cost=10.0,
            confidence=1.0,
        ),
    }
    world.facilities = {origin.node_id: object()}

    agent = world.agents[min(world.agents.keys())]
    agent.beliefs.upsert(Belief(key=f"route-risk:{edge_key(origin.node_id, site_a.node_id)}", value=0.9, weight=0.8, last_day=world.day))

    cfg = ExpansionPlannerConfig(
        min_site_confidence=0.5, project_kinds=("outpost",), labor_pool_size=2, min_idle_agents=2
    )
    state = ExpansionPlannerState(next_plan_day=0)
    created = maybe_plan(world, cfg=cfg, state=state)

    assert created, "planner should create at least one project"
    project_id = created[0]
    project = world.projects.projects[project_id]
    assert project.site_node_id == site_b.node_id


def test_route_selection_prefers_lower_risk_path():
    world = _basic_world()
    origin = "loc:origin"
    mid_high = "loc:high"
    mid_low = "loc:low"
    dest = "loc:dest"

    for node_id in (origin, mid_high, mid_low, dest):
        world.survey_map.nodes[node_id] = SurveyNode(node_id=node_id, kind="path", confidence=1.0)

    world.survey_map.edges = {
        edge_key(origin, mid_high): SurveyEdge(a=origin, b=mid_high, distance_m=5.0, travel_cost=5.0, confidence=1.0),
        edge_key(mid_high, dest): SurveyEdge(a=mid_high, b=dest, distance_m=5.0, travel_cost=5.0, confidence=1.0),
        edge_key(origin, mid_low): SurveyEdge(a=origin, b=mid_low, distance_m=5.0, travel_cost=5.0, confidence=1.0),
        edge_key(mid_low, dest): SurveyEdge(a=mid_low, b=dest, distance_m=5.0, travel_cost=5.0, confidence=1.0),
    }

    agent = world.agents[min(world.agents.keys())]
    agent.beliefs.upsert(
        Belief(key=f"route-risk:{edge_key(origin, mid_high)}", value=0.9, weight=0.9, last_day=world.day)
    )

    risky_ticks = estimate_travel_ticks(origin, dest, world.survey_map, world)

    neutral_world = _basic_world()
    neutral_world.survey_map = world.survey_map
    neutral_ticks = estimate_travel_ticks(origin, dest, neutral_world.survey_map, neutral_world)

    assert risky_ticks >= neutral_ticks
    assert risky_ticks > 0


def test_staffing_reserve_increases_with_risk():
    world = _basic_world()
    project = ConstructionProject(
        project_id="proj-1",
        site_node_id="loc:a",
        kind="outpost",
        status=ProjectStatus.BUILDING,
        created_tick=0,
        last_tick=0,
        cost=ProjectCost(materials={}, labor_hours=10.0),
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
    )
    world.projects.add_project(project)

    cfg = StaffingConfig(min_idle_agents=1, project_workers_default=3, extra_idle_reserve=4)
    state_low = StaffingState()
    run_staffing_policy(world, day=1, cfg=cfg, state=state_low)
    low_risk_assignments = [a for a in world.workforce.assignments.values() if a.kind is not None and a.kind.name != "IDLE"]

    # Apply high risk beliefs and rerun on a fresh world
    risky_world = _basic_world()
    risky_project = ConstructionProject(
        project_id="proj-1",
        site_node_id="loc:a",
        kind="outpost",
        status=ProjectStatus.BUILDING,
        created_tick=0,
        last_tick=0,
        cost=ProjectCost(materials={}, labor_hours=10.0),
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
    )
    risky_world.projects.add_project(risky_project)
    risky_agent = risky_world.agents[min(risky_world.agents.keys())]
    risky_agent.beliefs.upsert(Belief(key="route-risk:edge", value=0.95, weight=0.9, last_day=1))
    state_high = StaffingState()
    run_staffing_policy(risky_world, day=1, cfg=cfg, state=state_high)
    high_risk_assignments = [
        a for a in risky_world.workforce.assignments.values() if a.kind is not None and a.kind.name != "IDLE"
    ]

    assert len(high_risk_assignments) <= len(low_risk_assignments)
    assert len(high_risk_assignments) < len(world.agents)
