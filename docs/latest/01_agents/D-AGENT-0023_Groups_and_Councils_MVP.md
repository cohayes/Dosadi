---
title: Groups_and_Councils_MVP
doc_id: D-AGENT-0023
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-AGENT-0020   # Agent_Model_Foundation
  - D-AGENT-0021   # Agent_Goals_and_Episodic_Memory
  - D-AGENT-0022   # Agent_MVP_Python_Skeleton
  - D-RUNTIME-0200 # Founding_Wakeup_MVP_Runtime
  - D-SCEN-0002    # Founding_Wakeup_MVP_Scenario
  - D-WORLD-0100   # Founding_Wakeup_Topology
  - D-LAW-0010     # Risk_and_Protocol_Cycle
---

# 1. Purpose and Scope

This document defines the **minimum viable product (MVP)** group mechanics for the
**Founding Wakeup** scenario:

- Pods as **base groups** for social structure and leadership emergence.
- A single **proto-council** as the first cross-pod political body.
- Simple **group goals** (`GATHER_INFORMATION`, `AUTHOR_PROTOCOL`) and how they
  project to individual agents.

It provides:

- A conceptual model for pod groups and councils.
- Python-facing data shapes compatible with `D-AGENT-0022`.
- An **Event & Function Surface** for Codex to implement in
  `dosadi/agents/groups.py` or similar.

Scope is deliberately narrow:

- No guilds, cartels, or multi-tier noble hierarchy yet.
- No complex formal law or sanction system (protocols are soft norms in MVP).


# 2. Conceptual Model

## 2.1 Pods as base groups

In `founding_wakeup_mvp`:

- Every agent is assigned to one of 4 pods at tick 0.
- Each pod is a **natural group** that:
  - Shares risks (same exit corridor).
  - Shares local information (pod meetings).
  - Nominates 0–2 **pod representatives** (spokespeople).

- Implementation note: newly elected pod representatives immediately receive a
  high-priority `FORM_GROUP` personal goal to pull them toward the hub and
  form or sustain the proto-council.

Pods are the first site where:

- Informal leadership emerges.
- Group-level thinking (“how do we reduce risk for *us*?”) appears.


## 2.2 Proto-council

When pod representatives from multiple pods meet at the Well core hub, they form a
**proto-council**:

- A small group of Tier-1 colonists acting in a proto-Tier-3 way:
  - Aggregating hazard information.
  - Setting group-level goals to gather more information.
  - Authoring first movement/safety protocols.

The proto-council:

- Lives entirely inside the agent/goal/episode/protocol machinery (no god-logic).
- Is modeled as a **Group** object with its own goals (group goals).


## 2.3 Group goals and projection

Groups can hold **group goals**, such as:

- `GATHER_INFORMATION` about corridors with high risk or poor knowledge.
- `AUTHOR_PROTOCOL` for corridors whose risk score crosses a threshold.

Group goals are then **projected** into individual agent goals:

- Council assigns **scouts** and a **scribe**.
- Those agents get `GATHER_INFORMATION` or `AUTHOR_PROTOCOL`-related goals in their
  personal goal stacks (`origin = GROUP_DECISION`).

This aligns with the Risk and Protocol Cycle (`D-LAW-0010`):

> Episodes → Patterns → Group Goals → Protocols → New Episodes.


# 3. Group Data Structures (Python Skeleton)

These shapes are intended to complement any existing `Group` model in the repo. If a
`Group` type already exists, align fields as closely as possible; otherwise, this can
be introduced as-is.


## 3.1 GroupType and GroupRole

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import uuid


class GroupType(str, Enum):
    POD = "POD"
    COUNCIL = "COUNCIL"
    TASK_FORCE = "TASK_FORCE"  # may be used for scouts later
    # Additional types (GUILD, CARTEL, etc.) can be added in future.


class GroupRole(str, Enum):
    MEMBER = "MEMBER"
    POD_REPRESENTATIVE = "POD_REPRESENTATIVE"
    COUNCIL_MEMBER = "COUNCIL_MEMBER"
    SCOUT = "SCOUT"
    SCRIBE = "SCRIBE"
```


## 3.2 Group

```python
@dataclass
class Group:
    """MVP group representation for pods and proto-councils."""

    group_id: str
    group_type: GroupType
    name: str

    # Pod or council membership is represented by agent ids.
    member_ids: List[str] = field(default_factory=list)

    # Optional per-agent roles (e.g. representative, scout, scribe).
    roles_by_agent: Dict[str, List[GroupRole]] = field(default_factory=dict)

    # Group-level goals (e.g. GATHER_INFORMATION, AUTHOR_PROTOCOL).
    goal_ids: List[str] = field(default_factory=list)

    # Metadata (pod id, home location, etc.).
    parent_location_id: Optional[str] = None   # e.g. "loc:pod-1" or "loc:well-core"
    created_at_tick: int = 0
    last_meeting_tick: int = 0

    tags: List[str] = field(default_factory=list)


def make_group_id(prefix: str = "group") -> str:
    return f"{prefix}:{uuid.uuid4().hex}"
```


# 4. Pod Groups and Representative Selection

## 4.1 Pod groups

In Founding Wakeup MVP, there are **4 pod groups**, one per pod node:

- `group:pod-1` ↔ `loc:pod-1`
- `group:pod-2` ↔ `loc:pod-2`
- `group:pod-3` ↔ `loc:pod-3`
- `group:pod-4` ↔ `loc:pod-4`

Each pod group:

- Has `group_type = POD`.
- Has `member_ids` containing all agents whose `location_id` and/or initial pod
  assignment is that pod.
- May have 0–2 agents with role `POD_REPRESENTATIVE` at early ticks.


## 4.2 Pod meetings

At a regular cadence (e.g. every 20–40 ticks, see `D-SCEN-0002`):

- A subset of pod members are considered to be **attending a pod meeting**:
  - E.g. agents physically in `loc:pod-X` at that tick.
  - Optionally, only awake / low fatigue agents are included.

When a pod meeting occurs:

- For each attendee, a **competence score** for other podmates is updated.
- Competence is based on:
  - `Personality.leadership_weight`
  - Outcomes of previous actions (hazard avoidance, good information).
  - For MVP, we can approximate this with leadership_weight plus a bit of noise.


### 4.2.1 Competence scoring (MVP)

*Non-normative implementation suggestion*:

- Maintain a simple internal (in code) mapping:
  - `competence[agent_id][other_agent_id] -> float`
- On each meeting, for each attendee A and candidate B:
  - `score = B.personality.leadership_weight + small_noise`
  - Optionally adjust up if B has episodes where their advice avoided hazards.
- Agents then rank other podmates by this score.


## 4.3 Representative selection rule

After computing or updating competence scores, the pod group determines whether to
(re)appoint a representative.

MVP rule:

- Each attendee chooses their **top candidate** (most competent podmate, possibly
  excluding themselves or not, depending on taste).
- Count the “votes” for each candidate within this meeting.
- A candidate C becomes a `POD_REPRESENTATIVE` if:
  - They receive at least `rep_vote_fraction_threshold` of votes among attendees
    (e.g. ≥ 0.4), **and**
  - Their `Personality.leadership_weight` is above `min_leadership_threshold`
    (e.g. ≥ 0.6).
- Each pod aims to have **at least 1 and at most 2** representatives:
  - If there is no rep, appoint the best candidate.
  - If there is 1 rep and a second strong candidate emerges, allow a second.
  - If a new candidate significantly outperforms an existing rep, reps can be
    replaced over time.

Representative status is reflected by:

- Adding `GroupRole.POD_REPRESENTATIVE` to `roles_by_agent[agent_id]` in the pod group.
- Optionally by adding a `"POD_REPRESENTATIVE"` string into the agent’s `roles` list.


# 5. Proto-Council Formation

## 5.1 Council creation condition

Whenever **two or more** pod representatives are physically present at `loc:well-core`
in the same tick (or within a short window), the system checks whether a proto-council
exists:

- If **no** council exists:
  - Create a new `Group` with:
    - `group_type = COUNCIL`
    - `name = "Founding Proto-Council"` (or similar)
    - `member_ids` = set of representative agent ids at the hub.
    - `parent_location_id = "loc:well-core"`
  - Add `GroupRole.COUNCIL_MEMBER` for those agents.
- If a council **already exists**:
  - Add newly arrived representatives as members if they’re not already in it
    (up to some soft maximum size, e.g. 8–10 members).


## 5.2 Council meetings

A council meeting is triggered when:

- A council group exists **and**
- At least `min_council_members_for_meeting` (e.g. 2) are present at
  `loc:well-core` at the current tick **and**
- Sufficient time has passed since the last council meeting
  (`tick - group.last_meeting_tick >= council_meeting_cooldown_ticks`).

When a council meeting occurs:

- A `COUNCIL_MEETING` episode is generated for each participant (see `D-AGENT-0022`).
- The council:
  - Aggregates hazard-related episodes known to its members.
  - Updates its risk assessment for corridors using these episodes.
  - May create or update **group goals**:
    - `GATHER_INFORMATION`
    - `AUTHOR_PROTOCOL`


# 6. Group Goals and Projection

## 6.1 Group goals for the proto-council

The proto-council uses **group-level goals** to organize work:

- `GATHER_INFORMATION`:
  - Target: one or more corridor ids (e.g. `loc:corridor-7A`).
  - Motivation: understand risk and alternative routes.
- `AUTHOR_PROTOCOL`:
  - Target: a corridor (or set) whose risk score exceeds a threshold.
  - Motivation: codify safer behavior into a protocol.

Group goals should be represented using the same `Goal` dataclass as individual
goals (see `D-AGENT-0022`), with:

- `owner_id = group_id` (e.g. `"group:council:alpha"`).
- `origin = GoalOrigin.GROUP_DECISION`.
- `target` payload specifying corridor ids, risk metrics, etc.


## 6.2 Projecting group goals to individual goals

When a council group goal is created, it must be **projected** into personal goals
for specific agents.

MVP projection:

- For a `GATHER_INFORMATION` group goal:
  - Choose **scouts** from the pool of:
    - Council members,
    - Pod representatives,
    - Or other agents with good DEX/END and bravery.
  - Mark their group roles:
    - Add `GroupRole.SCOUT` in `roles_by_agent` for the appropriate group(s).
  - For each scout:
    - Add a personal `Goal` with:
      - `goal_type = GATHER_INFORMATION`
      - `origin = GoalOrigin.GROUP_DECISION`
      - `parent_goal_id` = the council group goal id (optional but nice).
      - `target` including:
        - `{"corridor_ids": [...], "group_goal_id": group_goal_id}`.

- For an `AUTHOR_PROTOCOL` group goal:
  - Select a **scribe** (agent with higher INT/WIL, more routine-seeking).
  - Mark with `GroupRole.SCRIBE` in the council group.
  - Add a personal `Goal` for the scribe:
    - `goal_type = AUTHOR_PROTOCOL`
    - `origin = GoalOrigin.GROUP_DECISION`
    - `target` referencing:
      - Corridor ids,
      - Risk metrics,
      - Proposed rule skeleton.

The individual agents’ decision loops then see these new goals in their goal stacks
and bias behavior accordingly (e.g. scouts are more likely to leave the pod and
traverse the targeted corridors).


# 7. Event & Function Surface (for Codex)

This section defines the main functions that Codex should implement to support pod
groups and the proto-council in the Founding Wakeup MVP.

Suggested module: `src/dosadi/agents/groups.py`.


## 7.1 Group creation helpers

```python
from typing import Dict, List, Optional, Tuple
from dosadi.agents.core import AgentState, Goal, GoalType, GoalOrigin, GoalStatus, GoalHorizon


def create_pod_group(pod_location_id: str, member_ids: List[str], tick: int) -> Group:
    """Create a Group of type POD for a given pod location.

    - group_id can be derived from pod_location_id or generated via make_group_id.
    - parent_location_id should be set to pod_location_id.
    """
    ...


def create_proto_council(member_ids: List[str], tick: int) -> Group:
    """Create the initial proto-council Group at the well-core hub.

    - group_type = COUNCIL
    - parent_location_id = "loc:well-core"
    - Assign COUNCIL_MEMBER role to each member.
    """
    ...
```


## 7.2 Pod meetings and representative selection

```python
def maybe_run_pod_meeting(
    pod_group: Group,
    agents_by_id: Dict[str, AgentState],
    tick: int,
    rng,
    meeting_interval_ticks: int,
    rep_vote_fraction_threshold: float = 0.4,
    min_leadership_threshold: float = 0.6,
    max_representatives: int = 2,
) -> None:
    """Possibly run a pod meeting and update pod representatives.

    - Decide whether a meeting occurs based on tick, meeting_interval_ticks,
      and possibly randomness.
    - Select attending members (e.g. agents whose location_id == pod_group.parent_location_id).
    - Update competence scores (implementation detail can be internal).
    - Evaluate votes and assign POD_REPRESENTATIVE roles as needed.
    """
    ...
```

**Trigger and consequence details**

- **When it fires:**
  - Skips immediately if the configured `meeting_interval_ticks` is `<= 0`.
  - Requires at least `meeting_interval_ticks` since `pod_group.last_meeting_tick`.
  - Requires the pod to have at least two members physically present at the `parent_location_id`; otherwise the meeting is treated as held but ends early with only `last_meeting_tick` updated.
- **How representatives are chosen:**
  - Every present member “votes” for the most competent podmate (highest `leadership_weight` plus a small noise term) drawn from the entire pod membership.
  - Candidates become representatives when both of these are true: their vote share is at least `rep_vote_fraction_threshold` **and** their `leadership_weight` is at least `min_leadership_threshold`.
  - The loop walks ranked vote totals until `max_representatives` are reached, allowing continuity of existing reps.
- **State changes:**
  - `POD_REPRESENTATIVE` roles are added/removed inside `roles_by_agent` to match the chosen set, and `last_meeting_tick` is set to the current tick.
  - No goals or episodes are emitted here; downstream systems should watch role changes if they need to react to new spokespeople.


## 7.3 Proto-council formation and meetings

```python
def maybe_form_proto_council(
    groups: List[Group],
    agents_by_id: Dict[str, AgentState],
    tick: int,
    hub_location_id: str = "loc:well-core",
) -> Optional[Group]:
    """Create or extend the proto-council if conditions are met.

    - Check if a council group (GroupType.COUNCIL) already exists.
    - Find pod representatives currently at the hub location.
    - If >= 2 reps present and no council exists, create it.
    - If council exists, add new reps as members, up to some soft max size.

    Returns the council group (existing or newly created), or None if no council.
    """
    ...


def maybe_run_council_meeting(
    council_group: Group,
    agents_by_id: Dict[str, AgentState],
    tick: int,
    rng,
    cooldown_ticks: int,
) -> None:
    """Possibly run a council meeting.

    - Check if enough council members are present at the hub.
    - Enforce a cooldown between meetings.
    - If a meeting is run:
      - Generate COUNCIL_MEETING episodes for participants.
      - Aggregate hazard-related episodes to update corridor risk assessments.
      - Create/maintain group-level GATHER_INFORMATION or AUTHOR_PROTOCOL goals
        when thresholds are met.
    """
    ...
```

**Trigger and consequence details**

- **When it fires:**
  - Skips if `cooldown_ticks` is `<= 0` or if `tick - last_meeting_tick < cooldown_ticks`.
  - Requires at least two council members physically present at the hub (`hub_location_id`, default `loc:well-core`).
- **Baseline effect:**
  - On a valid meeting, only `last_meeting_tick` is updated inside this helper; emitting COUNCIL_MEETING episodes remains the responsibility of the surrounding simulation loop.
- **Protocol authoring hook:**
  - If both `metrics` and `cfg` are supplied, the helper scans corridor risk metrics via `_find_dangerous_corridors_from_metrics`, using `cfg.min_incidents_for_protocol` and `cfg.risk_threshold_for_protocol` as filters.
  - When dangerous corridors are found, the council selects a scribe (biased toward INT/WIL and low curiosity), adds a `SCRIBE` role, and injects an `AUTHOR_PROTOCOL` goal into that agent with targets listing the dangerous corridor ids.
  - No goal is created when metrics are missing, risk is below thresholds, or no eligible scribe exists; in those cases the function exits after updating `last_meeting_tick`.


## 7.4 Group goals and projection

```python
def ensure_council_gather_information_goal(
    council_group: Group,
    corridors_of_interest: List[str],
    tick: int,
) -> Goal:
    """Ensure the council has an active GATHER_INFORMATION group goal.

    - If one already exists and is ACTIVE, return it.
    - Otherwise, create a new Goal owned by the council group and add its id
      to council_group.goal_ids.
    """
    ...


def project_gather_information_to_scouts(
    council_group: Group,
    group_goal: Goal,
    agents_by_id: Dict[str, AgentState],
    rng,
    max_scouts: int = 3,
) -> None:
    """Assign GATHER_INFORMATION goals to selected scouts.

    - Choose scouts favoring higher DEX/END and bravery.
    - Add SCOUT role in the council_group.roles_by_agent map.
    - Append individual GATHER_INFORMATION goals to chosen AgentState.goals
      with origin = GROUP_DECISION.
    """
    ...


def project_author_protocol_to_scribe(
    council_group: Group,
    group_goal: Goal,
    agents_by_id: Dict[str, AgentState],
    rng,
) -> None:
    """Assign an AUTHOR_PROTOCOL goal to a selected scribe.

    - Choose scribe favoring higher INT/WIL and routine-seeking personalities.
    - Add SCRIBE role in the council_group.roles_by_agent map.
    - Append individual AUTHOR_PROTOCOL goal to AgentState.goals
      with origin = GROUP_DECISION.
    """
    ...
```


# 8. Integration Notes

- Group mechanics are **invoked by the runtime loop**, not vice versa:
  - At each tick, the runtime can:
    - Call `maybe_run_pod_meeting` for each pod group at the configured cadence.
    - Call `maybe_form_proto_council` to create/extend the council.
    - Call `maybe_run_council_meeting` for the council with its cooldown.
- Agents remain the locus of action:
  - Groups only create/assign goals and interpret episodes.
  - Individual agents still decide whether to comply, travel, scout, or draft protocols.

In this MVP, enforcement and sanctions are minimal; the main objective is to see
**emergent structure**:

- Pod representatives,
- A proto-council,
- Group-level goals,
- First movement/safety protocols.
