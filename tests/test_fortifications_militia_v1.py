from dataclasses import replace
from types import SimpleNamespace

from dosadi.runtime.defense import DefenseConfig, run_defense_for_day
from dosadi.runtime.ledger import LedgerAccount
from dosadi.runtime.institutions import WardInstitutionPolicy
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.tech_ladder import TechConfig, TechState
from dosadi.simulation.snapshots import serialize_state
from dosadi.state import WardState, WorldState
from dosadi.world.facilities import Facility, FacilityKind, facility_unlocked
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key


def _basic_world() -> WorldState:
    world = WorldState()
    world.seed = 3
    world.rng.seed(world.seed)
    world.defense_cfg = DefenseConfig(enabled=True, militia_train_rate_per_day=0.1)
    world.ledger_cfg.enabled = True
    world.debug_cfg.level = "standard"
    nodes = {
        "node:a": SurveyNode(node_id="node:a", kind="corridor", ward_id="ward:a"),
        "node:b": SurveyNode(node_id="node:b", kind="corridor", ward_id="ward:b"),
    }
    edge = SurveyEdge(a="node:a", b="node:b", distance_m=1.0, travel_cost=1.0, hazard=0.2)
    world.survey_map = SurveyMap(nodes=nodes, edges={edge.key: edge})
    world.wards = {
        "ward:a": WardState(id="ward:a", name="A", ring=0, sealed_mode="open"),
        "ward:b": WardState(id="ward:b", name="B", ring=0, sealed_mode="open"),
    }
    return world


def test_militia_training_is_deterministic() -> None:
    world_a = _basic_world()
    world_b = _basic_world()
    policy = WardInstitutionPolicy(
        ward_id="ward:a",
        militia_target_strength=0.8,
        militia_training_budget=10.0,
        militia_upkeep_budget=5.0,
    )
    world_a.inst_policy_by_ward["ward:a"] = policy
    world_b.inst_policy_by_ward["ward:a"] = replace(policy)

    for acct in (world_a, world_b):
        acct.ledger_state.accounts["acct:ward:ward:a"] = LedgerAccount(acct_id="acct:ward:ward:a", balance=20.0)

    run_defense_for_day(world_a, day=1)
    run_defense_for_day(world_b, day=1)

    assert serialize_state(world_a.ward_defense) == serialize_state(world_b.ward_defense)


def test_upkeep_shortfall_causes_decay_and_metric() -> None:
    world = _basic_world()
    world.ward_defense["ward:a"] = SimpleNamespace(ward_id="ward:a", militia_strength=0.2, militia_ready=1.0)
    world.inst_policy_by_ward["ward:a"] = WardInstitutionPolicy(
        ward_id="ward:a",
        militia_target_strength=0.2,
        militia_training_budget=0.0,
        militia_upkeep_budget=10.0,
    )
    world.ledger_state.accounts["acct:ward:ward:a"] = LedgerAccount(acct_id="acct:ward:ward:a", balance=1.0)

    run_defense_for_day(world, day=1)

    state = world.ward_defense["ward:a"]
    assert state.militia_strength < 0.2
    assert world.metrics.gauges["defense"]["upkeep_shortfall"] > 0


def test_fortification_requires_unlock() -> None:
    world = WorldState()
    world.tech_cfg = TechConfig(enabled=True)
    world.tech_state = TechState(completed=set(), unlocked=set(), active=set())
    fac = Facility(facility_id="f1", kind=FacilityKind.OUTPOST_L1, site_node_id="node:a")
    world.facilities.add(fac)

    assert not facility_unlocked(world, fac)
    world.tech_state.unlocked.add("UNLOCK_OUTPOST_L1")
    assert facility_unlocked(world, fac)


def test_defense_reduces_raid_probability() -> None:
    world = _basic_world()
    target = edge_key("node:a", "node:b")
    plan = SimpleNamespace(intensity=0.6, target_id=target, op_id="raid:test")

    from dosadi.runtime.war import success_probability

    base_prob = success_probability(world, plan)
    world.defense_cfg.enabled = True
    world.ward_defense["ward:a"] = SimpleNamespace(ward_id="ward:a", militia_strength=0.9, militia_ready=1.0)
    world.facilities.add(
        Facility(facility_id="fort:1", kind=FacilityKind.FORT_L2, site_node_id="node:a", requires_unlocks=set())
    )

    defended_prob = success_probability(world, plan)
    assert defended_prob < base_prob


def test_defense_snapshot_roundtrip() -> None:
    world = _basic_world()
    world.inst_policy_by_ward["ward:a"] = WardInstitutionPolicy(
        ward_id="ward:a",
        militia_target_strength=0.5,
        militia_training_budget=5.0,
        militia_upkeep_budget=0.0,
    )
    run_defense_for_day(world, day=2)

    snapshot = snapshot_world(world, scenario_id="defense-test")
    restored = restore_world(snapshot)

    assert serialize_state(world.ward_defense) == serialize_state(restored.ward_defense)
    assert restored.defense_cfg.enabled
