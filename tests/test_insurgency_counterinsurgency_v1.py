from __future__ import annotations

import copy
import json

from dosadi.runtime.insurgency import (
    CellOpOutcome,
    CellOpPlan,
    CellState,
    InsurgencyConfig,
    _stable_float,
    ensure_active_ops,
    ensure_cells,
    ensure_insurgency_config,
    run_insurgency_week,
)
from dosadi.runtime.policing import ensure_policing_state
from dosadi.runtime.snapshot import restore_world, snapshot_world, to_snapshot_dict
from dosadi.state import WardState, WorldState


def _base_world() -> WorldState:
    world = WorldState(seed=42)
    world.day = 14
    world.wards = {
        "ward:high": WardState(id="ward:high", name="High", ring=1, sealed_mode="OPEN", need_index=0.9),
        "ward:low": WardState(id="ward:low", name="Low", ring=1, sealed_mode="OPEN", need_index=0.1),
    }
    cfg = ensure_insurgency_config(world)
    cfg.enabled = True
    cfg.base_emergence_rate = 0.5
    cfg.base_op_rate = 0.9
    return world


def test_determinism_same_inputs() -> None:
    world_a = _base_world()
    world_b = copy.deepcopy(world_a)

    run_insurgency_week(world_a, day=world_a.day)
    run_insurgency_week(world_b, day=world_b.day)

    sig_a = json.dumps(to_snapshot_dict(world_a.cells_by_ward), sort_keys=True)
    sig_b = json.dumps(to_snapshot_dict(world_b.cells_by_ward), sort_keys=True)

    assert sig_a == sig_b
    assert world_a.cell_ops_history == world_b.cell_ops_history


def test_hardship_and_backlash_increase_emergence() -> None:
    world = _base_world()
    ensure_policing_state(world, "ward:high").doctrine_mix = {"TERROR": 1.0}

    run_insurgency_week(world, day=world.day)

    high_cells = world.cells_by_ward.get("ward:high", [])
    low_cells = world.cells_by_ward.get("ward:low", [])
    assert len(high_cells) >= len(low_cells)
    if high_cells and low_cells:
        high_support = sum(c.support for c in high_cells) / len(high_cells)
        low_support = sum(c.support for c in low_cells) / len(low_cells)
        assert high_support >= low_support


def test_counterintel_improves_detection() -> None:
    world_low = _base_world()
    cfg = ensure_insurgency_config(world_low)
    cell = CellState(cell_id="cell:low", ward_id="ward:high", archetype="REVOLUTIONARY", support=0.6, capability=0.6)
    ensure_cells(world_low).setdefault("ward:high", []).append(cell)
    plan = CellOpPlan(
        op_id="op:low", op_type="SABOTAGE_RELAY", cell_id=cell.cell_id, ward_id="ward:high", day_started=0, day_end=0, target_kind="RELAY", target_id="ward:high", intensity=0.9, reason="test"
    )
    ensure_active_ops(world_low)[plan.op_id] = plan
    world_low.counterintel_by_ward = {"ward:high": 0.0}
    run_insurgency_week(world_low, day=world_low.day)
    low_outcome = world_low.cell_ops_history[-1]

    world_high = _base_world()
    ensure_insurgency_config(world_high).deterministic_salt = cfg.deterministic_salt
    ensure_cells(world_high).setdefault("ward:high", []).append(copy.deepcopy(cell))
    ensure_active_ops(world_high)[plan.op_id] = copy.deepcopy(plan)
    world_high.counterintel_by_ward = {"ward:high": 1.0}
    run_insurgency_week(world_high, day=world_high.day)
    high_outcome = world_high.cell_ops_history[-1]

    detect_roll = _stable_float(cfg, plan.op_id, world_low.day, "detect")
    assert isinstance(low_outcome, CellOpOutcome)
    assert isinstance(high_outcome, CellOpOutcome)
    assert detect_roll >= 0.2  # coverage changes detection threshold
    assert high_outcome.status in {"DETECTED", "ROLLED_UP"}
    assert low_outcome.status in {"SUCCEEDED", "FAILED"}


def test_terror_response_increases_backlash_support() -> None:
    world = _base_world()
    ensure_insurgency_config(world).deterministic_salt = "sabotage-low"
    ensure_insurgency_config(world).backlash_effect = 0.5
    policing = ensure_policing_state(world, "ward:high")
    policing.doctrine_mix = {"TERROR": 1.0}

    cell = CellState(cell_id="cell:terror", ward_id="ward:high", archetype="REVOLUTIONARY", support=0.2, capability=0.6, heat=0.8)
    ensure_cells(world).setdefault("ward:high", []).append(cell)
    plan = CellOpPlan(
        op_id="op:terror", op_type="PROPAGANDA_BROADCAST", cell_id=cell.cell_id, ward_id="ward:high", day_started=0, day_end=0, target_kind="WARD", target_id="ward:high", intensity=0.9, reason="test"
    )
    ensure_active_ops(world)[plan.op_id] = plan
    world.counterintel_by_ward = {"ward:high": 1.0}

    run_insurgency_week(world, day=world.day)

    updated_cell = world.cells_by_ward["ward:high"][0]
    assert updated_cell.support > 0.2
    assert world.metrics.get("insurgency.backlash_proxy", 0.0) > 0.0


def test_sabotage_modifies_comms_modifiers() -> None:
    world = _base_world()
    cell = CellState(cell_id="cell:relay", ward_id="ward:high", archetype="REVOLUTIONARY", support=0.8, capability=0.9)
    ensure_cells(world).setdefault("ward:high", []).append(cell)
    plan = CellOpPlan(
        op_id="op:relay", op_type="SABOTAGE_RELAY", cell_id=cell.cell_id, ward_id="ward:high", day_started=0, day_end=0, target_kind="RELAY", target_id="ward:high", intensity=1.0, reason="test"
    )
    ensure_active_ops(world)[plan.op_id] = plan

    ensure_insurgency_config(world).deterministic_salt = "sabotage-low"

    run_insurgency_week(world, day=world.day)

    mods = world.comms_mod_by_ward.get("ward:high")
    assert mods is not None
    assert getattr(mods, "loss_mult", 1.0) > 1.0


def test_snapshot_roundtrip_preserves_cells_and_ops() -> None:
    world = _base_world()
    run_insurgency_week(world, day=world.day)
    snapshot = snapshot_world(world, scenario_id="test")
    restored = restore_world(snapshot)

    assert restored.cells_by_ward.keys() == world.cells_by_ward.keys()
    assert len(restored.cell_ops_history) == len(world.cell_ops_history)
