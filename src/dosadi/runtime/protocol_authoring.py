"""Helpers for authoring movement protocols during wakeup runtime."""

from __future__ import annotations

from typing import Iterable, List

from dosadi.agents.core import AgentState, Goal, GoalHorizon, GoalOrigin, GoalStatus, GoalType, make_goal_id
from dosadi.state import WorldState
from dosadi.systems.protocols import ProtocolRegistry, activate_protocol, create_movement_protocol_from_goal
from dosadi.runtime.evidence_producers import dangerous_edges_from_evidence


def handle_protocol_authoring(
    world: WorldState, scribe: AgentState, authoring_goal: Goal, corridors: List[str]
) -> None:
    """Create and activate a movement protocol for the provided corridors."""

    council_group_id = authoring_goal.target.get("council_group_id", "group:council:alpha")
    registry = world.protocols if isinstance(world.protocols, ProtocolRegistry) else ProtocolRegistry()
    if not isinstance(world.protocols, ProtocolRegistry):
        world.protocols = registry
    protocol = create_movement_protocol_from_goal(
        council_group_id=council_group_id,
        scribe_agent_id=scribe.agent_id,
        group_goal=authoring_goal,
        corridors=corridors,
        tick=world.tick,
        registry=registry,
    )
    activate_protocol(protocol, tick=world.tick)


def maybe_author_movement_protocols(
    *, world: WorldState, dangerous_edge_ids: Iterable[str], tick: int
) -> bool:
    """Draft and activate a protocol if there are uncovered dangerous corridors.

    Returns True if a protocol draft was attempted.
    """

    dangerous_edge_ids = list(dangerous_edge_ids)
    if not dangerous_edge_ids:
        polity_id = getattr(world, "default_polity_id", "polity:default")
        dangerous_edge_ids = dangerous_edges_from_evidence(world, polity_id)
    if not dangerous_edge_ids:
        return False

    registry = world.protocols if isinstance(world.protocols, ProtocolRegistry) else None
    covered = set()
    if registry is not None:
        for proto in registry.protocols_by_id.values():
            covered.update(proto.covered_location_ids)

    uncovered_edges = [edge for edge in dangerous_edge_ids if edge not in covered]
    if not uncovered_edges:
        return False

    scribe = next(iter(world.agents.values()), None)
    if scribe is None:
        return False

    author_goal = Goal(
        goal_id=make_goal_id(),
        owner_id=scribe.agent_id,
        goal_type=GoalType.AUTHOR_PROTOCOL,
        description=f"Draft movement/safety protocol for: {', '.join(uncovered_edges)}",
        target={"corridor_ids": uncovered_edges, "edge_ids": uncovered_edges},
        priority=0.95,
        urgency=0.95,
        horizon=GoalHorizon.MEDIUM,
        status=GoalStatus.ACTIVE,
        created_at_tick=tick,
        last_updated_tick=tick,
        origin=GoalOrigin.OPPORTUNITY,
    )
    handle_protocol_authoring(world, scribe, author_goal, uncovered_edges)
    return True


__all__ = ["handle_protocol_authoring", "maybe_author_movement_protocols"]
