"""Core scheduling primitives for the Dosadi simulation.

This module implements the tick/turn/cycle/epoch/era cascade described in
``docs/Dosadi_Temporal_Simulation_v1.md``.  The scheduler is intentionally
minimal but provides the following pieces of infrastructure:

* A ``SimulationClock`` that converts between raw ticks and higher-order units.
* Enumeration of the canonical update phases executed each tick.
* A ``SimulationScheduler`` that executes registered callables in the mandated
  phase order, manages delayed events, and exposes hooks for time dilation.

Future systems (economy, rumor network, governance, etc.) can register phase
handlers or enqueue delayed callbacks without needing to coordinate on shared
state or bespoke timing logic.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
import heapq
from typing import Callable, DefaultDict, Iterable, List, MutableMapping, Tuple

TickHandler = Callable[["SimulationClock"], None]
DelayedHandler = Callable[["SimulationClock"], None]


class Phase(Enum):
    """Simulation phases executed in fixed order every tick."""

    WELL_AND_KING = auto()
    WARD_GOVERNANCE = auto()
    FACTION_OPERATIONS = auto()
    AGENT_ACTIVITY = auto()
    ENVIRONMENTAL_UPDATE = auto()
    RUMOR_AND_INFORMATION = auto()
    REFLECTION = auto()

    @classmethod
    def ordered(cls) -> Iterable["Phase"]:
        """Return phases in canonical execution order."""

        return (
            cls.WELL_AND_KING,
            cls.WARD_GOVERNANCE,
            cls.FACTION_OPERATIONS,
            cls.AGENT_ACTIVITY,
            cls.ENVIRONMENTAL_UPDATE,
            cls.RUMOR_AND_INFORMATION,
            cls.REFLECTION,
        )


@dataclass(slots=True)
class SimulationClock:
    """Track the simulation timeline and expose conversion helpers.

    The base unit is a *tick* which represents 0.6 seconds of world time as
    described in the temporal systems document.  Higher-order units are
    represented as integer tick counts to avoid precision drift.
    """

    tick_length_seconds: float = 0.6
    ticks_per_turn: int = 100
    ticks_per_cycle: int = 144_000
    cycles_per_epoch: int = 7
    epochs_per_era: int = 4
    current_tick: int = 0

    def advance(self, ticks: int = 1) -> None:
        """Advance the clock by ``ticks``."""

        if ticks < 0:
            raise ValueError("ticks must be non-negative")
        self.current_tick += ticks

    @property
    def current_turn(self) -> int:
        return self.current_tick // self.ticks_per_turn

    @property
    def current_cycle(self) -> int:
        return self.current_tick // self.ticks_per_cycle

    @property
    def current_epoch(self) -> int:
        return self.current_cycle // self.cycles_per_epoch

    @property
    def current_era(self) -> int:
        return self.current_epoch // self.epochs_per_era

    def ticks_until_turn_boundary(self) -> int:
        return self.ticks_per_turn - (self.current_tick % self.ticks_per_turn)

    def ticks_until_cycle_boundary(self) -> int:
        return self.ticks_per_cycle - (self.current_tick % self.ticks_per_cycle)

    def copy(self) -> "SimulationClock":
        """Return a snapshot of the current clock state."""

        return SimulationClock(
            tick_length_seconds=self.tick_length_seconds,
            ticks_per_turn=self.ticks_per_turn,
            ticks_per_cycle=self.ticks_per_cycle,
            cycles_per_epoch=self.cycles_per_epoch,
            epochs_per_era=self.epochs_per_era,
            current_tick=self.current_tick,
        )


@dataclass
class SimulationScheduler:
    """Execute registered handlers following the Dosadi temporal cascade."""

    clock: SimulationClock = field(default_factory=SimulationClock)
    phase_handlers: DefaultDict[Phase, List[TickHandler]] = field(
        default_factory=lambda: defaultdict(list)
    )
    time_dilation: MutableMapping[str, float] = field(default_factory=dict)
    _delayed_events: List[Tuple[int, int, DelayedHandler]] = field(default_factory=list)
    _delayed_counter: int = 0

    def register_handler(self, phase: Phase, handler: TickHandler) -> None:
        """Attach ``handler`` to a phase.

        Handlers receive the *current* clock snapshot allowing them to respond to
        the precise tick at which they were executed.  Handlers should be
        idempotent and capable of being called every tick unless they consult the
        clock to gate behavior at longer intervals.
        """

        self.phase_handlers[phase].append(handler)

    def schedule_event(
        self, delay_ticks: int, handler: DelayedHandler, *, priority: int = 0
    ) -> None:
        """Schedule ``handler`` to run after ``delay_ticks``.

        Events are stored in a priority queue keyed by their target tick.
        ``priority`` acts as a tiebreaker when multiple events land on the same
        tick.
        """

        if delay_ticks < 0:
            raise ValueError("delay_ticks must be non-negative")
        run_tick = self.clock.current_tick + delay_ticks
        self._delayed_counter += 1
        heapq.heappush(
            self._delayed_events, (run_tick, priority, self._delayed_counter, handler)
        )

    def set_time_dilation(self, scope: str, coefficient: float) -> None:
        """Record a time dilation coefficient for a logical scope.

        The scheduler does not interpret coefficients directly; instead it
        exposes them via :meth:`get_time_dilation` so that subsystems can adjust
        their fidelity.  ``coefficient`` must be positive.
        """

        if coefficient <= 0:
            raise ValueError("coefficient must be positive")
        self.time_dilation[scope] = coefficient

    def get_time_dilation(self, scope: str) -> float:
        """Return the dilation coefficient for ``scope`` or 1.0 if unset."""

        return self.time_dilation.get(scope, 1.0)

    def run_tick(self) -> None:
        """Advance the clock by one tick and execute the cascade."""

        # Advance first so that handlers observe the new tick when executed.
        self.clock.advance(1)
        snapshot = self.clock.copy()

        self._run_due_events(snapshot)

        for phase in Phase.ordered():
            for handler in self.phase_handlers.get(phase, ()):  # type: ignore[arg-type]
                handler(snapshot)

    def run(self, ticks: int) -> None:
        """Execute ``ticks`` ticks."""

        if ticks < 0:
            raise ValueError("ticks must be non-negative")
        for _ in range(ticks):
            self.run_tick()

    def _run_due_events(self, snapshot: SimulationClock) -> None:
        """Run all delayed events scheduled for the current tick."""

        while self._delayed_events and self._delayed_events[0][0] <= snapshot.current_tick:
            _, _, _, handler = heapq.heappop(self._delayed_events)
            handler(snapshot)


__all__ = [
    "DelayedHandler",
    "Phase",
    "SimulationClock",
    "SimulationScheduler",
    "TickHandler",
]
