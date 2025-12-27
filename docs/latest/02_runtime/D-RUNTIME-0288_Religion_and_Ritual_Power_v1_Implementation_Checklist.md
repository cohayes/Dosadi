---
title: Religion_and_Ritual_Power_v1_Implementation_Checklist
doc_id: D-RUNTIME-0288
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0285   # Ideology & Curriculum Control v1
  - D-RUNTIME-0286   # Media & Info Channels v1
---

# Religion & Ritual Power v1 — Implementation Checklist

Branch name: `feature/religion-ritual-power-v1`

Goal: add an “orthodoxy engine” where:
- rituals operate as coordination technology (shared cadence and meaning),
- clergy form parallel institutions and legitimacy brokers,
- faith networks travel through media channels,
- suppression or capture of religion shapes stability and culture wars.

v1 is macro religion, not personal spirituality per agent.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same ritual calendar and outcomes.
2. **Bounded.** Ward-level aggregates; TopK cults/sects per ward.
3. **Bidirectional power.** Religion can stabilize or destabilize depending on phase.
4. **Composable.** Integrates with ideology, governance, law enforcement, and media.
5. **Explainable.** Rituals have causes, costs, and measurable effects.
6. **Tested.** Ritual scheduling, influence change, suppression tradeoffs, persistence.

---

## 1) Concept model

Religion is represented as:
- **sects** (organized belief networks) with doctrines and alignment vectors,
- **clergy institutions** in wards that can collect tithes and mobilize crowds,
- **ritual calendars** that create synchronized behavior and social cohesion.

Religion impacts:
- legitimacy (positive if aligned with state; negative if hostile),
- civics vs orthodoxy tension (0285),
- compliance with rationing and law (0265/0269),
- recruitment for factions (0266),
- and resilience under crisis (A1/A2/A3 shocks).

---

## 2) Sect archetypes (v1)

Define 4 abstract sect archetypes (each is a “religious faction-like” entity):
- `ORTHODOX_CHURCH` (pro-state, order, obedience)
- `WELL_MYSTICS` (water-sacralization, scarcity ethics, anti-corruption)
- `MARTIAL_CULT` (security worship, raids-as-trial, violent mobilization)
- `HERETIC_NETWORK` (smuggling, forbidden knowledge, anti-state)

Each archetype defines:
- ideology axis vector (0285 axes),
- preferred rituals,
- recruitment conditions (crisis, camps, war),
- and conflict posture with law enforcement.

v1 can implement these as templates.

---

## 3) Data structures

Create `src/dosadi/runtime/religion.py`

### 3.1 Config
- `@dataclass(slots=True) class ReligionConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 7`         # weekly
  - `max_sects_per_ward: int = 4`
  - `deterministic_salt: str = "religion-v1"`
  - `conversion_rate: float = 0.03`
  - `suppression_cost_scale: float = 0.10`
  - `ritual_effect_scale: float = 0.08`

### 3.2 Sect state
- `@dataclass(slots=True) class SectState:`
  - `sect_id: str`
  - `archetype: str`
  - `global_strength: float = 0.0`     # overall empire presence 0..1
  - `doctrine: dict[str, float] = field(default_factory=dict)`  # axes vector, etc.

### 3.3 Ward religion state
- `@dataclass(slots=True) class WardReligionState:`
  - `ward_id: str`
  - `adherence: dict[str, float] = field(default_factory=dict)`   # sect_id -> 0..1 (sum<=1)
  - `clergy_power: dict[str, float] = field(default_factory=dict)` # sect_id -> 0..1
  - `tithe_rate: float = 0.0`           # fraction of local budget flow captured (proxy)
  - `ritual_calendar: dict[str, int] = field(default_factory=dict)` # ritual -> next_day
  - `suppression_level: float = 0.0`    # 0..1
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.religion_cfg`
- `world.sects: dict[str, SectState]`
- `world.religion_by_ward: dict[str, WardReligionState]`

Persist sects and ward religion state in snapshots and seeds.

---

## 4) Rituals (v1)

Define 5 ritual types, each with costs and effects:
1) `WATER_VIGIL`
- increases cohesion and compliance; reduces unrest slightly
- effect stronger during shortages

2) `PUBLIC_PENITENCE`
- increases orthodoxy and legitimacy for aligned sect/state
- increases resentment if suppression is high

3) `MARTIAL_PARADE`
- boosts security capacity perception; increases militarism axis (0285)
- can provoke neighbors (deterrence/war)

4) `HEALING_RITES`
- reduces outbreak intensity marginally (0283), increases trust in clergy

5) `HERESY_GATHERING`
- boosts smuggling tolerance and heretic influence; increases enforcement friction

Rituals are scheduled on the ritual_calendar per ward, deterministic:
- e.g., every 28 days, or triggered by shocks.

---

## 5) Update loop (weekly)

Implement:
- `run_religion_for_week(world, day)`

Per ward:
1) Compute sect adherence drift:
- influenced by:
  - crisis (war, camps, epidemics): increases conversion activity
  - ideology axes and censorship (0285): can suppress heresy
  - institution policy toward religion (new dials)
  - media channels: propaganda and sermons travel (0286)
- apply conversion_rate * (drivers) with deterministic tie breaks.

2) Update clergy_power:
- grows with adherence and funding (tithes) and facilities (temples)
- decays with suppression and raids.

3) Schedule or trigger rituals:
- if shock present (shortage/outbreak/raid), choose ritual from top sects
- else follow periodic cadence.

4) Apply ritual effects on ritual days:
- modify legitimacy/unrest/culture axes/health/security, bounded.

---

## 6) Institutions: suppression vs co-option

Add institution policy dials (0269):
- `religious_tolerance` (0..1) (higher tolerates heresy)
- `state_church_bias` (0..1) (co-opt orthodox sect)
- `suppression_intensity` (0..1)

Mechanics:
- suppression reduces hostile sect adherence but increases resentment/unrest and smuggling
- co-option increases legitimacy but increases corruption risk (tithes and patronage)

Costs:
- suppression consumes enforcement budget (0273) with reason `PAY_RELIGION_SUPPRESSION`
- co-option consumes patronage budget `PAY_STATE_CHURCH`

---

## 7) Facilities (optional v1)

Add 2 religious facility types (civic category):
- `TEMPLE_L1` (increases clergy_power capacity and ritual_effect_scale locally)
- `SHRINE_L0` (cheap, small cohesion boost)

These can be built by Urban Growth (0282) under civic bias.

If scope tight, skip facilities and keep it purely as policy + state.

---

## 8) Effects wiring into ideology and governance

- Ward religion influences curriculum axes (0285):
  - orthodox church boosts ORTHODOXY,
  - well mystics boost scarcity ethics and anti-corruption,
  - heretic network boosts TECHNICISM (forbidden knowledge) and MERCANTILISM (smuggling)

- Governance (0269/0271):
  - aligned religion increases legitimacy stability
  - suppression increases risk of governance failure incidents (“Religious Riot”, “Schism”)

- Media (0286):
  - sermons and edicts are PROPAGANDA messages with target axes.

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["religion"]["adherence_avg_by_sect"]`
- `metrics["religion"]["suppression_avg"]`
- `metrics["religion"]["rituals_performed"]`
- `metrics["religion"]["tithes_collected"]` (proxy)

TopK:
- wards by heresy adherence
- wards by suppression level
- sects growing fastest

Cockpit:
- ward religion page: adherence shares, clergy_power, suppression, next rituals
- sect overview: global strength and doctrine vector
- “religion vs stability” indicators: suppression vs unrest trend

Events:
- `RITUAL_PERFORMED`
- `SECT_GROWTH_SPIKE`
- `SCHISM_EVENT`
- `RELIGION_SUPPRESSED`
- `STATE_CHURCH_COOPTED`

---

## 10) Tests (must-have)

Create `tests/test_religion_ritual_power_v1.py`.

### T1. Determinism
- same shocks/policies → same adherence and rituals.

### T2. Crisis conversion
- camps/war/outbreak increase conversion rate and sect growth deterministically.

### T3. Suppression tradeoff
- suppression reduces hostile adherence but increases unrest (bounded).

### T4. Ritual effects
- healing rites reduce outbreak intensity (small) deterministically.

### T5. Media integration
- sermons delivered via media channels alter adherence/curriculum axes (smoke test).

### T6. Snapshot roundtrip
- sects and ward religion state persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add religion module + state
- Create `src/dosadi/runtime/religion.py` with ReligionConfig, SectState, WardReligionState
- Add world.sects and world.religion_by_ward to snapshots + seeds

### Task 2 — Implement weekly adherence drift and clergy power
- Compute adherence changes from shocks, ideology, media sermons, and policies
- Update clergy_power and tithes proxy

### Task 3 — Implement ritual calendar and effects
- Schedule/trigger rituals deterministically and apply bounded effects on legitimacy/unrest/health/axes
- Emit events and telemetry

### Task 4 — Add suppression/co-option policy hooks
- Add institution dials and ledger spending for suppression and state church patronage
- Wire suppression to enforcement and governance failure incidents

### Task 5 — Cockpit + tests
- Add religion dashboards (ward + sect views)
- Add `tests/test_religion_ritual_power_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - sect adherence evolves deterministically under crisis and policy,
  - rituals create measurable cohesion/legitimacy/health/security effects,
  - suppression/co-option tradeoffs are real and phase-sensitive,
  - religion feeds into ideology and culture wars,
  - state persists into 200-year seeds,
  - cockpit explains the “spiritual power map” of the empire.

---

## 13) Next slice after this

**Labor Unions & Guild Politics v1** — economic institutions as power centers:
- guild capture of supply chains,
- strikes and slowdowns,
- and negotiated productivity vs autonomy.
