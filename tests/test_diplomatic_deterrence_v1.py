import copy
import random

from dosadi.runtime.deterrence import (
    DeterrenceConfig,
    ensure_relationship,
    run_deterrence_for_day,
)
from dosadi.runtime.ledger import get_or_create_account
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.treaties import TreatyConfig, TreatyState, TreatyTerms
from dosadi.runtime.war import RaidPlan, WarConfig, run_war_for_day, success_probability
from dosadi.simulation.snapshots import serialize_state
from dosadi.state import WardState, WorldState
from dosadi.world.factions import Faction
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key


def _basic_world() -> WorldState:
    world = WorldState()
    world.seed = 17
    world.rng = random.Random(world.seed)
    world.deterrence_cfg = DeterrenceConfig(enabled=True, deterministic_salt="det-test")
    world.treaty_cfg = TreatyConfig(enabled=True)
    world.war_cfg = WarConfig(enabled=True, deterministic_salt="war-test")

    world.wards = {
        "ward:a": WardState(
            id="ward:a", name="A", ring=0, sealed_mode="open", legitimacy=0.4, risk_index=0.7, need_index=0.4
        ),
        "ward:b": WardState(
            id="ward:b", name="B", ring=0, sealed_mode="open", legitimacy=0.4, risk_index=0.7, need_index=0.4
        ),
    }
    world.factions = {
        "fac:state": Faction(faction_id="fac:state", name="State", kind="STATE"),
        "fac:raiders": Faction(faction_id="fac:raiders", name="Raiders", kind="RAIDERS"),
    }
    nodes = {
        "node:a": SurveyNode(node_id="node:a", kind="corridor", ward_id="ward:a"),
        "node:b": SurveyNode(node_id="node:b", kind="corridor", ward_id="ward:b"),
    }
    edges = {
        edge_key("node:a", "node:b"): SurveyEdge(
            a="node:a", b="node:b", distance_m=1.0, travel_cost=1.0, hazard=0.2
        )
    }
    world.survey_map = SurveyMap(nodes=nodes, edges=edges)
    return world


def _simple_plan(target: str, *, day: int = 0, intensity: float = 0.6) -> RaidPlan:
    return RaidPlan(
        op_id="raid:test",
        aggressor_faction="fac:raiders",
        target_kind="corridor",
        target_id=target,
        start_day=day,
        end_day=day,
        intensity=intensity,
        objective="disrupt",
    )


def test_relationship_updates_are_deterministic() -> None:
    world_a = _basic_world()
    world_b = copy.deepcopy(world_a)

    run_deterrence_for_day(world_a, day=7)
    run_deterrence_for_day(world_b, day=7)

    assert serialize_state(world_a.relationships) == serialize_state(world_b.relationships)


def test_mutual_defense_pact_forms_from_threat() -> None:
    world = _basic_world()
    rel = ensure_relationship(world, "ward:a", "ward:b")
    rel.threat = 0.8

    run_deterrence_for_day(world, day=7)

    assert any(
        state.terms.treaty_type == "MUTUAL_DEFENSE_PACT" for state in getattr(world, "treaties", {}).values()
    )


def test_deterrence_penalty_reduces_success_probability() -> None:
    world = _basic_world()
    target = edge_key("node:a", "node:b")
    plan = _simple_plan(target)

    rel = ensure_relationship(world, "fac:raiders", "ward:a")
    rel.trust = 0.8
    rel.credibility_a = 0.9
    rel.credibility_b = 0.9

    base_prob = success_probability(world, plan)

    terms = TreatyTerms(
        treaty_type="NONAGGRESSION_PACT",
        party_a="fac:raiders",
        party_b="ward:a",
        obligations_a=[],
        obligations_b=[],
        duration_days=30,
        consideration={},
        penalties={},
    )
    world.treaties = {"p1": TreatyState(treaty_id="p1", terms=terms, start_day=0, end_day=30)}

    penalized = success_probability(world, plan)
    assert penalized < base_prob


def test_pact_aid_and_bluff_penalty() -> None:
    target = edge_key("node:a", "node:b")

    # Successful aid delivery
    world = _basic_world()
    world.ledger_cfg.enabled = True
    donor = get_or_create_account(world, "acct:ward:ward:b")
    donor.balance = 5.0
    pact_terms = TreatyTerms(
        treaty_type="MUTUAL_DEFENSE_PACT",
        party_a="ward:a",
        party_b="ward:b",
        obligations_a=[],
        obligations_b=[],
        duration_days=30,
        consideration={},
        penalties={},
    )
    world.treaties = {"pact": TreatyState(treaty_id="pact", terms=pact_terms, start_day=0, end_day=30)}
    plan = _simple_plan(target)
    world.raid_active = {plan.op_id: plan}
    run_war_for_day(world, day=0)
    target_acct = get_or_create_account(world, "acct:ward:ward:a")
    assert target_acct.balance > 0.0

    # Failed aid triggers bluff penalty
    world2 = _basic_world()
    world2.ledger_cfg.enabled = True
    world2.treaties = {"pact": TreatyState(treaty_id="pact", terms=pact_terms, start_day=0, end_day=30)}
    rel_before = ensure_relationship(world2, "ward:b", "ward:a")
    rel_before.credibility_a = 0.6
    cred_before = rel_before.credibility_a
    plan2 = _simple_plan(target, day=1)
    world2.raid_active = {plan2.op_id: plan2}
    run_war_for_day(world2, day=1)
    rel_after = ensure_relationship(world2, "ward:b", "ward:a")
    assert rel_after.credibility_a < cred_before


def test_relationships_persist_through_snapshot() -> None:
    world = _basic_world()
    rel = ensure_relationship(world, "fac:raiders", "ward:a")
    rel.trust = 0.7

    run_deterrence_for_day(world, day=7)
    snapshot = snapshot_world(world, scenario_id="deterrence-test")
    restored = restore_world(snapshot)

    assert serialize_state(world.relationships) == serialize_state(restored.relationships)
