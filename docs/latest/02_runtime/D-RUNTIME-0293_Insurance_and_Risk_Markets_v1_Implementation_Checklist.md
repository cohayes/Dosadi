---
title: Insurance_and_Risk_Markets_v1_Implementation_Checklist
doc_id: D-RUNTIME-0293
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0276   # Smuggling Networks v1
  - D-RUNTIME-0277   # Crackdown Strategy v1
  - D-RUNTIME-0278   # War & Raids v1
  - D-RUNTIME-0289   # Labor Unions & Guild Politics v1
  - D-RUNTIME-0292   # Banking, Debt & Patronage v1
---

# Insurance & Risk Markets v1 — Implementation Checklist

Branch name: `feature/insurance-risk-markets-v1`

Goal: turn corridor danger into priced signals so that:
- shipping premiums reflect raid/interference risk,
- convoy/escort policy responds to market prices (not just rules),
- “shadow insurance” (protection rackets) emerges from smuggling networks,
- and investment/expansion decisions internalize risk over long horizons.

v1 is macro premiums and claims, not per-shipment contract law.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same premiums and payouts.
2. **Bounded.** Corridor-level premiums; TopK insured routes; no micro policy explosion.
3. **Signal integrity.** Premiums must correlate with realized incidents.
4. **Two markets.** Legit insurance and shadow protection can compete.
5. **Composable.** Feeds logistics costs, depot policy, and expansion planning.
6. **Tested.** Pricing updates, payouts, and interactions with risk.

---

## 1) Concept model

We define insurance products for:
- corridor shipments (logistics traffic),
- facility operations (optional later),
- and human risk (optional later).

For v1, focus on corridor shipping insurance:
- Each corridor has a **premium rate** (per unit value shipped),
- Insurers hold reserves and pay claims when losses occur (incidents).

Two insurer types:
- `STATE_MUTUAL` (legit; slower, regulated)
- `GUILD_UNDERWRITER` (merchant guild; profit-driven)
- `SHADOW_PROTECTION` (smuggling network; “pay or get hit” rackets)

Premiums respond to:
- corridor risk model (0261),
- observed losses (war/raids/interference),
- enforcement intensity (crackdowns),
- insurer solvency.

---

## 2) Data structures

Create `src/dosadi/runtime/insurance.py`

### 2.1 Config
- `@dataclass(slots=True) class InsuranceConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 7`
  - `deterministic_salt: str = "insurance-v1"`
  - `max_policies_active: int = 2000`      # macro “flows”, not per shipment
  - `premium_smoothing: float = 0.25`      # EMA step toward new rate
  - `loss_lookback_weeks: int = 8`
  - `min_premium: float = 0.001`
  - `max_premium: float = 0.20`
  - `shadow_markup: float = 0.25`          # rackets priced above legit
  - `insurer_reserve_floor: float = 0.15`  # if below, premiums jump

### 2.2 Insurer model
- `@dataclass(slots=True) class Insurer:`
  - `insurer_id: str`             # "insurer:state" | "insurer:guild:merchant" | "insurer:shadow:<id>"
  - `kind: str`                   # STATE_MUTUAL|GUILD_UNDERWRITER|SHADOW_PROTECTION
  - `reserve: float = 0.0`
  - `payout_ratio: float = 0.8`   # fraction of losses covered
  - `admin_cost: float = 0.05`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

### 2.3 Corridor pricing state
- `@dataclass(slots=True) class CorridorPremium:`
  - `corridor_id: str`
  - `insurer_id: str`
  - `premium_rate: float`            # 0..1 per unit value
  - `loss_rate_est: float`           # estimated loss rate from lookback
  - `claims_paid_lookback: float`
  - `premiums_collected_lookback: float`
  - `last_update_day: int = -1`

### 2.4 Macro flow policy (bounded)
Instead of per-shipment insurance, represent “flows”:
- `@dataclass(slots=True) class InsuredFlow:`
  - `flow_id: str`
  - `route_key: str`                # e.g., "wardA->wardB:resource:water"
  - `corridors: list[str]`
  - `insurer_id: str`
  - `weekly_value: float`
  - `status: str = "ACTIVE"`
  - `last_update_day: int = -1`

World stores:
- `world.insurance_cfg`
- `world.insurers: dict[str, Insurer]`
- `world.premiums_by_corridor: dict[tuple[str,str], CorridorPremium]`  # (corridor_id, insurer_id)
- `world.insured_flows: dict[str, InsuredFlow]`
- `world.insurance_events: list[dict]` (bounded)

Persist insurers, premiums, flows (bounded) in snapshots and seeds.

---

## 3) Premium pricing (weekly)

Implement:
- `run_insurance_week(world, day)`

For each corridor and insurer:
1) Compute base risk signal:
- from corridor risk model (0261): `risk_score` 0..1
2) Compute observed loss rate estimate:
- from war/raid incidents and interference logs over lookback
3) Set target premium:
- target = clamp(min_premium + a*risk_score + b*loss_rate_est, min, max)
- if insurer reserve < floor: multiply target by (1 + stress_factor)
- if kind==SHADOW: target *= (1 + shadow_markup)

4) Apply smoothing:
- premium_rate = (1 - premium_smoothing)*old + premium_smoothing*target

Update CorridorPremium record.

Deterministic.

---

## 4) Premium collection and claims

### 4.1 Collection
For each insured flow each week:
- premium = weekly_value * sum(premium_rate over corridors)
- transfer from shipper (ward/guild logistics budget) to insurer reserve:
  - ledger reason `PAY_INSURANCE_PREMIUM`
- record premiums_collected_lookback.

### 4.2 Claims
When incidents cause “shipment loss” on a corridor:
- compute loss_value proxy from affected flows that include corridor
- insurer pays payout_ratio * loss_value from reserve:
  - transfer to shipper relief pool (or directly to ward/guild account)
  - ledger reason `INSURANCE_CLAIM_PAYOUT`
- if reserve insufficient: partial payout + insurer stress next pricing update

Note: v1 can approximate loss_value by correlating to corridor traffic volume and value.

---

## 5) Choosing insurance (demand side)

Logistics planner (0238/0257/0261) can choose:
- buy legit insurance (cheaper, less reliable if insolvent),
- pay shadow protection (more expensive, reduces sabotage risk),
- or go uninsured (accept losses).

Decision rule (macro):
- compare expected loss vs premium and policy preference
- if corridor is dominated by a smuggling network, shadow protection may reduce realized risk (interference harshness D3).

Implement a bounded chooser:
- for TopK high-value flows only.

---

## 6) Shadow protection dynamics (smuggling integration)

Shadow insurer is tied to smuggling networks (0276):
- if you do not pay, your risk increases (targeted predation).
- if you pay, risk decreases (escort and protection), but corruption increases.
- crackdowns can disrupt shadow insurers and increase violent retaliation.

Implement as modifiers into corridor risk (0261):
- if insured by shadow, reduce interference risk component.
- if uninsured in shadow-controlled corridor, increase interference risk component.

---

## 7) Effects wiring

- Logistics costs: premiums become explicit cost in delivery planning.
- Expansion planner (0259): uses premiums as cost-of-distance/risk.
- War/raids and interference: payouts provide resilience but can bankrupt insurers.
- Finance (0292): insolvent insurers may borrow, creating debt crises.
- Labor (0289): high risk premiums reduce available budgets; can trigger slowdowns.

Keep v1 minimal: logistics/expansion hooks + a finance insolvency hook.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["insurance"]["premium_avg"]`
- `metrics["insurance"]["claims_paid"]`
- `metrics["insurance"]["insurer_reserve_total"]`
- `metrics["insurance"]["flows_insured"]`
- `metrics["insurance"]["shadow_share"]`

TopK:
- corridors with highest premiums
- insurers near insolvency
- flows with highest premium burden

Cockpit:
- corridor premium table (by insurer)
- insurer balance sheet: reserves, premiums, claims, solvency
- flow inspector: route, weekly_value, insurer, premium burden
- “shadow protection map”: where rackets dominate

Events:
- `PREMIUM_UPDATED`
- `FLOW_INSURED`
- `CLAIM_PAID`
- `INSURER_INSOLVENT`
- `SHADOW_RACKET_EXPANDS`

---

## 9) Persistence / seed vault

Export stable:
- `seeds/<name>/insurance.json` with insurers, premiums, flows.

---

## 10) Tests (must-have)

Create `tests/test_insurance_risk_markets_v1.py`.

### T1. Determinism
- same corridor risk and incidents → same premium rates.

### T2. Premium correlates with risk
- higher corridor risk yields higher premium (monotonic).

### T3. Claims reduce reserves and raise premiums
- after loss payouts, premium rises next updates.

### T4. Shadow protection effect
- paying shadow reduces realized interference risk; not paying increases it.

### T5. Bounds
- premium rates clamped to min/max; reserves never negative.

### T6. Snapshot roundtrip
- insurer reserves and premiums persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add insurance module + state
- Create `src/dosadi/runtime/insurance.py` with InsuranceConfig, Insurer, CorridorPremium, InsuredFlow
- Add world.insurers, premiums, and insured_flows to snapshots + seeds

### Task 2 — Implement weekly premium pricing
- Compute target premiums from corridor risk and observed losses with smoothing and solvency stress

### Task 3 — Implement premium collection and claim payouts
- Collect premiums from insured flows; pay claims on corridor loss incidents with bounded payout

### Task 4 — Integrate with logistics/expansion and smuggling rackets
- Add insurance choice for TopK flows; feed premiums into route costs and expansion decisions
- Implement shadow protection risk modifiers

### Task 5 — Cockpit + tests
- Add insurer/corridor/flow dashboards
- Add `tests/test_insurance_risk_markets_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - corridor premiums update deterministically and track risk,
  - claims pay out and can stress insolvency,
  - logistics and expansion planners respond to priced risk,
  - shadow protection competes with legit insurance and changes realized risk,
  - cockpit explains “why this route is expensive and dangerous.”

---

## 13) Next slice after this

**Communications Failure & Jamming v1** — break the information net under stress:
- relay outages, jamming, blackout incidents,
- and strategy shifting when the empire is blind.
