---
title: Demographic_Dynamics_v1_Implementation_Checklist
doc_id: D-RUNTIME-0309
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0281   # Migration & Refugees v1
  - D-RUNTIME-0282   # Urban Growth & Zoning v1
  - D-RUNTIME-0283   # Public Health & Epidemics v1
  - D-RUNTIME-0284   # Education & Human Capital v1
  - D-RUNTIME-0290   # Workforce Skill Assignment v2
  - D-RUNTIME-0291   # Wages, Rations & Class Stratification v1
  - D-RUNTIME-0307   # Intergenerational Social Mobility v1
---

# Demographic Dynamics v1 — Implementation Checklist

Branch name: `feature/demographic-dynamics-v1`

Goal: add population shape over centuries (macro) so that:
- births, deaths, and household formation shift the labor pool,
- mortality responds to health, scarcity, and war,
- age structure changes education load, military capacity, and legitimacy pressure,
- population growth can outrun infrastructure and trigger phase transitions.

v1 is **cohort-based**, not per-agent reproduction.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same demographic evolution.
2. **Bounded.** Cohorts, not individuals; O(#polities * #cohorts) updates.
3. **Composable.** Hooks into health, education, workforce, mobility, migration, and war.
4. **Legible.** Expose age pyramid and rates.
5. **Phase-aware.** P0 stable growth; P2 shocks and collapse risk.
6. **Tested.** Cohort transitions and persistence.

---

## 1) Concept model

Per polity, maintain an age distribution in cohorts:
- e.g., 0–4, 5–9, …, 70–74, 75+

Each year (or quarterly with annualized rates):
- apply births into the youngest cohort,
- apply age progression (move fraction into next cohort),
- apply deaths via mortality rates modulated by health/scarcity/war.

Also track:
- household formation rate (affects housing demand and zoning pressure),
- dependency ratio (non-working vs working-age),
- and “youth bulge” risk (insurgency/mobility pressure).

---

## 2) Cadence

- Update quarterly for rate drift and shocks.
- Apply cohort transitions annually (or every 360/365 days based on your timebase).

This keeps costs low.

---

## 3) Data structures

Create `src/dosadi/runtime/demographics.py`

### 3.1 Config
- `@dataclass(slots=True) class DemographicsConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 90`      # quarterly
  - `annual_step_days: int = 360`        # match sim timebase convention
  - `deterministic_salt: str = "demographics-v1"`
  - `cohort_years: int = 5`
  - `max_age: int = 80`                 # last cohort is max_age+
  - `base_fertility: float = 0.06`      # births per person-year (tunable)
  - `base_mortality: float = 0.01`
  - `shock_scale: float = 0.35`

### 3.2 Polity demographics state
- `@dataclass(slots=True) class PolityDemographics:`
  - `polity_id: str`
  - `cohort_pop: list[float] = field(default_factory=list)`  # index 0 is 0-4
  - `fertility: float = 0.0`          # current annual fertility rate
  - `mortality: list[float] = field(default_factory=list)`   # per cohort annual mortality
  - `household_rate: float = 0.0`     # new households per person-year
  - `dependency_ratio: float = 0.0`
  - `youth_bulge: float = 0.0`
  - `last_annual_year: int = 0`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Demographic event (bounded)
- `@dataclass(slots=True) class DemographicEvent:`
  - `day: int`
  - `polity_id: str`
  - `kind: str`                       # BABY_BOOM|FAMINE|EPIDEMIC|WAR_LOSSES|MIGRATION_WAVE
  - `magnitude: float`
  - `effects: dict[str, object] = field(default_factory=dict)

World stores:
- `world.demographics_cfg`
- `world.demographics_by_polity: dict[str, PolityDemographics]`
- `world.demographic_events: list[DemographicEvent]` (bounded)

Persist in snapshots and seeds.

---

## 4) Initialization

Seed cohort distribution from:
- founding wakeup baseline (initial adult-heavy cohort if colony ship)
- or a stable pyramid default.

Create helper:
- `make_default_cohorts(total_pop, shape="colony_adult_heavy"|"stable_pyramid")`

Ensure sum matches polity population estimate if available.

---

## 5) Rate computation (quarterly drift)

Compute modifiers from existing systems:
- health burden and epidemics (0283) → mortality increases
- wages/rations and scarcity (0291/0263) → fertility decreases, mortality increases
- education access (0284) → fertility decreases slightly (optional), youth outcomes improve
- war/civil war (0278/0298) → mortality spikes for working-age cohorts
- migration (0281) → cohort inflows (age-biased)

Compute:
- `fertility = base_fertility * f(stability, rations, housing, culture)` (bounded)
- `mortality[cohort] = base curve * f(health, scarcity, war)` (bounded per cohort)

Compute household formation:
- increases with young adult share and mobility aspirations, decreases with housing scarcity (0282).

---

## 6) Annual cohort step

When annual boundary crossed:
- births = fertility * total_pop
  - add to cohort 0 (0–4)
- deaths per cohort = cohort_pop[i] * mortality[i]
  - subtract
- aging:
  - move a fraction from cohort i to i+1 (e.g., 1/cohort_years per year), or
  - shift the entire cohort every 5 years if you align years to cohorts (keep smooth v1).
- migration:
  - apply net migration inflow/outflow by cohort from 0281 (if available)

Update derived stats:
- working_age = cohorts 15–64
- dependents = cohorts 0–14 + 65+
- dependency_ratio = dependents / max(working_age, eps)
- youth_bulge = share of 15–24 (proxy)

Emit summary event:
- `DEMOGRAPHICS_ANNUAL_STEP`

---

## 7) Integration hooks (v1)

- Workforce (0290): working-age pool size scales labor capacity and staffing constraints
- Education (0284): school demand = cohorts 5–17
- Urban growth (0282): household formation drives housing demand and zoning expansion pressure
- Public health (0283): mortality modifiers and epidemic susceptibility
- Mobility (0307): youth bulge increases competition, affects mobility trap risk
- Legitimacy (0299): high dependency ratio increases fiscal strain (tie to 0273/0291)

Keep v1 scalar: provide a few computed inputs per polity.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["demo"]["population_total"]`
- `metrics["demo"]["fertility"]`
- `metrics["demo"]["dependency_ratio"]`
- `metrics["demo"]["youth_bulge"]`

Cockpit:
- age pyramid (text histogram ok)
- cohort table
- timeline of fertility/mortality and major events
- “pressure dashboard”: school seats needed, workforce capacity, housing demand

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/demographics.json` with cohorts and rates.

---

## 10) Tests (must-have)

Create `tests/test_demographic_dynamics_v1.py`.

### T1. Determinism
- same modifiers → same cohort evolution.

### T2. Scarcity increases mortality and reduces fertility
- low rations increase deaths and reduce births.

### T3. Epidemic shock increases mortality in target cohorts
- epidemic raises mortality and reduces population deterministically.

### T4. Aging conserves mass (minus deaths)
- cohort progression maintains total population consistent with births-deaths-migration.

### T5. Derived stats compute correctly
- dependency ratio and youth bulge reflect cohorts.

### T6. Snapshot roundtrip
- demographics persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add demographics module + state
- Create `src/dosadi/runtime/demographics.py` with DemographicsConfig, PolityDemographics, DemographicEvent
- Add demographics_by_polity and demographic_events to snapshots + seeds

### Task 2 — Implement quarterly rate drift
- Compute fertility/mortality curves from health, scarcity, war, housing, and migration signals

### Task 3 — Implement annual cohort step
- Apply births, deaths, aging, and migration; compute derived stats; emit summary event

### Task 4 — Wire demographic outputs into workforce/education/housing pressure
- Provide scalar outputs consumed by staffing, education capacity, and zoning expansion planners

### Task 5 — Cockpit + tests
- Add age pyramid and pressure dashboard
- Add `tests/test_demographic_dynamics_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - polities have cohort populations that evolve annually,
  - fertility/mortality respond to shocks and scarcity,
  - demographic pressures feed into labor, schools, housing, and legitimacy,
  - seeds diverge into growing, stable, or collapsing populations,
  - cockpit explains “who the empire is made of.”

---

## 13) Next slice after this

**Climate Control & Habitat Engineering v1** — the built environment fights the planet:
- ward sealing quality, dehumidification, heat load,
- and infrastructure arms races that shape survival and politics.
