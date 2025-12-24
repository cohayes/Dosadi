---
title: Construction_Materials_Economy_v1_Implementation_Checklist
doc_id: D-RUNTIME-0251
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-24
depends_on:
  - D-RUNTIME-0238   # Logistics Delivery v1
  - D-RUNTIME-0239   # Scout Missions v1
  - D-RUNTIME-0240   # Construction Workforce Staffing v1
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0246   # Agent Courier Logistics v1
  - D-RUNTIME-0248   # Courier Micro-Pathing v1
  - D-RUNTIME-0250   # Escort Protocols v1
---

# Construction Materials Economy v1 — Implementation Checklist

Branch name: `feature/materials-economy-v1`

Goal: make “build new structures” depend on an actual **materials economy**:
- a small catalog of construction materials,
- inventories stored at facilities/sites,
- deterministic daily production/consumption,
- delivery requests created automatically when shortages occur,
- project stages that block and resume based on materials arrival.

v1 is intentionally small: enough to make expansion feel real, without becoming a full market system.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Feature flag default OFF.** With flag OFF, construction behaves as it does today.
2. **Deterministic.** Same seed/state → same production, consumption, and build outcomes.
3. **Bounded compute.** No global scans across all inventories every tick/day; use local ledgers and due-queues.
4. **Save/Load compatible.** Inventories and recipes serialize; old snapshots load safely with defaults.
5. **Tested.** Add tests for determinism, shortages, deliveries, and stage gating.

---

## 1) Concept model (v1)

### 1.1 Materials
A small set of material types, e.g.:
- `SCRAP_METAL`
- `FASTENERS`
- `SEALANT`
- `PLASTICS`
- `FABRIC`
- `ELECTRICAL`
- `CONCRETE_AGGREGATE` (optional)
- `WATER_BARREL_PARTS` (optional)

Keep this catalog tiny and extend later.

### 1.2 Inventories
Inventories exist at:
- facilities (e.g., workshop, depot),
- project sites (staging piles),
- optionally wards/nodes.

v1 uses integer unit counts (no weights/volumes yet), but inventories are bounded and tracked.

### 1.3 Production recipes
Facilities can produce materials daily if staffed and supplied:
- `Workshop` produces `FASTENERS`, `SEALANT` (small amounts)
- `Recycler` produces `SCRAP_METAL`, `PLASTICS` from `SCRAP_INPUT` (optional)
v1 can even “spawn” a trickle of materials deterministically to get the loop moving.

### 1.4 Construction consumption
Project stages require a bill of materials (BOM). Stages:
- request materials (deliveries)
- block until delivered
- consume on start/advance

---

## 2) Implementation Slice A — Material types + inventory ledger

### A1. Add material enum
Create `src/dosadi/world/materials.py`

**Deliverables**
- `class Material(Enum): ...`
- `@dataclass(slots=True) class MaterialStack:`
  - `material: Material`
  - `qty: int`

### A2. Inventory
Use a compact dict (material -> qty), with safe helpers.

- `@dataclass(slots=True) class Inventory:`
  - `items: dict[Material, int]`
  - `def get(self, m: Material) -> int`
  - `def add(self, m: Material, qty: int) -> None`
  - `def remove(self, m: Material, qty: int) -> int`   # returns removed (clamped)
  - `def can_afford(self, bom: dict[Material,int]) -> bool`
  - `def apply_bom(self, bom: dict[Material,int]) -> None`
  - `def signature(self) -> str`

### A3. InventoryRegistry (world-level)
To avoid scattering inventories, add:
- `@dataclass(slots=True) class InventoryRegistry:`
  - `by_owner: dict[str, Inventory]`  # owner_id -> Inventory (owner_id = "facility:12", "project:abc", "ward:7")
  - `def inv(self, owner_id: str) -> Inventory`        # create if missing
  - `def signature(self) -> str`

Store on world:
- `world.inventories: InventoryRegistry`

Snapshot it.

---

## 3) Implementation Slice B — Facility production (daily, deterministic)

### B1. Production config + feature flag
Create `src/dosadi/runtime/materials_economy.py`

**Deliverables**
- `@dataclass(slots=True) class MaterialsEconomyConfig:`
  - `enabled: bool = False`
  - `daily_production_cap: int = 5000`         # guardrail on units/day worldwide
  - `facility_production_enabled: bool = True`
  - `project_consumption_enabled: bool = True`
  - `auto_delivery_requests_enabled: bool = True`
  - `default_depot_owner_id: str = "ward:0"`   # fallback stockpile, scenario-specific
  - `deterministic_seed_salt: str = "mat-econ-v1"`

- `@dataclass(slots=True) class MaterialsEconomyState:`
  - `last_run_day: int = -1`

Add to world:
- `world.mat_cfg`, `world.mat_state`

### B2. Production recipes
Define a small static recipe table, keyed by facility kind (string or enum):

- `PRODUCTION_RECIPES = {`
  - `"facility_kind:workshop": {FASTENERS: 8, SEALANT: 3},`
  - `"facility_kind:recycler": {SCRAP_METAL: 12, PLASTICS: 6},`
`}`

Production is gated by staffing:
- if facility has `min_staff` assigned (WorkforceLedger), produce full output
- else produce 0 (or reduced output deterministically)

### B3. Daily production runner
Implement:
- `def run_materials_production_for_day(world, *, day: int) -> None`

Rules:
- iterate only over facilities that exist (world.facilities list/registry)
- for each facility:
  - determine owner_id = `facility:{id}`
  - add produced quantities to `world.inventories.inv(owner_id)`
- enforce global `daily_production_cap` (stop producing if cap exceeded; deterministic order by facility_id)

Emit WorldEvents (optional but useful):
- `MATERIALS_PRODUCED` with facility_id + outputs

---

## 4) Implementation Slice C — Project BOM gating + consumption

### C1. Add BOM to project stage definitions
Wherever project stages are defined, add:
- `stage.bom: dict[Material,int]` (default empty)

Examples:
- `FOUNDATION`: {SCRAP_METAL: 20, SEALANT: 5}
- `FRAME`: {SCRAP_METAL: 35, FASTENERS: 10}
Keep BOM tiny to start.

### C2. Material owner for a project
Define:
- project owner inventory id: `project:{project_id}`

When a stage begins:
- check if project inventory can afford stage.bom
  - if yes: consume (apply_bom) and proceed
  - if not: stage becomes BLOCKED_WAITING_MATERIALS and triggers deliveries

### C3. Where do deliveries originate?
v1 simplest:
- a “depot” is the source inventory:
  - choose nearest facility with stock, or
  - use `default_depot_owner_id` fallback (ward stockpile)

Deterministic source selection:
- iterate candidate depots in sorted owner_id order, pick first that can fulfill (or partial fulfill if allowed).

### C4. Automatic delivery requests
If stage lacks materials, create delivery requests:
- from depot owner (facility/ward) to project owner
- per-material or grouped (v1: grouped into one delivery payload dict)

Delivery payload should include:
- `materials: {Material->qty}`
- `priority: "construction"`
- `project_id`, `stage_id`

On delivery completion:
- add delivered materials to project inventory
- emit `MATERIALS_DELIVERED` event
- project can unblock on next daily tick or immediately (choose deterministic policy; recommended: next daily evaluation).

Guardrail:
- do not create duplicate deliveries for the same (project, stage) if one is already pending.
Store `project.pending_material_delivery_ids` or a per-stage flag.

---

## 5) Integration points (where to wire this)

### 5.1 Daily pipeline insertion
When enabled, run:

1) Materials production
2) Project material gating (request deliveries, unblock/consume)
3) Continue with existing projects/logistics cycle

Suggested placement:
- early in daily pipeline, before planner decisions:
  - production → gating → logistics assignment → incidents/router/beliefs/decisions

### 5.2 Decision hooks synergy (optional)
If a site has chronic shortages, beliefs can form:
- `facility-reliability:depot` or `supply-risk:route` (later)
v1 just ensures events exist to feed memory.

---

## 6) Save/Load requirements

Snapshot must include:
- `world.inventories`
- `world.mat_cfg`, `world.mat_state`
- any new project fields (`pending_material_delivery_ids`, stage blocked flags)

Old snapshots:
- inventories default empty
- config default disabled

---

## 7) Telemetry

Add O(1) counters:
- `metrics["materials"]["produced_units"]`
- `metrics["materials"]["consumed_units"]`
- `metrics["materials"]["deliveries_requested"]`
- `metrics["materials"]["deliveries_completed"]`
- `metrics["materials"]["projects_blocked"]`
- `metrics["materials"]["projects_unblocked"]`

---

## 8) Tests (must-have)

Create `tests/test_materials_economy.py`.

### T1. Flag off = baseline
- With enabled=False, signatures match baseline.

### T2. Deterministic production
- With same world state, run day twice (or clone world) → same inventory signatures.

### T3. Project blocks without materials
- Create project stage with BOM; ensure project blocks and requests deliveries.

### T4. Delivery completion unblocks project
- Fulfill delivery; ensure materials land in project inventory and stage proceeds (per policy).

### T5. No duplicate delivery requests
- Run gating twice; ensure only one pending request exists for a stage.

### T6. Cap enforcement
- Configure low daily_production_cap; ensure production stops deterministically.

### T7. Snapshot roundtrip
- Save mid-blocked stage with pending delivery; load; complete; identical final signature.

---

## 9) Codex Instructions (verbatim)

### Task 1 — Add materials + inventories
- Create `src/dosadi/world/materials.py` with Material enum, Inventory, InventoryRegistry
- Add `world.inventories` and snapshot support

### Task 2 — Add materials economy runtime
- Create `src/dosadi/runtime/materials_economy.py` with MaterialsEconomyConfig/State
- Implement `run_materials_production_for_day(world, day)` with deterministic order and cap

### Task 3 — Project BOM gating + auto deliveries
- Add `bom` dict to project stage definitions (safe defaults)
- Implement `evaluate_project_materials(world, day)`:
  - block stages lacking materials,
  - request deliveries from depots deterministically,
  - avoid duplicates
- On delivery completion, deposit to `project:{id}` inventory and emit events

### Task 4 — Wire into daily pipeline
- When enabled, call production + gating early in the daily pipeline

### Task 5 — Tests + telemetry
- Add `tests/test_materials_economy.py` implementing T1–T7
- Add metrics counters

---

## 10) Definition of Done

- `pytest` passes.
- With enabled=False: no behavior change.
- With enabled=True:
  - facilities produce materials deterministically,
  - projects block on BOM shortages,
  - deliveries are requested automatically and delivered materials unblock stages,
  - no duplicate delivery spam,
  - save/load works mid-cycle.

---

## 11) Next slice after this

**Facility Types & Recipes v1** (expand production network: depot/workshop/recycler/refinery),
and/or **Maintenance & Wear v1** (facilities consume parts and trigger downtime events).
