"""Rumor propagation and memory decay."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..runtime.timebase import Phase
from ..simulation.scheduler import SimulationClock


@dataclass
class RumorSystem(SimulationSystem):
    incident_cache: Dict[str, Dict[str, object]] = field(default_factory=dict)

    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.SOCIAL, self.on_rumor)
        self.bus.subscribe(self._on_infosec_event, predicate=self._is_infosec_event)

    def on_rumor(self, clock: SimulationClock) -> None:
        self.reseed(clock.current_tick)
        for agent in self.world.agents.values():
            if not agent.memory.events:
                continue
            if self.rng.random() < 0.05:
                rumor_id = agent.memory.events[-1]
                self.bus.publish(
                    Event(
                        id=f"rumor:{rumor_id}:{clock.current_tick}",
                        type="RumorEmitted",
                        tick=clock.current_tick,
                        ttl=120,
                        payload={"agent": agent.id, "rumor": rumor_id},
                        priority=EventPriority.LOW,
                        emitter="RumorSystem",
                    )
                )
            agent.memory.decay(cred_lambda=0.97, belief_lambda=0.98, salience_lambda=0.99)
        self._seed_pending_incident_rumors(clock)

    def _is_infosec_event(self, event: Event) -> bool:
        return event.type in {
            "InfosecIncident",
            "InfosecIncidentEscalated",
            "InfosecIncidentContained",
        }

    def _on_infosec_event(self, event: Event) -> None:
        payload = event.payload
        incident_id = str(payload.get("incident_id"))
        severity = str(payload.get("severity", "LOW"))
        self.incident_cache[incident_id] = {
            "event_id": event.id,
            "severity": severity,
            "stage": payload.get("stage", ""),
            "tick": event.tick,
        }
        severity_factor = {
            "LOW": 0.98,
            "MEDIUM": 0.95,
            "HIGH": 0.9,
            "CRITICAL": 0.85,
        }.get(severity.upper(), 0.95)
        if self.registry is not None:
            current = self.registry.get("rumor.Cred")
            self.registry.set("rumor.Cred", max(0.0, current * severity_factor))
        rumor_id = f"infosec:{incident_id}:{event.tick}"
        self.bus.publish(
            Event(
                id=rumor_id,
                type="RumorSeeded",
                tick=event.tick,
                ttl=720,
                payload={
                    "incident_id": incident_id,
                    "severity": severity,
                    "stage": payload.get("stage", ""),
                },
                priority=EventPriority.NORMAL,
                emitter="RumorSystem",
            )
        )
        for agent in self.world.agents.values():
            agent.memory.events.append(rumor_id)
            if len(agent.memory.events) > 50:
                del agent.memory.events[0]

    def _seed_pending_incident_rumors(self, clock: SimulationClock) -> None:
        if not self.incident_cache:
            return
        for incident_id, data in list(self.incident_cache.items()):
            if clock.current_tick - int(data.get("tick", 0)) > 3600:
                del self.incident_cache[incident_id]


__all__ = ["RumorSystem"]

