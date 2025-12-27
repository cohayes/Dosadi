---
title: Policing_Doctrine_v2_Implementation_Checklist
doc_id: D-RUNTIME-0296
version: 2.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0277   # Crackdown Strategy v1
  - D-RUNTIME-0283   # Public Health & Epidemics v1
  - D-RUNTIME-0286   # Media & Information Channels v1
  - D-RUNTIME-0287   # Counterintelligence & Espionage v1
  - D-RUNTIME-0291   # Wages, Rations & Class Stratification v1
  - D-RUNTIME-0294   # Comms Failure & Jamming v1
---

# Policing Doctrine v2 — Implementation Checklist

Branch name: `feature/policing-doctrine-v2`

Goal: make enforcement style a first-class strategic dial so that:
- “how” you police changes legitimacy, compliance, corruption, and insurgency risk,
- crackdowns can stabilize or radicalize depending on doctrine,
- information, comms, and intel posture alter enforcement effectiveness,
- the empire can slide from rule-of-law to terror policing across phases.

v2 upgrades Law & Enforcement (0265) and Crackdown Strategy (0277) with a doctrine engine.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same doctrine + conditions → same enforcement outcomes.
2. **Bounded.** Ward-level doctrine and capacity; no per-agent policing sim.
3. **Legitimacy tradeoffs.** Force short-run control vs long-run trust choices.
4. **Composable.** Feeds smuggling, espionage, sanctions, labor, and governance failure.
5. **Phase-aware.** P0 favors procedural law; P2 incentivizes coercion/corruption.
6. **Tested.** Doctrine effects, transitions, persistence.

---

## 1) Doctrine model (v2)

Represent doctrine as a weighted mix of 4 postures (sum=1):

1) `COMMUNITY` — trust-building, local mediation, intelligence via cooperation
2) `PROCEDURAL` — rule-of-law, due process, predictable enforcement
3) `MILITARIZED` — high force, patrol density, deterrence through presence
4) `TERROR` — collective punishment, fear, arbitrary violence (effective short-run, radicalizing)

Each posture defines multipliers:
- detection and arrest effectiveness
- corruption susceptibility
- collateral harm
- legitimacy delta
- insurgency recruitment delta (future slice, but provide hooks now)

Additionally, define 3 operational dials:
- `inspection_intensity` (0..1)
- `informant_reliance` (0..1)
- `force_threshold` (0..1)

---

## 2) Data structures

Create `src/dosadi/runtime/policing.py`

### 2.1 Config
- `@dataclass(slots=True) class PolicingConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 7`
  - `deterministic_salt: str = "policing-v2"`
  - `doctrine_change_limit: float = 0.10`   # max shift per week
  - `corruption_drift_p2: float = 0.02`
  - `backlash_scale: float = 0.25`
  - `effect_scale: float = 0.20`

### 2.2 Ward policing state
- `@dataclass(slots=True) class WardPolicingState:`
  - `ward_id: str`
  - `doctrine_mix: dict[str, float] = field(default_factory=dict)`  # COMMUNITY/PROCEDURAL/MILITARIZED/TERROR
  - `inspection_intensity: float = 0.5`
  - `informant_reliance: float = 0.5`
  - `force_threshold: float = 0.5`
  - `corruption: float = 0.0`                # 0..1
  - `capacity_effective: float = 1.0`        # staffing and morale multiplier
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.policing_cfg`
- `world.policing_by_ward: dict[str, WardPolicingState]`

Persist in snapshots and seeds.

---

## 3) Capacity inputs (staffing, comms, intel)

Compute capacity_effective per ward:
- staffing ratio of guards/admin (0290)
- comms status (0294) affects coordination and response time
- espionage/informants (0287) affects actionable intel
- labor actions (0289) in guards union reduce availability

Expose helper:
- `get_policing_capacity(world, ward_id, day) -> float`

---

## 4) Doctrine selection (weekly)

Institutions choose doctrine changes based on:
- smuggling/violations (0276/0295)
- unrest/hardship/inequality (0291)
- raids/war proximity (0278)
- legitimacy trend (0269/0273 proxies)
- leadership ideology (0285) (authoritarian axes push toward militarized/terror)

Implement:
- `update_policing_doctrine(world, ward_id, day)`

Rules:
- if raids high → shift toward MILITARIZED
- if legitimacy fragile and hardship high → COMMUNITY/PROCEDURAL recommended
- if governance failing and leadership authoritarian → TERROR increases
Limit per-week change by doctrine_change_limit; deterministic.

---

## 5) Applying doctrine to enforcement outcomes

Policing impacts:
- customs seizures (0275/0295)
- smuggling crackdown outcomes (0277)
- espionage detection (0287)
- general crime proxy (future)

Implement doctrine multipliers:
- `effective_detection = capacity * f(doctrine_mix, informant_reliance)`
- `effective_suppression = capacity * f(doctrine_mix, force_threshold)`
- `collateral_harm = capacity * f(doctrine_mix)`
- `corruption_gain = f(doctrine_mix, inspection_intensity, p2)`

Outputs:
- crackdown success probability (increase)
- seizure rate (increase)
- but legitimacy delta:
  - COMMUNITY/PROCEDURAL positive or neutral
  - MILITARIZED negative small
  - TERROR negative large; increases backlash and insurgency seed

Backlash:
- increases unrest and smuggling adaptation
- increases future recruitment potential (hook for insurgency slice)

---

## 6) Corruption dynamics

Weekly:
- corruption increases with:
  - low procedural share
  - high informant reliance (blackmail economy)
  - high inspection intensity without accountability
  - patronage networks (0292)
- corruption decreases with:
  - procedural/oversight spending (new budget line)
  - successful prosecutions (rare, deterministic)

Expose:
- `policing_corruption_index` per ward for other modules.

---

## 7) Incidents triggered by doctrine extremes

Use Incident Engine (0242):
- COMMUNITY: `MEDIATION_SUCCESS` (reduces unrest)
- MILITARIZED: `PATROL_SHOOTING` (moderate backlash)
- TERROR: `MASS_ARREST`, `DISAPPEARANCES`, `BLOOD_FEUD` (high backlash)
- PROCEDURAL: `HIGH_PROFILE_TRIAL` (legitimacy boost, slower suppression)

v2 minimal: a small set of incidents tied to thresholds.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["policing"]["avg_procedural"]`
- `metrics["policing"]["avg_terror"]`
- `metrics["policing"]["corruption_avg"]`
- `metrics["policing"]["seizure_rate_proxy"]`
- `metrics["policing"]["backlash_proxy"]`

TopK:
- wards with highest terror share
- wards with fastest corruption growth
- wards with doctrine oscillation

Cockpit:
- ward policing page: doctrine mix, dials, capacity inputs, predicted effects
- timeline of doctrine shifts vs incidents
- overlay: smuggling strength vs policing doctrine vs seizures

Events:
- `DOCTRINE_SHIFTED`
- `POLICING_CORRUPTION_SPIKE`
- `BACKLASH_SPIKE`
- `ENFORCEMENT_SUCCESS`
- `ENFORCEMENT_OVERREACH`

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/policing.json` with ward doctrine and corruption.

---

## 10) Tests (must-have)

Create `tests/test_policing_doctrine_v2.py`.

### T1. Determinism
- same inputs → same doctrine shifts and effects.

### T2. Raid pressure shifts militarized
- raids increase militarized share monotonically.

### T3. Terror reduces legitimacy and increases backlash
- increasing terror share increases backlash and reduces legitimacy proxy deterministically.

### T4. Procedural reduces corruption drift
- higher procedural share reduces corruption growth.

### T5. Comms failure reduces effectiveness
- comms outages reduce detection and crackdown success.

### T6. Snapshot roundtrip
- doctrine and corruption persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add policing module + ward policing state
- Create `src/dosadi/runtime/policing.py` with PolicingConfig and WardPolicingState
- Add world.policing_by_ward to snapshots + seeds

### Task 2 — Compute effective policing capacity
- Use staffing ratios (guards/admin), comms status, and labor modifiers to compute capacity_effective

### Task 3 — Implement doctrine update and effect multipliers
- Weekly doctrine shifts limited by doctrine_change_limit and deterministic scoring
- Produce enforcement effectiveness, collateral harm, legitimacy delta, corruption drift, and backlash proxy

### Task 4 — Integrate with crackdowns, customs, smuggling, and espionage
- Use policing multipliers to adjust seizure and crackdown success and espionage detection

### Task 5 — Cockpit + tests
- Add policing dashboards and doctrine timelines
- Add `tests/test_policing_doctrine_v2.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - wards shift doctrine in response to raids, hardship, ideology, and legitimacy,
  - enforcement effectiveness and corruption/backlash respond realistically,
  - doctrine extremes trigger incidents,
  - policing style becomes a lever for long-run stability vs collapse,
  - cockpit explains “why enforcement worked (or backfired).”

---

## 13) Next slice after this

**Terror, Insurgency & Counterinsurgency v1** — cell networks and suppression spirals:
- recruitment pools from hardship, camps, and terror policing,
- clandestine ops and reprisals,
- and fragmentation into warlordism when control fails.
