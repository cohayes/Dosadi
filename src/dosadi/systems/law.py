"""Law and contract progression."""

from __future__ import annotations

from dataclasses import dataclass

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..simulation.scheduler import Phase, SimulationClock


@dataclass
class LawSystem(SimulationSystem):
    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.REFLECTION, self.on_reflection)

    def on_reflection(self, clock: SimulationClock) -> None:
        self.reseed(clock.current_tick)
        for case in self.world.cases.values():
            if case.outcome is None:
                case.outcome = "RESTORATIVE"
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


__all__ = ["LawSystem"]

