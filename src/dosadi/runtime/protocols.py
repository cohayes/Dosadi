from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from dosadi.state import WorldState
from dosadi.systems.protocols import ProtocolAdoptionMetrics, ProtocolStatus


def _iter_active_colonists(world: WorldState) -> Iterable[Tuple[str, object]]:
    for agent_id, agent in getattr(world, "agents", {}).items():
        if "colonist" not in getattr(agent, "roles", []):
            continue
        if getattr(getattr(agent, "physical", None), "health", 0.0) <= 0:
            continue
        if getattr(agent, "is_asleep", False) or getattr(getattr(agent, "physical", None), "is_sleeping", False):
            continue
        yield agent_id, agent


def _index_agents_by_edge(world: WorldState) -> Dict[str, List[str]]:
    agents_by_edge: Dict[str, List[str]] = {}
    edges = getattr(world, "edges", {}) or {}

    for agent_id, agent in _iter_active_colonists(world):
        location_id = getattr(agent, "location_id", None)
        if not location_id:
            continue

        for edge in edges.values():
            edge_id = getattr(edge, "id", None)
            if not edge_id:
                continue
            if location_id == edge_id:
                agents_by_edge.setdefault(edge_id, []).append(agent_id)
                continue

            a = getattr(edge, "a", None)
            b = getattr(edge, "b", None)
            if location_id == a or location_id == b:
                agents_by_edge.setdefault(edge_id, []).append(agent_id)

    return agents_by_edge


def _iter_protocols(world: WorldState):
    registry = getattr(world, "protocols", None)
    if registry is None:
        return []
    if hasattr(registry, "protocols_by_id"):
        return registry.protocols_by_id.values()
    if isinstance(registry, dict):
        return registry.values()
    values = getattr(registry, "values", None)
    if callable(values):
        try:
            return values()
        except Exception:
            return []
    return []


def update_protocol_adoption_metrics(world: WorldState, current_tick: int) -> None:
    agents_by_edge = _index_agents_by_edge(world)

    for protocol in _iter_protocols(world):
        if getattr(protocol, "status", None) is not ProtocolStatus.ACTIVE:
            continue

        metrics = getattr(protocol, "adoption", None) or ProtocolAdoptionMetrics()
        protocol.adoption = metrics

        coverage_edge_ids: List[str] = []
        coverage = getattr(protocol, "coverage", None)
        if coverage is not None:
            coverage_edge_ids.extend(getattr(coverage, "edge_ids", []) or [])
        coverage_edge_ids.extend(getattr(protocol, "covered_edge_ids", []) or [])
        if not coverage_edge_ids and getattr(protocol, "covered_location_ids", None):
            coverage_edge_ids.extend(getattr(protocol, "covered_location_ids", []) or [])
        if coverage_edge_ids:
            coverage_edge_ids = list(dict.fromkeys(coverage_edge_ids))

        for edge_id in coverage_edge_ids:
            agents_here = agents_by_edge.get(edge_id, [])
            if not agents_here:
                continue

            if metrics.first_observed_tick is None:
                metrics.first_observed_tick = current_tick
            metrics.last_observed_tick = current_tick

            group_size = len(agents_here)
            required_group_size = (
                getattr(protocol, "required_group_size", None)
                or getattr(protocol, "min_group_size", None)
                or 2
            )

            for _ in agents_here:
                metrics.total_traversals += 1
                if group_size >= required_group_size:
                    metrics.conforming_traversals += 1
                else:
                    metrics.nonconforming_traversals += 1


__all__ = [
    "_index_agents_by_edge",
    "update_protocol_adoption_metrics",
]
