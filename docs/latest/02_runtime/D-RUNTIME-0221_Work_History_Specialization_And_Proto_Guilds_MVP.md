---
title: Work_History_Specialization_And_Proto_Guilds_MVP
doc_id: D-RUNTIME-0221
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-06
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0212   # Initial_Work_Detail_Taxonomy_MVP
  - D-RUNTIME-0213   # Work_Detail_Behaviors_MVP_Scout_And_Inventory
  - D-RUNTIME-0214   # Council_Metrics_And_Staffing_Response_MVP
  - D-RUNTIME-0215   # Food_Halls_Queues_And_Daily_Eating_MVP
  - D-RUNTIME-0216   # Environment_Control_And_Comfort_MVP
  - D-RUNTIME-0217   # Well_Water_Handling_And_Distribution_MVP
  - D-RUNTIME-0218   # Hydration_And_Water_Access_MVP
  - D-RUNTIME-0219   # Needs_Stress_And_Performance_MVP
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
---

# Work History, Specialization, and Proto-Guilds (MVP) — D-RUNTIME-0221

## 1. Purpose & scope

This document specifies a minimal **work history → specialization → crew**
loop that turns generic colonists into recognizable occupational blocs.

Loop (MVP):

1. Each agent accumulates **work history counters** per `WorkDetailType`.
2. Work history is mapped into coarse **proficiency scores** (0–1) per type.
3. Proficiency slightly boosts performance *for that work type*.
4. The council uses work history when assigning agents to persistent
   **task-forces / crews** for each work type.
5. Episodes referencing crews slowly seed **proto-guild identity**.

Scope (MVP):

- No full skill tree; we use simple counters and derived 0–1 proficiencies.
- Crews are just persistent labels (`crew_id` + membership), not full faction
  objects yet.
- Council only does **lightly smarter assignments** based on experience and
  current stress/morale.

This sits on top of the existing loops (food, water, needs, sleep) and moves
us toward Phase 0 guild-like structure without adding new political systems.


## 2. Agent-level work history and crew membership

### 2.1 Work history struct

Extend the agent state with a compact history for work details.

Define a small dataclass in e.g. `dosadi/agents/work_history.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from dosadi.runtime.work_details import WorkDetailType


@dataclass
class WorkDetailHistory:
    # Total "effective ticks" spent on this work type (already performance-weighted)
    ticks: float = 0.0

    # Number of distinct shifts/assignments (completed work detail goals)
    shifts: int = 0

    # Cached proficiency in [0.0, 1.0]
    proficiency: float = 0.0


@dataclass
class WorkHistory:
    # Map from WorkDetailType to per-type history
    per_type: Dict[WorkDetailType, WorkDetailHistory] = field(default_factory=dict)

    def get_or_create(self, work_type: WorkDetailType) -> WorkDetailHistory:
        if work_type not in self.per_type:
            self.per_type[work_type] = WorkDetailHistory()
        return self.per_type[work_type]
```

### 2.2 AgentState extensions

In `AgentState` (D-AGENT-0022 implementation), add:

```python
from dataclasses import dataclass, field
from typing import Optional

from dosadi.agents.work_history import WorkHistory

@dataclass
class AgentState:
    ...
    work_history: WorkHistory = field(default_factory=WorkHistory)

    # Optional persistent crew affiliation for current primary work
    current_crew_id: Optional[str] = None
```

Notes:

- `current_crew_id` is a simple string, e.g. `"crew:water:1"`, `"crew:scout:0"`.
- Multiple roles per agent are allowed; MVP treats `current_crew_id` as their
  primary crew.


## 3. Accumulating work history

### 3.1 Effective ticks per work detail

We already compute a **performance multiplier** per agent (D-RUNTIME-0219).
For every tick that an agent is executing a work detail, we:

1. Compute `perf = compute_performance_multiplier(physical)`.
2. Decrement `ticks_remaining` by `perf` for that work detail goal.
3. Add `perf` to the agent’s work history for that `WorkDetailType`.


### 3.2 Handler integration

In each `_handle_*` function for work details that use `ticks_remaining`:

- `SCOUT_INTERIOR`
- `INVENTORY_STORES`
- `FOOD_PROCESSING`
- `ENV_CONTROL`
- `WATER_HANDLING`
- (and any future long-running work types)

We already have a pattern like:

```python
ticks_remaining = _ensure_ticks_remaining(...)
perf = compute_performance_multiplier(agent.physical)
ticks_remaining -= perf
goal.metadata["ticks_remaining"] = ticks_remaining
```

Augment it to record work history:

```python
from dosadi.agents.work_history import WorkHistory  # type import only
from dosadi.runtime.work_details import WorkDetailType

def _handle_some_work_detail(..., work_type: WorkDetailType, ...):
    ...
    ticks_remaining = _ensure_ticks_remaining(goal, work_type, default_fraction=0.3)
    base_perf = compute_performance_multiplier(agent.physical)
    # specialization multiplier will be added in section 5
    perf = base_perf
    ticks_remaining -= perf
    goal.metadata["ticks_remaining"] = ticks_remaining

    # Accumulate work history
    wh = agent.work_history.get_or_create(work_type)
    wh.ticks += perf

    if ticks_remaining <= 0:
        wh.shifts += 1
        goal.status = GoalStatus.COMPLETED
        return
```

If `_handle_*` functions do not currently receive `work_type`, we can:

- either add it as an explicit parameter, or
- infer it from the goal’s `work_type` field.


## 4. Proficiency derivation

### 4.1 Mapping ticks to proficiency

We want a **smooth, saturating** mapping:

- e.g. reaching ~80% proficiency after a certain “practice horizon”,
- never exceeding 1.0.

Define per-type horizon constants:

```python
WORK_PROFICIENCY_HORIZONS = {
    WorkDetailType.SCOUT_INTERIOR: 80_000.0,     # effective ticks
    WorkDetailType.INVENTORY_STORES: 80_000.0,
    WorkDetailType.FOOD_PROCESSING: 60_000.0,
    WorkDetailType.ENV_CONTROL: 60_000.0,
    WorkDetailType.WATER_HANDLING: 60_000.0,
}
```

Proficiency mapping (e.g. in `work_history.py`):

```python
import math

def ticks_to_proficiency(work_type: WorkDetailType, ticks: float) -> float:
    horizon = WORK_PROFICIENCY_HORIZONS.get(work_type, 80_000.0)
    if horizon <= 0.0:
        return 0.0
    x = max(0.0, ticks) / horizon
    # Simple saturating curve: 1 - exp(-x)
    prof = 1.0 - math.exp(-x)
    if prof < 0.0:
        prof = 0.0
    elif prof > 1.0:
        prof = 1.0
    return prof
```

### 4.2 Proficiency refresh

We can refresh proficiencies:

- either incrementally whenever ticks change, or
- periodically (e.g. once per “day” tick window).

MVP: update proficiencies at the end of each completed shift:

```python
wh.proficiency = ticks_to_proficiency(work_type, wh.ticks)
```

Optionally, we can also add a “slow forgetting” term later.


## 5. Using proficiency in performance

### 5.1 Local work-type multiplier

We already have `compute_performance_multiplier(physical)` from
D-RUNTIME-0219. For specialization we add a **per-work-type modifier**.

In `physiology.py` or `work_history.py` add:

```python
from dosadi.runtime.work_details import WorkDetailType
from dosadi.agents.state import AgentState

def compute_specialization_multiplier(
    agent: AgentState,
    work_type: WorkDetailType,
) -> float:
    wh = agent.work_history.get_or_create(work_type)
    prof = wh.proficiency  # 0..1

    # Up to +20% speed at full proficiency
    multiplier = 1.0 + 0.2 * prof

    if multiplier < 0.8:
        multiplier = 0.8
    elif multiplier > 1.2:
        multiplier = 1.2

    return multiplier
```

### 5.2 Combined effective performance

In each work detail handler, replace the simple:

```python
perf = compute_performance_multiplier(agent.physical)
```

with:

```python
base_perf = compute_performance_multiplier(agent.physical)
spec_mult = compute_specialization_multiplier(agent, work_type)
perf = base_perf * spec_mult
```

This ensures:

- hungry, stressed agents still slow down,
- but within that, experienced agents are faster **on their specialty**.


## 6. Crews: persistent task-forces

### 6.1 World-level crew registry

We introduce a simple world-level structure to track crews per work type.

In `WorldState`:

```python
from dataclasses import dataclass, field
from typing import Dict, List
from dosadi.runtime.work_details import WorkDetailType

@dataclass
class CrewState:
    crew_id: str
    work_type: WorkDetailType
    member_ids: List[str] = field(default_factory=list)


@dataclass
class WorldState:
    ...
    crews: Dict[str, CrewState] = field(default_factory=dict)
```

We will use crew ids like `"crew:water:0"`, `"crew:scout:1"`.


### 6.2 Crew membership on agents

We already added `current_crew_id: Optional[str]` to `AgentState`.

When the council assigns an agent to a work detail (see below), it will:

- ensure the agent is a member of some crew for that work type,
- set `agent.current_crew_id` accordingly.

Crews do not yet confer any special mechanics; they are grouping labels.


## 7. Council assignment using specialization

### 7.1 Desired staffing (existing)

The council already computes desired headcounts per `WorkDetailType` in
D-RUNTIME-0214 and later runtime docs. We will **reuse** that, but change
*which* agents are picked for each type.

### 7.2 Assignment ranking

For each `WorkDetailType T`, the council needs to pick `N` agents. For each
candidate agent, we define a **suitability score**:

```text
suitability(agent, T) =
    w_prof * proficiency_T(agent)
  + w_morale * morale_level(agent)
  - w_stress * stress_level(agent)
```

Suggested weights:

```python
w_prof = 0.6
w_morale = 0.2
w_stress = 0.2
```

If needed we can add mild penalties for very high hunger/sleep pressure later.

### 7.3 Assignment procedure

Pseudocode inside `update_council_metrics_and_staffing` or a helper:

```python
def assign_work_crews(world: WorldState, desired_counts: Dict[WorkDetailType, int]) -> None:
    agents = list(world.agents.values())

    for work_type, target_count in desired_counts.items():
        # Score all agents
        scored = []
        for agent in agents:
            # Skip agents who are sleeping or otherwise unavailable
            if agent.physical.is_sleeping:
                continue

            wh = agent.work_history.get_or_create(work_type)
            prof = wh.proficiency
            stress = agent.physical.stress_level
            morale = agent.physical.morale_level

            score = 0.6 * prof + 0.2 * morale - 0.2 * stress
            scored.append((score, agent))

        # Sort by descending score
        scored.sort(key=lambda pair: pair[0], reverse=True)

        # Pick top N
        selected_agents = [a for (_s, a) in scored[:target_count]]

        # Ensure crew exists
        crew_id = _ensure_default_crew_for_type(world, work_type)

        crew = world.crews[crew_id]
        crew.member_ids = [a.id for a in selected_agents]

        # Update agents
        for agent in selected_agents:
            agent.current_crew_id = crew_id
```

Helper `_ensure_default_crew_for_type`:

```python
def _ensure_default_crew_for_type(world: WorldState, work_type: WorkDetailType) -> str:
    prefix = f"crew:{work_type.name.lower()}"
    # Try to find an existing crew
    for crew_id, crew in world.crews.items():
        if crew.work_type == work_type and crew_id.startswith(prefix):
            return crew_id

    # Otherwise create one
    crew_id = f"{prefix}:0"
    world.crews[crew_id] = CrewState(
        crew_id=crew_id,
        work_type=work_type,
        member_ids=[],
    )
    return crew_id
```

This is intentionally minimal:

- one crew per work type for now,
- membership is reassigned as desired counts change.

Later we can add multiple crews per type and rotation policies.


## 8. Crew-related episodes and proto-guild identity

### 8.1 Episodes referencing crew membership

We lightly extend existing **work episodes** to carry `crew_id` where relevant.

For example, when the agent completes a WATER_HANDLING shift, we can emit a
“worked shift” episode with crew context:

```python
factory = EpisodeFactory(world=world)
ep = factory.create_work_shift_completed_episode(
    owner_agent_id=agent.id,
    tick=world.current_tick,
    work_type=work_type,
    crew_id=agent.current_crew_id,
)
agent.record_episode(ep)
```

The MVP `Episode` payload could include:

- `target_type = OTHER`,
- `verb = WORK_SHIFT_COMPLETED` (new `EpisodeVerb`),
- tags such as `{"work", work_type.name.lower(), "crew"}`,
- `details = {"work_type": work_type.name, "crew_id": crew_id or ""}`.

These episodes will be compressed into beliefs later; for now they mainly
serve as a record of occupational identity.

### 8.2 Optional: simple crew belief summary

We are not yet introducing full **crew/faction belief** objects. However,
Tier-2 and Tier-3 agents can:

- maintain beliefs about **places** where crews gather (already supported),
- and we can later add lightweight beliefs about `crew_id` strings if needed.

MVP: crew identity is implicit in repeated work episodes and `current_crew_id`.


## 9. Integration order & boundaries

### 9.1 Recommended implementation steps

1. Add `WorkHistory` and `WorkDetailHistory` structs.
2. Extend `AgentState` with `work_history` and `current_crew_id`.
3. Wire work history accumulation into all long-running work detail handlers.
4. Add `ticks_to_proficiency` and update `WorkDetailHistory.proficiency`
   when shifts complete.
5. Add `compute_specialization_multiplier` and include it in per-work-type
   performance calculations.
6. Add `CrewState` and `WorldState.crews`.
7. Implement crew assignment helper (`assign_work_crews`) to use proficiency,
   morale, and stress for staffing.
8. Optionally add a `WORK_SHIFT_COMPLETED` episode (or re-use an existing
   work-related verb) to record crew-tagged work episodes.

### 9.2 Simplifications

- Only **one crew per work type** in MVP; crew rotation and multiple crews
  per type come later.
- No explicit penalties for switching specialties yet, but the proficiency
  mapping strongly encourages sticking with a specialty.
- Council assignment runs at the same cadence as existing staffing updates
  (e.g. once per “day” or every N ticks).

Once D-RUNTIME-0221 is implemented, the sim will naturally produce:

- agents with **visible occupational histories**,
- differentiated **specialists** and **generalists**,
- persistent **crews** as the proto-form of guilds and work blocs,

all from the same underlying agent/goal/episode machinery.
