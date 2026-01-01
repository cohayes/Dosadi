from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from hashlib import sha256
from typing import Dict, List


class IncidentKind(Enum):
    DELIVERY_LOSS = "DELIVERY_LOSS"
    DELIVERY_DELAY = "DELIVERY_DELAY"
    FACILITY_DOWNTIME = "FACILITY_DOWNTIME"
    WORKER_INJURY = "WORKER_INJURY"
    THEFT_CARGO = "THEFT_CARGO"
    THEFT_DEPOT = "THEFT_DEPOT"
    SABOTAGE_PROJECT = "SABOTAGE_PROJECT"
    STRIKE = "STRIKE"
    RIOT = "RIOT"
    SECESSION_ATTEMPT = "SECESSION_ATTEMPT"
    COUP_PLOT = "COUP_PLOT"
    CORRIDOR_CLOSED = "CORRIDOR_CLOSED"
    CORRIDOR_COLLAPSE = "CORRIDOR_COLLAPSE"


@dataclass(slots=True)
class Incident:
    incident_id: str
    kind: IncidentKind
    day: int
    target_kind: str
    target_id: str
    severity: float
    payload: Dict[str, object] = field(default_factory=dict)
    created_day: int = 0
    resolved: bool = False
    resolved_day: int | None = None
    status: str = "active"
    duration_days: int = 0
    cooldown_days: int = 0
    faction_id: str | None = None


@dataclass(slots=True)
class IncidentLedger:
    scheduled: Dict[int, List[str]] = field(default_factory=dict)
    incidents: Dict[str, Incident] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)

    def add(self, inc: Incident) -> None:
        self.incidents[inc.incident_id] = inc
        bucket = self.scheduled.setdefault(inc.day, [])
        if inc.incident_id not in bucket:
            bucket.append(inc.incident_id)

    def due_ids(self, day: int) -> List[str]:
        return list(self.scheduled.get(day, []))

    def signature(self) -> str:
        canonical = {
            "scheduled": {day: list(ids) for day, ids in sorted(self.scheduled.items())},
            "incidents": {
                inc_id: {
                    "kind": incident.kind.value,
                    "day": incident.day,
                    "target": incident.target_id,
                    "target_kind": incident.target_kind,
                    "severity": round(incident.severity, 6),
                    "payload": dict(sorted(incident.payload.items())),
                    "created_day": incident.created_day,
                    "resolved": incident.resolved,
                    "resolved_day": incident.resolved_day,
                }
                for inc_id, incident in sorted(self.incidents.items())
            },
            "history": list(self.history),
        }
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return sha256(payload).hexdigest()

