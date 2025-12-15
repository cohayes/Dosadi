from dosadi.agents.core import AgentState
from dosadi.runtime.scouting import maybe_create_scout_missions, step_scout_missions_for_day
from dosadi.runtime.scouting_config import ScoutConfig
from dosadi.state import WorldState
from dosadi.world.scout_missions import MissionStatus
from dosadi.world.survey_map import SurveyNode


def _seed_world() -> WorldState:
    world = WorldState(seed=7)
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
    world.agents["scout-1"] = AgentState(agent_id="scout-1", name="Scout One")
    return world


def test_mission_completes_and_releases_agents() -> None:
    cfg = ScoutConfig(max_active_missions=1, party_size=1, max_days_per_mission=2, new_node_chance=1.0)
    world = _seed_world()

    maybe_create_scout_missions(world, cfg=cfg)
    mission_id = world.scout_missions.active_ids[0]

    for day in range(2):
        world.day = day
        step_scout_missions_for_day(world, day=day, cfg=cfg)

    mission = world.scout_missions.missions[mission_id]
    assert mission.status == MissionStatus.COMPLETE
    assert world.scout_missions.active_ids == []

    agent = world.agents["scout-1"]
    assert agent.is_on_mission is False
    assert agent.last_scout_day == 1


def test_mission_failure_removes_active() -> None:
    cfg = ScoutConfig(
        max_active_missions=1,
        party_size=1,
        max_days_per_mission=3,
        base_fail_chance=1.0,
        new_node_chance=1.0,
    )
    world = _seed_world()

    maybe_create_scout_missions(world, cfg=cfg)
    mission_id = world.scout_missions.active_ids[0]

    world.day = 0
    step_scout_missions_for_day(world, day=0, cfg=cfg)

    mission = world.scout_missions.missions[mission_id]
    assert mission.status == MissionStatus.FAILED
    assert mission.mission_id not in world.scout_missions.active_ids
    assert world.agents["scout-1"].is_on_mission is False
