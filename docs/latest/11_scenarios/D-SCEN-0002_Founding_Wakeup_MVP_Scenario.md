---
title: Founding_Wakeup_MVP_Scenario
doc_id: D-SCEN-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-RUNTIME-0200  # Founding_Wakeup_MVP_Runtime
  - D-AGENT-0020    # Agent_Model_Foundation
  - D-AGENT-0021    # Agent_Goals_and_Episodic_Memory
---

# 1. Scenario Overview

## 1.1 Scenario id and label

- **scenario_id:** `founding_wakeup_mvp`
- **label:** Founding Wakeup MVP – Pods, Proto-Council, First Protocol

This scenario defines the concrete initial conditions and parameters for the first end-to-end runtime test of the Dosadi simulation:

- N colonists wake up in bunk pods around the Well.
- They form pod-level structures and at least one proto-council.
- The proto-council sets information-gathering goals and assigns scouts.
- Scouts explore dangerous corridors.
- The proto-council authors and propagates at least one movement/safety protocol.


## 1.2 Design intent

This is the **minimum viable product (MVP)** scenario. It exists to:

- Exercise the unified **Agent + Goal + Episodic Memory** loop in a small, legible world.
- Demonstrate the **Risk and Protocol Cycle** (D-LAW-0010) in miniature:
  - Hazard episodes → patterns → group goals → protocols → reduced hazard.
- Provide a stable target for incremental implementation:
  - Worldgen, agent core, decision loop, groups/councils, protocols, reporting.

The scenario is intentionally small and focused. Later scenarios (sting waves, cartel regimes, etc.) can be built by expanding this footprint, not by replacing it.


# 2. Initial Conditions

## 2.1 Population

- **Total colonists (N):**
  - Default: `80`
  - Range for experimentation: `40–120`

- **Tier:**
  - All colonists begin as `tier = 1`.

- **Roles at tick 0:**
  - `["colonist"]` for all agents.
  - No formal stewards, dukes, kings, guild heads, or cartel actors exist yet.

- **Distribution into pods:**
  - **Number of pods (K):** default `4`
  - Pod capacities (example default):
    - `pod-1`: 20 agents
    - `pod-2`: 20 agents
    - `pod-3`: 20 agents
    - `pod-4`: 20 agents
  - Worldgen should distribute agents across pods as evenly as possible.

Pods represent sealed bunk clusters that are safe and environmentally controlled but open onto hazardous corridors.


## 2.2 Environment & topology (high-level)

A minimal corridor graph connects pods to the Well core:

- Nodes:
  - `loc:pod-1`, `loc:pod-2`, `loc:pod-3`, `loc:pod-4`
  - `loc:corridor-2A`, `loc:corridor-3A`, `loc:corridor-7A`
  - `loc:junction-7A-7B` (optional)
  - `loc:well-core`

- Edges (example default):
  - `pod-1  <-> corridor-2A  <-> well-core`
  - `pod-2  <-> corridor-3A  <-> well-core`
  - `pod-3  <-> corridor-3A  <-> well-core`
  - `pod-4  <-> corridor-7A  <-> junction-7A-7B  <-> well-core`

- Hazard profile:
  - Corridors `2A` and `3A` have **low** base hazard probability (e.g. 0.02–0.05).
  - Corridor `7A` has **high** base hazard probability (e.g. 0.15–0.25).
  - Junction `7A-7B` may have low/moderate hazard (e.g. 0.05–0.10).

See `D-WORLD-0100` for a more detailed topology and parameterization.


## 2.3 Agent traits and state

At tick 0:

- **Attributes (STR/DEX/END/INT/WIL/CHA):**
  - Sampled from a narrow distribution around 10.
  - No extreme outliers needed for MVP.

- **Personality traits:**
  - Mild variation in:
    - bravery/caution,
    - communal/self-serving,
    - ambition/contentment,
    - curiosity/routine-seeking.
  - A small subset (10–20%) receive slightly elevated:
    - LeadershipWeight,
    - communal/responsible tendencies.

- **Physical & psychological state:**
  - Health: near baseline.
  - Fatigue: low.
  - Hunger/thirst: low but non-zero (to motivate eventual movement).
  - No major injuries or trauma at start.


## 2.4 Initial goals

Each agent’s **initial goal stack** must be consistent with `D-AGENT-0021` and include:

- **Universal parent goal:**
  - `MAINTAIN_SURVIVAL_TODAY` (priority ~1.0, horizon = SHORT)

- **Core sub-goals:**
  - `ACQUIRE_RESOURCE` (food/water abstracted; enough to justify limited travel).
  - `SECURE_SHELTER` (already effectively satisfied, but shapes avoidance of losing pod).
  - `MAINTAIN_RELATIONSHIPS` (generic social stability in pod; can be implied).

- **Leadership-inclined agents:**
  - `REDUCE_POD_RISK` (priority MEDIUM–HIGH, horizon = MEDIUM).
  - Optionally `FORM_GROUP` or `STABILIZE_POD`.

No proto-council or protocol-related goals exist at tick 0.


# 3. Scenario Parameters

## 3.1 Time horizon

- **Default tick count:** `ticks = 1000`
- **Exploration range:** `500–2000` ticks.

For MVP, a run is considered adequate if:

- Pod spokespeople emerge by ~tick 200–400.
- A proto-council forms by ~tick 300–600.
- First protocol authored by ~tick 400–800.

Exact numbers are guidelines, not strict requirements.


## 3.2 Meeting cadence

Default cadences (can be parameters):

- **Pod meeting interval:**
  - On average every `20–40` ticks, per pod.
  - Implementation can use:
    - Fixed interval (e.g. every 30 ticks), or
    - Probabilistic trigger each tick.

- **Council meeting trigger:**
  - Whenever ≥2 pod representatives are present at `loc:well-core` at the same tick.
  - Optionally, enforce a cool-down (e.g. 10 ticks) between formalized council meetings.


## 3.3 Hazard probabilities (suggested defaults)

- **Low-risk corridors (2A, 3A):**
  - `base_hazard_prob = 0.02` (2% per traversal).

- **High-risk corridor (7A):**
  - `base_hazard_prob = 0.20` (20% per traversal).

- **Junction (7A-7B):**
  - `base_hazard_prob = 0.05` (5% per traversal).

These values are intentionally exaggerated to make risk gradients / protocol effects visible in short runs.


## 3.4 Protocol thresholds

For the proto-council to author a movement/safety protocol for a corridor:

- **Minimum incident count:**
  - At least `3` hazard episodes (`HAZARD_INCIDENT` or `HAZARD_NEAR_MISS`) involving the corridor.
- **Risk score threshold:**
  - Simple risk score (frequency × severity) above `risk_threshold`, e.g. 0.3–0.5 on a 0–1 scale.

These thresholds are tuning knobs; the scenario spec defines suggested defaults for consistency across runs.


# 4. Scenario Success Conditions

A run of `founding_wakeup_mvp` is considered **successful** if all of the following are true by the end of the tick horizon:

1. **Pod leadership:**
   - Each pod has at least one agent with role `POD_REPRESENTATIVE`.

2. **Proto-council formation:**
   - At least one `group:council:*` exists with ≥2 pod representatives as members.

3. **Information-gathering goals:**
   - At least one `GATHER_INFORMATION` group goal has been created by a proto-council.
   - At least one corridor (preferably `corridor-7A`) has been visited by scouts as part of such a goal.

4. **Protocol authored and read:**
   - At least one `TRAFFIC_AND_SAFETY` protocol has been authored by the proto-council.
   - At least 10% of agents have `READ_PROTOCOL` episodes for that protocol.

5. **Hazard reduction:**
   - For at least one corridor covered by a protocol:
     - Hazard incidents per 100 traversals **decrease** in the post-protocol period vs the pre-protocol period.

These success conditions are logical/behavioral targets; exact numeric cutoffs can be tuned in code.


# 5. YAML-style Scenario Config (for Codex)

This section provides a concrete, machine-friendly configuration sketch for use by Codex and implementation scripts.

```yaml
scenario_id: founding_wakeup_mvp
label: "Founding Wakeup MVP – Pods, Proto-Council, First Protocol"

population:
  num_agents: 80
  num_pods: 4
  pod_capacities:
    pod-1: 20
    pod-2: 20
    pod-3: 20
    pod-4: 20

world:
  nodes:
    - id: loc:pod-1
      type: pod
    - id: loc:pod-2
      type: pod
    - id: loc:pod-3
      type: pod
    - id: loc:pod-4
      type: pod
    - id: loc:corridor-2A
      type: corridor
    - id: loc:corridor-3A
      type: corridor
    - id: loc:corridor-7A
      type: corridor
    - id: loc:junction-7A-7B
      type: junction
    - id: loc:well-core
      type: hub

  edges:
    - from: loc:pod-1
      to: loc:corridor-2A
      base_hazard_prob: 0.02
    - from: loc:corridor-2A
      to: loc:well-core
      base_hazard_prob: 0.02

    - from: loc:pod-2
      to: loc:corridor-3A
      base_hazard_prob: 0.02
    - from: loc:pod-3
      to: loc:corridor-3A
      base_hazard_prob: 0.02
    - from: loc:corridor-3A
      to: loc:well-core
      base_hazard_prob: 0.02

    - from: loc:pod-4
      to: loc:corridor-7A
      base_hazard_prob: 0.20
    - from: loc:corridor-7A
      to: loc:junction-7A-7B
      base_hazard_prob: 0.20
    - from: loc:junction-7A-7B
      to: loc:well-core
      base_hazard_prob: 0.05

runtime:
  ticks: 1000
  pod_meeting_interval_ticks: 30   # approximate target
  council_meeting_cooldown_ticks: 10

protocol_rules:
  min_incidents_for_protocol: 3
  risk_threshold: 0.4
  default_hazard_multiplier_if_compliant: 0.5  # halve hazard when protocol is obeyed

success_criteria:
  min_pod_representatives_per_pod: 1
  min_councils: 1
  min_information_goals: 1
  min_protocols_authored: 1
  min_protocol_read_fraction: 0.1
  require_hazard_reduction: true
```

Implementations do not need to read this YAML directly, but it should be used as the **source of truth** for worldgen and scenario-level parameters.


# 6. Implementation Surface (for Codex)

Codex and other tooling should rely on the following functions and ids when wiring this scenario into the codebase:

- **Scenario id:**
  - `founding_wakeup_mvp`

- **Worldgen:**
  - `generate_founding_wakeup_mvp(num_agents: int, seed: int) -> (world, agents, groups)`

- **Scenario runner:**
  - `run_founding_wakeup_mvp(num_agents: int, ticks: int, seed: int) -> ScenarioReport`

- **Report fields (minimum):**
  - `scenario_id`
  - `num_agents`
  - `num_pods`
  - `num_pod_representatives`
  - `num_councils`
  - `num_protocols_authored`
  - Per-corridor hazard metrics pre/post protocol.

The details of `world`, `agents`, `groups`, and `ScenarioReport` are further specified in `D-RUNTIME-0200` and related agent/runtime docs.
