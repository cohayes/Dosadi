from dosadi.agents.core import AgentState
from dosadi.runtime.timewarp import TimewarpConfig, step_day
from dosadi.runtime.scouting_config import ScoutConfig
from dosadi.state import WorldState
from dosadi.world.expansion_planner import ExpansionPlannerConfig, ExpansionPlannerState
from dosadi.world.survey_map import SurveyNode


def _seed_world() -> WorldState:
    world = WorldState(seed=55)
    world.survey_map.upsert_node(
        SurveyNode(
            node_id="loc:well-core",
            kind="well",
            ward_id=None,
            tags=(),
            hazard=0.0,
            water=1.0,
            confidence=1.0,
            last_seen_tick=0,
        )
    )
    for idx in range(5):
        agent_id = f"agent-{idx}"
        world.agents[agent_id] = AgentState(agent_id=agent_id, name=f"Agent {idx}")
    world.stockpiles = {"polymer": 100.0, "metal": 100.0}
    world.expansion_planner_cfg = ExpansionPlannerConfig(
        planning_interval_days=1,
        labor_pool_size=1,
        min_idle_agents=0,
        max_new_projects_per_cycle=1,
        max_active_projects=3,
        min_site_confidence=0.5,
    )
    world.expansion_planner_state = ExpansionPlannerState(next_plan_day=0)
    world.scout_cfg = ScoutConfig(max_active_missions=1, party_size=1, max_days_per_mission=3, new_node_chance=1.0)
    return world


def test_macrostep_creates_projects_from_scouting() -> None:
    world = _seed_world()
    step_day(world, days=5, cfg=TimewarpConfig(physiology_enabled=False))

    assert len(world.survey_map.nodes) > 1
    assert world.projects.projects
    project = next(iter(world.projects.projects.values()))
    assert project.site_node_id in world.survey_map.nodes
