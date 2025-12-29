"""World event bus with bounded retention and deferred dispatch.

This module implements the D-RUNTIME-0313 checklist: a deterministic, in-process
event bus with bounded retention, small immutable payloads, and a deferred drain
model. Producers publish :class:`WorldEvent` instances, subscribers receive them
in sequence order when :meth:`EventBus.drain` is invoked, and callers can query
recent events via ``get_since`` without scanning the full ring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping, MutableMapping, Sequence


class EventKind:
    """String constants for core world events."""

    TICK = "TICK"
    DAY_ROLLOVER = "DAY_ROLLOVER"
    INCIDENT_RECORDED = "INCIDENT_RECORDED"
    DEPOT_BUILT = "DEPOT_BUILT"
    CORRIDOR_ESTABLISHED = "CORRIDOR_ESTABLISHED"
    DELIVERY_COMPLETED = "DELIVERY_COMPLETED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    PROTOCOL_AUTHORED = "PROTOCOL_AUTHORED"
    PROTOCOL_VIOLATION = "PROTOCOL_VIOLATION"
    ENFORCEMENT_ACTION = "ENFORCEMENT_ACTION"
    CONSTRUCTION_PROJECT_STARTED = "CONSTRUCTION_PROJECT_STARTED"
    CONSTRUCTION_PROJECT_COMPLETED = "CONSTRUCTION_PROJECT_COMPLETED"
    SCOUT_MISSION_COMPLETED = "SCOUT_MISSION_COMPLETED"
    WATER_ALLOCATION_SET = "water.allocation.set"
    WATER_ENTITLEMENT_ISSUED = "water.entitlement.issued"
    WATER_PERMIT_VERIFIED = "water.permit.verified"
    WATER_UNITS_DISPENSED = "water.units.dispensed"
    WATER_LEDGER_RECONCILED = "water.ledger.reconciled"
    WATER_AUDIT_FINDINGS = "water.audit.findings"
    WATER_SANCTION_APPLIED = "water.sanction.applied"


@dataclass(frozen=True, slots=True)
class WorldEvent:
    seq: int
    tick: int
    day: int
    kind: str
    polity_id: str | None = None
    ward_id: str | None = None
    actor_id: str | None = None
    subject_id: str | None = None
    payload: tuple[tuple[str, object], ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(slots=True)
class EventBusConfig:
    enabled: bool = True
    max_events: int = 50_000
    max_payload_items: int = 12
    drop_policy: str = "DROP_OLDEST"


@dataclass(slots=True)
class _Subscription:
    handler: Callable[[WorldEvent], None]
    kinds: frozenset[str] | None
    active: bool = True


class EventBus:
    def __init__(self, config: EventBusConfig | None = None) -> None:
        self.config = config or EventBusConfig()
        self._events: list[WorldEvent] = []
        self._base_seq = 0
        self._next_seq = 0
        self._pending: list[WorldEvent] = []
        self._subscriptions: dict[int, _Subscription] = {}
        self._next_sub_id = 1

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------
    def publish(
        self,
        *,
        kind: str,
        tick: int,
        day: int,
        polity_id: str | None = None,
        ward_id: str | None = None,
        actor_id: str | None = None,
        subject_id: str | None = None,
        payload: Mapping[str, object] | Sequence[tuple[str, object]] | None = None,
        tags: Iterable[str] | None = None,
    ) -> WorldEvent | None:
        """Queue an event for later dispatch.

        Returns the :class:`WorldEvent` instance or ``None`` if the bus is
        disabled.
        """

        if not self.config.enabled:
            return None

        normalized_payload = self._normalize_payload(payload)
        normalized_tags = tuple(sorted(tags)) if tags else ()
        event = WorldEvent(
            seq=self._next_seq,
            tick=int(tick),
            day=int(day),
            kind=str(kind),
            polity_id=polity_id,
            ward_id=ward_id,
            actor_id=actor_id,
            subject_id=subject_id,
            payload=normalized_payload,
            tags=normalized_tags,
        )
        self._next_seq += 1
        self._append_to_ring(event)
        self._pending.append(event)
        return event

    def _normalize_payload(
        self, payload: Mapping[str, object] | Sequence[tuple[str, object]] | None
    ) -> tuple[tuple[str, object], ...]:
        if payload is None:
            return ()
        if isinstance(payload, Mapping):
            items = list(sorted(payload.items(), key=lambda kv: str(kv[0])))
        else:
            items = list(payload)
        max_items = max(0, int(self.config.max_payload_items))
        truncated = False
        if max_items and len(items) > max_items:
            items = items[:max_items]
            truncated = True
        normalized = tuple((str(k), v) for k, v in items)
        if truncated:
            normalized += (("__truncated__", True),)
        return normalized

    def _append_to_ring(self, event: WorldEvent) -> None:
        self._events.append(event)
        max_events = max(1, int(self.config.max_events)) if self.config.max_events else 0
        if max_events > 0 and len(self._events) > max_events:
            overflow = len(self._events) - max_events
            if self.config.drop_policy == "DROP_OLDEST":
                del self._events[:overflow]
                self._base_seq += overflow
            else:
                self._events = self._events[-max_events:]
                self._base_seq = max(0, self._next_seq - len(self._events))

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------
    def subscribe(
        self, handler: Callable[[WorldEvent], None], *, kinds: set[str] | frozenset[str] | None = None
    ) -> int:
        sub_id = self._next_sub_id
        self._next_sub_id += 1
        self._subscriptions[sub_id] = _Subscription(handler=handler, kinds=frozenset(kinds) if kinds else None)
        return sub_id

    def unsubscribe(self, sub_id: int) -> None:
        if sub_id in self._subscriptions:
            self._subscriptions[sub_id].active = False
            del self._subscriptions[sub_id]

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def drain(self) -> list[WorldEvent]:
        delivered: list[WorldEvent] = []
        pending_now = list(self._pending)
        self._pending.clear()
        for event in pending_now:
            delivered.append(event)
            for subscription in list(self._subscriptions.values()):
                if not subscription.active:
                    continue
                if subscription.kinds is not None and event.kind not in subscription.kinds:
                    continue
                subscription.handler(event)
        return delivered

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def get_since(self, seq: int) -> list[WorldEvent]:
        if seq < self._base_seq:
            seq = self._base_seq
        offset = seq - self._base_seq
        return list(self._events[offset:])

    def latest_seq(self) -> int:
        return self._next_seq - 1 if self._next_seq > 0 else -1


def tick_to_day(world: object, tick: int) -> int:
    ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(world, "ticks_per_day", 144_000)
    try:
        ticks_per_day = int(ticks_per_day)
    except Exception:
        ticks_per_day = 144_000
    ticks_per_day = max(1, ticks_per_day)
    return int(tick) // ticks_per_day


def ensure_event_bus(world: MutableMapping[str, object] | object) -> EventBus:
    cfg = getattr(world, "event_bus_cfg", None)
    if not isinstance(cfg, EventBusConfig):
        cfg = EventBusConfig()
        setattr(world, "event_bus_cfg", cfg)
    bus = getattr(world, "event_bus", None)
    if not isinstance(bus, EventBus):
        bus = EventBus(cfg)
        setattr(world, "event_bus", bus)
    return bus


def publish_tick_events(world: object, tick: int) -> None:
    bus = ensure_event_bus(world)
    current_day = tick_to_day(world, tick)
    if getattr(world, "day", None) != current_day:
        setattr(world, "day", current_day)
        bus.publish(kind=EventKind.DAY_ROLLOVER, tick=tick, day=current_day)
    bus.publish(kind=EventKind.TICK, tick=tick, day=current_day)


def drain_event_bus(world: object) -> list[WorldEvent]:
    bus = ensure_event_bus(world)
    return bus.drain()


__all__ = [
    "EventBus",
    "EventBusConfig",
    "EventKind",
    "WorldEvent",
    "drain_event_bus",
    "ensure_event_bus",
    "publish_tick_events",
    "tick_to_day",
]
