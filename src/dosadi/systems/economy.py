"""Economic subsystem covering credits, barrels, and conservation."""

from __future__ import annotations

from dataclasses import dataclass

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..simulation.scheduler import Phase, SimulationClock


@dataclass
class EconomySystem(SimulationSystem):
    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.WELL_AND_KING, self.on_well)
        self.register(Phase.FACTION_OPERATIONS, self.on_factions)

    def on_well(self, clock: SimulationClock) -> None:
        self.reseed(clock.current_tick)
        if clock.current_tick % 144_000 != 0:
            return
        wards = list(self.world.wards.values())
        if not wards:
            return
        total_bias = sum(1.0 / (ward.ring or 1) for ward in wards)
        allocation = 1000.0
        for ward in wards:
            share = allocation * (1.0 / (ward.ring or 1)) / total_bias
            ward.stocks.delta_water(share)
            self.bus.publish(
                Event(
                    id=f"barrel:{ward.id}:{clock.current_tick}",
                    type="BarrelCascadeIssued",
                    tick=clock.current_tick,
                    ttl=600,
                    payload={"ward": ward.id, "water": share},
                    priority=EventPriority.NORMAL,
                    emitter="EconomySystem",
                )
            )

    def on_factions(self, clock: SimulationClock) -> None:
        self.reseed(clock.current_tick)
        for faction in self.world.factions.values():
            legit = faction.metrics.gov.legitimacy
            corruption = faction.metrics.gov.corruption
            delta = (legit - corruption) * 0.001
            faction.assets.delta_credit(faction.id, max(0.0, delta))
            faction.metrics.econ.reliability = max(0.0, min(1.0, faction.metrics.econ.reliability * 0.99 + 0.01))


__all__ = ["EconomySystem"]

