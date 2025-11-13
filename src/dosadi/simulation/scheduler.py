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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum, auto
import heapq
from time import perf_counter
from typing import Callable, DefaultDict, Iterable, List, MutableMapping, Optional, Tuple

TickHandler = Callable[["SimulationClock"], None]
DelayedHandler = Callable[["SimulationClock"], None]


@dataclass(frozen=True)
class HandlerMetrics:
    """Execution metadata captured for each handler invocation."""

    name: str
    phase: "Phase"
    cadence: int
    duration_ms: float
    ran: bool


@dataclass(frozen=True)
class PhaseMetrics:
    """Aggregated metrics for a phase within a tick."""

    phase: "Phase"
    handlers: Tuple[HandlerMetrics, ...]
    bucket_count: int
    parallel_buckets: int


@dataclass(frozen=True)
class TickMetrics:
    """Summary metrics for a completed tick."""

    tick: int
    phases: Tuple[PhaseMetrics, ...]


@dataclass(slots=True)
class _HandlerRegistration:
    """Store registration metadata for a handler."""

    handler: TickHandler
    cadence: int
    reads: frozenset[str]
    writes: frozenset[str]
    name: str
    order: int

    @property
    def has_dependency_metadata(self) -> bool:
        return bool(self.reads or self.writes)


@dataclass(slots=True)
class _Bucket:
    handlers: List[_HandlerRegistration]
    reads: set[str]
    writes: set[str]
    allows_parallel: bool


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
    phase_handlers: DefaultDict[Phase, List[_HandlerRegistration]] = field(
        default_factory=lambda: defaultdict(list)
    )
    time_dilation: MutableMapping[str, float] = field(default_factory=dict)
    max_workers: Optional[int] = None
    _delayed_events: List[Tuple[int, int, DelayedHandler]] = field(default_factory=list)
    _delayed_counter: int = 0
    _registration_counter: int = 0
    _last_tick_metrics: Optional[TickMetrics] = None

    def register_handler(
        self,
        phase: Phase,
        handler: TickHandler,
        *,
        cadence: int = 1,
        reads: Optional[Iterable[str]] = None,
        writes: Optional[Iterable[str]] = None,
        name: Optional[str] = None,
    ) -> None:
        """Attach ``handler`` to a phase with optional dependency metadata.

        ``cadence`` controls how often the handler is invoked (``1`` indicates
        every tick).  ``reads`` and ``writes`` define the handler's declared data
        dependencies and enable the scheduler to place it into a parallel bucket
        when it does not conflict with other handlers.  Missing dependency
        information results in conservative sequential execution.
        """

        if cadence <= 0:
            raise ValueError("cadence must be positive")
        self._registration_counter += 1
        registration = _HandlerRegistration(
            handler=handler,
            cadence=cadence,
            reads=frozenset(reads or ()),
            writes=frozenset(writes or ()),
            name=name or getattr(handler, "__name__", f"handler_{self._registration_counter}"),
            order=self._registration_counter,
        )
        self.phase_handlers[phase].append(registration)

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

        phase_metrics: List[PhaseMetrics] = []
        for phase in Phase.ordered():
            metrics = self._execute_phase(phase, snapshot)
            phase_metrics.append(metrics)

        self._last_tick_metrics = TickMetrics(
            tick=self.clock.current_tick, phases=tuple(phase_metrics)
        )

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

    def last_tick_metrics(self) -> Optional[TickMetrics]:
        """Return the metrics generated for the most recent tick."""

        return self._last_tick_metrics

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _execute_phase(self, phase: Phase, snapshot: SimulationClock) -> PhaseMetrics:
        registrations = self.phase_handlers.get(phase, ())
        if not registrations:
            return PhaseMetrics(
                phase=phase, handlers=tuple(), bucket_count=0, parallel_buckets=0
            )

        due: List[_HandlerRegistration] = [
            registration
            for registration in registrations
            if snapshot.current_tick % registration.cadence == 0
        ]
        if not due:
            return PhaseMetrics(
                phase=phase, handlers=tuple(), bucket_count=0, parallel_buckets=0
            )

        buckets = self._bucketize(sorted(due, key=lambda reg: reg.order))
        handler_metrics: List[HandlerMetrics] = []
        parallel_buckets = 0
        for bucket in buckets:
            if bucket.allows_parallel and len(bucket.handlers) > 1:
                parallel_buckets += 1
            handler_metrics.extend(self._run_bucket(bucket, snapshot, phase))

        return PhaseMetrics(
            phase=phase,
            handlers=tuple(handler_metrics),
            bucket_count=len(buckets),
            parallel_buckets=parallel_buckets,
        )

    def _bucketize(self, registrations: List[_HandlerRegistration]) -> List[_Bucket]:
        buckets: List[_Bucket] = []
        for registration in registrations:
            placed = False
            for bucket in buckets:
                if not self._has_conflict(bucket, registration):
                    bucket.handlers.append(registration)
                    bucket.reads.update(registration.reads)
                    bucket.writes.update(registration.writes)
                    if not registration.has_dependency_metadata:
                        bucket.allows_parallel = False
                    placed = True
                    break
            if not placed:
                buckets.append(
                    _Bucket(
                        handlers=[registration],
                        reads=set(registration.reads),
                        writes=set(registration.writes),
                        allows_parallel=registration.has_dependency_metadata,
                    )
                )
        return buckets

    def _has_conflict(
        self, bucket: _Bucket, registration: _HandlerRegistration
    ) -> bool:
        if not bucket.allows_parallel or not registration.has_dependency_metadata:
            return True
        if bucket.writes & registration.reads:
            return True
        if bucket.reads & registration.writes:
            return True
        if bucket.writes & registration.writes:
            return True
        return False

    def _run_bucket(
        self, bucket: _Bucket, snapshot: SimulationClock, phase: Phase
    ) -> List[HandlerMetrics]:
        if bucket.allows_parallel and len(bucket.handlers) > 1:
            max_workers = self.max_workers or len(bucket.handlers)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(self._execute_handler, registration, snapshot, phase)
                    for registration in bucket.handlers
                ]
                results = [future.result() for future in futures]
            # Ensure deterministic ordering by original registration order.
            results.sort(key=lambda entry: entry[0])
            return [metrics for _, metrics in results]

        results = [
            self._execute_handler(registration, snapshot, phase)
            for registration in bucket.handlers
        ]
        return [metrics for _, metrics in results]

    def _execute_handler(
        self, registration: _HandlerRegistration, snapshot: SimulationClock, phase: Phase
    ) -> Tuple[int, HandlerMetrics]:
        start = perf_counter()
        registration.handler(snapshot)
        end = perf_counter()
        metrics = HandlerMetrics(
            name=registration.name,
            phase=phase,
            cadence=registration.cadence,
            duration_ms=(end - start) * 1000.0,
            ran=True,
        )
        return registration.order, metrics


__all__ = [
    "DelayedHandler",
    "HandlerMetrics",
    "PhaseMetrics",
    "Phase",
    "SimulationClock",
    "SimulationScheduler",
    "TickHandler",
    "TickMetrics",
]
