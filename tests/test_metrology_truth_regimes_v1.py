import copy

from dosadi.runtime.ideology import WardIdeologyState
from dosadi.runtime.shadow_state import CorruptionIndex
from dosadi.runtime.truth_regimes import (
    IntegrityState,
    TruthEvent,
    ensure_truth_ledgers,
    measurement_noise,
    run_truth_regimes_update,
)
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.runtime.class_system import WardClassState
from dosadi.state import WardState, WorldState


def _basic_world() -> WorldState:
    world = WorldState(seed=7)
    world.truth_cfg.enabled = True
    world.wards = {
        "ward:a": WardState(id="ward:a", name="A", ring=1, sealed_mode="OPEN"),
        "ward:b": WardState(id="ward:b", name="B", ring=1, sealed_mode="OPEN"),
    }
    world.corruption_by_ward = {
        "ward:a": CorruptionIndex(ward_id="ward:a", petty=0.1, capture=0.7, shadow_state=0.2, exposure_risk=0.3),
        "ward:b": CorruptionIndex(ward_id="ward:b", petty=0.1, capture=0.2, shadow_state=0.1, exposure_risk=0.1),
    }
    world.ideology_by_ward = {
        "ward:a": WardIdeologyState(ward_id="ward:a", propaganda_intensity=0.6),
        "ward:b": WardIdeologyState(ward_id="ward:b", propaganda_intensity=0.1),
    }
    world.class_by_ward = {
        "ward:a": WardClassState(ward_id="ward:a", hardship_index=0.2),
        "ward:b": WardClassState(ward_id="ward:b", hardship_index=0.4),
    }
    ensure_metrics(world)
    return world


def _state_signature(world: WorldState) -> dict:
    integrity_by_ward, integrity_by_polity = {}, {}
    for scope_id, state in getattr(world, "integrity_by_ward", {}).items():
        integrity_by_ward[scope_id] = {
            key: round(getattr(state, key), 6)
            for key in ("metrology", "ledger", "census", "telemetry", "judiciary")
        }
    for scope_id, state in getattr(world, "integrity_by_polity", {}).items():
        integrity_by_polity[scope_id] = {
            key: round(getattr(state, key), 6)
            for key in ("metrology", "ledger", "census", "telemetry", "judiciary")
        }
    events = [
        (
            evt.day,
            evt.scope_kind,
            evt.scope_id,
            evt.kind,
            evt.domain,
            round(evt.magnitude, 6),
            tuple(sorted(evt.reason_codes)),
        )
        for evt in getattr(world, "truth_events", [])
    ]
    return {"ward": integrity_by_ward, "polity": integrity_by_polity, "events": events}


def test_deterministic_updates_produce_same_signature():
    world_a = _basic_world()
    world_b = copy.deepcopy(world_a)

    run_truth_regimes_update(world_a, day=30)
    run_truth_regimes_update(world_b, day=30)

    assert _state_signature(world_a) == _state_signature(world_b)


def test_capture_and_propaganda_reduce_integrity():
    world = _basic_world()

    run_truth_regimes_update(world, day=30)

    state = world.integrity_by_ward["ward:a"]
    assert state.ledger < 1.0
    assert state.telemetry < 1.0
    assert state.metrology <= 1.0


def test_audit_capacity_pushes_integrity_upward():
    world = _basic_world()
    integrity_by_polity, integrity_by_ward, events = ensure_truth_ledgers(world)
    integrity_by_ward["ward:a"] = IntegrityState(
        scope_kind="WARD",
        scope_id="ward:a",
        metrology=0.6,
        ledger=0.65,
        census=0.62,
        telemetry=0.64,
        judiciary=0.66,
        audit_capacity=0.9,
        propaganda_pressure=0.2,
    )
    world.truth_events = events

    run_truth_regimes_update(world, day=30)

    updated = world.integrity_by_ward["ward:a"]
    assert updated.ledger > 0.65
    assert updated.metrology > 0.6


def test_truth_events_bounded_and_sorted():
    world = _basic_world()
    world.truth_cfg.max_fraud_events = 5
    world.wards.update({f"ward:{idx}": WardState(id=f"ward:{idx}", name=str(idx), ring=1, sealed_mode="OPEN") for idx in range(5, 15)})
    for idx in range(5, 15):
        world.corruption_by_ward[f"ward:{idx}"] = CorruptionIndex(
            ward_id=f"ward:{idx}", petty=0.2, capture=0.8, shadow_state=0.5, exposure_risk=0.4
        )
        world.ideology_by_ward[f"ward:{idx}"] = WardIdeologyState(ward_id=f"ward:{idx}", propaganda_intensity=0.7)

    run_truth_regimes_update(world, day=30)

    assert len(world.truth_events) <= world.truth_cfg.max_fraud_events
    ordered = sorted(world.truth_events, key=lambda evt: (evt.day, evt.magnitude, evt.scope_id))
    assert [evt.scope_id for evt in world.truth_events] == [evt.scope_id for evt in ordered]


def test_measurement_noise_reflects_integrity_and_propaganda():
    world = _basic_world()
    integrity_by_polity, integrity_by_ward, _ = ensure_truth_ledgers(world)
    integrity_by_polity["polity:empire"] = IntegrityState(
        scope_kind="POLITY",
        scope_id="polity:empire",
        ledger=0.5,
        propaganda_pressure=0.6,
        audit_capacity=0.2,
    )

    bias, variance, flags = measurement_noise(world, ("POLITY", "polity:empire"), "ledger")
    assert bias > 0.0
    assert variance > 0.0
    assert "LOW_INTEGRITY" in flags
    assert "PROPAGANDA" in flags
    assert "LOW_AUDIT" in flags
