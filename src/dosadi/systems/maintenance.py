"""Maintenance and fault progression."""

from __future__ import annotations

from dataclasses import dataclass

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..simulation.scheduler import Phase, SimulationClock


@dataclass
class MaintenanceSystem(SimulationSystem):
    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.FACTION_OPERATIONS, self.on_maintenance)

    def on_maintenance(self, clock: SimulationClock) -> None:
        self.reseed(clock.current_tick)
        for ward in self.world.wards.values():
            infra = ward.infrastructure
            decay = 0.0005 + 0.001 * ward.environment.stress / 100.0
            infra.degrade(decay)
            if infra.maintenance_index < 0.4:
                subsystem = self.rng.choice(list(infra.subsystems))
                infra.subsystems[subsystem] = "WARN"
                self.bus.publish(
                    Event(
                        id=f"maintenance:{ward.id}:{subsystem}:{clock.current_tick}",
                        type="MaintenanceFault",
                        tick=clock.current_tick,
                        ttl=600,
                        payload={"ward": ward.id, "subsystem": subsystem},
                        priority=EventPriority.HIGH,
                        emitter="MaintenanceSystem",
                    )
                )


__all__ = ["MaintenanceSystem"]

