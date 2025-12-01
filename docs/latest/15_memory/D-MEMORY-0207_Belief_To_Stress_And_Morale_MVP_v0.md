---
title: Belief_To_Stress_And_Morale_MVP
doc_id: D-MEMORY-0207
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-02
depends_on:
  - D-AGENT-0020   # Canonical_Agent_Model
  - D-AGENT-0022   # Agent_Core_State_Shapes
  - D-MEMORY-0004  # Memory_Tiers_and_Belief_Archetypes
  - D-MEMORY-0102  # Episode_Data_Structures_and_Buffers_v0
  - D-MEMORY-0205  # Place_Belief_Updates_From_Queue_Episodes_MVP_v0
  - D-MEMORY-0206  # Sleep_And_Episodic_Consolidation_MVP_v0
---

# 04_memory · Belief → Stress and Morale MVP (D-MEMORY-0207)

## 1. Purpose & Scope

This document specifies how **place beliefs** (especially those formed from
queue episodes) feed back into an agent’s **stress** and **morale** over time.

The goal is a light-weight feedback loop:

> episodes → beliefs → slow shifts in internal state → future decisions

without introducing full-blown rebellion or loyalty systems yet.

Scope (MVP):

- Define the agent-level fields for stress and morale.
- Define how place-level beliefs are sampled (per-sleep or per-day).
- Provide simple, sign-correct rules for how fairness, efficiency, safety,
  congestion, and reliability beliefs nudge stress and morale.
- Keep changes small and incremental; this is the simmer layer, not the
  explosion layer.

Out of scope for MVP:

- Explicit unrest/rebellion triggers.
- Factional recruitment or organized resistance.
- Long-term pathology (burnout, trauma trajectories).

Those will build on the same variables later.

---

## 2. Agent State: Stress & Morale Fields

We extend the core `AgentState` (D-AGENT-0020 / D-AGENT-0022) with:

- `stress: float`
  - A short-to-medium horizon “load” indicator.
  - Range: `[0.0, 1.0]`
    - `0.0` = fully relaxed,
    - `0.3–0.6` = normal tension for Dosadi,
    - `> 0.7` = consistently high strain.
- `morale: float`
  - A medium-to-long horizon “how worth it is life here?” indicator.
  - Range: `[0.0, 1.0]`
    - `0.0` = utterly demoralised,
    - `0.5` = neutral,
    - `1.0` = highly motivated / hopeful.

MVP initialisation during wakeup:

- `stress ≈ 0.3` (mild tension is default, not zero).
- `morale ≈ 0.6` (moderately optimistic at the founding).

Over time:

- **stress** responds faster to recent experiences.
- **morale** responds more slowly to accumulated beliefs.

Implementation suggestion (core dataclass additions):

```python
@dataclass
class PhysicalState:
    ...
    stress: float = 0.3
    morale: float = 0.6
```

or equivalently as top-level fields on `AgentState` if preferred.

---

## 3. When Beliefs Influence Stress & Morale

We anchor the belief → body link to **sleep consolidation** (D-MEMORY-0206)
rather than every tick. This keeps updates:

- infrequent (once per sleep cycle),
- smoothed over many episodes,
- easier to reason about.

During `run_sleep_consolidation(agent, tick, memory_config)` we add:

- a **belief sampling step** that reads relevant `PlaceBelief` entries,
- a **drift step** that nudges `stress` and `morale` accordingly.

Optional: intermediate “midday adjustment” passes (e.g. every 4 hours) can be
added later if needed, but MVP uses the sleep cycle only.

---

## 4. Which Beliefs Matter (MVP)

We focus on beliefs about **core service locations** during wakeup:

- Suit depot front: `queue:suit-issue:front` / `fac:suit-issue-1`
- Assignment hall front: `queue:assignment:front` / `fac:assign-hall-1`

For each of these, there may be one or more `PlaceBelief` entries per agent.

Belief dimensions, as defined in D-MEMORY-0205:

- `fairness_score` ∈ [-1, +1]
- `efficiency_score` ∈ [-1, +1]
- `safety_score` ∈ [-1, +1]
- `congestion_score` ∈ [-1, +1]
- `reliability_score` ∈ [-1, +1]

For MVP, we combine them into two composite “pressure” values:

1. **Stress pressure** (SP):

   - Strong contribution from:
     - low safety (`safety_score < 0`),
     - high congestion (`congestion_score > 0`),
     - low reliability (`reliability_score < 0`).
   - Mild contribution from perceived unfairness.

2. **Morale pressure** (MP):

   - Strong contribution from:
     - low fairness (`fairness_score < 0`),
     - low reliability (`reliability_score < 0`).
   - Mild contribution from efficiency (chronic slowness erodes morale).

We deliberately treat **stress** as more “immediate/physiological” and
**morale** as more “meaning-making/long-term expectation.”

---

## 5. Per-Place Contribution Formulas

For each relevant `PlaceBelief` `pb`, we compute **normalised scores**:

```text
fair = pb.fairness_score        # in [-1, +1]
eff  = pb.efficiency_score
safe = pb.safety_score
cong = pb.congestion_score
rel  = pb.reliability_score
```

We then map these to **stress pressure** and **morale pressure** contributions
for that place, on a conceptual [−1, +1] scale:

### 5.1 Stress Pressure per Place (SP_place)

Definition:

```text
# Negatives increase stress, positives reduce stress

SP_place = (
    # Safety: unsafe place (+stress when safe<0)
    -0.6 * (-safe)           # if safe = -1 → +0.6

    # Congestion: crowding and queue chaos (+stress when cong>0)
    +0.4 * cong              # if cong = +1 → +0.4

    # Reliability: unreliable services (+stress when rel<0)
    -0.4 * (-rel)            # if rel = -1 → +0.4

    # Fairness: unfair treatment (+stress, but modest)
    -0.2 * (-fair)           # if fair = -1 → +0.2
)
```

Interpretation:

- Highly unsafe, congested, unreliable, unfair places push SP_place toward
  +1.0 (stress-increasing).
- Safe, uncongested, reliable, fair places push SP_place toward negative
  values (stress-relieving).

### 5.2 Morale Pressure per Place (MP_place)

Definition:

```text
# Positives increase morale, negatives reduce morale

MP_place = (
    # Fairness: fair treatment supports morale
    +0.6 * fair              # if fair = +1 → +0.6

    # Reliability: being able to actually get things done
    +0.5 * rel               # if rel = +1 → +0.5

    # Efficiency: slow / jammed systems erode morale over time
    +0.3 * eff               # eff < 0 → negative contribution
)
```

Interpretation:

- Repeatedly fair & reliable service supports morale.
- Chronic unfairness and unreliability will push MP_place negative.
- Mild inefficiency alone is tolerable; severe inefficiency across key
  services erodes morale.

These coefficients can be tuned later; they are intentionally modest in
magnitude.

---

## 6. Aggregating Across Places

An agent may hold beliefs about multiple relevant places. We aggregate
per-place pressures into a **net pressure**.

Let `P` be the set of “core service places” for wakeup:

- `queue:suit-issue:front` (or `fac:suit-issue-1`),
- `queue:assignment:front` (or `fac:assign-hall-1`).

For each `place_id` in `P` where the agent has a `PlaceBelief` `pb`:

- compute `SP_place(pb)` and `MP_place(pb)` as defined above.

Then define:

```text
SP_net = average of SP_place over all pb in P that exist
MP_net = average of MP_place over all pb in P that exist
```

If the agent has no relevant `PlaceBelief` entries (e.g. has never queued
anywhere yet), then:

- `SP_net = 0.0`
- `MP_net = 0.0`

No adjustment happens that sleep cycle.

We deliberately weight all relevant places equally in MVP; later, usage
frequency or recency could weight them differently.

---

## 7. Translating Net Pressures to Stress & Morale Drifts

We treat `SP_net` and `MP_net` as **inputs** for a small, per-sleep adjustment
to `stress` and `morale` via an EMA-like rule.

### 7.1 Stress Update

Let `stress ∈ [0, 1]` and `SP_net ∈ [-1, +1]`.

We define a **stress drift**:

```text
delta_stress = stress_step_scale * SP_net
```

with a small `stress_step_scale`, e.g.:

- `stress_step_scale = 0.05`

Then:

```text
stress_new = clamp01(stress + delta_stress)
```

Where `clamp01` ensures `0.0 ≤ stress_new ≤ 1.0`.

Interpretation:

- `SP_net = +1` → +0.05 stress per sleep cycle (slow but cumulative).
- `SP_net = -1` → −0.05 stress per cycle (recovery if experiences are good).
- In typical ranges (e.g. `SP_net` near ±0.3–0.5), changes per day are small,
  building a simmer rather than spikes.

### 7.2 Morale Update

Let `morale ∈ [0, 1]` and `MP_net ∈ [-1, +1]`.

Similarly:

```text
delta_morale = morale_step_scale * MP_net
```

With, e.g.:

- `morale_step_scale = 0.03`

Then:

```text
morale_new = clamp01(morale + delta_morale)
```

Interpretation:

- `MP_net = +1` → +0.03 morale per sleep cycle.
- `MP_net = -1` → −0.03 morale per cycle.

Morale moves more slowly than stress, consistent with “meaning-making”
taking longer to change than moment-to-moment tension.

### 7.3 Attribute & Tier Modifiers

MVP can include simple per-tier scalars:

- Tier-1:
  - `effective_stress_step_scale = stress_step_scale * 1.2`
  - `effective_morale_step_scale = morale_step_scale * 1.2`
  - (more reactive)
- Tier-2:
  - use baseline scales.
- Tier-3:
  - `effective_stress_step_scale = stress_step_scale * 0.8`
  - `effective_morale_step_scale = morale_step_scale * 0.8`
  - (more buffered / stable)

Optional extension: WIL/INT can slightly alter the step scales but is not
required in MVP.

---

## 8. Runtime Integration

We extend `run_sleep_consolidation(agent, tick, config)`
(D-MEMORY-0206) with a final step:

1. Consolidate daily episodes into beliefs (as already implemented).
2. Compute **net pressures** `SP_net`, `MP_net` based on current
   `PlaceBelief` values (no new episodes required in this step).
3. Apply stress/morale drifts using per-tier (and later per-attribute) scales.

Conceptual pseudocode at the end of `run_sleep_consolidation`:

```python
def _apply_belief_driven_stress_and_morale(agent: AgentState) -> None:
    # Collect relevant place beliefs
    places_of_interest = [
        "queue:suit-issue:front",
        "queue:assignment:front",
        # or facility ids if that's what we store
        "fac:suit-issue-1",
        "fac:assign-hall-1",
    ]

    sp_list: list[float] = []
    mp_list: list[float] = []

    for place_id in places_of_interest:
        pb = agent.place_beliefs.get(place_id)
        if pb is None:
            continue

        fair = pb.fairness_score
        eff = pb.efficiency_score
        safe = pb.safety_score
        cong = pb.congestion_score
        rel = pb.reliability_score

        sp_place = (
            -0.6 * (-safe) +
             0.4 * cong +
            -0.4 * (-rel) +
            -0.2 * (-fair)
        )
        mp_place = (
             0.6 * fair +
             0.5 * rel +
             0.3 * eff
        )

        sp_list.append(sp_place)
        mp_list.append(mp_place)

    if not sp_list and not mp_list:
        return

    SP_net = sum(sp_list) / len(sp_list) if sp_list else 0.0
    MP_net = sum(mp_list) / len(mp_list) if mp_list else 0.0

    # Base step sizes
    stress_step_scale = 0.05
    morale_step_scale = 0.03

    # Simple tier modulation
    tier = agent.tier
    if tier == 1:
        stress_step_scale *= 1.2
        morale_step_scale *= 1.2
    elif tier == 3:
        stress_step_scale *= 0.8
        morale_step_scale *= 0.8

    agent.physical.stress = clamp01(agent.physical.stress + stress_step_scale * SP_net)
    agent.physical.morale = clamp01(agent.physical.morale + morale_step_scale * MP_net)
```

Where `clamp01` is a small helper:

```python
def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x
```

This function can be called at the end of `run_sleep_consolidation` once per
sleep cycle.

---

## 9. Future Extensions (Non-MVP)

- Incorporate **person beliefs** (e.g. “guards at this hall are cruel”) into
  stress/morale by weighting by usage frequency.
- Add protocols or events that specifically **reset** or **boost** morale
  (celebrations, windfalls, rare Well boons).
- Propagate stress/morale up into **decision heuristics**, e.g.:
  - high stress → riskier behaviors or more queue fights,
  - low morale → higher susceptibility to subversive recruitment.
- Allow Tier-3 entities to track aggregate stress/morale fields at
  pod/ward/city level, driving protocol changes.

For now, D-MEMORY-0207 defines a gentle, continuous feedback loop from place
experience to inner life, suitable for running from tick 0 to year 500 without
special-case rules.
