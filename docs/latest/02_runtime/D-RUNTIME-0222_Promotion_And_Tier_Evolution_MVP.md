---
title: Promotion_And_Tier_Evolution_MVP
doc_id: D-RUNTIME-0222
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-06
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0212   # Initial_Work_Detail_Taxonomy_MVP
  - D-RUNTIME-0213   # Work_Detail_Behaviors_MVP_Scout_And_Inventory
  - D-RUNTIME-0214   # Council_Metrics_And_Staffing_Response_MVP
  - D-RUNTIME-0219   # Needs_Stress_And_Performance_MVP
  - D-RUNTIME-0221   # Work_History_Specialization_And_Proto_Guilds_MVP
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
---

# Promotion and Tier Evolution (MVP) — D-RUNTIME-0222

## 1. Purpose & scope

This document specifies a minimal **promotion loop** that gradually creates
Tier-2 supervisors from Tier-1 workers, based on:

- accumulated **work history** and specialization,
- basic **stress/morale** state,
- and simple **council heuristics**.

Loop (MVP):

1. Agents accumulate work history and proficiency per work type
   (D-RUNTIME-0221).
2. Periodically, the council scans for **crew leads** for each work type.
3. Eligible agents are **promoted** to Tier-2 supervisors for a specific
   work type and assigned as crew leads.
4. Council staffing logic treats crew leads differently from regular crew
   members (less hands-on work, more coordination in future phases).

Scope (MVP):

- Promotions only from Tier-1 → Tier-2.
- No demotions or Tier-3 creation yet.
- No special protocol/authoring powers yet; Tier-2 are simply tagged as
  “supervisors” with a primary crew to lead.

This creates the **first vertical differentiation** in the colony without
importing any external hierarchy.


## 2. Agent state extensions

### 2.1 Supervisor role and promotion tracking

Extend `AgentState` with:

```python
from dataclasses import dataclass, field
from typing import Optional, List
from dosadi.runtime.work_details import WorkDetailType

@dataclass
class AgentState:
    ...
    # If non-None, this agent is a Tier-2 supervisor for this work type.
    supervisor_work_type: Optional[WorkDetailType] = None

    # Crew this supervisor leads, if any.
    supervisor_crew_id: Optional[str] = None

    # Simple seniority / promotion score bookkeeping
    total_ticks_employed: float = 0.0
    times_promoted: int = 0
```

Notes:

- `tier` is already present (from D-AGENT-0022); we will set `tier = 2` for
  supervisors.
- `total_ticks_employed` is a monotonic scalar that grows whenever the agent
  is awake and active; we use it as a tie-breaker for promotion.


## 3. World-level promotion bookkeeping

### 3.1 Promotion cadence

We treat promotions as a **slow process** run at a low cadence (e.g. once per
sim “day”). Add constants in an appropriate runtime config module:

```python
PROMOTION_CHECK_INTERVAL_TICKS: int = 120_000  # ~one "day" at current scales
MIN_TICKS_BEFORE_PROMOTION: float = 200_000.0  # minimal employment duration
MIN_PROFICIENCY_FOR_SUPERVISOR: float = 0.5    # medium-specialized
MIN_SHIFTS_FOR_SUPERVISOR: int = 10
MAX_SUPERVISORS_PER_WORK_TYPE: int = 3         # MVP cap
```

### 3.2 Last promotion check tick

Extend `WorldState`:

```python
from dataclasses import dataclass, field

@dataclass
class WorldState:
    ...
    last_promotion_check_tick: int = 0
```

The council will only run promotion checks when:

```python
world.current_tick - world.last_promotion_check_tick >= PROMOTION_CHECK_INTERVAL_TICKS
```


## 4. Seniority accumulation

### 4.1 Per-tick employment ticks

Whenever an agent is **awake** and not in a terminal state, we increment:

```python
agent.total_ticks_employed += 1.0
```

This can be done in the main per-tick agent loop after physical updates but
before goal handling.

Depending on performance, this can be a constant (1.0) or scaled by the same
performance multiplier; MVP uses a simple constant.


## 5. Supervisor eligibility and ranking

### 5.1 Eligibility criteria

An agent is eligible to become a supervisor for work type `T` if:

- `agent.tier == 1` (currently a worker),
- `agent.supervisor_work_type is None`,
- `agent.total_ticks_employed >= MIN_TICKS_BEFORE_PROMOTION`,
- In `agent.work_history` for `T`:
  - `history.proficiency >= MIN_PROFICIENCY_FOR_SUPERVISOR`,
  - `history.shifts >= MIN_SHIFTS_FOR_SUPERVISOR`,
- `agent.physical.stress_level` is not extreme (e.g. `< 0.7`),
- `agent.physical.morale_level` is not catastrophic (e.g. `>= 0.3`).

### 5.2 Supervisor score

For each eligible agent and work type `T`, define a **supervisor score**:

```text
supervisor_score(agent, T) =
    w_prof * prof_T(agent)
  + w_sen  * normalized_seniority(agent)
  + w_mor  * morale(agent)
  - w_str  * stress(agent)
```

Suggested weights:

```python
w_prof = 0.5
w_sen  = 0.2
w_mor  = 0.2
w_str  = 0.1
```

Where:

- `prof_T(agent)` is `work_history.per_type[T].proficiency`,
- `normalized_seniority(agent)` is `min(1.0, agent.total_ticks_employed / SENIORITY_HORIZON)`,
- `SENIORITY_HORIZON` can be e.g. `400_000.0` ticks.

We use this for ranking candidates when creating or filling supervisor slots.


## 6. Promotion procedure

### 6.1 Entry point

Inside the council’s periodic update (e.g.
`update_council_metrics_and_staffing`), after computing staffing and crews:

```python
def maybe_run_promotion_cycle(world: WorldState) -> None:
    if world.current_tick - world.last_promotion_check_tick < PROMOTION_CHECK_INTERVAL_TICKS:
        return
    world.last_promotion_check_tick = world.current_tick
    _run_promotion_cycle(world)
```

Call `maybe_run_promotion_cycle(world)` once per tick (or per council update
tick).


### 6.2 Running a promotion cycle

```python
from typing import Dict, List, Tuple

from dosadi.runtime.work_details import WorkDetailType
from dosadi.agents.state import AgentState
from dosadi.agents.work_history import ticks_to_proficiency
from dosadi.runtime.world import CrewState  # adjust import

SENIORITY_HORIZON: float = 400_000.0


def _run_promotion_cycle(world: WorldState) -> None:
    agents: List[AgentState] = list(world.agents.values())

    # Count existing supervisors per work type
    sup_counts: Dict[WorkDetailType, int] = {}
    for agent in agents:
        if agent.supervisor_work_type is not None:
            sup_counts[agent.supervisor_work_type] = sup_counts.get(agent.supervisor_work_type, 0) + 1

    for work_type in WorkDetailType:
        current_sup = sup_counts.get(work_type, 0)
        if current_sup >= MAX_SUPERVISORS_PER_WORK_TYPE:
            continue

        candidate_scores: List[Tuple[float, AgentState]] = []

        for agent in agents:
            if not _is_eligible_supervisor_candidate(agent, work_type):
                continue

            wh = agent.work_history.get_or_create(work_type)
            prof = wh.proficiency
            seniority = min(1.0, agent.total_ticks_employed / SENIORITY_HORIZON)
            morale = agent.physical.morale_level
            stress = agent.physical.stress_level

            score = (
                0.5 * prof
                + 0.2 * seniority
                + 0.2 * morale
                - 0.1 * stress
            )
            candidate_scores.append((score, agent))

        if not candidate_scores:
            continue

        candidate_scores.sort(key=lambda pair: pair[0], reverse=True)

        # Promote top candidate (one per work_type per cycle)
        best_score, best_agent = candidate_scores[0]
        _promote_to_supervisor(world, best_agent, work_type)
```

Helper for eligibility:

```python
def _is_eligible_supervisor_candidate(agent: AgentState, work_type: WorkDetailType) -> bool:
    if agent.tier != 1:
        return False
    if agent.supervisor_work_type is not None:
        return False
    if agent.total_ticks_employed < MIN_TICKS_BEFORE_PROMOTION:
        return False

    wh = agent.work_history.get_or_create(work_type)
    if wh.proficiency < MIN_PROFICIENCY_FOR_SUPERVISOR:
        return False
    if wh.shifts < MIN_SHIFTS_FOR_SUPERVISOR:
        return False

    if agent.physical.stress_level > 0.7:
        return False
    if agent.physical.morale_level < 0.3:
        return False

    return True
```


### 6.3 Promotion effect

Promotion helper:

```python
from dosadi.memory.episode_factory import EpisodeFactory
from dosadi.memory.episodes import EpisodeVerb, EpisodeTargetType, EpisodeGoalRelation, EpisodeOutcome


def _promote_to_supervisor(
    world: WorldState,
    agent: AgentState,
    work_type: WorkDetailType,
) -> None:
    agent.tier = 2
    agent.supervisor_work_type = work_type
    agent.times_promoted += 1

    # Try to attach them to an existing crew for this work type
    crew_id = _ensure_default_crew_for_type(world, work_type)
    crew = world.crews[crew_id]
    agent.supervisor_crew_id = crew_id

    # Make sure they are a member of the crew (if we want that invariant)
    if agent.id not in crew.member_ids:
        crew.member_ids.append(agent.id)

    # Emit a promotion episode for the agent
    factory = EpisodeFactory(world=world)
    ep = factory.create_promotion_episode(
        owner_agent_id=agent.id,
        tick=world.current_tick,
        work_type=work_type,
        new_tier=2,
        crew_id=crew_id,
    )
    agent.record_episode(ep)
```


## 7. Crew leads and staffing interaction

### 7.1 Supervisors vs. regular crew

In `assign_work_crews`, we want to:

- Prefer supervisors as members of crews of their `supervisor_work_type`,
- But avoid *only* selecting supervisors as workers — they are meant to be
  part of the crew but could later take on organizational roles.

MVP approach:

- When computing `scored` agents for work type `T`, still consider everyone.
- Do not add any special bonus for being a supervisor; their higher
  proficiency should already lift them.
- Later we can add a separate “crew lead” concept inside `CrewState`.


### 7.2 Optional: `CrewState.leader_id`

If we want a clear crew lead now:

```python
@dataclass
class CrewState:
    crew_id: str
    work_type: WorkDetailType
    member_ids: List[str] = field(default_factory=list)
    leader_id: Optional[str] = None
```

After promotion, if the promoted supervisor’s `supervisor_crew_id` matches a
crew, we can set:

```python
crew.leader_id = agent.id
```

This has no immediate mechanical effect in MVP but is valuable for:

- later routing crew-level decisions,
- narrative interrogation (“who’s in charge of the water crew?”).


## 8. Promotion episodes

### 8.1 Episode verb

Add to `EpisodeVerb` enum:

```python
class EpisodeVerb(Enum):
    ...
    PROMOTED_TO_TIER = auto()
```

### 8.2 EpisodeFactory helper

In `EpisodeFactory`:

```python
from typing import Optional
from dosadi.runtime.work_details import WorkDetailType

def create_promotion_episode(
    self,
    owner_agent_id: str,
    tick: int,
    work_type: WorkDetailType,
    new_tier: int,
    crew_id: Optional[str],
) -> Episode:
    tags = {"promotion", "work", work_type.name.lower()}
    if crew_id:
        tags.add("crew")

    return Episode(
        episode_id=self._next_episode_id(),
        owner_agent_id=owner_agent_id,
        tick=tick,
        location_id=None,
        channel=EpisodeChannel.DIRECT,
        target_type=EpisodeTargetType.SELF,
        target_id=owner_agent_id,
        verb=EpisodeVerb.PROMOTED_TO_TIER,
        summary_tag="promotion",
        goal_relation=EpisodeGoalRelation.SUPPORTS,
        goal_relevance=0.4,
        outcome=EpisodeOutcome.SUCCESS,
        emotion=EmotionSnapshot(valence=0.6, arousal=0.4, threat=0.0),
        importance=0.4,
        reliability=0.9,
        tags=tags,
        details={
            "work_type": work_type.name,
            "new_tier": int(new_tier),
            "crew_id": crew_id or "",
        },
    )
```

These episodes will be compressed into beliefs as the agent’s sense of
identity (“I’m a supervisor for water handling”).


## 9. Integration order & boundaries

### 9.1 Implementation steps

1. Extend `AgentState` with supervisor fields and `total_ticks_employed`.
2. Increment `total_ticks_employed` each tick for awake, non-terminal agents.
3. Add promotion-related constants and `WorldState.last_promotion_check_tick`.
4. Implement `_is_eligible_supervisor_candidate`, `_run_promotion_cycle`,
   `_promote_to_supervisor`, and `maybe_run_promotion_cycle`.
5. Wire `maybe_run_promotion_cycle(world)` into the council update cadence.
6. (Optional) Extend `CrewState` with `leader_id` and update after promotions.
7. Add `PROMOTED_TO_TIER` verb and `create_promotion_episode` in
   `EpisodeFactory`.

### 9.2 Simplifications

- Only Tier-1 → Tier-2 promotion; no Tier-3 yet.
- No demotion logic or burnout; supervisors can become overstressed but stay
  in role for now.
- No direct protocol-authoring powers yet; supervisors are just **tagged**
  for future use by Tier-3 pattern readers.

Once D-RUNTIME-0222 is implemented, the sim will gradually produce:

- identifiable **crew leaders**,
- a small but real Tier-2 stratum born from work history and council logic,

laying the groundwork for emergent ward hierarchies and, eventually,
political conflict over who controls which crews and resources.
