---
title: Labor_Unions_and_Guild_Politics_v1_Implementation_Checklist
doc_id: D-RUNTIME-0289
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
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0284   # Education & Human Capital v1
  - D-RUNTIME-0288   # Religion & Ritual Power v1
---

# Labor Unions & Guild Politics v1 — Implementation Checklist

Branch name: `feature/labor-unions-guild-politics-v1`

Goal: model economic institutions as power centers so that:
- guilds can capture supply chains (recipes, depots, workforce),
- unions can strike/slowdown and bargain for rations, pay, and safety,
- the state can negotiate, suppress, or co-opt,
- productivity becomes political and phase-sensitive (P0 cooperative, P2 coercive/corrupt).

v1 is macro collective bargaining, not per-agent union membership.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same bargaining outcomes and incidents.
2. **Bounded.** Ward-level aggregates; TopK guilds; no micro labor market simulation.
3. **Real tradeoffs.** Concessions improve output; repression risks sabotage/unrest.
4. **Composable.** Impacts production, construction timelines, logistics, and legitimacy.
5. **Phase-aware.** P0 rules-based; P2 patronage, extortion, and mafia guilds.
6. **Tested.** Strike triggers, negotiation, output modifiers, persistence.

---

## 1) Concept model

We model two related structures:

### 1.1 Guilds (industry-side)
- control access to key recipes, tools, and specialist labor pools
- can set “tolls” (price markups, bribes) and enforce standards
- can block or delay projects via withholding labor or materials routing

### 1.2 Unions (labor-side)
- represent workers in a ward or sector
- can strike, slowdown, or “work to rule”
- bargain for rations, pay, safety (suit repairs), and legal protections

Both behave like factions (0266) but specialized:
- membership strength is tied to human capital (0284), culture (0270), and conditions.

---

## 2) Entities & scopes (v1)

Define 6 abstract labor organizations:
- `COURIERS_GUILD`
- `MAINTENANCE_GUILD`
- `REFINERS_GUILD`
- `BUILDERS_GUILD`
- `WATER_ENGINEERS_GUILD`
- `GUARDS_UNION` (security labor)

Each can exist per ward with a strength level.
Optionally allow a “federated” empire-level guild presence later.

---

## 3) Data structures

Create `src/dosadi/runtime/labor.py`

### 3.1 Config
- `@dataclass(slots=True) class LaborConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 7`
  - `max_orgs_per_ward: int = 8`
  - `deterministic_salt: str = "labor-v1"`
  - `base_strike_rate: float = 0.01`
  - `negotiation_step: float = 0.15`
  - `repression_backlash: float = 0.12`
  - `sabotage_rate: float = 0.03`

### 3.2 Org state
- `@dataclass(slots=True) class LaborOrgState:`
  - `org_id: str`                     # e.g., "guild:builders"
  - `org_type: str`                   # "GUILD"|"UNION"
  - `sector: str`                     # "CONSTRUCTION"|"REFINING"|...
  - `ward_id: str`
  - `strength: float = 0.0`           # 0..1
  - `militancy: float = 0.0`          # 0..1
  - `corruption: float = 0.0`         # 0..1 (P2 grows)
  - `contract_state: dict[str, float] = field(default_factory=dict)` # wage/rations/safety dials
  - `status: str = "NORMAL"`          # NORMAL|SLOWDOWN|STRIKE|LOCKOUT
  - `status_until_day: int = -1`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

### 3.3 Bargaining record (bounded)
- `@dataclass(slots=True) class BargainingEvent:`
  - `day: int`
  - `ward_id: str`
  - `org_id: str`
  - `kind: str`                       # DEMAND|OFFER|AGREEMENT|STRIKE|REPRESSION|SABOTAGE
  - `terms: dict[str, float]`
  - `outcome: str`
  - `reason_codes: list[str]`

World stores:
- `world.labor_cfg`
- `world.labor_orgs_by_ward: dict[str, list[LaborOrgState]]`
- `world.labor_events: list[BargainingEvent]` (bounded)

Persist org states and optionally bounded event history.

---

## 4) Inputs: what drives strength and militancy

Per update, compute “grievance” and “power” signals:

Grievance increases with:
- ration shortages / price spikes (0263)
- safety incidents and suit failures (0254)
- epidemic stress (0283)
- crackdown harshness (0277) (especially against workers)
- corruption and unequal distributions (0273 + future class system)

Power increases with:
- human capital (0284): more skilled labor has more leverage
- scarcity of replacement workforce
- control of choke-points: depots, relays, water plants (0257/0286)
- cultural support for collective action (0270)

Militancy increases when grievances high and power high.

---

## 5) Strike/slowdown trigger (weekly)

For each LaborOrgState:
- compute `p_action`:
  - base_strike_rate
  - + grievance term
  - + militancy term
  - - institution responsiveness term (offers, legitimacy)
  - + phase multiplier (P2 higher)
Trigger deterministically:
- `pseudo_rand01(salt|day|org_id) < p_action`

If triggered:
- choose action:
  - SLOWDOWN (most common)
  - STRIKE (when militancy high)
  - LOCKOUT (if state/guild conflict)
Set `status_until_day = day + duration` (e.g., 7–21 days).

---

## 6) Bargaining loop (offer/accept)

Institutions (ward governance) respond using dials (0269):
- `labor_negotiation_bias` (-0.5..+0.5)
- `labor_repression_bias` (-0.5..+0.5)
- `labor_patronage_bias` (-0.5..+0.5)

Bargaining terms (v1):
- `wage` (proxy: budget allocation to workers)
- `rations` (priority access to food/water)
- `safety` (suit repair allocation, maintenance spend)
- `recognition` (legal protection; reduces future militancy slightly)
- `anti_corruption` (for “well mystics” aligned labor)

Resolution rule:
- org demand vector derived from grievances
- institution offer vector derived from budget constraints and ideology
- accept if utility(org, offer) > threshold and utility(state, offer) > threshold
Use deterministic scoring and tie breaks.

If agreement:
- apply contract_state updates for N weeks
- reduce militancy temporarily

If repression chosen:
- reduce org strength short-run
- increase unrest + sabotage risk (repression_backlash)
- possible incident: “Factory Fire,” “Courier Attack,” “Water Plant Damage”

---

## 7) Effects on production and logistics

When org is in SLOWDOWN or STRIKE:
- apply sector-specific output multipliers per ward:
  - Construction throughput reduced
  - Refining throughput reduced
  - Courier capacity reduced
  - Maintenance response slowed (wear increases)
- Also apply “quality drift”:
  - slowdowns increase wear and incident chance (bounded)

Guild capture mechanics (v1):
- guilds can impose “tolls” on sector output:
  - increase effective cost of production (ledger burn)
  - or reduce availability (market signal distortion)

Represent as modifiers applied at module boundaries:
- `world.modifiers["labor"]["construction_mult"][ward_id] = 0.7`, etc.

---

## 8) Corruption and patronage (phase-sensitive)

As phases progress:
- corruption tends to rise in P2 for guild leaders
- patronage deals:
  - state can buy off guild leaders (PAY_PATRONAGE)
  - improves output but increases corruption and inequality

Keep v1 small:
- add a corruption drift per week in P2
- patronage reduces strike probability but increases corruption and culture war intensity.

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["labor"]["orgs_active"]`
- `metrics["labor"]["strikes_active"]`
- `metrics["labor"]["slowdowns_active"]`
- `metrics["labor"]["output_loss_proxy"]`
- `metrics["labor"]["bargains_signed"]`
- `metrics["labor"]["repressions"]`

TopK:
- wards with biggest productivity loss from labor actions
- orgs with highest militancy
- wards where repression caused sabotage incidents

Cockpit:
- ward labor page: org list, strength, militancy, status, contract terms
- bargaining timeline: demands/offers/agreements
- “chokepoint capture” view: which guilds influence which recipes/depots
- sector throughput overlay with labor modifiers

Events:
- `LABOR_ACTION_SLOWDOWN`
- `LABOR_ACTION_STRIKE`
- `BARGAINING_OFFER`
- `BARGAINING_AGREEMENT`
- `LABOR_REPRESSION`
- `LABOR_SABOTAGE`

---

## 10) Persistence / seed vault

Export stable:
- `seeds/<name>/labor.json` with org states per ward.

---

## 11) Tests (must-have)

Create `tests/test_labor_unions_guild_politics_v1.py`.

### T1. Determinism
- same inputs → same actions and bargaining outcomes.

### T2. Shortage increases militancy
- ration shortages raise p_action and strike frequency deterministically.

### T3. Negotiation vs repression tradeoff
- negotiation reduces downtime; repression increases sabotage and unrest.

### T4. Output modifiers apply
- strikes reduce construction throughput and courier capacity.

### T5. Persistence
- org status and contract terms persist across snapshot/load and seeds.

---

## 12) Codex Instructions (verbatim)

### Task 1 — Add labor module + org states
- Create `src/dosadi/runtime/labor.py` with LaborConfig, LaborOrgState, BargainingEvent
- Add world.labor_orgs_by_ward and bounded labor_events to snapshots + seeds

### Task 2 — Implement weekly grievance/power update and action triggers
- Compute grievance from shortages, safety failures, epidemics, raids, crackdowns
- Update strength/militancy and deterministically trigger SLOWDOWN/STRIKE

### Task 3 — Implement bargaining and policy responses
- Add institution dials for negotiation/repression/patronage
- Apply contract terms or repression outcomes and emit incidents when needed

### Task 4 — Wire effects into production/logistics/maintenance
- Apply sector multipliers and cost tolls at module boundaries
- Add telemetry and cockpit views

### Task 5 — Tests
- Add `tests/test_labor_unions_guild_politics_v1.py` (T1–T5)

---

## 13) Definition of Done

- `pytest` passes.
- With enabled=True:
  - labor orgs form and evolve deterministically,
  - strikes/slowdowns occur under stress,
  - institutions negotiate or repress with real tradeoffs,
  - production/logistics/maintenance are materially affected,
  - corruption and patronage begin to appear in P2,
  - cockpit explains “why the empire is slowing down.”

---

## 14) Next slice after this

**Workforce Skill Assignment v2** — staffing becomes competence constrained:
- map human capital domains to facility staffing,
- enforce specialist scarcity,
- and make labor politics operate on “who can actually do the work.”
