"""Maintenance and fault progression."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

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
        ledger = self.world.suit_service_ledger
        for agent in self.world.agents.values():
            telemetry = {
                "integrity": agent.suit.integrity,
                "seal": agent.suit.seal,
                "comfort": agent.suit.comfort,
                "heat_rating": agent.suit.ratings.get("heat", 0.5),
            }
            wear_factor = max(0.0, 1.0 - agent.suit.integrity)
            seal_penalty = max(0.0, 1.0 - agent.suit.seal)
            parts_cost = 40.0 * wear_factor + 25.0 * seal_penalty
            deferred = agent.suit.integrity < 0.4 or agent.suit.seal < 0.5
            ledger.record(
                tick=clock.current_tick,
                agent_id=agent.id,
                faction_id=agent.faction,
                ward_id=agent.ward,
                telemetry=telemetry,
                parts_cost=parts_cost,
                deferred=deferred,
            )
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
        if self.registry is not None:
            summary = ledger.summary()
            self.registry.set("infra.service.parts", summary["parts_cost"])
            self.registry.set("infra.service.deferred", summary["deferred"])
            if self.world.wards:
                avg_maintenance = mean(
                    ward.infrastructure.maintenance_index for ward in self.world.wards.values()
                )
                self.registry.set("infra.M", avg_maintenance)


__all__ = ["MaintenanceSystem"]

