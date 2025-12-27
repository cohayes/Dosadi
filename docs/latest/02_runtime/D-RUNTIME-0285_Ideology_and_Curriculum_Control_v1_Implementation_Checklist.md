---
title: Ideology_and_Curriculum_Control_v1_Implementation_Checklist
doc_id: D-RUNTIME-0285
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0284   # Education & Human Capital v1
---

# Ideology & Curriculum Control v1 — Implementation Checklist

Branch name: `feature/ideology-curriculum-control-v1`

Goal: make education a contested terrain so that:
- factions compete to shape curriculum and “acceptable knowledge,”
- propaganda and censorship alter civics and tech diffusion,
- culture wars gain an institutional lever,
- seeds diverge politically even with similar resources.

v1 is macro curriculum control, not classroom-level narratives.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same curriculum outcomes.
2. **Bounded.** Ward-level aggregates; TopK factions; no per-agent persuasion loops.
3. **Two-sided tradeoffs.** Control boosts cohesion but harms innovation and trust.
4. **Phase-aware.** P0 pluralism; P2 coercion and censorship.
5. **Auditable.** We can explain who captured curriculum and why.
6. **Tested.** Influence contests, education effects, tech diffusion impacts, persistence.

---

## 1) Concept model

Curriculum control is modeled as:
- **influence shares** over the ward’s education institutions,
- a resulting **curriculum profile** that biases domain learning and beliefs.

Actors:
- state institutions (official curriculum),
- factions (guilds, clergy, military, raiders),
- cultural currents (0270) as background force.

Outputs:
- adjust education domain gains (0284),
- adjust civics/trust and legitimacy dynamics (0269/0271),
- adjust tech adoption rate and competence gating (0268/0284),
- adjust smuggling tolerance / black-market norms (0270/0276).

---

## 2) Curriculum axes (v1)

Represent curriculum as weights over 4 axes (sum ~1):
- `ORTHODOXY` (loyalty, obedience, doctrine)
- `TECHNICISM` (engineering, rational methods)
- `MERCANTILISM` (trade, negotiation, accounting)
- `MILITARISM` (security, discipline, threat posture)

These axes map into education domains:
- TECHNICISM → ENGINEERING, MEDICINE
- MERCANTILISM → TRADE, LOGISTICS
- MILITARISM → SECURITY, LOGISTICS
- ORTHODOXY → CIVICS (but in a specific “obedience” direction)

This keeps the model compact.

---

## 3) Data structures

Create `src/dosadi/runtime/ideology.py`

### 3.1 Config
- `@dataclass(slots=True) class IdeologyConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 14`
  - `max_factions_per_ward: int = 6`
  - `deterministic_salt: str = "ideology-v1"`
  - `capture_rate: float = 0.08`          # influence shift per update
  - `decay_rate: float = 0.02`            # influence drift toward culture baseline
  - `coercion_cost_scale: float = 0.10`   # political cost of harsh control

### 3.2 Ward ideology state
- `@dataclass(slots=True) class WardIdeologyState:`
  - `ward_id: str`
  - `influence: dict[str, float] = field(default_factory=dict)`  # faction_id -> 0..1 (sum<=1)
  - `state_share: float = 0.5`
  - `curriculum_axes: dict[str, float] = field(default_factory=dict)` # ORTHODOXY/TECHNICISM/...
  - `censorship_level: float = 0.0`          # 0..1
  - `propaganda_intensity: float = 0.0`      # 0..1
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.ideology_cfg`
- `world.ideology_by_ward: dict[str, WardIdeologyState]`

Persist in snapshots and seeds.

---

## 4) Inputs for the influence contest

Per ward, identify TopK relevant factions:
- the ward controller (0266),
- strongest local factions by territory/influence,
- institutions (clergy/guild/military) derived from Institution Evolution (0269),
- plus “state” share.

Influence shifts depend on:
- faction budgets for propaganda/education capture (0273),
- enforcement pressure and coercion (0265/0277),
- culture baseline (0270),
- war pressure (0278) (militarism rises),
- economic class conflict (0263/0270).

---

## 5) Contest resolution (semi-monthly)

Implement:
- `run_ideology_update(world, day)`

Steps per ward:
1) Read institution policy dials:
- `curriculum_control_strictness` (0..1)
- `propaganda_budget_bias` (-0.5..+0.5)
- `censorship_bias` (-0.5..+0.5)

2) Determine spend:
- state spends on propaganda/censorship via ledger:
  - `PAY_PROPAGANDA`
  - `PAY_CENSORSHIP`
- factions may also spend if they have budgets (optional v1: use a simple “faction influence budget” proxy)

3) Influence update:
- compute target shares based on spend, legitimacy, coercion, and culture alignment
- move influence toward targets by capture_rate
- apply decay toward culture baseline by decay_rate

4) Curriculum axes:
- compute weighted sum of faction ideology vectors + state ideology vector
- apply censorship: increases ORTHODOXY and decreases TECHNICISM diffusion
- store curriculum_axes.

Bounded: 36 wards x <= max_factions_per_ward.

---

## 6) Effects wiring (what ideology changes)

### 6.1 Education (0284)
Modify domain gains:
- gains *= (1 + axis_weight * domain_affinity) * (1 - censorship_penalty)
Examples:
- TECHNICISM increases ENGINEERING/MEDICINE gains
- ORTHODOXY increases CIVICS gains but reduces open inquiry (engineering cap growth)
- MILITARISM increases SECURITY gains, reduces CIVICS pluralism

Also modify `education_access`:
- high orthodoxy/censorship reduces access (elite capture), lowering broad human capital.

### 6.2 Tech ladder diffusion (0268/0284)
- high censorship reduces probability of unlocking “dangerous” tech nodes (e.g., comms, explosives analogs) (keep it abstract)
- TECHNICISM increases unlock success and reduces delays.

### 6.3 Governance and trust (0269/0271)
- propaganda can increase short-run legitimacy if aligned with culture,
- but high censorship reduces trust and increases long-run instability (P2).

### 6.4 Culture Wars (0270)
- curriculum axes feed back into culture drift:
  - repeated TECHNICISM increases pro-tech norms
  - repeated ORTHODOXY increases xenophobia/conformity norms
Keep v1 minimal: a small drift term.

---

## 7) Incidents: curriculum conflict events (optional v1)

Use Incident Engine (0242):
- “Teacher Purge”
- “Book Smuggling”
- “Student Riot”
- “Guild Capture of Academy”
Trigger when:
- rapid influence shifts
- high censorship + high TECHNICISM demand
- faction contest intensity high

v1 can just record events and adjust unrest/legitimacy.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["ideology"]["avg_censorship"]`
- `metrics["ideology"]["curriculum_axes_avg"]`
- `metrics["ideology"]["capture_events"]`

TopK:
- wards by censorship level
- wards by TECHNICISM dominance
- wards with fastest ideology swings

Cockpit:
- ward ideology page: faction shares, state share, axes, censorship/propaganda
- “curriculum capture map” overlay
- “why tech stalled” view: censorship + ideology penalties

Events:
- `CURRICULUM_SHIFT`
- `CENSORSHIP_RAISED`
- `FACTION_CAPTURED_SCHOOL`
- `PROPAGANDA_CAMPAIGN`

---

## 9) Persistence / seed vault

Export stable:
- `seeds/<name>/ideology.json` sorted by ward_id.

---

## 10) Tests (must-have)

Create `tests/test_ideology_curriculum_control_v1.py`.

### T1. Determinism
- same budgets/culture → same influence and axes.

### T2. Capture dynamics
- increased propaganda spend shifts influence shares toward spender.

### T3. Censorship tradeoff
- higher censorship reduces tech-related education gains and delays tech unlocks.

### T4. Governance effects
- high coercion/censorship increases unrest over time (bounded).

### T5. Snapshot roundtrip
- ideology state persists across snapshot/load and seed export.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add ideology module + ward ideology state
- Create `src/dosadi/runtime/ideology.py` with IdeologyConfig and WardIdeologyState
- Add world.ideology_by_ward to snapshots + seeds

### Task 2 — Implement semi-monthly influence contest
- Determine TopK factions per ward
- Apply spend-driven influence shifts with capture_rate and decay toward culture baseline
- Compute curriculum axes and store censorship/propaganda levels

### Task 3 — Wire ideology into education, tech, and governance
- Modify education domain gains using curriculum axes and censorship penalties
- Apply tech diffusion delays/blocks based on censorship and TECHNICISM
- Apply legitimacy/unrest/trust modifiers

### Task 4 — Cockpit + tests
- Add ideology dashboards and overlays
- Add `tests/test_ideology_curriculum_control_v1.py` (T1–T5)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - curriculum control evolves deterministically via faction contests,
  - censorship/propaganda trade off cohesion vs innovation,
  - education and tech adoption respond to ideology,
  - system produces believable culture war feedback loops over centuries,
  - cockpit explains “who controls what” and why.

---

## 13) Next slice after this

**Media & Information Channels v1** — how ideas travel:
- courier news packets, radio relays (tech-gated),
- rumor propagation at scale,
- and information warfare as a strategic layer.
