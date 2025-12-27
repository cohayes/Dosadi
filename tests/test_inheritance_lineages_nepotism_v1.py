from types import SimpleNamespace

from dosadi.runtime.constitution import ConstitutionState
from dosadi.runtime.lineages import (
    ensure_lineage_config,
    ensure_lineage_state,
    lineage_signature,
    nepotism_bias,
    update_lineages,
)
from dosadi.runtime.mobility import ensure_mobility_config, ensure_polity_mobility_state
from dosadi.runtime.snapshot import restore_world, snapshot_world


def _base_world(corruption: float = 0.0):
    world = SimpleNamespace()
    world.polity_id = "polity:test"
    ensure_lineage_config(world).enabled = True
    ensure_mobility_config(world).enabled = True
    mobility_state = ensure_polity_mobility_state(world, world.polity_id)
    mobility_state.tier_share = {
        "UNDERCLASS": 0.05,
        "WORKING": 0.35,
        "SKILLED": 0.2,
        "CLERK": 0.15,
        "GUILD": 0.15,
        "ELITE": 0.10,
    }
    world.corruption_index_by_polity = {world.polity_id: corruption}
    return world


def test_lineage_determinism():
    w1 = _base_world()
    w2 = _base_world()
    update_lineages(w1, day=0)
    update_lineages(w2, day=0)
    sig1 = lineage_signature(w1, w1.polity_id, day=0)
    sig2 = lineage_signature(w2, w2.polity_id, day=0)
    assert sig1 == sig2


def test_elite_houses_accumulate_faster():
    world = _base_world()
    update_lineages(world, day=0)
    baseline = {house.tier: house.wealth for house in ensure_lineage_state(world, world.polity_id).houses.values()}
    update_lineages(world, day=100)
    updated = {house.tier: house.wealth for house in ensure_lineage_state(world, world.polity_id).houses.values()}
    assert updated.get("ELITE", 0.0) > baseline.get("ELITE", 0.0)
    assert updated.get("ELITE", 0.0) - baseline.get("ELITE", 0.0) > updated.get("WORKING", 0.0) - baseline.get("WORKING", 0.0)


def test_corruption_strengthens_edges():
    low = _base_world(corruption=0.1)
    high = _base_world(corruption=0.8)
    update_lineages(low, day=120)
    update_lineages(high, day=120)
    low_state = ensure_lineage_state(low, low.polity_id)
    high_state = ensure_lineage_state(high, high.polity_id)
    low_strength = sum(edge.strength for edge in low_state.edges)
    high_strength = sum(edge.strength for edge in high_state.edges)
    assert high_strength > low_strength
    assert high_state.nepotism_norm > low_state.nepotism_norm


def test_rights_constrain_bias():
    world = _base_world(corruption=0.5)
    update_lineages(world, day=0)
    state = ensure_lineage_state(world, world.polity_id)
    house_id = next(iter(state.houses))
    constitution_state = ConstitutionState(polity_id=world.polity_id)
    constitution_state.rights_current = {"due_process": 0.8, "speech": 0.7}
    constitution_state.constraints_current = {"court_independence": 0.7, "audit_independence": 0.5, "term_limits": 0.6}
    world.constitution_by_polity = {world.polity_id: constitution_state}
    constrained_bias = nepotism_bias(world, world.polity_id, house_id, "SUPERVISOR")

    constitution_state_low = ConstitutionState(polity_id=world.polity_id)
    constitution_state_low.rights_current = {"due_process": 0.1}
    constitution_state_low.constraints_current = {"court_independence": 0.0, "audit_independence": 0.0, "term_limits": 0.0}
    world.constitution_by_polity = {world.polity_id: constitution_state_low}
    unconstrained_bias = nepotism_bias(world, world.polity_id, house_id, "SUPERVISOR")

    assert constrained_bias < unconstrained_bias


def test_inheritance_cycle_advances_generation():
    world = _base_world()
    cfg = ensure_lineage_config(world)
    cfg.inheritance_years = 1
    update_lineages(world, day=0)
    state = ensure_lineage_state(world, world.polity_id)
    generations_before = {house.house_id: house.head_generation for house in state.houses.values()}
    wealth_before = {house.house_id: house.wealth for house in state.houses.values()}
    update_lineages(world, day=400)
    state_after = ensure_lineage_state(world, world.polity_id)
    for house in state_after.houses.values():
        assert house.head_generation > generations_before[house.house_id]
        assert house.wealth >= wealth_before[house.house_id]


def test_lineage_snapshot_roundtrip():
    world = _base_world()
    update_lineages(world, day=0)
    sig_before = lineage_signature(world, world.polity_id, day=0)
    snapshot = snapshot_world(world, scenario_id="scenario:test")
    restored = restore_world(snapshot)
    sig_after = lineage_signature(restored, restored.polity_id, day=0)
    assert sig_before == sig_after
