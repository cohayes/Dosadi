from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import heapq
import json
from hashlib import sha256
import random
from typing import Dict, Mapping, MutableMapping, Optional

import math

from dosadi.runtime.belief_queries import belief_score, planner_perspective_agent

from .survey_map import SurveyMap, edge_key


@dataclass(slots=True)
class LogisticsConfig:
    use_agent_couriers: bool = False
    route_risk_cost_weight: float = 0.30


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
    if getattr(world, "logistics_cfg", None) is None:
        world.logistics_cfg = LogisticsConfig()
    return ledger


def _edge_neighbors(survey_map: SurveyMap, node: str) -> list[tuple[str, float, str]]:
    neighbors: list[tuple[str, float, str]] = []
    for key, edge in survey_map.edges.items():
        if edge.a == node:
            neighbors.append((edge.b, max(edge.distance_m, edge.travel_cost), key))
        elif edge.b == node:
            neighbors.append((edge.a, max(edge.distance_m, edge.travel_cost), key))
    return neighbors


def _route_cost(world, edge_key_str: str, base_cost: float) -> float:
    agent = planner_perspective_agent(world)
    risk = belief_score(agent, f"route-risk:{edge_key_str}", 0.5)
    cfg: LogisticsConfig = getattr(world, "logistics_cfg", LogisticsConfig())
    weight = getattr(cfg, "route_risk_cost_weight", 0.0)
    return base_cost * (1.0 + weight * (risk - 0.5))


def estimate_travel_ticks(origin: str, dest: str, survey_map: SurveyMap, world=None) -> int:
    if origin == dest:
        return 0

    if not survey_map.edges:
        return 1

    # Dijkstra with small graphs; deterministic ordering through sorted neighbors
    frontier: list[tuple[float, str]] = [(0.0, origin)]
    visited: set[str] = set()
    costs: dict[str, float] = {origin: 0.0}

    while frontier:
        frontier.sort()
        cost, node = frontier.pop(0)
        if node in visited:
            continue
        visited.add(node)
        if node == dest:
            break
        for neighbor, base_cost, key in sorted(_edge_neighbors(survey_map, node), key=lambda n: n[0]):
            adjusted = _route_cost(world, key, base_cost) if world is not None else base_cost
            next_cost = cost + adjusted
            if neighbor not in costs or next_cost < costs[neighbor]:
                costs[neighbor] = next_cost
                frontier.append((next_cost, neighbor))

    final_cost = costs.get(dest)
    if final_cost is None:
        return 1
    try:
        return max(1, int(math.ceil(final_cost)))
    except (TypeError, ValueError):
        return 1


def _has_stock(stock: MutableMapping[str, float], items: Mapping[str, float]) -> bool:
    for item, qty in items.items():
        if stock.get(item, 0.0) < qty:
            return False
    return True


def _consume_stock(stock: MutableMapping[str, float], items: Mapping[str, float]) -> None:
    for item, qty in items.items():
        stock[item] = stock.get(item, 0.0) - qty


def _logistics_metrics(world) -> MutableMapping[str, float]:
    metrics: MutableMapping[str, float] = getattr(world, "metrics", {})
    world.metrics = metrics
    return metrics.setdefault("logistics", {})  # type: ignore[arg-type]


def _choose_idle_courier_agent(world, *, day: int, max_candidates: int = 200) -> str | None:
    agents = getattr(world, "agents", {}) or {}
    if not agents:
        return None

    from .workforce import ensure_workforce

    ledger = ensure_workforce(world)
    ordered_ids = sorted(agents.keys())[: max(0, max_candidates)]
    for agent_id in ordered_ids:
        try:
            if ledger.is_idle(agent_id):
                return agent_id
        except Exception:
            # Best-effort; skip corrupted entries
            continue
    return None


def release_courier(world, carrier_id: str | None) -> None:
    if carrier_id is None:
        return

    if carrier_id.startswith("carrier:"):
        world.carriers_available = getattr(world, "carriers_available", 0) + 1
        return

    from .workforce import AssignmentKind, ensure_workforce

    metrics = _logistics_metrics(world)
    ledger = ensure_workforce(world)
    assignment = ledger.get(carrier_id)
    if assignment.kind is not AssignmentKind.LOGISTICS_COURIER:
        metrics["courier_release_mismatch"] = metrics.get("courier_release_mismatch", 0.0) + 1
    try:
        ledger.unassign(carrier_id)
    except Exception:
        metrics["courier_release_mismatch"] = metrics.get("courier_release_mismatch", 0.0) + 1


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

    cfg: LogisticsConfig = getattr(world, "logistics_cfg", LogisticsConfig())
    use_agent_couriers = getattr(cfg, "use_agent_couriers", False)
    metrics = _logistics_metrics(world)
    assigned_carrier: str | None = None

    if use_agent_couriers:
        agent_id = _choose_idle_courier_agent(world, day=getattr(world, "day", 0))
        if agent_id is not None:
            from .workforce import Assignment, AssignmentKind, ensure_workforce

            ledger = ensure_workforce(world)
            try:
                ledger.assign(
                    Assignment(
                        agent_id=agent_id,
                        kind=AssignmentKind.LOGISTICS_COURIER,
                        target_id=delivery.delivery_id,
                        start_day=getattr(world, "day", 0),
                        notes={"role": "courier"},
                    )
                )
                assigned_carrier = agent_id
                delivery.notes["carrier_kind"] = "agent"

                agent = getattr(world, "agents", {}).get(agent_id)
                if agent is not None:
                    agent.navigation_target_id = delivery.dest_node_id
            except ValueError:
                assigned_carrier = None

    if assigned_carrier is None:
        available = getattr(world, "carriers_available", 0)
        if available <= 0:
            delivery.status = DeliveryStatus.REQUESTED
            return

        world.next_carrier_seq = getattr(world, "next_carrier_seq", 0) + 1
        assigned_carrier = f"carrier:{world.next_carrier_seq}"
        world.carriers_available = max(0, available - 1)
        delivery.notes["carrier_kind"] = "abstract"
        metrics["assigned_abstract_carriers"] = metrics.get("assigned_abstract_carriers", 0.0) + 1
    else:
        metrics["assigned_agent_couriers"] = metrics.get("assigned_agent_couriers", 0.0) + 1

    delivery.assigned_carrier_id = assigned_carrier
    delivery.status = DeliveryStatus.PICKED_UP
    delivery.pickup_tick = tick

    _consume_stock(stockpiles, delivery.items)
    travel_ticks = estimate_travel_ticks(
        delivery.origin_node_id,
        delivery.dest_node_id,
        getattr(world, "survey_map", SurveyMap()),
        world,
    )
    delivery.deliver_tick = tick + travel_ticks
    delivery.status = DeliveryStatus.IN_TRANSIT
    logistics.add(delivery)
    queue = getattr(world, "delivery_due_queue", [])
    heapq.heapify(queue)
    heapq.heappush(queue, (delivery.deliver_tick, delivery.delivery_id))
    world.delivery_due_queue = queue


def assign_pending_deliveries(world, *, tick: int) -> None:
    logistics = ensure_logistics(world)
    cfg: LogisticsConfig = getattr(world, "logistics_cfg", LogisticsConfig())
    use_agent_couriers = getattr(cfg, "use_agent_couriers", False)
    available = getattr(world, "carriers_available", 0)
    has_agents = use_agent_couriers and bool(getattr(world, "agents", {}))
    if available <= 0 and not has_agents:
        return

    for delivery_id in sorted(logistics.active_ids):
        delivery = logistics.deliveries[delivery_id]
        if delivery.status != DeliveryStatus.REQUESTED:
            continue
        if getattr(world, "carriers_available", 0) <= 0 and not has_agents:
            break
        _assign_carrier(world, delivery, tick)


def _deliver(world, delivery: DeliveryRequest, tick: int) -> None:
    delivery.status = DeliveryStatus.DELIVERED
    delivery.deliver_tick = tick
    release_courier(world, delivery.assigned_carrier_id)

    agent = getattr(world, "agents", {}).get(delivery.assigned_carrier_id)
    if agent is not None:
        agent.location_id = delivery.dest_node_id

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
            release_courier(world, delivery.assigned_carrier_id)
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

