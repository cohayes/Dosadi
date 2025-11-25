---
title: Agent_MVP_Python_Skeleton
doc_id: D-AGENT-0022
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-AGENT-0020   # Agent_Model_Foundation
  - D-AGENT-0021   # Agent_Goals_and_Episodic_Memory
  - D-RUNTIME-0200 # Founding_Wakeup_MVP_Runtime
---

# 1. Purpose and Scope

This document specifies a **minimal Python-facing skeleton** for Dosadi agents in the
**Founding Wakeup MVP** scenario.

It does **not** attempt to be the final, fully-general agent implementation. Instead,
it:

- Defines the **core dataclasses and type shapes** needed for:
  - Agent state,
  - Goals,
  - Episodic memory,
  - Simple place beliefs.
- Provides an **Event & Function Surface** for Codex and other tooling to implement in
  `src/dosadi/agents/` (or equivalent).
- Is scoped to what the **Founding Wakeup MVP** requires:
  - No drive system.
  - No complex faction graphs, espionage, or economy.

Higher-complexity features (multi-faction graphs, black markets, narcotics, etc.) will
extend these shapes later rather than replace them.


# 2. Design Principles

1. **No drives.**
   - Agent motivations flow from:
     - Goal stacks,
     - Personality traits,
     - Physical/psychological state,
     - Episodic memories and beliefs.

2. **MVP-focused.**
   - Only define the structures needed for:
     - Movement,
     - Hazard episodes,
     - Pod + proto-council formation,
     - Simple movement/safety protocols.

3. **Stable ids, flexible internals.**
   - Public-facing ids like `agent_id`, `goal_id`, `episode_id`, `location_id` should be
     stable and string-based.
   - Internals (e.g. how beliefs are stored) can evolve as long as this shape remains valid.

4. **Dataclasses-first.**
   - Use `@dataclass` with type hints for clarity and ease of tooling.


# 3. Core Types

This section describes the core Python shapes as **dataclass sketches**. Exact module
paths may vary, but the field names and semantics should remain consistent.


## 3.1 Goal

A Goal is a structured commitment: “try to make X true, under Y constraints.” This is a
direct embodiment of the conceptual `Goal` in D-AGENT-0021.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional
import uuid
import math


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
    # Additional types can be added as needed.


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
    """MVP Goal representation for Dosadi agents.

    This is intentionally simple but compatible with D-AGENT-0021.
    """

    goal_id: str
    owner_id: str  # "agent:<id>" or "group:<type>:<id>"

    goal_type: GoalType
    description: str = ""

    parent_goal_id: Optional[str] = None

    # Typed payload; semantics depend on goal_type.
    target: Dict[str, Any] = field(default_factory=dict)

    # Priority and urgency are in [0, 1]. Horizon is coarse.
    priority: float = 0.5
    urgency: float = 0.0
    horizon: GoalHorizon = GoalHorizon.SHORT

    status: GoalStatus = GoalStatus.PENDING

    created_at_tick: int = 0
    deadline_tick: Optional[int] = None
    last_updated_tick: int = 0

    origin: GoalOrigin = GoalOrigin.INTERNAL_STATE
    source_ref: Optional[str] = None  # e.g. protocol id, order id, etc.

    # For group goals, multiple assignees are allowed.
    assigned_to: List[str] = field(default_factory=list)

    tags: List[str] = field(default_factory=list)

    def score_for_selection(self) -> float:
        """Return a simple scalar score for goal selection.

        This is a placeholder for more sophisticated functions that may also
        incorporate personality and physical state. For MVP, we just use
        priority * (0.5 + 0.5 * urgency) as a soft bias toward urgent items.
        """
        # Clamp priority and urgency just in case.
        p = max(0.0, min(1.0, self.priority))
        u = max(0.0, min(1.0, self.urgency))
        return p * (0.5 + 0.5 * u)


def make_goal_id(prefix: str = "goal") -> str:
    return f"{prefix}:{uuid.uuid4().hex}"
```


## 3.2 Episode

An Episode is how a single agent experienced an event. This directly mirrors the
conceptual `Episode` in D-AGENT-0021.

```python
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
    """Subjective record of an event from one agent's perspective.

    MVP episodes cover:
    - Movement
    - Hazard incidents / near-misses
    - Pod and council meetings
    - Protocol reading
    """

    episode_id: str
    owner_id: str           # "agent:<id>"

    event_id: Optional[str] = None  # shared id across witnesses (if applicable)

    tick_start: int = 0
    tick_end: int = 0

    location_id: Optional[str] = None
    context_tags: List[str] = field(default_factory=list)

    source_type: EpisodeSourceType = EpisodeSourceType.DIRECT
    source_agent_id: Optional[str] = None  # who told you, authored protocol, etc.

    participants: List[Dict[str, Any]] = field(default_factory=list)

    event_type: str = ""  # e.g. "MOVEMENT", "HAZARD_INCIDENT", "POD_MEETING"
    summary: str = ""

    goals_involved: List[EpisodeGoalDelta] = field(default_factory=list)

    # Simple outcome payload; MVP can keep this very light.
    outcome: Dict[str, Any] = field(default_factory=dict)

    # Emotion as valence/arousal + label.
    valence: float = 0.0   # -1 (very bad) .. +1 (very good)
    arousal: float = 0.0   # 0 (calm) .. 1 (intense)
    dominant_feeling: Optional[str] = None

    perceived_risk: float = 0.0       # subjective risk at time of event
    perceived_reliability: float = 1.0  # confidence this actually happened / is true

    privacy: str = "PRIVATE"  # PRIVATE | SHAREABLE | RUMOR_FODDER
    tags: List[str] = field(default_factory=list)


def make_episode_id(owner_id: str) -> str:
    return f"ep:{owner_id}:{uuid.uuid4().hex}"
```


## 3.3 PlaceBelief (MVP)

For Founding Wakeup MVP we only need **place-level beliefs** (e.g. corridor danger
perception). Person, protocol, and faction beliefs can be added later.

```python
@dataclass
class PlaceBelief:
    """Subjective belief about a single place/location.

    For MVP, we only model a few scalar scores.
    """

    owner_id: str      # "agent:<id>"
    place_id: str      # "loc:corridor-7A", etc.

    danger_score: float = 0.0        # 0..1, perceived hazard
    enforcement_score: float = 0.0   # 0..1, how tightly rules enforced here
    opportunity_score: float = 0.0   # 0..1, perceived chance to profit

    last_updated_tick: int = 0

    def update_from_episode(self, episode: Episode, learning_rate: float = 0.3) -> None:
        """Update this belief from a single episode.

        MVP heuristic:
        - If the episode has event_type related to hazards and negative valence,
          nudge danger_score upward.
        - If event_type suggests safe traversal, nudge danger_score downward slightly.
        """
        if episode.location_id != self.place_id:
            return

        # Simple: if hazard tag present, increase danger.
        is_hazard = "hazard" in (episode.tags or []) or episode.event_type in {
            "HAZARD_INCIDENT",
            "HAZARD_NEAR_MISS",
        }

        target_danger = 1.0 if is_hazard else 0.0
        self.danger_score += learning_rate * (target_danger - self.danger_score)
        self.danger_score = max(0.0, min(1.0, self.danger_score))
        self.last_updated_tick = max(self.last_updated_tick, episode.tick_end)
```


# 4. AgentState (MVP)

The MVP AgentState ties together identity, attributes, personality traits, current
state, goals, episodes, and basic beliefs.

```python
from typing import Optional, Mapping


@dataclass
class Attributes:
    """Physical and mental attributes, roughly centered on 10.

    This is a minimal subset for MVP. Additional attributes can be added later.
    """

    STR: int = 10
    DEX: int = 10
    END: int = 10
    INT: int = 10
    WIL: int = 10
    CHA: int = 10


@dataclass
class Personality:
    """MVP personality traits relevant to early decision-making."""

    bravery: float = 0.5           # 0 cautious .. 1 brave
    communal: float = 0.5          # 0 self-serving .. 1 communal
    ambition: float = 0.5          # 0 content .. 1 ambitious
    curiosity: float = 0.5         # 0 routine-seeking .. 1 novelty-seeking
    trusting: float = 0.5          # 0 paranoid .. 1 trusting

    leadership_weight: float = 0.5 # relative influence in groups


@dataclass
class PhysicalState:
    """Physical and psychological state variables."""

    health: float = 1.0            # 0..1
    fatigue: float = 0.0           # 0..1
    hunger: float = 0.0            # 0..1
    thirst: float = 0.0            # 0..1
    stress: float = 0.0            # 0..1
    morale: float = 0.5            # 0..1


@dataclass
class AgentState:
    """MVP agent representation used in the Founding Wakeup scenario.

    This is intentionally lean and focused on:
    - Movement and hazard exposure,
    - Pod + proto-council formation,
    - Simple protocol awareness.
    """

    agent_id: str

    # Identity & classification
    name: str
    tier: int = 1
    roles: List[str] = field(default_factory=lambda: ["colonist"])
    ward: Optional[str] = None

    # Core traits and state
    attributes: Attributes = field(default_factory=Attributes)
    personality: Personality = field(default_factory=Personality)
    physical: PhysicalState = field(default_factory=PhysicalState)

    # Location
    location_id: str = "loc:pod-1"

    # Goals & memory
    goals: List[Goal] = field(default_factory=list)
    episodes: List[Episode] = field(default_factory=list)

    # Beliefs: MVP only place beliefs, keyed by place_id.
    place_beliefs: Dict[str, PlaceBelief] = field(default_factory=dict)

    # Known protocols (by id); details implemented in law/protocol modules.
    known_protocols: List[str] = field(default_factory=list)

    # Cached / derived values
    last_decision_tick: int = 0

    def get_or_create_place_belief(self, place_id: str) -> PlaceBelief:
        if place_id not in self.place_beliefs:
            self.place_beliefs[place_id] = PlaceBelief(
                owner_id=self.agent_id,
                place_id=place_id,
            )
        return self.place_beliefs[place_id]

    def record_episode(self, episode: Episode) -> None:
        self.episodes.append(episode)
        # Optionally trim history in future for performance.

    def update_beliefs_from_episode(self, episode: Episode) -> None:
        if episode.location_id:
            pb = self.get_or_create_place_belief(episode.location_id)
            pb.update_from_episode(episode)

    def choose_focus_goal(self) -> Optional[Goal]:
        """Select a focus goal based on a simple scoring function.

        Later versions can incorporate personality, physical state, and more
        sophisticated horizon handling.
        """
        if not self.goals:
            return None
        # For MVP, pick the goal with the highest score_for_selection.
        return max(self.goals, key=lambda g: g.score_for_selection())
```


# 5. Event & Function Surface (for Codex)

This section defines the **public surface** that Codex and other tooling should rely
on when implementing the MVP agent logic for the Founding Wakeup scenario.


## 5.1 Core constructors and helpers

These can live in `src/dosadi/agents/core.py` or similar.

```python
def create_agent(agent_id: str, name: str, pod_location_id: str, rng) -> AgentState:
    """Create a new MVP AgentState with randomized attributes and personality.

    - Places the agent in the given pod_location_id (e.g. "loc:pod-1").
    - Initializes attributes and personality with small random variation around
      neutral values.
    - Seeds the goal stack with:
      - MAINTAIN_SURVIVAL (parent)
      - ACQUIRE_RESOURCE (sub-goal)
      - SECURE_SHELTER (sub-goal)
      - Optionally REDUCE_POD_RISK for some leadership-inclined agents.
    """
    ...


def initialize_agents_for_founding_wakeup(num_agents: int, seed: int) -> List[AgentState]:
    """Helper to create a list of AgentState for the Founding Wakeup MVP.

    Worldgen may call this, or it may be incorporated there directly. This function
    is primarily here to give Codex a clear target.
    """
    ...
```


## 5.2 Per-tick hooks (called from runtime)

These are simple hooks that the runtime can call each tick. The detailed logic is
defined in `D-RUNTIME-0201_Agent_Decision_Loop_MVP` (future doc), but the signatures
should look like:

```python
from typing import Sequence


def decide_next_action(agent: AgentState, world: "WorldState") -> "Action":
    """Select the next action for the agent based on goals, beliefs, and state.

    For MVP, this should:
    - Choose a focus goal (AgentState.choose_focus_goal).
    - Consider a small set of candidate actions:
      - REST_IN_POD
      - MOVE(location_id)
      - POD_MEETING
      - COUNCIL_MEETING (if eligible and at well-core)
    - Use place_beliefs.danger_score and basic personality traits to rank actions.
    """
    ...


def apply_action(agent: AgentState, action: "Action", world: "WorldState", tick: int) -> Sequence[Episode]:
    """Apply the chosen action to the world and return any resulting episodes.

    For MVP, this should include:
    - Movement with hazard resolution, emitting MOVEMENT + HAZARD_* episodes.
    - Meeting participation, emitting POD_MEETING or COUNCIL_MEETING episodes.
    - Protocol reading, emitting READ_PROTOCOL episodes.
    """
    ...
```


# 6. Notes and Future Extensions (Non-Normative)

- This skeleton is intentionally narrow. Future docs (e.g. D-AGENT-0030+) can define:
  - PersonBelief, ProtocolBelief, FactionBelief.
  - Richer emotional state and coping mechanisms.
  - Long-horizon identity and learning.
- As long as the **field names** and **basic behavior** of these MVP types remain
  stable, higher-complexity features should compose on top, not require rewrites.
