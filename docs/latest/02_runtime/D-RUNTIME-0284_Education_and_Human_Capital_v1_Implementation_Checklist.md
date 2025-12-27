---
title: Education_and_Human_Capital_v1_Implementation_Checklist
doc_id: D-RUNTIME-0284
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0268   # Tech Ladder v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0282   # Urban Growth & Zoning v1
  - D-RUNTIME-0283   # Public Health & Epidemics v1
---

# Education & Human Capital v1 — Implementation Checklist

Branch name: `feature/education-human-capital-v1`

Goal: add a macro “human capital” layer that:
- increases productivity and institutional competence over decades,
- gates tech adoption socially (not just resource/recipe),
- makes cultural beliefs shape learning rates and curriculum priorities,
- creates long-run divergence between seeds over 200-year horizons.

v1 is **ward-level skills**, not per-agent schooling.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same learning and output effects.
2. **Bounded.** Ward-level aggregates; no per-agent training loops required.
3. **Compositional.** Education impacts production, enforcement, governance, and tech.
4. **Policy-driven.** Institutions decide priorities (engineering vs civics vs military).
5. **Culture-constrained.** Culture can accelerate or suppress certain learning domains.
6. **Tested.** Learning update, facility effects, tech gating, persistence.

---

## 1) Concept model

Each ward maintains a small vector of **human capital** domains, e.g.:
- `ENGINEERING`
- `LOGISTICS`
- `CIVICS`
- `MEDICINE`
- `SECURITY`
- `TRADE`

Human capital:
- grows via schooling/training facilities and spending,
- decays slowly from neglect, war, and health crises,
- amplifies outputs (productivity multipliers),
- provides **competence** required to unlock higher tech tiers reliably.

This converts “tech ladder” from purely material gating into a social, learnable capacity.

---

## 2) Facilities (v1)

Add 3 education-related facility types (in facility/recipe systems):
1) `SCHOOLHOUSE_L1`
- basic literacy/numeracy, increases CIVICS and TRADE slightly

2) `TRAINING_HALL_L1`
- practical training, increases LOGISTICS, SECURITY

3) `ACADEMY_L2`
- advanced instruction, increases ENGINEERING, MEDICINE, CIVICS
- tech gate required; expensive upkeep

These plug into Urban Growth (0282) as civic candidates.

---

## 3) Data structures

Create `src/dosadi/runtime/education.py`

### 3.1 Config
- `@dataclass(slots=True) class EducationConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 14`            # semi-monthly
  - `deterministic_salt: str = "edu-v1"`
  - `base_gain_per_update: float = 0.01`
  - `base_decay_per_update: float = 0.003`
  - `max_level: float = 1.0`                  # 0..1 per domain
  - `health_penalty_scale: float = 0.4`       # epidemics reduce learning
  - `war_penalty_scale: float = 0.3`          # raids disrupt learning

### 3.2 Ward education state
- `@dataclass(slots=True) class WardEducationState:`
  - `ward_id: str`
  - `domains: dict[str, float] = field(default_factory=dict)`  # domain -> 0..1
  - `teacher_pool: float = 0.0`         # proxy for instructor availability
  - `spend_last_update: float = 0.0`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.education_cfg`
- `world.education_by_ward: dict[str, WardEducationState]`

Persist in snapshots and seeds.

---

## 4) Institution policy dials

Extend `WardInstitutionPolicy` (0269) with:
- `education_spend_bias: float = 0.0`           # -0.5..+0.5
- `education_priority: dict[str, float]`        # weights per domain (sums ~1)
- `education_access: float = 0.7`               # 0..1 (how inclusive; impacts civics vs elite capture)
- `apprenticeship_bias: float = 0.3`            # 0..1 (on-the-job training emphasis)

Cultural constraints (0270) provide modifiers:
- `anti_intellectualism` dampens ENGINEERING/MEDICINE gains
- `militarism` boosts SECURITY gains, dampens CIVICS
- `merchant_ethos` boosts TRADE/LOGISTICS
- `guild_control` shifts access lower but increases specialized gains

(v1 can use a small lookup if culture fields differ.)

---

## 5) Update loop (semi-monthly)

Implement:
- `run_education_update(world, day)`

For each ward:
1) Compute effective spend:
- base = institution budget fraction (0273) scaled by education_spend_bias
- cap by available balance (ledger)
- post transaction reason `PAY_EDUCATION`

2) Compute facility boost:
- presence of SCHOOLHOUSE/TRAINING_HALL/ACADEMY
- teacher_pool increases with facilities and sustained spend

3) Compute penalties:
- health outbreaks (0283) reduce gains
- raids/unrest (0278/0271) reduce gains
- severe shortages (0263) reduce attendance and supplies

4) Allocate gains across domains:
- weights = policy priority * cultural modifier * facility affinity
- gain = base_gain_per_update * f(spend, teacher_pool) * (1 - penalty)
- domains[d] += gain * weight

5) Apply decay:
- domains[d] -= base_decay_per_update * (1 + penalty_from_neglect)
Clamp 0..max_level.

Bounded: 36 wards x small domain vector.

---

## 6) Output effects (how human capital matters)

Expose ward-level multipliers used by other systems:

- **Engineering**:
  - reduces construction times and maintenance wear penalties
  - increases chance of successful corridor improvements (0267)

- **Logistics**:
  - improves delivery success and reduces delays (0238/0246/0261)
  - improves depot policies adherence (0257)

- **Civics**:
  - increases legitimacy stability; reduces governance failure probability (0271)
  - improves treaty compliance and diplomacy capacity (0274/0280)

- **Medicine**:
  - increases healthcare_cap effectiveness and reduces outbreak duration (0283)

- **Security**:
  - improves crackdown execution and raid defense (0277/0278/0279)

- **Trade**:
  - improves market efficiency; reduces price volatility (0263)

Implementation style:
- provide helper `ward_competence(world, ward_id) -> dict[str, float]`
- other modules multiply by bounded transforms of the level.

Keep v1 conservative.

---

## 7) Tech ladder gating (social constraints)

Add a “competence requirement” layer on tech unlocks (0268):
- each tech node can specify required domains and levels:
  - e.g., `FILTER_PLANT_L2` requires ENGINEERING >= 0.55 and LOGISTICS >= 0.45
- if competence is below threshold:
  - unlock attempts fail deterministically, or
  - unlock is delayed / costs extra.

Implementation suggestion:
- keep existing tech unlock conditions,
- add optional `competence_req` dict to tech nodes.

This makes seeds diverge socially.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["education"]["avg_level_by_domain"]`
- `metrics["education"]["spend_total"]`
- `metrics["education"]["teacher_pool_avg"]`

TopK:
- wards by engineering level
- wards with lowest civics and high unrest
- wards “stuck” on tech due to competence deficits

Cockpit:
- ward education page: domain levels, spend, facilities, modifiers
- “tech blocked by competence” report
- long-run charts (optional): engineering vs maintenance costs

Events:
- `EDU_SPEND`
- `EDU_LEVEL_UP`
- `TECH_UNLOCK_BLOCKED_COMPETENCE`

---

## 9) Persistence / seed vault

Export stable:
- `seeds/<name>/education.json` sorted by ward_id with domains and teacher_pool.

---

## 10) Tests (must-have)

Create `tests/test_education_human_capital_v1.py`.

### T1. Determinism
- same spend/facilities/culture → same domain evolution.

### T2. Facility effect
- adding a schoolhouse increases civics/trade growth vs baseline.

### T3. Penalties apply
- outbreak reduces medicine growth and overall gains deterministically.

### T4. Output effects wiring
- higher logistics reduces delivery delays (smoke test / direct multiplier test).

### T5. Tech competence gating
- tech unlock blocked when competence below threshold; succeeds when above.

### T6. Snapshot roundtrip
- education state persists and continues deterministically.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add education module + ward education state
- Create `src/dosadi/runtime/education.py` with EducationConfig and WardEducationState
- Add world.education_by_ward to snapshots + seeds

### Task 2 — Add facilities and policy dials
- Add SCHOOLHOUSE_L1, TRAINING_HALL_L1, ACADEMY_L2 facility types and recipes (tech gated)
- Extend WardInstitutionPolicy with education spend bias and domain priority weights

### Task 3 — Implement semi-monthly education update
- Pay education spend via ledger
- Compute gains by facilities, spend, culture modifiers, and penalties from health/war/unrest
- Apply decay and clamp; emit events and telemetry

### Task 4 — Wire output multipliers and tech competence gating
- Provide ward_competence helper consumed by logistics/maintenance/governance/health/security
- Add optional competence_req to tech nodes and block/delay unlocks when unmet

### Task 5 — Cockpit + tests
- Add education dashboards and “tech blocked” report
- Add `tests/test_education_human_capital_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - education spending and facilities increase human capital deterministically,
  - health/war shocks degrade learning,
  - human capital amplifies outputs and gates higher tech adoption,
  - state persists into 200-year seeds,
  - cockpit explains education posture and competence bottlenecks.

---

## 13) Next slice after this

**Ideology & Curriculum Control v1** — education becomes contested terrain:
- factions compete to shape curriculum,
- propaganda and censorship alter civics and tech diffusion,
- and culture wars gain an institutional lever.
