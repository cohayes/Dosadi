---
title: Belief_Data_Structures_and_Agent_Integration
doc_id: D-MEMORY-0101
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-MEMORY-0001  # Episode_Management_System_v0
  - D-MEMORY-0002  # Episode_Schema_and_Memory_Behavior_v0
  - D-MEMORY-0003  # Episode_Transmission_Channels_v0
  - D-MEMORY-0004  # Belief_System_and_Tiered_Memory_v0
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0006   # Agent_Attributes_and_Skills_v0
---

# 15_memory · Belief Data Structures & Agent Integration v0 (D-MEMORY-0101)

## 1. Purpose & Scope

This document defines the **concrete data structures** for beliefs described
conceptually in D-MEMORY-0004 and specifies how those beliefs are attached to
`AgentState` for use in the runtime.

It is intended as an implementation guide for Codex and other code generators,
targeting the Python codebase under `src/dosadi/`.

Specifically, this document:

- Defines a small set of enums used to type beliefs and their provenance.
- Defines a `BaseBelief` dataclass with fields shared by all beliefs.
- Defines concrete belief dataclasses for key belief families:
  - `PlaceBelief`, `PersonBelief`, `FactionBelief`,
  - `ProtocolBelief`, `ExpectationBelief`, `SelfBelief`.
- Defines a `BeliefStore` container to keep an agent's beliefs organized.
- Specifies how to attach a `BeliefStore` to `AgentState`.

Numerical rules for belief capacity, decay, and thresholds for promotion from
episodes into beliefs are out of scope here and should be defined in follow-up
runtime documents (e.g. D-MEMORY-02xx, D-RUNTIME-02xx).

Implementation language: **Python 3**, using `dataclasses`.

---

## 2. Module Layout

Create a new module:

- `src/dosadi/memory/beliefs.py`

This module will define:

- enums: `BeliefTargetType`, `BeliefSource`,
- base class: `BaseBelief`,
- concrete belief classes: `PlaceBelief`, `PersonBelief`, `FactionBelief`,
  `ProtocolBelief`, `ExpectationBelief`, `SelfBelief`,
- container: `BeliefStore`.

`AgentState` (in `dosadi.agents.core`) will gain a `beliefs: BeliefStore` field.

---

## 3. Enums

### 3.1 BeliefTargetType

Represents the broad category of thing a belief is about. This should be used
both for introspection and for routing episode integration logic.

```python
from enum import Enum, auto


class BeliefTargetType(Enum):
    """What this belief is about."""

    PLACE = auto()
    PERSON = auto()
    FACTION = auto()
    PROTOCOL = auto()
    EXPECTATION = auto()
    SELF = auto()
```

### 3.2 BeliefSource

Tracks the main **source** of evidence for a belief. This is lightweight
provenance used for later modeling of bias and trust (self-experience vs rumor
vs protocol vs archive).

```python
from enum import Enum, auto


class BeliefSource(Enum):
    """Where the belief got most of its weight from."""

    SELF_EPISODE = auto()   # directly experienced
    OTHER_AGENT = auto()    # close ally / subordinate / superior
    RUMOR = auto()          # anonymous or low-trust gossip
    PROTOCOL = auto()       # inferred from written protocol
    ARCHIVE = auto()        # logs / dashboards / records
    UNKNOWN = auto()
```

---

## 4. BaseBelief Dataclass

All belief types share a set of core fields. These are captured in `BaseBelief`.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

# Assumes BeliefTargetType and BeliefSource are defined in this module.


@dataclass
class BaseBelief:
    """
    Base record for any belief.

    Concrete belief types (PlaceBelief, PersonBelief, etc.) should embed or
    subclass this and then add domain-specific fields.
    """

    belief_id: str

    # The agent that owns/holds this belief.
    owner_agent_id: str

    # Target information.
    target_type: BeliefTargetType
    target_id: str  # facility_id, agent_id, faction_id, protocol_id, etc.

    # A coarse descriptor of what this belief is about, e.g. "safety", "trust".
    aspect: str

    # The agent's current estimate. Semantics depend on aspect but v0 assumes
    # a numeric score in [0, 1] where possible.
    value: float

    # Confidence that this belief is accurate [0, 1].
    confidence: float

    created_tick: int
    last_updated_tick: int

    # Lightweight provenance for later bias modeling.
    primary_source: BeliefSource = BeliefSource.SELF_EPISODE
    source_counts: Dict[BeliefSource, int] = field(default_factory=dict)

    # --- Small helper methods (optional but useful) ---

    def register_source(self, source: BeliefSource) -> None:
        """Increment count for a contributing source type."""
        self.source_counts[source] = self.source_counts.get(source, 0) + 1

    def decay_confidence(self, factor: float) -> None:
        """Apply a multiplicative confidence decay (e.g. factor < 1.0 over time)."""
        self.confidence *= factor

    def reinforce(self, delta: float, max_value: float = 1.0) -> None:
        """
        Increase belief value and confidence in response to consistent episodes.

        This is a simple v0 rule. Later docs may refine these dynamics.
        """
        self.value = max(0.0, min(max_value, self.value + delta))
        # simple rule: reinforcing events also raise confidence
        self.confidence = max(0.0, min(1.0, self.confidence + abs(delta) * 0.5))

    def weaken(self, delta: float) -> None:
        """
        Decrease confidence and optionally nudge value toward neutrality (0.5).

        Intended for use when episodes contradict existing beliefs.
        """
        self.confidence = max(0.0, min(1.0, self.confidence - abs(delta)))
        # optional: move value toward 0.5 as "unknown" when confidence is low
        if self.confidence < 0.3:
            self.value += (0.5 - self.value) * 0.5
```

Notes:

- The helper methods are v0 and may be refined or replaced by more explicit
  update functions later.
- `belief_id` creation strategy is left to existing id utilities (e.g.
  `make_belief_id()` if/when defined).

---

## 5. Concrete Belief Types

Each concrete belief type either subclasses `BaseBelief` or embeds it and adds
typed, optional fields that correspond to aspects described in D-MEMORY-0004.

In v0, `BaseBelief.value` and `BaseBelief.aspect` provide a generic view, while
the optional fields provide more semantic texture for systems that care.

### 5.1 PlaceBelief

Beliefs about specific locations or facilities (pods, corridors, bays, depots,
wards).

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class PlaceBelief(BaseBelief):
    """Belief about a specific place / facility."""

    perceived_safety: Optional[float] = None      # 0–1
    perceived_access: Optional[float] = None      # 0–1
    resource_quality: Optional[float] = None      # 0–1
    enforcement_level: Optional[float] = None     # 0–1
    crowding_level: Optional[float] = None        # 0–1
    home_feeling: Optional[float] = None          # 0–1
```

### 5.2 PersonBelief

Beliefs about specific individuals (agents) or persistent roles ("pod steward",
"bay chief").

```python
@dataclass
class PersonBelief(BaseBelief):
    """Belief about a specific individual (agent or persistent role)."""

    trustworthiness: Optional[float] = None       # 0–1
    fairness: Optional[float] = None              # 0–1
    bribability: Optional[float] = None           # 0–1 (higher = easier to bribe)
    threat_level: Optional[float] = None          # 0–1
    alignment: Optional[float] = None             # 0–1 (0 enemy, 1 ally; callers decide mapping)
    competence: Optional[float] = None            # 0–1
    influence: Optional[float] = None             # 0–1
```

### 5.3 FactionBelief

Beliefs about groups: pods, guilds, cartels, militias, councils, cults, etc.

```python
@dataclass
class FactionBelief(BaseBelief):
    """Belief about a group (pod, guild, cartel, militia, council, etc.)."""

    protects_own: Optional[float] = None          # 0–1
    uses_own: Optional[float] = None              # 0–1
    brutality: Optional[float] = None             # 0–1
    mercy: Optional[float] = None                 # 0–1
    retaliation_tendency: Optional[float] = None  # 0–1
    promise_reliability: Optional[float] = None   # 0–1
    legitimacy: Optional[float] = None            # 0–1
```

### 5.4 ProtocolBelief

Beliefs about protocols or rules: how real, enforced, and fair they are.

```python
@dataclass
class ProtocolBelief(BaseBelief):
    """Belief about a protocol or rule (enforcement and perception)."""

    enforcement_probability: Optional[float] = None  # 0–1
    severity: Optional[float] = None                 # 0–1
    fairness: Optional[float] = None                 # 0–1
    theater_vs_real: Optional[float] = None          # 0–1 (0 = theater, 1 = very real)
```

### 5.5 ExpectationBelief

Beliefs about trends or conditional relationships ("if X then Y" over time).

```python
@dataclass
class ExpectationBelief(BaseBelief):
    """Belief about a trend or conditional relationship."""

    # What class of entity this trend applies to, e.g. PLACE, FACTION, etc.
    subject_type: Optional[BeliefTargetType] = None

    # Rough time horizon over which the expectation is about to play out.
    horizon_ticks: Optional[int] = None

    # Optional key for the underlying hypothesis, e.g. "ration_cut->queue_violence".
    hypothesis_key: Optional[str] = None
```

### 5.6 SelfBelief

Beliefs about self-identity ("what kind of person am I?").

```python
from typing import List


@dataclass
class SelfBelief(BaseBelief):
    """Belief about self-identity."""

    self_view_tags: List[str] = field(default_factory=list)
    perceived_agency: Optional[float] = None         # 0–1: "I can affect outcomes"
    perceived_resilience: Optional[float] = None     # 0–1: "I can survive hardship"
    perceived_status: Optional[float] = None         # 0–1: "people listen to me"
```

---

## 6. BeliefStore Container

To keep `AgentState` manageable and make capacity enforcement easier, beliefs
are grouped in a `BeliefStore`.

```python
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class BeliefStore:
    """
    Container for an agent's long-term beliefs.

    This keeps beliefs grouped by type and provides simple lookup helpers.
    Capacity limits and pruning policies can be implemented here later.
    """

    places: Dict[str, PlaceBelief] = field(default_factory=dict)
    people: Dict[str, PersonBelief] = field(default_factory=dict)
    factions: Dict[str, FactionBelief] = field(default_factory=dict)
    protocols: Dict[str, ProtocolBelief] = field(default_factory=dict)
    expectations: Dict[str, ExpectationBelief] = field(default_factory=dict)
    self_beliefs: Dict[str, SelfBelief] = field(default_factory=dict)  # typically 1–few

    # --- Convenience getters ---

    def get_place(self, facility_id: str) -> Optional[PlaceBelief]:
        return self.places.get(facility_id)

    def get_person(self, agent_id: str) -> Optional[PersonBelief]:
        return self.people.get(agent_id)

    def get_faction(self, faction_id: str) -> Optional[FactionBelief]:
        return self.factions.get(faction_id)

    def get_protocol(self, protocol_id: str) -> Optional[ProtocolBelief]:
        return self.protocols.get(protocol_id)

    def get_expectation(self, key: str) -> Optional[ExpectationBelief]:
        return self.expectations.get(key)

    # --- v0 helper for place beliefs ---

    def ensure_place_belief(
        self,
        belief_id: str,
        owner_agent_id: str,
        facility_id: str,
        now_tick: int,
    ) -> PlaceBelief:
        """Get or create a PlaceBelief for this facility."""
        belief = self.places.get(facility_id)
        if belief is None:
            belief = PlaceBelief:
                belief_id=belief_id,
                owner_agent_id=owner_agent_id,
                target_type=BeliefTargetType.PLACE,
                target_id=facility_id,
                aspect="safety",     # default aspect, callers may refine
                value=0.5,
                confidence=0.3,
                created_tick=now_tick,
                last_updated_tick=now_tick,
            )
            self.places[facility_id] = belief
        return belief
```

> NOTE: Codex MUST correct any syntax errors (e.g. the colon typo after
> `PlaceBelief` above) when implementing in the repo. The pseudocode intent
> should be clear: construct a new `PlaceBelief` instance if none exists and
> store it in `self.places[facility_id]`.

Notes:

- Capacity limits by tier (e.g. max number of person beliefs for Tier-1 vs
  Tier-2 vs Tier-3) should be implemented in `BeliefStore` in a later pass.
- Additional `ensure_*` helpers can be added as needed (for people, factions,
  protocols).

---

## 7. AgentState Integration

`AgentState` (defined in `src/dosadi/agents/core.py`) should gain a `beliefs`
field of type `BeliefStore`.

### 7.1 AgentState field

In `AgentState` definition, import `BeliefStore` and add:

```python
from dataclasses import dataclass, field
from dosadi.memory.beliefs import BeliefStore


@dataclass
class AgentState:
    # ... existing fields ...
    beliefs: BeliefStore = field(default_factory=BeliefStore)
```

### 7.2 Backwards Compatibility

- Existing code that constructs `AgentState` instances can remain unchanged;
  the new `beliefs` field will be automatically initialized via the default
  factory.
- No existing logic is required to populate beliefs in this v0 patch; that will
  be implemented in later "episode → belief" integration work.

---

## 8. Notes for Episode → Belief Integration (Non-binding)

The following notes are **non-binding guidance** for future implementation:

- Episode integration logic (e.g. in `dosadi.memory.episodes` or in a runtime
  system) should:
  - inspect an episode,
  - determine relevant belief targets (place/person/faction/protocol),
  - use `agent_state.beliefs` helpers (e.g. `ensure_place_belief`) to fetch or
    create beliefs,
  - update those beliefs using `reinforce()` or `weaken()` as appropriate,
  - adjust `last_updated_tick`.

- Tier-based capacity and pruning should be handled inside `BeliefStore` or
  adjacent utilities, using the conceptual limits from D-MEMORY-0004.

This document only defines the **shapes** and **integration point**. Behavior
and numeric policies live in later documents.

---

## 9. Codex Implementation Checklist

When implementing D-MEMORY-0101 in the codebase, Codex SHOULD:

1. Create `src/dosadi/memory/beliefs.py` with:
   - `BeliefTargetType`, `BeliefSource` enums,
   - `BaseBelief` dataclass,
   - `PlaceBelief`, `PersonBelief`, `FactionBelief`,
   - `ProtocolBelief`, `ExpectationBelief`, `SelfBelief`,
   - `BeliefStore` container and methods as specified.

2. Update `src/dosadi/agents/core.py`:
   - import `BeliefStore`,
   - add `beliefs: BeliefStore = field(default_factory=BeliefStore)` to `AgentState`.

3. Run the existing test suite and ensure no failures are introduced.

4. (Optional) Add minimal unit tests for `BeliefStore.ensure_place_belief` and
   `BaseBelief.reinforce/weaken` behavior, if a test harness is already present.

No other behavioral changes are required in this patch.
