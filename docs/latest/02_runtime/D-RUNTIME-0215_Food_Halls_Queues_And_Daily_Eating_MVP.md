---
title: Food_Halls_Queues_And_Daily_Eating_MVP
doc_id: D-RUNTIME-0215
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-03
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0212   # Initial_Work_Detail_Taxonomy_MVP
  - D-RUNTIME-0213   # Work_Detail_Behaviors_MVP_Scout_And_Inventory
  - D-RUNTIME-0214   # Council_Metrics_And_Staffing_Response_MVP
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
  - D-MEMORY-0205    # Place_Belief_Updates_From_Queue_Episodes_MVP_v0
  - D-MEMORY-0210    # Episode_Verbs_For_Initial_Work_Details_MVP
  - D-MEMORY-0101    # Body_Signal_Episodes_Concept
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
---

# Food Halls, Queues, and Daily Eating (MVP) — D-RUNTIME-0215

## 1. Purpose & scope

This document specifies a **minimal but complete “eating loop”** for the
Founding Wakeup / early Golden Age phase.

Loop:

1. Agent **body state** produces hunger pressure.
2. Hunger creates / activates a **“get meal” goal**.
3. Agent chooses a **mess hall** based on place beliefs (reliability, congestion, fairness).
4. Agent travels there, joins a **queue**.
5. A **food steward work detail** serves or denies agents, emitting episodes:
   - `FOOD_SERVED`, `QUEUE_SERVED`, `QUEUE_DENIED`, `FOOD_SHORTAGE_EPISODE`.
6. Episodes update **place beliefs**, which in turn shape future hall choices
   and **council metrics** (via D-RUNTIME-0214).

Scope (MVP):

- Simple hunger model (no full nutrition yet).
- Simple “once or twice per waking day” eating behavior.
- Mess hall queues with FIFO ordering, single-server per hall.
- Single food-related work detail (Food Hall Steward).
- No hard enforcement on total calories vs survival yet; we keep it soft.


## 2. Hunger model and daily eating goal

### 2.1 Extending physical state

We assume `PhysicalState` already exists. Extend it (or confirm fields) with:

```python
@dataclass
class PhysicalState:
    ...
    hunger_level: float = 0.0  # 0.0 = fully satiated, 1.0+ = very hungry
    last_meal_tick: int = 0
```

### 2.2 Hunger dynamics (MVP)

Per tick, for each agent that is **awake**:

- Increase hunger at a slow fixed rate:

  ```text
  hunger_level += HUNGER_RATE_PER_TICK
  ```

  Suggested MVP constant:

  ```python
  HUNGER_RATE_PER_TICK = 1.0 / 50_000.0  # ~one full hunger unit per 50k ticks
  ```

  (We’ll later tie 50k ticks to a concrete time unit.)

- Clamp:

  ```text
  hunger_level = min(hunger_level, HUNGER_MAX)
  ```

  with `HUNGER_MAX ≈ 2.0` (beyond 1.0 is “very hungry” / “starving”).

### 2.3 “Get meal” goal

Define a new goal type and/or tag, e.g.:

- `GoalType.GET_MEAL_TODAY`

Trigger logic:

- When `hunger_level` crosses a threshold and no active/pending get-meal goal
  exists:

  ```text
  if hunger_level >= HUNGER_GOAL_THRESHOLD
      and not has_active_or_pending_get_meal_goal(agent):
      push new Goal(type=GET_MEAL_TODAY)
  ```

  Suggested `HUNGER_GOAL_THRESHOLD`:

  - `0.4` for “get a meal soon” (tunable).

Completion/failure:

- The goal is **COMPLETED** when the agent receives a `FOOD_SERVED` (and/or
  `QUEUE_SERVED` at a mess hall) episode with sufficient calories.
- The goal is **FAILED** or downgraded if:
  - it times out (e.g. more than `GET_MEAL_GOAL_TIMEOUT_TICKS` since creation),
  - or hunger crosses a higher threshold without success.
- For MVP we can simply **abandon** the goal after a long timeout and let a new
  goal be created later, carrying stress/health consequences in future work.

After a successful meal:

- Reduce hunger and track time:

  ```text
  hunger_level = max(0.0, hunger_level - MEAL_SATIATION_AMOUNT)
  last_meal_tick = current_tick
  ```

  Suggested `MEAL_SATIATION_AMOUNT ≈ 0.7` for a “good” meal.


## 3. Mess halls and queues

### 3.1 Mess hall facilities

Introduce a facility/location type for **mess halls**.

- e.g. facility kind/category `"mess_hall"`.

World-side:

- In the Founding Wakeup scenario, define at least **one** mess hall facility:
  - `loc:mess-hall-1`


### 3.2 Queue structure (per mess hall)

Each mess hall maintains a simple FIFO queue of agents awaiting service.

Suggested structure:

```python
@dataclass
class FacilityQueueState:
    facility_id: str
    queue: Deque[str] = field(default_factory=deque)  # agent_ids
```

Attach to world:

```python
@dataclass
class WorldState:
    ...
    facility_queues: Dict[str, FacilityQueueState] = field(default_factory=dict)
```

We will treat queues as **per facility**, keyed by `facility_id`.

### 3.3 Joining and leaving queues

Helpers:

```python
def join_facility_queue(world: WorldState, facility_id: str, agent_id: str) -> None:
    ...

def leave_facility_queue(world: WorldState, facility_id: str, agent_id: str) -> None:
    ...
```

Rules:

- An agent joins a queue when:
  - they reach the mess hall location **and**
  - they have an ACTIVE `GET_MEAL_TODAY` goal.
- An agent should not appear twice; `join` should check and avoid duplicates.
- An agent leaves the queue when:
  - served (`FOOD_SERVED` / `QUEUE_SERVED`),
  - denied (`QUEUE_DENIED`),
  - or if they abandon the goal / move away.


## 4. Agents choosing a mess hall

### 4.1 Candidate halls

When an agent decides to pursue `GET_MEAL_TODAY`:

- Discover a set of candidate mess halls (from world facilities), e.g.:
  - all facilities where `kind == "mess_hall"`.

### 4.2 Decision rule using place beliefs

For each candidate hall `h`:

- Look up or create `PlaceBelief` for `h`:

  - `reliability_score`
  - `comfort_score`
  - `congestion_score`
  - `fairness_score`

Additionally, we can estimate **current queue length** from `facility_queues`.

Construct a simple utility score:

```text
utility(h) =
    w_rel * reliability_score
  + w_comfort * comfort_score
  + w_fair  * fairness_score
  - w_cong  * congestion_score
  - w_q     * normalized_queue_length
```

Suggested MVP weights:

- `w_rel = 0.5`
- `w_comfort = 0.1`
- `w_fair = 0.2`
- `w_cong = 0.1`
- `w_q = 0.2`

Pick the hall with **maximum** utility, with some noise/exploration factor
(e.g. epsilon-greedy: with small probability choose a random hall).

Agents then:

1. Set a **sub-goal target** in the get-meal goal metadata:
   - `goal.metadata["target_mess_hall_id"] = chosen_hall_id`
2. Use existing movement/pathing logic to move toward that location.
3. When arriving, join that hall’s queue.


## 5. Food hall steward work detail

### 5.1 New work detail type

Extend `WorkDetailType` with e.g.:

- `FOOD_PROCESSING_DETAIL` or `MESS_HALL_STEWARD`

Add to the initial work detail catalog (D-RUNTIME-0212) with:

- scope: mess hall facilities,
- typical duration,
- job description: serving meals in FIFO order.

### 5.2 Behavior per tick

For each tick, within the work detail handler:

1. Identify which mess hall the steward is assigned to (via goal metadata or
   facility association).
2. Fetch its queue:

   ```python
   q = world.facility_queues.get(mess_hall_id)
   ```

3. If queue is empty: no-op or small idle behavior.

4. If queue is non-empty:

   - Pop the **next agent** id from `q.queue`.
   - Decide whether there is food capacity:
     - For MVP, assume infinite food and always serve (we can cap later).
   - If served:
     - emit `FOOD_SERVED` and `QUEUE_SERVED` episodes for the agent,
     - trigger hunger reduction + goal completion on that agent.
   - If not served (later extension when we model shortages):
     - emit `QUEUE_DENIED` and/or `FOOD_SHORTAGE_EPISODE` episodes.

### 5.3 Episode generation

Re-use `EpisodeFactory` helpers (from D-MEMORY-0210 implementation):

- `create_food_served_episode(...)`  → `FOOD_SERVED`
- `create_queue_served_episode(...)` → `QUEUE_SERVED`
- `create_queue_denied_episode(...)` → `QUEUE_DENIED`
- A small helper for `FOOD_SHORTAGE_EPISODE` can be added if missing.

The steward should record the **same** episodes as the consumer, or at least
their own perspective; MVP can focus on consumer episodes only.


## 6. Tying episodes back to beliefs and council

### 6.1 Place belief updates

D-MEMORY-0205 and D-MEMORY-0210 already define how queue and food verbs
should map to `PlaceBelief` updates.

Ensure the belief consolidation logic includes cases for:

- `FOOD_SERVED` (increase reliability, adjust congestion & comfort).
- `QUEUE_SERVED` (similar to any queue served).
- `QUEUE_DENIED` (reduce fairness / comfort, maybe increase perceived congestion).
- `FOOD_SHORTAGE_EPISODE` (reduce reliability and fairness).

These are triggered by **daily consolidation** / sleep cycles, not immediately.


### 6.2 Council metrics extension (optional but recommended)

Extend D-RUNTIME-0214 to add:

- `food_hall_reliability_index` in `CouncilMetrics`:

  ```python
  @dataclass
  class CouncilMetrics:
      ...
      food_hall_reliability_index: float = 0.0
      food_hall_count: int = 0
  ```

- Computation: average `reliability_score` across mess hall place beliefs.
- Optional new staffing lever:

  - `desired_work_details[FOOD_PROCESSING_DETAIL]`:
    - increase if `food_hall_reliability_index < target_food_reliability_low`,
    - decrease if above `target_food_reliability_high`.


## 7. Integration and MVP boundaries

### 7.1 Where to plug things in

- Hunger update:
  - inside the per-tick agent update / physiology step.
- Get-meal goal creation:
  - just after hunger update, or during goal selection if hunger is high.
- Mess hall selection and movement:
  - in the decision loop when the current focus goal is `GET_MEAL_TODAY`.
- Queue join/leave:
  - when agent enters/leaves the target mess hall location.
- Steward serving:
  - inside the work detail handler for `FOOD_PROCESSING_DETAIL`.

### 7.2 MVP simplifications

- No true nutritional accounting yet; hunger is a single scalar.
- No death from starvation yet; hunger may just cap at `HUNGER_MAX` and feed
  into future health/stress changes.
- Only one meal per “day” as a minimum viable behavior; we can add
  preferences (2 meals, snacks, etc.) later.
- Mess halls are always safe locations; we ignore fights, thefts, etc.

Once D-RUNTIME-0215 is implemented, the simulation will contain a second,
directly survival-linked loop:

- **body state → goal → hall selection → queue → steward → episodes → beliefs → council**,

providing rich data for later protocol changes and scarcity mechanics.
