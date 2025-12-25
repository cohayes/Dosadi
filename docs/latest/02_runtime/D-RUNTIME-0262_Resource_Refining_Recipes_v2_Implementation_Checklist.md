---
title: Resource_Refining_Recipes_v2_Implementation_Checklist
doc_id: D-RUNTIME-0262
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0253   # Maintenance & Wear v1
  - D-RUNTIME-0256   # Resource Extraction Sites v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0259   # Expansion Planner v2
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
---

# Resource Refining Recipes v2 — Implementation Checklist

Branch name: `feature/resource-refining-recipes-v2`

Goal: give the economy a **tech ladder** by turning raw, low-grade inputs (scrap/salvage)
into higher-value parts that unlock more complex construction and maintenance:
- define a refining pipeline (recipes + facilities),
- make production deterministic and bounded,
- integrate with depots/stockpile policy and planner signals,
- expose telemetry (“what’s being produced and why”).

This is where “discover scrap” becomes “build industry”.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic production.** Same state → same outputs.
2. **Bounded compute.** Iterate only over producer facilities; no global scans.
3. **Feature-flagged.** New production loop behind config; does not change baseline when off.
4. **No resource magic.** Conservation: inputs removed, outputs added; losses explicit.
5. **Save/Load safe.** Recipes config and facility production state serialize.
6. **Tested.** Recipe correctness, bounds, snapshot roundtrip.

---

## 1) Material tiers (v2)

Define (or confirm) a minimal tier ladder:

### Tier 0 (raw)
- `SCRAP_INPUT` (generic rubble)
- `SALVAGE_MIX` (misc parts bundle) (optional; can represent with multiple materials)

### Tier 1 (refined basics)
- `SCRAP_METAL`
- `PLASTICS`
- `FIBER`
- `CHEM_SALTS` (placeholder)
- `SEALANT`

### Tier 2 (construction parts)
- `FASTENERS`
- `GASKETS`
- `FILTER_MEDIA`
- `CIRCUIT_SIMPLE` (placeholder, small)
- `FABRIC` (if not already)

v2 goal: enable FASTENERS, SEALANT, GASKETS, FILTER_MEDIA at minimum.

If your Materials enum is already defined, use existing names; otherwise add these carefully.

---

## 2) Facilities involved

Use facility kinds (from 0252):
- `RECYCLER` — converts SCRAP_INPUT → SCRAP_METAL/PLASTICS/FIBER (lossy)
- `CHEM_WORKS` — converts CHEM_SALTS/FIBER → SEALANT/GASKETS (placeholder)
- `WORKSHOP` — converts refined basics → FASTENERS/FILTER_MEDIA/etc.

If you only have DEPOT/WORKSHOP now, you can implement RECYCLER as a WORKSHOP recipe set (but label it for future).

Each producer facility has an inventory owner:
- `facility:{facility_id}`

Optionally, support an input “pull” from nearby depots; but v2 can keep it simple:
- producer consumes from its own inventory (fed by depot policy or deliveries).

---

## 3) Implementation Slice A — Recipe registry upgrade

Locate recipe definitions (likely `src/dosadi/economy/recipes.py` or similar).
Create/extend:
- `@dataclass(frozen=True, slots=True) class Recipe:`
  - `recipe_id: str`
  - `facility_kind: str`
  - `inputs: dict[str,int]`
  - `outputs: dict[str,int]`
  - `duration_days: int = 1`
  - `labor_days: int = 0`          # optional gating (staffing)
  - `waste: dict[str,int] = ...`   # optional (loss material)
  - `tags: set[str] = ...`

Add:
- `class RecipeRegistry:`
  - `recipes_by_facility: dict[str, list[Recipe]]`
  - `def get(facility_kind) -> list[Recipe]`

Ensure deterministic recipe ordering (recipe_id sort).

---

## 4) Implementation Slice B — Producer job state

Create `src/dosadi/runtime/production_runtime.py`

**Deliverables**
- `@dataclass(slots=True) class ProductionConfig:`
  - `enabled: bool = False`
  - `max_jobs_per_day_global: int = 200`
  - `max_jobs_per_facility_per_day: int = 3`
  - `prefer_recipes: list[str] = ["FASTENERS","SEALANT","FILTER_MEDIA"]`  # heuristic
  - `deterministic_salt: str = "prod-v2"`

- `@dataclass(slots=True) class ProductionState:`
  - `last_run_day: int = -1`

- `@dataclass(slots=True) class FacilityProductionState:`
  - `facility_id: str`
  - `active_job: str | None = None`     # recipe_id
  - `job_started_day: int = -1`
  - `job_complete_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.prod_cfg`, `world.prod_state`, `world.fac_prod: dict[str, FacilityProductionState]`

Snapshot them.

---

## 5) Implementation Slice C — Choosing what to produce (bounded heuristic)

Implement:
- `def choose_recipe_for_facility(world, facility_id, facility_kind, day) -> Recipe | None`

Heuristic inputs:
- stockpile shortages (from 0257) → prefer producing the scarcest material that this facility can output
- blocked projects missing materials (from 0258)
- planner preference list as tie-break

Selection algorithm:
1) build a ranked list of “needed materials” (TopK) from telemetry (bounded)
2) filter facility recipes that output any needed material
3) choose highest-scoring recipe by:
   - sum(need_score[material] * output_qty)
   - tie-break by recipe_id
All deterministic.

If no needs match, pick a default “base refining” recipe (e.g. SCRAP_INPUT → SCRAP_METAL).

---

## 6) Implementation Slice D — Running production daily

Implement:
- `def run_production_for_day(world, *, day: int) -> None`

Process (bounded):
- iterate producer facilities (kinds: RECYCLER, CHEM_WORKS, WORKSHOP), sorted by facility_id
- for each facility:
  1) if has active_job and day >= job_complete_day:
     - deposit outputs into facility inventory
     - emit `PROD_JOB_DONE`
     - clear active_job
  2) if no active job:
     - choose recipe
     - verify inputs available in facility inventory
       - if not available: set block note + emit `PROD_JOB_BLOCKED_INPUTS`
     - if available:
       - consume inputs immediately on job start (recommended)
       - set active_job + job_complete_day = day + duration_days
       - emit `PROD_JOB_STARTED`

Enforce caps:
- per-facility jobs started/day
- global jobs/day

Note: if duration_days > 1, jobs overlap; v2 may keep duration=1 for simplicity.

---

## 7) Integration with depot policy (feeding producers)

Two viable v2 approaches:

### Option A (simplest): depot deliveries feed producer inventories
- stockpile policy can treat producer facilities as “sources” and “sinks”
- add policy rule: ensure each producer has minimum SCRAP_INPUT on hand
- and ensure depots receive produced FASTENERS/SEALANT etc.

### Option B: producers pull from nearest depot
- daily: if producer lacks inputs, create a pull delivery from nearest depot to producer

Recommended v2: **Option A**, extend stockpile policy to include “producer profiles”:
- e.g., RECYCLER wants SCRAP_INPUT min 100, target 300
- WORKSHOP wants SCRAP_METAL/PLASTICS min 50, etc.

Keep it deterministic and bounded.

---

## 8) Telemetry + admin display

Metrics:
- `metrics["production"]["jobs_started"]`
- `metrics["production"]["jobs_done"]`
- `metrics["production"]["blocked_inputs"]`
- `metrics["production"]["outputs"][material] += qty` (optional dict)
- TopK: `production.top_facilities` by units/day

Cockpit panel addition:
- “Production” table: facility_id, kind, active job, last outputs

Events:
- `PROD_JOB_STARTED`, `PROD_JOB_DONE`, `PROD_JOB_BLOCKED_INPUTS`

---

## 9) Tests (must-have)

Create `tests/test_production_runtime_v2.py`.

### T1. Recipe registry deterministic
- ordering stable; same registry signature.

### T2. Production consumes inputs and produces outputs
- setup facility inventory with inputs; run day; job started; next day outputs present.

### T3. Blocks when inputs missing
- no inputs; emits blocked; no negative inventory.

### T4. Respects caps
- set max_jobs_per_day_global small; deterministic selection.

### T5. Chooses recipe based on shortage signal
- set shortage FASTENERS; ensure workshop chooses a recipe producing FASTENERS.

### T6. Snapshot roundtrip mid-job
- save after job started; load; complete; outputs correct and deterministic.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Recipe registry upgrade
- Add Recipe dataclass and RecipeRegistry with deterministic ordering
- Define v2 refining recipes (scrap → refined, refined → parts)

### Task 2 — Production runtime
- Create `src/dosadi/runtime/production_runtime.py` with config/state/facility job state
- Add world.prod_cfg/world.prod_state/world.fac_prod to snapshots

### Task 3 — Deterministic recipe choice
- Use bounded shortage/block signals to choose recipes per facility
- Fallback to base refining if no match

### Task 4 — Daily production loop
- Start jobs (consume inputs), finish jobs (produce outputs), emit events
- Enforce per-facility and global caps

### Task 5 — Integrate with depot stockpile policy
- Add producer minimum input policies (SCRAP_INPUT, etc.)
- Ensure produced outputs are eligible for depot pulls

### Task 6 — Telemetry + tests
- Add metrics/events
- Add `tests/test_production_runtime_v2.py` (T1–T6)

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=False: baseline unchanged.
- With enabled=True:
  - producer facilities run deterministic production jobs,
  - refined materials and parts appear and feed construction/maintenance loops,
  - blocked inputs are visible in cockpit,
  - depot policy can keep producers fed and depots stocked,
  - save/load works mid-job.

---

## 12) Next slice after this

**Economy Market Signals v1** (soft prices / urgency scores) *or*
**Faction Interference v1** (theft/sabotage targeting high-value corridors and depots).
