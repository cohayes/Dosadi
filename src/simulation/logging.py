"""Utilities for collecting simulation telemetry.

This module provides lightweight data structures and helper
classes that capture what happened during a simulation run.
The resulting logs can be exported to JSON for downstream
analysis, RL training, or narrative replay tooling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union
import json


@dataclass
class AgentTickRecord:
    """Snapshot of a single agent's action for a tick."""

    tick: int
    facility: str
    agent_type: str
    agent_id: int
    action: str
    mood: Dict[str, float] = field(default_factory=dict)


@dataclass
class FacilityTickRecord:
    """Aggregated output for a facility on a tick."""

    tick: int
    facility: str
    efficiency: float
    output: Dict[str, float]
    resources: Dict[str, float]
    events: List[str] = field(default_factory=list)


@dataclass
class DistrictTickRecord:
    """District level summary for each tick."""

    tick: int
    production: float
    quota_ratio: float
    faction_power: Dict[str, float]
    weather: Dict[str, float]


class SimulationLogger:
    """Centralized collector for simulation telemetry."""

    def __init__(self):
        self.agent_ticks: List[AgentTickRecord] = []
        self.facility_ticks: List[FacilityTickRecord] = []
        self.district_ticks: List[DistrictTickRecord] = []

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def record_agent_tick(
        self,
        *,
        tick: int,
        facility: str,
        agent_type: str,
        agent_id: int,
        action: str,
        mood: Dict[str, float],
    ):
        self.agent_ticks.append(
            AgentTickRecord(
                tick=tick,
                facility=facility,
                agent_type=agent_type,
                agent_id=agent_id,
                action=action,
                mood=dict(mood),
            )
        )

    def record_facility_tick(
        self,
        *,
        tick: int,
        facility: str,
        efficiency: float,
        output: Dict[str, float],
        resources: Dict[str, float],
        events: Optional[List[str]] = None,
    ):
        self.facility_ticks.append(
            FacilityTickRecord(
                tick=tick,
                facility=facility,
                efficiency=efficiency,
                output=dict(output),
                resources=dict(resources),
                events=list(events) if events else [],
            )
        )

    def record_district_tick(
        self,
        *,
        tick: int,
        production: float,
        quota_ratio: float,
        faction_power: Dict[str, float],
        weather: Dict[str, float],
    ):
        self.district_ticks.append(
            DistrictTickRecord(
                tick=tick,
                production=production,
                quota_ratio=quota_ratio,
                faction_power=dict(faction_power),
                weather=dict(weather),
            )
        )

    # ------------------------------------------------------------------
    # Export utilities
    # ------------------------------------------------------------------

    def export(self) -> Dict[str, List[Dict]]:
        """Return a dict of raw log data."""

        return {
            "agent_ticks": [asdict(rec) for rec in self.agent_ticks],
            "facility_ticks": [asdict(rec) for rec in self.facility_ticks],
            "district_ticks": [asdict(rec) for rec in self.district_ticks],
        }

    def to_json(self, path: Union[Path, str], *, indent: int = 2):
        """Persist logs to a JSON file."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.export(), indent=indent))

    def reset(self):
        """Clear all stored logs."""

        self.agent_ticks.clear()
        self.facility_ticks.clear()
        self.district_ticks.clear()
