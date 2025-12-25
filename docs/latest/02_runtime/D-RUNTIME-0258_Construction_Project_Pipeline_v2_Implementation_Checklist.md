---
title: Construction_Project_Pipeline_v2_Implementation_Checklist
doc_id: D-RUNTIME-0258
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0238   # Logistics Delivery v1
  - D-RUNTIME-0240   # Construction Workforce Staffing v1
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0250   # Escort Protocols v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0253   # Maintenance & Wear v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
---

# Construction Project Pipeline v2 — Implementation Checklist

Branch name: `feature/construction-pipeline-v2`

Goal: upgrade construction from “a job that eventually finishes” into a legible, testable pipeline:
- staging inventory at the project site,
- partial deliveries and incremental BOM satisfaction,
- explicit blocked reasons (materials, staff, access, safety, downtime),
- deterministic stage transitions and progress,
- telemetry + admin views to answer: *why is this stuck?*

This is the slice that makes empire growth debuggable.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same stage transitions and delivery requests.
2. **Feature flag default OFF** for any behavior-altering changes; or gate v2 logic behind config.
3. **Bounded compute.** No per-tick scans of all projects; evaluate projects on cadence and/or via due queues.
4. **No spam.** Do not create duplicate material requests each evaluation.
5. **Save/Load safe.** New fields default; old snapshots load.
6. **Tested.** Block reasons, partial deliveries, determinism, snapshot roundtrip.

---

## 1) Concept model

### 1.1 Project site inventory (“staging”)
Each project has a staging inventory owner:
- `project:{project_id}`

Materials can accumulate here across days via deliveries.

### 1.2 Stages become state machines
Each stage can be in a state:
- `READY` → can start if requirements met
- `WAITING_MATERIALS` → missing BOM, pending deliveries
- `WAITING_STAFF` → no workforce assigned
- `BLOCKED_ACCESS` → route/safety constraint (optional v2)
- `PAUSED_INCIDENT` → incident downtime
- `IN_PROGRESS` → building days accumulate
- `DONE` → stage complete

Project progresses stage-by-stage deterministically.

### 1.3 Block reason reporting
Every project maintains a “current block reason” with structured detail:
- code + human string + key/value fields

This is printed by CLI/admin dashboard.

---

## 2) Implementation Slice A — Schema upgrades

Locate your project model (likely `src/dosadi/runtime/construction_projects.py` or similar).

Add/extend:

### A1. StageState enum
- `class StageState(Enum): READY, WAITING_MATERIALS, WAITING_STAFF, PAUSED_INCIDENT, IN_PROGRESS, DONE`

### A2. BlockReason dataclass
- `@dataclass(slots=True) class BlockReason:`
  - `code: str`         # e.g. "MATERIALS", "STAFF", "INCIDENT"
  - `msg: str`
  - `details: dict[str, object] = field(default_factory=dict)`

### A3. Project fields (safe defaults)
- `stage_state: StageState = READY`
- `block_reason: BlockReason | None = None`
- `staging_owner_id: str = "project:{project_id}"`  # set on create
- `pending_material_delivery_ids: list[str] = field(default_factory=list)`
- `progress_days_in_stage: int = 0`
- `last_evaluated_day: int = -1`

Snapshot safe defaults are mandatory.

---

## 3) Implementation Slice B — Partial delivery & BOM satisfaction

### B1. BOM evaluation helper
Add helper:
- `def bom_missing(inv: Inventory, bom: dict[Material,int]) -> dict[Material,int]`
  - returns missing quantities (qty - inv.get)

### B2. Request materials only for missing
If missing is non-empty:
- stage_state = WAITING_MATERIALS
- set block_reason with missing dict
- request deliveries for missing materials (or top-K materials)

v2 policy:
- allow partial delivery: request missing items even if some already present
- do not consume materials until stage starts (or consume on start)

### B3. Avoid duplicates
Use a per-stage key to track pending requests:
- `project.pending_material_delivery_ids`
- optionally `project.notes["pending_for_stage_id"]`

Before requesting:
- if there is already at least one pending delivery for this stage, do not request again.
Better: track per-material pending amount; but v2 can start with coarse “one request per stage”.

---

## 4) Implementation Slice C — Workforce gating

If materials sufficient:
- check workforce assignment for project/stage:
  - if insufficient: WAITING_STAFF with reason
  - else: READY to start (or transition to IN_PROGRESS)

Ensure deterministic staff selection:
- choose idle workers in sorted agent_id order
- cap assignment changes/day to prevent thrash

---

## 5) Implementation Slice D — Incident gating

If Incident Engine marks project site “paused” (downtime):
- stage_state = PAUSED_INCIDENT
- block_reason = INCIDENT
- do not advance progress days

This should be evaluated before starting/in-progress increments.

---

## 6) Implementation Slice E — Progress + completion rules

When stage_state is IN_PROGRESS:
- each day: progress_days_in_stage += 1
- if progress_days_in_stage >= stage.duration_days:
  - mark stage DONE
  - advance to next stage:
    - reset progress_days_in_stage = 0
    - stage_state = READY
    - clear block_reason

Materials consumption policy (recommended v2):
- consume stage BOM **when stage transitions from READY → IN_PROGRESS**
  - apply_bom on staging inventory
  - if consumption fails (should not if checked), treat as bug/test failure

Completion creates facility etc. as previously.

---

## 7) Implementation Slice F — Scheduling / performance

Avoid scanning all projects daily if project count grows.

v2 scheduling:
- maintain a “due projects” min-heap keyed by next_evaluate_day
- when a project is blocked waiting materials, set next evaluate to “when a delivery completes” OR day+1
- when in progress, evaluate daily until completion
- when done, remove from heap

If you don’t have the heap infra yet, v2 can evaluate all projects daily (small N), but add TODO and keep bounded tests.

---

## 8) Telemetry + events

Emit events:
- `PROJECT_STAGE_BLOCKED` (project_id, stage_id, reason_code, details)
- `PROJECT_STAGE_STARTED`
- `PROJECT_STAGE_PROGRESS` (optional)
- `PROJECT_STAGE_DONE`
- `PROJECT_DONE`

Counters:
- `metrics["projects"]["blocked_materials"]`
- `metrics["projects"]["blocked_staff"]`
- `metrics["projects"]["blocked_incident"]`
- `metrics["projects"]["deliveries_requested"]`
- `metrics["projects"]["stages_completed"]`

---

## 9) Admin/CLI display (minimal v2)

Update AdminDashboardCLI or ProjectTimelineCLI to show:
- project_id, kind, node/ward
- current stage + stage_state
- block reason code + key details (missing materials summary)
- pending deliveries count
- days progressed in stage

This is key for your “what’s stuck?” question.

---

## 10) Save/Load requirements

Snapshot must include:
- new stage_state fields
- block_reason (serialize safely; if complex, store as primitives)
- pending delivery IDs
- progress_days_in_stage
- last_evaluated_day
- staging inventories are already in InventoryRegistry

Old snapshots:
- default stage_state READY, progress 0, no block reason.

---

## 11) Tests (must-have)

Create `tests/test_construction_pipeline_v2.py`.

### T1. Deterministic progression
- clone world; run days; stage transitions identical.

### T2. Blocks on missing materials with reason
- no materials → WAITING_MATERIALS and missing dict populated.

### T3. Partial deliveries accumulate
- deliver some materials; still blocked with reduced missing; no duplicate requests.

### T4. Starts when materials + staff present
- once BOM satisfied and workers assigned → stage starts and consumes BOM.

### T5. Incident pause blocks progress
- mark project paused; verify progress does not increment and reason set.

### T6. Completion advances to next stage
- after duration days, stage done → next stage ready, progress reset.

### T7. Snapshot roundtrip mid-block
- save in WAITING_MATERIALS with pending deliveries; load; continue; identical final signature.

---

## 12) Codex Instructions (verbatim)

### Task 1 — Schema upgrades
- Add StageState enum and BlockReason dataclass
- Extend Project model with stage_state, block_reason, staging_owner_id, pending delivery ids, progress_days, last_evaluated_day
- Ensure snapshot compatibility

### Task 2 — BOM missing + partial delivery logic
- Implement `bom_missing(...)`
- Set WAITING_MATERIALS block reason and request deliveries only for missing items
- Avoid duplicate requests (one per stage or per-material pending tracking)

### Task 3 — Workforce + incident gating
- Add WAITING_STAFF reason if no workers assigned
- Add PAUSED_INCIDENT reason if project paused

### Task 4 — Progress + completion
- Consume BOM on stage start
- Increment progress daily
- Advance stages deterministically

### Task 5 — Admin views + telemetry
- Display stage_state and block_reason in CLI/dashboard
- Emit events and counters

### Task 6 — Tests
- Add `tests/test_construction_pipeline_v2.py` implementing T1–T7

---

## 13) Definition of Done

- `pytest` passes.
- Projects have staging inventories and can accept partial deliveries.
- Projects expose explicit block reasons and do not spam requests.
- Stage progression is deterministic and debuggable via CLI.
- Save/load works mid-stage and mid-block.

---

## 14) Next slice after this

**Expansion Planner v2** (use real signals: shortages, downtime rate, suit attrition, discovered yields)
to make the empire growth feel strategic and self-consistent.
