from dosadi.agents.core import AgentState
from dosadi.runtime.scouting import maybe_create_scout_missions, step_scout_missions_for_day
from dosadi.runtime.scouting_config import ScoutConfig
from dosadi.state import WorldState
from dosadi.world.discovery import DiscoveryConfig
from dosadi.world.survey_map import SurveyEdge, SurveyNode


def _seed_world(seed: int = 123) -> WorldState:
    world = WorldState(seed=seed)
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
    world.agents["a-1"] = AgentState(agent_id="a-1", name="Agent One")
    world.agents["a-2"] = AgentState(agent_id="a-2", name="Agent Two")
    return world


def _run_missions(world: WorldState, cfg: ScoutConfig) -> str:
    world.discovery_cfg = DiscoveryConfig(enabled=True)
    maybe_create_scout_missions(world, cfg=cfg)
    mission_id = world.scout_missions.active_ids[0]
    for day in range(cfg.max_days_per_mission):
        world.day = day
        step_scout_missions_for_day(world, day=day, cfg=cfg)
    return mission_id


def test_deterministic_map_growth() -> None:
    cfg = ScoutConfig(
        max_active_missions=1,
        party_size=1,
        max_days_per_mission=3,
    )

    world_a = _seed_world(seed=123)
    mission_id_a = _run_missions(world_a, cfg)
    mission_a = world_a.scout_missions.missions[mission_id_a]

    current = "loc:well-core"
    for discovery in mission_a.discoveries:
        assert discovery["kind"] == "DISCOVERY_NODE"
        node_id = discovery["node_id"]
        assert SurveyEdge(a=current, b=node_id, distance_m=0.0, travel_cost=0.0).key in world_a.survey_map.edges
        current = node_id

    assert len(world_a.survey_map.nodes) >= 2
    assert len(world_a.survey_map.edges) >= 1

    world_b = _seed_world(seed=123)
    _run_missions(world_b, cfg)

    assert world_a.survey_map.signature() == world_b.survey_map.signature()
