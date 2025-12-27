---
title: Trade_Federations_and_Cartels_v1_Implementation_Checklist
doc_id: D-RUNTIME-0301
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
  - D-RUNTIME-0274   # Diplomacy & Treaties v1
  - D-RUNTIME-0275   # Border Control & Customs v1
  - D-RUNTIME-0276   # Smuggling Networks v1
  - D-RUNTIME-0291   # Wages, Rations & Class Stratification v1
  - D-RUNTIME-0292   # Banking, Debt & Patronage v1
  - D-RUNTIME-0293   # Insurance & Risk Markets v1
  - D-RUNTIME-0295   # Sanctions & Embargo Systems v1
---

# Trade Federations & Cartels v1 — Implementation Checklist

Branch name: `feature/trade-federations-cartels-v1`

Goal: create higher-order economic alliances so that:
- guilds form federations spanning multiple wards/polities,
- cartels can coordinate pricing, restrict supply, and enforce quotas,
- federations become diplomacy actors (treaties, embargoes, mutual aid),
- market signals evolve from “local scarcity” into strategic manipulation,
- long-run seeds diverge into merchant-dominated empires, cartelized oligarchies, or state-broken guilds.

v1 is macro: quotas, coordination, and enforcement — not detailed company balance sheets.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same federation formation and cartel actions.
2. **Bounded.** Limit number of federations and cartel agreements.
3. **Legible.** Explain *who* formed *what* and *why* (scores + reason codes).
4. **Composable.** Integrates with markets, sanctions, finance, and law enforcement.
5. **Phase-aware.** P0 cooperative guilds; P2 cartelization and capture.
6. **Tested.** Formation, quota effects, enforcement, persistence.

---

## 1) Concept model

We model two related constructs:

### 1.1 Trade Federation
A membership alliance of guilds/factions across wards (and possibly polities) that:
- shares logistics capacity / depots,
- coordinates routing and risk coverage,
- negotiates treaties (via diplomacy module) on behalf of members,
- and can impose internal rules.

### 1.2 Cartel Agreement
A constrained agreement focused on specific goods where members:
- set target prices or price floors,
- allocate production quotas,
- restrict supply via hoarding,
- enforce compliance via sanctions, patronage, or coercion.

Federations can host multiple cartel agreements.

---

## 2) Federation and cartel types (v1)

Federation archetypes:
- `MERCHANT_LEAGUE` (logistics + markets)
- `ENGINEERS_CONSORTIUM` (infrastructure and suits)
- `WATER_AUTHORITY` (water rights and ration control)
- `MILITARY_SUPPLY_COMPACT` (war economy supply)
- `SHADOW_EXCHANGE` (smuggling-aligned pseudo federation) (optional v1)

Cartel agreement types:
- `PRICE_FLOOR`
- `QUOTA_ALLOCATION`
- `EXCLUSIVE_CONTRACTS`
- `JOINT_EMBARGO`
- `STOCKPILE_HOARDING`

---

## 3) Data structures

Create `src/dosadi/runtime/trade_federations.py`

### 3.1 Config
- `@dataclass(slots=True) class FederationConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 14`
  - `deterministic_salt: str = "federations-v1"`
  - `max_federations_total: int = 12`
  - `max_cartels_total: int = 24`
  - `max_members_per_fed: int = 10`
  - `formation_rate_base: float = 0.002`
  - `cartelization_rate_p2: float = 0.006`
  - `enforcement_strength: float = 0.55`
  - `defection_rate_base: float = 0.03`

### 3.2 Federation
- `@dataclass(slots=True) class Federation:`
  - `fed_id: str`                    # "fed:merchant:3"
  - `name: str`
  - `archetype: str`
  - `members: list[str]`             # faction_ids
  - `polities: list[str]`            # polity_ids touched
  - `hq_ward_id: str`
  - `influence: float = 0.0`         # 0..1
  - `cohesion: float = 0.5`          # 0..1
  - `treasury: float = 0.0`          # proxy, optional
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Cartel agreement
- `@dataclass(slots=True) class CartelAgreement:`
  - `cartel_id: str`                 # "cartel:water:5"
  - `fed_id: str | None`             # optional host federation
  - `goods: list[str]`               # categories
  - `kind: str`                      # PRICE_FLOOR|QUOTA_ALLOCATION|...
  - `members: list[str]`             # faction_ids
  - `target_price_mult: float = 1.0` # affects market prices (0263)
  - `quota_by_member: dict[str, float] = field(default_factory=dict)`  # shares sum=1
  - `hoard_target_days: int = 0`
  - `enforcement_mode: str = "SOFT"` # SOFT|CUSTOMS|COERCIVE
  - `start_day: int = 0`
  - `end_day: int = 0`
  - `status: str = "ACTIVE"`         # ACTIVE|BROKEN|EXPIRED
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.4 Compliance tracker (bounded)
- `@dataclass(slots=True) class CartelCompliance:`
  - `cartel_id: str`
  - `member_id: str`
  - `cheat_score: float = 0.0`       # 0..1
  - `penalties_applied: int = 0`
  - `last_update_day: int = -1`

World stores:
- `world.fed_cfg`
- `world.federations: dict[str, Federation]`
- `world.cartels: dict[str, CartelAgreement]`
- `world.cartel_compliance: dict[tuple[str,str], CartelCompliance]`
- `world.fed_events: list[dict]` (bounded)

Persist all in snapshots and seeds.

---

## 4) Formation dynamics (biweekly)

Implement:
- `run_federations_update(world, day)`

### 4.1 Candidate detection
For each archetype, score candidates:
- factions with high market share in relevant goods (0263)
- factions controlling depots/corridors (0257/0261)
- factions with high finance capacity (0292)
- polities with low enforcement enabling cartelization (0265/0296)
- phase multiplier (P2 increases cartelization)

### 4.2 Formation trigger
If `pseudo_rand < formation_rate_base * f(score)` and capacity allows:
- create federation
- select members TopK by synergy and proximity (shared corridors)

### 4.3 Cartel creation
If P2 or strong market power:
- create cartel agreement tied to federation or standalone
- choose goods with high scarcity elasticity (water, food, suits, medical)
- set kind:
  - PRICE_FLOOR or QUOTA when members have strong supply
  - JOINT_EMBARGO when targeting rival polities/factions

Bound by max_cartels_total.

---

## 5) Applying cartel effects to markets and logistics

### 5.1 Market price manipulation (0263)
Add a layer in market clearing:
- if cartel active for good category in a region:
  - apply `target_price_mult` to equilibrium price
  - reduce effective supply by quota restriction or hoard
  - increase volatility if enforcement weak (cheating wars)

### 5.2 Quota restriction and hoarding
Represent supply reduction as:
- a bounded “withheld supply fraction” per ward/polity and good.

If hoarding:
- redirect production to stockpiles (0257) for cartel members
- increase scarcity for non-members.

### 5.3 Logistics favoritism
Federations can preferentially route:
- better insurance options (0293)
- lower convoy risk via escorts (0261)
- faster customs processing via influence (0275)

Model as cost multipliers and priority weights.

---

## 6) Enforcement and cheating (cartel stability)

Each update, for each cartel:
- estimate member production/sales vs quota (macro proxies)
- compute cheat_score per member:
  - incentive increases when prices high and cohesion low
  - enforcement decreases cheating (customs audits, coercion)

If cheating high:
- cartel can respond:
  - SOFT: fines/patronage withdrawal (0292)
  - CUSTOMS: coordinate sanctions against cheaters (0295/0275)
  - COERCIVE: harassment/raids (integrate with policing/insurgency hooks, optional v1)

If cohesion collapses:
- status becomes BROKEN, prices revert, and a legitimacy shock can occur.

---

## 7) Diplomacy and sanctions integration

Federations can be treaty actors:
- create “trade compact” treaties (0274) with mutual tariffs and embargo rules (0295)
- run joint embargoes against rival polities

v1: expose a simple hook:
- `federation_as_actor_id` used by diplomacy/sanctions modules.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["feds"]["federations"]`
- `metrics["feds"]["cartels"]`
- `metrics["feds"]["avg_price_mult"]`
- `metrics["feds"]["withheld_supply_proxy"]`
- `metrics["feds"]["cartel_breakups"]`

TopK:
- cartels by price impact
- members by cheat_score
- wards/polities most harmed (scarcity spikes)

Cockpit:
- federation registry: archetype, members, HQ, influence, cohesion
- cartel dashboard: goods, kind, target_price_mult, quotas, enforcement mode
- “who is hoarding” view: withheld supply proxy by good
- timeline: formation → price shift → cheating → enforcement → breakup

Events:
- `FEDERATION_FORMED`
- `FEDERATION_MEMBER_JOINED`
- `CARTEL_CREATED`
- `CARTEL_CHEATING_DETECTED`
- `CARTEL_ENFORCEMENT_ACTION`
- `CARTEL_BROKE`

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/federations.json` with federations, cartels, compliance.

---

## 10) Tests (must-have)

Create `tests/test_trade_federations_cartels_v1.py`.

### T1. Determinism
- same inputs → same formation and cartel outcomes.

### T2. Cartel raises prices
- active PRICE_FLOOR cartel increases market price signals for affected goods.

### T3. Quotas reduce supply and increase scarcity
- quota restriction increases scarcity proxy and hardship in non-member wards.

### T4. Cheating destabilizes cartel
- low cohesion yields higher cheat_score; breakups occur deterministically.

### T5. Enforcement reduces cheating
- stronger enforcement reduces cheat_score and stabilizes cartel.

### T6. Snapshot roundtrip
- federations and cartels persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add trade federations module + state
- Create `src/dosadi/runtime/trade_federations.py` with FederationConfig, Federation, CartelAgreement, CartelCompliance
- Add world.federations, cartels, and compliance to snapshots + seeds

### Task 2 — Implement formation + cartel creation loop
- Biweekly update that forms federations and cartels deterministically under conditions/phase

### Task 3 — Integrate cartel effects into market clearing and logistics
- Apply target_price_mult, quota restrictions, and hoarding proxies to 0263 market signals
- Add federation favoritism cost multipliers into logistics and customs priority

### Task 4 — Implement cheating/enforcement/breakup mechanics
- Compute cheat_score; apply enforcement actions; allow cartels to break under low cohesion

### Task 5 — Cockpit + tests
- Add federation/cartel dashboards and timelines
- Add `tests/test_trade_federations_cartels_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - federations and cartels can form deterministically in response to power and scarcity,
  - cartels can raise prices, withhold supply, and destabilize rivals,
  - cheating and enforcement produce believable cartel lifecycles,
  - diplomacy and sanctions can treat federations as actors,
  - cockpit explains “who is manipulating what market and how.”

---

## 13) Next slice after this

**Shadow State & Deep Corruption v1** — capture without collapse:
- parallel institutions,
- bribery budgets and blackmail leverage,
- and corruption becoming a second governance layer.
