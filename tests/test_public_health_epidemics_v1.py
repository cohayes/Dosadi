from dosadi.runtime.health import (
    DISEASE_RESPIRATORY,
    DISEASE_WATERBORNE,
    DISEASE_WOUND,
    WardHealthState,
    run_health_for_day,
)
from dosadi.runtime.migration import WardMigrationState
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WardState, WorldState


def _make_world(seed: int = 1) -> WorldState:
    world = WorldState(seed=seed)
    world.wards["ward:a"] = WardState(id="ward:a", name="A", ring=1, sealed_mode="open", need_index=0.2, risk_index=0.1)
    world.wards["ward:b"] = WardState(id="ward:b", name="B", ring=1, sealed_mode="open", need_index=0.2, risk_index=0.1)
    world.edges = {"edge:ab": {"origin": "ward:a", "destination": "ward:b"}}
    world.migration_by_ward["ward:a"] = WardMigrationState(ward_id="ward:a")
    world.migration_by_ward["ward:b"] = WardMigrationState(ward_id="ward:b")
    world.health_cfg.enabled = True
    world.health_cfg.update_cadence_days = 1
    world.health_cfg.outbreak_trigger_rate = 0.02
    world.health_cfg.baseline_chronic_rate = 0.01
    return world


def test_deterministic_outbreaks() -> None:
    world_a = _make_world(seed=33)
    world_b = _make_world(seed=33)

    run_health_for_day(world_a, day=0)
    run_health_for_day(world_b, day=0)

    assert {k: v.outbreaks for k, v in world_a.health_by_ward.items()} == {
        k: v.outbreaks for k, v in world_b.health_by_ward.items()
    }


def test_camps_increase_risk() -> None:
    world_low = _make_world(seed=3)
    world_high = _make_world(seed=3)
    world_low.health_cfg.outbreak_trigger_rate = 0.0
    world_high.health_cfg.outbreak_trigger_rate = 0.0
    world_high.migration_by_ward["ward:a"].camp = 8000

    run_health_for_day(world_low, day=0)
    run_health_for_day(world_high, day=0)

    assert not world_low.health_by_ward["ward:a"].outbreaks
    assert world_high.health_by_ward["ward:a"].outbreaks


def test_clinics_and_sanitation_mitigate() -> None:
    world = _make_world(seed=9)
    state = WardHealthState(ward_id="ward:a", healthcare_cap=0.8, sanitation_cap=0.6)
    state.outbreaks[DISEASE_WATERBORNE] = 0.6
    world.health_by_ward["ward:a"] = state

    run_health_for_day(world, day=0)

    assert world.health_by_ward["ward:a"].outbreaks[DISEASE_WATERBORNE] < 0.6


def test_corridor_spread_between_wards() -> None:
    world = _make_world(seed=13)
    world.health_cfg.outbreak_trigger_rate = 0.0
    world.health_cfg.baseline_chronic_rate = 0.0
    world.health_by_ward["ward:a"] = WardHealthState(ward_id="ward:a", outbreaks={DISEASE_RESPIRATORY: 0.8})
    world.health_by_ward["ward:b"] = WardHealthState(ward_id="ward:b", outbreaks={})

    run_health_for_day(world, day=0)

    assert world.health_by_ward["ward:b"].outbreaks[DISEASE_RESPIRATORY] > 0.0


def test_consequences_affect_labor_and_displacement() -> None:
    world = _make_world(seed=21)
    world.health_cfg.outbreak_trigger_rate = 0.0
    world.health_cfg.baseline_chronic_rate = 0.0
    world.health_by_ward["ward:a"] = WardHealthState(
        ward_id="ward:a", chronic_burden=0.2, outbreaks={DISEASE_WOUND: 0.6}
    )

    run_health_for_day(world, day=0)

    labor_mult = world.health_by_ward["ward:a"].notes["labor_mult"]
    assert labor_mult < 1.0
    assert world.migration_by_ward["ward:a"].notes.get("disease_pressure", 0.0) > 0.0


def test_snapshot_roundtrip_health_state() -> None:
    world = _make_world(seed=77)
    world.health_cfg.outbreak_trigger_rate = 0.05
    run_health_for_day(world, day=0)
    snap = snapshot_world(world, scenario_id="health-scenario")
    restored = restore_world(snap)

    run_health_for_day(restored, day=1)

    assert restored.health_by_ward
    assert restored.health_events
    assert restored.health_cfg.enabled is True
