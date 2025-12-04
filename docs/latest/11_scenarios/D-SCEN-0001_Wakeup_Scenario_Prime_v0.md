---
title: Wakeup_Scenario_Prime
doc_id: D-SCEN-0001
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-01
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-RUNTIME-0200  # Founding_Wakeup_MVP_Runtime_Loop_v0
  - D-WORLD-0100    # Habitat_Layout_Prime_v0
  - D-AGENT-0020    # Unified_Agent_Model_V0
  - D-AGENT-0022    # Agent_Goal_Stack_MVP_v0
  - D-AGENT-0023    # Group_and_Proto_Council_Logic_MVP_v0
  - D-MEMORY-0102   # Episode_Data_Structures_and_Buffers_v0
  - D-MEMORY-0204   # Episode_Tag_Catalog_MVP_v0
---

# 04_scenarios · Wakeup Scenario Prime v0 (D-SCEN-0001)

## 1. Purpose & Scope

This document defines the **prime wakeup scenario** for the Dosadi simulation:
the initial few hours of life after `tick = 0` when colonists emerge from bunk
pods, receive basic suits, and are assigned roles and bunks.

Goals:

- Provide a **minimal but coherent** setup that can evolve into the broader
  Founding Wakeup MVP runtime (D-RUNTIME-0200) and, eventually, Golden Age play.
- Define the **core queues** and flows that shape early experience:
  - wake queue,
  - medical queue,
  - suit issue queue,
  - assignment queue,
  - optional exception/discipline queue.
- Ensure everything is expressed in terms of:
  - the unified agent model (D-AGENT-0020),
  - the runtime timebase (D-RUNTIME-0001),
  - the episodic memory system (D-MEMORY-0102, 0204).

This is a **design & configuration** document, not an implementation spec. Codex
and other tools should treat it as a reference when wiring scenario generation,
initial world state, and early runtime logic.

---

## 2. Initial Conditions Overview

### 2.1 Timebase

- Simulation tick length: as per D-RUNTIME-0001 (e.g. `1.67` ticks/second).
- Wakeup scenario horizon:
  - Focus on the first **6–12 in-game hours**.
  - In ticks: on the order of **36,000–72,000** ticks (exact values configurable).

### 2.2 Population

Define a base configuration for the initial colonist population:

- Total colonists, `N_total`: **200–400** (configurable; default 240).
- All start as **tier-1 colonists** (no pre-existing nobility or stewards).
- Role affinities (latent):
  - A subset has higher skills/attributes aligned with:
    - medical/biotech,
    - engineering/maintenance,
    - logistics/coordination,
    - security,
    - admin/record-keeping,
    - general labor.
  - These affinities matter for future **task-force formation** and **proto-council**,
    but do not grant formal titles at tick 0.

### 2.3 Physical Layout (Coarse)

The environment is a simple, high-level map (D-WORLD-0100 will define details):

- **Bunk pods**:
  - Multiple sealed pod blocks around the Well core.
  - Each pod block contains 20–40 individual bunk capsules.
  - Example ids: `pod:A`, `pod:B`, `pod:C`, etc.
- **Central corridors** (unsealed, hostile air outside pods):
  - Main radial corridor: `corr:main-core`.
  - Branch corridors leading to facilities (`corr:med`, `corr:suit`, `corr:assign`).
  - Additional side corridors for reconnaissance and maintenance drills (`corr:survey-a`
    → `corr:survey-b`, `corr:maintenance-a` → `corr:maintenance-b`). Half of these
    spur edges are marked **hazardous** (e.g. `edge:corr:main-core:corr:survey-a`,
    `edge:corr:main-core:corr:maintenance-a`) and are deliberately **non-essential**
    so early hazards don’t block access to suits, assignments, or medical.
- **Shared facilities** (unsealed, but with local environmental conditioning):
  - Medical bay: `fac:med-bay-1`.
  - Suit issue depot: `fac:suit-issue-1`.
  - Assignment hall (admin desks, small dais): `fac:assign-hall-1`.
  - Initial ration bay/canteen (optional for v0): `fac:canteen-1`.
- **Exception holding space** (for panic/fighting/etc.):
  - A small isolation or holding cell cluster: `fac:holding-1`.

Movement between pods and facilities requires basic suits.
Outside pods, conditions are harsh but survivable with **basic personal suits**.

Governance scaffolding is baked in from the former MVP runtime:

- Each pod designates an initial representative, enabling a **proto-council** to form
  at the hub without waiting for long migrations.
- Corridor risk metrics seed the **hazard → protocol** loop so council meetings can
  author movement/safety protocols once incident thresholds are crossed (defaults:
  ≥1 incident with ≥0.15 risk on an edge).
- Runtime ticks monitor these seeded metrics and immediately draft movement
  protocols for uncovered hazardous spurs, keeping governance visible even before
  organic incident data accrues.

### 2.4 Initial Resources

These are scenario parameters that can be tuned in config:

- Basic personal suits:
  - Count: equal to or slightly below `N_total` (e.g. 0.9–1.0 × population).
  - Quality: uniform, “mid-tier” breathable + moisture capture; **not** industrial grade.
- Medical resources:
  - Minimal stock, enough for basic triage, not for major disaster scenarios.
- Rations:
  - Enough for several days of full rations for `N_total`,
  - but stock can be dialed up/down to experiment with early scarcity.
- Tools & maintenance kits:
  - A limited number of engineering toolkits and diagnostic devices,
  - initially locked in storage, accessible only via assignment.

All resources start under the control of a **central depot authority** embodied
by the simulation’s early “system protocols” rather than specific agents.

---

## 3. Core Queues

This section defines the main **social and logistical queues** used in Wakeup
Scenario Prime. Each queue is both:

- a **runtime object** that can be implemented as a data structure, and
- a **place** in the world where agents stand, wait, and generate episodes.

### 3.1 Shared Queue Concepts

Common fields for all queues:

- `queue_id`: unique id, e.g. `queue:wakeup:pod-A`.
- `location_id`: where the queue physically exists (corridor or facility).
- `capacity_soft`: preferred max number of waiting agents.
- `capacity_hard`: absolute max (beyond this, new arrivals are redirected/refused).
- `priority_rule`: function / policy shaping ordering:
  - FIFO, role-based priority, severity-based (for medical), or random jitter.
- `processing_rate`: how many agents can be processed per time slice (e.g. per 100 ticks).
- `associated_facility`: facility id (med bay, suit depot, assignment hall).
- `state`: ACTIVE, PAUSED, CANCELED.

Queues naturally generate **episodes** with tags from D-MEMORY-0204:
`queue_served`, `queue_denied`, `queue_canceled`, `queue_fight`.

### 3.2 Wake Queue

**Purpose**: Order of emerging from bunk pods into the world.

- `queue_id`: `queue:wakeup` (may be one per pod block: `queue:wakeup:pod-A`).
- `location_id`: inside pod block corridor / small staging area.
- `priority_rule`:
  - MVP option A: uniform random ordering of all colonists.
  - MVP option B: mild bias toward critical skills (med/engineering first).
- `processing_rate`:
  - e.g. 1–5 agents per 60–300 ticks (tunable: slow/fast wakeup).

**Flow**:

1. At `tick = 0`, all colonists are in **SLEEPING** state in their pods.
2. A wake controller process selects next agents from `queue:wakeup`:
   - transitions them to `AWAKENING`,
   - pushes them to pod interior staging point.
3. After a short orientation period, they are released into adjacent corridor
   with instructions to proceed toward **medical** and then **suit issue**.

This queue does **not** itself use the `queue_*` tags; its main function is
to control initial agent release into the world.

### 3.3 Medical Queue

**Purpose**: Triage newly awakened colonists for health issues.

- `queue_id`: `queue:med-triage`.
- `location_id`: `corr:med` leading into `fac:med-bay-1`.
- `priority_rule`:
  - primarily severity-based (basic health assessment flags),
  - tie-breaker: time waiting, small random jitter.
- `processing_rate`:
  - small number per slice, reflecting limited med staff/resources.

**Flow**:

1. Newly awakened agents are first funneled through corridor near med bay.
2. Agents with obvious anomalies are flagged and added to `queue:med-triage`.
3. Others may bypass med or receive a “brief check” (design choice).

**Episodes** (future):

- Long waits, being passed over, or visibly unfair triage will later generate
  queue and guard/steward episodes, but may be deferred until med logic exists.

### 3.4 Suit Issue Queue

**Purpose**: Distribute basic personal suits to newly awakened colonists.

- `queue_id`: `queue:suit-issue`.
- `location_id`: `fac:suit-issue-1` entrance.
- `priority_rule`:
  - simple FIFO for MVP,
  - later: override for med-critical or essential staff.
- `processing_rate`:
  - suits/week, e.g. 1–3 agents per processing slice.

**Flow**:

1. After wake (and optional med), agents join `queue:suit-issue`.
2. Each processed agent receives:
   - a **basic suit** (if stock available),
   - or a denial if suits are exhausted (config-dependent).
3. Agents without suits may be restricted in where they can go next.

**Episodes**:

- When an agent is successfully given a suit:
  - `summary_tag = "queue_served"`,
  - `target_type = PLACE`, `target_id = fac:suit-issue-1`,
  - `channel = DIRECT` for the served agent.
- When an agent is denied due to stock or exclusion:
  - `summary_tag = "queue_denied"`,
  - same target semantics,
  - high importance, negative valence.
- Observers in/near the queue may receive OBSERVED episodes for these events.

### 3.5 Assignment Queue

**Purpose**: Assign roles, bunks, and initial ration entitlements.

- `queue_id`: `queue:assignment`.
- `location_id`: `fac:assign-hall-1` fore area.
- `priority_rule`:
  - FIFO for MVP, but with potential for future bias toward critical skill sets.
- `processing_rate`:
  - small but steady: a few agents per processing slice.

**Flow**:

1. After acquiring suits, agents are instructed to join `queue:assignment`.
2. Each processed agent receives:
   - role/assignment (e.g. general labor, med assistant, maintenance trainee),
   - bunk assignment,
   - ration band/category.
3. Agents that display initiative, composure, or relevant skills may be tagged
   for future proto-council or steward roles.

**Episodes**:

- Days with smooth, orderly allocation yield mostly `queue_served` episodes.
- Perceived or real unfairness in assignment can be represented later via
  steward/guard tags rather than new queue tags.

### 3.6 Exception / Discipline Queue (Optional for v0)

**Purpose**: Handle agents who panic, resist orders, or cause disruption.

- `queue_id`: `queue:exception`.
- `location_id`: `fac:holding-1` entry.
- `priority_rule`:
  - defined by security protocol (later),
  - likely severity-based (threat to others first).
- **Flow** (MVP placeholder):
  - Agents flagged as disruptive are redirected here for temporary confinement.
  - Actions taken in/around this queue will later seed `guard_brutal`,
    `guard_help`, `steward_unfair` episodes.

For v0, this queue can exist only as a stub; implementation can come later.

---

## 4. Agent State & Goal Setup at Wake

### 4.1 Initial AgentState Fields

All agents should be instantiated using `AgentState` (D-AGENT-0020) with:

- `tier = 1`,
- `roles = ["colonist"]` (later updated by assignment queue),
- `location_id =` their bunk pod id or pod interior area,
- `episodes` and belief structures initialized but empty,
- attributes/personality sampled within reasonable ranges.

### 4.2 Initial Goals

At the moment an agent is fully awakened (exits pod sleep state), they should
receive a minimal goal stack, for example:

1. **Primary**: survive the first phase of wakeup.
2. **Sub-goals**:
   - `Goal(kind="get_suit", target_location_id="fac:suit-issue-1")`,
   - `Goal(kind="get_checked", target_location_id="fac:med-bay-1")` (optional),
   - `Goal(kind="get_assignment", target_location_id="fac:assign-hall-1")`,
   - `Goal(kind="secure_bunk")` (implied by assignment).

As soon as the agent has a basic suit + assignment, higher-level goals can
be introduced (e.g. “perform assigned work”, “maintain access to rations”).

### 4.3 Interaction With Episodic Memory

During the wakeup window, the main episode types likely to be generated are:

- `queue_served`, `queue_denied`, `queue_canceled`, `queue_fight`,
- body signals (hunger, thirst, fatigue) as time passes,
- early guard/steward episodes around exception handling (later),
- protocol reads if any posted rules exist.

These episodes will:

- flow into `AgentState.episodes.short_term` (via `record_episode`),
- be promoted to `daily` via the promotion logic (D-MEMORY-0102),
- be consolidated into place/person beliefs during sleep/downtime.

Wakeup Scenario Prime assumes at least one **rest cycle** after the initial
wake wave so that early experiences can start to gel into beliefs.

---

## 5. Scenario Progression Sketch (Tick Timeline)

This is a qualitative sketch; exact tick counts and rates are tunable via
runtime configuration.

1. **Tick 0–N_wake**: Wake wave rollout
   - `queue:wakeup` gradually releases agents from pods.
   - Agents orient and begin moving toward med/suit facilities.
   - Little to no formal hierarchy beyond basic system prompts.

2. **Tick N_wake–N_suit**: Suit distribution stress test
   - `queue:suit-issue` fills and starts processing.
   - If suit stock is at or below population, tension emerges:
     - denials (`queue_denied`),
     - complaints, possibly first minor altercations (`queue_fight` candidates).
   - Early body signal episodes begin accumulating (fatigue, hunger, thirst).

3. **Tick N_suit–N_assign**: Assignment hall activation
   - Agents with suits join `queue:assignment`.
   - Proto-patterns of work organization begin:
     - some agents are tagged as more competent or composed,
     - these may be first candidates for proto-council or steward roles.
   - Early perceptions of fairness/unfairness in assignment form.

4. **Tick N_assign–N_rest**: First consolidation opportunity
   - Some agents reach temporary rest/sleep windows.
   - Daily memory buffers are consolidated into beliefs.
   - The system’s initial **soft stratification** begins:
     - some corridors/facilities become “known” as orderly/chaotic,
     - some staff members acquire reputational halos (not yet formal titles).

5. **Post N_rest**: Hand-off to broader Founding Wakeup runtime
   - Scenario passes a fully-initialized population with:
     - basic suits,
     - initial work/bunk assignments,
     - nascent place/person beliefs.
   - Further evolution (proto-council formation, guild seeds) is handled by
     D-RUNTIME-0200 and related docs.

---

## 6. Parameters & Tuning Knobs

To support experimentation and later phase transitions, this scenario SHOULD
expose the following configuration knobs:

- Population:
  - `N_total` colonists,
  - distribution of latent role affinities.
- Wake parameters:
  - wake batch size,
  - wake interval (ticks between wake operations),
  - wake ordering rule (random vs biased).
- Queue parameters (per queue):
  - processing_rate,
  - soft/hard capacity,
  - priority_rule (function/enum).
- Suit stock:
  - initial suit count (relative to population).
- Med capacity:
  - med triage processing rate,
  - fraction of agents routed through full med queue.
- Assignment style:
  - whether assignments try to match role affinities or are random.
- Exception handling:
  - whether an exception queue is active,
  - fraction of agents diverted there under stress.

These knobs will be central to exploring different **Golden Age Baseline**
variants (abundant vs tight, orderly vs chaotic) while using the same core
mechanics.

---

## 7. Implementation Notes (Non-binding)

When implementing Wakeup Scenario Prime in code, Codex SHOULD:

- Provide a scenario generator function, e.g.:
  - `generate_wakeup_scenario_prime(config) -> WorldState`,
  - residing under `src/dosadi/scenarios/`.
- Instantiate queue objects for:
  - wake,
  - med (optional in v0),
  - suit,
  - assignment,
  - exception (optional stub).
- Register facilities and corridors with ids matching this document, or
  provide a consistent mapping layer if names differ.
- Seed agents using `AgentState` with:
  - tier-1 status,
  - basic `roles=["colonist"]`,
  - initial goals as described in §4.2.

All detailed behavioral rules (how agents move, how queues are processed, how
episodes are generated) should follow the relevant runtime and memory docs and
be implemented in their respective modules, not inside the scenario generator.

