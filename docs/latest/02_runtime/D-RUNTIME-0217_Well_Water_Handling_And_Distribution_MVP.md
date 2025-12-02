---
title: Well_Water_Handling_And_Distribution_MVP
doc_id: D-RUNTIME-0217
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
  - D-RUNTIME-0216   # Environment_Control_And_Comfort_MVP
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
  - D-MEMORY-0210    # Episode_Verbs_For_Initial_Work_Details_MVP
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
---

# Well, Water Handling, and Distribution (MVP) — D-RUNTIME-0217

## 1. Purpose & scope

This document specifies a **minimal “water loop”** for the Founding Wakeup /
early Golden Age phase.

Loop (MVP):

1. The world has a **Well** with a large but finite **daily capacity**.
2. Interior **water depots** and facilities track simple water stocks.
3. **WATER_HANDLING** work details:
   - pump water at the Well,
   - move it to depots.
4. Episodes (`WELL_PUMPED`, `WATER_DELIVERED`) update **place beliefs** about
   water reliability and capacity.
5. The proto-council reads **water stock metrics** and nudges
   `WATER_HANDLING` staffing up or down.

Scope (MVP):

- Model **physical water** only at facility level (Well + depots).
- No personal thirst yet (that can be layered later using the same stocks).
- No barrel-level tracking; treat water in continuous units per facility.
- Phase 0: Well capacity is generous; we do not yet enforce scarcity.

This sets up the infrastructure and feedback channels that later phases will
stress (rationing, queues at taps, cartelization, etc.).


## 2. World-level water representation

### 2.1 Well state

Introduce a well object in world state, e.g. in `dosadi/world/water.py`:

```python
from dataclasses import dataclass

@dataclass
class WellState:
    well_id: str = "well:core"

    # Max amount pumpable per day in whatever unit we choose (e.g. cubic meters)
    daily_capacity: float = 10_000.0

    # How much has been pumped in the current day window
    pumped_today: float = 0.0

    # Optional: rolling average utilization, for metrics/debug
    utilization_rolling: float = 0.0
```

Attach to `WorldState`:

```python
from dataclasses import dataclass, field

@dataclass
class WorldState:
    ...
    well: WellState = field(default_factory=WellState)
```

Later, the daily window can be tied directly to your timebase (ticks → days);
for MVP we can reset `pumped_today` every fixed number of ticks.


### 2.2 Facility-level water stocks

Extend facility / place state to track **water stock** where appropriate.

If you have a `FacilityState` or similar, add:

```python
from dataclasses import dataclass

@dataclass
class FacilityState:
    ...
    water_stock: float = 0.0      # current volume
    water_capacity: float = 0.0   # max it can hold (0.0 means "not a depot")
```

Conventions:

- **Well head** facility:
  - `kind = "well_head"`
  - `water_capacity` may be left at 0 (we treat it as an infinite source up to
    `WellState.daily_capacity`).

- **Water depots**:
  - `kind = "water_depot"`
  - `water_capacity > 0`
  - `water_stock` between 0 and capacity.


### 2.3 Initial conditions for Founding Wakeup

In the Founding Wakeup scenario:

- Define a **Well head facility**, e.g. `loc:well-head-core`, linked conceptually
  to `WellState.well_id`.
- Define at least one **water depot**, e.g. `loc:depot-water-1`, with:
  - `water_capacity` high enough to accept significant stock (e.g. 5_000 units).
  - `water_stock` starting at some moderate level (e.g. 2_000) or 0.


## 3. WATER_HANDLING work detail

### 3.1 Work detail type & catalog

Extend `WorkDetailType` with:

- `WATER_HANDLING`

Add an entry in `WORK_DETAIL_CATALOG`:

- typical duration: e.g. `8_000–12_000` ticks,
- description: “pump water at the Well and deliver to depots”.


### 3.2 Behavior overview

Each WATER_HANDLING worker cycles through:

1. Move to Well head.
2. Pump a batch of water into a **virtual container**.
3. Choose a target depot that needs water (low `water_stock / capacity`).
4. Move to depot.
5. Deliver the batch into the depot’s `water_stock`.
6. Emit episodes:
   - `WELL_PUMPED` at the Well,
   - `WATER_DELIVERED` at the depot.

We do **not** track individual barrel items; we just move volumes between
global Well and depot stocks.


### 3.3 Handler pseudo-code

A WATER_HANDLING goal uses metadata:

- `carried_water` (float, amount agent is currently “carrying”),
- `phase` (`"TO_WELL"` or `"TO_DEPOT"`),
- `target_depot_id` (optional).

Simplified FSM:

- If `phase == "TO_WELL"`:
  - Move to Well head.
  - Once at Well, **pump**:
    - compute `batch = min(BATCH_SIZE, remaining_daily_capacity)`,
    - increase `agent_goal_metadata["carried_water"] += batch`,
    - increase `world.well.pumped_today += batch`,
    - emit `WELL_PUMPED` episode,
    - set `phase = "TO_DEPOT"` and pick target depot.

- If `phase == "TO_DEPOT"`:
  - Move toward `target_depot_id`.
  - Once at depot:
    - deposit `carried_water` into `facility.water_stock`, clamped to capacity,
    - emit `WATER_DELIVERED` episode,
    - reset `carried_water = 0`,
    - set `phase = "TO_WELL"` to repeat.

If `remaining_daily_capacity` is 0, the worker can idle, or perform a small
maintenance behavior.


### 3.4 Batch & capacity parameters

Suggested MVP constants:

```python
WATER_BATCH_SIZE: float = 100.0
WATER_DAILY_CAPACITY: float = 10_000.0  # WellState.daily_capacity default
WATER_DAY_TICKS: int = 144_000          # or reuse your "ticks per day"
```

Each pump operation:

```text
remaining = daily_capacity - pumped_today
batch = min(WATER_BATCH_SIZE, max(0.0, remaining))
```

Daily reset:

- Every `WATER_DAY_TICKS` ticks, reset `pumped_today = 0.0`.


## 4. Episodes and beliefs

### 4.1 Episode verbs

If not already present, add verbs to `EpisodeVerb`:

- `WELL_PUMPED`
- `WATER_DELIVERED`

### 4.2 EpisodeFactory helpers

Add to `EpisodeFactory`:

```python
def create_well_pumped_episode(
    self,
    owner_agent_id: str,
    tick: int,
    well_facility_id: str,
    batch_amount: float,
    pumped_today: float,
    daily_capacity: float,
) -> Episode:
    ...

def create_water_delivered_episode(
    self,
    owner_agent_id: str,
    tick: int,
    depot_id: str,
    amount: float,
    new_stock: float,
    capacity: float,
) -> Episode:
    ...
```

MVP details:

- `WELL_PUMPED`:
  - `target_type = PLACE`, `target_id = well_facility_id`,
  - tags: `{"water", "well"}`,
  - details: `{"amount": batch_amount, "pumped_today": pumped_today, "daily_capacity": daily_capacity}`.

- `WATER_DELIVERED`:
  - `target_type = PLACE`, `target_id = depot_id`,
  - tags: `{"water", "depot"}`,
  - details: `{"amount": amount, "new_stock": new_stock, "capacity": capacity}`.


### 4.3 Place belief updates

Extend place belief consolidation to react to:

- `WELL_PUMPED` episodes at the Well head:
  - small increase to perceived `reliability_score` for the Well place.

- `WATER_DELIVERED` episodes at depots:
  - increase `reliability_score` and `safety_score`,
  - optionally nudge `comfort_score` since reliable water yields comfort.

For example:

```python
elif episode.verb == EpisodeVerb.WELL_PUMPED:
    pb.reliability_score = min(1.0, pb.reliability_score + 0.02)

elif episode.verb == EpisodeVerb.WATER_DELIVERED:
    pb.reliability_score = min(1.0, pb.reliability_score + 0.03)
    pb.safety_score = min(1.0, pb.safety_score + 0.01)
```


## 5. Council metrics and staffing (water)

### 5.1 Water metrics

Extend `CouncilMetrics` with:

```python
@dataclass
class CouncilMetrics:
    ...
    water_depot_fill_index: float = 0.0
    water_depot_count: int = 0
```

Computation in `update_council_metrics_and_staffing`:

- Iterate over facilities with `kind == "water_depot"`.
- If `capacity > 0`, compute `fill_ratio = stock / capacity`.
- Average these into `water_depot_fill_index`.

Example:

```python
fill_ratios = []
for fid, facility in world.facilities.items():
    if getattr(facility, "kind", None) == "water_depot" and facility.water_capacity > 0:
        fill = facility.water_stock / facility.water_capacity
        fill_ratios.append(max(0.0, min(1.0, fill)))

if fill_ratios:
    metrics.water_depot_fill_index = sum(fill_ratios) / len(fill_ratios)
    metrics.water_depot_count = len(fill_ratios)
else:
    metrics.water_depot_fill_index = 1.0  # optimistic default
    metrics.water_depot_count = 0
```


### 5.2 Staffing response

Extend `CouncilStaffingConfig` with:

```python
@dataclass
class CouncilStaffingConfig:
    ...
    target_water_fill_low: float = 0.40
    target_water_fill_high: float = 0.80

    water_handling_adjust_step: int = 1
    min_water_handling: int = 0
    max_water_handling: int = 32
```

In `_adjust_staffing_from_metrics`:

```python
desired.setdefault(WorkDetailType.WATER_HANDLING, 0)

wf = metrics.water_depot_fill_index
if wf < cfg.target_water_fill_low:
    desired[WorkDetailType.WATER_HANDLING] += cfg.water_handling_adjust_step
elif wf > cfg.target_water_fill_high:
    desired[WorkDetailType.WATER_HANDLING] -= cfg.water_handling_adjust_step

desired[WorkDetailType.WATER_HANDLING] = max(
    cfg.min_water_handling,
    min(desired[WorkDetailType.WATER_HANDLING], cfg.max_water_handling),
)
```


## 6. Integration & MVP boundaries

### 6.1 Wiring

Implementation order (recommended):

1. Add `WellState` and facility `water_stock/capacity`.
2. Initialize Well head and at least one water depot in Founding Wakeup.
3. Add `WATER_HANDLING` work detail type and catalog entry.
4. Implement `_handle_water_handling` behavior and its simple FSM.
5. Add `WELL_PUMPED` / `WATER_DELIVERED` episode verbs + factory helpers.
6. Hook episodes into place belief consolidation.
7. Extend council metrics & staffing for water.

### 6.2 Simplifications

- No thirst or personal consumption yet; depots can be treated as “strategic stock”.
- No water loss/leakage; all movement is lossless for MVP.
- No rationing or queues; those come in later phases when scarcity appears.
- The Well cannot “run dry” yet; capacity only represents daily throughput.

Once D-RUNTIME-0217 is implemented, the simulation gains its first explicit
representation of the Well and water logistics, closing another loop:

- **Well capacity → handling work → depot stocks → beliefs → council staffing → handling capacity → depot stocks**,

ready to be stressed by Phase 1 “realization of limits” and Phase 2 scarcity.
