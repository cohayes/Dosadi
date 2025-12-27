---
title: Workforce_Skill_Assignment_v2_Implementation_Checklist
doc_id: D-RUNTIME-0290
version: 2.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0247   # Focus Mode Awake vs Ambient v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0262   # Resource Refining Recipes v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0284   # Education & Human Capital v1
  - D-RUNTIME-0289   # Labor Unions & Guild Politics v1
---

# Workforce Skill Assignment v2 — Implementation Checklist

Branch name: `feature/workforce-skill-assignment-v2`

Goal: make staffing competence-constrained so that:
- facilities require staffing “skill bundles” to operate at full throughput,
- human capital (0284) translates into a scarce specialist pool,
- labor actions (0289) can target critical staffing categories,
- output bottlenecks feel “real” (not just materials).

v2 is macro staffing at ward/facility level, not per-agent job scheduling.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same staffing allocation.
2. **Bounded.** Ward-level pools and facility staffing lines; no agent-level assignment needed.
3. **Composable.** Affects production, maintenance, logistics, enforcement, and health.
4. **Graceful degradation.** Partial staffing yields reduced throughput, not binary off.
5. **Auditable.** We can explain why a facility is underperforming (“missing engineers”).
6. **Tested.** Allocation, throughput mapping, persistence, and edge cases.

---

## 1) Concept model

Each ward has **workforce pools** per skill category:
- Engineers, Medics, Couriers, Builders, Refiners, Guards, Administrators, etc.

Pools are derived from:
- population (migration/urban growth),
- human capital domain levels (0284),
- health labor multiplier (0283),
- labor org modifiers (0289),
- and phase/institution policies.

Facilities declare staffing requirements:
- required “FTE” (full-time equivalents) per category
- optional minimum thresholds and quality weights.

The staffing system:
- allocates limited pools across facilities and tasks (TopK),
- produces an “effective staffing ratio” per facility,
- and other modules use it as a throughput multiplier.

---

## 2) Data structures

Create `src/dosadi/runtime/workforce.py`

### 2.1 Config
- `@dataclass(slots=True) class WorkforceConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 3`
  - `deterministic_salt: str = "workforce-v2"`
  - `max_facilities_scored_per_ward: int = 40`
  - `priority_topk: int = 18`
  - `min_staffing_floor: float = 0.20`      # facilities never drop below unless 0 pool
  - `allocation_step: float = 0.10`         # chunking for greedy allocation

### 2.2 Workforce pools
- `@dataclass(slots=True) class WardWorkforcePools:`
  - `ward_id: str`
  - `pools: dict[str, float] = field(default_factory=dict)`      # skill -> FTE available
  - `reserved: dict[str, float] = field(default_factory=dict)`   # reserved for emergencies
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

### 2.3 Facility staffing snapshot
- `@dataclass(slots=True) class FacilityStaffing:`
  - `facility_id: str`
  - `ward_id: str`
  - `req: dict[str, float]`                 # skill -> FTE needed for full ops
  - `alloc: dict[str, float] = field(default_factory=dict)
  - `ratio: float = 0.0`                    # 0..1 effective staffing ratio
  - `priority: float = 0.0`
  - `last_update_day: int = -1`

World stores:
- `world.workforce_cfg`
- `world.workforce_by_ward: dict[str, WardWorkforcePools]`
- `world.staffing_by_facility: dict[str, FacilityStaffing]`

Persist in snapshots and seeds (pools; facility staffing optional to recompute on load).

---

## 3) Skill taxonomy (v2)

Define a small canonical set (strings):
- `ENGINEER`
- `BUILDER`
- `REFINER`
- `COURIER`
- `MEDIC`
- `ADMIN`
- `GUARD`
- `MAINTAINER`

Map human capital domains (0284) into pool composition:
- ENGINEERING → ENGINEER + MAINTAINER
- LOGISTICS → COURIER + ADMIN (routing/dispatch)
- MEDICINE → MEDIC
- CIVICS → ADMIN (bureaucracy/coordination)
- SECURITY → GUARD
- TRADE → ADMIN (accounting/markets)

Mapping is configurable, but deterministic.

---

## 4) Pool computation (every 3 days)

Implement:
- `compute_workforce_pools(world, day)`

Inputs:
- ward pop and camp (0281) (camps contribute low-skilled workforce but high instability)
- health labor multiplier (0283)
- labor slowdowns/strikes (0289) by sector reduce availability
- education levels (0284) increase skilled fraction
- institutions: reserve dials (e.g., keep guards reserved)

Simple v2 formula:
- base_fte = pop * participation_rate (e.g., 0.35)
- skilled_fte share = f(education_domain_levels)
- distribute into pools using mapping weights
- apply labor_mult and strike reductions by skill group
- reserve fraction for emergency response (raids/epidemics)

---

## 5) Facility staffing requirements

Extend facility definitions (0252/0272) to include:
- `staff_req: dict[str, float]`
- `staff_affinity: dict[str, float]` (optional weights)
- `staff_min: dict[str, float]` (optional minimum per skill)

Examples:
- Water plant: ENGINEER 4, MAINTAINER 6, GUARD 2
- Clinic: MEDIC 6, ADMIN 2
- Refinery: REFINER 8, ENGINEER 2, GUARD 2
- Depot: ADMIN 3, COURIER 2, GUARD 1
- Relay tower: ADMIN 2, ENGINEER 1, GUARD 1

Construction sites:
- BUILDER + ENGINEER + MAINTAINER depending on project tier

---

## 6) Allocation algorithm (bounded, deterministic)

Implement:
- `allocate_staffing_for_ward(world, ward_id, day)`

Steps:
1) Build a list of staffing “demands”:
- active facilities
- active construction projects (0258)
- critical services (enforcement, quarantine, escorts)

2) Score each demand with priority:
- life support (water/air/health) highest
- security next during war/raids
- logistics next if shortages high
- industry next
- civic/education next

Priority influenced by:
- institution policy dials
- phase
- current crises

3) Greedy allocate in chunks (allocation_step) across TopK demands:
- stable sort by priority then facility_id
- allocate required skills until pools depleted
- compute facility ratio:
  - ratio = min over skills (alloc[k]/req[k]) smoothed with min_staffing_floor

4) Store FacilityStaffing entries.

Bounded by max_facilities_scored_per_ward and priority_topk.

---

## 7) Wiring to other modules

Other modules should read staffing ratios:

- Production/refining (0262/0263): throughput *= staffing_ratio
- Maintenance/wear (0253/0254): repair capacity *= staffing_ratio of maintenance facilities
- Logistics delivery (0238/0246): courier capacity *= staffing ratio of couriers/depots
- Enforcement/crackdowns (0265/0277): enforcement capacity *= staffing ratio of guard/admin
- Health (0283): healthcare_cap effectiveness *= staffing ratio of clinics
- Education (0284): teacher_pool growth *= staffing ratio of schools/academies

Keep multipliers bounded.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["workforce"]["fte_total"]`
- `metrics["workforce"]["fte_by_skill"]`
- `metrics["workforce"]["critical_facilities_understaffed"]`
- `metrics["workforce"]["avg_staffing_ratio"]`

TopK:
- understaffed water/air/clinic facilities
- wards with biggest engineer deficit
- projects delayed due to builder shortage

Cockpit:
- ward workforce page: pools, reserves, allocations by facility
- facility view: req vs alloc, missing skills, ratio
- “bottleneck explainer”: map shortages to skills to facilities

Events:
- `WORKFORCE_ALLOCATED`
- `FACILITY_UNDERSTAFFED`
- `PROJECT_DELAYED_SKILL_SHORTAGE`

---

## 9) Persistence / seed vault

Persist:
- workforce pools per ward (stable)
Optionally recompute facility staffing after load to reduce seed size.

Export:
- `seeds/<name>/workforce.json`

---

## 10) Tests (must-have)

Create `tests/test_workforce_skill_assignment_v2.py`.

### T1. Determinism
- same pools/demands → same allocations.

### T2. Priority protects life support
- water/clinic facilities get staffed before refineries under shortage.

### T3. Partial staffing reduces throughput
- staffing ratio scales outputs deterministically.

### T4. Strike reduces availability
- labor strike in refining reduces REFINER pool and refinery staffing.

### T5. Health penalty reduces pools
- outbreak reduces total available FTE and staffing ratios.

### T6. Snapshot roundtrip
- pools persist and allocations remain consistent after recompute.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add workforce module + pools
- Create `src/dosadi/runtime/workforce.py` with WorkforceConfig and WardWorkforcePools
- Add world.workforce_by_ward to snapshots + seeds

### Task 2 — Add staffing requirements to facility definitions
- Extend facility types to include staff_req per skill
- Add sane defaults for existing facilities

### Task 3 — Implement pool computation and staffing allocation
- Compute skill pools from pop + human capital + health + labor modifiers
- Allocate staffing greedily by priority with deterministic tie breaks
- Store staffing ratios per facility

### Task 4 — Wire staffing ratios into throughput calculations
- Apply staffing multipliers to refining, logistics, maintenance, enforcement, health, and education

### Task 5 — Cockpit + tests
- Add workforce dashboards and bottleneck explainer
- Add `tests/test_workforce_skill_assignment_v2.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - wards compute skill pools deterministically,
  - facilities and projects compete for scarce specialists,
  - life support is protected by priority rules,
  - staffing ratios explain throughput and delays,
  - labor politics can choke critical skills,
  - seeds diverge due to competence and staffing bottlenecks.

---

## 13) Next slice after this

**Wages, Rations & Class Stratification v1** — who gets what, and why:
- household tiers (macro),
- ration differentials as policy,
- and class pressure feeding labor militancy and ideology.
