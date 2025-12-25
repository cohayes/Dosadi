from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from hashlib import sha256
from typing import Dict, List


class EventKind(Enum):
    INCIDENT = "INCIDENT"
    DELIVERY_DELIVERED = "DELIVERY_DELIVERED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    DELIVERY_DELAYED = "DELIVERY_DELAYED"
    STOCKPILE_PULL_REQUESTED = "STOCKPILE_PULL_REQUESTED"
    STOCKPILE_PULL_COMPLETED = "STOCKPILE_PULL_COMPLETED"
    STOCKPILE_SHORTAGE = "STOCKPILE_SHORTAGE"
    PROJECT_APPROVED = "PROJECT_APPROVED"
    PROJECT_STAGED = "PROJECT_STAGED"
    PROJECT_COMPLETE = "PROJECT_COMPLETE"
    FACILITY_DOWNTIME = "FACILITY_DOWNTIME"
    FACILITY_REACTIVATED = "FACILITY_REACTIVATED"
    PHASE_TRANSITION = "PHASE_TRANSITION"
    FOCUS_SESSION_START = "FOCUS_SESSION_START"
    FOCUS_SESSION_END = "FOCUS_SESSION_END"
    FOCUS_DAY_TRANSITION = "FOCUS_DAY_TRANSITION"
    SUIT_WEAR_WARN = "SUIT_WEAR_WARN"
    SUIT_REPAIR_NEEDED = "SUIT_REPAIR_NEEDED"
    SUIT_CRITICAL = "SUIT_CRITICAL"
    SUIT_REPAIR_STARTED = "SUIT_REPAIR_STARTED"
    SUIT_REPAIRED = "SUIT_REPAIRED"


@dataclass(slots=True)
class WorldEvent:
    event_id: str
    day: int
    kind: EventKind
    subject_kind: str
    subject_id: str
    severity: float = 0.0
    payload: Dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class WorldEventLog:
    max_len: int
    events: List[WorldEvent] = field(default_factory=list)
    next_seq: int = 0
    base_seq: int = 0

    def append(self, event: WorldEvent) -> None:
        if not event.event_id:
            event.event_id = f"evt:{event.day}:{self.next_seq}"
        self.events.append(event)
        self.next_seq += 1

        if self.max_len > 0 and len(self.events) > self.max_len:
            overflow = len(self.events) - self.max_len
            del self.events[:overflow]
            self.base_seq += overflow

    def since(self, cursor_seq: int) -> List[WorldEvent]:
        if cursor_seq < self.base_seq:
            cursor_seq = self.base_seq
        offset = cursor_seq - self.base_seq
        if offset < 0:
            offset = 0
        return list(self.events[offset:])

    def signature(self) -> str:
        canonical = {
            "base_seq": self.base_seq,
            "next_seq": self.next_seq,
            "events": [
                {
                    "event_id": e.event_id,
                    "day": e.day,
                    "kind": e.kind.value,
                    "subject_kind": e.subject_kind,
                    "subject_id": e.subject_id,
                    "severity": round(float(e.severity), 6),
                    "payload": {k: v for k, v in sorted(e.payload.items())},
                }
                for e in self.events
            ],
        }
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "EventKind",
    "WorldEvent",
    "WorldEventLog",
]
