---
title: Council_Metrics_And_Staffing_Response_MVP
doc_id: D-RUNTIME-0214
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-02
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0212   # Initial_Work_Detail_Taxonomy_MVP
  - D-RUNTIME-0213   # Work_Detail_Behaviors_MVP_Scout_And_Inventory
  - D-LAW-0014       # Proto_Council_Protocol_Tuning_MVP
  - D-MEMORY-0205    # Place_Belief_Updates_From_Queue_Episodes_MVP_v0
  - D-MEMORY-0210    # Episode_Verbs_For_Initial_Work_Details_MVP
  - D-AGENT-0020     # Canonical_Agent_Model
---

# Council Metrics & Staffing Response (MVP) — D-RUNTIME-0214

## 1. Purpose & scope

This document defines a **minimal feedback loop** where the proto-council:

1. Reads **aggregate signals** about the world from place beliefs.
2. Maintains a tiny set of **council metrics**.
3. Adjusts **desired staffing for work details** in response.

The goal is to:

- close the loop from `episodes → beliefs → council decisions → work details`,
- keep the implementation **cheap and readable**,
- avoid premature complexity (no big optimization or control theory yet).

Scope (MVP):

- Phase: Founding Wakeup / early Golden Age.
- Metrics: corridor congestion and store reliability.
- Levers: desired headcount for:
  - `SCOUT_INTERIOR`
  - `INVENTORY_STORES`

Later documents can extend this to:

- environment control, food halls, water logistics,
- more sophisticated metrics (trends, variance, hotspots),
- and interaction with protocol authoring.


## 2. Data structures

### 2.1 Council metrics snapshot

Add a structure to hold **current metrics** and a last-updated tick.

Suggested shape:

```python
@dataclass
class CouncilMetrics:
    last_update_tick: int = 0

    # Mean scores (0–1)
    corridor_congestion_index: float = 0.0
    stores_reliability_index: float = 0.0

    # Simple counts (for debugging / dashboards)
    corridor_count: int = 0
    store_count: int = 0
```

Attach to `WorldState` (or equivalent):

```python
@dataclass
class WorldState:
    ...
    council_metrics: CouncilMetrics = field(default_factory=CouncilMetrics)
```

### 2.2 Council cadence

Define a **council update interval** in ticks, e.g.:

```python
COUNCIL_UPDATE_INTERVAL_TICKS = 5_000  # MVP; tweak later
```

The council metrics + staffing logic runs at most once per interval.


## 3. Reading aggregate signals from beliefs

### 3.1 Source of place beliefs

We assume there is either:

- a **world-level index** of place beliefs, or
- a way to iterate over agents’ `place_beliefs` and aggregate them.

MVP recommendation:

- Provide a helper that returns an **iterator of (place_id, belief)** representing
  the “current council view” of places.

For example:

```python
def iter_council_place_beliefs(world: WorldState) -> Iterable[Tuple[str, PlaceBelief]]:
    """
    Return the set of place beliefs council should treat as its input.

    MVP: if a world-level aggregated index exists, use that.
    Otherwise, aggregate across all agents by averaging their beliefs per place.
    """
```

Implementation detail is left to the code, but the important bit is that the
council update function works over a set of `(place_id, PlaceBelief)` pairs.


### 3.2 Classifying corridors vs stores

To compute metrics, we need to know whether a belief’s `place_id` refers to:

- an **interior corridor/junction**, or
- a **store / depot**.

MVP: use whatever facility/location metadata already exists, e.g.:

- `world.get_place_type(place_id) -> "corridor" | "junction" | "store" | ...`
- or `world.facilities[place_id].category` etc.

If no such helper exists yet, we can start with crude string prefixes or tags
and refactor later.

We only need boolean tests:

- `is_corridor(place_id: str) -> bool`
- `is_store(place_id: str) -> bool`


### 3.3 Metric definitions

Given a stream of `(place_id, PlaceBelief)`:

- **Corridor congestion index**

  ```text
  corridor_congestion_index =
      mean(pb.congestion_score for corridor-like places)
  ```

  If there are no corridor-like places yet, default to 0.0.

- **Stores reliability index**

  ```text
  stores_reliability_index =
      mean(pb.reliability_score for store-like places)
  ```

  If there are no store-like places yet, default to 1.0 (optimistic prior).


## 4. Staffing response rules

### 4.1 Desired staffing fields (existing)

From D-RUNTIME-0212, `WorldState` already includes:

```python
desired_work_details: Dict[WorkDetailType, int]
active_work_details: Dict[WorkDetailType, int]
```

We now define how the council **nudges** `desired_work_details` for:

- `WorkDetailType.SCOUT_INTERIOR`
- `WorkDetailType.INVENTORY_STORES`


### 4.2 Parameters

Introduce a small config structure or constants:

```python
@dataclass
class CouncilStaffingConfig:
    # Target ranges for metrics
    target_corridor_congestion_low: float = 0.30
    target_corridor_congestion_high: float = 0.60

    target_store_reliability_low: float = 0.40
    target_store_reliability_high: float = 0.75

    # Step sizes for changing desired staffing
    scout_adjust_step: int = 1
    inventory_adjust_step: int = 1

    # Min/max caps (safety rails)
    min_scouts: int = 0
    max_scouts: int = 32

    min_inventory: int = 0
    max_inventory: int = 32
```

Attach to `WorldState`:

```python
@dataclass
class WorldState:
    ...
    council_staffing_config: CouncilStaffingConfig = field(default_factory=CouncilStaffingConfig)
```


### 4.3 Response logic

At each council update tick, after computing metrics:

```text
if corridor_congestion_index > target_corridor_congestion_high:
    desired_SCOUT_INTERIOR += scout_adjust_step

elif corridor_congestion_index < target_corridor_congestion_low:
    desired_SCOUT_INTERIOR -= scout_adjust_step
```

Similarly for inventory:

```text
if stores_reliability_index < target_store_reliability_low:
    desired_INVENTORY_STORES += inventory_adjust_step

elif stores_reliability_index > target_store_reliability_high:
    desired_INVENTORY_STORES -= inventory_adjust_step
```

After adjustment, clamp to `[min, max]`.


### 4.4 Notes

- This is deliberately **one-dimensional and local**:
  - Each metric affects only one work detail.
- The same metric can eventually drive **protocol tweaks** (D-LAW-0014),
  but for MVP we only change staffing.

This is enough to:

- increase scouts when corridors seem jammed,
- increase inventory workers when stores feel flaky,
- and later decrease them when conditions drift back into a “comfortable band”.


## 5. Council update function & integration

### 5.1 Council update function

Define a function, e.g. in a new module `council_metrics.py` under runtime:

```python
def update_council_metrics_and_staffing(world: WorldState) -> None:
    """
    Periodically recompute council metrics from place beliefs and adjust
    desired staffing for key work details.
    """
```

Pseudo-steps:

1. **Cadence check**

   ```python
   metrics = world.council_metrics
   if world.current_tick - metrics.last_update_tick < COUNCIL_UPDATE_INTERVAL_TICKS:
       return
   metrics.last_update_tick = world.current_tick
   ```

2. **Aggregate place beliefs**

   ```python
   corridor_scores = []
   store_scores = []

   for place_id, pb in iter_council_place_beliefs(world):
       if is_corridor(place_id):
           corridor_scores.append(pb.congestion_score)
       if is_store(place_id):
           store_scores.append(pb.reliability_score)
   ```

3. **Compute metrics** (with defaults):

   ```python
   if corridor_scores:
       metrics.corridor_congestion_index = sum(corridor_scores) / len(corridor_scores)
       metrics.corridor_count = len(corridor_scores)
   else:
       metrics.corridor_congestion_index = 0.0
       metrics.corridor_count = 0

   if store_scores:
       metrics.stores_reliability_index = sum(store_scores) / len(store_scores)
       metrics.store_count = len(store_scores)
   else:
       metrics.stores_reliability_index = 1.0
       metrics.store_count = 0
   ```

4. **Adjust staffing**

   ```python
   cfg = world.council_staffing_config
   desired = world.desired_work_details

   # Ensure keys exist
   desired.setdefault(WorkDetailType.SCOUT_INTERIOR, 0)
   desired.setdefault(WorkDetailType.INVENTORY_STORES, 0)

   # Corridor → scouts
   cc = metrics.corridor_congestion_index
   if cc > cfg.target_corridor_congestion_high:
       desired[WorkDetailType.SCOUT_INTERIOR] += cfg.scout_adjust_step
   elif cc < cfg.target_corridor_congestion_low:
       desired[WorkDetailType.SCOUT_INTERIOR] -= cfg.scout_adjust_step

   # Stores → inventory workers
   sr = metrics.stores_reliability_index
   if sr < cfg.target_store_reliability_low:
       desired[WorkDetailType.INVENTORY_STORES] += cfg.inventory_adjust_step
   elif sr > cfg.target_store_reliability_high:
       desired[WorkDetailType.INVENTORY_STORES] -= cfg.inventory_adjust_step

   # Clamp
   desired[WorkDetailType.SCOUT_INTERIOR] = min(
       max(desired[WorkDetailType.SCOUT_INTERIOR], cfg.min_scouts),
       cfg.max_scouts,
   )
   desired[WorkDetailType.INVENTORY_STORES] = min(
       max(desired[WorkDetailType.INVENTORY_STORES], cfg.min_inventory),
       cfg.max_inventory,
   )
   ```


### 5.2 Integration into the main loop

In the main simulation step (from D-RUNTIME-0200), after agents have:

- taken actions,
- recorded episodes,
- and (if applicable) after belief consolidation,

call:

```python
from dosadi.runtime.council_metrics import update_council_metrics_and_staffing

def step_world_once(world: WorldState, rng: random.Random) -> None:
    ...
    # agents act, episodes recorded, beliefs updated
    ...
    update_council_metrics_and_staffing(world)
```

The exact ordering can be tuned later; for MVP, end-of-tick is fine.


## 6. Debugging & telemetry

To make this loop inspectable:

- Log or expose via admin dashboard:
  - `world.council_metrics.corridor_congestion_index`
  - `world.council_metrics.stores_reliability_index`
  - `world.desired_work_details[SCOUT_INTERIOR]`
  - `world.desired_work_details[INVENTORY_STORES]`

Even a crude text table over time will help verify that:

- congestion spikes lead to increased scouts,
- store reliability dips lead to more inventory workers,
- and that the values stay within the min/max rails.

Once D-RUNTIME-0214 is implemented, the simulation
achieves a first, fully-closed **Council ⇄ Work Detail ⇄ Beliefs** loop in
the Golden Age phase.
