---
title: Facility_Types_and_Recipes_v1_Implementation_Checklist
doc_id: D-RUNTIME-0252
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-24
depends_on:
  - D-RUNTIME-0236   # Expansion Planner v1
  - D-RUNTIME-0238   # Logistics Delivery v1
  - D-RUNTIME-0240   # Construction Workforce Staffing v1
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
---

# Facility Types & Recipes v1 — Implementation Checklist

Branch name: `feature/facility-types-recipes-v1`

Goal: formalize a small set of **facility kinds** with deterministic **recipes** that:
- produce construction materials daily,
- consume inputs (where applicable),
- require staffing to operate,
- integrate with incidents (downtime) and beliefs (reliability),
- make expansion planning choose *what* to build, not just *where*.

This builds directly on the Materials Economy v1 inventory system.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Feature flag default OFF** for any behavior-altering change beyond v1 economy defaults.
2. **Deterministic** production/consumption/selection order.
3. **Bounded**: no per-day scans over “all owners”; iterate only over facilities that exist.
4. **Save/Load compatible**: new facility fields have defaults; old snapshots load.
5. **Tested**: recipes, staffing gates, downtime behavior, signature determinism.

---

## 1) Concept model

### 1.1 FacilityKind
Facilities have a kind that determines:
- staffing requirements (min staff),
- recipes (inputs → outputs),
- storage role (depot vs producer),
- maintenance profile (later).

v1 facility kinds (small but useful):
- `DEPOT` (storage hub, no production)
- `WORKSHOP` (fasteners, sealant, simple parts)
- `RECYCLER` (scrap → metal/plastic)
- `REFINERY` (optional v1; produces “processed metal” or “fuel” later)
- `WATER_WORKS` (optional; supports the water loop later)

Start with DEPOT/WORKSHOP/RECYCLER as the core.

### 1.2 Recipe
A recipe is a deterministic transform executed once per day per facility (if operating):
- consumes inputs from facility inventory (or upstream depot if allowed),
- produces outputs to facility inventory,
- emits events for telemetry/memory.

---

## 2) Implementation Slice A — FacilityKind + schema

### A1. FacilityKind enum
Add to `src/dosadi/world/facilities.py` (or create it if missing):
- `class FacilityKind(Enum): DEPOT, WORKSHOP, RECYCLER, REFINERY, WATER_WORKS`

### A2. Facility fields
Extend Facility dataclass with safe defaults:
- `kind: FacilityKind = FacilityKind.DEPOT`
- `min_staff: int = 0`
- `is_operational: bool = True`
- `down_until_day: int = -1`  # if >= day, facility is down
- `tags: set[str] = field(default_factory=set)`  # optional

Snapshot-safe defaults are mandatory.

### A3. Owner ID conventions
Facility inventory owner id:
- `owner_id = f"facility:{facility_id}"`

Depot inventory owner id can still be facility-based; depots are facilities too.

---

## 3) Implementation Slice B — Recipe representation

Create `src/dosadi/world/recipes.py`

**Deliverables**
- `@dataclass(frozen=True, slots=True) class Recipe:`
  - `id: str`
  - `kind: str`  # "daily"
  - `inputs: dict[Material,int]`
  - `outputs: dict[Material,int]`
  - `min_staff: int = 0`
  - `enabled: bool = True`
  - `notes: str = ""`

- `FACILITY_RECIPES: dict[FacilityKind, list[Recipe]]`

v1 example recipes:
- WORKSHOP:
  - inputs: {SCRAP_METAL: 6} → outputs: {FASTENERS: 6}
  - inputs: {PLASTICS: 4} → outputs: {SEALANT: 2}
- RECYCLER:
  - inputs: {SCRAP_INPUT: 10} → outputs: {SCRAP_METAL: 7, PLASTICS: 3}
If you don’t have SCRAP_INPUT, simplify:
- inputs empty → outputs small trickle (bootstrap mode), but keep it deterministic.

Important:
- recipes should be small numbers to avoid exploding inventories early.

---

## 4) Implementation Slice C — Operating rules (staffing + downtime)

### C1. Staffing gate
A facility “operates” on a given day if:
- `facility.is_operational == True`
- `facility.down_until_day < day`
- `assigned_staff_count >= recipe.min_staff` (from WorkforceLedger)

If not operating:
- produce nothing
- optionally emit `FACILITY_NOT_OPERATING` telemetry event.

### C2. Downtime integration
Incident Engine v1 already supports downtime patterns. Extend it so it can mark:
- `facility.down_until_day = day + duration_days`

When down:
- recipes do not run
- emit `FACILITY_DOWN` events

Belief Formation can learn:
- `facility-reliability:{facility_id}` from uptime/downtime events.

---

## 5) Implementation Slice D — Production runner upgrade

Upgrade `run_materials_production_for_day` to:
- iterate facilities in deterministic order
- for each facility, run its recipes (if operating)
- consume inputs from facility inventory, clamped if insufficient:
  - v1 policy: if cannot afford full inputs, skip recipe (recommended)
- add outputs to facility inventory
- enforce global production cap (units/day) globally

### D1. Optional “upstream pull” (depot supply)
If you want depots to supply producers in v1, do it explicitly and deterministically:
- a producer can pull missing inputs from nearest depot once per day (bounded)
This can be deferred; simplest is “inputs must be onsite”.

---

## 6) Implementation Slice E — Expansion planner integration (what to build)

Upgrade Expansion Planner v1 so it chooses facility kinds, not just “facility” generic.

### E1. Demand signals
Compute small demand signals from:
- projects blocked on materials (which materials are missing),
- inventory low-water marks at depots.

Then choose what facility kind to build:
- if FASTENERS/SEALANT missing → WORKSHOP
- if SCRAP_METAL/PLASTICS missing → RECYCLER
- else DEPOT

Make deterministic and bounded:
- evaluate only top-K shortages (K small, e.g. 5)
- tie-break by material enum order

### E2. Project templates
Construction Projects v1 should accept a `facility_kind` target.
When finished, create facility of that kind with appropriate defaults.

---

## 7) Telemetry + events

Emit events:
- `FACILITY_RECIPE_RAN` (facility_id, recipe_id, outputs)
- `FACILITY_RECIPE_SKIPPED` (reason: insufficient inputs / insufficient staff / downtime)
- `FACILITY_DOWN` / `FACILITY_UP`

Add counters:
- `metrics["facilities"]["recipes_ran"]`
- `metrics["facilities"]["recipes_skipped_inputs"]`
- `metrics["facilities"]["recipes_skipped_staff"]`
- `metrics["facilities"]["downtime_days"]`

---

## 8) Save/Load requirements

Snapshot must include:
- facility kind + downtime fields
- inventories (already)
- any recipe config (prefer static table in code; don’t snapshot)

Old snapshots:
- default kind DEPOT, operational True, down_until_day -1

---

## 9) Tests (must-have)

Create `tests/test_facility_recipes.py`.

### T1. Deterministic recipe execution
- Same world clone → same inventory signature after one day production.

### T2. Staffing gate
- No staff assigned → recipe does not run.
- Enough staff → recipe runs.

### T3. Input insufficiency skips recipe
- Not enough inputs → no partial consume; outputs unchanged.

### T4. Downtime prevents production
- Mark facility down_until_day >= day → recipe not run.

### T5. Expansion planner chooses facility kind based on shortages
- Create shortages → planner selects expected kind deterministically.

### T6. Snapshot roundtrip
- Save mid-downtime; load; production remains off until day passes; signatures match.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add FacilityKind + schema fields
- Add FacilityKind enum and extend Facility dataclass with kind/min_staff/is_operational/down_until_day defaults
- Ensure snapshot compatibility for old worlds

### Task 2 — Add recipe module
- Create `src/dosadi/world/recipes.py` with Recipe dataclass and FACILITY_RECIPES table

### Task 3 — Upgrade daily production runner
- Update materials economy production to run facility recipes deterministically
- Enforce staffing gates and downtime
- Enforce global production cap

### Task 4 — Incidents integration
- Extend Incident Engine facility downtime to set down_until_day
- Emit FACILITY_DOWN / FACILITY_UP events

### Task 5 — Expansion planner integration
- Add deterministic shortage signals
- Choose facility kind based on shortages
- Ensure projects create facility of chosen kind on completion

### Task 6 — Tests + telemetry
- Add `tests/test_facility_recipes.py` implementing T1–T6
- Add metrics/events as described

---

## 11) Definition of Done

- `pytest` passes.
- Facility kinds exist and serialize safely.
- Recipes run deterministically with staffing + downtime gates.
- Expansion planner selects facility kinds based on actual material shortages.
- Events/telemetry make production and downtime legible.
- Save/load works across downtime and production days.

---

## 12) Next slice after this

**Maintenance & Wear v1** (facilities and suits consume parts; downtime becomes inevitable),
which will make escorts/logistics and black markets start to matter.
