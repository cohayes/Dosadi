"""Agent MVP core data structures and helpers (D-AGENT-0022)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple
import uuid
import random

from dosadi.memory.episodes import EpisodeBuffers, EpisodeChannel
from dosadi.systems.protocols import (
    ProtocolRegistry,
    compute_effective_hazard_prob,
    create_movement_protocol_from_goal,
    activate_protocol,
    record_protocol_read,
)


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

        p = max(0.0, min(1.0, float(self.priority)))
        u = max(0.0, min(1.0, float(self.urgency)))
        return p + u


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

    fairness_score: float = 0.0
    efficiency_score: float = 0.0
    safety_score: float = 0.0
    congestion_score: float = 0.0
    reliability_score: float = 0.0

    danger_score: float = 0.0
    enforcement_score: float = 0.0
    opportunity_score: float = 0.0

    alpha: float = 0.1

    last_updated_tick: int = 0

    def _nudge(self, field_name: str, impact: float, alpha: Optional[float] = None) -> None:
        """
        Exponential moving average update with clamping to [-1.0, +1.0].

        new = old * (1 - alpha) + impact * alpha
        """

        if impact == 0.0:
            return

        if alpha is None:
            alpha = self.alpha

        old = getattr(self, field_name, 0.0)
        new = old * (1.0 - alpha) + impact * alpha

        if new > 1.0:
            new = 1.0
        elif new < -1.0:
            new = -1.0

        setattr(self, field_name, new)

    def update_from_episode(self, episode: Episode, learning_rate: float = 0.3) -> None:
        # Location/target relevance check
        ep_location = getattr(episode, "location_id", None)
        ep_target = getattr(episode, "target_id", None)

        if ep_location not in (None, ""):
            if ep_location != self.place_id:
                if ep_target != self.place_id:
                    return
        elif ep_target != self.place_id:
            return

        # Episode weight computation
        base_importance = getattr(episode, "importance", 0.0)
        base_reliability = getattr(episode, "reliability", 0.5)

        channel = getattr(episode, "channel", None)
        if channel == EpisodeChannel.DIRECT:
            channel_multiplier = 1.0
        elif channel == EpisodeChannel.OBSERVED:
            channel_multiplier = 0.75
        elif channel == EpisodeChannel.REPORT:
            channel_multiplier = 0.6
        elif channel == EpisodeChannel.RUMOR:
            channel_multiplier = 0.4
        elif channel == EpisodeChannel.PROTOCOL:
            channel_multiplier = 0.5
        elif channel == EpisodeChannel.BODY_SIGNAL:
            channel_multiplier = 1.0
        else:
            channel_multiplier = 0.5

        emotion = getattr(episode, "emotion", None)
        arousal = getattr(emotion, "arousal", 0.0) if emotion is not None else 0.0
        arousal_multiplier = 0.5 + 0.5 * max(0.0, min(1.0, arousal))

        episode_weight = (
            base_importance * base_reliability * channel_multiplier * arousal_multiplier
        )

        if episode_weight < 0.01:
            return

        role_scale = 1.0 if channel == EpisodeChannel.DIRECT else 0.5
        weight = episode_weight
        scale = role_scale

        tags = getattr(episode, "tags", None) or set()
        details = getattr(episode, "details", None) or {}

        if "queue_served" in tags:
            fairness_base = 0.2

            wait = details.get("wait_ticks", 0)
            if wait <= 50:
                efficiency_base = 0.2
            elif wait <= 200:
                efficiency_base = 0.1
            else:
                efficiency_base = 0.05

            reliability_base = 0.1

            self._nudge("fairness_score", fairness_base * weight * scale)
            self._nudge("efficiency_score", efficiency_base * weight * scale)
            self._nudge("reliability_score", reliability_base * weight * scale)

        if "queue_denied" in tags:
            fairness_base = -0.4
            reliability_base = -0.4

            threat = getattr(emotion, "threat", 0.0) if emotion is not None else 0.0
            safety_base = -0.1 * max(0.0, min(1.0, threat))

            self._nudge("fairness_score", fairness_base * weight * scale)
            self._nudge("reliability_score", reliability_base * weight * scale)
            if safety_base != 0.0:
                self._nudge("safety_score", safety_base * weight * scale)

        if "queue_canceled" in tags:
            efficiency_base = -0.3
            reliability_base = -0.3
            fairness_base = -0.1

            self._nudge("efficiency_score", efficiency_base * weight * scale)
            self._nudge("reliability_score", reliability_base * weight * scale)
            self._nudge("fairness_score", fairness_base * weight * scale)

        if "queue_fight" in tags:
            safety_base = -0.6
            congestion_base = 0.1
            fairness_base = -0.1 if "guard_brutal" in tags else 0.0

            self._nudge("safety_score", safety_base * weight * scale)
            self._nudge("congestion_score", congestion_base * weight * scale)
            if fairness_base != 0.0:
                self._nudge("fairness_score", fairness_base * weight * scale)

        is_hazard = "hazard" in tags or getattr(episode, "event_type", "") in {
            "HAZARD_INCIDENT",
            "HAZARD_NEAR_MISS",
        }

        target_danger = 1.0 if is_hazard else 0.0
        self.danger_score += learning_rate * (target_danger - self.danger_score)
        self.danger_score = max(0.0, min(1.0, self.danger_score))

        tick_end = getattr(episode, "tick_end", getattr(episode, "tick", 0))
        self.last_updated_tick = max(self.last_updated_tick, tick_end)


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

    home: Optional[str] = None

    attributes: Attributes = field(default_factory=Attributes)
    personality: Personality = field(default_factory=Personality)
    physical: PhysicalState = field(default_factory=PhysicalState)

    location_id: str = "loc:pod-1"
    navigation_target_id: Optional[str] = None
    current_queue_id: Optional[str] = None
    queue_join_tick: Optional[int] = None

    has_basic_suit: bool = False
    assignment_role: Optional[str] = None
    bunk_location_id: Optional[str] = None

    goals: List[Goal] = field(default_factory=list)
    episodes: EpisodeBuffers = field(default_factory=EpisodeBuffers)

    place_beliefs: Dict[str, PlaceBelief] = field(default_factory=dict)

    known_protocols: List[str] = field(default_factory=list)

    last_decision_tick: int = 0
    rest_ticks_in_pod: int = 0

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
        """
        Record an episode for this agent.

        - Route all episode writes through EpisodeBuffers.push_short_term so that
          capacity rules and eviction behavior are respected.
        - Belief updates are now handled by sleep-time consolidation via
          consolidate_daily_memory(), not here.
        """
        self.episodes.push_short_term(episode)

    def update_beliefs_from_episode(self, episode: Episode) -> None:
        if episode.location_id:
            pb = self.get_or_create_place_belief(episode.location_id)
            pb.update_from_episode(episode)

    def promote_short_term_episodes(self) -> None:
        """
        Promote important short-term episodes into the daily buffer.

        This is a v0 heuristic that looks at episode importance, goal relevance,
        and threat level to decide what to keep for sleep-time consolidation.
        """
        # We take a snapshot of short_term so we don't mutate while iterating.
        for episode in list(self.episodes.short_term):
            # Simple scoring heuristic; can be refined later.
            score = (
                episode.importance
                + 0.5 * episode.goal_relevance
                + 0.5 * episode.emotion.threat
            )

            # v0 threshold; can later be a config constant or derived from traits.
            if score >= 0.6:
                self.episodes.promote_to_daily(episode)

    def consolidate_daily_memory(self) -> None:
        """
        Integrate daily-buffer episodes into beliefs, then clear the buffer.

        This is the sleep-time consolidation step: daily episodes are turned
        into belief updates, and the daily buffer is reset.
        """
        if not self.episodes.daily:
            return

        for episode in self.episodes.daily:
            self.update_beliefs_from_episode(episode)

        self.episodes.daily.clear()

    def choose_focus_goal(self) -> Optional[Goal]:
        """
        Pick the current focus goal for an agent.

        - Prefer goals that are ACTIVE.
        - If there are no ACTIVE goals, fall back to PENDING goals.
        - When a PENDING goal is chosen, promote it to ACTIVE so the agent
          actually starts working on it.
        - Ignore COMPLETED / FAILED / ABANDONED goals.
        """
        if not self.goals:
            return None

        non_terminal = [
            g
            for g in self.goals
            if g.status
            not in (
                GoalStatus.COMPLETED,
                GoalStatus.FAILED,
                GoalStatus.ABANDONED,
            )
        ]
        if not non_terminal:
            return None

        active = [g for g in non_terminal if g.status == GoalStatus.ACTIVE]
        pending = [g for g in non_terminal if g.status == GoalStatus.PENDING]

        pool = active if active else pending
        if not pool:
            return None

        best = max(pool, key=lambda g: g.score_for_selection())

        if best.status == GoalStatus.PENDING:
            best.status = GoalStatus.ACTIVE

        return best


@dataclass
class Action:
    """Lightweight action representation for the MVP decision loop."""

    actor_id: str
    verb: str
    target_location_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_goal_id: Optional[str] = None


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
        home=pod_location_id,
        attributes=attrs,
        personality=personality,
        physical=PhysicalState(),
        location_id=pod_location_id,
    )

    def jitter_pair(priority_base: float, urgency_base: float) -> Tuple[float, float]:
        def clamp(val: float) -> float:
            return max(0.0, min(1.0, val))

        priority_delta = rng.uniform(-0.15, 0.15)
        urgency_delta = rng.uniform(-0.1, 0.1)
        return clamp(priority_base + priority_delta), clamp(urgency_base + urgency_delta)

    survival_priority, survival_urgency = jitter_pair(1.0, 0.3)
    survival_goal = Goal(
        goal_id=make_goal_id(),
        owner_id=agent_id,
        goal_type=GoalType.MAINTAIN_SURVIVAL,
        description="Stay alive and functional today.",
        priority=survival_priority,
        urgency=survival_urgency,
        horizon=GoalHorizon.SHORT,
        status=GoalStatus.ACTIVE,
    )

    acquire_priority, acquire_urgency = jitter_pair(0.7, 0.2)
    acquire_resource = Goal(
        goal_id=make_goal_id(),
        owner_id=agent_id,
        goal_type=GoalType.ACQUIRE_RESOURCE,
        description="Acquire necessary resources to support survival.",
        parent_goal_id=survival_goal.goal_id,
        priority=acquire_priority,
        urgency=acquire_urgency,
        horizon=GoalHorizon.SHORT,
        status=GoalStatus.ACTIVE,
    )

    shelter_priority, shelter_urgency = jitter_pair(0.6, 0.1)
    secure_shelter = Goal(
        goal_id=make_goal_id(),
        owner_id=agent_id,
        goal_type=GoalType.SECURE_SHELTER,
        description="Maintain access to a safe bunk/pod.",
        parent_goal_id=survival_goal.goal_id,
        priority=shelter_priority,
        urgency=shelter_urgency,
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

    core_types = {
        GoalType.MAINTAIN_SURVIVAL,
        GoalType.ACQUIRE_RESOURCE,
        GoalType.SECURE_SHELTER,
    }
    for goal in agent.goals:
        if goal.goal_type in core_types:
            goal.status = GoalStatus.ACTIVE

    return agent


def _topology_from_world(world: Any) -> Dict[str, Any]:
    policy = getattr(world, "policy", {}) or {}
    if isinstance(policy, dict) and policy.get("topology"):
        return policy.get("topology", {})

    nodes = getattr(world, "nodes", None)
    edges = getattr(world, "edges", None)
    if nodes or edges:
        node_values = list(nodes.values()) if isinstance(nodes, dict) else []
        edge_values = list(edges.values()) if isinstance(edges, dict) else []
        return {
            "nodes": [n if isinstance(n, dict) else n.__dict__ for n in node_values],
            "edges": [e if isinstance(e, dict) else e.__dict__ for e in edge_values],
        }

    return {}


def _build_neighbors(topology: Dict[str, Any]) -> Dict[str, List[str]]:
    neighbors: Dict[str, List[str]] = {}
    for edge in topology.get("edges", []) or []:
        a = edge.get("a")
        b = edge.get("b")
        if not a or not b:
            continue
        neighbors.setdefault(a, []).append(b)
        neighbors.setdefault(b, []).append(a)
    return neighbors


def _find_well_core_id(topology: Dict[str, Any]) -> Optional[str]:
    for node in topology.get("nodes", []) or []:
        if node.get("is_well_core"):
            return node.get("id")
    return None


def prepare_navigation_context(world: Any) -> Tuple[Dict[str, Any], Dict[str, List[str]], str, Any]:
    """
    Build reusable navigation primitives for a single decision tick.

    This keeps repeated calls to _topology_from_world / _build_neighbors /
    random.Random creation from occurring once per agent when the same world
    snapshot is used across many agents in a tick.
    """

    topology = _topology_from_world(world)
    neighbors = _build_neighbors(topology)
    well_core_id = _find_well_core_id(topology) or "loc:well-core"
    rng = getattr(world, "rng", None) or random.Random(getattr(world, "seed", 0))

    return topology, neighbors, well_core_id, rng


def _edge_hazard_probability(current: str, target: str, topology: Dict[str, Any]) -> float:
    for edge in topology.get("edges", []) or []:
        a = edge.get("a")
        b = edge.get("b")
        if {a, b} == {current, target}:
            return float(edge.get("base_hazard_prob", 0.0))
    return 0.0


def _edge_lookup(current: str, target: str, topology: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for edge in topology.get("edges", []) or []:
        a = edge.get("a")
        b = edge.get("b")
        if {a, b} == {current, target}:
            return edge
    return None


def decide_next_action(
    agent: AgentState,
    world: "WorldState",
    *,
    topology: Optional[Dict[str, Any]] = None,
    neighbors: Optional[Dict[str, List[str]]] = None,
    well_core_id: Optional[str] = None,
    rng: Optional[Any] = None,
) -> Action:
    """Select a coarse next action using goals, beliefs, and topology hints."""

    focus_goal = agent.choose_focus_goal()
    topology = topology or _topology_from_world(world)
    neighbors = neighbors or _build_neighbors(topology)
    well_core_id = well_core_id or _find_well_core_id(topology) or "loc:well-core"
    rng = rng or getattr(world, "rng", None) or random.Random(getattr(world, "seed", 0))

    def best_neighbor_location() -> Optional[str]:
        options = neighbors.get(agent.location_id, [])
        if not options:
            return None
        scored = []
        for loc in options:
            belief = agent.place_beliefs.get(loc)
            danger = belief.danger_score if belief else 0.0
            scored.append((danger, loc))
        scored.sort(key=lambda pair: pair[0])
        return scored[0][1]

    if focus_goal and focus_goal.goal_type == GoalType.GATHER_INFORMATION:
        options = neighbors.get(agent.location_id, [])
        target_loc = rng.choice(options) if options else None
        if target_loc:
            return Action(
                actor_id=agent.agent_id,
                verb="MOVE",
                target_location_id=target_loc,
                related_goal_id=focus_goal.goal_id,
            )

    if focus_goal and focus_goal.goal_type == GoalType.SECURE_SHELTER:
        home_location = agent.home or agent.location_id
        if agent.location_id != home_location:
            target_loc = home_location if home_location in neighbors.get(agent.location_id, []) else best_neighbor_location()
            if target_loc:
                return Action(
                    actor_id=agent.agent_id,
                    verb="MOVE",
                    target_location_id=target_loc,
                    related_goal_id=focus_goal.goal_id,
                )

    if focus_goal and focus_goal.goal_type in {
        GoalType.ACQUIRE_RESOURCE,
        GoalType.FORM_GROUP,
        GoalType.STABILIZE_POD,
    }:
        if agent.location_id != well_core_id:
            target_loc = well_core_id if well_core_id in neighbors.get(agent.location_id, []) else best_neighbor_location()
            if target_loc:
                return Action(
                    actor_id=agent.agent_id,
                    verb="MOVE",
                    target_location_id=target_loc,
                    related_goal_id=focus_goal.goal_id,
                )

    if focus_goal and focus_goal.goal_type in {
        GoalType.MAINTAIN_RELATIONSHIPS,
        GoalType.ORGANIZE_GROUP,
        GoalType.REDUCE_POD_RISK,
    }:
        return Action(
            actor_id=agent.agent_id,
            verb="POD_MEETING",
            target_location_id=agent.location_id,
            related_goal_id=focus_goal.goal_id,
        )

    if focus_goal and focus_goal.goal_type == GoalType.AUTHOR_PROTOCOL:
        target_payload = focus_goal.target or {}
        corridor_ids = (
            target_payload.get("corridor_ids")
            or target_payload.get("edge_ids")
            or []
        )
        return Action(
            actor_id=agent.agent_id,
            verb="AUTHOR_PROTOCOL",
            target_location_id=agent.location_id,
            metadata={
                "corridor_ids": corridor_ids,
                "council_group_id": target_payload.get("council_group_id"),
            },
            related_goal_id=focus_goal.goal_id,
        )

    if agent.location_id == well_core_id and focus_goal and focus_goal.goal_type == GoalType.FORM_GROUP:
        return Action(
            actor_id=agent.agent_id,
            verb="COUNCIL_MEETING",
            target_location_id=well_core_id,
            related_goal_id=focus_goal.goal_id,
        )

    return Action(
        actor_id=agent.agent_id,
        verb="REST_IN_POD",
        target_location_id=agent.location_id,
        related_goal_id=focus_goal.goal_id if focus_goal else None,
    )



def apply_action(agent: AgentState, action: Action, world: "WorldState", tick: int) -> Sequence[Episode]:
    """Apply the chosen action, logging episodes and updating beliefs."""

    rng = getattr(world, "rng", None) or random.Random(getattr(world, "seed", 0))
    topology = _topology_from_world(world)
    episodes: List[Episode] = []

    goal_ref: Optional[Goal] = None
    if action.related_goal_id:
        goal_ref = next((g for g in agent.goals if g.goal_id == action.related_goal_id), None)

    def goal_delta() -> List[EpisodeGoalDelta]:
        if not goal_ref:
            return []
        return [
            EpisodeGoalDelta(
                goal_id=goal_ref.goal_id,
                pre_status=goal_ref.status,
                post_status=goal_ref.status,
                delta_progress=0.0,
            )
        ]

    def log_episode(
        *,
        event_type: str,
        summary: str,
        location_id: Optional[str],
        tags: Optional[List[str]] = None,
        valence: float = 0.0,
        arousal: float = 0.0,
        perceived_risk: float = 0.0,
    ) -> Episode:
        episode = Episode(
            episode_id=make_episode_id(agent.agent_id),
            owner_id=agent.agent_id,
            event_id=None,
            tick_start=tick,
            tick_end=tick,
            location_id=location_id,
            context_tags=[],
            source_type=EpisodeSourceType.DIRECT,
            source_agent_id=None,
            participants=[],
            event_type=event_type,
            summary=summary,
            goals_involved=goal_delta(),
            outcome={},
            valence=valence,
            arousal=arousal,
            dominant_feeling=None,
            perceived_risk=perceived_risk,
            perceived_reliability=1.0,
            privacy="PRIVATE",
            tags=tags or [],
        )
        agent.record_episode(episode)
        episodes.append(episode)
        return episode

    if action.verb == "MOVE":
        target = action.target_location_id or agent.location_id
        edge = _edge_lookup(agent.location_id, target, topology)
        base_hazard_prob = 0.0 if edge is None else float(edge.get("base_hazard_prob", 0.0))
        # TODO: support explicit group travel and compliance decisions in movement selection
        group_size = 1
        registry: Optional[ProtocolRegistry] = getattr(world, "protocols", None)
        hazard_prob = compute_effective_hazard_prob(
            agent=agent,
            location_id=target,
            base_hazard_prob=base_hazard_prob,
            group_size=group_size,
            registry=registry,
        )
        edge_id = None
        if edge:
            edge_id = edge.get("id") or f"edge:{edge.get('a')}:{edge.get('b')}"
        else:
            edge_id = f"edge:{agent.location_id}:{target}"

        agent.location_id = target
        log_episode(
            event_type="MOVEMENT",
            summary=f"Moved to {target}",
            location_id=target,
            tags=["movement"],
            valence=0.0,
            arousal=0.2,
            perceived_risk=hazard_prob,
        )
        traversals_key = f"traversals:{edge_id}"
        if hasattr(world, "metrics"):
            world.metrics[traversals_key] = world.metrics.get(traversals_key, 0.0) + 1.0
        if rng.random() < hazard_prob:
            agent.physical.health = max(0.0, agent.physical.health - 0.1)
            if hasattr(world, "metrics"):
                incidents_key = f"incidents:{edge_id}"
                world.metrics[incidents_key] = world.metrics.get(incidents_key, 0.0) + 1.0
            log_episode(
                event_type="HAZARD_INCIDENT",
                summary=f"Encountered hazard while moving to {target}",
                location_id=target,
                tags=["hazard"],
                valence=-0.7,
                arousal=0.8,
                perceived_risk=1.0,
            )
            if goal_ref and goal_ref.goal_type == GoalType.GATHER_INFORMATION:
                hazard_encounters = goal_ref.target.get("hazard_encounters", 0) + 1
                goal_ref.target["hazard_encounters"] = hazard_encounters
                if hazard_encounters >= 5:
                    goal_ref.status = GoalStatus.PENDING
                    goal_ref.priority = 0.05
                    goal_ref.urgency = 0.05
                    goal_ref.last_updated_tick = tick
    elif action.verb == "POD_MEETING":
        log_episode(
            event_type="POD_MEETING",
            summary="Participated in a pod meeting.",
            location_id=agent.location_id,
            tags=["meeting"],
            valence=0.1,
            arousal=0.3,
        )
    elif action.verb == "COUNCIL_MEETING":
        log_episode(
            event_type="COUNCIL_MEETING",
            summary="Attended a proto-council gathering at well core.",
            location_id=action.target_location_id or agent.location_id,
            tags=["meeting"],
            valence=0.15,
            arousal=0.4,
        )
    elif action.verb == "READ_PROTOCOL":
        protocol_id = action.metadata.get("protocol_id") if action.metadata else None
        registry: Optional[ProtocolRegistry] = getattr(world, "protocols", None)
        protocol = registry.get(protocol_id) if registry and protocol_id else None
        if protocol:
            read_episode = record_protocol_read(agent, protocol, tick)
            episodes.append(read_episode)
        else:
            if protocol_id and protocol_id not in agent.known_protocols:
                agent.known_protocols.append(protocol_id)
            log_episode(
                event_type="READ_PROTOCOL",
                summary="Reviewed station protocol.",
                location_id=agent.location_id,
                tags=["protocol"],
                valence=0.05,
                arousal=0.2,
            )
    elif action.verb == "AUTHOR_PROTOCOL":
        registry: Optional[ProtocolRegistry] = getattr(world, "protocols", None)
        corridors = action.metadata.get("corridor_ids", []) if action.metadata else []
        if goal_ref:
            corridors = goal_ref.target.get("corridor_ids", corridors)
        council_group_id = None
        if goal_ref:
            council_group_id = goal_ref.target.get("council_group_id")
        if registry and goal_ref:
            protocol = create_movement_protocol_from_goal(
                council_group_id=council_group_id or "group:council:alpha",
                scribe_agent_id=agent.agent_id,
                group_goal=goal_ref,
                corridors=corridors,
                tick=tick,
                registry=registry,
            )
            activate_protocol(protocol, tick=tick)
            log_episode(
                event_type="AUTHOR_PROTOCOL",
                summary="Drafted and activated a movement protocol.",
                location_id=agent.location_id,
                tags=["protocol", "authoring"],
                valence=0.2,
                arousal=0.4,
                perceived_risk=0.1,
            )
    elif action.verb == "REST_IN_POD":
        agent.rest_ticks_in_pod += 1
        log_episode(
            event_type=action.verb,
            summary=f"Took action {action.verb}.",
            location_id=agent.location_id,
            tags=["action"],
            valence=0.0,
            arousal=0.1,
        )
    else:
        log_episode(
            event_type=action.verb,
            summary=f"Took action {action.verb}.",
            location_id=agent.location_id,
            tags=["action"],
            valence=0.0,
            arousal=0.1,
        )

    if action.verb != "REST_IN_POD":
        agent.rest_ticks_in_pod = 0

    agent.last_decision_tick = tick
    return episodes


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
    "Action",
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
    "apply_action",
    "create_agent",
    "decide_next_action",
    "initialize_agents_for_founding_wakeup",
    "make_episode_id",
  "make_goal_id",
  "prepare_navigation_context",
]
