"""Governance updates: legitimacy and corruption rollups."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..simulation.scheduler import Phase, SimulationClock


@dataclass
class GovernanceSystem(SimulationSystem):
    incidents: Dict[str, Dict[str, object]] = field(default_factory=dict)

    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.WARD_GOVERNANCE, self.on_governance)

    def on_governance(self, clock: SimulationClock) -> None:
        self.reseed(clock.current_tick)
        self._update_incidents(clock)
        for ward in self.world.wards.values():
            faction_id = ward.governor_faction
            if not faction_id or faction_id not in self.world.factions:
                continue
            faction = self.world.factions[faction_id]
            stress = ward.environment.stress
            delta = -0.0005 * (stress - 40.0) / 40.0
            faction.metrics.gov.apply_delta(legitimacy=delta)
            if abs(delta) > 1e-4:
                self.bus.publish(
                    Event(
                        id=f"legitimacy:{faction.id}:{clock.current_tick}",
                        type="LegitimacyRecalculated",
                        tick=clock.current_tick,
                        ttl=300,
                        payload={
                            "faction": faction.id,
                            "ward": ward.id,
                            "legitimacy": faction.metrics.gov.legitimacy,
                        },
                        priority=EventPriority.NORMAL,
                        emitter="GovernanceSystem",
                    )
                )
            if self.rng.random() < 0.01:
                self._spawn_incident(clock, ward.id, faction.id)

    def _spawn_incident(self, clock: SimulationClock, ward_id: str, faction_id: str) -> None:
        incident_id = f"infosec:{ward_id}:{clock.current_tick}"
        severity = self.rng.choice(["LOW", "MEDIUM", "HIGH"])
        record = {
            "id": incident_id,
            "ward": ward_id,
            "faction": faction_id,
            "stage": 0,
            "severity": severity,
            "last_stage_tick": clock.current_tick,
            "stage_duration": 600,
        }
        self.incidents[incident_id] = record
        self.bus.publish(
            Event(
                id=f"{incident_id}:0",
                type="InfosecIncident",
                tick=clock.current_tick,
                ttl=600,
                payload={
                    "incident_id": incident_id,
                    "stage": "DETECTED",
                    "severity": severity,
                    "ward": ward_id,
                    "faction": faction_id,
                },
                priority=EventPriority.HIGH,
                emitter="GovernanceSystem",
            )
        )

    def _update_incidents(self, clock: SimulationClock) -> None:
        stages = ["DETECTED", "INVESTIGATING", "BREACH", "CONTAINED"]
        for incident_id, record in list(self.incidents.items()):
            stage = int(record["stage"])
            if stage >= len(stages) - 1:
                continue
            if clock.current_tick - int(record["last_stage_tick"]) < int(record["stage_duration"]):
                continue
            stage += 1
            record["stage"] = stage
            record["last_stage_tick"] = clock.current_tick
            event_type = "InfosecIncidentEscalated"
            if stage == len(stages) - 1:
                event_type = "InfosecIncidentContained"
            self.bus.publish(
                Event(
                    id=f"{incident_id}:{stage}",
                    type=event_type,
                    tick=clock.current_tick,
                    ttl=600,
                    payload={
                        "incident_id": incident_id,
                        "stage": stages[stage],
                        "severity": record["severity"],
                        "ward": record["ward"],
                        "faction": record["faction"],
                    },
                    priority=EventPriority.HIGH,
                    emitter="GovernanceSystem",
                )
            )
            if event_type == "InfosecIncidentContained":
                del self.incidents[incident_id]


__all__ = ["GovernanceSystem"]

