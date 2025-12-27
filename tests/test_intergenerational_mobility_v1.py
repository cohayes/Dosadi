from __future__ import annotations

from dosadi.runtime.mobility import (
    MobilityConfig,
    apply_generation_if_due,
    build_mobility_matrix_from_signals,
    mobility_signature,
    update_mobility,
    update_mobility_matrix,
    _indices,  # type: ignore
)
from dosadi.state import WorldState
from dosadi.runtime.snapshot import snapshot_world, restore_world


DEFAULT_POLITY = "default"


def _world(enabled: bool = True) -> WorldState:
    world = WorldState(seed=42)
    world.mobility_cfg.enabled = enabled
    world.polity_id = DEFAULT_POLITY
    return world


def test_deterministic_matrix_from_same_signals():
    world1 = _world()
    world1.day = 90
    update_mobility(world1, day=90)
    state1 = world1.mobility_by_polity[DEFAULT_POLITY]
    sig1 = mobility_signature(state1, world1.mobility_cfg, day=90)

    world2 = _world()
    world2.day = 90
    update_mobility(world2, day=90)
    state2 = world2.mobility_by_polity[DEFAULT_POLITY]
    sig2 = mobility_signature(state2, world2.mobility_cfg, day=90)

    assert sig1 == sig2
    assert state1.mobility_matrix == state2.mobility_matrix


def test_education_increases_upward_mobility():
    cfg = MobilityConfig(enabled=True)
    low = build_mobility_matrix_from_signals(cfg, {"education_access": 0.1})
    high = build_mobility_matrix_from_signals(cfg, {"education_access": 0.9})
    low_indices = _indices(low, cfg)
    high_indices = _indices(high, cfg)

    assert high["WORKING"].get("SKILLED", 0.0) > low["WORKING"].get("SKILLED", 0.0)
    assert high_indices["upward_index"] > low_indices["upward_index"]


def test_debt_increases_traps_and_downward_moves():
    cfg = MobilityConfig(enabled=True)
    low_debt = build_mobility_matrix_from_signals(cfg, {"debt_pressure": 0.05})
    high_debt = build_mobility_matrix_from_signals(cfg, {"debt_pressure": 0.9})
    low_idx = _indices(low_debt, cfg)
    high_idx = _indices(high_debt, cfg)

    assert high_idx["trap_index"] > low_idx["trap_index"]
    assert high_idx["downward_index"] > low_idx["downward_index"]


def test_union_strength_reduces_downward_mobility():
    cfg = MobilityConfig(enabled=True)
    weak = build_mobility_matrix_from_signals(cfg, {"union_strength": 0.0, "debt_pressure": 0.5})
    strong = build_mobility_matrix_from_signals(cfg, {"union_strength": 0.9, "debt_pressure": 0.5})
    weak_idx = _indices(weak, cfg)
    strong_idx = _indices(strong, cfg)

    assert strong_idx["downward_index"] < weak_idx["downward_index"]


def test_generation_step_applies_distribution_changes():
    world = _world()
    world.day = 365 * 20
    update_mobility_matrix(world, DEFAULT_POLITY, day=0, signals={"education_access": 0.5})
    state = world.mobility_by_polity[DEFAULT_POLITY]
    state.tier_share = {
        "UNDERCLASS": 0.2,
        "WORKING": 0.3,
        "SKILLED": 0.2,
        "CLERK": 0.15,
        "GUILD": 0.1,
        "ELITE": 0.05,
    }
    before = dict(state.tier_share)
    apply_generation_if_due(world, day=365 * 20, force=True)
    updated_state = world.mobility_by_polity[DEFAULT_POLITY]
    assert abs(sum(updated_state.tier_share.values()) - 1.0) < 1e-6
    assert updated_state.tier_share != before


def test_snapshot_roundtrip_preserves_mobility_state():
    world = _world()
    world.day = 90
    update_mobility(world, day=90)
    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)

    assert hasattr(restored, "mobility_by_polity")
    assert restored.mobility_by_polity[DEFAULT_POLITY].mobility_matrix
    assert restored.mobility_cfg.enabled is True
