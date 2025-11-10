"""Environment system implementation."""

from __future__ import annotations

from dataclasses import dataclass

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..simulation.scheduler import Phase, SimulationClock


@dataclass
class EnvironmentSystem(SimulationSystem):
    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.ENVIRONMENTAL_UPDATE, self.on_environment)

    def on_environment(self, clock: SimulationClock) -> None:
        self.reseed(clock.current_tick)
        for ward in self.world.wards.values():
            env = ward.environment
            infra = ward.infrastructure
            baseline = 35.0 - 0.2 * (ward.ring - 1)
            variability = self.rng.uniform(-1.5, 1.5)
            env.temperature = max(-20.0, min(80.0, baseline + variability))
            env.humidity = max(0.05, min(5.0, env.humidity + self.rng.uniform(-0.05, 0.05)))
            env.oxygen = max(0.05, min(0.25, env.oxygen + (infra.maintenance_index - 0.7) * 0.005))
            env.radiation = max(0.5, min(10.0, env.radiation + (1.0 - infra.maintenance_index) * 0.02))
            env.water_loss = max(0.0001, min(0.05, env.water_loss * (1.0 + self.rng.uniform(-0.02, 0.02))))
            env.stress = env.compute_stress()

            if env.stress > 70.0:
                self.bus.publish(
                    Event(
                        id=f"event:heat:{ward.id}:{clock.current_tick}",
                        type="HeatSurge",
                        tick=clock.current_tick,
                        ttl=60,
                        payload={
                            "ward": ward.id,
                            "temperature": env.temperature,
                            "stress": env.stress,
                        },
                        priority=EventPriority.HIGH,
                        emitter="EnvironmentSystem",
                    )
                )


__all__ = ["EnvironmentSystem"]

