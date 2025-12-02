---
title: Work_Detail_Behaviors_MVP_Scout_And_Inventory
doc_id: D-RUNTIME-0213
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-02
depends_on:
  - D-RUNTIME-0212  # Initial_Work_Detail_Taxonomy_MVP
  - D-MEMORY-0210  # Episode_Verbs_For_Initial_Work_Details_MVP
  - D-MEMORY-0102  # Episode_Representation
  - D-AGENT-0022   # Agent_Core_State_Shapes
---

# Work Detail Behaviors (MVP) — Scout & Inventory — D-RUNTIME-0213

## 1. Purpose & scope

This document specifies **minimal per-tick behaviors** for two early work
details:

- `SCOUT_INTERIOR`
- `INVENTORY_STORES`

Goal: give them **simple, repeatable loops** that:

- move agents between relevant facilities/locations,
- emit the new episode verbs from D-MEMORY-0210,
- terminate or refresh goals reasonably,
- remain cheap enough for large runs.

This is an MVP: we do not yet implement full task graphs, hazard escalation,
or complex scheduling. We just want these details to:

1. Pull agents out of the assignment hall into meaningful work.
2. Produce SCOUT / CROWDED / CRATE / STOCK episodes that feed beliefs.
3. Finish or re-request work in a simple, understandable way.


## 2. Shared concepts

### 2.1 Work-detail goals

We assume `Goal` instances of type `WORK_DETAIL` with metadata:

- `metadata["work_detail_type"] = "SCOUT_INTERIOR"` or `"INVENTORY_STORES"`
- Optionally: `metadata["origin_facility_id"]` (assignment hall id).
- Optionally: `metadata["ticks_remaining"]` as a coarse duration budget.

### 2.2 World navigation primitives

We assume the runtime exposes basic pathing helpers, e.g.:

- `world.get_neighbors(location_id) -> List[location_ids]`
- `world.random_neighbor(location_id, rng)`
- or a minimal routing system between facilities.

MVP requirement: each work-detail handler only needs to pick **one step** per
tick toward or within its “work area”.


### 2.3 Episode production

We assume `EpisodeFactory` from D-MEMORY-0210 is available as:

- `factory = EpisodeFactory(world=world)`

and agents call:

- `agent.record_episode(ep)`

which already pushes into `EpisodeBuffers` and triggers optional immediate
belief updates.


## 3. SCOUT_INTERIOR behavior

### 3.1 Intuition

`SCOUT_INTERIOR` agents:

- roam **pods, corridors, and junctions**,
- periodically drop `SCOUT_PLACE` episodes,
- occasionally notice congestion and drop `CORRIDOR_CROWDING_OBSERVED`,
- run for a fixed duration, then mark their work-detail goal as completed and
  return to assignment hall (implicitly or as a follow-up goal).

They do not need full coverage guarantees in MVP: it’s okay if they wander
locally; over many agents & ticks this still produces useful place beliefs.


### 3.2 State in the goal

For an active SCOUT_INTERIOR goal `g` we use metadata keys:

- `g.metadata["ticks_remaining"]` (int)
- `g.metadata["last_scout_tick"]` (int, optional)

On first activation, if `ticks_remaining` is absent, we initialize it from the
work-detail config, e.g.:

- `ticks_remaining = WORK_DETAIL_CATALOG[SCOUT_INTERIOR].typical_duration_ticks`
  (or some smaller value like 5_000 for MVP).


### 3.3 Per-tick behavior outline

For each tick where an agent has SCOUT_INTERIOR as focused goal:

1. **Decrement duration**

   ```text
   g.metadata["ticks_remaining"] -= 1
   if ticks_remaining <= 0:
       mark goal COMPLETED and return
   ```

2. **Move one step** within interior graph

   - If agent is currently in an “interior” node (pod, interior corridor,
     junction), pick a neighbor (prefer corridors not recently visited).
   - If not in an interior node (e.g. stuck elsewhere), move toward nearest
     interior node or no-op.

3. **Occasional SCOUT_PLACE episode**

   - With low probability each tick (e.g. 0.1), or every N ticks,
     emit a `SCOUT_PLACE` episode with:
     - `place_id = agent.location_id`
     - `interior = True`
     - `hazard_level` based on primitive environment flags if available
       (else 0.0 for MVP).

4. **Occasional CORRIDOR_CROWDING_OBSERVED**

   - When the agent is in a corridor/junction with many co-located agents
     (or a queue present):
     - compute a rough density (agents / capacity),
     - emit `CORRIDOR_CROWDING_OBSERVED` with:
       - `estimated_density` = density clamped 0–1,
       - `estimated_wait_ticks` approximate (or 0 for MVP).

5. **Goal completion**

   - When `ticks_remaining <= 0`, set:
     - `goal.status = COMPLETED`
   - Optionally push a new goal like `RETURN_TO_ASSIGNMENT_HALL` so the loop
     repeats naturally through the existing assignment flow.


## 4. INVENTORY_STORES behavior

### 4.1 Intuition

`INVENTORY_STORES` agents:

- move between **stores / depots** and nearby storage locations,
- “open crates” and “stock resources”,
- produce `CRATE_OPENED` and `RESOURCE_STOCKED` episodes,
- run for a duration then complete their work-detail goal.

MVP doesn’t track exact physical crate movement; we just simulate basic
inventory work and its informational footprint.


### 4.2 State in the goal

For an active INVENTORY_STORES goal `g` we use metadata:

- `g.metadata["ticks_remaining"]`
- `g.metadata["target_store_id"]` (optional)

On first activation:

- If `target_store_id` absent, assign the agent to the **nearest** or a
  random store facility from world config.

### 4.3 Per-tick behavior outline

For each tick where INVENTORY_STORES is the focused goal:

1. **Decrement duration** (same as SCOUT_INTERIOR):

   ```text
   g.metadata["ticks_remaining"] -= 1
   if ticks_remaining <= 0:
       mark goal COMPLETED and return
   ```

2. **Move toward target store**

   - If `agent.location_id != target_store_id`:
     - take one step along a path toward the store (or teleport in MVP).
     - no episodes required this tick other than movement.

3. **At store: perform inventory actions**

   When `agent.location_id == target_store_id`:

   - With some probability or cadence (e.g. once every 20–50 ticks):
     1. Emit `CRATE_OPENED`:
        - `crate_id`: synthetic ID or from world if crates exist.
        - `resource_type`: one of a few coarse strings (`"food"`, `"water"`, `"suit_parts"`, `"materials"`).
        - `quantity`: small float.
     2. Emit `RESOURCE_STOCKED` for the store:
        - `resource_type` same as above,
        - `quantity` may match or differ from crate amount.

   - Both episodes are recorded on the agent; the **ledger system** can later
     choose to also write global entries based on these episodes.

4. **Optional: minor queue episodes**

   - If the store has a queue/line and the agent must wait:
     - you may emit `QUEUE_SERVED` episodes for the worker to experience
       the store’s own congestion/fairness.
   - For MVP this can be skipped or added later.


## 5. Integration in the decision loop

### 5.1 Handler dispatch

We assume the main decision loop already distinguishes WORK_DETAIL goals and
calls a handler like `_handle_work_detail_goal(...)`. Extend that handler:

```python
def _handle_work_detail_goal(world, agent, goal, work_type, rng):
    if work_type == WorkDetailType.SCOUT_INTERIOR:
        _handle_scout_interior(world, agent, goal, rng)
    elif work_type == WorkDetailType.INVENTORY_STORES:
        _handle_inventory_stores(world, agent, goal, rng)
    else:
        # other work types handled elsewhere or no-op for now
        pass
```

### 5.2 Handler signatures

We expect:

```python
def _handle_scout_interior(world: WorldState, agent: AgentState, goal: Goal, rng: random.Random) -> None:
    ...

def _handle_inventory_stores(world: WorldState, agent: AgentState, goal: Goal, rng: random.Random) -> None:
    ...
```

Each handler must be **idempotent per tick**: decide one “micro-step” and
return; the outer simulation loop handles ticks.


## 6. MVP simplifications & extensions

### 6.1 Simplifications (deliberate)

- Movement can be **very simple**:
  - random neighbor choices, or nearest-facility routing using a pre-baked graph.
- Duration is coarse:
  - e.g. 2_000–10_000 ticks, not tied to human-realistic hours yet.
- Crate/stock actions are **symbolic**:
  - we do not yet enforce consistency with a full resource ledger.

### 6.2 Near-term extensions

Once this MVP is in place and stable, future docs can:

- Add **success/failure** conditions to work-detail goals beyond “time elapsed”:
  - e.g. “survey at least N unique interior places” for SCOUT_INTERIOR.
- Introduce **fatigue and body signals** tied to work:
  - SCOUT_INTERIOR raising fatigue and producing hunger/thirst signals.
- Push `CRATE_OPENED` / `RESOURCE_STOCKED` into **actual inventories** and
  resource ledgers with conservation constraints.
- Add **risk events**:
  - minor accidents, dropped crates, near-miss episodes in crowded corridors.

For now, D-RUNTIME-0213’s job is to give SCOUT_INTERIOR and INVENTORY_STORES
simple, consistent behaviors that generate meaningful episodes and evolve
place beliefs over time.
