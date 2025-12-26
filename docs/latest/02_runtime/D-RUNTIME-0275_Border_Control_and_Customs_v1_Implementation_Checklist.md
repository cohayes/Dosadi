---
title: Border_Control_and_Customs_v1_Implementation_Checklist
doc_id: D-RUNTIME-0275
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0274   # Diplomacy & Treaties v1
---

# Border Control & Customs v1 — Implementation Checklist

Branch name: `feature/border-control-customs-v1`

Goal: add a corridor-politics layer that answers:
- who can move what, where?
- what gets inspected or taxed?
- how does contraband flow emerge?
- how do treaties and enforcement interact with smuggling tolerance?

This slice turns corridors into **political membranes**, not just paths.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same state/seed → same inspections/tariffs outcomes.
2. **Bounded.** Apply customs checks only on shipments that cross a “border” edge.
3. **Composable.** Works with escort policy, enforcement budgets, treaties, and ledger.
4. **Legible.** Telemetry can answer “why was this shipment seized?”
5. **Phase-aware.** P0 light customs, P2 aggressive and corrupt.
6. **Tested.** Inspection decisions, seizures, bribery/corruption, treaty exemptions.

---

## 1) Concept model

A “border” is any corridor segment where:
- controlling authority changes (territory boundary),
- customs policy changes (ward institutions have different dials),
- treaty specifies special passage rules.

Crossing a border triggers a **customs check**:
- tariff calculation,
- inspection probability,
- contraband detection roll,
- optional bribery / corruption diversion,
- possible seizure, delay, or reroute.

We do not require agent-level negotiation; all is deterministic from shipment metadata.

---

## 2) Data structures

Create `src/dosadi/runtime/customs.py`

### 2.1 Config
- `@dataclass(slots=True) class CustomsConfig:`
  - `enabled: bool = False`
  - `base_inspection_rate: float = 0.05`
  - `base_tariff_rate: float = 0.02`
  - `contraband_detection_base: float = 0.10`
  - `max_checks_per_day: int = 5000`          # safety cap
  - `deterministic_salt: str = "customs-v1"`
  - `phase_multipliers: dict[str, dict[str, float]]`  # inspection/tariff/detection/bribery

### 2.2 Policy dials per ward (extends institutions policy)
Extend `WardInstitutionPolicy` (0269) with:
- `customs_inspection_bias: float = 0.0`   # -0.5..+0.5
- `customs_tariff_bias: float = 0.0`       # -0.5..+0.5
- `customs_contraband_bias: float = 0.0`   # -0.5..+0.5
- `customs_bribe_tolerance: float = 0.1`   # 0..1

### 2.3 Shipment annotation
Ensure logistics shipments (0261/0238/0246) carry:
- `shipment_id`
- `owner_party` (ward or faction)
- `origin_ward`, `dest_ward`
- `route_corridors: list[str]`
- `cargo: dict[material, qty]`
- `declared_value: float` (or derive from material weights)
- `flags: set[str]` e.g. ('treaty_exempt', 'high_priority', 'suspicious')

### 2.4 Customs event record (bounded)
- `@dataclass(slots=True) class CustomsEvent:`
  - `day: int`
  - `shipment_id: str`
  - `border_at: str`                  # corridor_id or node_id
  - `from_control: str`
  - `to_control: str`
  - `inspection: bool`
  - `tariff_charged: float`
  - `contraband_found: bool`
  - `bribe_paid: float`
  - `outcome: str`                    # "CLEARED"|"DELAYED"|"SEIZED"|"REROUTED"
  - `reason_codes: list[str]`

World stores:
- `world.customs_cfg`
- `world.customs_events: list[CustomsEvent]` (bounded)
- `world.customs_counters` (optional)

Persist events in snapshots; seeds can omit event history (optional).

---

## 3) Border detection (when to check)

When a shipment traverses corridor edges, detect border crossings:
- using territory map from 0266:
  - owner/control at each node/ward
- or using ward institutions policy boundaries (if different policies between wards)

Define helper:
- `iter_border_crossings(route_corridors) -> list[BorderCrossing]`

Bounded:
- do not check every hop if route is long; only check where control/policy changes.

---

## 4) Inspection + tariff logic (deterministic)

For each border crossing (up to max_checks_per_day):
1) compute tariff rate:
- base_tariff_rate * (1 + policy_bias + phase_multiplier)
- apply treaty exemptions:
  - SAFE_PASSAGE or RESOURCE_SWAP treaties can set tariff to 0 or reduced
2) compute inspection probability:
- base_inspection_rate * (1 + bias + phase_multiplier)
- increase if shipment flagged suspicious
- decrease if escorted (0261/0265)
3) decide inspection deterministically:
- `pseudo_rand01(salt|day|shipment|border) < p_inspect`
4) if inspected:
- compute contraband detection probability:
  - contraband_detection_base * (1 + bias + phase_multiplier)
  - reduced by corruption (higher corruption → lower effective detection)
5) contraband found?
- deterministic pseudo-rand
6) bribery:
- if contraband found or tariff high, allow bribe attempt when corruption high or bribe_tolerance high
- bribe amount = function(tariff, cargo value, severity)
- if bribe paid successfully:
  - reduce/avoid seizure
  - transfer bribe in ledger to `acct:blackmarket` or corrupt ward account

Outcomes:
- CLEARED (normal)
- DELAYED (adds delay days to shipment)
- SEIZED (cargo removed; owner loses; customs may gain some)
- REROUTED (force alternate route; increases risk/cost)

All deterministic and bounded.

---

## 5) Contraband model (simple v1)

Define a small list of contraband tags/material categories:
- `NARCOTICS`
- `WEAPON_PARTS` (in-world, not real)
- `STOLEN_GOODS`
- `UNLICENSED_SUIT_MODS`
- `RAIDER_SUPPLIES`

Cargo can be marked contraband by:
- material type,
- origin/destination mismatches,
- faction ownership (raider shipments suspicious),
- treaty violations.

v1 can use a simple function:
- `contraband_score(shipment) -> 0..1`
and treat “contraband exists” if score above threshold.

---

## 6) Integration points

### 6.1 Ledger (0273)
- tariffs are payments from shipment owner to border authority:
  - from `acct:ward:<owner>` or `acct:fac:<owner>` to `acct:ward:<border_ward>` or `acct:state:treasury`
- bribes go to `acct:blackmarket` or directly to a corrupt faction acct

### 6.2 Treaties (0274)
- SAFE_PASSAGE exempts or reduces tariffs/inspections on specified corridors
- breaches can increase inspection rates for that party

### 6.3 Enforcement (0265) + Escort (0261)
- higher enforcement budgets increase detection and reduce bribery success
- escorted shipments are less likely to be extorted/delayed

### 6.4 Culture (0270) + Institutions (0269)
- smuggling_tolerance norm increases bribe_tolerance and reduces inspection aggressiveness (locally)
- anti_state norms may increase “harassment inspections” (optional)
- corruption increases bribery success and reduces true detection

### 6.5 Incidents (0242)
- seizures and harassment can increase unrest and strike/riot propensity (0271 synergy)

---

## 7) Telemetry + cockpit

Metrics:
- `metrics["customs"]["checks"]`
- `metrics["customs"]["inspections"]`
- `metrics["customs"]["seizures"]`
- `metrics["customs"]["tariffs_total"]`
- `metrics["customs"]["bribes_total"]`

TopK:
- busiest borders
- most seized owners
- most corrupt borders (bribes/check high)

Cockpit:
- customs events feed (recent N)
- border heatmap table (corridor_id -> checks/inspections/seizures/bribes)
- per party: tariffs paid, bribes paid, seizures suffered

Events:
- `CUSTOMS_CHECK`
- `CUSTOMS_SEIZURE`
- `CUSTOMS_BRIBE`

---

## 8) Tests (must-have)

Create `tests/test_border_control_customs_v1.py`.

### T1. Determinism
- same shipment + day + route → same customs outcome.

### T2. Treaty exemptions
- SAFE_PASSAGE reduces tariff/inspection as configured.

### T3. Corruption/bribery effect
- higher corruption increases bribe success and reduces seizures (bounded).

### T4. Ledger integration
- tariffs transfer balances correctly; bribes go to blackmarket/corrupt accounts.

### T5. Caps
- never exceed max_checks_per_day; remaining checks are deterministically skipped.

### T6. Snapshot roundtrip
- shipment delays/seizures persist; outcomes stable after load.

---

## 9) Codex Instructions (verbatim)

### Task 1 — Add customs module + configs
- Create `src/dosadi/runtime/customs.py` with CustomsConfig and CustomsEvent
- Extend WardInstitutionPolicy with customs dials
- Ensure shipments carry owner + cargo + route metadata needed

### Task 2 — Implement border detection + deterministic customs checks
- Detect border crossings where territory/policy changes
- Apply tariff and inspection logic with phase multipliers and escorts
- Handle contraband detection, delays, seizures, reroutes
- Emit events and store bounded CustomsEvent history

### Task 3 — Wire ledger + treaties + enforcement hooks
- Tariffs/bribes are ledger transfers
- Treaties modify inspection/tariff rates
- Enforcement budgets influence detection and bribery

### Task 4 — Telemetry + tests
- Cockpit panels and metrics/topK
- Add `tests/test_border_control_customs_v1.py` (T1–T6)

---

## 10) Definition of Done

- `pytest` passes.
- With enabled=True:
  - shipments crossing borders are taxed/inspected deterministically,
  - treaties create meaningful passage privileges,
  - corruption produces bribery and contraband flow,
  - the ledger records tariffs/bribes,
  - customs pressure can feed unrest/governance instability,
  - cockpit can explain outcomes per shipment and per border.

---

## 11) Next slice after this

**Smuggling Networks v1** — model contraband supply chains explicitly:
- raiders choose preferred borders,
- bribery budgets allocate strategically,
- and enforcement learns where to focus.
