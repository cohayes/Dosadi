"""Agent MVP core data structures and helpers (D-AGENT-0022)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple
import uuid
import random

from dosadi.agents.physiology import (
    compute_performance_multiplier,
    compute_specialization_multiplier,
    recover_sleep_pressure,
)
from dosadi.agents.work_history import (
    WorkHistory,
    WorkPreferences,
    ticks_to_proficiency,
    update_work_preference_after_shift,
)
from dosadi.memory.episodes import EpisodeBuffers, EpisodeChannel
from dosadi.memory.sleep_consolidation import consolidate_sleep_for_agent
from dosadi.runtime.admin_log import AdminLogEntry, create_admin_log_id
from dosadi.runtime.config import SUPERVISOR_REPORT_INTERVAL_TICKS
from dosadi.runtime.work_details import WorkDetailType, WORK_DETAIL_CATALOG
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
    GATHER_INFORMATION = "gather_information"
    AUTHOR_PROTOCOL = "AUTHOR_PROTOCOL"
    ORGANIZE_GROUP = "ORGANIZE_GROUP"
    WORK_DETAIL = "WORK_DETAIL"
    GET_MEAL_TODAY = "GET_MEAL_TODAY"
    GET_WATER_TODAY = "GET_WATER_TODAY"
    REST_TONIGHT = "REST_TONIGHT"
    WRITE_SUPERVISOR_REPORT = "WRITE_SUPERVISOR_REPORT"


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
    metadata: Dict[str, Any] = field(default_factory=dict)

    def score_for_selection(self) -> float:
        """Simple scalar score for goal selection."""

        p = max(0.0, min(1.0, float(self.priority)))
        u = max(0.0, min(1.0, float(self.urgency)))
        return p + u


def make_goal_id(prefix: str = "goal") -> str:
    return f"{prefix}:{uuid.uuid4().hex}"


def create_work_detail_goal(agent_id: str, work_type: "WorkDetailType", priority: float = 1.0) -> "Goal":
    """Create a WORK_DETAIL goal referencing a specific WorkDetailType."""

    return Goal(
        goal_id=make_goal_id("goal"),
        owner_id=agent_id,
        goal_type=GoalType.WORK_DETAIL,
        description=f"Work detail: {getattr(work_type, 'name', str(work_type))}",
        priority=priority,
        metadata={"work_detail_type": getattr(work_type, "name", str(work_type))},
    )


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
    comfort_score: float = 0.0

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
    hunger_level: float = 0.0  # 0.0 = satiated, 1.0+ = very hungry
    last_meal_tick: int = 0
    hydration_level: float = 1.0  # 1.0 = fully hydrated, 0.0 = severely dehydrated
    last_drink_tick: int = 0
    thirst: float = 0.0
    # Psychological load indicators
    stress_level: float = 0.0  # 0.0 = calm, 1.0 = max stressed
    morale_level: float = 0.7  # 0.0 = hopeless, 1.0 = very optimistic
    # Sleep state
    is_sleeping: bool = False
    sleep_pressure: float = 0.0
    last_sleep_tick: int = 0


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
    work_history: WorkHistory = field(default_factory=WorkHistory)
    work_preferences: WorkPreferences = field(default_factory=WorkPreferences)

    # If non-None, this agent is a Tier-2 supervisor for this work type.
    supervisor_work_type: Optional[WorkDetailType] = None

    # If non-None, the work type this agent would prefer to move into.
    desired_work_type: Optional[WorkDetailType] = None

    # Crew this supervisor leads, if any.
    supervisor_crew_id: Optional[str] = None

    # Last tick when a supervisor report was written.
    last_report_tick: int = 0

    # Simple seniority tracking for promotion ranking
    total_ticks_employed: float = 0.0

    # How many times this agent has been promoted (for future use)
    times_promoted: int = 0

    location_id: str = "loc:pod-1"
    navigation_target_id: Optional[str] = None
    current_queue_id: Optional[str] = None
    queue_join_tick: Optional[int] = None

    # Persistent crew affiliation for current primary work
    current_crew_id: Optional[str] = None

    # Sleep and memory scheduling
    is_asleep: bool = False

    next_sleep_tick: int = 0
    next_wake_tick: int = 0

    last_short_term_maintenance_tick: int = 0
    last_daily_promotion_tick: int = 0
    last_consolidation_tick: int = 0

    # Cadence tracking for chronic physiological goal updates (meal/water/rest)
    last_chronic_goal_tick: int = -1500

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

    if focus_goal and focus_goal.goal_type == GoalType.GET_MEAL_TODAY:
        _handle_get_meal_goal(world, agent, focus_goal, rng)
        return Action(
            actor_id=agent.agent_id,
            verb="REST_IN_POD",
            target_location_id=agent.location_id,
            related_goal_id=focus_goal.goal_id,
        )

    if focus_goal and focus_goal.goal_type == GoalType.GET_WATER_TODAY:
        _handle_get_water_goal(world, agent, focus_goal, rng)
        return Action(
            actor_id=agent.agent_id,
            verb="REST_IN_POD",
            target_location_id=agent.location_id,
            related_goal_id=focus_goal.goal_id,
        )

    if focus_goal and focus_goal.goal_type == GoalType.REST_TONIGHT:
        _handle_rest_goal(world, agent, focus_goal, rng)
        return Action(
            actor_id=agent.agent_id,
            verb="REST_IN_POD",
            target_location_id=agent.location_id,
            related_goal_id=focus_goal.goal_id,
        )

    if focus_goal and focus_goal.goal_type == GoalType.WRITE_SUPERVISOR_REPORT:
        _handle_write_supervisor_report(world, agent, focus_goal, rng)
        return Action(
            actor_id=agent.agent_id,
            verb="REST_IN_POD",
            target_location_id=agent.location_id,
            related_goal_id=focus_goal.goal_id,
        )

    if focus_goal and focus_goal.goal_type == GoalType.WORK_DETAIL:
        work_type_name = focus_goal.metadata.get("work_detail_type") if hasattr(focus_goal, "metadata") else None
        work_type = None
        try:
            if work_type_name:
                from dosadi.runtime.work_details import WorkDetailType

                work_type = WorkDetailType[work_type_name]
        except Exception:
            work_type = None

        _handle_work_detail_goal(
            world=world,
            agent=agent,
            goal=focus_goal,
            work_type=work_type,
            rng=rng,
        )
        return Action(
            actor_id=agent.agent_id,
            verb="REST_IN_POD",
            target_location_id=agent.location_id,
            related_goal_id=focus_goal.goal_id,
        )

    if focus_goal and focus_goal.goal_type == GoalType.GATHER_INFORMATION:
        _handle_scout_interior(world, agent, focus_goal, rng)
        return Action(
            actor_id=agent.agent_id,
            verb="REST_IN_POD",
            target_location_id=agent.location_id,
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


def _handle_work_detail_goal(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    work_type: Optional["WorkDetailType"],
    rng: random.Random,
) -> None:
    if work_type is None:
        return
    if work_type == WorkDetailType.SCOUT_INTERIOR:
        _handle_scout_interior(world, agent, goal, rng)
    elif work_type == WorkDetailType.INVENTORY_STORES:
        _handle_inventory_stores(world, agent, goal, rng)
    elif work_type == WorkDetailType.ENV_CONTROL:
        _handle_env_control(world, agent, goal, rng)
    elif work_type in (
        WorkDetailType.FOOD_PROCESSING_DETAIL,
        getattr(WorkDetailType, "FOOD_PROCESSING", WorkDetailType.FOOD_PROCESSING_DETAIL),
    ):
        _handle_food_processing(world, agent, goal, rng)
    elif work_type in (
        WorkDetailType.WATER_HANDLING,
        getattr(WorkDetailType, "WATER_HANDLING_DETAIL", WorkDetailType.WATER_HANDLING),
    ):
        _handle_water_handling(world, agent, goal, rng)
    else:
        return


def _handle_get_meal_goal(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    from dosadi.runtime.eating import GET_MEAL_GOAL_TIMEOUT_TICKS, choose_mess_hall_for_agent
    from dosadi.runtime.queues import join_facility_queue

    current_tick = getattr(world, "tick", 0)
    created_tick = getattr(goal, "created_at_tick", None)
    if created_tick is None:
        created_tick = goal.metadata.get("created_tick", current_tick)
        goal.created_at_tick = created_tick

    if current_tick - created_tick > GET_MEAL_GOAL_TIMEOUT_TICKS:
        goal.status = GoalStatus.FAILED
        return

    meta = goal.metadata
    target_hall_id = meta.get("target_mess_hall_id")

    if not target_hall_id:
        target_hall_id = choose_mess_hall_for_agent(world, agent, rng)
        if not target_hall_id:
            return
        meta["target_mess_hall_id"] = target_hall_id

    if agent.location_id != target_hall_id:
        _move_one_step_toward(world, agent, target_hall_id, rng)
        return

    join_facility_queue(world, target_hall_id, agent.id)
    if agent.current_queue_id != target_hall_id:
        agent.queue_join_tick = current_tick
    agent.current_queue_id = target_hall_id


def _handle_get_water_goal(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    from dosadi.runtime.eating import (
        GET_WATER_GOAL_TIMEOUT_TICKS,
        choose_water_source_for_agent,
    )

    current_tick = getattr(world, "tick", 0)
    created_tick = getattr(goal, "created_at_tick", None)
    if created_tick is None:
        created_tick = goal.metadata.get("created_tick", current_tick)
        goal.created_at_tick = created_tick

    if current_tick - created_tick > GET_WATER_GOAL_TIMEOUT_TICKS:
        goal.status = GoalStatus.FAILED
        return

    meta = goal.metadata
    target_place_id = meta.get("target_water_place_id")

    if not target_place_id:
        target_place_id = choose_water_source_for_agent(world, agent, rng)
        if not target_place_id:
            return
        meta["target_water_place_id"] = target_place_id

    if agent.location_id != target_place_id:
        _move_one_step_toward(world, agent, target_place_id, rng)
        return

    facility = world.facilities.get(target_place_id)
    if facility is None:
        goal.status = GoalStatus.FAILED
        return

    kind = getattr(facility, "kind", None)

    if kind == "water_tap":
        _attempt_drink_from_tap(world, agent, goal, target_place_id)
    elif kind == "mess_hall":
        _attempt_drink_from_mess_hall(world, agent, goal, target_place_id)
    else:
        goal.status = GoalStatus.FAILED


MIN_SLEEP_BLOCK_TICKS: int = 40_000
MAX_SLEEP_BLOCK_TICKS: int = 120_000

SLEEP_STRESS_RECOVERY_RATE: float = 1.0 / 10_000.0
SLEEP_MORALE_RECOVERY_RATE: float = 1.0 / 10_000.0

SLEEP_HUNGER_INCREASE_PER_TICK: float = 1.0 / 120_000.0
SLEEP_HYDRATION_DECAY_PER_TICK: float = 1.0 / 120_000.0


def _choose_sleep_place(
    world: "WorldState",
    agent: AgentState,
    rng: random.Random,
) -> Optional[str]:
    candidates: List[str] = []

    for fid, facility in world.facilities.items():
        if getattr(facility, "kind", None) == "bunk_pod":
            candidates.append(fid)

    if not candidates:
        return None

    if agent.home and agent.home in candidates and rng.random() < 0.8:
        return agent.home

    def utility(place_id: str) -> float:
        pb = agent.get_or_create_place_belief(place_id)
        return (
            0.5 * pb.safety_score
            + 0.4 * pb.comfort_score
            - 0.1 * pb.congestion_score
        )

    if rng.random() < 0.1:
        return rng.choice(candidates)

    best_id = None
    best_score = float("-inf")
    for fid in candidates:
        score = utility(fid)
        if score > best_score:
            best_score = score
            best_id = fid

    return best_id


def _apply_sleep_recovery_effects(world: "WorldState", agent: AgentState) -> None:
    physical = agent.physical
    if not physical.is_sleeping:
        return

    physical.stress_level -= SLEEP_STRESS_RECOVERY_RATE
    if physical.stress_level < 0.0:
        physical.stress_level = 0.0

    physical.morale_level += SLEEP_MORALE_RECOVERY_RATE
    if physical.morale_level > 1.0:
        physical.morale_level = 1.0

    physical.hunger_level += SLEEP_HUNGER_INCREASE_PER_TICK
    if physical.hunger_level < 0.0:
        physical.hunger_level = 0.0

    physical.hydration_level -= SLEEP_HYDRATION_DECAY_PER_TICK
    if physical.hydration_level < 0.0:
        physical.hydration_level = 0.0


def _handle_rest_goal(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    physical = agent.physical
    meta = goal.metadata

    if "sleep_ticks_remaining" not in meta:
        sleep_ticks = rng.randint(MIN_SLEEP_BLOCK_TICKS, MAX_SLEEP_BLOCK_TICKS)
        meta["sleep_ticks_remaining"] = float(sleep_ticks)

        sleep_place_id = _choose_sleep_place(world, agent, rng)
        if sleep_place_id is None:
            goal.status = GoalStatus.FAILED
            return
        meta["target_sleep_place_id"] = sleep_place_id

    target_sleep_place_id = meta.get("target_sleep_place_id")
    if not target_sleep_place_id:
        goal.status = GoalStatus.FAILED
        return

    if agent.location_id != target_sleep_place_id:
        physical.is_sleeping = False
        agent.is_asleep = False
        _move_one_step_toward(world, agent, target_sleep_place_id, rng)
        return

    physical.is_sleeping = True
    agent.is_asleep = True

    sleep_ticks_remaining = float(meta.get("sleep_ticks_remaining", 0.0))
    sleep_ticks_remaining -= 1.0
    meta["sleep_ticks_remaining"] = sleep_ticks_remaining

    recover_sleep_pressure(physical)

    _apply_sleep_recovery_effects(world, agent)

    if sleep_ticks_remaining <= 0.0:
        consolidate_sleep_for_agent(world, agent)
        physical.is_sleeping = False
        agent.is_asleep = False
        physical.last_sleep_tick = getattr(world, "tick", getattr(world, "current_tick", 0))
        goal.status = GoalStatus.COMPLETED


def _attempt_drink_from_tap(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    tap_id: str,
) -> None:
    from dosadi.memory.episode_factory import EpisodeFactory
    from dosadi.runtime.eating import DRINK_REPLENISH_AMOUNT, DRINK_WATER_UNIT

    depot_id = getattr(world, "water_tap_sources", {}).get(tap_id)
    if not depot_id:
        _record_water_denied(world, agent, tap_id, reason="no_source")
        return

    depot = world.facilities.get(depot_id)
    if depot is None or getattr(depot, "water_capacity", 0.0) <= 0.0:
        _record_water_denied(world, agent, tap_id, reason="invalid_depot")
        return

    if getattr(depot, "water_stock", 0.0) < DRINK_WATER_UNIT:
        _record_water_denied(world, agent, tap_id, reason="empty")
        return

    depot.water_stock -= DRINK_WATER_UNIT

    hydration_before = agent.physical.hydration_level
    hydration_after = min(1.0, hydration_before + DRINK_REPLENISH_AMOUNT)
    agent.physical.hydration_level = hydration_after
    agent.physical.last_drink_tick = getattr(world, "tick", 0)

    factory = EpisodeFactory(world=world)
    ep = factory.create_drank_water_episode(
        owner_agent_id=agent.id,
        tick=getattr(world, "tick", 0),
        place_id=tap_id,
        amount=DRINK_WATER_UNIT,
        hydration_before=hydration_before,
        hydration_after=hydration_after,
    )
    agent.record_episode(ep)

    goal.status = GoalStatus.COMPLETED


def _attempt_drink_from_mess_hall(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    hall_id: str,
) -> None:
    from dosadi.memory.episode_factory import EpisodeFactory
    from dosadi.runtime.eating import DRINK_REPLENISH_AMOUNT, DRINK_WATER_UNIT

    hydration_before = agent.physical.hydration_level
    hydration_after = min(1.0, hydration_before + DRINK_REPLENISH_AMOUNT)
    agent.physical.hydration_level = hydration_after
    agent.physical.last_drink_tick = getattr(world, "tick", 0)

    factory = EpisodeFactory(world=world)
    ep = factory.create_drank_water_episode(
        owner_agent_id=agent.id,
        tick=getattr(world, "tick", 0),
        place_id=hall_id,
        amount=DRINK_WATER_UNIT,
        hydration_before=hydration_before,
        hydration_after=hydration_after,
    )
    agent.record_episode(ep)

    goal.status = GoalStatus.COMPLETED


def _record_water_denied(world: "WorldState", agent: AgentState, place_id: str, reason: str) -> None:
    from dosadi.memory.episode_factory import EpisodeFactory

    factory = EpisodeFactory(world=world)
    ep = factory.create_water_denied_episode(
        owner_agent_id=agent.id,
        tick=getattr(world, "tick", 0),
        place_id=place_id,
        reason=reason,
    )
    agent.record_episode(ep)

def _ensure_ticks_remaining(
    goal: Goal,
    work_type: WorkDetailType,
    default_fraction: float = 0.5,
) -> float:
    meta = goal.metadata
    if "ticks_remaining" not in meta:
        cfg = WORK_DETAIL_CATALOG.get(work_type)
        base = cfg.typical_duration_ticks if cfg and cfg.typical_duration_ticks > 0 else 2000
        meta["ticks_remaining"] = float(base) * float(default_fraction)
    return float(meta["ticks_remaining"])


def _compute_shift_enjoyment(agent: AgentState, work_type: WorkDetailType) -> float:
    """
    Map stress/morale to an enjoyment score in [-1, 1].
    MVP: use current physical state as a proxy for how the shift felt.
    """

    phys = agent.physical

    # Start from morale in [0,1] mapped roughly into [-0.2, +0.8]
    base = phys.morale_level - 0.2

    # Stress penalty
    stress_penalty = 0.6 * phys.stress_level

    enjoyment = base - stress_penalty

    # Clamp
    if enjoyment < -1.0:
        enjoyment = -1.0
    elif enjoyment > 1.0:
        enjoyment = 1.0

    return enjoyment


def _handle_scout_interior(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    from dosadi.memory.episode_factory import EpisodeFactory

    work_type = WorkDetailType.SCOUT_INTERIOR

    ticks_remaining = _ensure_ticks_remaining(goal, work_type, default_fraction=0.3)
    base_perf = compute_performance_multiplier(agent.physical)
    spec_mult = compute_specialization_multiplier(agent, work_type)
    perf = base_perf * spec_mult
    ticks_remaining -= perf

    wh = agent.work_history.get_or_create(work_type)
    wh.ticks += perf

    goal.metadata["ticks_remaining"] = ticks_remaining
    if ticks_remaining <= 0:
        wh.shifts += 1
        wh.proficiency = ticks_to_proficiency(work_type, wh.ticks)
        enjoyment = _compute_shift_enjoyment(agent, work_type)
        update_work_preference_after_shift(agent, work_type, enjoyment)
        goal.status = GoalStatus.COMPLETED
        return

    gather_goal = goal if goal.goal_type == GoalType.GATHER_INFORMATION else None
    if gather_goal is None:
        parent_id = goal.metadata.get("parent_group_goal_id") if hasattr(goal, "metadata") else None
        if parent_id:
            gather_goal = getattr(world, "get_goal", lambda _gid: None)(parent_id)
        if gather_goal is None:
            gather_goal = next(
                (
                    g
                    for g in getattr(agent, "goals", [])
                    if g.goal_type == GoalType.GATHER_INFORMATION
                    and g.status == GoalStatus.ACTIVE
                ),
                None,
            )

    gather_goal_meta = gather_goal.metadata if gather_goal is not None else goal.metadata
    gather_goal_meta["ticks_active"] = gather_goal_meta.get("ticks_active", 0) + 1

    target_edges = []
    if hasattr(goal, "metadata"):
        target_edges = list(goal.metadata.get("target_edges", []))
    if not target_edges and gather_goal is not None:
        target_edges = list(gather_goal.metadata.get("corridor_edge_ids", []))

    topology = _topology_from_world(world)
    neighbors = _neighbors_for_location(world, agent.location_id)
    chosen_neighbor = None
    chosen_edge_id = None
    targeted_neighbors: List[Tuple[str, str]] = []
    for loc in neighbors:
        edge = _edge_lookup(agent.location_id, loc, topology)
        edge_id = edge.get("id") if edge else None
        if edge_id in target_edges:
            targeted_neighbors.append((loc, edge_id))

    if targeted_neighbors:
        chosen_neighbor, chosen_edge_id = rng.choice(targeted_neighbors)
    elif neighbors:
        chosen_neighbor = rng.choice(neighbors)
        edge = _edge_lookup(agent.location_id, chosen_neighbor, topology)
        chosen_edge_id = edge.get("id") if edge else None

    if chosen_neighbor:
        agent.location_id = chosen_neighbor

    current_tick = getattr(world, "tick", 0)
    factory = EpisodeFactory(world=world)

    if chosen_edge_id and chosen_edge_id in target_edges:
        gather_goal_meta["visits_recorded"] = gather_goal_meta.get("visits_recorded", 0) + 1
        episode = factory.create_scout_place_episode(
            owner_agent_id=agent.id,
            tick=current_tick,
            place_id=agent.location_id,
            interior=True,
            hazard_level=0.0,
            visibility=1.0,
            distance_from_pod=0.0,
            note="hazard_inspection",
        )
        agent.record_episode(episode)
        min_visits = gather_goal.metadata.get("min_visits_for_gather_information", 1) if gather_goal is not None else 1
        if gather_goal is not None and gather_goal_meta.get("visits_recorded", 0) >= min_visits:
            gather_goal.status = GoalStatus.COMPLETED

    if rng.random() < 0.10:
        episode = factory.create_scout_place_episode(
            owner_agent_id=agent.id,
            tick=current_tick,
            place_id=agent.location_id,
            interior=True,
            hazard_level=0.0,
            visibility=1.0,
            distance_from_pod=0.0,
            note="interior_scout",
        )
        agent.record_episode(episode)

    co_located = _agents_at_location(world, agent.location_id)
    if len(co_located) > 8:
        density = min(1.0, (len(co_located) - 8) / 8.0)
        episode = factory.create_corridor_crowding_episode(
            owner_agent_id=agent.id,
            tick=current_tick,
            corridor_id=agent.location_id,
            estimated_density=density,
            estimated_wait_ticks=0,
        )
        agent.record_episode(episode)


def _move_one_step_random_interior(
    world: "WorldState",
    agent: AgentState,
    rng: random.Random,
) -> None:
    neighbors = _neighbors_for_location(world, agent.location_id)
    if not neighbors:
        return
    next_loc = rng.choice(neighbors)
    agent.location_id = next_loc


def _handle_inventory_stores(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    work_type = WorkDetailType.INVENTORY_STORES

    ticks_remaining = _ensure_ticks_remaining(goal, work_type, default_fraction=0.3)
    base_perf = compute_performance_multiplier(agent.physical)
    spec_mult = compute_specialization_multiplier(agent, work_type)
    perf = base_perf * spec_mult
    ticks_remaining -= perf
    wh = agent.work_history.get_or_create(work_type)
    wh.ticks += perf
    goal.metadata["ticks_remaining"] = ticks_remaining
    if ticks_remaining <= 0:
        wh.shifts += 1
        wh.proficiency = ticks_to_proficiency(work_type, wh.ticks)
        enjoyment = _compute_shift_enjoyment(agent, work_type)
        update_work_preference_after_shift(agent, work_type, enjoyment)
        goal.status = GoalStatus.COMPLETED
        return

    meta = goal.metadata
    target_store_id = meta.get("target_store_id")
    if target_store_id is None:
        target_store_id = _choose_inventory_store_for_agent(world, agent, rng)
        if target_store_id is None:
            return
        meta["target_store_id"] = target_store_id

    if agent.location_id != target_store_id:
        _move_one_step_toward(world, agent, target_store_id, rng)
        return

    if rng.random() < 0.05:
        _perform_inventory_actions_at_store(world, agent, target_store_id, rng)


def _choose_inventory_store_for_agent(
    world: "WorldState",
    agent: AgentState,
    rng: random.Random,
) -> Optional[str]:
    facilities = getattr(world, "facilities", {}) or {}
    store_ids = [
        fac_id
        for fac_id, facility in facilities.items()
        if getattr(facility, "kind", None) in {"facility", "store"}
        or "store" in getattr(facility, "tags", ())
        or "inventory" in getattr(facility, "tags", ())
    ]
    if not store_ids:
        return None
    return rng.choice(store_ids)


def _handle_food_processing(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    from dosadi.memory.episode_factory import EpisodeFactory
    from dosadi.runtime.eating import MEAL_SATIATION_AMOUNT
    from dosadi.runtime.queues import get_or_create_facility_queue

    work_type = WorkDetailType.FOOD_PROCESSING_DETAIL

    ticks_remaining = _ensure_ticks_remaining(goal, work_type, default_fraction=0.3)
    base_perf = compute_performance_multiplier(agent.physical)
    spec_mult = compute_specialization_multiplier(agent, work_type)
    perf = base_perf * spec_mult
    ticks_remaining -= perf
    wh = agent.work_history.get_or_create(work_type)
    wh.ticks += perf
    goal.metadata["ticks_remaining"] = ticks_remaining
    if ticks_remaining <= 0:
        wh.shifts += 1
        wh.proficiency = ticks_to_proficiency(work_type, wh.ticks)
        enjoyment = _compute_shift_enjoyment(agent, work_type)
        update_work_preference_after_shift(agent, work_type, enjoyment)
        goal.status = GoalStatus.COMPLETED
        return

    meta = goal.metadata
    hall_id = meta.get("mess_hall_id")
    if not hall_id:
        mess_halls = [
            fid
            for fid, facility in getattr(world, "facilities", {}).items()
            if getattr(facility, "kind", None) == "mess_hall"
        ]
        if not mess_halls:
            return
        hall_id = mess_halls[0]
        meta["mess_hall_id"] = hall_id

    if agent.location_id != hall_id:
        _move_one_step_toward(world, agent, hall_id, rng)
        return

    q_state = get_or_create_facility_queue(world, hall_id)
    if not q_state.queue:
        return

    consumer_id = q_state.queue.popleft()
    consumer = world.agents.get(consumer_id)
    if consumer is None:
        return

    factory = EpisodeFactory(world=world)
    current_tick = getattr(world, "tick", 0)

    wait_ticks = 0
    if consumer.queue_join_tick is not None:
        wait_ticks = max(0, current_tick - consumer.queue_join_tick)
    elif getattr(consumer, "last_decision_tick", None) is not None:
        wait_ticks = max(0, current_tick - int(consumer.last_decision_tick))

    ep_food = factory.create_food_served_episode(
        owner_agent_id=consumer.id,
        tick=current_tick,
        hall_id=hall_id,
        wait_ticks=wait_ticks,
        calories_estimate=500.0,
    )
    consumer.record_episode(ep_food)

    ep_queue = factory.create_queue_served_episode(
        owner_agent_id=consumer.id,
        tick=current_tick,
        place_id=hall_id,
        wait_ticks=wait_ticks,
        resource_type="food",
    )
    consumer.record_episode(ep_queue)

    consumer.physical.hunger_level = max(
        0.0, consumer.physical.hunger_level - MEAL_SATIATION_AMOUNT
    )
    consumer.physical.last_meal_tick = current_tick
    consumer.current_queue_id = None
    consumer.queue_join_tick = None

    for g in consumer.goals:
        if g.goal_type == GoalType.GET_MEAL_TODAY and g.status in (
            GoalStatus.PENDING,
            GoalStatus.ACTIVE,
        ):
            g.status = GoalStatus.COMPLETED
            break


def _get_well_head_id(world: "WorldState") -> Optional[str]:
    for fid, facility in getattr(world, "facilities", {}).items():
        if getattr(facility, "kind", None) == "well_head":
            return fid
    return None


def _choose_target_depot(world: "WorldState", rng: random.Random) -> Optional[str]:
    candidates: List[Tuple[float, str]] = []
    for fid, facility in getattr(world, "facilities", {}).items():
        if getattr(facility, "kind", None) == "water_depot" and getattr(
            facility, "water_capacity", 0.0
        ) > 0:
            fill_ratio = getattr(facility, "water_stock", 0.0) / float(
                getattr(facility, "water_capacity", 1.0)
            )
            candidates.append((fill_ratio, fid))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    best_fill, _ = candidates[0]
    low_fill = [fid for (fill, fid) in candidates if fill <= best_fill + 0.1]
    return rng.choice(low_fill) if low_fill else candidates[0][1]


def _update_well_daily_reset(world: "WorldState") -> None:
    from dosadi.world.constants import WATER_DAY_TICKS

    tick = getattr(world, "tick", 0)
    ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", WATER_DAY_TICKS)
    ticks_per_day = max(1, int(ticks_per_day))
    if tick % ticks_per_day == 0:
        world.well.pumped_today = 0.0


def _water_handling_phase_to_well(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
    carried: float,
) -> None:
    from dosadi.memory.episode_factory import EpisodeFactory
    from dosadi.world.constants import WATER_BATCH_SIZE

    meta = goal.metadata
    well_head_id = _get_well_head_id(world)
    if not well_head_id:
        return

    if agent.location_id != well_head_id:
        _move_one_step_toward(world, agent, well_head_id, rng)
        return

    remaining = world.well.daily_capacity - world.well.pumped_today
    if remaining <= 0.0:
        return

    batch = min(WATER_BATCH_SIZE, max(0.0, remaining))
    if batch <= 0.0:
        return

    world.well.pumped_today += batch
    carried += batch

    factory = EpisodeFactory(world=world)
    ep = factory.create_well_pumped_episode(
        owner_agent_id=agent.id,
        tick=getattr(world, "tick", 0),
        well_facility_id=well_head_id,
        batch_amount=batch,
        pumped_today=world.well.pumped_today,
        daily_capacity=world.well.daily_capacity,
    )
    agent.record_episode(ep)

    target_depot_id = _choose_target_depot(world, rng)
    meta["carried_water"] = carried
    meta["target_depot_id"] = target_depot_id
    meta["phase"] = "TO_DEPOT"


def _water_handling_phase_to_depot(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
    carried: float,
    target_depot_id: Optional[str],
) -> None:
    from dosadi.memory.episode_factory import EpisodeFactory

    meta = goal.metadata
    if not target_depot_id:
        target_depot_id = _choose_target_depot(world, rng)
        if not target_depot_id:
            meta["phase"] = "TO_WELL"
            return
        meta["target_depot_id"] = target_depot_id

    if agent.location_id != target_depot_id:
        _move_one_step_toward(world, agent, target_depot_id, rng)
        return

    if carried <= 0.0:
        meta["phase"] = "TO_WELL"
        meta["carried_water"] = 0.0
        return

    depot = getattr(world, "facilities", {}).get(target_depot_id)
    if depot is None or getattr(depot, "water_capacity", 0.0) <= 0.0:
        meta["phase"] = "TO_WELL"
        meta["carried_water"] = carried
        return

    available_capacity = max(0.0, float(depot.water_capacity) - float(depot.water_stock))
    delivered = min(carried, available_capacity)
    depot.water_stock += delivered
    new_stock = depot.water_stock

    factory = EpisodeFactory(world=world)
    ep = factory.create_water_delivered_episode(
        owner_agent_id=agent.id,
        tick=getattr(world, "tick", 0),
        depot_id=target_depot_id,
        amount=delivered,
        new_stock=new_stock,
        capacity=float(depot.water_capacity),
    )
    agent.record_episode(ep)

    meta["carried_water"] = max(0.0, carried - delivered)
    meta["phase"] = "TO_WELL"


def _handle_water_handling(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    work_type = WorkDetailType.WATER_HANDLING

    ticks_remaining = _ensure_ticks_remaining(
        goal,
        work_type,
        default_fraction=0.3,
    )
    base_perf = compute_performance_multiplier(agent.physical)
    spec_mult = compute_specialization_multiplier(agent, work_type)
    perf = base_perf * spec_mult
    ticks_remaining -= perf
    wh = agent.work_history.get_or_create(work_type)
    wh.ticks += perf
    goal.metadata["ticks_remaining"] = ticks_remaining
    if ticks_remaining <= 0:
        wh.shifts += 1
        wh.proficiency = ticks_to_proficiency(work_type, wh.ticks)
        enjoyment = _compute_shift_enjoyment(agent, work_type)
        update_work_preference_after_shift(agent, work_type, enjoyment)
        goal.status = GoalStatus.COMPLETED
        return

    meta = goal.metadata
    phase = meta.get("phase") or "TO_WELL"
    carried = float(meta.get("carried_water", 0.0))
    target_depot_id = meta.get("target_depot_id")

    _update_well_daily_reset(world)

    if phase == "TO_WELL":
        _water_handling_phase_to_well(world, agent, goal, rng, carried)
    else:
        _water_handling_phase_to_depot(world, agent, goal, rng, carried, target_depot_id)


def _move_one_step_toward(
    world: "WorldState",
    agent: AgentState,
    target_location_id: str,
    rng: random.Random,
) -> None:
    neighbors = _neighbors_for_location(world, agent.location_id)
    if not neighbors:
        return
    if target_location_id in neighbors:
        agent.location_id = target_location_id
        return
    next_loc = rng.choice(neighbors)
    agent.location_id = next_loc


_RESOURCE_TYPES = ["food", "water", "suit_parts", "materials"]


def _perform_inventory_actions_at_store(
    world: "WorldState",
    agent: AgentState,
    store_id: str,
    rng: random.Random,
) -> None:
    from dosadi.memory.episode_factory import EpisodeFactory

    factory = EpisodeFactory(world=world)
    current_tick = getattr(world, "tick", 0)

    resource_type = rng.choice(_RESOURCE_TYPES)
    quantity = rng.uniform(1.0, 10.0)

    crate_id = f"crate:{resource_type}:{current_tick}:{agent.id}"
    episode_opened = factory.create_crate_opened_episode(
        owner_agent_id=agent.id,
        tick=current_tick,
        crate_id=crate_id,
        resource_type=resource_type,
        quantity=quantity,
        location_id=store_id,
    )
    agent.record_episode(episode_opened)

    episode_stocked = factory.create_resource_stocked_episode(
        owner_agent_id=agent.id,
        tick=current_tick,
        place_id=store_id,
        resource_type=resource_type,
        quantity=quantity,
    )
    agent.record_episode(episode_stocked)


ENV_TARGET_COMFORT = 0.6
ENV_ADJUST_STEP = 0.02
ENV_CONTROL_PLACES_KEY = "env_control_places"


def _assign_env_control_places(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
    max_places: int = 5,
) -> None:
    if ENV_CONTROL_PLACES_KEY in goal.metadata:
        return

    candidate_ids = list(getattr(world, "places", {}).keys())
    if not candidate_ids:
        goal.metadata[ENV_CONTROL_PLACES_KEY] = []
        return

    rng.shuffle(candidate_ids)
    goal.metadata[ENV_CONTROL_PLACES_KEY] = candidate_ids[:max_places]


def _choose_env_target_place(
    world: "WorldState", agent: AgentState, goal: Goal, rng: random.Random
) -> Optional[str]:
    from dosadi.world.environment import get_or_create_place_env

    places = goal.metadata.get(ENV_CONTROL_PLACES_KEY) or []
    if not places:
        return None

    worst_place_id = None
    worst_delta = 0.0

    for pid in places:
        env = get_or_create_place_env(world, pid)
        delta = abs(env.comfort - ENV_TARGET_COMFORT)
        if delta > worst_delta:
            worst_delta = delta
            worst_place_id = pid

    return worst_place_id


def _handle_env_control(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    from dosadi.world.environment import get_or_create_place_env

    work_type = WorkDetailType.ENV_CONTROL

    ticks_remaining = _ensure_ticks_remaining(
        goal,
        work_type,
        default_fraction=0.3,
    )
    base_perf = compute_performance_multiplier(agent.physical)
    spec_mult = compute_specialization_multiplier(agent, work_type)
    perf = base_perf * spec_mult
    ticks_remaining -= perf
    wh = agent.work_history.get_or_create(work_type)
    wh.ticks += perf
    goal.metadata["ticks_remaining"] = ticks_remaining
    if ticks_remaining <= 0:
        wh.shifts += 1
        wh.proficiency = ticks_to_proficiency(work_type, wh.ticks)
        enjoyment = _compute_shift_enjoyment(agent, work_type)
        update_work_preference_after_shift(agent, work_type, enjoyment)
        goal.status = GoalStatus.COMPLETED
        return

    _assign_env_control_places(world, agent, goal, rng)
    target_place_id = _choose_env_target_place(world, agent, goal, rng)
    if not target_place_id:
        return

    if agent.location_id != target_place_id:
        _move_one_step_toward(world, agent, target_place_id, rng)
        return

    env = get_or_create_place_env(world, target_place_id)
    comfort_before = env.comfort

    if env.comfort < ENV_TARGET_COMFORT:
        env.comfort = min(ENV_TARGET_COMFORT, env.comfort + ENV_ADJUST_STEP)
    elif env.comfort > ENV_TARGET_COMFORT:
        env.comfort = max(ENV_TARGET_COMFORT, env.comfort - ENV_ADJUST_STEP)

    comfort_after = env.comfort
    if comfort_after != comfort_before:
        factory = EpisodeFactory(world=world)
        episode = factory.create_env_node_tuned_episode(
            owner_agent_id=agent.id,
            tick=getattr(world, "tick", 0),
            place_id=target_place_id,
            comfort_before=comfort_before,
            comfort_after=comfort_after,
        )
        agent.record_episode(episode)


def _handle_write_supervisor_report(
    world: "WorldState",
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    from dosadi.memory.episode_factory import EpisodeFactory

    if agent.tier != 2 or agent.supervisor_work_type is None:
        goal.status = GoalStatus.FAILED
        return

    work_type = agent.supervisor_work_type
    crew_id = agent.supervisor_crew_id

    tick_end = getattr(world, "tick", getattr(world, "current_tick", 0))
    tick_start = max(0, tick_end - SUPERVISOR_REPORT_INTERVAL_TICKS)

    metrics, flags, notes = _aggregate_supervisor_report_inputs(
        world=world,
        agent=agent,
        work_type=work_type,
        crew_id=crew_id,
        tick_start=tick_start,
        tick_end=tick_end,
    )

    log_id = create_admin_log_id(world)
    entry = AdminLogEntry(
        log_id=log_id,
        author_agent_id=agent.id,
        work_type=work_type,
        crew_id=crew_id,
        tick_start=tick_start,
        tick_end=tick_end,
        metrics=metrics,
        flags=flags,
        notes=notes,
    )

    if getattr(world, "admin_logs", None) is None:
        world.admin_logs = {}
    world.admin_logs[log_id] = entry

    agent.last_report_tick = tick_end

    _emit_report_episodes(world, agent, entry)

    goal.status = GoalStatus.COMPLETED


def _aggregate_supervisor_report_inputs(
    world: "WorldState",
    agent: AgentState,
    work_type: WorkDetailType,
    crew_id: Optional[str],
    tick_start: int,
    tick_end: int,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, str]]:
    metrics: Dict[str, float] = {}
    flags: Dict[str, float] = {}
    notes: Dict[str, str] = {}

    total_work_eps = 0
    queue_issue_eps = 0
    strain_eps = 0
    incident_eps = 0

    work_tag = work_type.name.lower()
    daily_eps = getattr(getattr(agent, "episodes", None), "daily", [])

    for ep in daily_eps:
        ep_tick = getattr(ep, "tick", 0)
        if ep_tick < tick_start or ep_tick > tick_end:
            continue

        ep_tags = getattr(ep, "tags", set()) or set()
        lower_tags = {str(t).lower() for t in ep_tags}

        if work_tag not in lower_tags:
            continue

        total_work_eps += 1

        if "queue" in lower_tags:
            queue_issue_eps += 1
        if "strain" in lower_tags or "overworked" in lower_tags:
            strain_eps += 1
        if "incident" in lower_tags or "failure" in lower_tags:
            incident_eps += 1

    metrics["episodes_work_related"] = float(total_work_eps)
    metrics["episodes_queue_issues"] = float(queue_issue_eps)
    metrics["episodes_strain"] = float(strain_eps)
    metrics["episodes_incidents"] = float(incident_eps)

    if total_work_eps > 0:
        strain_ratio = strain_eps / total_work_eps
        queue_ratio = queue_issue_eps / total_work_eps
    else:
        strain_ratio = 0.0
        queue_ratio = 0.0

    flags["strain_high"] = 1.0 if strain_ratio > 0.3 else 0.0
    flags["queue_chronic"] = 1.0 if queue_ratio > 0.3 else 0.0

    notes["summary"] = (
        f"Supervisor report for {work_type.name} crew {crew_id or 'none'}; "
        f"work_eps={total_work_eps}, strain_eps={strain_eps}, incidents={incident_eps}."
    )

    return metrics, flags, notes


def _emit_report_episodes(world: "WorldState", agent: AgentState, entry: AdminLogEntry) -> None:
    from dosadi.memory.episode_factory import EpisodeFactory

    factory = EpisodeFactory(world=world)
    ep = factory.create_supervisor_report_episode(
        owner_agent_id=agent.id,
        tick=getattr(world, "tick", getattr(world, "current_tick", 0)),
        entry=entry,
    )
    agent.record_episode(ep)


def _neighbors_for_location(world: "WorldState", location_id: str) -> List[str]:
    neighbors = _build_neighbors(_topology_from_world(world))
    return neighbors.get(location_id, [])


def _agents_at_location(world: "WorldState", location_id: str) -> List[AgentState]:
    return [
        agent
        for agent in getattr(world, "agents", {}).values()
        if getattr(agent, "location_id", None) == location_id
    ]



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
