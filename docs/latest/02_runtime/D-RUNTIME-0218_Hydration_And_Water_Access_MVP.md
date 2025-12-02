---
title: Hydration_And_Water_Access_MVP
doc_id: D-RUNTIME-0218
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-03
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0215   # Food_Halls_Queues_And_Daily_Eating_MVP
  - D-RUNTIME-0217   # Well_Water_Handling_And_Distribution_MVP
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
  - D-MEMORY-0205    # Place_Belief_Updates_From_Queue_Episodes_MVP_v0
  - D-MEMORY-0210    # Episode_Verbs_For_Initial_Work_Details_MVP
  - D-MEMORY-0101    # Body_Signal_Episodes_Concept
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
---

# Hydration and Water Access (MVP) — D-RUNTIME-0218

## 1. Purpose & scope

This document specifies a **minimal “personal water” loop** that sits on top
of the world-level water handling in D-RUNTIME-0217.

Loop (MVP):

1. Agents have a **hydration state** that slowly degrades over time.
2. Hydration state and body signals create a **GET_WATER_TODAY** goal.
3. Agents choose a **water access point** (tap / fountain / mess hall) based
   on place beliefs and simple heuristics.
4. On arrival, they consume water from local **facility water stock**.
5. Episodes (`DRANK_WATER`, `WATER_DENIED`) update place beliefs and, in
   future, protocol logic.

Scope (MVP):

- Hydration is a single scalar per agent.
- Drinking draws water from facility-level stocks (depots or hall tanks).
- No explicit queues at water taps yet; we reuse queues for food only.
- No lethal dehydration yet; we only influence comfort / stress as a first pass.

This connects the **Well/Depot** logistics to individual bodies without
yet introducing Phase 1 scarcity or explicit rationing.


## 2. Hydration model

### 2.1 Extending PhysicalState

Extend `PhysicalState` (see D-AGENT-0022) with a hydration scalar:

```python
from dataclasses import dataclass

@dataclass
class PhysicalState:
    ...
    hydration_level: float = 1.0  # 1.0 = fully hydrated, 0.0 = severely dehydrated
    last_drink_tick: int = 0
```

### 2.2 Hydration dynamics

Per tick, for each **awake** agent:

- Decrease hydration at a slow rate:

  ```text
  hydration_level -= HYDRATION_DECAY_PER_TICK
  ```

- Clamp between 0.0 and 1.0:

  ```text
  hydration_level = max(0.0, min(1.0, hydration_level))
  ```

Suggested MVP constant:

```python
HYDRATION_DECAY_PER_TICK = 1.0 / 80_000.0  # ~one full unit every 80k ticks
```

(We’ll align 80k ticks with hours of waking time once the timebase is pinned.)

### 2.3 Body signal episodes for thirst

As hydration falls, occasionally emit body signals (D-MEMORY-0101):

- At `hydration_level < 0.7`: mild thirst (`"THIRSTY"`).
- At `hydration_level < 0.4`: strong thirst (`"VERY_THIRSTY"`).
- At `hydration_level < 0.2`: severe thirst (`"EXTREMELY_THIRSTY"`).

Example pseudo-logic in `update_agent_physical_state`:

```python
if physical.hydration_level < 0.2 and rng.random() < 0.05:
    signal_type = "EXTREMELY_THIRSTY"
    intensity = 1.0
elif physical.hydration_level < 0.4 and rng.random() < 0.03:
    signal_type = "VERY_THIRSTY"
    intensity = 0.7
elif physical.hydration_level < 0.7 and rng.random() < 0.02:
    signal_type = "THIRSTY"
    intensity = 0.4
else:
    signal_type = None

if signal_type is not None:
    ep = factory.create_body_signal_episode(
        owner_agent_id=agent.id,
        tick=world.current_tick,
        signal_type=signal_type,
        intensity=intensity,
    )
    agent.record_episode(ep)
```

These episodes will contribute to **importance** for short-term → daily buffer
promotion and, later, stress/health dynamics.


## 3. GET_WATER_TODAY goal

### 3.1 Goal type

Add a new goal type alongside `GET_MEAL_TODAY`:

- `GoalType.GET_WATER_TODAY`

### 3.2 Creation criteria

A `GET_WATER_TODAY` goal is created when hydration falls below a threshold
and no active/pending goal of that type exists:

```text
if hydration_level <= HYDRATION_GOAL_THRESHOLD
    and not has_active_or_pending_get_water_goal(agent):
    create_get_water_goal(world, agent)
```

Suggested MVP constants:

- `HYDRATION_GOAL_THRESHOLD = 0.6` (start seeking water before it gets bad).
- `GET_WATER_GOAL_TIMEOUT_TICKS = 80_000` (roughly one “day”).

Helper functions:

```python
def has_active_or_pending_get_water_goal(agent: AgentState) -> bool:
    ...

def create_get_water_goal(world: WorldState, agent: AgentState) -> Goal:
    ...
```

Both mirror the existing `GET_MEAL_TODAY` helpers.


### 3.3 Completion & failure

- Completion:
  - goal is **COMPLETED** when the agent successfully drinks water (`DRANK_WATER`
    episode) at a valid facility.
- Failure/abandonment:
  - if timeout exceeds `GET_WATER_GOAL_TIMEOUT_TICKS`,
  - or if the agent repeatedly experiences `WATER_DENIED` at multiple places
    (later we can convert that into stress and new meta-goals like “complain”).

When the goal is completed:

```text
hydration_level = min(1.0, hydration_level + DRINK_REPLENISH_AMOUNT)
last_drink_tick = current_tick
```

Suggested `DRINK_REPLENISH_AMOUNT = 0.7` (one “good drink”).


## 4. Water access points

### 4.1 Facility kinds

We need places where agents can consume water from **facility water stocks**
(see D-RUNTIME-0217). Two simple patterns:

1. **Dedicated taps / fountains** near depots:
   - `kind = "water_tap"`
   - linked to a nearby `water_depot` facility for stock.


2. **Mess halls with water access**:
   - reuse `kind = "mess_hall"`,
   - assume each mess hall has an internal water stock that is regularly filled
     from a depot (for MVP, we can treat mess halls as direct consumers of
     depot water).

For MVP, we will:

- define at least one `kind="water_tap"` facility,
- and optionally allow mess halls to act as water sources too.


### 4.2 Tap-to-depot mapping

Introduce a simple mapping from **tap** to **source depot**.

Option A (explicit mapping in scenario config):

```python
world.water_tap_sources: Dict[str, str] = {
    "loc:tap-1": "loc:depot-water-1",
}
```

Option B (heuristic):

- when a tap is first used, choose the **nearest** or first `water_depot` as
  its source and store in `world.water_tap_sources`.

For MVP, Option A (explicit mapping) is simpler and more transparent.


## 5. Agent behavior for GET_WATER_TODAY

### 5.1 Choosing a water source

When `GET_WATER_TODAY` is the focus goal, the agent should:

1. Enumerate candidate water sources:
   - all `facilities` with `kind in {"water_tap", "mess_hall"}`.

2. For each candidate `p`, consider:
   - `PlaceBelief.reliability_score`,
   - `PlaceBelief.fairness_score`,
   - `PlaceBelief.congestion_score`,
   - distance / travel effort (if available).

3. Compute a simple utility, similar to mess halls:

   ```text
   utility(p) =
       w_rel * reliability_score
     + w_fair * fairness_score
     - w_cong * congestion_score
     - w_dist * normalized_distance
   ```

4. Choose the place with maximal utility (with small exploration chance).

Store the chosen place in goal metadata:

```python
goal.metadata["target_water_place_id"] = chosen_place_id
```


### 5.2 Movement and drinking

Handler for `GET_WATER_TODAY` (similar to `_handle_get_meal_goal`):

1. If `target_water_place_id` is not set:
   - run the selection logic above.

2. If `agent.location_id != target_water_place_id`:
   - move one step toward the target (`_move_one_step_toward`).

3. If at the target:
   - attempt to **consume water** from the appropriate `FacilityState` stock.

#### 5.2.1 Consuming water from facility stock

Consumption rules:

- If target is a `water_tap`:
  - find its source depot:
    - `depot_id = world.water_tap_sources[target_id]`,
    - `depot = world.facilities[depot_id]`.
  - if `depot.water_stock >= DRINK_WATER_UNIT`:
    - decrease `depot.water_stock`,
    - replenish `hydration_level`,
    - emit `DRANK_WATER` episode,
    - mark goal as completed.
  - else:
    - emit `WATER_DENIED` episode,
    - maybe mark the goal as failed (or allow retry elsewhere).

- If target is a `mess_hall`:
  - For MVP, either:
    - treat it as having infinite water (Phase 0), or
    - also link to a depot and draw from `water_stock` as above.

Suggested constant:

```python
DRINK_WATER_UNIT: float = 1.0  # volume per personal drink, scaled to depot units
```


### 5.3 Episodes `DRANK_WATER` and `WATER_DENIED`

Define new `EpisodeVerb` variants:

- `DRANK_WATER`
- `WATER_DENIED`

Add `EpisodeFactory` helpers:

```python
def create_drank_water_episode(
    self,
    owner_agent_id: str,
    tick: int,
    place_id: str,
    amount: float,
    hydration_before: float,
    hydration_after: float,
) -> Episode:
    ...

def create_water_denied_episode(
    self,
    owner_agent_id: str,
    tick: int,
    place_id: str,
    reason: str,
) -> Episode:
    ...
```

MVP details:

- `DRANK_WATER`:
  - `target_type = PLACE`, `target_id = place_id`,
  - tags: `{"water", "drink"}`,
  - details: `{"amount": amount, "hydration_before": hydration_before, "hydration_after": hydration_after}`.

- `WATER_DENIED`:
  - `target_type = PLACE`, `target_id = place_id`,
  - tags: `{"water", "denied"}`,
  - details: `{"reason": reason}` (e.g. `"empty"`, `"restricted"`).


## 6. Belief updates for water access

Extend place belief consolidation to respond to:

- `DRANK_WATER`:
  - increase `reliability_score`,
  - small increase `comfort_score`,
  - if hydration was very low before, maybe a bigger bump.

- `WATER_DENIED`:
  - decrease `reliability_score`,
  - decrease `fairness_score`,
  - optional small decrease to `safety_score` if repeated.

Example heuristics:

```python
elif episode.verb == EpisodeVerb.DRANK_WATER:
    before = float(episode.details.get("hydration_before", 0.5))
    after = float(episode.details.get("hydration_after", 0.8))
    delta = max(0.0, after - before)
    pb.reliability_score = min(1.0, pb.reliability_score + 0.05 + 0.05 * delta)
    pb.comfort_score = min(1.0, pb.comfort_score + 0.03 * delta)

elif episode.verb == EpisodeVerb.WATER_DENIED:
    pb.reliability_score = max(0.0, pb.reliability_score - 0.08)
    pb.fairness_score = max(0.0, pb.fairness_score - 0.05)
```

Over time, this will cause agents to **prefer** water sources where they
seldom get denied, and gradually **abandon** frequently empty or unfair taps.


## 7. Integration & MVP boundaries

### 7.1 Where to plug in

- Hydration update & thirst body signals:
  - in the same per-tick physical update that already handles hunger.

- GET_WATER_TODAY goal creation:
  - just after hydration update, similar to `maybe_create_get_meal_goal`.

- Water source selection, movement, and consumption:
  - in the goal handler for `GET_WATER_TODAY`.

- Facility water stock interactions:
  - read/write `FacilityState.water_stock` and `water_capacity`,
  - respect depot capacity (but Phase 0 should rarely saturate).


### 7.2 Simplifications

- No explicit death, collapse, or long-term illness yet from poor hydration.
- No water access queues (we can introduce them later in Phase 1 when taps
  become contested).
- No social rules about who may drink where (later: “restricted” taps, guild
  lines, etc.).

Once D-RUNTIME-0218 is implemented, the simulation will have a complete,
though gentle, **personal water loop**:

- **hydration decay → thirst body signals → GET_WATER_TODAY → water sources → depot stocks → episodes → beliefs**,

closing the conceptual chain between Well capacity, logistics, and individual
colonist experience, ready to be hardened into real scarcity later.
