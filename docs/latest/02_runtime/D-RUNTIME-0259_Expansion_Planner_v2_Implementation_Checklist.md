---
title: Expansion_Planner_v2_Implementation_Checklist
doc_id: D-RUNTIME-0259
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0234   # Survey Map v1
  - D-RUNTIME-0236   # Expansion Planner v1
  - D-RUNTIME-0239   # Scout Missions v1
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0253   # Maintenance & Wear v1
  - D-RUNTIME-0254   # Suit Wear & Repair v1
  - D-RUNTIME-0255   # Exploration & Discovery v1
  - D-RUNTIME-0256   # Resource Extraction Sites v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
---

# Expansion Planner v2 — Implementation Checklist

Branch name: `feature/expansion-planner-v2`

Goal: upgrade the planner from “build something somewhere” into a deterministic strategic loop that:
- chooses *what* to build (depots, workshops, recyclers, corridors, repairs),
- chooses *where* based on discovered resources, corridor risk, supply flow, and project blockage,
- schedules scouts when information is missing,
- uses real signals: shortages, downtime rate, suit attrition, extraction yields, and blocked projects,
- remains bounded and testable.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same plan outputs.
2. **Bounded.** Evaluate only top-K candidates per day; no global scans over all nodes.
3. **Explainable.** Every chosen action has a score breakdown saved for debugging.
4. **Feature-flagged.** v2 logic behind config; v1 planner remains available.
5. **Tested.** Determinism, bounds, and correct preference in simple scenarios.
6. **Save/Load safe.** New planner state defaults; old snapshots load.

---

## 1) Planner output types (v2 actions)

Define `PlannerActionKind`:
- `BUILD_DEPOT`
- `BUILD_WORKSHOP`
- `BUILD_RECYCLER`
- `BUILD_CORRIDOR_EDGE` (optional v2.1)
- `SCHEDULE_SCOUT_MISSION`
- `INCREASE_ESCORT_LEVEL` (optional, ties into escort protocols)
- `ALLOCATE_MAINTENANCE_CREW` (optional; workforce tuning)

v2 core: BUILD_DEPOT / BUILD_WORKSHOP / BUILD_RECYCLER / SCHEDULE_SCOUT_MISSION.

Each action yields a concrete project/mission request.

---

## 2) Implementation Slice A — Config + state + scoring record

Create `src/dosadi/runtime/expansion_planner_v2.py`

**Deliverables**
- `@dataclass(slots=True) class ExpansionPlannerV2Config:`
  - `enabled: bool = False`
  - `top_k_nodes: int = 25`
  - `top_k_actions: int = 8`
  - `max_actions_per_day: int = 2`
  - `min_days_between_actions: int = 3`
  - `shortage_lookback_days: int = 5`
  - `downtime_lookback_days: int = 14`
  - `suit_attrition_lookback_days: int = 7`
  - `prefer_same_ward: bool = True`
  - `deterministic_salt: str = "planner-v2"`
  - scoring weights:
    - `w_shortage: float = 1.0`
    - `w_blocked_projects: float = 0.9`
    - `w_extraction: float = 1.1`
    - `w_flow_distance: float = 0.6`
    - `w_risk: float = 0.7`
    - `w_downtime: float = 0.5`
    - `w_suit_cost: float = 0.4`
    - `w_information: float = 0.8`

- `@dataclass(slots=True) class ExpansionPlannerV2State:`
  - `last_action_day: int = -10`
  - `actions_taken_today: int = 0`
  - `last_plan_signature: str = ""`

- `@dataclass(slots=True) class ScoreBreakdown:`
  - `total: float`
  - `terms: dict[str, float]`
  - `details: dict[str, object]`

- `@dataclass(slots=True) class PlannedAction:`
  - `kind: str`
  - `target_node_id: str | None`
  - `facility_kind: str | None`
  - `payload: dict[str, object]`
  - `score: ScoreBreakdown`

Add to world:
- `world.plan2_cfg`, `world.plan2_state`

Snapshot them.

---

## 3) Implementation Slice B — Signal extraction (bounded, cheap)

Implement helpers that produce small, bounded signal sets.

### B1. Shortage signal
From depot policy + construction pipeline:
- gather top-K “missing materials” across:
  - projects currently WAITING_MATERIALS (v2 pipeline)
  - depots below min/target levels (stockpile policy)

Return:
- `shortages: list[(material, severity, depot_id)]` sorted deterministically.

Severity suggestion:
- normalized deficit / target (0..1) with clamps.

### B2. Blocked projects signal
From construction pipeline:
- count blocked projects by node/ward and reason:
  - materials vs staff vs incident

Return:
- `blocked_by_node: dict[node_id, float]` bounded to top_k_nodes.

### B3. Extraction yield signal
From extraction sites:
- compute expected yield score per node (based on richness and yield tables)
- only for nodes that have sites

Return:
- `yield_by_node: dict[node_id, float]` bounded to top_k_nodes.

### B4. Downtime signal
From telemetry/events (maintenance + incident):
- compute downtime rate per facility or node (lookback window)
If telemetry not yet easily queriable, approximate using:
- facility.down_until_day and job history (bounded)

Return:
- `downtime_by_node: dict[node_id, float]` bounded.

### B5. Suit attrition signal
From suit wear / repair system:
- count repairs needed/done by corridor/node (if you track) or globally.
v2 minimal:
- compute a global “suit stress index” as repairs_needed / active_agents.

Return:
- `suit_stress: float`

### B6. Information signal (need scouts)
If shortages persist and there are frontier nodes undiscovered:
- create signal that encourages scout missions.

Return:
- `need_information: bool` plus frontier candidates list bounded.

All helpers must be deterministic and capped.

---

## 4) Implementation Slice C — Candidate nodes selection

We only score a small set of nodes.

Candidate set union (then top_k_nodes):
- nodes with extraction yields
- nodes with blocked projects
- depots’ node locations
- top frontier nodes (for scouting)

Tie-break:
- deterministic sort by (score_proxy desc, node_id).

If node locations are not tracked on facilities yet:
- treat depot facility node as its construction node, or use ward id.

---

## 5) Implementation Slice D — Action scoring functions

Implement scorers that return ScoreBreakdown.

### D1. BUILD_DEPOT at node
Terms:
- + extraction yield nearby (w_extraction)
- + shortages severity (w_shortage) if node is on route to depot
- + blocked projects nearby (w_blocked_projects)
- - distance penalty from existing depot coverage (w_flow_distance)
- - risk penalty from hazard edges (w_risk)
- - downtime penalty if node has unreliable facilities (w_downtime)

### D2. BUILD_WORKSHOP at node
Terms:
- + shortages in FASTENERS/SEALANT/FABRIC
- + blocked projects missing those materials
- + proximity to scrap/salvage
- - downtime penalty
- - risk penalty

### D3. BUILD_RECYCLER at node
Terms:
- + shortages in SCRAP_METAL/PLASTICS
- + proximity to SCRAP_FIELD yields
- - downtime penalty
- - risk penalty

### D4. SCHEDULE_SCOUT_MISSION
Terms:
- + need_information (w_information)
- + persistent shortages without enough yield sites known
- - suit stress penalty (w_suit_cost) if suits are in bad shape (don’t explore if suits failing)
- - risk (if frontier routes are dangerous)

Each scorer must fill:
- terms dict with named terms
- details dict with key facts (top shortages, chosen source nodes, etc.)

---

## 6) Implementation Slice E — Plan selection + execution hooks

### E1. Generate actions
For each candidate node:
- compute depot/workshop/recycler scores (bounded)
For scouting:
- compute at most N scout action candidates

Collect into list, sort by:
- total score desc
- kind order (stable)
- node_id asc

### E2. Select up to max_actions_per_day
Respect cooldown:
- if day - last_action_day < min_days_between_actions: produce no actions (or 1 max)
Update plan2_state on action execution.

### E3. Execute actions deterministically
Tie into existing systems:
- BUILD_* → create construction project via Construction Projects/Pipeline v2
- SCHEDULE_SCOUT_MISSION → create scout mission targeting frontier node

Emit:
- `PLANNER_V2_ACTION_CHOSEN` with score breakdown (serialized compactly)

---

## 7) Debuggability: store last plan

Save last plan’s top actions (e.g., 5) into state:
- `world.plan2_state.last_plan_signature`
- `world.plan2_state.last_actions: list[PlannedAction]` (optional; can be stored in telemetry instead)

If storing rich objects is hard for snapshots, store a compact JSON-ish dict.

---

## 8) Telemetry + events

Counters:
- `metrics["planner_v2"]["actions_considered"]`
- `metrics["planner_v2"]["actions_taken"]`
- `metrics["planner_v2"]["scout_scheduled"]`
- `metrics["planner_v2"]["build_depot"]`, `build_workshop`, `build_recycler`

Events:
- `PLANNER_V2_ACTION_CHOSEN` (kind, node_id, score_terms)
- `PLANNER_V2_SKIPPED_COOLDOWN`

---

## 9) Tests (must-have)

Create `tests/test_expansion_planner_v2.py`.

### T1. Deterministic plan
- same world clone → same chosen actions and scores.

### T2. Shortage drives workshop
- create FASTENERS shortage → planner chooses BUILD_WORKSHOP.

### T3. Scrap drives recycler
- create SCRAP_FIELD site + scrap shortage → chooses BUILD_RECYCLER near it.

### T4. Extraction drives depot
- high yield node discovered → chooses BUILD_DEPOT at/near it.

### T5. Cooldown respected
- last_action_day recent → no new action.

### T6. Bound enforcement
- create many candidates; ensure top_k_nodes and top_k_actions caps honored.

### T7. Snapshot roundtrip
- save after plan chosen; load; re-run; stable action selection.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add v2 planner module + world state
- Create `src/dosadi/runtime/expansion_planner_v2.py` with config/state/score breakdown/action types
- Add `world.plan2_cfg`, `world.plan2_state` to snapshots

### Task 2 — Implement signal extraction helpers (bounded)
- shortages from depots/projects
- blocked projects summary
- extraction yield per node
- downtime approximation
- suit stress index
- information/frontier need

### Task 3 — Candidate selection + scoring
- build bounded candidate node set
- implement scorers for depot/workshop/recycler/scout with score breakdown

### Task 4 — Action selection + execution
- select up to max_actions_per_day, obey cooldown
- emit PLANNER_V2_ACTION_CHOSEN event with score terms
- execute by creating construction projects or scout missions

### Task 5 — Tests + telemetry
- add `tests/test_expansion_planner_v2.py` implementing T1–T7
- add metrics counters

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=False: v1 planner remains unchanged.
- With enabled=True:
  - planner chooses actions deterministically using real signals,
  - bounded candidate scoring prevents blowups,
  - actions are explainable via score breakdown,
  - cooldown prevents thrash,
  - save/load works.

---

## 12) Next slice after this

**Telemetry & Admin Views v2** (a “Why is it stuck?” panel + flow maps),
so you can see planner motives, depot shortages, and project blocks at a glance.
