---
title: Suit_Wear_and_Repair_v1_Implementation_Checklist
doc_id: D-RUNTIME-0254
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-24
depends_on:
  - D-AGENT-0020     # Canonical Agent Model (or current agent schema doc)
  - D-RUNTIME-0230   # Cadence Contract (physio/psy decay cadence)
  - D-RUNTIME-0243   # Event → Memory Router v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0253   # Maintenance & Wear v1
---

# Suit Wear & Repair v1 — Implementation Checklist

Branch name: `feature/suit-wear-repair-v1`

Goal: introduce **agent suit wear** as the personal-scale entropy loop that:
- makes exploration/work meaningfully risky,
- feeds into physio penalties (hydration/heat protection),
- creates repair demand that ties into materials + facilities + maintenance,
- generates memory/beliefs about “unsafe routes”, “reliable workshops”, and “cheap repairs”.

v1 is deliberately minimal: one suit per agent, a small wear meter, and a deterministic repair path.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic wear.** No random per-tick wear; use deterministic schedules and/or hashed draws keyed by IDs and day/tick.
2. **Bounded compute.** Suit wear updates run on cadence (daily or coarse), not per tick for all agents.
3. **Feature flag default OFF.** With flag OFF, agent behavior unchanged.
4. **Save/Load safe.** Suit state serializes; old snapshots load.
5. **Uses economy.** Repairs consume materials and require a facility + staffing (workshop).
6. **Tested.** Wear, threshold events, repair workflow, snapshot roundtrip.

---

## 1) Concept model

### 1.1 Suit as equipment
Each agent has a suit with:
- `integrity` in [0,1]
- `seal_quality` in [0,1] (optional v1; can equal integrity)
- `filter_quality` in [0,1] (optional v1)
- `last_repair_day`
- `repair_needed` boolean

v1 can collapse to just `integrity` + `repair_needed`.

### 1.2 Why it matters
Suit integrity affects:
- ambient hydration/heat decay multipliers (from Cadence Contract),
- risk of incidents during courier travel/exploration (optional),
- ability to perform certain jobs (optional).

v1 mechanical effect recommendation:
- when integrity < 0.6, apply a small penalty multiplier to hydration/heat stress.
- when integrity < 0.3, agent becomes “high risk” and decision hooks should prioritize repair.

---

## 2) Implementation Slice A — Data structures + config

Create module: `src/dosadi/agent/suits.py` (or `src/dosadi/agent/equipment.py`)

**Deliverables**
- `@dataclass(slots=True) class SuitState:`
  - `integrity: float = 1.0`
  - `repair_needed: bool = False`
  - `last_repair_day: int = 0`
  - `notes: dict[str, object] = field(default_factory=dict)`

- Ensure Agent dataclass includes:
  - `suit: SuitState = field(default_factory=SuitState)`

Create runtime module: `src/dosadi/runtime/suit_wear.py`

- `@dataclass(slots=True) class SuitWearConfig:`
  - `enabled: bool = False`
  - `wear_per_day_base: float = 0.0025`
  - `wear_per_day_courier_mult: float = 1.4`
  - `wear_per_day_worker_mult: float = 1.2`
  - `threshold_warn: float = 0.60`
  - `threshold_repair: float = 0.40`
  - `threshold_critical: float = 0.25`
  - `max_repairs_per_day: int = 8`
  - `repair_duration_days: int = 1`
  - `repair_facility_kind: str = "WORKSHOP"`
  - `deterministic_salt: str = "suit-wear-v1"`
  - `apply_physio_penalties: bool = True`
  - `warn_event_enabled: bool = True`

- `@dataclass(slots=True) class SuitWearState:`
  - `last_run_day: int = -1`
  - `repairs_started_today: int = 0`

Add to world:
- `world.suit_cfg`, `world.suit_state`

Snapshot them.

---

## 3) Implementation Slice B — Deterministic wear update (cadence-aware)

We do not iterate all agents blindly every tick.

### B1. Candidate set selection
Use a bounded “agents with activity” list if available:
- couriers (agents assigned to LOGISTICS_COURIER / LOGISTICS_ESCORT)
- active workers (agents assigned to construction/maintenance)
- optionally: awake cohort during focus sessions

If you *must* touch all agents:
- do it daily, not per tick, and keep agent count small in early scenarios.

Implement:
- `def iter_suit_wear_candidates(world) -> Iterable[str]`
  - returns deterministic sorted list of agent_ids in active assignments
  - bounded by a cap (e.g., first 500) to prevent explosions; safe for v1.

### B2. Wear increment per day
For each candidate agent:
- base delta = wear_per_day_base
- multiply by role:
  - courier mult if assigned courier/escort
  - worker mult if assigned construction/maintenance
- optional deterministic jitter:
  - `j = hashed_unit_float("suit", salt, agent_id, str(day))`
  - delta *= (0.9 + 0.2*j)
- apply:
  - `agent.suit.integrity = clamp(agent.suit.integrity - delta, 0, 1)`

### B3. Threshold flags + events
If integrity crosses:
- warn threshold → emit `SUIT_WEAR_WARN` (once per crossing)
- repair threshold → set `repair_needed=True` and emit `SUIT_REPAIR_NEEDED`
- critical threshold → emit `SUIT_CRITICAL` and optionally schedule urgent repair

Use “edge detection” to avoid spamming events:
- store `notes["last_bucket"]` or compare previous day integrity.

---

## 4) Implementation Slice C — Repair workflow (jobs + materials)

Repairs should reuse the maintenance/job concepts, but a separate ledger keeps it simple in v1.

### C1. Repair job ledger
In `suit_wear.py` add:
- `@dataclass(slots=True) class SuitRepairJob:`
  - `job_id: str`
  - `agent_id: str`
  - `facility_id: str`
  - `created_day: int`
  - `status: str`          # OPEN, WAITING_PARTS, IN_PROGRESS, DONE
  - `bom: dict[Material,int]`
  - `pending_delivery_ids: list[str]`
  - `assigned_staff_ids: list[str]`
  - `progress_days: int = 0`

- `@dataclass(slots=True) class SuitRepairLedger:`
  - `jobs: dict[str, SuitRepairJob]`
  - `open_job_by_agent: dict[str, str]`
  - `def signature(self) -> str`

Store on world:
- `world.suit_repairs: SuitRepairLedger`

Snapshot it.

### C2. BOM for suit repair (v1)
Small and consistent:
- `{SEALANT: 1, FABRIC: 1, FASTENERS: 1}`

### C3. Facility selection
Choose a workshop deterministically:
- iterate facilities of kind WORKSHOP by facility_id
- pick first operational workshop (not down) in same ward/node if available (optional), else first overall.

### C4. Parts deliveries
If facility inventory cannot afford BOM:
- request delivery from depots (like maintenance/material economy)
- avoid duplicate deliveries

### C5. Staffing
Use WorkforceLedger:
- assign 1 staff member (or min_staff) to the repair job:
  - `AssignmentKind.SUIT_REPAIR_TECH` (new)
- select deterministically from idle staff; bounded cap; preserve reserves

### C6. Progress and completion
When BOM available and staff assigned:
- status IN_PROGRESS
- each day progress_days += 1
- when progress_days >= repair_duration_days:
  - consume BOM from facility inventory
  - set agent suit integrity = 1.0 (or 0.9 if you want “used but fixed”)
  - set repair_needed False, last_repair_day = day
  - release repair tech assignment
  - job DONE
  - emit `SUIT_REPAIRED`

---

## 5) Implementation Slice D — Physio integration (minimal)

If apply_physio_penalties:
- update the physio daily update to read suit integrity and apply a multiplier:
  - if integrity < 0.6: hydration_decay *= 1.05
  - if integrity < 0.4: hydration_decay *= 1.15 and heat_stress *= 1.10
  - if integrity < 0.25: hydration_decay *= 1.30 and heat_stress *= 1.20

Do not scan all agents to apply this; apply only when agent is updated anyway (awake agents, candidates, or during existing physio decay loop if it already touches all agents).

---

## 6) Event → Memory → Belief hooks

Emit events:
- `SUIT_WEAR_WARN`
- `SUIT_REPAIR_NEEDED`
- `SUIT_CRITICAL`
- `SUIT_REPAIR_STARTED`
- `SUIT_REPAIRED`

Router should create crumbs:
- `repair-needed`
- `workshop-reliability:{facility_id}` (from repair outcomes)
- `route-wear:{edge_key}` (optional if attributing wear to travel edges in focus)

Belief formation can then influence decisions:
- avoid harsh routes if suit is fragile,
- prefer certain workshops.

---

## 7) Pipeline wiring

Run daily (when enabled):
1) suit wear update (candidates)
2) open repair jobs for repair_needed agents (bounded max_repairs_per_day)
3) request parts deliveries
4) advance repair jobs and complete

Suggested placement:
- after materials production (so parts exist), before decision hooks (so decisions can react).

---

## 8) Telemetry

Counters:
- `metrics["suits"]["wear_candidates"]`
- `metrics["suits"]["warnings"]`
- `metrics["suits"]["repairs_needed"]`
- `metrics["suits"]["repairs_started"]`
- `metrics["suits"]["repairs_done"]`

---

## 9) Tests (must-have)

Create `tests/test_suit_wear_repair.py`.

### T1. Flag off = baseline
- enabled=False → no suit state changes.

### T2. Deterministic wear
- same world clone → same integrity signatures after day update.

### T3. Threshold events + flags
- set integrity near thresholds; run update; repair_needed set and events emitted once.

### T4. Repair job creation bounded
- many agents needing repair; ensure max_repairs_per_day respected deterministically.

### T5. Repair completes with parts + staff
- provision workshop + materials; run pipeline; suit restored; job DONE; assignments released.

### T6. No duplicate deliveries
- run repair job logic twice; only one pending delivery set.

### T7. Snapshot roundtrip mid-repair
- save after job created; load; complete; identical final signature.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add suit state to Agent
- Create `src/dosadi/agent/suits.py` (or equipment module) with SuitState dataclass
- Add `agent.suit` with safe default and snapshot support

### Task 2 — Add suit wear runtime + ledgers
- Create `src/dosadi/runtime/suit_wear.py` with SuitWearConfig/State, job ledger
- Add `world.suit_cfg`, `world.suit_state`, `world.suit_repairs` to snapshots

### Task 3 — Deterministic wear update
- Implement candidate selection from assignments (bounded)
- Apply deterministic wear decrement and emit threshold events (edge-detected)

### Task 4 — Repair workflow
- Create repair jobs for repair_needed agents (bounded)
- Select workshop deterministically
- Request parts deliveries (avoid duplicates)
- Assign repair tech via WorkforceLedger
- Advance and complete jobs, consuming BOM and restoring integrity

### Task 5 — Physio integration (minimal)
- Apply suit-based decay multipliers where physio updates already occur (avoid new global scans)

### Task 6 — Tests + telemetry
- Add `tests/test_suit_wear_repair.py` implementing T1–T7
- Add metrics counters and events

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=False: no behavior change.
- With enabled=True:
  - active agents accumulate deterministic suit wear,
  - repair jobs open and complete via workshops + materials + staffing,
  - suit integrity affects physio decay minimally,
  - events flow through router → beliefs,
  - save/load works mid-repair.

---

## 12) Next slice after this

**Exploration & Discovery v1** (scouts learn new nodes/resources, update SurveyMap, and seed expansion),
now that suits and maintenance make scouting meaningfully costly.
