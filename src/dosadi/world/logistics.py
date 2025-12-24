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
from dosadi.runtime.escort_protocols import (
    assign_escorts_for_delivery,
    ensure_escort_config,
    ensure_escort_state,
    has_escort,
    release_escorts,
)
from dosadi.runtime.local_interactions import (
    InteractionOpportunity,
    enqueue_interaction_opportunity,
    ensure_interaction_config,
)

from .routing import Route, compute_route
from .survey_map import SurveyEdge, SurveyMap, edge_key
from .workforce import Assignment, AssignmentKind, WorkforceLedger, ensure_workforce


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
    route_nodes: list[str] = field(default_factory=list)
    route_edge_keys: list[str] = field(default_factory=list)
    route_index: int = 0
    remaining_edge_ticks: int = 0
    next_edge_complete_tick: int | None = None
    escort_agent_ids: list[str] = field(default_factory=list)


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
                "escorts": list(sorted(delivery.escort_agent_ids)),
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
    ensure_escort_config(world)
    ensure_escort_state(world)
    return ledger


def _route_cost(world, edge_key_str: str, base_cost: float) -> float:
    agent = planner_perspective_agent(world)
    risk = belief_score(agent, f"route-risk:{edge_key_str}", 0.5)
    cfg: LogisticsConfig = getattr(world, "logistics_cfg", LogisticsConfig())
    weight = getattr(cfg, "route_risk_cost_weight", 0.0)
    return base_cost * (1.0 + weight * (risk - 0.5))


def _edge_travel_ticks(edge: SurveyEdge) -> int:
    base = max(getattr(edge, "distance_m", 0.0), getattr(edge, "travel_cost", 0.0))
    return max(1, int(math.ceil(base)))


def estimate_travel_ticks(origin: str, dest: str, survey_map: SurveyMap, world=None) -> int:
    if world is None:
        world = type("Stub", (), {})()
    route = compute_route(world, from_node=origin, to_node=dest, perspective_agent_id=None)
    if route is None:
        return 1
    cost = 0
    for edge_key_str in route.edge_keys:
        edge = survey_map.edges.get(edge_key_str)
        if edge is None:
            continue
        cost += _edge_travel_ticks(edge)
    return max(1, int(cost))


def _has_stock(stock: MutableMapping[str, float], items: Mapping[str, float]) -> bool:
    for item, qty in items.items():
        if stock.get(item, 0.0) < qty:
            return False
    return True


def _consume_stock(stock: MutableMapping[str, float], items: Mapping[str, float]) -> None:
    for item, qty in items.items():
        stock[item] = stock.get(item, 0.0) - qty


def _day_from_tick(world, tick: int) -> int:
    if hasattr(world, "day"):
        try:
            return int(getattr(world, "day", 0))
        except Exception:
            return 0
    ticks_per_day = getattr(world, "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", 144_000)
    try:
        ticks_per_day = int(ticks_per_day)
    except Exception:
        ticks_per_day = 144_000
    return max(0, tick // max(1, ticks_per_day))


def _maybe_enqueue_courier_opportunity(
    world,
    *,
    kind: str,
    node_id: str | None,
    edge_key: str | None,
    delivery: DeliveryRequest,
    tick: int,
) -> None:
    cfg = ensure_interaction_config(world)
    if not getattr(cfg, "enabled", False):
        return

    day = _day_from_tick(world, tick)
    opp = InteractionOpportunity(
        day=day,
        tick=tick,
        kind=kind,
        node_id=node_id,
        edge_key=edge_key,
        primary_agent_id=delivery.assigned_carrier_id,
        subject_id=delivery.delivery_id,
        severity=float(getattr(world, "logistics_loss_rate", 0.0) or 0.0),
        payload={},
    )
    enqueue_interaction_opportunity(world, opp)


def _schedule_next_edge(world, delivery: DeliveryRequest, start_tick: int) -> None:
    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    if delivery.route_index >= len(delivery.route_edge_keys):
        return
    edge_key_str = delivery.route_edge_keys[delivery.route_index]
    edge = survey_map.edges.get(edge_key_str)
    if _edge_closed(world, edge):
        return
    remaining = _edge_travel_ticks(edge)
    escort_cfg = ensure_escort_config(world)
    if getattr(escort_cfg, "enabled", False) and has_escort(world, delivery.delivery_id):
        penalty = 1.0 + max(0.0, getattr(escort_cfg, "escort_speed_penalty", 0.0))
        remaining = int(math.ceil(remaining * penalty))
    delivery.remaining_edge_ticks = remaining
    delivery.next_edge_complete_tick = start_tick + delivery.remaining_edge_ticks
    queue: list[tuple[int, str]] = getattr(world, "delivery_due_queue", [])
    heapq.heapify(queue)
    heapq.heappush(queue, (delivery.next_edge_complete_tick, delivery.delivery_id))
    world.delivery_due_queue = queue


def _logistics_metrics(world) -> MutableMapping[str, float]:
    metrics: MutableMapping[str, float] = getattr(world, "metrics", {})
    world.metrics = metrics
    return metrics.setdefault("logistics", {})  # type: ignore[arg-type]


def _edge_closed(world, edge: SurveyEdge | None) -> bool:
    if edge is None:
        return True
    if edge.closed_until_day is None:
        return False
    return getattr(world, "day", 0) < edge.closed_until_day


def _init_delivery_route(world, delivery: DeliveryRequest, *, tick: int) -> bool:
    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    route = compute_route(world, from_node=delivery.origin_node_id, to_node=delivery.dest_node_id, perspective_agent_id=delivery.assigned_carrier_id)
    if route is None:
        delivery.route_nodes = [delivery.origin_node_id, delivery.dest_node_id]
        delivery.route_edge_keys = []
    else:
        delivery.route_nodes = list(route.nodes)
        delivery.route_edge_keys = list(route.edge_keys)
    delivery.route_index = 0
    delivery.remaining_edge_ticks = 0
    delivery.next_edge_complete_tick = None

    total_ticks = 0
    for ekey in delivery.route_edge_keys:
        edge = survey_map.edges.get(ekey)
        if edge is None:
            continue
        total_ticks += _edge_travel_ticks(edge)
    delivery.deliver_tick = tick + total_ticks
    return True


def _reroute_delivery(world, delivery: DeliveryRequest) -> None:
    current_node = delivery.route_nodes[delivery.route_index]
    dest = delivery.route_nodes[-1]
    new_route = compute_route(world, from_node=current_node, to_node=dest, perspective_agent_id=delivery.assigned_carrier_id)
    if new_route is None:
        delivery.status = DeliveryStatus.FAILED
        delivery.notes["failure"] = "reroute_failed"
        release_courier(world, delivery.assigned_carrier_id)
        release_escorts(world, delivery.delivery_id)
        return
    delivery.route_nodes = list(new_route.nodes)
    delivery.route_edge_keys = list(new_route.edge_keys)
    delivery.route_index = 0
    delivery.remaining_edge_ticks = 0
    delivery.next_edge_complete_tick = None


def advance_delivery_along_route(world, delivery: DeliveryRequest, *, tick: int, step_ticks: int | None = None) -> None:
    if delivery.status not in {DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT}:
        return

    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    remaining = delivery.remaining_edge_ticks if step_ticks is None else step_ticks
    while remaining > 0 and delivery.status == DeliveryStatus.IN_TRANSIT:
        if delivery.remaining_edge_ticks <= 0:
            if delivery.route_index >= len(delivery.route_edge_keys):
                _deliver(world, delivery, tick)
                return
            edge_key_str = delivery.route_edge_keys[delivery.route_index]
            edge = survey_map.edges.get(edge_key_str)
            if _edge_closed(world, edge):
                _reroute_delivery(world, delivery)
                if delivery.status != DeliveryStatus.IN_TRANSIT:
                    return
                continue
            delivery.remaining_edge_ticks = _edge_travel_ticks(edge)
            delivery.next_edge_complete_tick = tick + delivery.remaining_edge_ticks

        consume = min(remaining, delivery.remaining_edge_ticks)
        delivery.remaining_edge_ticks -= consume
        remaining -= consume
        if delivery.remaining_edge_ticks <= 0:
            current_edge_key = None
            if delivery.route_index < len(delivery.route_edge_keys):
                current_edge_key = delivery.route_edge_keys[delivery.route_index]
            dest_node = None
            if delivery.route_index + 1 < len(delivery.route_nodes):
                dest_node = delivery.route_nodes[delivery.route_index + 1]
            if current_edge_key:
                _maybe_enqueue_courier_opportunity(
                    world,
                    kind="courier_edge",
                    node_id=dest_node,
                    edge_key=current_edge_key,
                    delivery=delivery,
                    tick=tick,
                )
            delivery.route_index += 1
            if delivery.route_index >= len(delivery.route_edge_keys):
                final_node = delivery.route_nodes[-1] if delivery.route_nodes else None
                _maybe_enqueue_courier_opportunity(
                    world,
                    kind="courier_arrival",
                    node_id=final_node,
                    edge_key=current_edge_key,
                    delivery=delivery,
                    tick=tick,
                )
                _deliver(world, delivery, tick)
                return
            delivery.next_edge_complete_tick = None

    if step_ticks is None and delivery.status == DeliveryStatus.IN_TRANSIT:
        _schedule_next_edge(world, delivery, tick)


def _choose_idle_courier_agent(world, *, day: int, max_candidates: int = 200) -> str | None:
    agents = getattr(world, "agents", {}) or {}
    if not agents:
        return None

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
    day = getattr(world, "day", 0)

    if use_agent_couriers:
        agent_id = _choose_idle_courier_agent(world, day=day)
        if agent_id is not None:
            ledger = ensure_workforce(world)
            try:
                ledger.assign(
                    Assignment(
                        agent_id=agent_id,
                        kind=AssignmentKind.LOGISTICS_COURIER,
                        target_id=delivery.delivery_id,
                        start_day=day,
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
    if not _init_delivery_route(world, delivery, tick=tick):
        return
    assign_escorts_for_delivery(world, delivery.delivery_id, day=day)
    if not delivery.route_edge_keys:
        delivery.status = DeliveryStatus.IN_TRANSIT
        _deliver(world, delivery, tick)
        return
    delivery.status = DeliveryStatus.IN_TRANSIT
    logistics.add(delivery)
    _schedule_next_edge(world, delivery, tick)


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
    release_escorts(world, delivery.delivery_id)

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
            release_escorts(world, delivery.delivery_id)
            continue
        delivery.next_edge_complete_tick = None
        advance_delivery_along_route(world, delivery, tick=tick)

    world.delivery_due_queue = queue


def process_logistics_until(world, *, target_tick: int, current_tick: Optional[int] = None) -> None:
    start_tick = getattr(world, "tick", 0) if current_tick is None else current_tick
    logistics = ensure_logistics(world)
    if getattr(world, "delivery_due_queue", None) is None:
        world.delivery_due_queue = []
    assign_pending_deliveries(world, tick=start_tick)
    process_due_deliveries(world, tick=target_tick)
    world.logistics = logistics

