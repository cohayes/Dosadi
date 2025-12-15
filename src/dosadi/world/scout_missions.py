from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Mapping


def _canonical_json(data: Mapping[str, object]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


class MissionStatus(str, Enum):
    PLANNED = "PLANNED"
    EN_ROUTE = "EN_ROUTE"
    RETURNING = "RETURNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class MissionIntent(str, Enum):
    PERIMETER = "PERIMETER"
    RADIAL = "RADIAL"
    TARGET_NODE = "TARGET_NODE"


@dataclass(slots=True)
class ScoutMission:
    mission_id: str
    status: MissionStatus
    intent: MissionIntent

    origin_node_id: str
    current_node_id: str
    target_node_id: str | None
    heading_deg: float | None
    max_days: int

    party_agent_ids: list[str]
    supplies: dict[str, float]
    risk_budget: float

    start_day: int
    last_step_day: int
    days_elapsed: int

    discoveries: list[dict[str, object]]
    notes: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ScoutMissionLedger:
    missions: dict[str, ScoutMission] = field(default_factory=dict)
    active_ids: list[str] = field(default_factory=list)

    def add(self, mission: ScoutMission) -> None:
        self.missions[mission.mission_id] = mission
        if mission.mission_id not in self.active_ids:
            self.active_ids.append(mission.mission_id)
            self.active_ids.sort()

    def signature(self) -> str:
        canonical = {
            mission_id: {
                "status": mission.status.value,
                "intent": mission.intent.value,
                "origin": mission.origin_node_id,
                "current": mission.current_node_id,
                "target": mission.target_node_id,
                "heading": mission.heading_deg,
                "max_days": mission.max_days,
                "party": list(mission.party_agent_ids),
                "supplies": dict(sorted(mission.supplies.items())),
                "risk": mission.risk_budget,
                "start": mission.start_day,
                "last_step": mission.last_step_day,
                "elapsed": mission.days_elapsed,
                "discoveries": [dict(sorted(d.items())) for d in mission.discoveries],
                "notes": dict(sorted(mission.notes.items())),
            }
            for mission_id, mission in sorted(self.missions.items())
        }
        payload = _canonical_json(canonical)
        return sha256(payload.encode("utf-8")).hexdigest()


def ensure_scout_missions(world) -> ScoutMissionLedger:
    ledger: ScoutMissionLedger = getattr(world, "scout_missions", None) or ScoutMissionLedger()
    world.scout_missions = ledger
    if getattr(world, "next_mission_seq", None) is None:
        world.next_mission_seq = 0
    return ledger


__all__ = [
    "MissionIntent",
    "MissionStatus",
    "ScoutMission",
    "ScoutMissionLedger",
    "ensure_scout_missions",
]
