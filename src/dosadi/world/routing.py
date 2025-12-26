from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Any, Dict, Mapping

from dosadi.runtime.belief_queries import belief_score, planner_perspective_agent

from .corridor_infrastructure import travel_time_multiplier_for_edge
from .survey_map import SurveyMap, edge_key


@dataclass(slots=True)
class Route:
    nodes: list[str]
    edge_keys: list[str]
    total_cost: float


@dataclass(slots=True)
class RoutingConfig:
    enabled: bool = True
    max_expansions: int = 5000
    risk_weight: float = 0.35
    hazard_weight: float = 0.50
    belief_weight: float = 0.50
    tie_break: str = "lex"
    cache_size: int = 2000


class _LRU:
    def __init__(self, capacity: int):
        self.capacity = max(1, capacity)
        self.order: list[str] = []
        self.data: Dict[str, Route | None] = {}

    def _touch(self, key: str) -> None:
        if key in self.order:
            self.order.remove(key)
        self.order.append(key)
        if len(self.order) > self.capacity:
            oldest = self.order.pop(0)
            self.data.pop(oldest, None)

    def get(self, key: str) -> Route | None | None:
        if key not in self.data:
            return None
        self._touch(key)
        return self.data[key]

    def set(self, key: str, value: Route | None) -> None:
        self.data[key] = value
        self._touch(key)


_ROUTE_CACHE = _LRU(capacity=2000)


def _edge_cost(world: Any, edge_data: Mapping[str, Any], cfg: RoutingConfig, perspective: Any) -> float:
    edge_key_str = edge_key(edge_data.get("a"), edge_data.get("b"))
    base_cost = max(float(edge_data.get("distance_m", 0.0)), float(edge_data.get("travel_cost", 0.0)))
    base_cost *= travel_time_multiplier_for_edge(world, edge_key_str)
    hazard = float(edge_data.get("hazard", 0.0))
    edge = edge_data.get("edge_obj")
    belief = 0.0
    if perspective is not None:
        belief = belief_score(perspective, f"route-risk:{edge_key_str}", cfg.hazard_weight)
    risk_component = cfg.hazard_weight * hazard + cfg.belief_weight * belief
    return base_cost * (1.0 + cfg.risk_weight * risk_component)


def _build_neighbors(survey_map: SurveyMap) -> Dict[str, list[tuple[str, str]]]:
    if survey_map.adj:
        return survey_map.adj
    survey_map.rebuild_adjacency()
    return survey_map.adj


def _stable_push(frontier: list[tuple[float, str, str]], cost: float, node: str, tie_key: str) -> None:
    heapq.heappush(frontier, (cost, tie_key, node))


def compute_route(
    world: Any,
    *,
    from_node: str,
    to_node: str,
    perspective_agent_id: str | None = None,
) -> Route | None:
    cfg: RoutingConfig = getattr(world, "routing_cfg", RoutingConfig())
    if not cfg.enabled:
        return None

    cache_key = f"{from_node}->{to_node}:{perspective_agent_id}:{getattr(world, 'day', 0)}"
    cached = _ROUTE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    if from_node == to_node:
        route = Route(nodes=[from_node], edge_keys=[], total_cost=0.0)
        _ROUTE_CACHE.set(cache_key, route)
        return route

    neighbors = _build_neighbors(survey_map)
    if from_node not in neighbors or to_node not in neighbors:
        _ROUTE_CACHE.set(cache_key, None)
        return None

    perspective = None
    if perspective_agent_id:
        perspective = getattr(world, "agents", {}).get(perspective_agent_id)
    if perspective is None:
        perspective = planner_perspective_agent(world)

    frontier: list[tuple[float, str, str]] = []
    _stable_push(frontier, 0.0, from_node, from_node)
    costs: Dict[str, float] = {from_node: 0.0}
    parents: Dict[str, str] = {}
    parent_edge: Dict[str, str] = {}
    expansions = 0

    while frontier and expansions < cfg.max_expansions:
        cost, _, node = heapq.heappop(frontier)
        expansions += 1
        if node == to_node:
            break
        for nbr, ekey in sorted(neighbors.get(node, [])):
            edge_obj = survey_map.edges.get(ekey)
            if edge_obj and edge_obj.closed_until_day is not None:
                if getattr(world, "day", 0) < edge_obj.closed_until_day:
                    continue
            edge_payload = {
                "a": node,
                "b": nbr,
                "distance_m": getattr(edge_obj, "distance_m", 0.0),
                "travel_cost": getattr(edge_obj, "travel_cost", 0.0),
                "hazard": getattr(edge_obj, "hazard", 0.0),
                "edge_obj": edge_obj,
            }
            step_cost = _edge_cost(world, edge_payload, cfg, perspective)
            next_cost = cost + step_cost
            prev = costs.get(nbr)
            tie_key = nbr if cfg.tie_break == "lex" else f"{node}->{nbr}"
            if prev is None or next_cost < prev or (math.isclose(next_cost, prev) and tie_key < parents.get(nbr, tie_key)):
                costs[nbr] = next_cost
                parents[nbr] = node
                parent_edge[nbr] = ekey
                _stable_push(frontier, next_cost, nbr, tie_key)

    if to_node not in costs:
        _ROUTE_CACHE.set(cache_key, None)
        return None

    path_nodes: list[str] = []
    path_edges: list[str] = []
    cursor = to_node
    while cursor != from_node:
        path_nodes.append(cursor)
        ekey = parent_edge[cursor]
        path_edges.append(ekey)
        cursor = parents[cursor]
    path_nodes.append(from_node)
    path_nodes.reverse()
    path_edges.reverse()

    route = Route(nodes=path_nodes, edge_keys=path_edges, total_cost=costs[to_node])
    _ROUTE_CACHE.set(cache_key, route)
    return route


__all__ = [
    "Route",
    "RoutingConfig",
    "compute_route",
]
