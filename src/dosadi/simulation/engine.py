"""High level orchestration for the Dosadi simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from ..actions.base import ActionProcessor
from ..actions.verbs import register_default_verbs
from ..event import EventBus
from ..registry import SharedVariableRegistry, default_registry
from ..state import WorldState
from ..systems import (
    EnvironmentSystem,
    EconomySystem,
    GovernanceSystem,
    LawSystem,
    MaintenanceSystem,
    RumorSystem,
    StressSystem,
)
from .scheduler import Phase, SimulationClock, SimulationScheduler


@dataclass
class SimulationEngine:
    """Container wiring together the scheduler and subsystems."""

    world: WorldState
    scheduler: SimulationScheduler = field(default_factory=SimulationScheduler)
    bus: EventBus = field(default_factory=EventBus)
    registry: SharedVariableRegistry = field(default_factory=default_registry)

    def __post_init__(self) -> None:
        self.scheduler.attach_bus(self.bus)
        self.scheduler.attach_registry(self.registry)
        self.action_processor = ActionProcessor(self.world, self.bus)
        register_default_verbs(self.action_processor)
        self.systems = [
            EnvironmentSystem(self.world, self.bus, rng_seed=1, registry=self.registry),
            EconomySystem(self.world, self.bus, rng_seed=2, registry=self.registry),
            GovernanceSystem(self.world, self.bus, rng_seed=3, registry=self.registry),
            MaintenanceSystem(self.world, self.bus, rng_seed=4, registry=self.registry),
            RumorSystem(self.world, self.bus, rng_seed=5, registry=self.registry),
            StressSystem(self.world, self.bus, rng_seed=7, registry=self.registry),
            LawSystem(self.world, self.bus, rng_seed=6, registry=self.registry),
        ]
        for system in self.systems:
            for phase, handler in system.phase_handlers().items():
                self.scheduler.register_handler(phase, handler)

    def run(self, ticks: int) -> None:
        for _ in range(ticks):
            self.scheduler.run_tick()
            self.world.advance_tick()
            self.registry.set("tick", float(self.world.tick))
            self.registry.set("t_min", float(self.world.minute))
            self.registry.set("t_day", float(self.world.day))
            self.registry.decay_all()
            self.action_processor.run(self.world.tick)
            self.bus.dispatch()


__all__ = ["SimulationEngine"]

