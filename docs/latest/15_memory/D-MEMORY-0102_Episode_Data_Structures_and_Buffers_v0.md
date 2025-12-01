---
title: Episode_Data_Structures_and_Buffers
doc_id: D-MEMORY-0102
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-MEMORY-0001  # Episode_Management_System_v0
  - D-MEMORY-0002  # Episode_Schema_and_Memory_Behavior_v0
  - D-MEMORY-0003  # Episode_Transmission_Channels_v0
  - D-MEMORY-0004  # Belief_System_and_Tiered_Memory_v0
  - D-MEMORY-0101  # Belief_Data_Structures_and_Agent_Integration_v0
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0020   # Unified_Agent_Model_v0
---

# 15_memory · Episode Data Structures & Buffers v0 (D-MEMORY-0102)

## 1. Purpose & Scope

This document defines the **concrete data structures** for episodes and
per-agent episode buffers, as required by the conceptual memory model in
D-MEMORY-0001–0004.

It is intended as an implementation guide for Codex and other generators,
targeting the Python codebase under `src/dosadi/`.

Design goals:

- Distinguish **world events** (objective-ish) from **episodes**
  (an event as experienced by a specific agent).
- Define a compact, per-agent `Episode` record that captures just enough:
  - when/where/who,
  - channel and reliability,
  - relation to goals,
  - emotional tone,
  - a small, structured payload.
- Provide `EpisodeBuffers` for:
  - short-term episodic memory (minutes),
  - daily episodic memory (wake cycle),
  - optional references to external logs.
- Attach `EpisodeBuffers` to `AgentState` in a way that scales from a small
  founding colony to a multi-ward city after 500 years of simulation time.

This document defines **shapes and containers only**. Numeric policies for
capacity, promotion, and decay are left to D-MEMORY-02xx and D-RUNTIME-02xx.

Implementation language: **Python 3**, using `dataclasses`.

---

## 2. Concept: Events vs Episodes

- **World events** (runtime / logs):
  - single representation for a happening in the simulation:
    - e.g. `MOVE`, `ATTACK`, `PROTOCOL_CREATED`.
  - stored in global logs or per-system structures.
- **Episodes** (per-agent):
  - an event **as experienced or learned by one agent**:
    - partial, noisy view,
    - subjective tags: goal linkage, emotion, importance, reliability,
    - “I saw a guard beat someone in corridor X while I was hungry and scared.”
  - always have an `owner_agent_id`.

Multiple agents can receive distinct episodes from the same world event.

The world may retain events for long periods (via admin logs), but agents only
retain a **tiny, filtered subset** of episodes in internal buffers, from which
beliefs are later formed.

---

## 3. Enums & Support Types

Create a new module:

- `src/dosadi/memory/episodes.py`

This module defines enums and support types used by `Episode` and
`EpisodeBuffers`.

### 3.1 EpisodeChannel

How this episode reached the agent.

```python
from enum import Enum, auto


class EpisodeChannel(Enum):
    """How this episode reached the agent."""

    DIRECT = auto()        # directly experienced (own body + senses)
    OBSERVED = auto()      # watching others
    REPORT = auto()        # structured report from known agent
    RUMOR = auto()         # informal, low-structure hearsay
    PROTOCOL = auto()      # reading/hearing official text
    BODY_SIGNAL = auto()   # internal state cue ("I'm hungry", "I'm in pain")
```

### 3.2 EpisodeTargetType

What the episode is mainly about (the primary focus).

```python
class EpisodeTargetType(Enum):
    """What the episode is mainly about."""

    SELF = auto()
    PERSON = auto()
    PLACE = auto()
    FACTION = auto()
    PROTOCOL = auto()
    OBJECT = auto()
    RESOURCE = auto()      # e.g. water, food
    OTHER = auto()
```

### 3.3 EpisodeOutcome

Coarse outcome classification from the agent's perspective.

```python
class EpisodeOutcome(Enum):
    """Coarse outcome classification."""

    NEUTRAL = auto()
    SUCCESS = auto()
    FAILURE = auto()
    HARM = auto()
    HELP = auto()
    NEAR_MISS = auto()
```

### 3.4 EpisodeGoalRelation

How this episode relates to the agent’s current goal (if known).

```python
class EpisodeGoalRelation(Enum):
    """How this episode relates to the agent's current goal."""

    UNKNOWN = auto()
    IRRELEVANT = auto()
    SUPPORTS = auto()
    THWARTS = auto()
    MIXED = auto()
```

---

## 4. Emotion Snapshot

A minimal emotional state associated with an episode. This is not a full emotion
model, but a compact snapshot sufficient to drive salience and risk-avoidance.

```python
from dataclasses import dataclass


@dataclass
class EmotionSnapshot:
    """
    Minimal emotional state associated with an episode.

    valence: -1 (very negative) .. +1 (very positive)
    arousal: 0 (calm) .. 1 (highly activated)
    threat:  0 (safe) .. 1 (immediate danger)
    """

    valence: float = 0.0
    arousal: float = 0.0
    threat: float = 0.0
```

---

## 5. Episode Dataclass

The core per-agent record.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set

# Assumes EpisodeChannel, EpisodeTargetType, EpisodeOutcome,
# EpisodeGoalRelation, EmotionSnapshot are defined in this module.


@dataclass
class Episode:
    """
    A single, owner-relative record of something the agent experienced or learned.

    Episodes live in short-term and daily buffers and are periodically compressed
    into beliefs. Most episodes will be discarded; only a minority leave lasting
    traces in belief structures or written logs.
    """

    episode_id: str

    owner_agent_id: str
    tick: int

    # Where this happened (coarse).
    location_id: Optional[str] = None  # facility_id / corridor_id / ward_id

    # Channel & source.
    channel: EpisodeChannel = EpisodeChannel.DIRECT
    source_agent_id: Optional[str] = None  # teller, reporter, oppressor, etc.

    # Optional link to a world event record, if one exists.
    event_id: Optional[str] = None

    # Focus of the episode (what it's mainly "about").
    target_type: EpisodeTargetType = EpisodeTargetType.OTHER
    target_id: Optional[str] = None  # agent_id, facility_id, faction_id, etc.

    # Action semantics from this agent's perspective.
    verb: str = ""          # e.g. "SEE_FIGHT", "QUEUE_DENIED", "READ_PROTOCOL"
    summary_tag: str = ""   # short code for clustering: "queue_fight", "guard_cruelty"

    # Goal linkage.
    goal_id: Optional[str] = None     # current goal id, if known
    goal_relation: EpisodeGoalRelation = EpisodeGoalRelation.UNKNOWN
    goal_relevance: float = 0.0       # 0–1: how important for that goal

    # Subjective evaluation.
    outcome: EpisodeOutcome = EpisodeOutcome.NEUTRAL
    emotion: EmotionSnapshot = field(default_factory=EmotionSnapshot)

    # Salience and reliability.
    importance: float = 0.0           # 0–1: promotion/retention weight
    reliability: float = 0.5          # 0–1: trust in this episode's accuracy

    # Optional tag set for later pattern mining.
    tags: Set[str] = field(default_factory=set)

    # Tiny structured payload for role-specific details.
    details: Dict[str, float | int | str] = field(default_factory=dict)
```

Notes:

- `summary_tag` and `tags` provide clustering hooks for pattern-mining and
  protocol authoring (e.g. “all `queue_fight` episodes in ward:12”).
- `details` is intentionally small and lightly typed to keep episodes compact.
- `goal_id` and `goal_relation` connect episodes to the goal system in
  D-AGENT-0023.

---

## 6. EpisodeBuffers – Per-Agent Episodic Layers

Each agent maintains two primary in-memory episode buffers:

- **short_term** – minutes of experience (high churn),
- **daily** – promoted episodes for the wake cycle, processed at sleep.

Scribes and similar roles may also maintain a list of references to external
records (`archive_refs`).

```python
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List


@dataclass
class EpisodeBuffers:
    """
    Container for an agent's episodic memory layers.

    - short_term: very recent, high-churn episodes (minutes).
    - daily: promoted episodes that will be considered during the next sleep
      consolidation.
    - archive_refs: optional references to externally recorded episodes/logs
      (for scribes, auditors, etc.).
    """

    short_term: Deque[Episode] = field(default_factory=deque)
    daily: List[Episode] = field(default_factory=list)

    # For agents whose job includes record-keeping, they may keep references
    # to long-lived external records instead of internal full episodes.
    archive_refs: List[str] = field(default_factory=list)  # e.g. admin_log ids

    # Capacity hints (actual values can be set per agent/tier).
    short_term_capacity: int = 50
    daily_capacity: int = 100

    def push_short_term(self, episode: Episode) -> None:
        """
        Add an episode to short-term buffer, evicting a low-importance episode
        if over capacity.
        """
        self.short_term.append(episode)
        if len(self.short_term) > self.short_term_capacity:
            # Simple eviction: drop the lowest-importance episode.
            lowest_idx = None
            lowest_importance = 1.1
            for idx, ep in enumerate(self.short_term):
                if ep.importance < lowest_importance:
                    lowest_importance = ep.importance
                    lowest_idx = idx
            if lowest_idx is not None:
                # remove by index using rotate/popleft
                self.short_term.rotate(-lowest_idx)
                self.short_term.popleft()
                self.short_term.rotate(lowest_idx)

    def promote_to_daily(self, episode: Episode) -> None:
        """
        Move or copy an episode into the daily buffer, respecting capacity.
        Lower-importance daily episodes are dropped on overflow.
        """
        self.daily.append(episode)
        if len(self.daily) > self.daily_capacity:
            # drop lowest-importance daily episode
            self.daily.sort(key=lambda ep: ep.importance, reverse=True)
            self.daily = self.daily[: self.daily_capacity]
```

Notes:

- Capacity values (`short_term_capacity`, `daily_capacity`) are placeholders.
  Actual values SHOULD be derived from:
  - agent tier,
  - INT and WIL attributes,
  - traumatic / stress state if modeled.
- This v0 implementation uses simple O(n) scanning and sorting for eviction;
  later performance passes MAY replace this with more efficient structures.

---

## 7. AgentState Integration

`AgentState` (in `src/dosadi/agents/core.py`) should gain an `episodes` field of
type `EpisodeBuffers`.

### 7.1 AgentState field

In `AgentState` definition:

```python
from dataclasses import dataclass, field
from dosadi.memory.episodes import EpisodeBuffers


@dataclass
class AgentState:
    # ... existing fields ...
    episodes: EpisodeBuffers = field(default_factory=EpisodeBuffers)
```

### 7.2 Backwards Compatibility

- Existing code that constructs `AgentState` instances can remain unchanged;
  `episodes` will be automatically initialized via the default factory.
- No logic is required yet to populate or process episodes; this patch only
  adds shapes.

Future documents (e.g. D-MEMORY-020x) will specify:

- how actions and world events generate `Episode` instances,
- how short-term episodes are periodically promoted to `daily`,
- how sleep/downtime cycles integrate `daily` episodes into beliefs.

---

## 8. Notes for Episode Generation & Use (Non-binding)

The following notes are **non-binding guidance** for future implementation.

### 8.1 Generating Episodes

When an action or world event occurs, affected agents SHOULD:

1. Determine **who receives an episode**:
   - the actor (self), targets, nearby observers, and sometimes rumor listeners.
2. For each recipient:
   - construct an `Episode` with:
     - `owner_agent_id`,
     - `tick`, `location_id`,
     - `channel` (`DIRECT`, `OBSERVED`, `REPORT`, `RUMOR`, `PROTOCOL`, `BODY_SIGNAL`),
     - `target_type` + `target_id` (*place, person, faction, protocol, self*),
     - `verb`, `summary_tag`,
     - goal linkage (`goal_id`, `goal_relation`, `goal_relevance`),
     - `outcome` (e.g. `SUCCESS`, `HARM`, `NEAR_MISS`),
     - `emotion` snapshot,
     - `importance` and `reliability`.
   - push to `agent_state.episodes.push_short_term(episode)`.

### 8.2 Promotion & Sleep Integration

- During wake cycle, periodic routines MAY:
  - examine `short_term` episodes,
  - promote those above certain thresholds (goal relevance, emotion, novelty)
    into `daily` via `promote_to_daily`.
- During sleep/downtime, nightly consolidation SHOULD:
  - iterate over `episodes.daily`,
  - update relevant beliefs in `agent_state.beliefs`,
  - clear `episodes.daily`.

These policies (thresholds, cadences, attribute-based modifiers) are defined in
future runtime/memory docs; D-MEMORY-0102 only guarantees that the necessary
fields and containers exist.

---

## 9. Codex Implementation Checklist

When implementing D-MEMORY-0102 in the codebase, Codex SHOULD:

1. Create `src/dosadi/memory/episodes.py` with:
   - `EpisodeChannel`, `EpisodeTargetType`, `EpisodeOutcome`,
     `EpisodeGoalRelation` enums,
   - `EmotionSnapshot` dataclass,
   - `Episode` dataclass,
   - `EpisodeBuffers` container and methods as specified.

2. Update `src/dosadi/agents/core.py`:
   - import `EpisodeBuffers`,
   - add `episodes: EpisodeBuffers = field(default_factory=EpisodeBuffers)`
     to `AgentState`.

3. Run the existing test suite and ensure no failures are introduced.

4. (Optional) Add minimal unit tests for:
   - `EpisodeBuffers.push_short_term` eviction behavior,
   - `EpisodeBuffers.promote_to_daily` capacity handling.

No behavioral changes beyond the presence of these new fields and types are
required in this patch.
