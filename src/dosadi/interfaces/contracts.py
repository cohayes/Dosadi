"""Canonical schema contracts for runtime interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class PayloadSchema:
    """Minimal structural schema for validating payload dictionaries."""

    required: Mapping[str, tuple[type, ...]]
    optional: Mapping[str, tuple[type, ...]] = field(default_factory=dict)

    def validate(self, payload: Mapping[str, Any]) -> None:
        missing = [key for key in self.required if key not in payload]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        for key, expected in self.required.items():
            if not isinstance(payload[key], expected):
                raise TypeError(f"Field '{key}' has type {type(payload[key])!r}, expected {expected!r}")
        for key, expected in self.optional.items():
            if key in payload and not isinstance(payload[key], expected):
                raise TypeError(f"Field '{key}' has type {type(payload[key])!r}, expected {expected!r}")


NUMERIC = (int, float)


EVENT_PAYLOAD_SCHEMAS: Dict[str, PayloadSchema] = {
    "RationConsumed": PayloadSchema(
        required={
            "item_id": (str,),
            "action_id": (str,),
            "actor": (str,),
        },
    ),
    "ProductionReported": PayloadSchema(
        required={
            "ward": (str,),
            "action_id": (str,),
            "actor": (str,),
        }
    ),
    "WitnessStubCreated": PayloadSchema(
        required={
            "ward": (str,),
            "action_id": (str,),
            "actor": (str,),
        }
    ),
    "FuzzMarketShock": PayloadSchema(
        required={"magnitude": NUMERIC, "ward": (str,)},
        optional={"action_id": (str,), "actor": (str,)},
    ),
    "FuzzRumorStorm": PayloadSchema(
        required={"magnitude": NUMERIC, "ward": (str,)},
        optional={"action_id": (str,), "actor": (str,)},
    ),
    "FuzzHealthCrisis": PayloadSchema(
        required={"magnitude": NUMERIC, "ward": (str,)},
        optional={"action_id": (str,), "actor": (str,)},
    ),
}


TELEMETRY_SCHEMA = PayloadSchema(
    required={
        "tick": NUMERIC,
        "phase_latency_ms": (Mapping,),
        "handler_latency_ms": (Mapping,),
        "queue_depths": (Mapping,),
        "expired_events": (Mapping,),
        "dropped_events": (Mapping,),
    }
)


def validate_event_payload(event_type: str, payload: Mapping[str, Any]) -> None:
    schema = EVENT_PAYLOAD_SCHEMAS.get(event_type)
    if schema is None:
        return
    schema.validate(payload)


def validate_telemetry_snapshot(snapshot: Mapping[str, Any]) -> None:
    TELEMETRY_SCHEMA.validate(snapshot)


__all__ = [
    "EVENT_PAYLOAD_SCHEMAS",
    "PayloadSchema",
    "TELEMETRY_SCHEMA",
    "validate_event_payload",
    "validate_telemetry_snapshot",
]
