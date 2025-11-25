---
title: Movement_Protocols_MVP
doc_id: D-LAW-0013
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-RUNTIME-0200  # Founding_Wakeup_MVP_Runtime
  - D-SCEN-0002     # Founding_Wakeup_MVP_Scenario
  - D-WORLD-0100    # Founding_Wakeup_Topology
  - D-AGENT-0020    # Agent_Model_Foundation
  - D-AGENT-0021    # Agent_Goals_and_Episodic_Memory
  - D-AGENT-0022    # Agent_MVP_Python_Skeleton
  - D-AGENT-0023    # Groups_and_Councils_MVP
  - D-LAW-0010      # Risk_and_Protocol_Cycle
---

# 1. Purpose and Scope

This document defines the **minimum viable product (MVP)** representation and logic
for **movement/safety protocols** in the Founding Wakeup scenario.

It answers, at MVP scale:

- What is a *protocol* (vs a law or ad-hoc advice)?  
- How are movement/safety protocols represented in code?  
- How do protocols interact with:
  - hazard probabilities on corridors and junctions, and
  - agent decisions about movement?
- How do proto-councils **author**, **activate**, and **propagate** protocols in
  a way that fits the Risk and Protocol Cycle (`D-LAW-0010`)?

Scope is intentionally narrow:

- Only **movement/safety** protocols affecting traversal of edges/locations.
- Only a single proto-council (Founding Wakeup MVP).
- No fines, prisons, or full legal sanction system yet; protocols are soft norms
  that influence behavior and hazard odds.


# 2. Conceptual Model

## 2.1 Protocols in the Risk and Protocol Cycle

In `D-LAW-0010`, the core cycle is:

> Episodes → Patterns → Group Goals → Protocols → New Episodes

For Founding Wakeup MVP:

- Agents experience **hazard episodes** on corridors (falls, suit scrapes, near
  suffocation, etc.).
- Pod reps and the proto-council integrate these into **risk patterns**
  (e.g. “corridor-7A is dangerous”).
- The council sets **group goals** (`GATHER_INFORMATION`, `AUTHOR_PROTOCOL`) to
  respond to that risk.
- The council authors **movement/safety protocols** that prescribe safer behavior:
  - travel in groups,
  - avoid certain corridors at busy times,
  - restrict non-essential traffic, etc.
- Agents learn about these protocols and either **comply** or **ignore** them,
  modifying their movement choices and hazard odds.


## 2.2 Protocol vs law vs rumor

- **Protocol** (this document):  
  - Semi-formal rule or safety procedure, authored by a group (proto-council),
    communicated to the population, and expected (but not guaranteed) to be followed.
  - Example: “No one walks corridor-7A alone; groups of 3+ only.”

- **Law** (future docs):  
  - Protocol backed by explicit sanction system and enforcement agents.
  - Example: “Violators will be detained and lose water rations.”

- **Rumor / informal advice**:  
  - Unofficial, untracked statements (“I heard 7A kills people, don’t go there”).
  - These live as `Episode`s and beliefs but do not have a Protocol record.

In MVP, we only model **protocols** and their practical effect on hazard resolution.


# 3. Data Model

Movement/safety protocols are stored as explicit objects and referenced by id from:

- Agent state (`known_protocols`),
- Episodes (`READ_PROTOCOL`),
- World / law modules (`ProtocolRegistry`).


## 3.1 Protocol enums

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ProtocolType(str, Enum):
    MOVEMENT = "MOVEMENT"
    TRAFFIC_AND_SAFETY = "TRAFFIC_AND_SAFETY"
    # Later: RATIONING, SURVEILLANCE, etc.


class ProtocolStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"
```


## 3.2 Protocol dataclass (MVP)

```python
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

    # Who authored it
    author_group_id: Optional[str] = None   # e.g. "group:council:alpha"
    author_agent_id: Optional[str] = None   # scribe or lead author

    created_at_tick: int = 0
    activated_at_tick: Optional[int] = None
    retired_at_tick: Optional[int] = None

    # What it applies to
    covered_location_ids: List[str] = field(default_factory=list)
    covered_edge_ids: List[str] = field(default_factory=list)  # optional, for later

    # Movement constraints (MVP)
    min_group_size: int = 1
    max_group_size: Optional[int] = None
    allowed_ticks_modulo: Optional[int] = None  # e.g. every N ticks; None = any time

    # Hazard effect when *compliant*
    compliant_hazard_multiplier: float = 0.5  # < 1 reduces risk
    # Optional extra risk when *violating* an ACTIVE protocol
    violation_hazard_multiplier: float = 1.0  # >= 1 increases risk

    tags: List[str] = field(default_factory=list)

    # Simple adoption metrics (MVP)
    times_read: int = 0
    times_referenced: int = 0
```


### 3.2.1 Id helper

```python
def make_protocol_id(prefix: str = "protocol") -> str:
    return f"{prefix}:{uuid.uuid4().hex}"
```


## 3.3 ProtocolRegistry

Protocols are stored in a simple registry for the MVP:

```python
@dataclass
class ProtocolRegistry:
    """In-memory registry of protocols for the MVP.

    In a more complex system this might be part of WorldState, but for the
    Founding Wakeup MVP it can be a small dedicated structure.
    """

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
            and (
                location_id in p.covered_location_ids
            )
        ]
```

In MVP, this registry can be carried on the `WorldState` or alongside it in the
runtime module.


# 4. Protocol Lifecycle in Founding Wakeup

Movement protocols follow a simple lifecycle in this scenario.


## 4.1 Trigger conditions (risk thresholds)

When the proto-council meets and aggregates hazard episodes (see `D-AGENT-0023`):

- For each corridor `c`:
  - Compute an empirical risk estimate:
    - `incidents_c / traversals_c`
  - If:
    - `incidents_c >= min_incidents_for_protocol` (default 3), **and**
    - `risk_c >= risk_threshold` (e.g. 0.3–0.5),
    - and no ACTIVE movement protocol already covers `c`,
  - Then the council should create an `AUTHOR_PROTOCOL` group goal targeting `c`.


## 4.2 Drafting and activation

Within that group goal:

- A **scribe** agent is chosen (see `D-AGENT-0023`).
- The scribe gets a personal `Goal` with `goal_type = AUTHOR_PROTOCOL` and a
  `target` referencing the corridor(s).

When the scribe completes that goal in the simulation, the law/protocol system:

1. Creates a `Protocol`:
   - `protocol_type = ProtocolType.TRAFFIC_AND_SAFETY`
   - `covered_location_ids` includes the corridor(s) (e.g. `loc:corridor-7A`).
   - Default pattern for MVP:
     - `min_group_size = 3`
     - `compliant_hazard_multiplier = 0.5`
     - `violation_hazard_multiplier = 1.0` (no extra punishment yet).
2. Adds it to the `ProtocolRegistry` with `status = DRAFT`.
3. Marks it as `ACTIVE` when the council “ratifies” it, which in MVP can be:
   - At the end of the council meeting where it’s authored, or
   - Immediately on creation for simplicity.


## 4.3 Propagation to agents

Agents learn about protocols via **READ_PROTOCOL** episodes:

- A protocol is “published” at the Well core or Pods (e.g. posters, briefings).
- When an agent is exposed to it:
  - A `READ_PROTOCOL` episode is created for that agent.
  - The protocol id is added to `AgentState.known_protocols`.
  - `Protocol.times_read` is incremented.

Agents may then update their movement decisions to follow the protocol, depending on:

- Personality (communal vs self-serving, trusting vs paranoid),
- Perceived risk (PlaceBelief.danger_score),
- Goals (e.g. scouts may “accept” extra risk).


# 5. Hazard Modification Logic

Protocols influence the **per-traversal hazard probability** for an agent moving
through a corridor or across an edge.


## 5.1 Baseline hazard

Each edge in the world has a **base hazard probability** (`base_hazard_prob`) as
defined in `D-WORLD-0100` (e.g. 0.02 for safe corridors, 0.20 for corridor-7A).


## 5.2 Effective hazard with protocols

For MVP, we use a simple multiplicative model:

```text
effective_hazard_prob
  = base_hazard_prob
    * protocol_multiplier
```

Where:

- `protocol_multiplier` depends on:
  - Whether the location is covered by any ACTIVE protocol(s),
  - Whether the agent is **compliant** with at least one such protocol,
  - Whether we model extra risk for violations.


### 5.2.1 Computing the protocol multiplier

MVP rule:

1. Gather all ACTIVE protocols `P` for the location the agent is entering.
2. For each `Protocol p in P`:
   - Check if the agent is **compliant** with its movement constraints:
     - `group_size` at this traversal ≥ `p.min_group_size`, and
     - if `p.max_group_size` is not `None`, `group_size <= p.max_group_size`.
   - (MVP can ignore `allowed_ticks_modulo` initially or treat it as always satisfied.)
3. If the agent is compliant with at least one protocol:
   - `protocol_multiplier = min(p.compliant_hazard_multiplier for compliant p)`
4. Otherwise, if they are explicitly *violating* an ACTIVE protocol:
   - `protocol_multiplier = max(p.violation_hazard_multiplier for violated p)`
5. If no protocols apply:
   - `protocol_multiplier = 1.0`


## 5.3 Helper function (for Codex)

```python
from typing import Sequence, List
from dosadi.agents.core import AgentState
# Assume Edge and WorldState types exist in the world module.


def compute_effective_hazard_prob(
    agent: AgentState,
    location_id: str,
    base_hazard_prob: float,
    group_size: int,
    registry: ProtocolRegistry,
) -> float:
    """Return the effective per-traversal hazard probability for movement.

    - Looks up ACTIVE protocols covering location_id.
    - Computes protocol_multiplier according to MVP rules.
    - Returns base_hazard_prob * protocol_multiplier.
    """
    applicable = registry.active_protocols_for_location(location_id)
    if not applicable:
        return base_hazard_prob

    compliant_multipliers: List[float] = []
    violated_multipliers: List[float] = []

    for p in applicable:
        # Check group size constraints
        size_ok = group_size >= p.min_group_size
        if p.max_group_size is not None:
            size_ok = size_ok and group_size <= p.max_group_size

        if size_ok:
            compliant_multipliers.append(p.compliant_hazard_multiplier)
        else:
            violated_multipliers.append(p.violation_hazard_multiplier)

    if compliant_multipliers:
        m = min(compliant_multipliers)
    elif violated_multipliers:
        m = max(violated_multipliers)
    else:
        m = 1.0

    return base_hazard_prob * m
```

Note: **compliance decision** (e.g. whether the agent *tries* to travel in a group)
is made in the **agent decision loop** (`D-RUNTIME-0201`), not here. This function
merely evaluates the risk given a resolved `group_size`.


# 6. Event & Function Surface (for Codex)

This section defines the key functions that Codex should implement in the
law/protocols module. Suggested module path:

- `src/dosadi/systems/protocols.py` or
- `src/dosadi/systems/law.py`


## 6.1 Protocol creation and activation

```python
from dosadi.agents.core import Goal, GoalType, GoalOrigin, GoalStatus, GoalHorizon


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
    ...


def activate_protocol(protocol: Protocol, tick: int) -> None:
    """Mark a protocol as ACTIVE and stamp activated_at_tick."""
    ...
```


## 6.2 Recording protocol reading

Agents learn about protocols via episodes and their `known_protocols` list:

```python
from dosadi.agents.core import AgentState, Episode, EpisodeSourceType, make_episode_id


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
    ...
```


## 6.3 Hazard computation hook

As specified in §5.3:

```python
def compute_effective_hazard_prob(
    agent: AgentState,
    location_id: str,
    base_hazard_prob: float,
    group_size: int,
    registry: ProtocolRegistry,
) -> float:
    """Apply active movement/safety protocols to base hazard probability."""
    ...
```


# 7. Integration Notes

- **Where protocols live**:  
  - For MVP, a `ProtocolRegistry` instance can be attached to `WorldState` or passed
    alongside it to the simulation loop.

- **Who creates protocols**:  
  - Only the proto-council (through its scribe) creates protocols in this scenario.
  - Later, multiple councils / guild heads / dukes may author conflicting protocols.

- **Enforcement level**:  
  - There is no explicit punishment besides the risk itself.
  - A future doc can add sanction episodes and enforcement agent roles.

- **Debugging & telemetry**:  
  - Admin dashboards (future `D-INTERFACE-*` docs) can display:
    - List of ACTIVE protocols,
    - Per-corridor incident rates pre/post protocol activation,
    - Adoption (times_read) counts.

With this MVP, the Founding Wakeup run can show a complete arc:

1. Unstructured movement → high hazard on corridor-7A.  
2. Hazard episodes → pod-level concern → proto-council formation.  
3. Proto-council drafts and activates a “travel in groups” protocol.  
4. Agents adopt the protocol to varying degrees.  
5. Effective hazard probabilities fall for compliant group traversals, visible in
   scenario reports.
