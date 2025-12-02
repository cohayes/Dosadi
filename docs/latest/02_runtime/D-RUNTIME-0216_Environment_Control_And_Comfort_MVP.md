---
title: Environment_Control_And_Comfort_MVP
doc_id: D-RUNTIME-0216
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-03
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0212   # Initial_Work_Detail_Taxonomy_MVP
  - D-RUNTIME-0213   # Work_Detail_Behaviors_MVP_Scout_And_Inventory
  - D-RUNTIME-0214   # Council_Metrics_And_Staffing_Response_MVP
  - D-RUNTIME-0215   # Food_Halls_Queues_And_Daily_Eating_MVP
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
  - D-MEMORY-0210    # Episode_Verbs_For_Initial_Work_Details_MVP
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
---

# Environment Control and Comfort (MVP) — D-RUNTIME-0216

## 1. Purpose & scope

This document specifies a **minimal “environment comfort” loop** for the
Founding Wakeup / early Golden Age phase.

Loop:

1. World has interior **environment nodes** (pods, corridors, facilities) with
   coarse comfort levels (temperature, humidity, air quality).
2. Agents experience these as **body signals** and `SCOUT_PLACE` / queue-like
   episodes that influence **comfort-related place beliefs**.
3. A simple **ENV_CONTROL** work detail tunes environment nodes toward a
   target comfort band, emitting `ENV_NODE_TUNED` episodes.
4. The proto-council reads aggregate **comfort metrics** and nudges staffing
   for ENV_CONTROL workers up or down.

Scope (MVP):

- Single scalar “comfort” per place (0–1), not a full thermodynamics model.
- Simple environment work detail acting on nodes.
- Basic belief updates for comfort/safety; no accidents yet.
- Optional council metric & staffing lever.

This is enough to:

- make some pods/corridors “pleasant” and others “stuffy / harsh”,
- see agents gradually prefer more comfortable paths and mess halls,
- give council a third lever beyond scouts and inventory/food.


## 2. Environment representation

### 2.1 Place environment state

Add or confirm a small environment struct per place/facility, e.g.:

```python
from dataclasses import dataclass

@dataclass
class PlaceEnvironmentState:
    place_id: str

    # 0.0 = hostile/uncomfortable, 1.0 = ideal interior comfort
    comfort: float = 0.5

    # Optional coarse physical attributes (can be extended later)
    temperature: float = 0.0  # deviation from ideal, -1 .. +1
    humidity: float = 0.0     # deviation from ideal, -1 .. +1
```

Attach to `WorldState` either as:

- a parallel mapping:

  ```python
  @dataclass
  class WorldState:
      ...
      place_environment: Dict[str, PlaceEnvironmentState] = field(default_factory=dict)
  ```

- or as fields on your existing `Place`/`Facility` objects; either is fine as
  long as handlers can read/write `comfort` per place.

Provide a helper:

```python
def get_or_create_place_env(world: WorldState, place_id: str) -> PlaceEnvironmentState:
    ...
```


### 2.2 Initial conditions

In the Founding Wakeup scenario, initialize environment for:

- pods,
- corridors,
- mess halls,
- assignment hall,
- stores.

Suggested defaults:

- pods, mess halls: `comfort ≈ 0.6–0.7`
- main corridors: `comfort ≈ 0.4–0.5`
- marginal or long corridors: `comfort ≈ 0.2–0.3`

This immediately induces some “better” and “worse” places without extra logic.


## 3. Bridging environment to beliefs and body signals

### 3.1 Body signal episodes

When updating physical state each tick, agents should emit **occasional body
signal episodes** based on the current place comfort:

- For places with **low comfort** (e.g. `comfort < 0.3`):
  - increase heat/cold stress if you track it,
  - occasionally emit a `BODY_SIGNAL_UNCOMFORTABLE` episode.

- For places with **high comfort** (e.g. `comfort > 0.7`):
  - reduce stress / improve morale slightly,
  - occasionally emit `BODY_SIGNAL_COMFORTABLE`.

We can use the existing body-signal episode pattern from D-MEMORY-0101.

Minimal pseudo-logic:

```python
env = get_or_create_place_env(world, agent.location_id)
if env.comfort < 0.3 and rng.random() < 0.02:
    ep = factory.create_body_signal_episode(
        owner_agent_id=agent.id,
        tick=world.current_tick,
        signal_type="ENV_UNCOMFORTABLE",  # or enum
        intensity=1.0 - env.comfort,
    )
    agent.record_episode(ep)
elif env.comfort > 0.7 and rng.random() < 0.02:
    ep = factory.create_body_signal_episode(
        owner_agent_id=agent.id,
        tick=world.current_tick,
        signal_type="ENV_COMFORTABLE",
        intensity=env.comfort,
    )
    agent.record_episode(ep)
```

These episodes should be mapped in belief consolidation to:

- adjust `PlaceBelief.comfort_score`,
- slightly adjust `safety_score` (if extreme discomfort implies risk).


### 3.2 SCOUT_PLACE / queue episodes and comfort

Update D-MEMORY-0210 / place belief consolidation so that:

- when a `SCOUT_PLACE` or `QUEUE_SERVED` / `QUEUE_DENIED` episode includes
  `details["comfort"]` (if present),
- those values also nudge `comfort_score` toward the reported level.

MVP: for now, body-signal episodes are the primary comfort driver; explicit
comfort readings in other episodes can be added later.


## 4. ENV_CONTROL work detail

### 4.1 New work detail type

Extend `WorkDetailType` with:

- `ENV_CONTROL`

Add to `WORK_DETAIL_CATALOG` (D-RUNTIME-0212) with:

- scope: environment nodes (pods, corridors, key facilities),
- typical duration, e.g. `typical_duration_ticks = 10_000`,
- description: “maintain interior comfort for a set of assigned places”.


### 4.2 Assignment

For MVP, **each ENV_CONTROL worker** will be responsible for:

- a small set of places (e.g. 3–10) near their home/ward.

Represent this as metadata on the worker’s work-detail goal:

```python
goal.metadata["env_control_places"] = ["loc:pod-1", "loc:corridor-3", ...]
```

On first activation, fill this list with nearby or randomly chosen places:

```python
def _assign_env_control_places(world, agent, goal, rng):
    if "env_control_places" not in goal.metadata:
        candidates = list(world.places.keys())  # or a filtered subset
        rng.shuffle(candidates)
        goal.metadata["env_control_places"] = candidates[:5]
```


### 4.3 Behavior per tick

Define handler `_handle_env_control(...)`, wired into the existing
`_handle_work_detail_goal` dispatch similar to SCOUT / INVENTORY / FOOD.

Per tick (simplified):

1. Ensure `ticks_remaining` via `_ensure_ticks_remaining(...)`, decrement, and
   COMPLETE goal when it hits zero (same pattern as other work details).

2. Ensure `env_control_places` list exists; if empty, no-op.

3. Choose a target place:

   - For MVP, iterate through `env_control_places` round-robin or randomly,
     or focus on the place with comfort farthest from target.

4. Move toward the target place location:

   - if not already there, take one step via `_move_one_step_toward`.

5. If at the target place:

   - read its `PlaceEnvironmentState`,
   - compute delta from **target comfort** (e.g. `target = 0.6`),
   - nudge comfort toward target by a small step:

     ```python
     adjustment = 0.02  # MVP step size
     if env.comfort < target:
         env.comfort = min(target, env.comfort + adjustment)
     elif env.comfort > target:
         env.comfort = max(target, env.comfort - adjustment)
     ```

   - emit an `ENV_NODE_TUNED` episode with details:
     - `place_id`,
     - `comfort_before`, `comfort_after`,
     - optional notes (`"heater_adjusted"`, `"vents_cleaned"`, etc.).


### 4.4 Episode creation

Extend `EpisodeVerb` / `EpisodeFactory` if needed:

- `EpisodeVerb.ENV_NODE_TUNED`

Factory helper (MVP):

```python
def create_env_node_tuned_episode(
    self,
    owner_agent_id: str,
    tick: int,
    place_id: str,
    comfort_before: float,
    comfort_after: float,
) -> Episode:
    ep = Episode(
        episode_id=self._next_episode_id(),
        owner_agent_id=owner_agent_id,
        tick=tick,
        location_id=place_id,
        channel=EpisodeChannel.DIRECT,
        target_type=EpisodeTargetType.PLACE,
        target_id=place_id,
        verb=EpisodeVerb.ENV_NODE_TUNED,
        summary_tag="env_node_tuned",
        goal_relation=EpisodeGoalRelation.SUPPORTS,
        goal_relevance=0.3,
        outcome=EpisodeOutcome.SUCCESS,
        emotion=EmotionSnapshot(valence=0.1, arousal=0.2, threat=0.0),
        importance=0.2,
        reliability=0.9,
        tags={"environment", "comfort"},
        details={
            "comfort_before": float(comfort_before),
            "comfort_after": float(comfort_after),
        },
    )
    return ep
```


## 5. Belief updates for comfort & safety

Extend the belief consolidation logic to react to:

- `ENV_NODE_TUNED`
- `BODY_SIGNAL_ENV_COMFORTABLE` / `BODY_SIGNAL_ENV_UNCOMFORTABLE`

Heuristic updates:

- For `ENV_NODE_TUNED`:
  - nudge `comfort_score` toward `comfort_after`,
  - small bump to `reliability_score` (place is “maintained”).

- For `BODY_SIGNAL_ENV_COMFORTABLE`:
  - increase `comfort_score`,
  - slight increase to `safety_score`.

- For `BODY_SIGNAL_ENV_UNCOMFORTABLE`:
  - decrease `comfort_score`,
  - if intensity high, small decrease to `safety_score`.


## 6. Council metrics extension (optional but recommended)

Extend `CouncilMetrics` (D-RUNTIME-0214) with:

```python
@dataclass
class CouncilMetrics:
    ...
    interior_comfort_index: float = 0.0
    interior_place_count: int = 0
```

Computation in `update_council_metrics_and_staffing`:

- Aggregate comfort scores from a council-view of place beliefs
  (or from `place_environment` directly, but beliefs are more consistent with
  the overall architecture).

Simple version:

```python
comfort_scores = []
for place_id, pb in iter_council_place_beliefs(world):
    if is_interior_place(world, place_id):  # corridors, pods, mess halls, etc.
        comfort_scores.append(pb.comfort_score)

if comfort_scores:
    metrics.interior_comfort_index = sum(comfort_scores) / len(comfort_scores)
    metrics.interior_place_count = len(comfort_scores)
else:
    metrics.interior_comfort_index = 0.5
    metrics.interior_place_count = 0
```

Add a new staffing lever in `_adjust_staffing_from_metrics`:

- Introduce config fields in `CouncilStaffingConfig`:

  ```python
  target_interior_comfort_low: float = 0.45
  target_interior_comfort_high: float = 0.70
  env_control_adjust_step: int = 1
  min_env_control: int = 0
  max_env_control: int = 32
  ```

- Then:

  ```python
  desired.setdefault(WorkDetailType.ENV_CONTROL, 0)

  ic = metrics.interior_comfort_index
  if ic < cfg.target_interior_comfort_low:
      desired[WorkDetailType.ENV_CONTROL] += cfg.env_control_adjust_step
  elif ic > cfg.target_interior_comfort_high:
      desired[WorkDetailType.ENV_CONTROL] -= cfg.env_control_adjust_step

  desired[WorkDetailType.ENV_CONTROL] = min(
      max(desired[WorkDetailType.ENV_CONTROL], cfg.min_env_control),
      cfg.max_env_control,
  )
  ```


## 7. Integration order & MVP boundaries

### 7.1 Wiring order

Implementation order (recommended):

1. Add `PlaceEnvironmentState` and `place_environment` mapping.
2. Initialize environment values for initial facilities in Founding Wakeup.
3. Add body-signal episodes for comfort (env → episodes).
4. Implement `ENV_CONTROL` work detail behavior (episodes → env).
5. Hook episodes into belief consolidation (episodes → beliefs).
6. Optionally extend council metrics & staffing (beliefs → council → staffing).

### 7.2 Simplifications

- Comfort is a single scalar (`comfort`), not a full physical process.
- No accidents / environmental hazards yet; discomfort only influences beliefs
  and mild body signals.
- ENV_CONTROL workers cannot fully “fix” extreme conditions; they only nudge
  toward a target band.
- No explicit energy or maintenance cost is modeled yet.

Once D-RUNTIME-0216 is implemented, the simulation will contain a third
loop:

- **place environment → body signals & episodes → beliefs → env-control staffing → environment**,

further enriching agent path choices, work detail allocation, and proto-council
pattern reading in the Golden Age phase.
