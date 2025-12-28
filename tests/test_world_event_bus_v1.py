import pytest

from dosadi.runtime.events import EventBus, EventBusConfig, EventKind, publish_tick_events
from dosadi.runtime.kpis import ensure_kpi_store
from dosadi.state import WorldState


def _make_bus(max_events: int = 100, max_payload_items: int = 12) -> EventBus:
    return EventBus(EventBusConfig(max_events=max_events, max_payload_items=max_payload_items))


def test_deterministic_ordering() -> None:
    bus = _make_bus()
    seen: list[tuple[int, str]] = []
    bus.subscribe(lambda evt: seen.append((evt.seq, evt.kind)))

    bus.publish(kind="A", tick=1, day=0)
    bus.publish(kind="B", tick=2, day=0)

    bus.drain()

    assert seen == [(0, "A"), (1, "B")]


def test_ring_buffer_retention() -> None:
    bus = _make_bus(max_events=3)
    for idx in range(5):
        bus.publish(kind=f"K{idx}", tick=idx, day=0)

    retained = bus.get_since(0)
    assert [evt.seq for evt in retained] == [2, 3, 4]
    assert bus.latest_seq() == 4


def test_kind_filtering() -> None:
    bus = _make_bus()
    seen: list[str] = []
    bus.subscribe(lambda evt: seen.append(evt.kind), kinds={EventKind.DELIVERY_COMPLETED})

    bus.publish(kind=EventKind.DELIVERY_COMPLETED, tick=1, day=0)
    bus.publish(kind=EventKind.DEPOT_BUILT, tick=2, day=0)
    bus.drain()

    assert seen == [EventKind.DELIVERY_COMPLETED]


def test_deferred_drain_semantics() -> None:
    bus = _make_bus()
    delivered: list[str] = []

    def handler(evt):
        delivered.append(evt.kind)
        if evt.kind == "FIRST":
            bus.publish(kind="SECOND", tick=evt.tick + 1, day=evt.day)

    bus.subscribe(handler)
    bus.publish(kind="FIRST", tick=0, day=0)

    bus.drain()
    assert delivered == ["FIRST"]

    bus.drain()
    assert delivered == ["FIRST", "SECOND"]


def test_bounded_payload() -> None:
    bus = _make_bus(max_payload_items=2)
    bus.publish(
        kind="PAYLOAD",
        tick=0,
        day=0,
        payload={"a": 1, "b": 2, "c": 3, "d": 4},
    )
    event = bus.get_since(0)[0]
    keys = [k for k, _ in event.payload]
    assert len(keys) == 3  # two items + truncation marker
    assert "__truncated__" in keys


def test_kpi_integration_smoke() -> None:
    world = WorldState()
    ensure_kpi_store(world)
    bus = world.event_bus

    publish_tick_events(world, tick=0)
    bus.publish(kind=EventKind.DEPOT_BUILT, tick=1, day=0)
    bus.publish(kind=EventKind.CORRIDOR_ESTABLISHED, tick=2, day=0)
    bus.publish(kind=EventKind.DELIVERY_COMPLETED, tick=3, day=0)
    bus.publish(kind=EventKind.DELIVERY_FAILED, tick=4, day=0)

    bus.drain()

    store = world.kpis
    assert store.values["progress.tick"].value == 0
    assert store.values["logistics.depots_built"].value == 1
    assert store.values["logistics.corridors_established"].value == 1
    assert store.values["logistics.deliveries_completed"].value == 1
    assert store.values["logistics.delivery_success_rate"].value == pytest.approx(0.5)
