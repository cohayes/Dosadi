---
title: Needs_Stress_And_Performance_MVP
doc_id: D-RUNTIME-0219
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-03
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0215   # Food_Halls_Queues_And_Daily_Eating_MVP
  - D-RUNTIME-0218   # Hydration_And_Water_Access_MVP
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
  - D-MEMORY-0101    # Body_Signal_Episodes_Concept
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
---

# Needs, Stress, and Performance (MVP) — D-RUNTIME-0219

## 1. Purpose & scope

This document specifies a **minimal coupling** between:

- physiological needs (hunger, hydration),
- **stress & morale**,
- and agent **performance** (how effectively they execute work details).

Loop (MVP):

1. Hunger and hydration each contribute to a **needs pressure** signal.
2. Needs pressure nudges **stress** up and **morale** down over time.
3. Stress/morale modulate:
   - work detail **efficiency** (how much gets done per tick),
   - and occasional **body-signal episodes** (e.g. “weak from hunger”).

Scope (MVP):

- Simple scalar signals; no fine-grained health damage yet.
- We do not model death, collapse, or illness in this pass.
- Effects are gentle but noticeable over long runs.

This connects the **food + hydration** loops to behavior and performance,
without yet introducing lethal failure states.


## 2. Agent state: stress and morale

### 2.1 Physical & psychological state fields

Verify `PhysicalState` (D-AGENT-0022) already includes, or extend it with:

```python
from dataclasses import dataclass

@dataclass
class PhysicalState:
    ...
    stress_level: float = 0.0   # 0.0 = calm, 1.0 = max stressed
    morale_level: float = 0.7   # 0.0 = hopeless, 1.0 = very optimistic
```

We treat both as clamped to `[0.0, 1.0]`.


## 3. Needs pressure

### 3.1 Definition

At any tick, define **needs pressure** as a function of:

- `hunger_level` (0..2 from D-RUNTIME-0215),
- `hydration_level` (0..1 from D-RUNTIME-0218).

We want pressure near 0 when needs are satisfied, ~1 when very hungry and
dehydrated.

MVP heuristic:

```text
hunger_component = clamp((hunger_level - HUNGER_COMFORT_THRESHOLD) / (HUNGER_MAX - HUNGER_COMFORT_THRESHOLD), 0, 1)
hydration_component = clamp((HYDRATION_COMFORT_LEVEL - hydration_level) / HYDRATION_COMFORT_LEVEL, 0, 1)

needs_pressure = 0.6 * hunger_component + 0.4 * hydration_component
```

Constants (aligned with existing hunger/hydration):

```python
HUNGER_COMFORT_THRESHOLD = 0.3   # below this, hunger is mostly ignorable
HYDRATION_COMFORT_LEVEL = 0.9    # near 1.0 is ideal; below this starts to count
```

If you already have `HUNGER_MAX` from D-RUNTIME-0215, reuse it here.


### 3.2 Implementation helper

In a shared module (e.g. `dosadi/agents/physiology.py`), add:

```python
def compute_needs_pressure(physical: PhysicalState) -> float:
    hunger_component = 0.0
    if physical.hunger_level > HUNGER_COMFORT_THRESHOLD:
        denom = max(1e-6, HUNGER_MAX - HUNGER_COMFORT_THRESHOLD)
        hunger_component = (physical.hunger_level - HUNGER_COMFORT_THRESHOLD) / denom
        if hunger_component > 1.0:
            hunger_component = 1.0

    hydration_component = 0.0
    if physical.hydration_level < HYDRATION_COMFORT_LEVEL:
        hydration_component = (HYDRATION_COMFORT_LEVEL - physical.hydration_level) / HYDRATION_COMFORT_LEVEL
        if hydration_component > 1.0:
            hydration_component = 1.0

    return 0.6 * hunger_component + 0.4 * hydration_component
```


## 4. Stress and morale dynamics

### 4.1 Per-tick updates

After hunger/hydration updates, we update `stress_level` and `morale_level`
based on needs pressure.

Heuristic:

- **Base drift** toward moderate levels (e.g. stress → 0.2, morale → 0.6).
- Needs pressure pushes stress up and morale down.

MVP per-tick logic:

```python
BASE_STRESS_TARGET = 0.2
BASE_MORALE_TARGET = 0.6

STRESS_RELAX_RATE = 1.0 / 100_000.0
MORALE_RELAX_RATE = 1.0 / 100_000.0

STRESS_NEEDS_RATE = 1.0 / 20_000.0
MORALE_NEEDS_RATE = 1.0 / 20_000.0
```

Update snippet:

```python
def update_stress_and_morale(physical: PhysicalState, needs_pressure: float) -> None:
    # Relax toward baseline
    physical.stress_level += (BASE_STRESS_TARGET - physical.stress_level) * STRESS_RELAX_RATE
    physical.morale_level += (BASE_MORALE_TARGET - physical.morale_level) * MORALE_RELAX_RATE

    # Needs pressure pushes stress up, morale down
    physical.stress_level += needs_pressure * STRESS_NEEDS_RATE
    physical.morale_level -= needs_pressure * MORALE_NEEDS_RATE

    # Clamp
    physical.stress_level = min(1.0, max(0.0, physical.stress_level))
    physical.morale_level = min(1.0, max(0.0, physical.morale_level))
```

### 4.2 Integration into physical update

In `update_agent_physical_state`, after hunger/hydration and thirst/hunger
body signals:

```python
needs_pressure = compute_needs_pressure(agent.physical)
update_stress_and_morale(agent.physical, needs_pressure)
```


## 5. Body-signal episodes for low performance

To give agents a subjective feel of their state (and feed more episodes into
memory), we add occasional body signals when needs pressure is high.

Heuristic:

- When `needs_pressure > 0.6`, occasionally emit a **weakness** signal.
- When `needs_pressure > 0.9`, emit a stronger distress signal.

Pseudo-logic (after `update_stress_and_morale`):

```python
factory = EpisodeFactory(world=world)

if needs_pressure > 0.9 and rng.random() < 0.02:
    ep = factory.create_body_signal_episode(
        owner_agent_id=agent.id,
        tick=world.current_tick,
        signal_type="NEEDS_OVERWHELMING",
        intensity=needs_pressure,
    )
    agent.record_episode(ep)
elif needs_pressure > 0.6 and rng.random() < 0.02:
    ep = factory.create_body_signal_episode(
        owner_agent_id=agent.id,
        tick=world.current_tick,
        signal_type="WEAK_FROM_HUNGER_AND_THIRST",
        intensity=needs_pressure,
    )
    agent.record_episode(ep)
```

These can later drive more complex behaviors (e.g. abandoning work, seeking
help, complaining). For now they primarily enrich memory.


## 6. Performance modulation

### 6.1 Concept

We want stress and morale to affect **how much progress** an agent makes on
long-running tasks, without changing control flow drastically.

We already track `ticks_remaining` for work detail goals. We can treat
“effective” ticks per real tick as a function of stress/morale:

- High stress and low morale → **slower** progress.
- Low stress and decent morale → **normal** or slightly faster.


### 6.2 Performance multiplier

Define a helper function, e.g. in `dosadi/agents/physiology.py`:

```python
def compute_performance_multiplier(physical: PhysicalState) -> float:
    # 0..1 stress, 0..1 morale
    stress = physical.stress_level
    morale = physical.morale_level

    # Start from 1.0, apply penalties/boosts
    multiplier = 1.0

    # Stress penalty: up to -30% at max stress
    multiplier *= (1.0 - 0.3 * stress)

    # Morale bonus/penalty: +/- 10% relative to 0.5
    morale_delta = morale - 0.5
    multiplier *= (1.0 + 0.2 * morale_delta)

    # Clamp to reasonable range
    if multiplier < 0.4:
        multiplier = 0.4
    elif multiplier > 1.2:
        multiplier = 1.2

    return multiplier
```


### 6.3 Applying performance to work details

In each work detail handler where you decrement `ticks_remaining`, instead of:

```python
ticks_remaining -= 1
```

do:

```python
perf = compute_performance_multiplier(agent.physical)
ticks_remaining -= perf
```

Since `ticks_remaining` may now be a float, ensure:

- you initialize it as `float(...)`,
- you check `ticks_remaining <= 0` as before.

Example (SCOUT, INVENTORY, ENV_CONTROL, FOOD_PROCESSING, WATER_HANDLING):

```python
ticks_remaining = _ensure_ticks_remaining(
    goal,
    WorkDetailType.SCOUT_INTERIOR,
    default_fraction=0.3,
)
perf = compute_performance_multiplier(agent.physical)
ticks_remaining -= perf
goal.metadata["ticks_remaining"] = ticks_remaining
if ticks_remaining <= 0:
    goal.status = GoalStatus.COMPLETED
    return
```

For MVP, applying this to all long-running work details is enough to see
aggregate effects:

- well-fed, hydrated agents keep the colony running smoothly;
- agents who repeatedly miss meals/drinks gradually become slower, causing
  knock-on effects in water, food, and environment loops.


## 7. Integration order & boundaries

### 7.1 Implementation order

1. Add `stress_level` and `morale_level` to `PhysicalState` (if missing).
2. Implement `compute_needs_pressure`.
3. Implement `update_stress_and_morale` and call it from
   `update_agent_physical_state`.
4. Add extra body-signal episodes for high needs pressure (optional but nice).
5. Implement `compute_performance_multiplier`.
6. Apply performance multiplier to `ticks_remaining` in work detail handlers.


### 7.2 Simplifications

- We do not yet feed stress/morale back into **goal creation** or **social
  behavior**; they only affect performance and body signals.
- We do not yet have health damage or acute collapse from unfulfilled needs.
- There is no explicit “rest and recovery” behavior beyond the slow drift
  toward baseline; sleep will later accelerate recovery.

Once D-RUNTIME-0219 is implemented, the sim will support a gentle but
systematic link between **need satisfaction** and **productive capacity**,
making hunger and hydration feel materially important to the colony’s
function, even in Phase 0 Golden Age conditions.
