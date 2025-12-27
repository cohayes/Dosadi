from __future__ import annotations

from dosadi.runtime.class_system import (
    ClassConfig,
    class_hardship,
    class_inequality,
    ensure_ward_class_state,
    update_class_system_for_day,
)
from dosadi.runtime.institutions import ensure_policy
from dosadi.runtime.labor import update_labor_for_day
from dosadi.runtime.migration import MigrationConfig, WardMigrationState
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WardState, WorldState


def _make_world() -> WorldState:
    world = WorldState(seed=1337)
    world.class_cfg = ClassConfig(enabled=True, update_cadence_days=14)
    world.migration_cfg = MigrationConfig(enabled=True)
    world.labor_cfg.enabled = True
    world.wards["w1"] = WardState(id="w1", name="Ward One", ring=0, sealed_mode="open")
    return world


def test_class_system_determinism() -> None:
    world_a = _make_world()
    world_b = _make_world()

    update_class_system_for_day(world_a, day=14)
    update_class_system_for_day(world_b, day=14)

    state_a = world_a.class_by_ward["w1"]
    state_b = world_b.class_by_ward["w1"]

    assert state_a.tier_share == state_b.tier_share
    assert state_a.notes.get("signature") == state_b.notes.get("signature")


def test_shortage_and_tier_mix_raise_hardship() -> None:
    world = _make_world()
    world.wards["w1"].need_index = 0.8
    state_high = ensure_ward_class_state(world, "w1")
    state_high.tier_share = {
        "T0_ELITE": 0.05,
        "T1_OFFICERS": 0.10,
        "T2_SKILLED": 0.15,
        "T3_UNSKILLED": 0.30,
        "T4_DISPLACED": 0.40,
    }

    world_low = _make_world()
    world_low.wards["w1"].need_index = 0.8
    ensure_ward_class_state(world_low, "w1").tier_share = {
        "T0_ELITE": 0.10,
        "T1_OFFICERS": 0.20,
        "T2_SKILLED": 0.30,
        "T3_UNSKILLED": 0.30,
        "T4_DISPLACED": 0.10,
    }

    update_class_system_for_day(world, day=14)
    update_class_system_for_day(world_low, day=14)

    assert class_hardship(world, "w1") > class_hardship(world_low, "w1")


def test_regime_impacts_inequality() -> None:
    world_equal = _make_world()
    policy_equal = ensure_policy(world_equal, "w1")
    policy_equal.rationing_regime = "EQUAL"
    policy_equal.wage_regime = "FLAT"

    world_elite = _make_world()
    policy_elite = ensure_policy(world_elite, "w1")
    policy_elite.rationing_regime = "ELITE_FIRST"
    policy_elite.wage_regime = "PATRONAGE"

    update_class_system_for_day(world_equal, day=14)
    update_class_system_for_day(world_elite, day=14)

    assert class_inequality(world_elite, "w1") > class_inequality(world_equal, "w1")


def test_camp_integration_reduces_displaced_share() -> None:
    world = _make_world()
    policy = ensure_policy(world, "w1")
    policy.camp_integration_bias = 1.0
    policy.housing_allocation_bias = 1.0
    migration_state = WardMigrationState(ward_id="w1", pop=1000, camp=500, displaced=300)
    world.migration_by_ward["w1"] = migration_state
    class_state = ensure_ward_class_state(world, "w1")
    class_state.tier_share["T4_DISPLACED"] = 0.4

    update_class_system_for_day(world, day=14)

    assert world.class_by_ward["w1"].tier_share["T4_DISPLACED"] < 0.4


def test_labor_receives_hardship_signal() -> None:
    hard_world = _make_world()
    hard_world.wards["w1"].need_index = 0.9
    ensure_ward_class_state(hard_world, "w1").tier_share["T4_DISPLACED"] = 0.4
    update_class_system_for_day(hard_world, day=14)
    update_labor_for_day(hard_world, day=14)

    soft_world = _make_world()
    soft_world.wards["w1"].need_index = 0.1
    ensure_ward_class_state(soft_world, "w1").tier_share["T4_DISPLACED"] = 0.05
    update_class_system_for_day(soft_world, day=14)
    update_labor_for_day(soft_world, day=14)

    hard_org = hard_world.labor_orgs_by_ward["w1"][0]
    soft_org = soft_world.labor_orgs_by_ward["w1"][0]
    assert hard_org.militancy > soft_org.militancy


def test_class_state_survives_snapshot() -> None:
    world = _make_world()
    policy = ensure_policy(world, "w1")
    policy.wage_regime = "GUILD_CAPTURE"
    update_class_system_for_day(world, day=14)

    snapshot = snapshot_world(world, scenario_id="spec")
    restored = restore_world(snapshot)

    assert restored.class_by_ward["w1"].wage_index == world.class_by_ward["w1"].wage_index
    assert restored.class_by_ward["w1"].tier_share == world.class_by_ward["w1"].tier_share
