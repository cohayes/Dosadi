"""Rumor propagation and memory decay."""

from __future__ import annotations

from dataclasses import dataclass

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..simulation.scheduler import Phase, SimulationClock


@dataclass
class RumorSystem(SimulationSystem):
    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.RUMOR_AND_INFORMATION, self.on_rumor)

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


__all__ = ["RumorSystem"]

