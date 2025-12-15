from __future__ import annotations

from dosadi.agents.core import Goal, GoalStatus, GoalType, _handle_scout_interior
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.world.scenarios.founding_wakeup import generate_founding_wakeup_mvp
from dosadi.world.site_scoring import SiteScoreConfig, score_site
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode


def test_survey_map_deterministic_merge() -> None:
    obs_sequence = [
        {
            "discovered_nodes": [
                {"node_id": "a", "kind": "ridge", "hazard": 0.2, "tags": ("ridge",)},
                {"node_id": "b", "kind": "pit", "hazard": 0.1, "water": 0.3},
            ],
            "discovered_edges": [
                {"a": "a", "b": "b", "distance_m": 10.0, "travel_cost": 11.0, "hazard": 0.15},
            ],
        },
        {
            "discovered_nodes": [
                {"node_id": "a", "kind": "ridge", "hazard": 0.25, "confidence_delta": 0.2},
            ],
            "discovered_edges": [
                {"a": "a", "b": "b", "distance_m": 10.0, "travel_cost": 10.5, "hazard": 0.2},
            ],
        },
    ]

    map_one = SurveyMap()
    map_two = SurveyMap()

    for tick, obs in enumerate(obs_sequence, start=1):
        map_one.merge_observation(obs, tick=tick)
        map_two.merge_observation(obs, tick=tick)

    assert map_one.signature() == map_two.signature()


def test_survey_map_monotonic_growth() -> None:
    survey = SurveyMap()
    first_obs = {
        "discovered_nodes": [
            {"node_id": "n1", "kind": "ridge", "hazard": 0.1, "confidence_delta": 0.1},
        ],
        "discovered_edges": [
            {"a": "n1", "b": "n2", "distance_m": 5.0, "travel_cost": 5.0, "hazard": 0.05, "confidence_delta": 0.1},
        ],
    }
    second_obs = {
        "discovered_nodes": [
            {"node_id": "n1", "kind": "ridge", "hazard": 0.05, "confidence_delta": 0.3},
        ],
        "discovered_edges": [
            {"a": "n1", "b": "n2", "distance_m": 4.0, "travel_cost": 4.5, "hazard": 0.02, "confidence_delta": 0.2},
        ],
    }

    survey.merge_observation(first_obs, tick=1)
    node_before = survey.nodes["n1"]
    edge_key = SurveyEdge(a="n1", b="n2", distance_m=0, travel_cost=0).key
    edge_before = survey.edges[edge_key]

    survey.merge_observation(second_obs, tick=5)
    node_after = survey.nodes["n1"]
    edge_after = survey.edges[edge_key]

    assert node_after.hazard >= node_before.hazard
    assert node_after.confidence >= node_before.confidence
    assert edge_after.hazard >= edge_before.hazard
    assert edge_after.confidence >= edge_before.confidence
    assert edge_after.last_seen_tick >= edge_before.last_seen_tick


def test_survey_map_snapshot_roundtrip() -> None:
    world = generate_founding_wakeup_mvp(num_agents=2, seed=3)
    world.survey_map.merge_observation(
        {
            "discovered_nodes": [{"node_id": "loc:pod-1", "kind": "pod", "water": 0.0}],
            "discovered_edges": [],
        },
        tick=world.tick,
    )

    snapshot = snapshot_world(world, scenario_id="founding_wakeup_mvp")
    restored_world = restore_world(snapshot)

    assert restored_world.survey_map.signature() == world.survey_map.signature()


def test_scout_action_records_survey_map() -> None:
    world = generate_founding_wakeup_mvp(num_agents=2, seed=5)
    agent = next(iter(world.agents.values()))
    goal = Goal(goal_id="goal:test", owner_id=agent.id, goal_type=GoalType.GATHER_INFORMATION, description="scout")
    goal.status = GoalStatus.ACTIVE

    _handle_scout_interior(world, agent, goal, world.rng)

    assert world.survey_map.nodes
    assert agent.location_id in world.survey_map.nodes


def test_site_scoring_deterministic() -> None:
    survey = SurveyMap(
        nodes={
            "origin": SurveyNode(node_id="origin", kind="pod", water=0.0),
            "candidate": SurveyNode(node_id="candidate", kind="ridge", water=0.5, hazard=0.1, tags=("strategic",)),
        },
        edges={
            "candidate|origin": SurveyEdge(a="origin", b="candidate", distance_m=10.0, travel_cost=12.0, confidence=0.2),
        },
    )
    cfg = SiteScoreConfig(hazard_weight=2.0, distance_weight=0.5, water_weight=1.5, strategic_tag_weights={"strategic": 1.0})

    first_score = score_site(
        survey.nodes["candidate"],
        origin_node_id="origin",
        survey=survey,
        cfg=cfg,
    )
    second_score = score_site(
        survey.nodes["candidate"],
        origin_node_id="origin",
        survey=survey,
        cfg=cfg,
    )

    assert first_score == second_score
