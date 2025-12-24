---
title: Maintenance_and_Wear_v1_Implementation_Checklist
doc_id: D-RUNTIME-0253
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-24
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0243   # Event → Memory Router v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
---

# Maintenance & Wear v1 — Implementation Checklist

Branch name: `feature/maintenance-wear-v1`

Goal: make scarcity *inevitable* by introducing deterministic **wear** and **maintenance**:
- facilities degrade and require parts to stay operational,
- suits (or basic equipment) degrade (optional v1),
- maintenance requests generate deliveries and staffing,
- downtime becomes a regular rhythm that affects production, logistics, and expansion.

This provides the “entropy engine” that will later feed black markets, corruption, and rebellion.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** No random decay; use hashed draws or fixed schedules keyed by IDs and day.
2. **Bounded compute.** Wear updates run once per day; operate only over existing facilities (and optionally a bounded agent subset).
3. **Feature flag default OFF.** With flag OFF, existing behavior unchanged.
4. **Save/Load safe.** Wear state serializes; old snapshots load with defaults.
5. **Integrates with economy.** Maintenance consumes real materials and triggers real deliveries.
6. **Tested.** Downtime, parts consumption, determinism, snapshot roundtrip.

---

## 1) Concept model

### 1.1 Wear state per facility
Each facility has:
- a wear meter (0..1 or 0..100)
- a maintenance threshold (when crossed, maintenance is required)
- a downtime mode when maintenance is overdue or cannot be performed

### 1.2 Maintenance job
A maintenance job is a small “project-like” unit:
- targets one facility
- has a parts BOM (materials)
- requires staffing (maintenance crew)
- completes after N days or after parts delivered + one day of work
- on completion, resets facility wear and clears downtime

We implement this using existing project/delivery primitives where possible.

---

## 2) Implementation Slice A — Data structures + config

Create `src/dosadi/runtime/maintenance.py`

**Deliverables**
- `@dataclass(slots=True) class MaintenanceConfig:`
  - `enabled: bool = False`
  - `wear_per_day_base: float = 0.003`         # ~333 days to full wear (tune later)
  - `wear_per_day_phase2_mult: float = 1.25`   # harsher in phase2
  - `threshold_warn: float = 0.60`
  - `threshold_required: float = 0.80`
  - `threshold_shutdown: float = 0.95`
  - `max_jobs_per_day: int = 10`
  - `job_duration_days: int = 2`
  - `auto_request_parts: bool = True`
  - `auto_assign_crew: bool = True`
  - `crew_kind: str = "MAINTENANCE_CREW"`
  - `parts_source_policy: str = "nearest_depot_then_any"`
  - `deterministic_salt: str = "maint-v1"`

- `@dataclass(slots=True) class MaintenanceState:`
  - `last_run_day: int = -1`
  - `jobs_open_today: int = 0`

Add to world:
- `world.maint_cfg`, `world.maint_state`

---

## 3) Implementation Slice B — Facility wear fields (schema)

Extend Facility dataclass (safe defaults):
- `wear: float = 0.0`
- `maintenance_due: bool = False`
- `maintenance_job_id: str | None = None`

Also reuse existing downtime fields from 0252:
- `down_until_day`
- `is_operational`

Defaults must make old snapshots load safely.

---

## 4) Implementation Slice C — Deterministic wear update

### C1. Wear increment per day
Implement:

`def update_facility_wear(world, *, day: int) -> None`

For each facility in deterministic order:
- `delta = wear_per_day_base * facility_kind_multiplier * phase_multiplier`
- optional deterministic jitter (small) via hashed draw:
  - `j = hashed_unit_float("wear", salt, facility_id, str(day))`
  - `delta *= (0.9 + 0.2*j)`  # bounded, deterministic
- `facility.wear = clamp(facility.wear + delta, 0, 1)`

Facility kind multipliers (v1):
- DEPOT: 0.6
- WORKSHOP: 1.0
- RECYCLER: 1.2
- REFINERY: 1.1

### C2. Threshold behaviors
- if wear >= threshold_warn: emit `FACILITY_WEAR_WARN`
- if wear >= threshold_required:
  - set `maintenance_due=True`
  - if no job exists: open maintenance job (bounded)
- if wear >= threshold_shutdown:
  - set facility down: `facility.down_until_day = max(facility.down_until_day, day)` (down now)
  - emit `FACILITY_SHUTDOWN_WEAR`

---

## 5) Implementation Slice D — Maintenance jobs (job ledger)

We need a small ledger of maintenance jobs.

### D1. Job dataclass
Add to `maintenance.py`:

- `@dataclass(slots=True) class MaintenanceJob:`
  - `job_id: str`
  - `facility_id: str`
  - `owner_id: str`                    # e.g., "facility:{id}" or "ward:{w}"
  - `created_day: int`
  - `due_day: int`
  - `status: str`                      # OPEN, WAITING_PARTS, IN_PROGRESS, DONE, FAILED
  - `bom: dict[Material,int]`
  - `pending_delivery_ids: list[str]`
  - `assigned_agent_ids: list[str]`
  - `progress_days: int = 0`
  - `notes: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class MaintenanceLedger:`
  - `jobs: dict[str, MaintenanceJob]`
  - `open_jobs_by_facility: dict[str, str]`  # facility_id -> job_id
  - `def signature(self) -> str`

Store on world:
- `world.maintenance: MaintenanceLedger`

Snapshot it.

### D2. Job creation (bounded)
Implement:
- `def maybe_open_maintenance_jobs(world, day) -> None`

Rules:
- iterate facilities in deterministic order
- open at most `max_jobs_per_day`
- if facility already has open job, skip
- job BOM determined by facility kind (v1 small table)

Example BOM (v1):
- DEPOT: {FASTENERS: 2, SEALANT: 1}
- WORKSHOP: {FASTENERS: 4, SEALANT: 2, SCRAP_METAL: 5}
- RECYCLER: {FASTENERS: 5, SEALANT: 2, PLASTICS: 3}

Emit `MAINT_JOB_OPENED`.

---

## 6) Implementation Slice E — Parts delivery requests

When a job opens (or if WAITING_PARTS):
- if auto_request_parts:
  - create deliveries from depot inventories to facility inventory owner
  - payload includes: `job_id`, `facility_id`, materials dict
  - avoid duplicates (job.pending_delivery_ids non-empty)

On delivery completion:
- deposit materials to facility inventory owner (facility already has inventory)
- update job status if BOM can now be satisfied

Policy (v1):
- parts delivered into facility inventory, but job consumes them on start of IN_PROGRESS.

---

## 7) Implementation Slice F — Crew assignment + progress

### F1. Crew assignment
If auto_assign_crew:
- choose idle agents deterministically (bounded cap, preserve reserves)
- assign via WorkforceLedger with a new AssignmentKind:
  - `AssignmentKind.MAINTENANCE`
  - target_id = job_id
- store assigned_agent_ids on job

### F2. Progress
Once:
- BOM available at facility inventory
- crew assigned (or crew not required if you want v1 simplified)

Then:
- set status IN_PROGRESS
- each day increment `progress_days += 1`
- when progress_days >= job_duration_days:
  - consume BOM from facility inventory (apply_bom)
  - set facility.wear = 0.0
  - set maintenance_due False
  - clear shutdown: `facility.down_until_day = -1` (or day-1)
  - release crew assignments
  - mark job DONE
  - emit `MAINT_JOB_DONE`, `FACILITY_MAINTENANCE_COMPLETE`

If job passes due_day and cannot progress:
- optional: mark FAILED and keep facility down (v1 can omit; just keep OPEN)

---

## 8) Pipeline wiring

Recommended daily insertion (when enabled):
- after facility recipes and before incident engine OR after incident engine and before router.

Suggested:
1) facility recipes (production)
2) wear update + job open
3) maintenance progress + deliveries
4) proceed to incident engine/router/beliefs/decisions

Reason: incidents can react to downtime but shouldn’t be required for wear.

---

## 9) Telemetry + events

Events:
- `FACILITY_WEAR_WARN`
- `FACILITY_SHUTDOWN_WEAR`
- `MAINT_JOB_OPENED`
- `MAINT_PARTS_REQUESTED`
- `MAINT_JOB_STARTED`
- `MAINT_JOB_DONE`

Counters:
- `metrics["maintenance"]["jobs_opened"]`
- `metrics["maintenance"]["jobs_done"]`
- `metrics["maintenance"]["facilities_shutdown"]`
- `metrics["maintenance"]["parts_deliveries_requested"]`
- `metrics["maintenance"]["crew_assigned"]`

These feed memory and reliability beliefs.

---

## 10) Tests (must-have)

Create `tests/test_maintenance_wear.py`.

### T1. Flag off = baseline
- enabled=False → no wear changes, no jobs.

### T2. Deterministic wear increments
- clone world, run day update → same wear signatures.

### T3. Job opens at threshold
- set facility wear near threshold_required; run; job created.

### T4. Shutdown at threshold_shutdown
- set wear >= shutdown; facility down_until_day set; event emitted.

### T5. Maintenance completes when parts + crew available
- provision depot parts; run pipeline days; job completes; wear resets; facility operational.

### T6. No duplicate deliveries
- run job logic twice; ensure only one set of pending deliveries.

### T7. Crew release on job done
- assignment cleared after completion.

### T8. Snapshot roundtrip
- save mid-job; load; continue; identical final signature.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add maintenance module + world state
- Create `src/dosadi/runtime/maintenance.py` with config/state/job dataclasses and ledger
- Add `world.maint_cfg`, `world.maint_state`, and `world.maintenance` to snapshots

### Task 2 — Extend facility schema
- Add wear/maintenance_due/maintenance_job_id fields with safe defaults

### Task 3 — Wear update + job open
- Implement deterministic wear increments and threshold behaviors
- Open bounded maintenance jobs when required

### Task 4 — Parts deliveries + crew assignment + progress
- Request parts deliveries deterministically, avoid duplicates
- Assign maintenance crew via WorkforceLedger (new AssignmentKind)
- Advance jobs daily; on completion consume BOM, reset wear, clear downtime, release crew

### Task 5 — Wire into daily pipeline
- Insert maintenance system into day pipeline when enabled

### Task 6 — Tests + telemetry
- Add `tests/test_maintenance_wear.py` implementing T1–T8
- Add events and metrics counters

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=False: no behavior change.
- With enabled=True:
  - facilities accumulate deterministic wear,
  - jobs open at thresholds and request parts,
  - jobs complete and restore facility operation when supplied/staffed,
  - downtime becomes a real constraint feeding logistics and planning,
  - save/load works mid-job.

---

## 13) Next slice after this

**Suit Wear & Repair v1** (agents’ suits degrade, repair uses the same maintenance/materials loop),
which will make “awake vs ambient” choices meaningful for individual survival.
