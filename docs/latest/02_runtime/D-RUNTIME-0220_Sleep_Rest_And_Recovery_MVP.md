---
title: Sleep_Rest_And_Recovery_MVP
doc_id: D-RUNTIME-0220
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-03
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0212   # Initial_Work_Detail_Taxonomy_MVP
  - D-RUNTIME-0215   # Food_Halls_Queues_And_Daily_Eating_MVP
  - D-RUNTIME-0218   # Hydration_And_Water_Access_MVP
  - D-RUNTIME-0219   # Needs_Stress_And_Performance_MVP
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
  - D-MEMORY-0205    # Place_Belief_Updates_From_Queue_Episodes_MVP_v0
  - D-MEMORY-0300    # Sleep_And_Episode_Consolidation_Design
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
---

# Sleep, Rest, and Recovery (MVP) — D-RUNTIME-0220

## 1. Purpose & scope

This document specifies a **minimal sleep/rest loop** that connects:

- time awake, hunger, and hydration → **sleep pressure**,
- sleep pressure → **REST_TONIGHT / GO_SLEEP** goals and actions,
- sleep episodes → **episode consolidation** (D-MEMORY-0300),
- sleep → gradual **recovery** of stress and morale.

Loop (MVP):

1. Agents accumulate **sleep pressure** as they stay awake.
2. When pressure is high and basic needs are not in crisis, they seek a bunk
   and **sleep** for a coarse “block” of ticks.
3. During sleep:
   - we call the **memory consolidation** logic for that agent,
   - stress decreases and morale drifts up toward baseline,
   - hunger and hydration slowly worsen (but not catastrophically).

Scope (MVP):

- Single sleep block per “day” (no naps yet).
- No shift scheduling or explicit “night/day” at the world level yet.
- No explicit insomnia or trauma effects; those can be layered on later.

This loop ties the episodic memory design into the runtime and connects sleep
to both cognition and performance indirectly.


## 2. Agent state for sleep

### 2.1 PhysicalState fields

Extend `PhysicalState` (if not already present) with:

```python
from dataclasses import dataclass

@dataclass
class PhysicalState:
    ...
    is_sleeping: bool = False
    sleep_pressure: float = 0.0      # 0.0 = fully rested, 1.0 = exhausted
    last_sleep_tick: int = 0
```

- `sleep_pressure` is clamped to `[0.0, 1.0]`.
- `is_sleeping` is a coarse flag; we don’t need finer sleep stages for MVP.


## 3. Sleep pressure dynamics

### 3.1 Accumulation while awake

Each tick when an agent is **awake** (`is_sleeping == False`):

- Increase `sleep_pressure` at a slow, roughly linear rate.
- Let hunger and stress amplify the rate slightly.

Heuristic constants:

```python
SLEEP_BASE_ACCUM_PER_TICK = 1.0 / 120_000.0  # ~1.2 "days" to full pressure if nothing else
SLEEP_HUNGER_MODIFIER = 0.2                  # hunger contribution
SLEEP_STRESS_MODIFIER = 0.3                  # stress contribution
```

Update logic:

```python
def accumulate_sleep_pressure(physical: PhysicalState) -> None:
    if physical.is_sleeping:
        return

    base = SLEEP_BASE_ACCUM_PER_TICK
    extra = (
        SLEEP_HUNGER_MODIFIER * max(0.0, physical.hunger_level) +
        SLEEP_STRESS_MODIFIER * max(0.0, physical.stress_level)
    )
    physical.sleep_pressure += base + extra * SLEEP_BASE_ACCUM_PER_TICK
    if physical.sleep_pressure > 1.0:
        physical.sleep_pressure = 1.0
```


### 3.2 Recovery while sleeping

While sleeping, `sleep_pressure` decays toward zero:

```python
SLEEP_RECOVERY_RATE = 1.0 / 40_000.0  # ~0.4 "day" of continuous sleep to fully reset

def recover_sleep_pressure(physical: PhysicalState) -> None:
    if not physical.is_sleeping:
        return

    physical.sleep_pressure -= SLEEP_RECOVERY_RATE
    if physical.sleep_pressure < 0.0:
        physical.sleep_pressure = 0.0
```


## 4. Sleep goals and decisions

### 4.1 Goal type

Add a goal type for rest, e.g.:

```python
from enum import Enum, auto

class GoalType(Enum):
    ...
    GET_MEAL_TODAY = auto()
    GET_WATER_TODAY = auto()
    REST_TONIGHT = auto()
```

The semantics of `REST_TONIGHT` are:

- get to an acceptable bunk/sleep facility,
- remain sleeping for at least a minimum number of ticks,
- then wake up with reduced sleep pressure.


### 4.2 Goal creation conditions

We want agents to **prefer** eating and drinking over sleep when needs are bad,
but to eventually rest when `sleep_pressure` is high.

Heuristic thresholds:

```python
SLEEP_PRESSURE_GOAL_THRESHOLD = 0.6
SLEEP_PRESSURE_FORCE_THRESHOLD = 0.9
MIN_TICKS_BETWEEN_SLEEP_GOALS = 40_000   # avoid oscillation
```

Creation logic (MVP):

```python
def has_active_or_pending_rest_goal(agent: AgentState) -> bool:
    for g in agent.goals:
        if g.goal_type == GoalType.REST_TONIGHT and g.status in (
            GoalStatus.PENDING,
            GoalStatus.ACTIVE,
        ):
            return True
    return False


def maybe_create_rest_goal(world: WorldState, agent: AgentState) -> None:
    physical = agent.physical

    if physical.is_sleeping:
        return
    if physical.sleep_pressure < SLEEP_PRESSURE_GOAL_THRESHOLD:
        return
    if has_active_or_pending_rest_goal(agent):
        return
    if world.current_tick - physical.last_sleep_tick < MIN_TICKS_BETWEEN_SLEEP_GOALS:
        return

    # If hunger or hydration are in critical ranges, skip for now;
    # we want GET_MEAL / GET_WATER to take priority.
    if physical.hunger_level > 1.0 or physical.hydration_level < 0.3:
        return

    goal = Goal(
        goal_id=f"goal:rest:{agent.id}:{world.current_tick}",
        goal_type=GoalType.REST_TONIGHT,
        status=GoalStatus.PENDING,
        created_tick=world.current_tick,
        metadata={},
    )
    agent.goals.append(goal)
```

Call `maybe_create_rest_goal` after hunger/hydration updates and goal creation
for food and water.


### 4.3 Selecting a sleep place

When `REST_TONIGHT` is the focus goal, agent should:

1. Enumerate candidate sleep places:
   - initially just bunk pods (`kind = "bunk_pod"`).

2. Use place beliefs (comfort, safety, congestion) and possibly distance to
   choose a bunk, similar to mess-hall / queue selection:

   ```text
   utility(pod) =
       w_safe * safety_score
     + w_comf * comfort_score
     - w_cong * congestion_score
     - w_dist * distance
   ```

3. Store chosen bunk in `goal.metadata["target_sleep_place_id"]`.


## 5. Sleep behavior and memory consolidation

### 5.1 Minimum sleep block

Define a minimum sleep block length and a maximum:

```python
MIN_SLEEP_BLOCK_TICKS = 40_000
MAX_SLEEP_BLOCK_TICKS = 120_000
```

Use `goal.metadata["sleep_ticks_remaining"]` to track progress.

### 5.2 Handler for REST_TONIGHT

Add to the goal dispatcher:

```python
def _handle_goal(world, agent, goal, rng):
    ...
    if goal.goal_type == GoalType.REST_TONIGHT:
        _handle_rest_goal(world, agent, goal, rng)
        return
```

Implementation sketch:

```python
from dosadi.agents.goals import GoalStatus
from dosadi.memory.sleep_consolidation import consolidate_sleep_for_agent  # or similar

def _handle_rest_goal(
    world: WorldState,
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    physical = agent.physical
    meta = goal.metadata

    # Initialize sleep target if needed
    if "sleep_ticks_remaining" not in meta:
        meta["sleep_ticks_remaining"] = float(
            rng.randint(MIN_SLEEP_BLOCK_TICKS, MAX_SLEEP_BLOCK_TICKS)
        )
        # choose sleep place now
        sleep_place_id = _choose_sleep_place(world, agent, rng)
        if sleep_place_id is None:
            goal.status = GoalStatus.FAILED
            return
        meta["target_sleep_place_id"] = sleep_place_id

    target_sleep_place_id = meta.get("target_sleep_place_id")
    if not target_sleep_place_id:
        goal.status = GoalStatus.FAILED
        return

    # Move to chosen bunk if not there yet
    if agent.location_id != target_sleep_place_id:
        physical.is_sleeping = False
        _move_one_step_toward(world, agent, target_sleep_place_id, rng)
        return

    # At bunk: go / remain sleeping
    physical.is_sleeping = True

    # Sleep ticks decrement
    sleep_ticks_remaining = float(meta.get("sleep_ticks_remaining", 0.0))
    sleep_ticks_remaining -= 1.0
    meta["sleep_ticks_remaining"] = sleep_ticks_remaining

    # Sleep-related updates
    recover_sleep_pressure(physical)
    _apply_sleep_recovery_effects(world, agent)

    # Trigger memory consolidation occasionally or once per block
    # MVP: when we first enter sleep, or when block completes.
    if sleep_ticks_remaining <= 0.0:
        # Run consolidation once at the end of the block
        consolidate_sleep_for_agent(world, agent)
        physical.is_sleeping = False
        physical.last_sleep_tick = world.current_tick
        goal.status = GoalStatus.COMPLETED
```

The `consolidate_sleep_for_agent` function should be wired to the logic defined
in D-MEMORY-0300 (short-term → daily → belief updates, clearing buffers, etc.).


### 5.3 Sleep recovery effects

During sleep we want to gently improve stress and morale, and slightly affect
hunger/hydration.

Add a helper:

```python
SLEEP_STRESS_RECOVERY_RATE = 1.0 / 10_000.0
SLEEP_MORALE_RECOVERY_RATE = 1.0 / 10_000.0

SLEEP_HUNGER_INCREASE_PER_TICK = 1.0 / 120_000.0
SLEEP_HYDRATION_DECAY_PER_TICK = 1.0 / 120_000.0


def _apply_sleep_recovery_effects(world: WorldState, agent: AgentState) -> None:
    physical = agent.physical

    if not physical.is_sleeping:
        return

    # Stress down
    physical.stress_level -= SLEEP_STRESS_RECOVERY_RATE
    if physical.stress_level < 0.0:
        physical.stress_level = 0.0

    # Morale up
    physical.morale_level += SLEEP_MORALE_RECOVERY_RATE
    if physical.morale_level > 1.0:
        physical.morale_level = 1.0

    # Needs drift while sleeping
    physical.hunger_level += SLEEP_HUNGER_INCREASE_PER_TICK
    if physical.hunger_level < 0.0:
        physical.hunger_level = 0.0

    physical.hydration_level -= SLEEP_HYDRATION_DECAY_PER_TICK
    if physical.hydration_level < 0.0:
        physical.hydration_level = 0.0
```


## 6. Sleep place choice

### 6.1 Candidate places

In `_choose_sleep_place(world, agent, rng)`:

- consider facilities with `kind = "bunk_pod"`,
- optionally constrain to the agent’s `home` pod or nearby pods first.

Example:

```python
from typing import Optional, List

def _choose_sleep_place(
    world: WorldState,
    agent: AgentState,
    rng: random.Random,
) -> Optional[str]:
    candidates: List[str] = []

    for fid, facility in world.facilities.items():
        if getattr(facility, "kind", None) == "bunk_pod":
            candidates.append(fid)

    if not candidates:
        return None

    # If agent has a 'home', prefer it if present
    if agent.home and agent.home in candidates:
        if rng.random() < 0.8:
            return agent.home

    def utility(place_id: str) -> float:
        pb = agent.get_or_create_place_belief(place_id)
        # Distance term omitted for MVP
        return (
            0.5 * pb.safety_score +
            0.4 * pb.comfort_score -
            0.1 * pb.congestion_score
        )

    # epsilon-greedy selection
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
```


## 7. Interaction with other systems

### 7.1 Agent update order

For each tick, per agent:

1. Update hunger and hydration (existing).
2. Thirst/hunger body signals (existing).
3. Compute needs pressure & update stress/morale (D-RUNTIME-0219).
4. Accumulate or recover sleep pressure depending on `is_sleeping`.
5. Create goals: `GET_MEAL_TODAY`, `GET_WATER_TODAY`, `REST_TONIGHT`.
6. Select focus goal and route to handler (including `REST_TONIGHT`).

### 7.2 Performance during sleep

While sleeping, the agent should:

- not execute work detail goals,
- ideally have **no** work detail goals active.
- This is enforced by normal goal selection: when `REST_TONIGHT` is ACTIVE,
  it will win; when it completes, other goals can return.

If your decision loop does not allow for “being busy sleeping” yet, ensure
that `REST_TONIGHT` is scored highly when `is_sleeping == True` so it remains
the focus until completion.


## 8. Simplifications and future extensions

- No explicit world-level **day/night** yet; sleep is per-agent and based on
  `sleep_pressure` and thresholds.
- No explicit social penalties for sleeping in “wrong” pods.
- No modeling of insomnia, nightmares, or trauma-influenced sleep; these can
  later perturb `sleep_pressure` and recovery rates.
- Memory consolidation is treated as a single call at the end of each sleep
  block; in future we can stagger this across ticks or split into stages.

Once D-RUNTIME-0220 is implemented, the sim will have a coherent loop:

- **time awake + needs → sleep pressure → REST_TONIGHT → sleep → memory consolidation + recovery → stress/morale → performance**,

giving agents a basic circadian-like rhythm and tying memory consolidation into
the lived experience of the colonists.
