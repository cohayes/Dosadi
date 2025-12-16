from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import json
from hashlib import sha256
from typing import Dict, List


class WorldPhase(IntEnum):
    PHASE0 = 0
    PHASE1 = 1
    PHASE2 = 2


@dataclass(slots=True)
class PhaseConfig:
    min_days_in_phase0: int = 30
    min_days_in_phase1: int = 60
    hysteresis_days: int = 30
    water_per_capita_p0_to_p1: float = 2.0
    water_per_capita_p1_to_p2: float = 1.0
    logistics_backlog_p0_to_p1: int = 10
    logistics_backlog_p1_to_p2: int = 50
    maintenance_backlog_p1_to_p2: int = 20
    require_multiple_signals: bool = True


@dataclass(slots=True)
class KPISnapshot:
    day: int
    water_total: float
    population: int
    water_per_capita: float
    logistics_backlog: int
    maintenance_backlog: int
    notes: Dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class PhaseState:
    phase: WorldPhase = WorldPhase.PHASE0
    phase_day: int = 0
    last_eval_day: int = -1
    history: List[dict] = field(default_factory=list)
    kpi_ring: List[KPISnapshot] = field(default_factory=list)

    def signature(self) -> str:
        canonical = {
            "phase": int(self.phase),
            "phase_day": self.phase_day,
            "last_eval_day": self.last_eval_day,
            "history": [dict(entry) for entry in self.history],
            "kpi_ring": [
                {
                    "day": snap.day,
                    "water_total": round(snap.water_total, 6),
                    "population": snap.population,
                    "water_per_capita": round(snap.water_per_capita, 6),
                    "logistics_backlog": snap.logistics_backlog,
                    "maintenance_backlog": snap.maintenance_backlog,
                    "notes": dict(sorted(snap.notes.items())),
                }
                for snap in self.kpi_ring
            ],
        }
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "KPISnapshot",
    "PhaseConfig",
    "PhaseState",
    "WorldPhase",
]
