"""Small helpers for reading belief scores in a deterministic way."""
from __future__ import annotations

from typing import Iterable

from dosadi.agent.beliefs import BeliefStore


def _get_belief_store(agent) -> BeliefStore | None:
    if agent is None:
        return None
    store = getattr(agent, "beliefs", None)
    if isinstance(store, BeliefStore):
        return store
    return None


def belief_value(agent, key: str, default: float = 0.5) -> float:
    store = _get_belief_store(agent)
    if store is None:
        return default
    belief = store.get(key)
    if belief is None:
        return default
    return float(getattr(belief, "value", default) or default)


def belief_weight(agent, key: str, default: float = 0.0) -> float:
    store = _get_belief_store(agent)
    if store is None:
        return default
    belief = store.get(key)
    if belief is None:
        return default
    return float(getattr(belief, "weight", default) or default)


def belief_score(agent, key: str, default: float = 0.5) -> float:
    """Blend the belief value with its weight to dampen weak signals."""

    val = belief_value(agent, key, default)
    weight = belief_weight(agent, key, 0.0)
    applied_weight = weight if weight >= 0.2 else 0.0
    return float(default * (1.0 - applied_weight) + val * applied_weight)


def _mean(values: Iterable[float], default: float = 0.5) -> float:
    total = 0.0
    count = 0
    for val in values:
        total += val
        count += 1
    if count == 0:
        return default
    return total / float(count)


def route_risk(agent, edge_key: str, default: float = 0.5) -> float:
    return belief_score(agent, f"route-risk:{edge_key}", default)


def facility_reliability(agent, facility_id: str, default: float = 0.5) -> float:
    return belief_score(agent, f"facility-reliability:{facility_id}", default)


def planner_perspective_agent(world):
    """Pick a deterministic planner perspective agent."""

    agents = getattr(world, "agents", {}) or {}
    steward = None
    for agent_id, agent in agents.items():
        if getattr(agent, "role", None) in {"steward", "council", "councilor"}:
            steward = agent
            break
    if steward is not None:
        return steward
    if not agents:
        return None
    smallest_id = sorted(agents.keys())[0]
    return agents.get(smallest_id)


__all__ = [
    "belief_score",
    "belief_value",
    "belief_weight",
    "facility_reliability",
    "planner_perspective_agent",
    "route_risk",
]
