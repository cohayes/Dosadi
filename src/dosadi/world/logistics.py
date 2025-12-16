from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import heapq
import json
from hashlib import sha256
import random
from typing import Dict, Mapping, MutableMapping, Optional

from .survey_map import SurveyMap, edge_key


class DeliveryStatus(Enum):
    REQUESTED = "REQUESTED"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


@dataclass(slots=True)
class DeliveryRequest:
    delivery_id: str
    project_id: str
    origin_node_id: str
    dest_node_id: str
    items: Dict[str, float]
    status: DeliveryStatus
    created_tick: int
    due_tick: int | None = None
    assigned_carrier_id: str | None = None
    pickup_tick: int | None = None
    deliver_tick: int | None = None
    notes: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class LogisticsLedger:
    deliveries: Dict[str, DeliveryRequest] = field(default_factory=dict)
    active_ids: list[str] = field(default_factory=list)

    def add(self, delivery: DeliveryRequest) -> None:
        self.deliveries[delivery.delivery_id] = delivery
        if delivery.delivery_id not in self.active_ids:
            self.active_ids.append(delivery.delivery_id)
            self.active_ids.sort()

    def signature(self) -> str:
        canonical = {
            delivery_id: {
                "status": delivery.status.value,
                "project": delivery.project_id,
                "origin": delivery.origin_node_id,
                "dest": delivery.dest_node_id,
                "items": dict(sorted(delivery.items.items())),
                "carrier": delivery.assigned_carrier_id,
                "due": delivery.due_tick,
                "deliver": delivery.deliver_tick,
            }
            for delivery_id, delivery in sorted(self.deliveries.items())
        }
        payload = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
        return sha256(payload.encode("utf-8")).hexdigest()


def ensure_logistics(world) -> LogisticsLedger:
    ledger: LogisticsLedger = getattr(world, "logistics", None) or LogisticsLedger()
    world.logistics = ledger
    if getattr(world, "delivery_due_queue", None) is None:
        world.delivery_due_queue = []
    if getattr(world, "carriers_available", None) is None:
        world.carriers_available = 1
    if getattr(world, "next_carrier_seq", None) is None:
        world.next_carrier_seq = 0
    return ledger


def estimate_travel_ticks(origin: str, dest: str, survey_map: SurveyMap) -> int:
    if origin == dest:
        return 0
    edge = survey_map.edges.get(edge_key(origin, dest))
    if edge:
        try:
            ticks = int(max(1.0, edge.distance_m))
        except (TypeError, ValueError):
            ticks = 10
        return ticks
    return 1


def _has_stock(stock: MutableMapping[str, float], items: Mapping[str, float]) -> bool:
    for item, qty in items.items():
        if stock.get(item, 0.0) < qty:
            return False
    return True


def _consume_stock(stock: MutableMapping[str, float], items: Mapping[str, float]) -> None:
    for item, qty in items.items():
        stock[item] = stock.get(item, 0.0) - qty


def _release_carrier(world) -> None:
    world.carriers_available = getattr(world, "carriers_available", 0) + 1


def _delivery_should_fail(world, delivery_id: str, day: int) -> bool:
    loss_rate = float(getattr(world, "logistics_loss_rate", 0.0) or 0.0)
    if loss_rate <= 0.0:
        return False

    seed_blob = f"{delivery_id}:{day}:{getattr(world, 'seed', 0)}"
    seed_int = int(sha256(seed_blob.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed_int)
    return rng.random() < loss_rate


def _assign_carrier(world, delivery: DeliveryRequest, tick: int) -> None:
    logistics = ensure_logistics(world)
    stockpiles: MutableMapping[str, float] = getattr(world, "stockpiles", {})

    if not _has_stock(stockpiles, delivery.items):
        delivery.status = DeliveryStatus.FAILED
        delivery.notes["failure"] = "insufficient_stock"
        return

    world.next_carrier_seq = getattr(world, "next_carrier_seq", 0) + 1
    carrier_id = f"carrier:{world.next_carrier_seq}"
    world.carriers_available = max(0, getattr(world, "carriers_available", 1) - 1)
    delivery.assigned_carrier_id = carrier_id
    delivery.status = DeliveryStatus.PICKED_UP
    delivery.pickup_tick = tick

    _consume_stock(stockpiles, delivery.items)
    travel_ticks = estimate_travel_ticks(delivery.origin_node_id, delivery.dest_node_id, getattr(world, "survey_map", SurveyMap()))
    delivery.deliver_tick = tick + travel_ticks
    delivery.status = DeliveryStatus.IN_TRANSIT
    logistics.add(delivery)
    queue = getattr(world, "delivery_due_queue", [])
    heapq.heapify(queue)
    heapq.heappush(queue, (delivery.deliver_tick, delivery.delivery_id))
    world.delivery_due_queue = queue


def assign_pending_deliveries(world, *, tick: int) -> None:
    logistics = ensure_logistics(world)
    available = getattr(world, "carriers_available", 0)
    if available <= 0:
        return

    for delivery_id in sorted(logistics.active_ids):
        delivery = logistics.deliveries[delivery_id]
        if delivery.status != DeliveryStatus.REQUESTED:
            continue
        if getattr(world, "carriers_available", 0) <= 0:
            break
        delivery.status = DeliveryStatus.ASSIGNED
        _assign_carrier(world, delivery, tick)


def _deliver(world, delivery: DeliveryRequest, tick: int) -> None:
    delivery.status = DeliveryStatus.DELIVERED
    delivery.deliver_tick = tick
    _release_carrier(world)

    projects = getattr(world, "projects", None)
    if projects and delivery.project_id in projects.projects:
        project = projects.projects[delivery.project_id]
        for item, qty in delivery.items.items():
            project.materials_delivered[item] = project.materials_delivered.get(item, 0.0) + qty


def process_due_deliveries(world, *, tick: int) -> None:
    logistics = ensure_logistics(world)
    queue = getattr(world, "delivery_due_queue", [])
    heapq.heapify(queue)

    while queue and queue[0][0] <= tick:
        _, delivery_id = heapq.heappop(queue)
        delivery = logistics.deliveries.get(delivery_id)
        if delivery is None:
            continue
        if delivery.status != DeliveryStatus.IN_TRANSIT:
            continue
        if _delivery_should_fail(world, delivery_id, getattr(world, "day", 0)):
            delivery.status = DeliveryStatus.FAILED
            delivery.deliver_tick = tick
            delivery.notes["failure"] = "phase_loss"
            _release_carrier(world)
            continue
        _deliver(world, delivery, tick)

    world.delivery_due_queue = queue


def process_logistics_until(world, *, target_tick: int, current_tick: Optional[int] = None) -> None:
    start_tick = getattr(world, "tick", 0) if current_tick is None else current_tick
    logistics = ensure_logistics(world)
    if getattr(world, "delivery_due_queue", None) is None:
        world.delivery_due_queue = []
    assign_pending_deliveries(world, tick=start_tick)
    process_due_deliveries(world, tick=target_tick)
    world.logistics = logistics

