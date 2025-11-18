---
title: Agent_Decision_Rule_v0
doc_id: D-AGENT-0002
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0001  # Agent_Core_Schema_v0
  - D-WORLD-0003  # Ward_Branch_Hierarchies
  - D-CIV-0000    # Civic_Microdynamics_Index
  - D-CIV-0001    # Civic_Microdynamics_Soup_Kitchens_and_Bunkhouses
  - D-CIV-0002    # Civic_Microdynamics_Clinics_and_Triage_Halls
  - D-CIV-0006    # Civic_Microdynamics_Entertainment_and_Vice_Halls
  - D-INFO-0003   # Information_Flows_and_Report_Credibility
---

# Agent Decision Rule v0

> This document defines a **lightweight decision algorithm** for Tier 1 agents in early Dosadi simulations.
> - It connects the Agent Core Schema (drives, traits, beliefs) to concrete actions.
> - It is cheap to run for thousands of agents.
> - It is designed so that later, more advanced controllers (e.g. RL policies) can *replace only the scoring step*.

The focus is daily civic behavior in and around:

- Soup kitchens & bunkhouses
- Clinics & triage halls
- Entertainment & vice venues
- Streets and simple workplaces

---

## 1. Overview

At each decision tick, an agent:

1. Checks hard constraints (alive, incapacitated, arrested).
2. Refreshes drives from body state and recent experience.
3. Builds a set of feasible candidate actions.
4. Scores each action using:
   - Drive urgencies
   - Expected drive relief/penalty
   - Beliefs about facilities & factions
   - Simple costs (distance, price, risk)
5. Samples one action (probabilistic, not purely greedy).
6. Commits the decision by updating its `state` block.

This rule is intended for **Tier 1** agents (background population):

- Simple heuristics.
- Light memory.
- No explicit planning beyond local expectations.

Tier 2/3 agents may later substitute a richer decision module while keeping the same input/output structure.

---

## 2. Preconditions & Tick Cadence

- **Decision tick**: every N simulation ticks (e.g. every few in-game minutes).
- Before running the decision rule:

```pseudo
if not body.alive:
    return  // handled elsewhere

if state.incapacitated:
    // e.g. unconscious in clinic or after beating
    state.current_action = "WAIT"
    return

if state.arrested:
    // separate logic (guard interactions, court transfers) may handle this
    return
```

Agents who are:
- Healthy enough and not constrained by arrest/incapacitation
- Proceed through the decision pipeline.

---

## 3. Drive Refresh

Drives are maintained as:

```json
"drives": {
  "SURVIVAL": { "value": 0.6, "weight": 1.0 },
  "SAFETY":   { "value": 0.3, "weight": 0.9 },
  "BELONG":   { "value": 0.5, "weight": 0.8 },
  "STATUS":   { "value": 0.2, "weight": 1.1 },
  "CONTROL":  { "value": 0.3, "weight": 1.0 },
  "NOVELTY":  { "value": 0.4, "weight": 1.0 },
  "MORAL":    { "value": 0.1, "weight": 0.9 }
},
"stress": 0.4
```

### 3.1 Body → Drive Updates

On each decision tick (or every few ticks), run a simple update:

- SURVIVAL.value:
  - Increases as:
    - `hydration` decreases
    - `nutrition` decreases
    - `health` decreases
    - `sleep_debt` increases
- SAFETY.value:
  - Increases with:
    - Recent violent events in `memory.recent_events`
    - High perceived risk in current ward/zone
- BELONG.value:
  - Increases as:
    - Time since meaningful interaction with own faction / close ties grows
- STATUS.value:
  - Increases after:
    - Public humiliation, demotions, chronic low-rank work, visible inequality
- CONTROL.value:
  - Increases when:
    - Repeatedly denied permits, blocked at facilities, tightly surveilled
- NOVELTY.value:
  - Increases with:
    - Monotonous routines and lack of interesting events
  - Decreases temporarily after:
    - High-stimulation events (vice, fights, major discoveries)
- MORAL.value:
  - Increases when:
    - Agent acts against their own code, or witnesses factional hypocrisy

### 3.2 Stress as Modifier

`stress` is a scalar (0–1):

- Increases with:
  - Conflict, overwork, crowding, perceived danger, humiliation.
- Decreases with:
  - Rest, safe bunk sleep, calming social contact, certain vice.

Stress does not have its own “goal”; instead it **amplifies or distorts** other drives when choosing actions.

---

## 4. Candidate Actions

The simulation defines a set of generic action types, e.g.:

- `GO_TO_FACILITY(facility_id)`
  - Kitchens, bunkhouses, clinics, vice halls, workplaces, courts, permit offices.
- `REST_HERE`
  - Resting/sleeping when current location allows (bunk, clinic bed, etc.).
- `STAY_PUT` / `IDLE`
  - Loiter, small talk, passive waiting.
- `GO_TO_WORK`
  - If `job_role` has an associated workplace.

For an early civic-focused prototype, a minimal set might be:

- `GO_TO_KITCHEN`
- `GO_TO_BUNK`
- `GO_TO_CLINIC`
- `GO_TO_VICE`
- `GO_TO_WORK`
- `IDLE`

### 4.1 Building the Candidate Set

At each decision tick:

1. Start from global action templates.
2. Filter by **feasibility**:
   - Facility of required type exists and is reachable from `state.location_id`.
   - Agent is not banned or hard-blocked (e.g. blacklisted, closed facility).
3. Filter by **role constraints**:
   - If `state.on_duty == true` and `job_role` is `militia_guard`, allowed actions may be restricted to patrol/inspection behaviours.
4. Wrap each as an action proposal:

```json
{
  "type": "GO_TO_FACILITY",
  "target_facility": "W21_KITCHEN_01"
}
```

Result: a list `candidate_actions = [a1, a2, ..., ak]`.

---

## 5. Scoring Actions

Each candidate action is scored based on:

- Drive urgencies
- Expected drive relief/penalty
- Beliefs about the target facility/faction
- Costs (distance, time, price, risk)
- Small randomness

### 5.1 Drive Urgency

For each drive D:

```text
urgency(D) = drives[D].value * drives[D].weight * f(stress)
```

Where a simple choice for `f(stress)` is:

```text
f(stress) = 1 + stress    // 1 to 2x amplification
```

This means:

- At high stress, all unmet drives “scream” louder.
- At low stress, agents can be more measured.

### 5.2 Expected Drive Relief per Action

For each action `a`, we define **expected** drive changes:

```text
expected_relief(D, a) ≈ - E[Δ drives[D].value | performing a]
```

Examples (signs are conceptual only):

- `GO_TO_KITCHEN` (and receive food):

  - `ΔSURVIVAL.value  ≈ -0.5`  → strong positive relief
  - `ΔBELONG.value    ≈ -0.1`  → if regulars/friends are present
  - `ΔSTRESS          ≈ -0.1`

- `GO_TO_BUNK` (and sleep a block):

  - `ΔSURVIVAL.value  ≈ -0.3`  → via sleep_debt recovery
  - `ΔSAFETY.value    ≈ -0.05 .. +0.05` depending on bunk reputation
  - `ΔSTRESS          ≈ -0.2`

- `GO_TO_VICE` (drinking hall):

  - `ΔSTRESS          ≈ -0.4`
  - `ΔBELONG.value    ≈ -0.2` (short-term social relief)
  - `ΔNOVELTY.value   ≈ -0.3` (for now)
  - But:
    - `ΔSURVIVAL.value  ≈ +0.05` (health/addiction risk)
    - `ΔSAFETY.value    ≈ +0.05` (violence/raid risk)

These expectations can be stored in a **drive–facility impact table** (separate document or data file), and may be modulated by the agent’s beliefs.

### 5.3 Costs

Each action has a simple cost term:

- Travel distance/time from current location to target facility.
- Monetary cost (entry, food, drink, treatment).
- Risk exposure (e.g. passing through dangerous zones, or vice violence risk).

Represented as a single scalar `cost(a)`, normalized to the same rough scale as the utilities.

### 5.4 Belief-Based Adjustment

Agents hold noisy beliefs about facilities (see D-AGENT-0001 and civic docs):

For a facility `F`, they might store:

```json
"facility_attitudes": {
  "W21_KITCHEN_01": {
    "safety": 0.6,
    "fairness": 0.4,
    "queue_length": 0.7
  }
}
```

We define a simple multiplicative adjustment:

```text
belief_adjustment(F) =
    (0.5 + 0.5 * safety)
  * (0.5 + 0.5 * fairness)
  * (1.0 - 0.3 * queue_length)
```

- Unsafe, unfair, and long-queue facilities reduce the effective utility of going there.
- Safer, fairer, and efficient facilities boost it.

### 5.5 Loyalty & MORAL Modifiers

Actions can **support** or **undermine** factions to which the agent has loyalty:

- Supportive actions:
  - e.g. obeying orders from `primary_faction`, patronizing their facilities, assisting their projects.
- Undermining actions:
  - e.g. attending rival faction halls, joining their micro-economy, or actions that betray secrets.

We apply an additional factor:

```text
loyalty_adjustment(a) ≈ 1 + k * (net_loyalty_supported - net_loyalty_harmed)
```

Where `k` is a small constant, and `net_loyalty_*` is a function of:

- `social.loyalty[faction]`
- The known alignment of the target facility/action.

If an action strongly undermines a high-loyalty faction, MORAL drive may spike and an extra penalty can be applied to its utility.

---

## 6. Utility Calculation & Selection

### 6.1 Utility

For each action `a`:

```text
utility(a) =
    Σ_D [ urgency(D) * expected_relief(D, a) ]
  * belief_adjustment(target_facility(a))
  * loyalty_adjustment(a)
  - cost(a)
  + noise
```

Where:

- `D` ranges over the drives: SURVIVAL, SAFETY, BELONG, STATUS, CONTROL, NOVELTY, MORAL.
- `noise` is a small random term to avoid deterministic lockstep behavior.

### 6.2 Selection Method

We avoid deterministic argmax to keep populations diverse.

Two simple options:

#### Softmax

```text
P(a_i) = exp(utility(a_i) / T) / Σ_j exp(utility(a_j) / T)
```

- `T` = temperature; higher `T` yields more randomness.

#### Epsilon-Greedy

- With probability `ε`:
  - Pick a random action from `candidate_actions`.
- With probability `1 - ε`:
  - Choose the action with maximum utility.

For v0:

- Either softmax with a moderate `T`, or epsilon-greedy with `ε` ~ 0.1–0.2 is sufficient.

---

## 7. Committing the Decision

Once an action `a*` is chosen:

- Update the agent’s `state`:

```json
"state": {
  "location_id": "W21_STREET_03",
  "current_action": "GO_TO_FACILITY",
  "current_target_facility": "W21_KITCHEN_01",
  "on_duty": false,
  "arrested": false,
  "incapacitated": false,
  "tick_last_decision": 128290
}
```

The **world/simulation** then:

- Moves the agent toward the target facility.
- Resolves:
  - Entry vs rejection.
  - Queues and wait times.
  - Outcomes (fed, treated, entertained, injured, arrested, etc.).
- Writes a summary of this as an event in:

```json
"memory.recent_events"
```

And optionally into facility-level logs (LEDGER, OP_LOG, SHADOW).

On the next decision tick:

- Drives are nudged based on the new body state and `recent_events`.
- Beliefs about the facility/faction are gently updated.
- A new decision is made under slightly shifted urgencies.

---

## 8. Worked Micro-Example

**Scenario:**

- Agent: low-caste day laborer, moderately injured, very hungry, stressed.
- Drives:
  - `SURVIVAL.value = 0.8`, `SAFETY.value = 0.3`, `BELONG.value = 0.4`,
  - `STATUS.value = 0.1`, `CONTROL.value = 0.2`, `NOVELTY.value = 0.3`, `MORAL.value = 0.1`, `stress = 0.5`.
- Candidates:
  - `GO_TO_KITCHEN_01`
  - `GO_TO_VICE_DRINK_01`
  - `GO_TO_BUNK_02`
  - `IDLE`

**Expected impacts (simplified):**

- `GO_TO_KITCHEN_01`:
  - Strong SURVIVAL relief, small BELONG relief, small STRESS relief.
- `GO_TO_VICE_DRINK_01`:
  - Strong STRESS and BELONG relief, some NOVELTY relief, small SURVIVAL penalty, small SAFETY penalty.
- `GO_TO_BUNK_02`:
  - Moderate SURVIVAL relief (sleep), moderate STRESS relief.
- `IDLE`:
  - Essentially no relief, maybe small BELONG relief if others nearby.

Given SURVIVAL urgency dominates (0.8 unmet, weight 1.0, plus stress), `GO_TO_KITCHEN_01` will likely have the highest utility, but:

- If the kitchen is believed unfair, unsafe, and very slow:
  - `belief_adjustment` reduces its effective draw.
- If vice hall is perceived as safe and cheap relative to how miserable they feel:
  - It may sometimes win out.

The result is a population where:

- Most hungry agents head toward kitchens.
- A fraction peel off into bunkhouses (if exhausted) or vice halls (if stress/novelty + traits push them).
- Lines, crowding, and venue reputations feed back into future decisions.

---

## 9. Extensibility

This v0 rule is designed so that future upgrades can:

- Swap out the **utility calculation** with:
  - Learned policies (RL), local planners, or hand-authored scripts.
- Add richer candidate actions:
  - Explicit `REPORT`, `BRIBE`, `INTIMIDATE`, `BLACKMAIL`, `JOIN_FACTION`, `BETRAY_FACTION`.
- Apply the same loop at higher abstraction:
  - Leaders choosing ward-scale decisions.

The rest of the pipeline:

- Drive refresh
- Candidate generation
- State update

can remain largely unchanged, keeping the system understandable and debuggable.

---
