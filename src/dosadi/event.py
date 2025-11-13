"""Event bus and message primitives for the Dosadi simulation.

The design follows the requirements from the design documentation:

* Events are immutable records with TTL handling and priority queues
  (see ``docs/Dosadi_Event_and_Message_Taxonomy_v1.md`` and
  ``docs/Dosadi_Tick_Loop_and_Scheduling_v1.md``).
* Emission is deterministic – the order of delivery is derived from
  priority first and insertion order second.
* Consumers subscribe with callables that receive events matching an
  optional predicate.  The bus stores all emitted events in an outbox
  that can be inspected for logging or testing.

The implementation deliberately avoids heavy frameworks so that the
simulation core can run in constrained environments (e.g. unit tests or
analysis notebooks).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
import heapq
import itertools
from typing import Callable, Dict, Iterable, Iterator, List, MutableMapping, MutableSequence, Optional

TelemetrySubscriber = Callable[["TelemetrySnapshot"], None]


class EventPriority(Enum):
    """Discrete delivery priority classes.

    The ordering mirrors the documentation which specifies four queues.
    ``CRITICAL`` events always run before ``HIGH`` and so on.  Within the
    same priority the bus delivers events according to their creation
    order.
    """

    CRITICAL = auto()
    HIGH = auto()
    NORMAL = auto()
    LOW = auto()

    @property
    def queue_index(self) -> int:
        """Return an integer useful for ordering comparisons."""

        return {
            EventPriority.CRITICAL: 0,
            EventPriority.HIGH: 1,
            EventPriority.NORMAL: 2,
            EventPriority.LOW: 3,
        }[self]


@dataclass(slots=True)
class Event:
    """Canonical event structure carried on the simulation bus."""

    id: str
    type: str
    tick: int
    ttl: int
    payload: Dict[str, object] = field(default_factory=dict)
    ward: Optional[str] = None
    actors: MutableSequence[str] = field(default_factory=list)
    emitter: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL

    def decremented(self) -> "Event":
        """Return a copy of the event with its TTL decreased by one.

        The method does not mutate the instance which keeps the event
        records immutable for logging.  Callers are expected to drop the
        event when the returned TTL becomes negative.
        """

        return Event(
            id=self.id,
            type=self.type,
            tick=self.tick,
            ttl=self.ttl - 1,
            payload=dict(self.payload),
            ward=self.ward,
            actors=list(self.actors),
            emitter=self.emitter,
            priority=self.priority,
        )


Subscriber = Callable[[Event], None]
Predicate = Callable[[Event], bool]


@dataclass
class Subscription:
    """Handle returned when subscribing to the event bus."""

    predicate: Predicate
    callback: Subscriber
    active: bool = True

    def matches(self, event: Event) -> bool:
        return self.active and self.predicate(event)


class EventBus:
    """Priority queue based event dispatcher."""

    def __init__(self) -> None:
        self._subscriptions: List[Subscription] = []
        self._queue: List[tuple[int, int, Event]] = []
        self._counter = itertools.count()
        self._outbox: List[Event] = []
        self._queue_depth: MutableMapping[str, int] = defaultdict(int)
        self._expired_counts: Counter[str] = Counter()
        self._dropped_counts: Counter[str] = Counter()
        self._telemetry_subscribers: List[TelemetrySubscriber] = []
        self._telemetry_log: List[TelemetrySnapshot] = []

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------
    def subscribe(self, callback: Subscriber, *, predicate: Optional[Predicate] = None) -> Subscription:
        """Register a subscriber and return the :class:`Subscription`.

        ``predicate`` defaults to a function that always returns ``True``.
        Callers can deactivate a subscription by setting
        ``subscription.active = False``.
        """

        if predicate is None:
            predicate = lambda event: True
        sub = Subscription(predicate=predicate, callback=callback)
        self._subscriptions.append(sub)
        return sub

    # ------------------------------------------------------------------
    # Emission and dispatch
    # ------------------------------------------------------------------
    def publish(self, event: Event) -> None:
        """Queue ``event`` for delivery."""

        heapq.heappush(
            self._queue,
            (event.priority.queue_index, next(self._counter), event),
        )
        self._outbox.append(event)
        self._queue_depth[event.type] += 1

    def dispatch(self) -> List[Event]:
        """Drain the queue and notify matching subscribers.

        Returns the list of events delivered which is convenient for
        diagnostics and testing.  Events whose TTL expires before they are
        delivered are silently discarded.
        """

        delivered: List[Event] = []
        while self._queue:
            _, _, event = heapq.heappop(self._queue)
            self._queue_depth[event.type] = max(0, self._queue_depth[event.type] - 1)
            if event.ttl < 0:
                self._expired_counts[event.type] += 1
                continue
            delivered.append(event)
            for subscription in self._subscriptions:
                if subscription.matches(event):
                    subscription.callback(event)
        return delivered

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    @property
    def outbox(self) -> Iterable[Event]:
        """Iterate over emitted events without mutating the bus."""

        return tuple(self._outbox)

    def clear_outbox(self) -> None:
        self._outbox.clear()

    # ------------------------------------------------------------------
    # Telemetry channel
    # ------------------------------------------------------------------
    def subscribe_telemetry(self, callback: TelemetrySubscriber) -> None:
        """Register a telemetry subscriber that receives tick snapshots."""

        self._telemetry_subscribers.append(callback)

    def emit_telemetry(self, snapshot: "TelemetrySnapshot") -> "TelemetrySnapshot":
        """Record and broadcast a telemetry snapshot."""

        snapshot.queue_depths = {
            event_type: depth for event_type, depth in sorted(self._queue_depth.items())
        }
        snapshot.expired_events = dict(self._expired_counts)
        snapshot.dropped_events = dict(self._dropped_counts)
        self._telemetry_log.append(snapshot)
        for subscriber in list(self._telemetry_subscribers):
            subscriber(snapshot)
        self._expired_counts.clear()
        self._dropped_counts.clear()
        return snapshot

    @property
    def telemetry_log(self) -> Iterable["TelemetrySnapshot"]:
        return tuple(self._telemetry_log)


@dataclass
class TelemetrySnapshot:
    """Structured metrics emitted once per tick."""

    tick: int
    phase_latency_ms: Dict[str, float] = field(default_factory=dict)
    handler_latency_ms: Dict[str, float] = field(default_factory=dict)
    queue_depths: Dict[str, int] = field(default_factory=dict)
    expired_events: Dict[str, int] = field(default_factory=dict)
    dropped_events: Dict[str, int] = field(default_factory=dict)


__all__ = ["Event", "EventBus", "EventPriority", "TelemetrySnapshot"]

