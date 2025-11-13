import pytest

from dosadi.interfaces.contracts import (
    EVENT_PAYLOAD_SCHEMAS,
    validate_event_payload,
    validate_telemetry_snapshot,
)


def test_known_event_types_are_registered():
    known = {"RationConsumed", "ProductionReported", "WitnessStubCreated"}
    assert known.issubset(EVENT_PAYLOAD_SCHEMAS.keys())


def test_event_payload_validation_enforces_required_fields():
    payload = {"item_id": "r1", "action_id": "a1", "actor": "agent"}
    validate_event_payload("RationConsumed", payload)
    with pytest.raises(ValueError):
        validate_event_payload("RationConsumed", {"item_id": "r1"})


def test_telemetry_snapshot_contract_accepts_expected_shape():
    snapshot = {
        "tick": 10,
        "phase_latency_ms": {"AGENT_ACTIVITY": 1.2},
        "handler_latency_ms": {"AGENT_ACTIVITY.Example": 0.6},
        "queue_depths": {"Foo": 2},
        "expired_events": {"Foo": 0},
        "dropped_events": {},
    }
    validate_telemetry_snapshot(snapshot)
