from types import SimpleNamespace

import pytest

from dosadi.runtime.market_signals import MarketSignalsState, MaterialMarketSignal, run_market_signals_for_day
from dosadi.runtime.sanctions import (
    SanctionRule,
    compute_leak_rate,
    evaluate_sanctioned_flow,
    ensure_sanctions_config,
    register_sanction_rule,
    update_compliance,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WorldState
from dosadi.world.routing import compute_route
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode


def _basic_rule(kind: str, target_kind: str, target_id: str, *, goods: list[str] | None = None) -> SanctionRule:
    return SanctionRule(
        rule_id=f"rule:{kind}:{target_id}",
        issuer_id="issuer:1",
        treaty_id=None,
        kind=kind,
        target_kind=target_kind,
        target_id=target_id,
        goods=goods or [],
        severity=0.5,
        start_day=0,
        end_day=10,
        enforcement_required=0.5,
    )


def test_sanctions_deterministic_leak() -> None:
    world = WorldState()
    ensure_sanctions_config(world).enabled = True
    rule = _basic_rule("EMBARGO_GOOD", "WARD", "ward:1", goods=["water"])
    register_sanction_rule(world, rule)

    leak_one = compute_leak_rate(world, rule, day=2, smuggling_strength=0.3, enforcement_override=0.6)
    leak_two = compute_leak_rate(world, rule, day=2, smuggling_strength=0.3, enforcement_override=0.6)

    assert leak_one == leak_two


def test_enforcement_reduces_leak() -> None:
    world = WorldState()
    ensure_sanctions_config(world).enabled = True
    rule = _basic_rule("EMBARGO_GOOD", "WARD", "ward:1", goods=["food"])
    register_sanction_rule(world, rule)

    weak_leak = compute_leak_rate(world, rule, day=1, enforcement_override=0.1)
    strong_leak = compute_leak_rate(world, rule, day=1, enforcement_override=0.9)

    assert strong_leak < weak_leak


def test_comms_penalty_increases_leak() -> None:
    world = WorldState()
    ensure_sanctions_config(world).enabled = True
    world.comms_mod_by_ward["ward:1"] = SimpleNamespace(reliability=0.2)
    rule = _basic_rule("EMBARGO_GOOD", "WARD", "ward:1", goods=["suits"])
    register_sanction_rule(world, rule)

    degraded = compute_leak_rate(world, rule, day=1)
    world.comms_mod_by_ward.clear()
    baseline = compute_leak_rate(world, rule, day=1)

    assert degraded > baseline


def test_transit_denial_blocks_primary_route() -> None:
    node_a = SurveyNode(node_id="A", ward_id="ward:1", kind="WAYPOINT")
    node_b = SurveyNode(node_id="B", ward_id="ward:1", kind="WAYPOINT")
    node_c = SurveyNode(node_id="C", ward_id="ward:1", kind="WAYPOINT")
    edge_ab = SurveyEdge(a="A", b="B", distance_m=1.0, hazard=0.0, travel_cost=1.0)
    edge_ac = SurveyEdge(a="A", b="C", distance_m=1.0, hazard=0.0, travel_cost=1.0)
    edge_cb = SurveyEdge(a="C", b="B", distance_m=1.0, hazard=0.0, travel_cost=1.0)

    survey_map = SurveyMap(
        nodes={node_a.node_id: node_a, node_b.node_id: node_b, node_c.node_id: node_c},
        edges={edge_ab.key: edge_ab, edge_ac.key: edge_ac, edge_cb.key: edge_cb},
    )

    world = WorldState(survey_map=survey_map)
    ensure_sanctions_config(world).enabled = True
    rule = _basic_rule("TRANSIT_DENIAL", "CORRIDOR", edge_ab.key)
    register_sanction_rule(world, rule)

    route = compute_route(world, from_node="A", to_node="B")

    assert route is not None
    assert edge_ab.key not in route.edge_keys


def test_tariffs_raise_costs_and_market_urgency() -> None:
    world = WorldState()
    ensure_sanctions_config(world).enabled = True
    tariff = _basic_rule("TARIFF_PUNITIVE", "FACTION", "faction:1", goods=["SCRAP_METAL"])
    register_sanction_rule(world, tariff)

    flow = evaluate_sanctioned_flow(
        world,
        goods=["scrap_metal"],
        actor_faction_id="faction:1",
        actor_ward_id=None,
        day=1,
        base_cost=10.0,
    )
    assert flow["cost"] > 10.0

    baseline_urgency = 0.2
    world.market_cfg.enabled = True
    world.market_state = MarketSignalsState(
        global_signals={"SCRAP_METAL": MaterialMarketSignal(material="SCRAP_METAL", urgency=baseline_urgency)}
    )
    run_market_signals_for_day(world, day=1)
    updated = world.market_state.global_signals["SCRAP_METAL"].urgency

    assert updated > baseline_urgency


def test_snapshot_roundtrip_preserves_rules_and_compliance() -> None:
    world = WorldState()
    ensure_sanctions_config(world).enabled = True
    rule = _basic_rule("EMBARGO_GOOD", "WARD", "ward:1", goods=["food"])
    register_sanction_rule(world, rule)
    compliance = update_compliance(world, target_id="ward:1", leak_rate=0.2, penalties=0.1, day=3)

    snapshot = snapshot_world(world, scenario_id="scenario:test")
    restored = restore_world(snapshot)

    restored_rule = restored.sanction_rules.get(rule.rule_id)
    assert restored_rule is not None
    assert restored_rule.target_id == "ward:1"
    restored_comp = restored.sanctions_compliance.get(compliance.entity_id)
    assert restored_comp is not None
    assert restored_comp.penalties_applied == pytest.approx(0.1)
