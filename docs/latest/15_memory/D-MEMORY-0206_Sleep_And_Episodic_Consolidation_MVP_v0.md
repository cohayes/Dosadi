---
title: Sleep_And_Episodic_Consolidation_MVP
doc_id: D-MEMORY-0206
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-02
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-MEMORY-0004   # Memory_Tiers_and_Belief_Archetypes
  - D-MEMORY-0102   # Episode_Data_Structures_and_Buffers_v0
  - D-MEMORY-0203   # Episode_Scoring_and_Defaults_v0
  - D-MEMORY-0204   # Episode_Tag_Catalog_MVP_v0
  - D-MEMORY-0205   # Place_Belief_Updates_From_Queue_Episodes_MVP_v0
---

# 04_memory · Sleep and Episodic Consolidation MVP (D-MEMORY-0206)

## 1. Purpose & Scope

This document specifies the **minimum viable sleep & episodic consolidation
loop** used by agents in the wakeup and early Golden Age phases.

The goal is to move from:

- a raw stream of **Episode** objects in `EpisodeBuffers.short_term` and
  `EpisodeBuffers.daily`

to:

- a stable, long-lived set of **beliefs** (places now; people/factions later)
- with realistic forgetting, overload, and variation by agent tier/attributes.

Scope (MVP):

- Define additional agent state needed for sleep/wake and consolidation.
- Specify **cadences** for short-term pruning, daily promotion, and sleep
  consolidation using the global timebase (D-RUNTIME-0001).
- Define the mechanics of:
  - short-term maintenance (discard vs promote),
  - daily buffer overflow behavior,
  - sleep-triggered consolidation from episodes → beliefs.
- Keep behavior simple and parameterised; no hard-coded global “everyone sleeps
  at the same tick”.

Out of scope for this MVP:

- Detailed circadian differences by role (night shifts, multi-shift systems).
- Dreams / imaginative episodes.
- Tier-3 archival behavior (scribes, logs, telemetry documents).

Those can be layered on top of this base.

---

## 2. Timebase & Cadences

We assume the **Simulation Timebase** (D-RUNTIME-0001):

- `ticks_per_second ≈ 1.67`
- `ticks_per_minute = 100`
- `ticks_per_hour = 6,000`
- `ticks_per_day = 144,000` (24h).

Using this, we define **recommended cadences** as ranges, not constants. The
runtime will configure exact values via a `RuntimeConfig`/`MemoryConfig` object.

### 2.1 Cadence Types

- **Short-term maintenance cadence**:
  - Intent: prune very low-value short-term episodes and opportunistically
    promote interesting ones to the daily buffer.
  - Range: every **5–15 minutes** of wake time.
  - Suggested default: `short_term_maintenance_interval_ticks = 1,000`
    (≈10 minutes).

- **Daily promotion cadence**:
  - Intent: ensure medium-importance/wake-cycle episodes are in the `daily`
    buffer and ready for the next sleep consolidation.
  - Range: every **4 hours** of wake time.
  - Suggested default: `daily_promotion_interval_ticks = 24,000`.

- **Sleep cycle / consolidation cadence**:
  - Intent: perform the heavy “compress to beliefs” work once per **24h
    personal cycle**.
  - Suggested default per agent:
    - `wake_duration_ticks ≈ 96,000` (≈16h),
    - `sleep_duration_ticks ≈ 48,000` (≈8h),
    - Each agent has a personal **offset** so not everyone sleeps in lockstep.

Implementation details:

- Cadences are **per-agent logical clocks** derived from the global tick.
- Agents track their last maintenance/promotion/consolidation tick and compare
  to configured intervals.

---

## 3. Agent State Additions (Sleep & Memory Schedules)

Extend `AgentState` (D-AGENT-0020 / D-AGENT-0022) with minimal sleep/consolidation fields:

- `is_asleep: bool` (default `False`)
- `next_sleep_tick: int`
- `next_wake_tick: int`
- `last_short_term_maintenance_tick: int`
- `last_daily_promotion_tick: int`
- `last_consolidation_tick: int`

MVP semantics:

- On scenario initialization, each agent receives:
  - a personal `sleep_phase_offset` (e.g. uniform across `[0, ticks_per_day)`),
  - from that, compute `next_sleep_tick` and `next_wake_tick` for the first day.
- `is_asleep` toggles at those ticks, but **local protocols** may override or
  delay this later (not in MVP).
- The `last_*` ticks default to the current `tick` at spawn, avoiding
  retroactive maintenance.

These fields can be grouped in a dedicated `SleepCycleState` if desired, but
are conceptually part of core `AgentState`.

---

## 4. Short-Term Maintenance & Promotion (Wake-phase)

During **wake** (i.e. `is_asleep == False`), the runtime periodically calls:

- `maintain_short_term_memory(agent, tick, config)`
- `promote_daily_memory(agent, tick, config)`

The two functions can be implemented distinctly but may share scoring helpers.

### 4.1 Short-Term Maintenance

Called when:

- `tick - agent.last_short_term_maintenance_tick >= short_term_maintenance_interval_ticks`

Algorithm outline:

1. Update `agent.last_short_term_maintenance_tick = tick`.
2. For each episode `ep` in `episodes.short_term`:
   - Compute a **retention score** `R(ep)` from:
     - `ep.importance` (0–1),
     - `ep.goal_relation` (supports/thwarts vs irrelevant),
     - `ep.emotion.valence`/`arousal`,
     - `ep.channel` (DIRECT, OBSERVED, RUMOR, etc.).
   - If `R(ep)` < `short_term_retention_threshold` (configurable, e.g. 0.2):
     - mark this episode as **discardable**.
   - Else, keep it, and possibly mark as **promotion candidate** (see §4.2).
3. Remove discardable episodes from `short_term`.
   - Eviction order: prefer dropping the **lowest** `R(ep)` first if capacity
     is exceeded.

This is **not** the only place eviction happens (EpisodeBuffers already enforce
capacity), but adds semantic trimming.

### 4.2 Promotion to Daily Buffer

Promotion can occur:

- opportunistically during short-term maintenance, and/or
- in a separate “daily promotion” pass every 4h.

Promotion criteria (per episode):

- `ep.importance >= daily_promotion_importance_min` (e.g. ≥ 0.4), or
- `ep.goal_relation` in `{SUPPORTS, THWARTS}` and `ep.importance >= 0.2`, or
- `ep.emotion.arousal` or `ep.emotion.threat` above a threshold.

If an episode meets promotion criteria:

- call `episodes.promote_to_daily(ep)`,
- leave it in `short_term` until natural eviction or an optional explicit
  removal.

Daily buffer overflow behavior is defined in §5.

### 4.3 Daily Promotion Cadence

In addition to opportunistic promotion, every:

- `tick - agent.last_daily_promotion_tick >= daily_promotion_interval_ticks`

run `promote_daily_memory(agent, tick, config)` which:

1. Updates `last_daily_promotion_tick`.
2. Re-scans `short_term` for episodes that now qualify for `daily` based on:
   - time since event (older but still important episodes),
   - persistent goal relevance.
3. Moves or copies those episodes into `daily`.

This ensures that important episodes that were initially low-salience can still
be captured before sleep, if they remain relevant over hours.

---

## 5. Daily Buffer Overflow & Overstimulation

The `EpisodeBuffers.daily` buffer has a fixed `daily_capacity` (e.g. 100).

Overflow policy (MVP):

- When adding a new episode:
  - If `len(daily) < daily_capacity`, append.
  - Else:
    - Sort or scan by `ep.importance` (or `R(ep)` if available),
    - Drop the **lowest-importance** episode to make space for the new one.

Interpretation:

- Agents under heavy stimulation (crowded queues, crises) will naturally lose
  low-importance daily episodes as the buffer “fills up” — modeling an
  inability to retain all details.

This overflow behavior is already partially implemented in `EpisodeBuffers`;
this document clarifies that it is **intended**, not an implementation quirk.

---

## 6. Sleep Cycle & Consolidation

When `tick >= agent.next_sleep_tick` and `is_asleep == False`, the runtime:

1. Sets `agent.is_asleep = True`.
2. Schedules `agent.next_wake_tick = tick + sleep_duration_ticks`.
3. Calls `run_sleep_consolidation(agent, tick, config)` **once** near the
   beginning of the sleep window.

Subsequent ticks in the sleep window may apply only minor maintenance (e.g.
physical recovery), but the heavy episodic consolidation is a single pass per
cycle.

### 6.1 Consolidation Algorithm

`run_sleep_consolidation(agent, tick, config)`:

1. If `tick - agent.last_consolidation_tick < min_consolidation_interval_ticks`
   (e.g. one per 18–30h), early return.
2. Set `agent.last_consolidation_tick = tick`.
3. For each episode `ep` in `episodes.daily`:
   - Route it to relevant belief structures:
     - **PlaceBeliefs**:
       - Use `agent.get_or_create_place_belief(place_id)` and call
         `place_belief.update_from_episode(ep)` (D-MEMORY-0205).
     - **PersonBeliefs** (future):
       - If `ep.target_type == PERSON`, update that person’s belief record.
     - **FactionBeliefs** (future):
       - If `ep.target_type == FACTION`, update the faction’s belief record.
4. After processing all `daily` episodes:
   - Optionally apply a **global decay** to some beliefs (e.g. move scores
     slightly toward 0.0 to model forgetting when no new evidence exists).
   - Clear or heavily down-sample `episodes.daily`:
     - MVP: `episodes.daily.clear()`.
     - Optional: retain a few highest-importance daily episodes for “multi-night” consolidation.
5. Optionally trim `short_term` of very old entries (beyond a max age in
   ticks).

### 6.2 Wake Transition

When `tick >= agent.next_wake_tick` and `is_asleep == True`:

- Set `agent.is_asleep = False`.
- Schedule a new `next_sleep_tick = tick + wake_duration_ticks`.
- Reset short-term promotion and maintenance timers if desired, or allow them
  to continue from previous values.

No special memory logic is needed at wake time; the core work happened in `run_sleep_consolidation`.

---

## 7. Attribute & Tier Effects on Memory

MVP attributes influence **capacities** and **sensitivity**, not the basic
algorithm:

- **Tier**:
  - Tier-1:
    - larger `short_term_capacity` but smaller `daily_capacity`,
    - higher `alpha` (beliefs move more quickly / are more volatile).
  - Tier-2:
    - moderate capacities, medium `alpha`.
  - Tier-3:
    - larger `daily_capacity`, smaller `alpha` (beliefs move slowly).
- **INT** and **WIL**:
  - INT:
    - slightly higher `daily_capacity`,
    - lower `short_term_retention_threshold` (keeps more subtle episodes).
  - WIL:
    - slightly larger `daily_capacity`,
    - more resistance to global forgetting/decay during consolidation.
- **Trauma / stress** (future):
  - high trauma might reduce effective capacities or bias safety-related
    beliefs negative.

Concrete formulas and mappings can be implemented in a small helper, e.g.
`configure_agent_memory_capacities(agent)` in the runtime.

---

## 8. Runtime Integration

Add the following runtime-level helpers:

- `step_agent_sleep_wake(world, agent, tick, config)`
  - toggles `is_asleep` based on `next_sleep_tick` / `next_wake_tick`.
  - invokes `run_sleep_consolidation` when entering sleep.
- `step_agent_memory_maintenance(world, agent, tick, config)`
  - if awake: call `maintain_short_term_memory` and `promote_daily_memory`
    when due.
  - if asleep: no-op or minimal short-term trimming.

Integration into the main loop (conceptual):

```python
for tick in range(max_ticks):
    ...
    for agent in world.agents.values():
        step_agent_sleep_wake(world, agent, tick, memory_config)
        step_agent_memory_maintenance(world, agent, tick, memory_config)
    ...
```

Decision/movement logic should respect `is_asleep` (sleeping agents generally
do not move or engage in complex decisions, except for emergencies/protocols).

---

## 9. Future Extensions (Non-MVP)

- Different **shift patterns** by role and ward (D-RUNTIME-02xx Daily Rhythms).
- Dream-like integration of **hypothetical episodes** into beliefs.
- Tier-3 consolidation of **written logs** and **telemetry** into higher-level
  “city beliefs” used by protocols.
- Rich emotional effects of sleep quality on next-day decisions.

For now, D-MEMORY-0206 provides a basic, configurable pipeline that:

1. filters and promotes episodes during wake,
2. compresses daily episodes into long-lived beliefs during sleep,
3. respects per-agent cycles rather than forcing a single global day/night,
4. scales from early wakeup to a 500-year empire without rule changes.
