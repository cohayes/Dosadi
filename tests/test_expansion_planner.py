from dosadi.agents.core import AgentState
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.runtime.timewarp import TimewarpConfig, step_day
from dosadi.state import WorldState
from dosadi.world.construction import ProjectLedger, ProjectStatus
from dosadi.world.expansion_planner import (
    ExpansionPlannerConfig,
    ExpansionPlannerState,
    maybe_plan,
)
from dosadi.world.survey_map import SurveyNode


def _seed_survey(world: WorldState, count: int = 3) -> None:
    for idx in range(count):
        node_id = f"loc:survey-{idx+1}"
        world.survey_map.upsert_node(
            SurveyNode(
                node_id=node_id,
                kind="outpost_site",
                ward_id="ward:core",
                hazard=0.05 * idx,
                water=10.0 - idx,
                confidence=0.9,
                last_seen_tick=world.tick,
            ),
            confidence_delta=0.2,
        )


def _basic_world(seed: int = 1) -> WorldState:
    world = WorldState(seed=seed)
    world.projects = ProjectLedger()
    world.stockpiles = {"polymer": 200.0, "metal": 200.0}
    for idx in range(20):
        agent_id = f"agent:{idx}"
        world.agents[agent_id] = AgentState(agent_id=agent_id, name=agent_id)
    return world


def test_deterministic_planning_creates_same_project() -> None:
    world_a = _basic_world(seed=2)
    world_b = _basic_world(seed=2)
    _seed_survey(world_a)
    _seed_survey(world_b)

    cfg = ExpansionPlannerConfig(max_new_projects_per_cycle=1)
    state_a = ExpansionPlannerState(next_plan_day=0)
    state_b = ExpansionPlannerState(next_plan_day=0)

    created_a = maybe_plan(world_a, cfg=cfg, state=state_a)
    created_b = maybe_plan(world_b, cfg=cfg, state=state_b)

    assert created_a == created_b
    assert world_a.projects.signature() == world_b.projects.signature()


def test_candidate_selection_is_bounded() -> None:
    world = _basic_world(seed=3)
    _seed_survey(world, count=8)
    cfg = ExpansionPlannerConfig(max_candidates=2, max_new_projects_per_cycle=1)
    state = ExpansionPlannerState(next_plan_day=0)

    created = maybe_plan(world, cfg=cfg, state=state)
    assert created
    chosen_site = world.projects.get(created[0]).site_node_id
    assert chosen_site in {"loc:survey-1", "loc:survey-2"}


def test_insufficient_materials_prevents_project() -> None:
    world = _basic_world(seed=4)
    _seed_survey(world, count=1)
    world.stockpiles = {"polymer": 1.0, "metal": 1.0}
    cfg = ExpansionPlannerConfig()
    state = ExpansionPlannerState(next_plan_day=0)

    created = maybe_plan(world, cfg=cfg, state=state)
    assert created == []
    assert not world.projects.projects


def test_snapshot_roundtrip_preserves_planner_state() -> None:
    world = _basic_world(seed=5)
    _seed_survey(world, count=3)
    cfg = ExpansionPlannerConfig()
    state = ExpansionPlannerState(next_plan_day=0)

    maybe_plan(world, cfg=cfg, state=state)
    snapshot = snapshot_world(world, scenario_id="planner-test")
    restored = restore_world(snapshot)

    restored_state = restored.expansion_planner_state
    restored_cfg = restored.expansion_planner_cfg
    restored.day = restored_state.next_plan_day
    created_after = maybe_plan(restored, cfg=restored_cfg, state=restored_state)

    world.day = state.next_plan_day
    created_world = maybe_plan(world, cfg=cfg, state=state)

    assert created_after == created_world
    assert world_signature(world) == world_signature(restored)


def test_timewarp_integration_spawns_project() -> None:
    world = _basic_world(seed=6)
    _seed_survey(world, count=2)
    world.agents = {f"agent:{i}": AgentState(agent_id=f"agent:{i}", name=f"agent:{i}") for i in range(30)}
    cfg = TimewarpConfig(physiology_enabled=False)

    step_day(world, days=60, cfg=cfg)

    assert any(
        project.status in {ProjectStatus.APPROVED, ProjectStatus.STAGED, ProjectStatus.BUILDING}
        for project in world.projects.projects.values()
    )
