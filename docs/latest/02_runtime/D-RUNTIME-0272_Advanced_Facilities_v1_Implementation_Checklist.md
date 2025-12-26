---
title: Advanced_Facilities_v1_Implementation_Checklist
doc_id: D-RUNTIME-0272
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0253   # Maintenance & Wear v1
  - D-RUNTIME-0254   # Suit Wear & Repair v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0262   # Resource Refining Recipes v2
  - D-RUNTIME-0268   # Tech Ladder v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0271   # Governance Failure Incidents v1
---

# Advanced Facilities v1 — Implementation Checklist

Branch name: `feature/advanced-facilities-v1`

Goal: introduce a small set of **mid-to-late tech facilities** that:
- deepen the economy/industry loop,
- provide levers to fight A1 (environment) and A2 (predation),
- enable long-run technological growth (0268),
without exploding scope.

This slice focuses on **facility archetypes + recipes + operational effects**, not UI.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Bounded.** Facilities update at macro cadences; avoid per-tick per-facility heavy loops.
2. **Tech-gated.** Most advanced facilities require unlock tags (0268).
3. **Material-grounded.** Facilities consume/produce real resources (0262).
4. **Wear/maintenance.** Advanced facilities create new maintenance demand (0253).
5. **Composable.** Outputs feed construction, suits, corridor upgrades, and institutions.
6. **Tested.** Recipes work; gating works; persistence works.

---

## 1) Facility set (v1)

Add 4 new facility types:

1) **CHEM_LAB_T2**
- produces sealants, gaskets, filter media variants
- reduces suit leak incidents indirectly by improving supplies
- tech gate: `UNLOCK_CHEM_SEALANTS_T2`

2) **WORKSHOP_T2** (upgrade or distinct)
- produces fasteners, fittings, simple parts
- gate: `UNLOCK_WORKSHOP_PARTS_T2`

3) **FAB_SHOP_T3** (limited fabrication)
- produces “advanced components” (e.g., pumps, valves, compressors-lite)
- gate: `UNLOCK_FABRICATION_SIMPLE_T3` (or later tag)
- v1 can include but keep scarce and expensive

4) **WAYSTATION_L2**
- corridor-edge facility (special placement on corridor nodes)
- improves hazard mitigation and reduces suit wear for couriers
- ties directly to corridor improvements (0267)
- gate: `UNLOCK_CORRIDOR_L2` (or corridor level >=2)

If your current facility framework doesn’t support corridor-edge facilities yet:
- represent WAYSTATION as a normal facility in a “node ward” and let routing consult it.
Keep v1 pragmatic.

---

## 2) Data structures / schema updates

Extend facility schema (0252) with:
- `requires_unlocks: set[str]` (default empty)
- `tier: int` (default 1)
- `role_tags: set[str]` (e.g., {"chem","industry","logistics_support"})
- `base_throughput: dict[str,float]` (optional)
- `consumes: dict[material,qty_per_day]`
- `produces: dict[material,qty_per_day]`

Operational model (bounded):
- facilities run once per day (or once per shift) producing outputs if inputs available.
- store per-facility last_run_day.

---

## 3) Recipes (0262) additions

Add materials (or placeholders) required for the new loop:
- SEALANT
- GASKETS
- FILTER_MEDIA
- FASTENERS
- FITTINGS
- ADV_COMPONENTS (pumps/valves class)
You may already have some; add what’s missing.

Add refining recipes:
- CHEM_LAB_T2: CHEM_SALTS + WATER_ALLOC (+ ENERGY optional) -> SEALANT
- WORKSHOP_T2: SCRAP_METAL -> FASTENERS/FITTINGS
- FAB_SHOP_T3: FASTENERS + SEALANT + METAL_PLATE -> ADV_COMPONENTS

Keep quantities small and tune later.

---

## 4) Facility operations runner (bounded)

If you already have a daily facility runner, extend it; else add:
- `run_facilities_for_day(world, day)`

Rules:
- iterate only facilities in active wards (or those with input availability / queued production)
- cap total facilities processed per day (optional safety) and prioritize by:
  - facilities that are feeding active projects (construction, suits, corridor)
  - facilities in wards with high market urgency
- produce outputs into nearest depot or local stockpile owner.

All deterministic:
- stable ordering by (priority desc, facility_id asc).

---

## 5) Integration points (what advanced facilities change)

### 5.1 Suit system (0254)
- Availability of SEALANT/GASKETS increases repair success or reduces leak severity.
- If supplies scarce, suit failure incidents increase (A1 escalates).

### 5.2 Corridor improvements (0267)
- FILTER_MEDIA, SEALANT, FASTENERS required for L1→L2 upgrades.
- WAYSTATION reduces hazard multiplier and wear along nearby edges/routes.

### 5.3 Institutions (0269) and Governance failures (0271)
- shortages of key maintenance parts increase unrest and strike probability.
- advanced facilities can relieve pressure and reduce A3 incidents.

### 5.4 Tech ladder (0268)
- tech unlocks enable these facilities, but the facilities also create the material base for further tech.

---

## 6) Construction integration (0258)

Add facility build costs for the new types:
- CHEM_LAB_T2: needs sealable room + filters + lab kit components
- WORKSHOP_T2: needs benches + tools (fasteners, scrap)
- FAB_SHOP_T3: heavy cost, slow build
- WAYSTATION_L2: corridor node shelter kit + filters

Ensure facility `requires_unlocks` are enforced at project planning time:
- planner cannot propose building a facility without required unlocks.

---

## 7) Telemetry + cockpit

Metrics:
- metrics["facilities"]["count_by_type"]
- metrics["facilities"]["outputs_by_material"]
- metrics["facilities"]["inputs_missing"] TopK

Cockpit:
- Facility roster with:
  - type, tier, requires_unlocks satisfied?, last_run_day
  - inputs available?, outputs produced today
- “Bottleneck view”: top missing inputs preventing production.

Events:
- FACILITY_PRODUCED
- FACILITY_STALLED_INPUTS

---

## 8) Tests (must-have)

Create `tests/test_advanced_facilities_v1.py`.

### T1. Tech gating
- without unlock tag, cannot plan/build/run the facility.
- with unlock, it becomes available.

### T2. Production correctness
- with inputs, facility consumes inputs and produces outputs deterministically.

### T3. Stalling behavior
- without inputs, facility does not produce and emits stalled telemetry.

### T4. Integration with corridor upgrade recipe
- corridor L1→L2 requires FILTER_MEDIA/SEALANT from CHEM_LAB.
- after production, corridor upgrade can proceed.

### T5. Snapshot roundtrip
- facility state and inventories persist; production continues deterministically after load.

---

## 9) Codex Instructions (verbatim)

### Task 1 — Add advanced facility definitions + tech gates
- Extend facility schema with requires_unlocks/tier/role_tags
- Add CHEM_LAB_T2, WORKSHOP_T2, FAB_SHOP_T3, WAYSTATION_L2 facility types

### Task 2 — Add materials + recipes
- Add missing materials (SEALANT, GASKETS, FILTER_MEDIA, FASTENERS, FITTINGS, ADV_COMPONENTS)
- Add daily production recipes per facility

### Task 3 — Facility daily runner updates
- Update daily facilities runner to process advanced facilities deterministically and bounded
- Consume inputs and produce outputs into depots/stockpiles
- Emit stalled/produced events

### Task 4 — Planner/construction integration
- Ensure construction planner respects requires_unlocks for facility projects
- Add build costs and construction stages for new facility types

### Task 5 — Telemetry + tests
- Add cockpit panels and bottleneck views
- Add `tests/test_advanced_facilities_v1.py` (T1–T5)

---

## 10) Definition of Done

- pytest passes.
- With enabled=True and tech unlocks achieved:
  - new facilities can be built and run,
  - production supplies suit repair and corridor upgrades,
  - missing-input stalls are visible,
  - economy pressure can be relieved,
  - persistence works.

---

## 11) Next slice after this

Empire Balance Sheet v1 — budgets, levies, faction funding, and corruption flows
to connect institutions + facilities + factions under one accounting model.
