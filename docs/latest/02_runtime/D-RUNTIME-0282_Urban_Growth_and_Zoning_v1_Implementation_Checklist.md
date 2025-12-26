---
title: Urban_Growth_and_Zoning_v1_Implementation_Checklist
doc_id: D-RUNTIME-0282
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0253   # Maintenance & Wear v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0259   # Expansion Planner v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0268   # Tech Ladder v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0272   # Advanced Facilities v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0281   # Migration & Refugees v1
---

# Urban Growth & Zoning v1 — Implementation Checklist

Branch name: `feature/urban-growth-zoning-v1`

Goal: convert migration pressure and economic signals into **city morphology**:
- wards expand housing and utilities,
- zoning preferences shape what gets built where,
- specialization emerges (industrial vs civic vs military vs agrarian proxies),
- long-run seeds develop believable urban structure over centuries.

v1 is macro urban planning, not detailed street grids.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same growth decisions.
2. **Bounded.** TopK needs and TopK build candidates; no per-agent housing.
3. **Capacity-driven.** Population pressure drives build priorities.
4. **Maintained.** New infrastructure adds upkeep burden (0253).
5. **Policy-driven.** Institutions can choose zoning biases and growth style.
6. **Tested.** Growth triggers, build selection, persistence.

---

## 1) Concept model

Each ward maintains a macro “urban profile”:
- housing capacity,
- utility capacity (water, air processing, waste),
- industrial slots (workshops/refineries),
- security capacity (garrison/outposts),
- civic capacity (administration/education/medicine).

Population pressure (0281) and shortages (0263) produce **needs**.
Needs are translated into construction projects (0258) constrained by:
- available materials (0262),
- budget points (0273),
- tech unlocks (0268),
- zoning policy preferences (0269).

---

## 2) Data structures

Create `src/dosadi/runtime/urban.py`

### 2.1 Config
- `@dataclass(slots=True) class UrbanConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 7`
  - `need_topk: int = 8`
  - `project_topk: int = 8`
  - `deterministic_salt: str = "urban-v1"`

### 2.2 Ward urban state
- `@dataclass(slots=True) class WardUrbanState:`
  - `ward_id: str`
  - `housing_cap: int = 0`
  - `utility_cap: dict[str, int] = field(default_factory=dict)`      # water/air/waste
  - `civic_cap: dict[str, int] = field(default_factory=dict)`        # clinic/school/admin
  - `industry_cap: dict[str, int] = field(default_factory=dict)`      # refinery/workshop
  - `security_cap: dict[str, int] = field(default_factory=dict)`     # militia/fort
  - `zoning_bias: dict[str, float] = field(default_factory=dict)`    # weights by category
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.urban_cfg`
- `world.urban_by_ward: dict[str, WardUrbanState]`

Persist in snapshots and seeds.

---

## 3) Zoning policy dials (institutions)

Extend institution policy (0269) with:
- `zoning_residential_bias` (housing)
- `zoning_industrial_bias` (refining/workshops)
- `zoning_civic_bias` (clinics/admin)
- `zoning_security_bias` (garrisons/forts)
- `growth_aggressiveness` (0..1)
- `heritage_preservation` (0..1) (slows replacement)

These biases influence project selection.

---

## 4) Need model (how we decide what to build)

Every update_cadence_days, compute needs per ward from:
- population pressure (0281):
  - high camp or displaced → housing need
  - high pop growth → utility need
- economy shortages (0263):
  - persistent shortages in key materials → industrial/refining need
- governance pressure (0271):
  - high unrest → civic need (administration, clinics) and/or security need
- war pressure (0278):
  - raids/corridor collapses → security need (fortifications, garrison)

Represent each need as:
- kind (HOUSING, WATER_UTIL, AIR_UTIL, WASTE_UTIL, CLINIC, ADMIN, REFINERY, WORKSHOP, GARRISON)
- severity score 0..1

Pick TopK needs per ward.

---

## 5) Mapping needs to build candidates (recipes)

Define a small mapping table:
- HOUSING → `HOUSING_BLOCK_L1`, `HOUSING_BLOCK_L2`
- WATER_UTIL → `WATER_PLANT_L1`, `WATER_PLANT_L2`
- AIR_UTIL → `DEHUMIDIFIER_BANK_L1`, `FILTER_PLANT_L2`
- WASTE_UTIL → `WASTE_RECLAIMER_L1`
- CLINIC → `CLINIC_L1`
- ADMIN → `ADMIN_HALL_L1`
- REFINERY → `REFINERY_L1`, `REFINERY_L2`
- WORKSHOP → `WORKSHOP_L1`, `FAB_SHOP_L2`
- GARRISON → `GARRISON_L2` (from 0279)

For each need, generate candidate projects with:
- tech gate checks (0268),
- cost checks (materials/budget),
- maintenance burden estimate (0253).

Pick TopK candidate projects per ward.

---

## 6) Project selection logic (deterministic)

For each ward:
- score candidate projects:
  - + need severity
  - + zoning bias weight
  - + long-run ROI proxy (reduces shortage, reduces camp)
  - - cost and maintenance burden
  - - risk of collapse (if corridor access poor)

Select up to N new projects per update (e.g., 1–2) depending on growth_aggressiveness and capacity.

Submit to construction pipeline (0258) via the existing planner hooks (0259/0236).

---

## 7) Replacement and density (optional v1)

If facility slots are limited, allow replacement:
- choose a low-utility facility to decommission when heritage_preservation is low
- replacement is deterministic

If slot system not implemented yet, keep v1 additive only.

---

## 8) Effects wiring

When facilities complete:
- update WardUrbanState capacities accordingly
- migration intake capacity (0281) increases with housing/utilities
- market shortages should improve over time with new industry
- maintenance load increases (0253), affecting budgets (0273)

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["urban"]["projects_started"]`
- `metrics["urban"]["housing_cap_total"]`
- `metrics["urban"]["camp_total"]` (from migration, mirrored)
- `metrics["urban"]["utility_shortfalls"]`

TopK:
- wards with highest camp pressure
- wards with worst utility gap
- wards with strongest industrial shortage signal

Cockpit:
- ward urban profile page: capacities, zoning biases, recent projects
- “growth decisions” log: need scores and chosen projects
- “city morphology” summary: ward specialization indices (simple)

Events:
- `URBAN_NEED_COMPUTED`
- `URBAN_PROJECT_SELECTED`
- `URBAN_PROJECT_COMPLETED`

---

## 10) Tests (must-have)

Create `tests/test_urban_growth_zoning_v1.py`.

### T1. Determinism
- same needs and policies → same project selection.

### T2. Need-driven growth
- higher camp pressure increases housing build frequency.

### T3. Zoning bias effect
- industrial-biased wards choose refineries more often, all else equal.

### T4. Tech gating
- without unlocks, higher-tier facilities are not selected.

### T5. Persistence
- urban state persists across snapshot/load and seed export.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add urban module + ward urban state
- Create `src/dosadi/runtime/urban.py` with UrbanConfig and WardUrbanState
- Add world.urban_by_ward to snapshots + seeds

### Task 2 — Need computation on cadence
- Compute needs from migration pressure, shortages, unrest, and war signals
- Keep TopK needs per ward with deterministic tie breaks

### Task 3 — Candidate mapping and project selection
- Map needs to facility project candidates using facility definitions and tech gates
- Score deterministically using zoning biases, costs, and maintenance burden
- Submit selected projects to construction pipeline

### Task 4 — Telemetry + tests
- Add cockpit pages and logs for needs and projects
- Add `tests/test_urban_growth_zoning_v1.py` (T1–T5)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - wards compute needs from population/economy signals,
  - zoning biases steer build choices,
  - construction pipeline receives urban growth projects,
  - new builds increase capacities and reduce camps/shortages over time,
  - urban state persists into long-run seeds,
  - cockpit explains “why this ward built that.”

---

## 13) Next slice after this

**Public Health & Epidemics v1** — disease dynamics amplified by camps and density:
- chronic illness baseline,
- outbreak incidents,
- and health infrastructure as a stabilizer across phases.
