import pytest

from dosadi.runtime.institutions import ensure_policy
from dosadi.runtime.labor import labor_sector_multiplier, update_labor_for_day
from dosadi.runtime.governance_failures import production_multiplier_for_ward
from dosadi.state import WardState, WorldState
from dosadi.runtime.snapshot import restore_world, snapshot_world


def _basic_world(*, need_index: float = 0.2, seed: int = 1) -> WorldState:
    world = WorldState(seed=seed)
    ward = WardState(id="ward:1", name="Ward One", ring=1, sealed_mode="open")
    ward.need_index = need_index
    world.register_ward(ward)
    world.labor_cfg.enabled = True
    world.labor_cfg.base_strike_rate = 0.25
    return world


def test_deterministic_actions() -> None:
    world_a = _basic_world(seed=99, need_index=0.6)
    world_b = _basic_world(seed=99, need_index=0.6)

    update_labor_for_day(world_a, day=7)
    update_labor_for_day(world_b, day=7)

    a_orgs = world_a.labor_orgs_by_ward["ward:1"]
    b_orgs = world_b.labor_orgs_by_ward["ward:1"]
    assert [(o.status, o.status_until_day, round(o.militancy, 4)) for o in a_orgs] == [
        (o.status, o.status_until_day, round(o.militancy, 4)) for o in b_orgs
    ]
    assert [(e.kind, e.outcome) for e in world_a.labor_events] == [
        (e.kind, e.outcome) for e in world_b.labor_events
    ]


def test_shortage_increases_militancy() -> None:
    calm_world = _basic_world(need_index=0.1)
    stressed_world = _basic_world(need_index=0.8)
    calm_world.labor_cfg.base_strike_rate = 0.0
    stressed_world.labor_cfg.base_strike_rate = 0.0

    update_labor_for_day(calm_world, day=7)
    update_labor_for_day(stressed_world, day=7)

    calm_m = calm_world.labor_orgs_by_ward["ward:1"][0].militancy
    stressed_m = stressed_world.labor_orgs_by_ward["ward:1"][0].militancy
    assert stressed_m > calm_m


def test_negotiation_vs_repression_tradeoff() -> None:
    negotiate_world = _basic_world(need_index=0.9, seed=5)
    repress_world = _basic_world(need_index=0.9, seed=5)
    policy_negotiate = ensure_policy(negotiate_world, "ward:1")
    policy_negotiate.labor_negotiation_bias = 0.6
    policy_repress = ensure_policy(repress_world, "ward:1")
    policy_repress.labor_repression_bias = 0.6
    negotiate_world.labor_cfg.base_strike_rate = 1.0
    repress_world.labor_cfg.base_strike_rate = 1.0

    update_labor_for_day(negotiate_world, day=7)
    update_labor_for_day(repress_world, day=7)

    m_negotiate = negotiate_world.labor_orgs_by_ward["ward:1"][0].militancy
    m_repress = repress_world.labor_orgs_by_ward["ward:1"][0].militancy
    assert m_negotiate < m_repress


def test_output_modifier_applies_to_production_multiplier() -> None:
    baseline = _basic_world(need_index=0.2)
    update_labor_for_day(baseline, day=7)
    normal_mult = production_multiplier_for_ward(baseline, "ward:1")

    disrupted = _basic_world(need_index=0.9)
    disrupted.labor_cfg.base_strike_rate = 1.0
    update_labor_for_day(disrupted, day=7)
    # Force visible disruption
    for org in disrupted.labor_orgs_by_ward["ward:1"]:
        org.status = "STRIKE"
        org.status_until_day = 30
    strike_mult = production_multiplier_for_ward(disrupted, "ward:1")

    assert strike_mult < normal_mult
    assert labor_sector_multiplier(disrupted, "ward:1", "REFINING") < 1.0


def test_persistence_round_trip() -> None:
    world = _basic_world(need_index=0.7, seed=11)
    update_labor_for_day(world, day=7)
    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)

    assert restored.labor_cfg.enabled is True
    assert restored.labor_orgs_by_ward.keys() == world.labor_orgs_by_ward.keys()
    assert [(e.kind, e.ward_id) for e in restored.labor_events] == [
        (e.kind, e.ward_id) for e in world.labor_events
    ]
