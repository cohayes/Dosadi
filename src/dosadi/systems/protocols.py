from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import uuid
from typing import Dict, List, Optional

from dosadi.agents.core import (
    AgentState,
    Episode,
    EpisodeSourceType,
    Goal,
    GoalHorizon,
    GoalOrigin,
    GoalStatus,
    GoalType,
    make_episode_id,
)


class ProtocolType(str, Enum):
    MOVEMENT = "MOVEMENT"
    TRAFFIC_AND_SAFETY = "TRAFFIC_AND_SAFETY"
    # Later: RATIONING, SURVEILLANCE, etc.


class ProtocolStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


@dataclass
class Protocol:
    """MVP movement/safety protocol.

    Focused on:
    - Which locations/edges it covers,
    - What movement pattern it prescribes,
    - How it modifies hazard odds when obeyed.
    """

    protocol_id: str
    protocol_type: ProtocolType
    name: str
    description: str

    status: ProtocolStatus = ProtocolStatus.DRAFT

    author_group_id: Optional[str] = None  # e.g. "group:council:alpha"
    author_agent_id: Optional[str] = None  # scribe or lead author

    created_at_tick: int = 0
    activated_at_tick: Optional[int] = None
    retired_at_tick: Optional[int] = None

    covered_location_ids: List[str] = field(default_factory=list)
    covered_edge_ids: List[str] = field(default_factory=list)  # optional, for later

    # Movement constraints (MVP)
    min_group_size: int = 1
    max_group_size: Optional[int] = None
    allowed_ticks_modulo: Optional[int] = None  # e.g. every N ticks; None = any time

    # Hazard effect when compliant
    compliant_hazard_multiplier: float = 0.5  # < 1 reduces risk
    # Optional extra risk when violating
    violation_hazard_multiplier: float = 1.0  # >= 1 increases risk

    tags: List[str] = field(default_factory=list)

    times_read: int = 0
    times_referenced: int = 0


def make_protocol_id(prefix: str = "protocol") -> str:
    return f"{prefix}:{uuid.uuid4().hex}"


@dataclass
class ProtocolRegistry:
    """In-memory registry of protocols for the MVP."""

    protocols_by_id: Dict[str, Protocol] = field(default_factory=dict)

    def add_protocol(self, protocol: Protocol) -> None:
        self.protocols_by_id[protocol.protocol_id] = protocol

    def get(self, protocol_id: str) -> Optional[Protocol]:
        return self.protocols_by_id.get(protocol_id)

    def active_protocols_for_location(self, location_id: str) -> List[Protocol]:
        return [
            p
            for p in self.protocols_by_id.values()
            if p.status == ProtocolStatus.ACTIVE
            and location_id in p.covered_location_ids
        ]


# ---------------------------------------------------------------------------
# Protocol authoring
# ---------------------------------------------------------------------------


def create_movement_protocol_from_goal(
    council_group_id: str,
    scribe_agent_id: str,
    group_goal: Goal,
    corridors: List[str],
    tick: int,
    registry: ProtocolRegistry,
) -> Protocol:
    """Create a DRAFT movement/safety protocol from an AUTHOR_PROTOCOL group goal.

    - Uses default MVP values for min_group_size and multipliers.
    - Registers the protocol in the given registry.
    - Returns the new Protocol.
    """
    corr_str = ", ".join(sorted(corridors))
    name = f"Group travel protocol for {corr_str}"
    description = "Travel in groups to reduce hazard risk on corridors: " + corr_str

    if group_goal.goal_type == GoalType.AUTHOR_PROTOCOL:
        group_goal.status = GoalStatus.COMPLETED
        group_goal.last_updated_tick = tick

    protocol = Protocol(
        protocol_id=make_protocol_id(),
        protocol_type=ProtocolType.TRAFFIC_AND_SAFETY,
        name=name,
        description=description,
        status=ProtocolStatus.DRAFT,
        author_group_id=council_group_id,
        author_agent_id=scribe_agent_id,
        created_at_tick=tick,
        covered_location_ids=list(corridors),
        # MVP defaults from D-LAW-0013
        min_group_size=3,
        max_group_size=None,
        allowed_ticks_modulo=None,
        compliant_hazard_multiplier=0.5,
        violation_hazard_multiplier=1.0,
        tags=[group_goal.goal_id],
    )

    registry.add_protocol(protocol)
    return protocol


def activate_protocol(protocol: Protocol, tick: int) -> None:
    """Mark a protocol as ACTIVE and stamp activated_at_tick."""

    protocol.status = ProtocolStatus.ACTIVE
    protocol.activated_at_tick = tick


# ---------------------------------------------------------------------------
# Protocol awareness
# ---------------------------------------------------------------------------


def record_protocol_read(
    agent: AgentState,
    protocol: Protocol,
    tick: int,
) -> Episode:
    """Record that an agent has read/learned a protocol.

    - Adds protocol_id to agent.known_protocols (if not already present).
    - Increments protocol.times_read.
    - Returns a READ_PROTOCOL Episode (caller should append to agent.episodes).
    """

    if protocol.protocol_id not in agent.known_protocols:
        agent.known_protocols.append(protocol.protocol_id)

    protocol.times_read += 1

    ep = Episode(
        episode_id=make_episode_id(agent.agent_id),
        owner_id=agent.agent_id,
        event_id=None,
        tick_start=tick,
        tick_end=tick,
        location_id=None,  # caller may fill in a specific location if desired
        context_tags=["protocol", "movement", "safety"],
        source_type=EpisodeSourceType.READ_PROTOCOL,
        source_agent_id=None,
        participants=[{"agent_id": agent.agent_id}],
        event_type="READ_PROTOCOL",
        summary=f"Read protocol {protocol.protocol_id}: {protocol.name}",
        goals_involved=[],
        outcome={"protocol_id": protocol.protocol_id},
        valence=0.0,
        arousal=0.1,
        perceived_risk=0.0,
        perceived_reliability=1.0,
        privacy="PRIVATE",
        tags=["protocol"],
    )

    agent.record_episode(ep)
    return ep


# ---------------------------------------------------------------------------
# Movement hazard modifiers
# ---------------------------------------------------------------------------


def compute_effective_hazard_prob(
    agent: AgentState,
    location_id: str,
    base_hazard_prob: float,
    group_size: int,
    registry: Optional[ProtocolRegistry],
) -> float:
    """Return the effective per-traversal hazard probability for movement.

    - Looks up ACTIVE protocols covering location_id.
    - Computes a protocol multiplier according to MVP rules.
    - Returns base_hazard_prob * multiplier.
    """

    if registry is None:
        return base_hazard_prob

    applicable = registry.active_protocols_for_location(location_id)
    if not applicable:
        return base_hazard_prob

    compliant_multipliers: List[float] = []
    violated_multipliers: List[float] = []

    for p in applicable:
        size_ok = group_size >= p.min_group_size
        if p.max_group_size is not None:
            size_ok = size_ok and group_size <= p.max_group_size

        if size_ok:
            compliant_multipliers.append(p.compliant_hazard_multiplier)
        else:
            violated_multipliers.append(p.violation_hazard_multiplier)

    if compliant_multipliers:
        multiplier = min(compliant_multipliers)
    elif violated_multipliers:
        multiplier = max(violated_multipliers)
    else:
        multiplier = 1.0

    return base_hazard_prob * multiplier


__all__ = [
    "Protocol",
    "ProtocolRegistry",
    "ProtocolStatus",
    "ProtocolType",
    "activate_protocol",
    "compute_effective_hazard_prob",
    "create_movement_protocol_from_goal",
    "make_protocol_id",
    "record_protocol_read",
]
