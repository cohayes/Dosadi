from __future__ import annotations

from types import SimpleNamespace

from dosadi.runtime.religion_sects import (
    PolitySectState,
    SchismEvent,
    ensure_default_sects,
    ensure_polity_sect_state,
    ensure_sects_config,
    update_sects,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.telemetry import DebugConfig, ensure_event_ring, ensure_metrics


def _make_world(seed: int = 7) -> SimpleNamespace:
    world = SimpleNamespace()
    world.seed = seed
    world.polities = ["polity:1"]
    world.metrics = ensure_metrics(world)
    world.debug_cfg = DebugConfig(level="standard")
    ensure_event_ring(world)
    ensure_sects_config(world)
    ensure_default_sects(world)
    state = ensure_polity_sect_state(world, "polity:1")
    state.strength_by_sect = {"sect:orthodox": 0.7, "sect:martyr_cult": 0.3}
    return world


def test_determinism_same_inputs_same_outcome():
    w1 = _make_world(seed=9)
    w2 = _make_world(seed=9)
    w1.sects_cfg.enabled = True
    w2.sects_cfg.enabled = True

    update_sects(w1, day=14)
    update_sects(w2, day=14)

    assert w1.sects_by_polity["polity:1"].strength_by_sect == w2.sects_by_polity["polity:1"].strength_by_sect
    assert w1.sects_by_polity["polity:1"].schism_pressure == w2.sects_by_polity["polity:1"].schism_pressure


def test_pressure_rises_with_hardship_and_culture():
    baseline = _make_world()
    baseline.sects_cfg.enabled = True
    update_sects(baseline, day=14)
    base_pressure = baseline.sects_by_polity["polity:1"].schism_pressure

    stressed = _make_world()
    stressed.sects_cfg.enabled = True
    stressed.hardship_by_polity = {"polity:1": 0.9}
    stressed.culture_war_by_polity = {"polity:1": 0.8}
    update_sects(stressed, day=14)
    stressed_pressure = stressed.sects_by_polity["polity:1"].schism_pressure

    assert stressed_pressure > base_pressure
    assert stressed_pressure > 0.0


def test_schism_generates_new_sect_and_reallocates_strength():
    world = _make_world(seed=3)
    cfg = world.sects_cfg
    cfg.enabled = True
    cfg.schism_base_rate = 1.0
    cfg.update_cadence_days = 0
    world.hardship_by_polity = {"polity:1": 1.0}
    state = world.sects_by_polity["polity:1"]

    update_sects(world, day=0)

    assert len(state.strength_by_sect) > 2
    assert any(key.startswith("sect:") and ":" in key for key in state.strength_by_sect if key not in {"sect:orthodox", "sect:martyr_cult"})
    parent_share = state.strength_by_sect.get("sect:orthodox", 0)
    assert parent_share < 0.7
    assert isinstance(world.schism_events[0], SchismEvent)


def test_repression_bolsters_martyr_cults():
    calm = _make_world()
    calm.sects_cfg.enabled = True
    calm.policing_repression_by_polity = {"polity:1": 0.0}
    update_sects(calm, day=14)
    calm_share = calm.sects_by_polity["polity:1"].strength_by_sect.get("sect:martyr_cult")

    repressive = _make_world()
    repressive.sects_cfg.enabled = True
    repressive.policing_repression_by_polity = {"polity:1": 0.9}
    update_sects(repressive, day=14)
    martyr_share = repressive.sects_by_polity["polity:1"].strength_by_sect.get("sect:martyr_cult")

    assert martyr_share > calm_share


def test_holy_conflict_escalates_when_dominant_and_aligned():
    world = _make_world()
    world.sects_cfg.enabled = True
    state: PolitySectState = world.sects_by_polity["polity:1"]
    state.strength_by_sect = {"sect:orthodox": 0.8, "sect:martyr_cult": 0.2}
    world.leadership_sponsor_alignment = {"polity:1": 0.8}
    update_sects(world, day=14)

    assert state.conflict_intensity > 0.0


def test_snapshot_roundtrip_persists_sects():
    world = _make_world()
    world.sects_cfg.enabled = True
    world.hardship_by_polity = {"polity:1": 0.5}
    update_sects(world, day=14)

    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)

    restored_state: PolitySectState = restored.sects_by_polity["polity:1"]
    assert isinstance(restored_state, PolitySectState)
    assert restored_state.strength_by_sect == world.sects_by_polity["polity:1"].strength_by_sect
    assert restored.sects_cfg.enabled == world.sects_cfg.enabled
