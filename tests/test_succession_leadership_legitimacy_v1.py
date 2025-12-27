from dosadi.runtime.leadership import ensure_leadership_config, run_leadership_for_day
from dosadi.runtime.sovereignty import ensure_sovereignty_state
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.policing import ensure_policing_state
from dosadi.state import WardState, WorldState


def _base_world() -> WorldState:
    world = WorldState(seed=42)
    world.wards = {
        "ward:0": WardState(id="ward:0", name="A", ring=1, sealed_mode="NONE", need_index=0.2),
        "ward:1": WardState(id="ward:1", name="B", ring=1, sealed_mode="NONE", need_index=0.2),
    }
    ensure_sovereignty_state(world, ward_ids=list(world.wards.keys()))
    cfg = ensure_leadership_config(world)
    cfg.enabled = True
    cfg.update_cadence_days = 1
    world.phase_state.phase = "P1"
    return world


def test_determinism_same_inputs() -> None:
    world_a = _base_world()
    snap = snapshot_world(world_a, scenario_id="determinism")
    world_b = restore_world(snap)

    run_leadership_for_day(world_a, day=30)
    run_leadership_for_day(world_b, day=30)

    assert world_a.leadership_by_polity == world_b.leadership_by_polity
    assert world_a.succession_events == world_b.succession_events


def test_hardship_reduces_legitimacy() -> None:
    low_hardship = _base_world()
    run_leadership_for_day(low_hardship, day=30)
    low_leg = next(iter(low_hardship.leadership_by_polity.values())).legitimacy

    high_hardship = _base_world()
    for ward in high_hardship.wards.values():
        ward.need_index = 0.9
    run_leadership_for_day(high_hardship, day=30)
    high_leg = next(iter(high_hardship.leadership_by_polity.values())).legitimacy

    assert high_leg < low_leg


def test_terror_legitimacy_backlash() -> None:
    baseline = _base_world()
    run_leadership_for_day(baseline, day=30)
    base_state = next(iter(baseline.leadership_by_polity.values()))

    terror = _base_world()
    for ward_id in terror.wards:
        p_state = ensure_policing_state(terror, ward_id)
        p_state.doctrine_mix = {"TERROR": 1.0}
    run_leadership_for_day(terror, day=30)
    terror_state = next(iter(terror.leadership_by_polity.values()))

    assert terror_state.fear_legit > base_state.fear_legit
    assert terror_state.legitimacy < base_state.legitimacy


def test_coup_trigger_in_phase_two_low_legitimacy() -> None:
    world = _base_world()
    cfg = ensure_leadership_config(world)
    cfg.coup_rate_p2 = 0.5
    world.phase_state.phase = "P2"
    for ward in world.wards.values():
        ward.need_index = 0.95
    run_leadership_for_day(world, day=30)

    assert world.succession_events
    assert world.succession_events[-1].kind in {"COUP", "PURGE"}


def test_leadership_change_increases_fracture_pressure() -> None:
    world = _base_world()
    cfg = ensure_leadership_config(world)
    cfg.coup_rate_p2 = 0.6
    world.phase_state.phase = "P2"
    run_leadership_for_day(world, day=30)

    ward_pressures = getattr(world, "governance_failure_pressure", {})
    assert any(val > 0.0 for val in ward_pressures.values())
    insurgency_support = getattr(world, "insurgency_support", {})
    assert any(val > 0.0 for val in insurgency_support.values())


def test_snapshot_roundtrip_preserves_leadership() -> None:
    world = _base_world()
    run_leadership_for_day(world, day=30)
    snap = snapshot_world(world, scenario_id="leader_snap")
    restored = restore_world(snap)

    assert restored.leadership_by_polity == world.leadership_by_polity
    assert restored.succession_events == world.succession_events

    metrics = ensure_metrics(restored)
    assert "leadership.avg_legitimacy" in metrics.gauges
