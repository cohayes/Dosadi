---
title: Shadow_State_and_Deep_Corruption_v1_Implementation_Checklist
doc_id: D-RUNTIME-0302
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
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0276   # Smuggling Networks v1
  - D-RUNTIME-0277   # Crackdown Strategy v1
  - D-RUNTIME-0286   # Media & Information Channels v1
  - D-RUNTIME-0287   # Counterintelligence & Espionage v1
  - D-RUNTIME-0292   # Banking, Debt & Patronage v1
  - D-RUNTIME-0296   # Policing Doctrine v2
  - D-RUNTIME-0301   # Trade Federations & Cartels v1
---

# Shadow State & Deep Corruption v1 — Implementation Checklist

Branch name: `feature/shadow-state-deep-corruption-v1`

Goal: model “governance by capture” so that:
- corruption becomes an explicit parallel decision layer (not just a scalar),
- bribes, blackmail, and patronage route outcomes around formal institutions,
- shadow budgets fund smuggling, coercion, and influence ops,
- corruption can stabilize elites short-run but hollow the state and trigger collapse long-run.

v1 is macro: networks and budgets, not individual bribe events.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same capture dynamics.
2. **Bounded.** TopK corruption ties per ward/polity; bounded shadow budgets.
3. **Legible.** Explain why “the law didn’t apply” (capture path).
4. **Composable.** Integrates with policing, sanctions, finance, cartels, and espionage.
5. **Phase-aware.** P2 drives deep capture; P0 mostly petty corruption.
6. **Tested.** Capture effects, exposure, and persistence.

---

## 1) Concept model

We represent corruption as:
- **influence edges**: who can sway whom (faction → institution/office),
- **shadow budgets**: off-ledger funds used to bribe, intimidate, and launder,
- **capture level** per institution area (customs, policing, courts, depots),
- and **exposure risk**: scandals that trigger reforms or purges.

Shadow state operates by:
- redirecting enforcement away from allies,
- granting contracts and permits to patrons,
- permitting smuggling leakage,
- and sabotaging reforms.

---

## 2) Corruption layers (v1)

Model 3 layers:
1) `PETTY` — local bribes; small leak in enforcement
2) `CAPTURE` — key offices controlled; systematic bias
3) `SHADOW_STATE` — parallel governance; formal policy is theater

Represent these as continuous indices (0..1) plus TopK edges.

---

## 3) Data structures

Create `src/dosadi/runtime/shadow_state.py`

### 3.1 Config
- `@dataclass(slots=True) class ShadowStateConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 14`
  - `deterministic_salt: str = "shadowstate-v1"`
  - `max_edges_per_ward: int = 12`
  - `max_shadow_accounts: int = 64`
  - `capture_growth_p2: float = 0.03`
  - `reform_pressure_scale: float = 0.25`
  - `exposure_rate_base: float = 0.002`
  - `laundering_efficiency: float = 0.6`

### 3.2 Influence edge
- `@dataclass(slots=True) class InfluenceEdge:`
  - `ward_id: str`
  - `from_faction: str`
  - `to_domain: str`                 # CUSTOMS|POLICING|COURTS|DEPOTS|MARKETS|MEDIA|COUNCIL
  - `strength: float`                # 0..1
  - `mode: str`                      # BRIBE|BLACKMAIL|PATRONAGE|THREAT
  - `exposure: float = 0.0`          # 0..1 (how risky/visible)
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Shadow account
- `@dataclass(slots=True) class ShadowAccount:`
  - `account_id: str`                # "shadow:<faction_id>:<ward_id>"
  - `faction_id: str`
  - `ward_id: str`
  - `balance: float = 0.0`
  - `sources: dict[str, float] = field(default_factory=dict)`   # SMUGGLING, CARTEL, SKIM_TAX, EXTORTION
  - `uses: dict[str, float] = field(default_factory=dict)`      # BRIBES, THREATS, MEDIA, MILITIA
  - `last_update_day: int = -1`

### 3.4 Corruption indices
- `@dataclass(slots=True) class CorruptionIndex:`
  - `ward_id: str`
  - `petty: float = 0.0`
  - `capture: float = 0.0`
  - `shadow_state: float = 0.0`
  - `exposure_risk: float = 0.0`
  - `last_update_day: int = -1`

World stores:
- `world.shadow_cfg`
- `world.influence_edges_by_ward: dict[str, list[InfluenceEdge]]`
- `world.shadow_accounts: dict[str, ShadowAccount]`
- `world.corruption_by_ward: dict[str, CorruptionIndex]`
- `world.shadow_events: list[dict]` (bounded)

Persist in snapshots and seeds.

---

## 4) Shadow budget inflows/outflows (biweekly)

Inflows:
- smuggling leakage share (0276/0295): `SMUGGLING_TITHE`
- cartel profits (0301): `CARTEL_RENTS`
- tax skimming (0273) (optional proxy): `SKIM_TAX`
- extortion/protection (0293 shadow protection): `EXTORTION`

Outflows:
- bribes to customs/policing/courts
- blackmail and threats
- media capture spend (0286)
- militia funding (0279) (optional proxy)

Implement:
- `run_shadow_state_update(world, day)`

Transfer flows:
- can be off-ledger (shadow) but must be deterministic and bounded.
Optionally mirror as “unexplained variance” vs official ledger for audit.

---

## 5) Influence edge evolution

For each ward:
- choose TopK edges based on:
  - faction power locally (0266)
  - available shadow funds
  - target domain value (customs in high trade wards, depots in logistics hubs)
- strength increases with spend and low oversight (procedural policing low)
- exposure increases with spend, scandals, and counterintel pressure (0287)

Edges decay if:
- reforms and prosecutions succeed,
- sponsor loses power,
- or exposure triggers purge.

---

## 6) Applying capture effects (where it matters)

Provide a helper:
- `apply_capture_modifier(world, ward_id, domain, base_value, actor_faction_id=None) -> (value, audit_flags)`

Domains affected:
- CUSTOMS: reduces enforcement vs allies, increases leakage vs rivals
- POLICING: reduces arrest of allies; increases terror selectively
- COURTS: changes conviction rate, property seizures, and contract enforcement
- DEPOTS: skims stockpiles; re-routes deliveries; “missing barrels”
- MARKETS: preferential access; price manipulation
- MEDIA: propaganda amplification, scandal suppression
- COUNCIL: policy outcomes skew toward sponsors

v1 can route through a few key integrations:
- sanctions enforcement leakage (0295)
- policing corruption and enforcement (0296)
- cartel stability and cheating enforcement (0301)
- finance default resolution (0292) (friends get restructured, enemies seized)

---

## 7) Exposure, scandals, reforms, and purges

Exposure risk rises when:
- capture and shadow_state indices high,
- media not fully captured,
- counterintel strong,
- or leadership seeks legitimacy reforms (0299)

If random trigger:
- generate scandal incident:
  - `BRIBERY_SCANDAL`, `MISSING_STOCKPILE`, `JUDGE_BOUGHT`, `CUSTOMS_RING_EXPOSED`

Scandal outcomes:
- reform drive (reduces capture but may provoke backlash)
- purge drive (targets rival factions, increases fear legitimacy)
- state hollowing (if scandal suppressed, shadow_state grows)

v1: deterministic choice based on leadership alignment and policing doctrine.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["shadow"]["petty_avg"]`
- `metrics["shadow"]["capture_avg"]`
- `metrics["shadow"]["shadow_state_avg"]`
- `metrics["shadow"]["shadow_balance_total"]`
- `metrics["shadow"]["scandals"]`

TopK:
- wards by capture index
- factions by shadow balance
- highest-value edges (strength * domain value)

Cockpit:
- corruption map: indices per ward
- edge viewer: who captures which domain, strength, exposure
- shadow budget ledger: sources and uses
- audit view: discrepancies vs official ledger, “missing barrels” proxies

Events:
- `SHADOW_FUNDS_ACCUMULATED`
- `CAPTURE_EDGE_STRENGTHENED`
- `CAPTURE_APPLIED`
- `SCANDAL_EXPOSED`
- `REFORM_ENACTED`
- `PURGE_ORDERED`

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/shadow_state.json` with indices, edges (bounded), and shadow accounts.

---

## 10) Tests (must-have)

Create `tests/test_shadow_state_deep_corruption_v1.py`.

### T1. Determinism
- same inputs → same edges, budgets, and scandals.

### T2. Smuggling increases shadow budgets
- higher smuggling strength yields larger shadow account balances.

### T3. Capture reduces enforcement and increases leakage
- custom capture reduces sanctions enforcement and increases leak.

### T4. Exposure triggers scandals
- higher exposure increases scandal event probability deterministically.

### T5. Reforms reduce capture
- reform outcome reduces capture indices and edge strengths.

### T6. Snapshot roundtrip
- edges, indices, and shadow accounts persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add shadow state module + state
- Create `src/dosadi/runtime/shadow_state.py` with ShadowStateConfig, InfluenceEdge, ShadowAccount, CorruptionIndex
- Add world corruption/edges/accounts to snapshots + seeds

### Task 2 — Implement shadow budget update
- Compute inflows from smuggling/cartels/tax skims and outflows to bribes/media/militia
- Maintain bounded shadow accounts deterministically

### Task 3 — Implement influence edge evolution + capture modifier helper
- Build/decay TopK influence edges per ward and apply capture modifiers in customs/policing/courts/depots and related modules

### Task 4 — Implement exposure and scandal/reform logic
- Generate scandals; choose reform vs purge vs suppression outcomes and apply deltas

### Task 5 — Cockpit + tests
- Add corruption map, edge viewer, and audit panels
- Add `tests/test_shadow_state_deep_corruption_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - shadow budgets accumulate and spend deterministically,
  - corruption evolves from petty to capture to shadow state,
  - key domains are biased by capture (sanctions, policing, cartels, finance),
  - exposure triggers scandals that can reform or harden the shadow state,
  - cockpit explains “why enforcement failed and where the money went.”

---

## 13) Next slice after this

**Reform Movements & Anti-Corruption Drives v1** — legitimacy restoration loops:
- reform coalitions, watchdog institutions,
- and the risk of counter-coups when reform bites too hard.
