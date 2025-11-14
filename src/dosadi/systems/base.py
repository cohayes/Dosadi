"""Base classes shared by simulation subsystems."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Callable, Dict, Iterable, Mapping, MutableMapping, Optional

from ..event import EventBus
from ..runtime.timebase import Phase
from ..simulation.scheduler import SimulationClock
from ..state import WorldState
from ..registry import SharedVariableRegistry


PhaseHandler = Callable[[SimulationClock], None]


@dataclass
class SimulationSystem:
    world: WorldState
    bus: EventBus
    rng_seed: int
    registry: Optional[SharedVariableRegistry] = None

    def __post_init__(self) -> None:
        self.rng = Random(self.rng_seed)
        self.handlers: Dict[Phase, PhaseHandler] = {}

    def register(self, phase: Phase, handler: PhaseHandler) -> None:
        self.handlers[phase] = handler

    def phase_handlers(self) -> Mapping[Phase, PhaseHandler]:
        return dict(self.handlers)

    def reseed(self, tick: int) -> None:
        self.rng.seed(hash((self.rng_seed, tick)))


__all__ = ["SimulationSystem"]

