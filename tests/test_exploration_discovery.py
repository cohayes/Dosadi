from dosadi.agents.core import AgentState
from dosadi.runtime.scouting import maybe_create_scout_missions, step_scout_missions_for_day
from dosadi.runtime.scouting_config import ScoutConfig
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WorldState
from dosadi.world.discovery import DiscoveryConfig, expand_frontier
from dosadi.world.routing import compute_route
from dosadi.world.site_scoring import SiteScoreConfig, score_site
from dosadi.world.survey_map import SurveyNode


def _seed_world(seed: int = 11, *, enable_discovery: bool = True) -> WorldState:
    world = WorldState(seed=seed)
    world.survey_map.upsert_node(
        SurveyNode(
            node_id="loc:well-core",
            kind="well",
            tags=("origin",),
            hazard=0.0,
            water=1.0,
            confidence=1.0,
            last_seen_tick=0,
        )
    )
    world.agents["scout"] = AgentState(agent_id="scout", name="Scout")
    world.discovery_cfg = DiscoveryConfig(enabled=enable_discovery)
    return world


def test_deterministic_frontier_expansion() -> None:
    world_a = _seed_world(seed=101)
    world_b = _seed_world(seed=101)

    nodes_a = expand_frontier(
        world_a,
        from_node="loc:well-core",
        budget_nodes=3,
        budget_edges=3,
        day=0,
        mission_id="mission-1",
    )
    nodes_b = expand_frontier(
        world_b,
        from_node="loc:well-core",
        budget_nodes=3,
        budget_edges=3,
        day=0,
        mission_id="mission-1",
    )

    assert nodes_a == nodes_b
    assert world_a.survey_map.signature() == world_b.survey_map.signature()


def test_discovery_respects_budgets() -> None:
    world = _seed_world()
    world.discovery_cfg = DiscoveryConfig(
        enabled=True,
        max_new_nodes_per_day=1,
        max_new_edges_per_day=1,
        max_frontier_expansions_per_mission=5,
        resource_tag_probs={},
    )

    nodes = expand_frontier(
        world,
        from_node="loc:well-core",
        budget_nodes=3,
        budget_edges=3,
        day=1,
        mission_id="mission-budget",
    )

    assert len(nodes) == 1
    assert len(world.survey_map.edges) == 1


def test_snapshot_roundtrip_preserves_discoveries() -> None:
    world = _seed_world(seed=77)
    initial_nodes = expand_frontier(
        world,
        from_node="loc:well-core",
        budget_nodes=2,
        budget_edges=2,
        day=0,
        mission_id="mission-snap",
    )
    snapshot = snapshot_world(world, scenario_id="discovery-test")
    restored = restore_world(snapshot)

    expand_frontier(
        restored,
        from_node="loc:well-core",
        budget_nodes=2,
        budget_edges=2,
        day=1,
        mission_id="mission-snap",
    )
    expand_frontier(
        world,
        from_node="loc:well-core",
        budget_nodes=2,
        budget_edges=2,
        day=1,
        mission_id="mission-snap",
    )

    assert initial_nodes
    assert restored.survey_map.signature() == world.survey_map.signature()


def test_routing_traverses_new_edges() -> None:
    world = _seed_world(seed=88)
    discovered = expand_frontier(
        world,
        from_node="loc:well-core",
        budget_nodes=2,
        budget_edges=2,
        day=0,
        mission_id="mission-route",
    )
    target = discovered[0]
    route = compute_route(world, from_node="loc:well-core", to_node=target)
    assert route is not None
    assert route.nodes[0] == "loc:well-core"
    assert route.nodes[-1] == target


def test_resource_tag_scores_sites() -> None:
    world = _seed_world(seed=33)
    scrap_node = SurveyNode(
        node_id="node:scrap",
        kind="frontier",
        tags=(),
        resource_tags=("scrap_field",),
        hazard=0.0,
        water=0.0,
        confidence=0.8,
        last_seen_tick=0,
    )
    plain_node = SurveyNode(
        node_id="node:plain",
        kind="frontier",
        tags=(),
        hazard=0.0,
        water=0.0,
        confidence=0.8,
        last_seen_tick=0,
    )
    world.survey_map.upsert_node(scrap_node)
    world.survey_map.upsert_node(plain_node)

    cfg = SiteScoreConfig()
    scrap_score = score_site(scrap_node, origin_node_id="loc:well-core", survey=world.survey_map, cfg=cfg)
    plain_score = score_site(plain_node, origin_node_id="loc:well-core", survey=world.survey_map, cfg=cfg)

    assert scrap_score > plain_score


def test_flag_off_static_map() -> None:
    world = _seed_world(enable_discovery=False)
    cfg = ScoutConfig(max_active_missions=1, party_size=1, max_days_per_mission=2)
    maybe_create_scout_missions(world, cfg=cfg)
    mission_id = world.scout_missions.active_ids[0]
    for day in range(cfg.max_days_per_mission):
        world.day = day
        step_scout_missions_for_day(world, day=day, cfg=cfg)

    mission = world.scout_missions.missions[mission_id]
    assert mission.discovered_nodes == []
    assert len(world.survey_map.nodes) == 1

