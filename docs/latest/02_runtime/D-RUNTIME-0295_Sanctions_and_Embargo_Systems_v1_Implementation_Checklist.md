---
title: Sanctions_and_Embargo_Systems_v1_Implementation_Checklist
doc_id: D-RUNTIME-0295
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0274   # Diplomacy & Treaties v1
  - D-RUNTIME-0275   # Border Control & Customs v1
  - D-RUNTIME-0276   # Smuggling Networks v1
  - D-RUNTIME-0277   # Crackdown Strategy v1
  - D-RUNTIME-0293   # Insurance & Risk Markets v1
  - D-RUNTIME-0294   # Comms Failure & Jamming v1
---

# Sanctions & Embargo Systems v1 — Implementation Checklist

Branch name: `feature/sanctions-embargo-v1`

Goal: give diplomacy real teeth so that:
- treaties can impose trade restrictions and compliance requirements,
- customs can enforce embargoes at borders and key corridors,
- smuggling can subvert sanctions with measurable leakage,
- sanctions become a strategic tool (economic warfare) that shapes conflict.

v1 is macro trade restrictions, not item-by-item legal simulation.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same sanction outcomes and leak rates.
2. **Bounded.** TopK restricted goods and target sets; no explosion in rule count.
3. **Enforceable.** Sanctions must change trade flows and prices (0263).
4. **Leakage exists.** Smuggling makes enforcement imperfect but measurable.
5. **Composable.** Hooks into customs, diplomacy, war, insurance, and crackdowns.
6. **Tested.** Rule evaluation, enforcement, leakage, persistence.

---

## 1) Concept model

Sanctions are modeled as **rules** attached to:
- a treaty between parties (0274), OR
- a unilateral state decree, OR
- a faction embargo (guild cartelization).

A sanction rule specifies:
- who is sanctioned (target factions/wards),
- what is restricted (goods categories),
- what is restricted action (import/export/transit),
- what enforcement level is required,
- penalties for violation.

Sanctions operate at:
- customs checkpoints (0275),
- corridor chokepoints (0261),
- depots (0257),
- and market matching (0263).

---

## 2) Rule types (v1)

Support 4 rule kinds:
1) `EMBARGO_GOOD`
- ban or cap on a good category to/from target

2) `TARIFF_PUNITIVE`
- add tariff cost multiplier for target flows

3) `TRANSIT_DENIAL`
- deny passage through certain corridors for target factions/wards

4) `FINANCIAL_FREEZE`
- block payments/credit to target (ties into finance 0292) (optional v1: just apply a penalty)

Goods categories should match existing resource taxonomy:
- water, food, suits, weapons-equivalent (abstract), refined materials, medical supplies, etc.

---

## 3) Data structures

Create `src/dosadi/runtime/sanctions.py`

### 3.1 Config
- `@dataclass(slots=True) class SanctionsConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 1`
  - `deterministic_salt: str = "sanctions-v1"`
  - `max_rules_active: int = 200`
  - `max_goods_restricted_per_rule: int = 8`
  - `base_leak_rate: float = 0.10`          # smuggling leakage baseline
  - `enforcement_effect: float = 0.6`       # how much enforcement reduces leak
  - `comms_penalty_scale: float = 0.3`      # comms failures reduce enforcement
  - `penalty_scale: float = 0.25`           # political/economic penalty magnitude

### 3.2 Sanction rule
- `@dataclass(slots=True) class SanctionRule:`
  - `rule_id: str`
  - `issuer_id: str`                 # state or faction
  - `treaty_id: str | None`
  - `kind: str`                      # EMBARGO_GOOD|TARIFF_PUNITIVE|TRANSIT_DENIAL|FINANCIAL_FREEZE
  - `target_kind: str`               # WARD|FACTION|TERRITORY|CORRIDOR
  - `target_id: str`
  - `goods: list[str]`               # category strings
  - `severity: float`                # 0..1
  - `start_day: int`
  - `end_day: int`                   # inclusive/exclusive okay, pick one
  - `enforcement_required: float`    # 0..1
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Compliance state (bounded)
- `@dataclass(slots=True) class SanctionsCompliance:`
  - `entity_id: str`                 # ward_id or faction_id
  - `violations_lookback: int = 0`
  - `leak_rate_est: float = 0.0`
  - `penalties_applied: float = 0.0`
  - `last_update_day: int = -1`

World stores:
- `world.sanctions_cfg`
- `world.sanction_rules: dict[str, SanctionRule]`
- `world.sanctions_compliance: dict[str, SanctionsCompliance]`
- `world.sanctions_events: list[dict]` (bounded)

Persist rules and compliance in snapshots and seeds.

---

## 4) Enforcement capacity and leakage

Enforcement capacity comes from:
- customs resources (0275)
- law enforcement capacity (0265/0290 staffing)
- crackdown posture (0277)
- comms reliability (0294) (bad comms → lower enforcement effectiveness)

Leakage comes from:
- smuggling network strength (0276) in the region
- corridor risk and escort coverage (0261)
- shadow protection (0293) (can increase or decrease leakage depending on who controls it)

Compute effective enforcement per border/corridor/ward:
- `E = clamp(base + enforcement_inputs - comms_penalty, 0..1)`

Compute leak rate:
- `leak = base_leak_rate * (1 + smuggling_strength) * (1 - E*enforcement_effect)`
Clamp 0..1.

Deterministic.

---

## 5) Applying sanctions to trade flows (0263/0238)

Integration points:

### 5.1 Route planning / transit denial
When planning a delivery:
- if TRANSIT_DENIAL applies to corridor or region and actor matches target:
  - route planner must avoid corridor (or pay huge risk penalty)
- if unavoidable, delivery fails deterministically.

### 5.2 Embargo / tariff
When computing route cost:
- if EMBARGO applies, flow must:
  - be blocked OR
  - become “smuggled flow” with leak probability and added cost
- if TARIFF applies:
  - add cost multiplier proportional to severity and enforcement

### 5.3 Smuggling override
If smuggling network exists:
- some proportion of blocked flows become smuggled flows.
This shows up as:
- reduced official volume,
- increased black market volume (future or proxied),
- and increased enforcement incidents.

---

## 6) Compliance scoring and penalties

For each sanctioned entity weekly:
- estimate violations from:
  - smuggled flow volume,
  - customs interceptions,
  - market anomalies (price/volume divergence)
- update SanctionsCompliance

Penalties (issuer can apply):
- legitimacy hit to violator (naming and shaming)
- increased tariffs next period
- diplomatic escalation (treaty breach event)
- enforcement escalation (more inspections, raids)

v1 minimal: apply a bounded penalty to the target’s economy efficiency and legitimacy.

---

## 7) Incidents

Use Incident Engine (0242):
- `CUSTOMS_SEIZURE`
- `SMUGGLING_CRACKDOWN`
- `TREATY_BREACH`
- `EMBARGO_RIOT` (shortage triggered)
- `SANCTIONS_ESCALATION`

Effects:
- seizure reduces smuggling strength temporarily but increases violence risk
- embargo riot increases unrest if critical goods restricted.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["sanctions"]["rules_active"]`
- `metrics["sanctions"]["blocked_volume_proxy"]`
- `metrics["sanctions"]["smuggled_volume_proxy"]`
- `metrics["sanctions"]["violations"]`
- `metrics["sanctions"]["seizures"]`
- `metrics["sanctions"]["avg_leak_rate"]`

TopK:
- most-leaked embargoes
- entities with most violations
- corridors with most seizures

Cockpit:
- sanctions register: active rules, targets, goods, severity, duration
- compliance dashboard: violations and leak estimates
- trade flow overlay: official vs smuggled proxy
- “why shortages happened” explainer: embargo + enforcement + comms status

Events:
- `SANCTION_ISSUED`
- `SANCTION_EXPIRED`
- `SANCTION_VIOLATION`
- `CUSTOMS_SEIZURE`
- `SANCTIONS_ESCALATED`

---

## 9) Persistence / seed vault

Export stable:
- `seeds/<name>/sanctions.json` with rules and compliance.

---

## 10) Tests (must-have)

Create `tests/test_sanctions_embargo_v1.py`.

### T1. Determinism
- same rules/enforcement/smuggling → same leak and outcomes.

### T2. Enforcement reduces leak
- higher enforcement yields lower leak monotonically.

### T3. Comms failures hurt enforcement
- comms outage increases leak and violations.

### T4. Transit denial blocks routes
- affected actor cannot route through denied corridor.

### T5. Tariffs increase costs and affect market prices
- punitive tariffs increase effective costs and shift market signals.

### T6. Snapshot roundtrip
- rules and compliance persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add sanctions module + rule state
- Create `src/dosadi/runtime/sanctions.py` with SanctionsConfig, SanctionRule, SanctionsCompliance
- Add world.sanction_rules and compliance to snapshots + seeds

### Task 2 — Implement enforcement/leakage computation
- Compute effective enforcement from customs/enforcement/crackdown and comms status
- Compute leak rate from smuggling strength and enforcement

### Task 3 — Integrate sanctions into route planning and market costs
- Apply transit denial to routing
- Apply embargo/tariff costs and smuggled flow conversions

### Task 4 — Compliance scoring and incidents
- Track violations and apply penalties
- Emit customs seizure and treaty breach incidents/events

### Task 5 — Cockpit + tests
- Add sanctions register and compliance dashboard
- Add `tests/test_sanctions_embargo_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - sanctions and embargoes materially change trade routes and prices,
  - enforcement and smuggling produce measurable leakage,
  - comms failures weaken compliance,
  - violations trigger penalties and incidents,
  - cockpit explains “what is restricted, who is cheating, and where.”

---

## 13) Next slice after this

**Policing Doctrine v2** — enforce the law differently:
- community policing vs terror policing,
- legitimacy tradeoffs,
- and a doctrine engine that shapes crackdown outcomes.
