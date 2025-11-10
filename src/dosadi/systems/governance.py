"""Governance updates: legitimacy and corruption rollups."""

from __future__ import annotations

from dataclasses import dataclass

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..simulation.scheduler import Phase, SimulationClock


@dataclass
class GovernanceSystem(SimulationSystem):
    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.WARD_GOVERNANCE, self.on_governance)

    def on_governance(self, clock: SimulationClock) -> None:
        self.reseed(clock.current_tick)
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


__all__ = ["GovernanceSystem"]

