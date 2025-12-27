---
title: Metrology_and_Truth_Regimes_v1_Implementation_Checklist
doc_id: D-RUNTIME-0305
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
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0286   # Media & Information Channels v1
  - D-RUNTIME-0292   # Banking, Debt & Patronage v1
  - D-RUNTIME-0302   # Shadow State & Deep Corruption v1
  - D-RUNTIME-0303   # Reform & Anti-Corruption Drives v1
  - D-RUNTIME-0304   # Constitutional Settlements & Rights Regimes v1
---

# Metrology & Truth Regimes v1 — Implementation Checklist

Branch name: `feature/metrology-truth-regimes-v1`

Goal: model “what counts as official reality” so that:
- markets, taxes, rations, and contracts depend on measurement integrity,
- corruption can falsify ledgers and audit trails,
- reform and constitutional constraints can restore trustworthy measurement,
- polities can drift into “post-truth” regimes where numbers are propaganda,
- long-run seeds can end in stable technocracy or falsified hollow states.

v1 is macro: integrity indices + bounded fraud events, not per-transaction fraud.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same integrity drifts and fraud events.
2. **Bounded.** TopK fraud events per period; no scanning every ledger row.
3. **Composable.** Integrates with markets, balance sheet, banking, policing, and shadow state.
4. **Legible.** Explain “why the numbers are wrong” with reason codes.
5. **Phase-aware.** P0 high integrity; P2 propaganda and falsification.
6. **Tested.** Integrity effects and persistence.

---

## 1) Concept model

We represent “truth” as a set of integrity indices per polity and per ward:
- metrology integrity (weights/measures standards)
- ledger integrity (financial and stockpile accounting)
- census integrity (population and labor reporting)
- telemetry integrity (sensor logs, admin dashboards)
- judiciary integrity (contracts and verdicts reliability)

Truth regimes affect:
- tax/ration allocation (balance sheet and rations),
- market price signals and credit risk,
- enforcement fairness and corruption exposure,
- and the effectiveness of reform campaigns.

---

## 2) Integrity dimensions (v1)

Indices 0..1:
- `metrology` (calibration, measurement standards)
- `ledger` (accounting accuracy)
- `census` (population/labor truth)
- `telemetry` (logs/sensors truth)
- `judiciary` (contract enforcement truth)

Plus:
- `propaganda_pressure` (0..1) (drives falsification)
- `audit_capacity` (0..1) (ability to detect and correct)

---

## 3) Data structures

Create `src/dosadi/runtime/truth_regimes.py`

### 3.1 Config
- `@dataclass(slots=True) class TruthConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 30`
  - `deterministic_salt: str = "truth-v1"`
  - `max_fraud_events: int = 24`
  - `drift_scale_p2: float = 0.03`
  - `correction_scale: float = 0.04`
  - `fraud_rate_base: float = 0.002`
  - `truth_effect_scale: float = 0.25`

### 3.2 Integrity state (polity + ward)
- `@dataclass(slots=True) class IntegrityState:`
  - `scope_kind: str`                # POLITY|WARD
  - `scope_id: str`                  # polity_id or ward_id
  - `metrology: float = 1.0`
  - `ledger: float = 1.0`
  - `census: float = 1.0`
  - `telemetry: float = 1.0`
  - `judiciary: float = 1.0`
  - `propaganda_pressure: float = 0.0`
  - `audit_capacity: float = 0.5`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Fraud/correction event (bounded)
- `@dataclass(slots=True) class TruthEvent:`
  - `day: int`
  - `scope_kind: str`
  - `scope_id: str`
  - `kind: str`                      # FRAUD|CORRECTION|RECALIBRATION|CENSUS_REWRITE|LEDGER_FALSIFIED
  - `domain: str`                    # METROLOGY|LEDGER|CENSUS|TELEMETRY|JUDICIARY
  - `magnitude: float`               # 0..1 severity
  - `reason_codes: list[str]`
  - `effects: dict[str, object] = field(default_factory=dict)

World stores:
- `world.truth_cfg`
- `world.integrity_by_polity: dict[str, IntegrityState]`
- `world.integrity_by_ward: dict[str, IntegrityState]`
- `world.truth_events: list[TruthEvent]` (bounded)

Persist in snapshots and seeds.

---

## 4) Integrity drift (monthly)

Drift drivers:
- shadow state/capture indices (0302) reduce integrity
- policing procedural share and constitutional constraints (0296/0304) increase integrity
- reform campaigns (0303) increase audit_capacity and correct integrity
- propaganda pressure (0286 + leadership fear legitimacy 0299) reduces telemetry/ledger truth
- hardship and instability (0291/0298/0278) reduce census accuracy

Implement:
- `run_truth_regimes_update(world, day)`

Rules:
- In P0, drift small; P2 adds drift_scale_p2.
- audit_capacity corrects drift and can restore integrity toward 1.0.
- propaganda_pressure pushes some domains down even with audits (bounded).

---

## 5) Fraud and correction events (bounded)

Generate up to max_fraud_events per update across world:
- sample TopK high-risk scopes:
  - high capture, low integrity, high propaganda
For each, trigger:
- FRAUD events:
  - LEDGER_FALSIFIED (tax/ration misreporting)
  - METROLOGY_TAMPERED (short weights, barrel volumes)
  - CENSUS_REWRITE (ghost workers or missing refugees)
  - TELEMETRY_SPOOFED (dashboard lies)
  - JUDICIARY_RIGGED (contract enforcement bias)

Correction events:
- triggered by high audit_capacity and reform activity:
  - RECALIBRATION sweeps, audits, truth commissions.

Effects:
- change integrity indices
- emit “error bars” into dependent systems (markets, rations, credit).

---

## 6) Applying truth regime effects to the economy and governance

Provide helper:
- `measurement_noise(world, scope, domain) -> (bias, variance, flags)`

Integrations (v1 minimum):

### 6.1 Markets (0263)
- low ledger/metrology integrity increases price signal noise and volatility
- cartel manipulation (0301) becomes harder to detect when truth low

### 6.2 Balance sheet and rations (0273/0291)
- low ledger/census integrity increases misallocation and grievance
- “ghost rations” and missing barrels become a systemic phenomenon

### 6.3 Banking/credit (0292)
- low ledger integrity increases default risk and reduces lending efficiency

### 6.4 Policing and courts (0265/0296)
- low judiciary integrity increases selective enforcement and reduces procedural legitimacy (0299)

### 6.5 Shadow state exposure (0302) and reform (0303)
- low telemetry integrity reduces scandal detection
- high audit_capacity increases exposure and correction chances

Keep it scalar: compute noise factors and apply in those modules without scanning granular records.

---

## 7) Incidents

Use Incident Engine (0242):
- `BARREL_MEASURE_FRAUD_EXPOSED`
- `CENSUS_SCANDAL`
- `LEDGER_DISCREPANCY_FOUND`
- `TRUTH_COMMISSION`
- `TELEMETRY_BLACKOUT`
- `JUDGE_CORRUPTION_TRIAL`

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["truth"]["avg_integrity_ledger"]`
- `metrics["truth"]["avg_integrity_metrology"]`
- `metrics["truth"]["avg_integrity_census"]`
- `metrics["truth"]["propaganda_pressure_avg"]`
- `metrics["truth"]["fraud_events"]`
- `metrics["truth"]["corrections"]`

TopK:
- wards with lowest ledger integrity
- polities with highest propaganda pressure
- biggest fraud magnitude events

Cockpit:
- truth dashboard per polity: five integrity indices + audit capacity + propaganda
- fraud timeline: events and impacts
- “error bars” view: how uncertain are market prices and ration allocation
- audit leverage: expected correction per audit spend

Events:
- `TRUTH_FRAUD_EVENT`
- `TRUTH_CORRECTION_EVENT`
- `INTEGRITY_COLLAPSE_WARNING`

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/truth_regimes.json` with integrity states and event history (bounded).

---

## 10) Tests (must-have)

Create `tests/test_metrology_truth_regimes_v1.py`.

### T1. Determinism
- same inputs → same integrity drift and events.

### T2. Shadow state reduces integrity
- higher capture lowers ledger/telemetry integrity.

### T3. Reform increases audit capacity and corrections
- reform campaign improves audit_capacity and increases correction events.

### T4. Low integrity increases market volatility proxy
- decreasing ledger/metrology increases market noise outputs.

### T5. Propaganda pressure decreases telemetry truth
- increasing propaganda pressure reduces telemetry integrity and correction effectiveness.

### T6. Snapshot roundtrip
- integrity states and event history persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add truth regimes module + state
- Create `src/dosadi/runtime/truth_regimes.py` with TruthConfig, IntegrityState, TruthEvent
- Add world integrity_by_polity/ward and truth_events to snapshots + seeds

### Task 2 — Implement monthly drift + bounded fraud/correction events
- Update integrity indices from capture, reforms, propaganda pressure, and constitutional constraints
- Generate bounded fraud and correction events deterministically

### Task 3 — Provide measurement noise helper and wire into key modules
- Add `measurement_noise()` and apply noise factors into markets, balance sheet/rations, banking, and courts/policing legitimacy

### Task 4 — Telemetry + cockpit
- Add truth dashboards, fraud timelines, and error bar views

### Task 5 — Tests
- Add `tests/test_metrology_truth_regimes_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - integrity indices drift and recover deterministically,
  - fraud and correction events affect dependent systems via noise factors,
  - propaganda can collapse telemetry truth and hide corruption,
  - reforms and constitutions can restore truth regimes,
  - cockpit explains “how much you can trust the numbers.”

---

## 13) Next slice after this

**Federated Archives & Historical Narrative v1** — memory at the empire scale:
- official histories, revisionism, and the politics of archives,
- and how belief formation can be steered at society scale.
