---
title: Wages_Rations_and_Class_Stratification_v1_Implementation_Checklist
doc_id: D-RUNTIME-0291
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0281   # Migration & Refugees v1
  - D-RUNTIME-0283   # Public Health & Epidemics v1
  - D-RUNTIME-0284   # Education & Human Capital v1
  - D-RUNTIME-0289   # Labor Unions & Guild Politics v1
  - D-RUNTIME-0290   # Workforce Skill Assignment v2
---

# Wages, Rations & Class Stratification v1 — Implementation Checklist

Branch name: `feature/wages-rations-class-v1`

Goal: create a macro “who gets what” ladder so that:
- ration differentials and pay tiers become explicit policy levers,
- inequality produces predictable pressure (unrest, labor militancy, migration),
- institutions can buy loyalty or enforce austerity,
- class dynamics shape culture wars and faction recruitment across centuries.

v1 is **macro household tiers**, not per-agent income tracking.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same tier distributions and outcomes.
2. **Bounded.** Ward-level tier shares; no per-household simulation.
3. **Policy-driven.** Institutions set rationing and pay posture by phase.
4. **Market-aware.** Shortages raise effective hardship at lower tiers.
5. **Composable.** Feeds labor politics, ideology, migration, health, and legitimacy.
6. **Tested.** Tier evolution, hardship signals, policy effects, persistence.

---

## 1) Concept model

Each ward has:
- a distribution over **class tiers** (shares of population),
- tier-specific access to:
  - wages (money proxy),
  - rations (food/water priority),
  - housing quality and suit maintenance,
- a resulting **hardship index** and **inequality index**.

These indices feed into:
- labor grievances (0289),
- ideology and curriculum control (0285),
- migration pressure (0281),
- health risks (0283),
- governance failure probability (0271).

---

## 2) Tier model (v1)

Define 5 tiers, each 0..1 share (sum=1):
- `T0_ELITE` (council, clergy heads, guild masters)
- `T1_OFFICERS` (admins, engineers, skilled supervisors)
- `T2_SKILLED` (trained workers, technicians)
- `T3_UNSKILLED` (basic labor)
- `T4_DISPLACED` (camped/refugees, marginal)

Each tier has:
- wage index (money)
- ration priority (food/water)
- housing quality index
- suit maintenance priority

Tier membership shares are influenced by:
- education/human capital levels (0284),
- workforce composition (0290),
- migration camps (0281) (increases T4),
- corruption and patronage (0273/0269),
- war and raids (0278) (pushes down tiers via destruction/displacement).

---

## 3) Data structures

Create `src/dosadi/runtime/class_system.py`

### 3.1 Config
- `@dataclass(slots=True) class ClassConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 14`
  - `deterministic_salt: str = "class-v1"`
  - `mobility_rate: float = 0.03`              # tier share drift per update
  - `camp_assimilation_rate: float = 0.05`     # T4→T3/T2 when housing/jobs exist
  - `inequality_sensitivity: float = 0.7`
  - `hardship_sensitivity: float = 0.9`

### 3.2 Ward class state
- `@dataclass(slots=True) class WardClassState:`
  - `ward_id: str`
  - `tier_share: dict[str, float] = field(default_factory=dict)`   # T0..T4 sums to 1
  - `wage_index: dict[str, float] = field(default_factory=dict)`   # per tier
  - `ration_priority: dict[str, float] = field(default_factory=dict)`
  - `housing_quality: dict[str, float] = field(default_factory=dict)`
  - `suit_priority: dict[str, float] = field(default_factory=dict)`
  - `hardship_index: float = 0.0`      # 0..1
  - `inequality_index: float = 0.0`    # 0..1 (e.g., Gini-like proxy)
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.class_cfg`
- `world.class_by_ward: dict[str, WardClassState]`

Persist in snapshots and seeds.

---

## 4) Policy dials (institutions)

Extend WardInstitutionPolicy (0269) with:
- `rationing_regime` enum:
  - `EQUAL`, `MERIT`, `OFFICER_FIRST`, `SECURITY_FIRST`, `ELITE_FIRST`, `AUSTERITY`
- `wage_regime` enum:
  - `FLAT`, `SKILL_BONUS`, `GUILD_CAPTURE`, `PATRONAGE`, `WAR_ECONOMY`
- `housing_allocation_bias` (0..1) favor integration vs segregation
- `camp_integration_bias` (0..1) how aggressively to absorb T4 into housing/jobs
- `suit_maintenance_bias` (0..1) prioritize workforce tiers vs equal access

These determine tier-specific indices.

---

## 5) Computing tier indices

At each update (biweekly):
1) Determine **ration priorities** by regime:
- EQUAL: small differences
- OFFICER_FIRST / ELITE_FIRST: large gaps
- SECURITY_FIRST: guards/officers favored
- MERIT: skilled favored

2) Determine **wage indices** by regime:
- FLAT: small gaps
- SKILL_BONUS: linked to education/workforce scarcity
- GUILD_CAPTURE: skilled wages rise but corruption increases
- PATRONAGE: T0/T1 wages rise; inequality high
- WAR_ECONOMY: guards/officers up; others down

3) Determine **housing quality**:
- derived from housing capacity (0282) vs population + camps (0281)
- segregation bias pushes lower tiers to worse housing

4) Determine **suit maintenance priority**:
- linked to suit repair capacity (0254) and policy bias.

All indices are bounded 0..1 and deterministic.

---

## 6) Evolving tier shares (mobility + camps)

Update tier_share with bounded drift:
- Education/human capital moves some share from T3→T2 and T2→T1 (slowly)
- War/raids and epidemics push down (T2→T3, T3→T4)
- Housing/jobs availability pulls T4 upward (assimilation):
  - if housing pressure low and workforce demand high, move T4→T3 (and some to T2)

Use mobility_rate and camp_assimilation_rate with deterministic ordering.

---

## 7) Hardship and inequality indices

### 7.1 Hardship
Compute a hardship proxy:
- shortages (0263) weighted heavily for lower tiers
- camp share (T4) increases hardship strongly
- health outbreaks (0283) increase hardship and lower tier survival
- suit maintenance deficits add hardship

### 7.2 Inequality
Compute a simple inequality proxy:
- function of wage_index and ration_priority spread across tiers
- plus housing segregation
Bounded 0..1.

Expose both indices for other modules.

---

## 8) Effects wiring

- Labor (0289): grievances += hardship + inequality
- Ideology (0285): inequality increases polarization, boosts orthodoxy or heresy depending on culture
- Migration (0281): high hardship pushes out-migration / internal displacement
- Health (0283): hardship increases outbreak triggers and chronic burden
- Governance failures (0271): high hardship + inequality raises incident probabilities
- Law enforcement (0265/0277): repression on high inequality worsens backlash

Keep v1 minimal: just produce indices and feed into a few input terms.

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["class"]["avg_hardship"]`
- `metrics["class"]["avg_inequality"]`
- `metrics["class"]["camp_share_total"]` (T4 weighted)
- `metrics["class"]["tier_share_avg"]`

TopK:
- wards by hardship
- wards by inequality
- wards with high T4 and low housing

Cockpit:
- ward class page: tier shares, indices, policy regimes
- “ration ladder” view: tier priorities vs shortages
- “mobility” view: recent share drift

Events:
- `RATION_REGIME_CHANGED`
- `HARDSHIP_SPIKE`
- `INEQUALITY_SPIKE`
- `CAMP_INTEGRATION_PUSH`

---

## 10) Persistence / seed vault

Export stable:
- `seeds/<name>/class.json` sorted by ward_id.

---

## 11) Tests (must-have)

Create `tests/test_wages_rations_class_v1.py`.

### T1. Determinism
- same policies/shortages → same indices and tier shares.

### T2. Shortage amplifies hardship for lower tiers
- under shortages, hardship increases more when T4/T3 are large.

### T3. Regime impacts inequality
- ELITE_FIRST and PATRONAGE yield higher inequality than EQUAL.

### T4. Camp integration reduces T4 under capacity
- with housing + jobs, T4 share declines deterministically.

### T5. Wiring to labor
- hardship increases labor action probability input (smoke test).

### T6. Snapshot roundtrip
- class states persist across snapshot/load and seeds.

---

## 12) Codex Instructions (verbatim)

### Task 1 — Add class system module + ward class state
- Create `src/dosadi/runtime/class_system.py` with ClassConfig and WardClassState
- Add world.class_by_ward to snapshots + seeds

### Task 2 — Add institution policy regimes
- Add rationing_regime and wage_regime enums and allocation biases to WardInstitutionPolicy

### Task 3 — Implement biweekly updates
- Compute tier indices and evolve tier shares via mobility + camp assimilation
- Compute hardship and inequality indices and expose helpers

### Task 4 — Wire indices into other modules
- Add hardship/inequality inputs to labor grievances, ideology polarization, migration pressure, health risk, and governance failures

### Task 5 — Cockpit + tests
- Add class dashboards and ladder views
- Add `tests/test_wages_rations_class_v1.py` (T1–T6)

---

## 13) Definition of Done

- `pytest` passes.
- With enabled=True:
  - rationing and wage regimes create distinct tier outcomes,
  - camps and shortages generate hardship pressure,
  - inequality shapes labor/ideology/migration/health dynamics,
  - class state persists into long-run 200-year seeds,
  - cockpit explains “who is suffering and why.”

---

## 14) Next slice after this

**Banking, Debt & Patronage v1** — financial chains of obligation:
- credit issuance by guilds/state,
- debt peonage and patronage networks,
- and corruption becoming balance-sheet-visible.
