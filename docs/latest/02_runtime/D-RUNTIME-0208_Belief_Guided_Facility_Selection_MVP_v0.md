---
title: Belief_Guided_Facility_Selection_MVP
doc_id: D-RUNTIME-0208
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-02
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-AGENT-0020   # Canonical_Agent_Model
  - D-AGENT-0022   # Agent_Core_State_Shapes
  - D-MEMORY-0004  # Memory_Tiers_and_Belief_Archetypes
  - D-MEMORY-0205  # Place_Belief_Updates_From_Queue_Episodes_MVP_v0
  - D-MEMORY-0206  # Sleep_And_Episodic_Consolidation_MVP_v0
  - D-MEMORY-0207  # Belief_To_Stress_And_Morale_MVP_v0
---

# 02_runtime · Belief-Guided Facility Selection MVP (D-RUNTIME-0208)

## 1. Purpose & Scope

This document defines a **minimum viable rule** for how agents choose between
multiple facilities that offer the same service, using:

- their **place beliefs** (fairness, safety, reliability, etc.),
- approximate **travel cost**,
- and light **personality-based** modifiers.

The intent is to move from “hard-coded facility IDs” to:

> when an agent needs a service S, they call a generic chooser that returns
> a facility id based on beliefs, distance, and a bit of exploration.

Scope (MVP):

- Define a `service_type` → `facility_ids` registry.
- Define a scoring rule `U(f)` for each candidate facility `f`.
- Define a helper function  
  `choose_facility_for_service(agent, service_type, world, rng)`.
- Describe where this plugs into the existing decision/queue-join flow for
  early services (`ACQUIRE_SUIT`, `OBTAIN_ASSIGNMENT`).

Out of scope (for now):

- Detailed multi-stage pathfinding.
- Tier-3 global optimization or protocol-level traffic shaping.
- Fine-grained personality models; we apply only simple weight adjustments.

---

## 2. Service Types & Facility Registry

### 2.1 Service Types (MVP)

For the wakeup/Golden Age baseline, we treat these services:

- `suit_issue`  
  “Get my initial personal suit” or later, “repair/replace suit.”
- `assignment_hall`  
  “Obtain my initial work assignment / pod allocation.”

Later services can include: `medical`, `rations`, `water_topup`,
`housing_office`, etc.

### 2.2 World-Level Registry

The world must answer:

> “Which facilities provide service S?”

MVP implementation: add a simple mapping on `WorldState`:

```python
class WorldState:
    ...
    service_facilities: dict[str, list[str]] = field(default_factory=dict)
```

Interpretation:

- Keys: `service_type` strings (e.g. `"suit_issue"`, `"assignment_hall"`).
- Values: lists of `facility_id` strings (e.g. `["fac:suit-issue-1", "fac:suit-issue-2"]`).

Scenario setup code (e.g. wakeup scenario builder) MUST populate this mapping:

```python
world.service_facilities.setdefault("suit_issue", []).append("fac:suit-issue-1")
world.service_facilities.setdefault("assignment_hall", []).append("fac:assign-hall-1")
```

Later, adding a second depot is just another `append`.

---

## 3. Belief & Cost Inputs Per Facility

For a given `service_type` S and agent A, the chooser needs, for each
candidate facility `f`:

- `facility_id: str`
- `place_id: str`
  - This can be the facility id itself (`fac:suit-issue-1`) or an associated
    queue-front id (`queue:suit-issue-1:front`), as long as it matches how
    `PlaceBelief.place_id` is keyed.
- `PlaceBelief` record for that `place_id`, if present:
  - `fairness_score` ∈ [-1, +1]
  - `efficiency_score` ∈ [-1, +1]
  - `safety_score` ∈ [-1, +1]
  - `congestion_score` ∈ [-1, +1]
  - `reliability_score` ∈ [-1, +1]
- `distance` / travel cost from the agent’s `location_id` to the facility.

### 3.1 PlaceBelief lookup

Given an `AgentState agent` and a `place_id`:

```python
pb = agent.place_beliefs.get(place_id)
```

If `pb` is `None`, treat all scores as 0.0 (unknown/neutral).

### 3.2 Travel Cost (MVP)

Distance modeling can be simplistic for now. MVP options:

- If a graph distance or path length is already available, normalise it
  into `[0, 1]`:

  ```text
  d_norm = min(1.0, raw_distance / max_reference_distance)
  ```

- If not, use a coarse heuristic:

  - `d_norm = 0.0` if `agent.location_id == facility.location_id`
  - `d_norm = 0.3` if in same pod/cluster
  - `d_norm = 0.7` otherwise

The chooser only assumes a `float` in `[0, 1]` where 0 is “trivial” and
1 is “far”.

---

## 4. Belief-Based Utility U(f)

For each candidate facility `f`, we compute a **subjective utility** `U(f)`
that combines beliefs and travel cost.

Let, for facility `f` and its `PlaceBelief pb` (or defaults):

```text
fair = pb.fairness_score      # [-1, +1]
eff  = pb.efficiency_score
safe = pb.safety_score
cong = pb.congestion_score
rel  = pb.reliability_score
d    = distance_norm          # [0, +1]
```

### 4.1 Base belief utility U_belief

Define:

```text
U_belief = (
    w_rel  * rel  +   # can I actually get things done here?
    w_fair * fair +   # will I be treated fairly?
    w_eff  * eff  +   # does it feel smooth or jammed?
    w_safe * safe -   # personal safety, higher is better
    w_cong * max(0.0, cong)  # penalty for crowding if cong>0
)
```

MVP default weights:

```text
w_rel  = 0.5
w_fair = 0.4
w_eff  = 0.3
w_safe = 0.3
w_cong = 0.2
```

### 4.2 Travel penalty U_cost

Define a travel penalty:

```text
U_cost = -w_dist * d
```

Default:

- `w_dist = 0.5`

Interpretation:

- A very “good” facility might still be disfavored if extremely far.
- Two similar facilities → closer one wins.

### 4.3 Unknown beliefs & exploration bias

If `pb` is `None` (no PlaceBelief yet) treat all scores as 0.0, but we
can add an exploration bonus for curious agents (see §5).

---

## 5. Personality Modifiers & Exploration

### 5.1 Personality trait hooks

We assume `AgentState.personality` includes traits like:

- `caution_vs_bravery` ∈ [-1, +1] (negative = brave, positive = cautious)
- `curiosity_vs_routine` ∈ [-1, +1] (negative = routine, positive = curious)

We apply small scaling to the base weights:

- Cautious vs brave:
  - Cautious (+): increase `w_safe`, `w_cong` (care more about safety & crowding).
  - Brave (−): decrease `w_safe`, `w_cong`.
- Curious vs routine:
  - Curious (+): increase exploration probability (ε) and exploration bonus.
  - Routine-seeking (−): decrease ε, favor last-used facility.

Example pattern:

```python
caution = agent.personality.caution_vs_bravery  # [-1, +1]
curiosity = agent.personality.curiosity_vs_routine

w_safe_eff = w_safe * (1.0 + 0.2 * caution)
w_cong_eff = w_cong * (1.0 + 0.2 * caution)

epsilon_base = 0.1
epsilon = epsilon_base * (1.0 + 0.5 * curiosity)
```

### 5.2 Exploration vs exploitation (ε-greedy)

To avoid “everyone always picks the same max” determinism:

1. Compute `U(f)` for all candidates.
2. With probability `epsilon` (agent-specific):
   - Choose a facility at random, optionally weighted by `softmax(U(f))`.
3. Otherwise:
   - Choose the facility with maximal `U(f)` (tie-break uniformly).

Typical values:

- `epsilon_base = 0.1`
- curious agents: `epsilon ≈ 0.15–0.2`
- routine-seekers: `epsilon ≈ 0.05`

### 5.3 Routine stickiness (optional MVP)

A simple habit effect:

- Track `agent.last_facility_by_service: dict[str, str]`.
- If this contains a facility `f0` for this `service_type`, and
  `curiosity_vs_routine` is negative (routine-seeking), add a small bonus
  (e.g. `+0.1`) to `U(f0)`.

---

## 6. Chooser Helper: Signature & Flow

We define a runtime helper in e.g. `dosadi/runtime/facility_choice.py`:

```python
def choose_facility_for_service(
    agent: AgentState,
    service_type: str,
    world: WorldState,
    rng: random.Random,
) -> str | None:
    """
    Return the facility_id that this agent chooses for the given service_type,
    or None if no facility offers that service.
    """
```

Algorithm (MVP):

1. Get candidates:

```python
candidates = world.service_facilities.get(service_type, [])
if not candidates:
    return None
```

2. For each `facility_id` in `candidates`:
   - Choose `place_id` used for beliefs:
     - MVP: `place_id = facility_id`
     - or a known `queue:*:front` mapping if that’s how beliefs are stored.
   - `pb = agent.place_beliefs.get(place_id)` or default scores (0.0).
   - Compute `d_norm` as approximate distance in `[0, 1]`.
   - Compute personality-adjusted weights.
   - Compute `U_belief` + `U_cost` (+ optional routine bonus).

3. Collect `(facility_id, U)` pairs.

4. Apply ε-greedy selection:

   - With probability `epsilon`, explore.
   - Else, exploit (pick max U).

5. Update `agent.last_facility_by_service[service_type] = chosen_id`
   (if tracking it) and return `chosen_id`.

The helper is pure runtime logic and does not mutate world state (beyond
optional agent-local metadata).

---

## 7. Integration into Decision / Queue Logic

MVP integration targets at least these goal types:

- `ACQUIRE_SUIT`
- `OBTAIN_ASSIGNMENT`

Wherever the code currently uses a **hard-coded facility id**, for example:

```python
target_facility_id = "fac:suit-issue-1"
```

replace with:

```python
target_facility_id = choose_facility_for_service(
    agent=agent,
    service_type="suit_issue",
    world=world,
    rng=rng,
)
if target_facility_id is None:
    # No facility offers this service; either fail the goal
    # or defer until later.
    return
```

Then let the existing navigation / queue-joining code operate on
`target_facility_id` as it already does.

### 7.1 Behavior with One Facility

In the current wakeup scenario:

- `world.service_facilities["suit_issue"]        = ["fac:suit-issue-1"]`
- `world.service_facilities["assignment_hall"]  = ["fac:assign-hall-1"]`

Therefore:

- The chooser always returns that single facility.
- Behavior is identical to the current hard-coded version.
- As soon as a second facility is added (e.g. `fac:suit-issue-2`), belief
  differences and distance start to shape actual routing.

---

## 8. Future Extensions (Non-MVP)

- Use **queue-front-specific** place ids to distinguish “same facility,
  different entrance/shift.”
- Incorporate **time-of-day** or shift information into beliefs and selection
  (e.g. morning vs night crew).
- Let Tier-3 actors manipulate `service_facilities` (open/close sites,
  reroute traffic) in response to aggregate beliefs and metrics.
- Allow some agents to serve as **guides** or **gossip hubs** whose episodes
  disproportionately influence others’ beliefs and thus the flows.

For now, D-RUNTIME-0208 provides a thin but powerful bridge from place beliefs
to actual **movement choices**, ready to scale from early wakeup to a dense,
multi-facility city without changing the core logic.
