"""Law and contract progression."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..simulation.scheduler import Phase, SimulationClock
from ..state import CaseState


@dataclass
class LawSystem(SimulationSystem):
    incident_cases: Dict[str, CaseState] = field(default_factory=dict)

    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.REFLECTION, self.on_reflection)
        self.bus.subscribe(self._on_infosec_event, predicate=self._is_infosec_event)

    def on_reflection(self, clock: SimulationClock) -> None:
        self.reseed(clock.current_tick)
        for incident_id, case in self.incident_cases.items():
            if case.outcome is None:
                for party in case.parties:
                    faction = self.world.factions.get(party)
                    if faction is None:
                        continue
                    faction.metrics.law.retributive_index = min(
                        1.0, faction.metrics.law.retributive_index + 0.01
                    )
                    faction.metrics.law.restorative_ratio = max(
                        0.0, faction.metrics.law.restorative_ratio - 0.01
                    )
                case.proceedings.append(
                    {
                        "tick": clock.current_tick,
                        "note": f"Incident {incident_id} ongoing",
                    }
                )
            elif case.closed_tick is None:
                case.closed_tick = clock.current_tick
                self.bus.publish(
                    Event(
                        id=f"case:{case.id}:{clock.current_tick}",
                        type="ArbiterRulingIssued",
                        tick=clock.current_tick,
                        ttl=600,
                        payload={"case": case.id, "outcome": case.outcome},
                        priority=EventPriority.HIGH,
                        emitter="LawSystem",
                    )
                )

    def _is_infosec_event(self, event: Event) -> bool:
        return event.type in {
            "InfosecIncident",
            "InfosecIncidentEscalated",
            "InfosecIncidentContained",
        }

    def _on_infosec_event(self, event: Event) -> None:
        payload = event.payload
        incident_id = str(payload.get("incident_id"))
        case_id = f"case:{incident_id}"
        stage = payload.get("stage", "")
        severity = payload.get("severity", "LOW")
        faction = payload.get("faction")
        case = self.incident_cases.get(incident_id)
        if case is None:
            case = CaseState(
                id=case_id,
                contract_id=None,
                arbiter_tier="INFOSEC",
                parties=tuple(filter(None, [faction])) or tuple(),
            )
            self.world.cases[case_id] = case
            self.incident_cases[incident_id] = case
        if event.type == "InfosecIncidentContained":
            outcome = "RESTORATIVE" if severity != "CRITICAL" else "RETRIBUTIVE"
            case.outcome = outcome
        else:
            case.outcome = None
        case.evidence.append(
            {
                "stage": stage,
                "severity": severity,
                "tick": event.tick,
            }
        )


__all__ = ["LawSystem"]

