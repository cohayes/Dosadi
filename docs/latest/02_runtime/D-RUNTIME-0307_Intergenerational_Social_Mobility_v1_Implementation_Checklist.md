---
title: Intergenerational_Social_Mobility_v1_Implementation_Checklist
doc_id: D-RUNTIME-0307
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
  - D-RUNTIME-0289   # Labor Unions & Guild Politics v1
  - D-RUNTIME-0290   # Workforce Skill Assignment v2
  - D-RUNTIME-0291   # Wages, Rations & Class Stratification v1
  - D-RUNTIME-0292   # Banking, Debt & Patronage v1
  - D-RUNTIME-0303   # Reform & Anti-Corruption Drives v1
---

# Inter-Generational Social Mobility v1 — Implementation Checklist

Branch name: `feature/intergenerational-mobility-v1`

Goal: make class dynamics evolve over centuries so that:
- education, patronage, debt, unions, and health shape mobility,
- elites reproduce power through inheritance and credential control,
- reforms can expand mobility (or entrench it via “merit theater”),
- migration and war create upward/downward shocks,
- long-run seeds diverge into fluid meritocracies, rigid castes, or churny warlord ladders.

v1 is macro: cohort mobility indices and bounded transitions, not full family trees.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same mobility outcomes and distributions.
2. **Bounded.** Use cohort distributions; no per-family genealogies in v1.
3. **Composable.** Integrates with education, labor markets, debt, health, and reforms.
4. **Legible.** Expose mobility matrices and why they change.
5. **Phase-aware.** P0 higher mobility; P2 traps and patronage.
6. **Tested.** Mobility updates and persistence.

---

## 1) Concept model

We model society as a distribution over “class tiers” per polity:
- `UNDERCLASS` (unhoused/refugees/penal labor)
- `WORKING` (laborers, service)
- `SKILLED` (artisans, technicians)
- `CLERK` (administration)
- `GUILD` (licensed/union protected)
- `ELITE` (nobility, high clergy, cartel leaders)

Each “generation” (e.g., 20 years) we compute:
- transition probabilities between tiers (mobility matrix),
- resulting tier distribution,
- and a mobility index (e.g., upward probability from bottom two tiers).

The matrix is influenced by:
- education throughput and credential barriers,
- debt and patronage,
- health shocks and survival,
- labor bargaining institutions,
- zoning/segregation,
- and corruption/capture.

---

## 2) Cadence

- Update monthly/quarterly for “drift” signals.
- Apply mobility transitions on a longer cadence:
  - `generation_years = 20` (configurable)
  - apply as a macro-step per polity when day crosses the boundary.

This keeps performance tight.

---

## 3) Data structures

Create `src/dosadi/runtime/mobility.py`

### 3.1 Config
- `@dataclass(slots=True) class MobilityConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 90`          # quarterly drift update
  - `generation_years: int = 20`
  - `deterministic_salt: str = "mobility-v1"`
  - `tiers: tuple[str, ...] = ("UNDERCLASS","WORKING","SKILLED","CLERK","GUILD","ELITE")`
  - `max_events_per_update: int = 12`
  - `mobility_effect_scale: float = 0.25`

### 3.2 Polity mobility state
- `@dataclass(slots=True) class PolityMobilityState:`
  - `polity_id: str`
  - `tier_share: dict[str, float] = field(default_factory=dict)   # sum=1
  - `mobility_matrix: dict[str, dict[str, float]] = field(default_factory=dict)  # from->to probs
  - `upward_index: float = 0.0`          # proxy 0..1
  - `downward_index: float = 0.0`
  - `trap_index: float = 0.0`            # persistence bottom tiers
  - `generation_last_applied_year: int = 0`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Mobility event (bounded)
- `@dataclass(slots=True) class MobilityEvent:`
  - `day: int`
  - `polity_id: str`
  - `kind: str`                          # CREDENTIAL_TIGHTENED|DEBT_CRISIS|UNION_WIN|SCHOOL_EXPANSION|WAR_SHOCK|EPIDEMIC_SHOCK
  - `magnitude: float`
  - `effects: dict[str, object] = field(default_factory=dict)

World stores:
- `world.mobility_cfg`
- `world.mobility_by_polity: dict[str, PolityMobilityState]`
- `world.mobility_events: list[MobilityEvent]` (bounded)

Persist in snapshots and seeds.

---

## 4) Initialization

If absent:
- initialize tier_share using:
  - current wage/ration class stratification (0291) mapped into tiers
  - union/guild strength (0289) for GUILD share
  - admin size (0290/0284) for CLERK share
If no data, use a stable default distribution (documented).

Initialize a baseline mobility matrix:
- diagonal heavy (persistence),
- small adjacent moves up/down,
- tiny leaps.

---

## 5) Building the mobility matrix from signals (quarterly)

Compute signals per polity:
- `education_access` and `education_quality` (0284)
- `credential_barrier` (ideology/curriculum control 0285 + guild gatekeeping 0289)
- `debt_pressure` (0292)
- `patronage_intensity` (0292 + corruption capture 0302)
- `health_burden` (0283)
- `zoning_segregation` (0282)
- `union_strength` (0289)
- `reform_strength` (0303)
- `war_pressure` (0278/0298)
- `migration_shock` (0281)

Map to transition modifiers:
- education increases WORKING→SKILLED, SKILLED→CLERK, CLERK→GUILD
- credential barriers reduce upward transitions and increase persistence
- debt increases downward moves and traps
- patronage increases jumps for connected groups but reduces overall fairness (increase inequality)
- union strength increases WORKING→GUILD and reduces downward moves
- health and war increase downward and underclass share
- zoning reduces upward moves from UNDERCLASS/WORKING

Normalize each row to sum to 1, enforce adjacency constraints (v1: only move up/down at most 2 tiers per generation).

Compute indices:
- upward_index = sum(prob bottom2 move up)
- trap_index = prob UNDERCLASS stays UNDERCLASS + WORKING stays WORKING
- downward_index = sum(prob top tiers move down)

---

## 6) Applying generation transition (every generation_years)

When world time crosses generation boundary:
- apply matrix to tier_share:
  - new_share[to] = Σ from share[from] * P(from→to)
- renormalize and clamp.

Emit summary events:
- `MOBILITY_GENERATION_APPLIED` with before/after indices.

---

## 7) Shocks and special events (bounded)

When big macro events occur:
- epidemic, war/civil war, famine, debt crisis, major reform, school expansion,
create MobilityEvent and adjust matrix temporarily for a few quarters.

Tie into:
- Public health (0283): epidemic shock increases downward and underclass
- War/civil war (0278/0298): displacement increases underclass and volatility
- Reform (0303): procedural reform increases education and reduces credential barriers
- Ideology control (0285): curriculum capture increases barriers

---

## 8) Integration hooks (v1)

Expose outputs to:
- workforce assignment (0290): tier shares influence staffing pools
- wages/rations (0291): tier shares influence distribution politics
- leadership legitimacy (0299): low mobility reduces legitimacy
- insurgency recruitment (0297): high trap_index increases recruitment
- education system: demand pressure and school building priorities

Keep it scalar and bounded.

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["mobility"]["upward_index"]`
- `metrics["mobility"]["trap_index"]`
- `metrics["mobility"]["tier_share"]` (per tier)
- `metrics["mobility"]["generation_applied"]`

Cockpit:
- polity mobility dashboard:
  - tier distribution
  - mobility matrix heatmap (text table ok)
  - indices over time
  - major mobility events timeline

---

## 10) Persistence / seed vault

Export:
- `seeds/<name>/mobility.json` with tier shares, matrix, and generation counters.

---

## 11) Tests (must-have)

Create `tests/test_intergenerational_mobility_v1.py`.

### T1. Determinism
- same signals → same matrix and tier outcomes.

### T2. Education increases upward mobility
- higher education_access increases upward_index and WORKING→SKILLED transitions.

### T3. Debt increases trap and downward moves
- higher debt_pressure increases trap_index and downward_index.

### T4. Union strength reduces downward mobility
- higher union_strength reduces SKILLED/WORKING downward transitions.

### T5. Generation step applies correctly
- matrix application yields valid distribution sum=1.

### T6. Snapshot roundtrip
- mobility state persists across snapshot/load and seeds.

---

## 12) Codex Instructions (verbatim)

### Task 1 — Add mobility module + state
- Create `src/dosadi/runtime/mobility.py` with MobilityConfig, PolityMobilityState, MobilityEvent
- Add world.mobility_by_polity and mobility_events to snapshots + seeds

### Task 2 — Implement quarterly matrix build from signals
- Read inputs from education, debt, unions, health, zoning, reform, war, migration
- Build normalized mobility matrix with bounded moves

### Task 3 — Implement generation transition macro-step
- Apply matrix every generation_years; update tier shares; emit summary event

### Task 4 — Wire outputs into legitimacy and recruitment proxies
- Low mobility reduces legitimacy and increases insurgency recruitment; tie into workforce pools

### Task 5 — Cockpit + tests
- Add mobility dashboard and matrix view
- Add `tests/test_intergenerational_mobility_v1.py` (T1–T6)

---

## 13) Definition of Done

- `pytest` passes.
- With enabled=True:
  - polities have tier distributions and mobility matrices that evolve with signals,
  - generation steps reshape society without per-agent genealogy cost,
  - traps and ladders influence legitimacy, insurgency, and workforce capacity,
  - seeds produce distinct long-run class structures,
  - cockpit explains “how hard it is to climb.”

---

## 14) Next slice after this

**Inheritance, Lineages & Nepotism v1** — moving closer to micro:
- family wealth buckets, nepotism edges,
- and how elites reproduce power beyond pure mobility matrices.
