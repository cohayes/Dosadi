---
title: Public_Health_and_Epidemics_v1_Implementation_Checklist
doc_id: D-RUNTIME-0283
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0253   # Maintenance & Wear v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0281   # Migration & Refugees v1
  - D-RUNTIME-0282   # Urban Growth & Zoning v1
---

# Public Health & Epidemics v1 — Implementation Checklist

Branch name: `feature/public-health-epidemics-v1`

Goal: add a macro health layer that:
- models chronic illness baseline and outbreaks,
- makes camps and density amplify risk,
- allows clinics/sanitation to stabilize society,
- produces believable phase transitions (P0 managed, P2 brittle and crisis-prone).

v1 is population-level health, not per-agent pathogen simulation.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same outbreak timing and spread.
2. **Bounded.** Operate on wards and corridors; no per-agent infection loops.
3. **Composable.** Health affects labor capacity, legitimacy, unrest, and migration.
4. **Infrastructure matters.** Clinics, sanitation, and water quality reduce risk.
5. **Phase-aware.** P2 increases corruption/neglect and outbreak severity.
6. **Tested.** Outbreak triggers, mitigation, persistence.

---

## 1) Concept model

Each ward tracks macro health:
- baseline chronic disease burden,
- current outbreak intensity by disease type,
- effective healthcare capacity,
- sanitation/water quality modifiers,
- mortality and recovery rates (as proxies).

Outbreaks can:
- reduce effective labor output,
- increase unrest and migration pressure,
- trigger incidents and policy responses.

---

## 2) Data structures

Create `src/dosadi/runtime/health.py`

### 2.1 Config
- `@dataclass(slots=True) class HealthConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 3`
  - `deterministic_salt: str = "health-v1"`
  - `baseline_chronic_rate: float = 0.02`        # per 3-day tick
  - `outbreak_trigger_rate: float = 0.01`        # base chance per ward per update
  - `max_outbreak_intensity: float = 1.0`
  - `spread_strength: float = 0.10`              # corridor spillover factor
  - `recovery_per_update: float = 0.06`
  - `mortality_per_update: float = 0.01`

### 2.2 Disease catalog (v1)
Define 3 abstract disease types:
- `RESPIRATORY`
- `WATERBORNE`
- `WOUND_INFECTION`

Each has:
- trigger affinities (camp density, water quality, raids)
- mitigation affinities (clinics, sanitation, security)

### 2.3 Ward health state
- `@dataclass(slots=True) class WardHealthState:`
  - `ward_id: str`
  - `chronic_burden: float = 0.0`            # 0..1
  - `outbreaks: dict[str, float] = field(default_factory=dict)`  # disease -> intensity 0..1
  - `healthcare_cap: float = 0.0`            # from clinics/med supplies
  - `sanitation_cap: float = 0.0`            # from waste reclaimers, cleanliness
  - `water_quality: float = 0.5`             # 0..1
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

### 2.4 Health event record (bounded)
- `@dataclass(slots=True) class HealthEvent:`
  - `day: int`
  - `ward_id: str`
  - `kind: str`                 # "OUTBREAK_STARTED"|"OUTBREAK_PEAK"|"OUTBREAK_ENDED"
  - `disease: str`
  - `intensity: float`
  - `reason_codes: list[str]`

World stores:
- `world.health_cfg`
- `world.health_by_ward: dict[str, WardHealthState]`
- `world.health_events: list[HealthEvent]` (bounded)

Persist ward health in snapshots and seeds; events bounded and optional in seeds.

---

## 3) Inputs from other systems

Per update, compute risk modifiers:
- migration camps (0281): camp -> density risk
- urban capacity (0282): sanitation and clinics increase caps
- economy shortages (0263): medical supply shortages reduce effective healthcare_cap
- governance failures (0271): unrest reduces compliance and increases spread
- war/raids (0278): wound infections and infrastructure damage risk
- maintenance neglect (0253): degraded water/sanitation raises risk

---

## 4) Outbreak triggering (deterministic)

For each ward and each disease type:
- compute trigger probability:
  - base outbreak_trigger_rate
  - + camp density term
  - + water_quality deficit (for WATERBORNE)
  - + raid pressure (for WOUND_INFECTION)
  - + phase multiplier (P2 higher)
  - - healthcare/sanitation mitigations

Trigger deterministically:
- `pseudo_rand01(salt|day|ward|disease) < p_trigger`

When triggered:
- set outbreak intensity to small start (e.g., 0.10)
- emit OUTBREAK_STARTED event.

---

## 5) Outbreak evolution (bounded dynamics)

Each update:
- outbreaks intensify or decay based on:
  - current intensity
  - mitigation caps
  - compliance proxy (legitimacy)
  - camps and density
  - corridor spillover (spread)

Simple rule:
- `intensity += growth - recovery - mitigation`
Clamp 0..1.

When intensity crosses 0.7 for first time:
- emit OUTBREAK_PEAK.

When intensity falls below 0.05:
- clear outbreak and emit OUTBREAK_ENDED.

---

## 6) Spread across corridors (macro)

Use corridor adjacency (0261):
- for each corridor connecting ward A and B:
  - spillover = spread_strength * (outbreak_intensity_A - outbreak_intensity_B)+
  - apply bounded transfer to B

Use TopK corridors by traffic to keep bounded, or just corridors count is small enough.

---

## 7) Consequences (how health affects the world)

Compute per ward an “effective labor multiplier”:
- `labor_mult = 1 - 0.3*chronic_burden - 0.6*sum(outbreaks)`
Clamp 0.3..1.0.

Apply to:
- production throughput (refining, construction workforce),
- logistics capacity (couriers),
- enforcement capacity (crackdowns/patrols),
- institutional budgets (lower tax yield).

Also:
- outbreaks increase unrest and migration displacement pressure:
  - if outbreak intensity high → add DISPLACEMENT_DISEASE to 0281
- outbreaks can trigger incidents (0242/0271):
  - quarantine failures, riots, scapegoating.

Keep v1 minimal: labor_mult + unrest + displacement.

---

## 8) Mitigation actions (policy hooks)

Institutions can respond with:
- increase clinic funding and med stockpiles (ledger spending)
- increase sanitation spending
- impose quarantine policy (reduces spread but increases unrest and customs friction)

Add policy dials:
- `public_health_spend_bias`
- `quarantine_strictness` (0..1)

Implementation:
- health module reads these dials to modify mitigation terms.

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["health"]["outbreaks_active"]`
- `metrics["health"]["avg_chronic_burden"]`
- `metrics["health"]["labor_mult_avg"]`

TopK:
- wards by outbreak intensity
- wards by camp-driven risk

Cockpit:
- ward health page: chronic, outbreaks, caps, water_quality, labor_mult
- outbreak timeline view (recent N events)
- correlation hints: camps vs outbreaks, water quality vs waterborne

Events:
- `OUTBREAK_STARTED`
- `OUTBREAK_PEAK`
- `OUTBREAK_ENDED`

---

## 10) Persistence / seed vault

Export stable:
- `seeds/<name>/health.json` with ward states (sorted).
Optional: omit health_events history for compactness.

---

## 11) Tests (must-have)

Create `tests/test_public_health_epidemics_v1.py`.

### T1. Determinism
- same risk inputs → same outbreak triggers and evolution.

### T2. Camps increase risk
- higher camp leads to higher p_trigger and more outbreaks (bounded).

### T3. Clinics/sanitation mitigate
- increasing healthcare_cap reduces outbreak intensity over time.

### T4. Corridor spread
- outbreak in ward A spills to B deterministically given corridor connection.

### T5. Consequences
- outbreak reduces labor_mult and increases displacement pressure.

### T6. Snapshot roundtrip
- health state persists and continues deterministically.

---

## 12) Codex Instructions (verbatim)

### Task 1 — Add health module + ward health state
- Create `src/dosadi/runtime/health.py` with HealthConfig, WardHealthState, HealthEvent
- Add world.health_by_ward and bounded health_events to snapshots + seeds

### Task 2 — Implement outbreak triggers and evolution
- Deterministic outbreak triggering using risk modifiers from camps, water_quality, raids, and phase
- Update intensities, emit events, clear ended outbreaks

### Task 3 — Implement corridor spread and consequences
- Spread outbreaks via corridor adjacency
- Compute labor multiplier and feed into production/logistics/enforcement capacities
- Add disease displacement pressure into migration module

### Task 4 — Policy hooks + telemetry + tests
- Add institution dials for spending/quarantine
- Add cockpit pages and metrics/topK
- Add `tests/test_public_health_epidemics_v1.py` (T1–T6)

---

## 13) Definition of Done

- `pytest` passes.
- With enabled=True:
  - outbreaks trigger and evolve deterministically,
  - camps and poor sanitation amplify risk,
  - clinics and spending mitigate,
  - health impacts labor, unrest, and migration,
  - health state persists into long-run seeds,
  - cockpit can explain where and why health crises occur.

---

## 14) Next slice after this

**Education & Human Capital v1** — long-run skill formation:
- schools/training halls increase productivity and institutional competence,
- cultural beliefs shape learning,
- and the tech ladder becomes socially constrained.
