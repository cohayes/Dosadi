"""Agent MVP core data structures and helpers (D-AGENT-0022)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
import random


class GoalType(str, Enum):
    MAINTAIN_SURVIVAL = "MAINTAIN_SURVIVAL"
    ACQUIRE_RESOURCE = "ACQUIRE_RESOURCE"
    SECURE_SHELTER = "SECURE_SHELTER"
    MAINTAIN_RELATIONSHIPS = "MAINTAIN_RELATIONSHIPS"
    REDUCE_POD_RISK = "REDUCE_POD_RISK"
    FORM_GROUP = "FORM_GROUP"
    STABILIZE_POD = "STABILIZE_POD"
    GATHER_INFORMATION = "GATHER_INFORMATION"
    AUTHOR_PROTOCOL = "AUTHOR_PROTOCOL"
    ORGANIZE_GROUP = "ORGANIZE_GROUP"


class GoalStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"
    BLOCKED = "BLOCKED"


class GoalOrigin(str, Enum):
    INTERNAL_STATE = "INTERNAL_STATE"
    ORDER = "ORDER"
    PROTOCOL = "PROTOCOL"
    GROUP_DECISION = "GROUP_DECISION"
    OPPORTUNITY = "OPPORTUNITY"


class GoalHorizon(str, Enum):
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    LONG = "LONG"


@dataclass
class Goal:
    """MVP Goal representation for Dosadi agents."""

    goal_id: str
    owner_id: str

    goal_type: GoalType
    description: str = ""

    parent_goal_id: Optional[str] = None

    target: Dict[str, Any] = field(default_factory=dict)

    priority: float = 0.5
    urgency: float = 0.0
    horizon: GoalHorizon = GoalHorizon.SHORT

    status: GoalStatus = GoalStatus.PENDING

    created_at_tick: int = 0
    deadline_tick: Optional[int] = None
    last_updated_tick: int = 0

    origin: GoalOrigin = GoalOrigin.INTERNAL_STATE
    source_ref: Optional[str] = None

    assigned_to: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def score_for_selection(self) -> float:
        """Simple scalar score for goal selection."""

        p = max(0.0, min(1.0, self.priority))
        u = max(0.0, min(1.0, self.urgency))
        return p * (0.5 + 0.5 * u)


def make_goal_id(prefix: str = "goal") -> str:
    return f"{prefix}:{uuid.uuid4().hex}"


class EpisodeSourceType(str, Enum):
    DIRECT = "DIRECT"
    HEARD_RUMOR = "HEARD_RUMOR"
    READ_PROTOCOL = "READ_PROTOCOL"
    RECEIVED_ORDER = "RECEIVED_ORDER"
    RECEIVED_REPORT = "RECEIVED_REPORT"
    WATCHED_THEATER = "WATCHED_THEATER"


@dataclass
class EpisodeGoalDelta:
    goal_id: str
    pre_status: GoalStatus
    post_status: GoalStatus
    delta_progress: float = 0.0


@dataclass
class Episode:
    """Subjective record of an event from one agent's perspective."""

    episode_id: str
    owner_id: str

    event_id: Optional[str] = None

    tick_start: int = 0
    tick_end: int = 0

    location_id: Optional[str] = None
    context_tags: List[str] = field(default_factory=list)

    source_type: EpisodeSourceType = EpisodeSourceType.DIRECT
    source_agent_id: Optional[str] = None

    participants: List[Dict[str, Any]] = field(default_factory=list)

    event_type: str = ""
    summary: str = ""

    goals_involved: List[EpisodeGoalDelta] = field(default_factory=list)

    outcome: Dict[str, Any] = field(default_factory=dict)

    valence: float = 0.0
    arousal: float = 0.0
    dominant_feeling: Optional[str] = None

    perceived_risk: float = 0.0
    perceived_reliability: float = 1.0

    privacy: str = "PRIVATE"
    tags: List[str] = field(default_factory=list)


def make_episode_id(owner_id: str) -> str:
    return f"ep:{owner_id}:{uuid.uuid4().hex}"


@dataclass
class PlaceBelief:
    """Subjective belief about a single place/location."""

    owner_id: str
    place_id: str

    danger_score: float = 0.0
    enforcement_score: float = 0.0
    opportunity_score: float = 0.0

    last_updated_tick: int = 0

    def update_from_episode(self, episode: Episode, learning_rate: float = 0.3) -> None:
        if episode.location_id != self.place_id:
            return

        is_hazard = "hazard" in (episode.tags or []) or episode.event_type in {
            "HAZARD_INCIDENT",
            "HAZARD_NEAR_MISS",
        }

        target_danger = 1.0 if is_hazard else 0.0
        self.danger_score += learning_rate * (target_danger - self.danger_score)
        self.danger_score = max(0.0, min(1.0, self.danger_score))
        self.last_updated_tick = max(self.last_updated_tick, episode.tick_end)


@dataclass
class Attributes:
    """Physical and mental attributes, roughly centered on 10."""

    STR: int = 10
    DEX: int = 10
    END: int = 10
    INT: int = 10
    WIL: int = 10
    CHA: int = 10


@dataclass
class Personality:
    """MVP personality traits relevant to early decision-making."""

    bravery: float = 0.5
    communal: float = 0.5
    ambition: float = 0.5
    curiosity: float = 0.5
    trusting: float = 0.5

    leadership_weight: float = 0.5


@dataclass
class PhysicalState:
    """Physical and psychological state variables."""

    health: float = 1.0
    fatigue: float = 0.0
    hunger: float = 0.0
    thirst: float = 0.0
    stress: float = 0.0
    morale: float = 0.5


@dataclass
class AgentState:
    """MVP agent representation used in the Founding Wakeup scenario."""

    agent_id: str

    name: str
    tier: int = 1
    roles: List[str] = field(default_factory=lambda: ["colonist"])
    ward: Optional[str] = None

    attributes: Attributes = field(default_factory=Attributes)
    personality: Personality = field(default_factory=Personality)
    physical: PhysicalState = field(default_factory=PhysicalState)

    location_id: str = "loc:pod-1"

    goals: List[Goal] = field(default_factory=list)
    episodes: List[Episode] = field(default_factory=list)

    place_beliefs: Dict[str, PlaceBelief] = field(default_factory=dict)

    known_protocols: List[str] = field(default_factory=list)

    last_decision_tick: int = 0

    @property
    def id(self) -> str:
        """Alias for agent_id to ease integration with WorldState registries."""

        return self.agent_id

    def get_or_create_place_belief(self, place_id: str) -> PlaceBelief:
        if place_id not in self.place_beliefs:
            self.place_beliefs[place_id] = PlaceBelief(
                owner_id=self.agent_id,
                place_id=place_id,
            )
        return self.place_beliefs[place_id]

    def record_episode(self, episode: Episode) -> None:
        self.episodes.append(episode)

    def update_beliefs_from_episode(self, episode: Episode) -> None:
        if episode.location_id:
            pb = self.get_or_create_place_belief(episode.location_id)
            pb.update_from_episode(episode)

    def choose_focus_goal(self) -> Optional[Goal]:
        if not self.goals:
            return None
        return max(self.goals, key=lambda g: g.score_for_selection())


def create_agent(agent_id: str, name: str, pod_location_id: str, rng: Any) -> AgentState:
    """
    Create a new MVP AgentState with randomized attributes and personality.

    - Places the agent in the given pod_location_id (e.g. "loc:pod-1").
    - Initializes attributes and personality with small random variation.
    - Seeds the goal stack with:
      - MAINTAIN_SURVIVAL (parent)
      - ACQUIRE_RESOURCE
      - SECURE_SHELTER
      - Optionally REDUCE_POD_RISK for some leadership-inclined agents.
    """

    def rand_attr() -> int:
        return (
            max(6, min(14, int(round(rng.normalvariate(10, 1)))))
            if hasattr(rng, "normalvariate")
            else rng.randint(8, 12)
        )

    attrs = Attributes(
        STR=rand_attr(),
        DEX=rand_attr(),
        END=rand_attr(),
        INT=rand_attr(),
        WIL=rand_attr(),
        CHA=rand_attr(),
    )

    def rand_trait() -> float:
        return max(0.0, min(1.0, 0.5 + rng.uniform(-0.2, 0.2)))

    personality = Personality(
        bravery=rand_trait(),
        communal=rand_trait(),
        ambition=rand_trait(),
        curiosity=rand_trait(),
        trusting=rand_trait(),
        leadership_weight=max(0.0, min(1.0, 0.5 + rng.uniform(-0.3, 0.3))),
    )

    agent = AgentState(
        agent_id=agent_id,
        name=name,
        tier=1,
        roles=["colonist"],
        ward=None,
        attributes=attrs,
        personality=personality,
        physical=PhysicalState(),
        location_id=pod_location_id,
    )

    survival_goal = Goal(
        goal_id=make_goal_id(),
        owner_id=agent_id,
        goal_type=GoalType.MAINTAIN_SURVIVAL,
        description="Stay alive and functional today.",
        priority=1.0,
        urgency=0.3,
        horizon=GoalHorizon.SHORT,
        status=GoalStatus.ACTIVE,
    )

    acquire_resource = Goal(
        goal_id=make_goal_id(),
        owner_id=agent_id,
        goal_type=GoalType.ACQUIRE_RESOURCE,
        description="Acquire necessary resources to support survival.",
        parent_goal_id=survival_goal.goal_id,
        priority=0.7,
        urgency=0.2,
        horizon=GoalHorizon.SHORT,
        status=GoalStatus.ACTIVE,
    )

    secure_shelter = Goal(
        goal_id=make_goal_id(),
        owner_id=agent_id,
        goal_type=GoalType.SECURE_SHELTER,
        description="Maintain access to a safe bunk/pod.",
        parent_goal_id=survival_goal.goal_id,
        priority=0.6,
        urgency=0.1,
        horizon=GoalHorizon.MEDIUM,
        status=GoalStatus.ACTIVE,
    )

    agent.goals.extend([survival_goal, acquire_resource, secure_shelter])

    if personality.communal > 0.6 and personality.leadership_weight > 0.6:
        reduce_pod_risk = Goal(
            goal_id=make_goal_id(),
            owner_id=agent_id,
            goal_type=GoalType.REDUCE_POD_RISK,
            description="Reduce physical risk to pod members.",
            priority=0.75,
            urgency=0.3,
            horizon=GoalHorizon.MEDIUM,
            status=GoalStatus.ACTIVE,
        )
        agent.goals.append(reduce_pod_risk)

    return agent


def initialize_agents_for_founding_wakeup(
    num_agents: int, seed: int, pod_ids: List[str]
) -> List[AgentState]:
    """
    Helper to create a list of AgentState for the Founding Wakeup MVP.

    - Distributes agents approximately evenly across the given pod_ids.
    - Uses the provided seed for reproducible randomness.
    """

    rng = random.Random(seed)

    agents: List[AgentState] = []
    num_pods = len(pod_ids)

    for i in range(num_agents):
        pod_location_id = pod_ids[i % num_pods]
        agent_id = f"agent:{i}"
        name = f"Colonist {i}"
        agent = create_agent(
            agent_id=agent_id, name=name, pod_location_id=pod_location_id, rng=rng
        )
        agents.append(agent)

    return agents


__all__ = [
    "AgentState",
    "Attributes",
    "Episode",
    "EpisodeGoalDelta",
    "EpisodeSourceType",
    "Goal",
    "GoalHorizon",
    "GoalOrigin",
    "GoalStatus",
    "GoalType",
    "PhysicalState",
    "Personality",
    "PlaceBelief",
    "create_agent",
    "initialize_agents_for_founding_wakeup",
    "make_episode_id",
    "make_goal_id",
]
