---
title: Initial_Work_Detail_Taxonomy_MVP
doc_id: D-RUNTIME-0212
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-02
depends_on:
  - D-SCEN-0002   # Founding_Wakeup_Scenario
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-LAW-0010   # Civilization_Risk_Loop
  - D-LAW-0014   # Proto_Council_Protocol_Tuning_MVP
  - D-AGENT-0020   # Canonical_Agent_Model
  - D-AGENT-0022   # Agent_Core_State_Shapes
  - D-MEMORY-0102  # Episode_Representation
---

# Initial Work Detail Taxonomy (MVP) — D-RUNTIME-0212

## 1. Purpose & scope

This document defines a **minimal taxonomy of work details** available in the
Founding Wakeup / early Golden Age phase. These are the concrete “job types”
that:

- the **proto council** requests in order to reduce risk and uncertainty, and
- the **assignment hall** hands out as work details to individual agents.

Scope (MVP):

- Phase: Founding Wakeup and the first few “days” of Golden Age.
- Focus: “first arc” jobs that answer:
  - *What is out there?*
  - *What do we have?*
  - *How do we keep people alive?*
- Output: a small catalog of `WorkDetailType` entries with:
  - purpose,
  - preferred agent traits,
  - typical episodes produced,
  - proto-council goals that spawn them.

Out of scope (for now):

- Long-run specialized guild jobs (water cartel, espionage, narcotics, etc.).
- Complex rank ladders, pay scales, or political offices.


## 2. Conceptual frame

From D-LAW-0010, the civilization loop is:

1. Individuals form groups to reduce risk.
2. Groups coordinate assets to identify risk.
3. Councils author protocols to reduce these risks.

Work details are the **bridge** between (2) and (3):

- Proto council sets **macro goals**:
  - MAP_INTERIOR, MAP_EXTERIOR, INVENTORY_STORES,
    STABILIZE_ENVIRONMENT, BRING_FOODLINE_ONLINE, etc.
- Assignment hall translates these into **micro-level work details** that
  individual agents can perform:
  - SCOUT_INTERIOR, SCOUT_EXTERIOR, INVENTORY_STORES,
    ENV_CONTROL_DETAIL, FOOD_PROCESSING_DETAIL, etc.
- Agents perform work → generate **episodes**:
  - `SCOUT_PLACE`, `HAZARD_FOUND`, `CRATE_OPENED`, `QUEUE_FED`, …
- These episodes feed:
  - place beliefs (for movement and risk perception),
  - resource ledgers (for production plans),
  - proto-council understanding (via reports and logs).


## 3. Proto council macro goals (early phase)

At wakeup, the proto council’s first macro-level goals are:

1. **MAP_INTERIOR**
   - Understand pods, corridors, choke points, bottlenecks.
2. **MAP_EXTERIOR**
   - Assess immediate environment; identify safe / unsafe zones.
3. **INVENTORY_STORES**
   - Determine stocks of food, water, suit parts, tools, materials.
4. **STABILIZE_ENVIRONMENT**
   - Make living spaces breathable, not lethal, not disgusting.
5. **BRING_FOODLINE_ONLINE**
   - Establish basic food processing and distribution.
6. **SECURE_WATER_HANDLING**
   - Ensure barrels, purification, and conditioning are under control.
7. **ESTABLISH_RECORDKEEPING**
   - Make small but durable ledgers, maps, and protocols.

Each macro goal is realized through **one or more work detail types**.


## 4. Work detail types — catalog

### 4.1 Scout & survey details

#### 4.1.1 SCOUT_INTERIOR

- **Purpose**
  - Walk pods, corridors, stairwells, junctions; map topology and bottlenecks.
- **Preferred traits**
  - Above-average END, reasonable AGI.
  - Moderate curiosity, moderate bravery.
- **Typical actions**
  - MOVE_THROUGH_CORRIDOR, MARK_JUNCTION, NOTE_CHOKEPOINT,
    REPORT_TO_SCRIBE.
- **Typical episodes produced**
  - `SCOUT_PLACE` (PLACE target, low threat).
  - `CORRIDOR_CROWDING_OBSERVED` (PLACE, congestion tags).
- **Council macro goals**
  - Supports MAP_INTERIOR, STABILIZE_ENVIRONMENT.

#### 4.1.2 SCOUT_EXTERIOR

- **Purpose**
  - Short sorties outside to identify terrain, hazards, potential build sites.
- **Preferred traits**
  - High END, high bravery, decent AGI, functional suits.
- **Typical actions**
  - EXIT_HATCH, WALK_EXTERNAL, MARK_LANDMARK, RETURN_WITH_REPORT.
- **Typical episodes produced**
  - `SCOUT_PLACE` (PLACE, higher threat / hazard tags).
  - `HAZARD_FOUND` (PLACE, RESOURCE if any).
- **Council macro goals**
  - Supports MAP_EXTERIOR, future site selection for facilities.


### 4.2 Inventory & stores details

#### 4.2.1 INVENTORY_STORES

- **Purpose**
  - Unseal crates, catalog contents, update simple stock ledgers.
- **Preferred traits**
  - INT/WIL for systematic work; STR/AGI for handling crates.
- **Typical actions**
  - OPEN_CRATE, READ_LABEL, LOG_ITEM, MOVE_TO_STORAGE_AREA.
- **Typical episodes produced**
  - `CRATE_OPENED` (OBJECT/RESOURCE).
  - `RESOURCE_STOCKED` (RESOURCE, PLACE).
- **Council macro goals**
  - Supports INVENTORY_STORES, SECURE_WATER_HANDLING,
    BRING_FOODLINE_ONLINE, SUIT_MAINTENANCE planning.

#### 4.2.2 STORES_STEWARD

- **Purpose**
  - Manage access at key storerooms; avoid chaos and theft.
- **Preferred traits**
  - High WIL/CHA, fairness-leaning personalities, low corruption tendency.
- **Typical actions**
  - CHECK_REQUEST, APPROVE_ISSUE, DENY_ISSUE, RECORD_WITHDRAWAL.
- **Typical episodes produced**
  - `QUEUE_DENIED` / `QUEUE_SERVED` (PLACE, fairness tags).
  - `DISPUTE_AT_STORES` (PERSON/PLACE).
- **Council macro goals**
  - Supports INVENTORY_STORES, establishes norms of fairness.


### 4.3 Life support & environment details

#### 4.3.1 ENV_CONTROL_DETAIL

- **Purpose**
  - Install/tune fans, filters, ducts, dehumidifiers; manage air and humidity.
- **Preferred traits**
  - TECH-friendly skills; moderate INT; patience.
- **Typical actions**
  - INSTALL_DEVICE, ADJUST_FLOW, MEASURE_AIR_QUALITY.
- **Typical episodes produced**
  - `ENV_NODE_TUNED` (PLACE, better comfort/safety tags).
  - `ENV_NODE_FAILURE` (PLACE, risk tags).
- **Council macro goals**
  - Supports STABILIZE_ENVIRONMENT.

#### 4.3.2 SUIT_INSPECTION_DETAIL

- **Purpose**
  - Inspect colonist suits; apply minor repairs; mark critical defects.
- **Preferred traits**
  - Fine motor skills; AGI; detail-oriented INT/WIL.
- **Typical actions**
  - INSPECT_SUIT, PATCH_SUIT, FLAG_FOR_REPLACEMENT.
- **Typical episodes produced**
  - `SUIT_TUNED` (PERSON/OBJECT).
  - `SUIT_FAILURE_NEAR_MISS` (PERSON, high threat).
- **Council macro goals**
  - Supports STABILIZE_ENVIRONMENT, later SUIT_MAINTENANCE_FACILITY.


### 4.4 Food & water details

#### 4.4.1 FOOD_PROCESSING_DETAIL

- **Purpose**
  - Turn raw stocks into edible rations; run early mess halls.
- **Preferred traits**
  - Steady, hygiene-aware; moderate CON; low aversion to repetitive work.
- **Typical actions**
  - PREP_FOOD, COOK_BATCH, SERVE_RATION, CLEAN_STATION.
- **Typical episodes produced**
  - `FOOD_SERVED` (PLACE/RESOURCE).
  - `FOOD_SHORTAGE_EPISODE` or `QUEUE_STARVED` under stress.
- **Council macro goals**
  - Supports BRING_FOODLINE_ONLINE.

#### 4.4.2 WATER_HANDLING_DETAIL

- **Purpose**
  - Manage barrels, purification/conditioning, basic water logistics.
- **Preferred traits**
  - Responsibility, low corruption, reasonable physical strength.
- **Typical actions**
  - MOVE_BARREL, MARK_POTABLE, MARK_NONPOTABLE, MONITOR_LEAK.
- **Typical episodes produced**
  - `BARREL_MOVED`, `LEAK_FOUND`, `WATER_LOSS_INCIDENT`.
- **Council macro goals**
  - Supports SECURE_WATER_HANDLING, informs later barrel cascade design.


### 4.5 Knowledge & coordination details

#### 4.5.1 SCRIBE_DETAIL

- **Purpose**
  - Record scout findings, inventory results, incidents; maintain maps/ledgers.
- **Preferred traits**
  - High INT/WIL, literacy; calm temperament.
- **Typical actions**
  - RECORD_REPORT, UPDATE_MAP, UPDATE_LEDGER.
- **Typical episodes produced**
  - `REPORT_RECEIVED`, `MAP_UPDATED`, `LEDGER_UPDATED`.
- **Council macro goals**
  - Supports ESTABLISH_RECORDKEEPING; provides backbone for protocols.


#### 4.5.2 DISPATCH_DETAIL

- **Purpose**
  - Translate proto-council priorities into assignments at the hall.
- **Preferred traits**
  - CHA, situational awareness of pods, sense of fairness.
- **Typical actions**
  - INTERVIEW_AGENT, SELECT_WORK_DETAIL_TYPE, ISSUE_ASSIGNMENT.
- **Typical episodes produced**
  - `ASSIGNMENT_GIVEN`, `ASSIGNMENT_DISPUTE`.
- **Council macro goals**
  - Supports all others by routing labor where it is most needed.


## 5. Work detail config shape (MVP)

To make this taxonomy executable, each `WorkDetailType` should have a small
configuration record, e.g.:

- `id`: enum value (`SCOUT_INTERIOR`, `INVENTORY_STORES`, …)
- `category`: `"scout" | "inventory" | "env" | "food" | "water" | "coordination"`
- `description`: human-readable purpose.
- `preferred_attributes`: hints like `{"END": +1, "INT": +1}`.
- `preferred_traits`: personality hints (e.g. brave, fair, methodical).
- `risk_level`: `"low" | "medium" | "high"`.
- `typical_verbs`: list of episode verbs this job tends to emit.
- `macro_goals`: which proto-council macro goals this detail serves.
- `default_team_size`: how many agents to assign by default.
- `typical_duration_ticks`: rough expected work window.

This config supports:

- The **assignment hall** choosing a good detail for an incoming agent.
- The **proto council** expressing “we want N of this detail” instead of
  micromanaging individuals.


## 6. Integration points (runtime)

MVP wiring plan (high-level):

1. **Define `WorkDetailType` enum** and a static registry of configs matching
   the catalog above.
2. **Extend proto-council goals** to include “desired headcounts per detail”,
   e.g. `desired_details: Dict[WorkDetailType, int]`.
3. **Extend assignment hall behavior**:
   - when an agent reaches the assignment hall with “needs assignment” goal,
   - pick a `WorkDetailType` based on:
     - current council demand (need vs filled),
     - the agent’s attributes/personality,
     - perhaps fairness (avoid always giving the same agent the risky jobs).
   - push a new **work-detail goal** onto the agent’s goal stack, tagged with
     the chosen `WorkDetailType`.
4. **Let existing movement / queue logic handle** how the job is carried out:
   - details specify which facilities/locations to route to,
   - episodes produced along the way are already captured by the episode system.

Later documents can refine this into actual job scripts, scheduling, and
promotion tracks. For this MVP, D-RUNTIME-0212’s main role is to pin down the
initial job vocabulary the sim will speak at wakeup.
