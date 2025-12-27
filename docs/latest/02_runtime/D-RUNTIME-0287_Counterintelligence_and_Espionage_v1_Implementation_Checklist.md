---
title: Counterintelligence_and_Espionage_v1_Implementation_Checklist
doc_id: D-RUNTIME-0287
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0246   # Agent Courier Logistics v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0264   # Faction Interference v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0276   # Smuggling Networks v1
  - D-RUNTIME-0277   # Crackdown Strategy v1
  - D-RUNTIME-0286   # Media & Information Channels v1
---

# Counterintelligence & Espionage v1 — Implementation Checklist

Branch name: `feature/counterintel-espionage-v1`

Goal: move from passive interceptions (0286) to active operations so that:
- spy cells run recruitment, bribery, sabotage, and theft of secrets,
- defenders allocate counterintelligence and internal security budgets,
- information asymmetry becomes a durable power source,
- smuggling networks carry secrets and agents, not just goods.

v1 is macro intel ops, not stealth pathfinding.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same ops selection and outcomes.
2. **Bounded.** TopK targets and bounded active ops; no per-agent stealth sim.
3. **Two-sided game.** Attackers and defenders both optimize under budgets.
4. **Composable.** Integrates with media channels, crackdowns, war, and smuggling.
5. **Explainable.** Each op has a reason, target, cost, and outcome.
6. **Tested.** Determinism, detection/coverage, persistence, and effect wiring.

---

## 1) Concept model

Intel is handled via “operations”:
- attackers launch ops to gain info or disrupt channels,
- defenders run counterintel to detect and degrade ops.

Operations types (v1):
- `BRIBE_COURIER` (increase interception and distortion)
- `PLANT_INFORMANT` (increase visibility into ward/faction metrics)
- `SABOTAGE_RELAY` (reduce relay bandwidth / increase loss rate)
- `STEAL_LEDGER` (steal budget points or expose corruption)
- `FALSE_FLAG_PROPAGANDA` (inject propaganda messages with spoofed sender)

Each operation:
- lasts N days,
- applies modifiers during that window,
- can be detected and dismantled.

---

## 2) Data structures

Create `src/dosadi/runtime/espionage.py`

### 2.1 Config
- `@dataclass(slots=True) class EspionageConfig:`
  - `enabled: bool = False`
  - `max_ops_active: int = 20`
  - `candidate_topk: int = 24`
  - `op_duration_days: int = 7`
  - `deterministic_salt: str = "espionage-v1"`
  - `base_detect_rate: float = 0.05`
  - `base_success_rate: float = 0.25`
  - `counterintel_efficiency: float = 0.8`

### 2.2 Ops model
- `@dataclass(slots=True) class IntelOpPlan:`
  - `op_id: str`
  - `day_started: int`
  - `day_end: int`
  - `attacker_faction: str`
  - `defender_faction: str | None`    # optional
  - `target_kind: str`               # "CORRIDOR"|"WARD"|"RELAY"|"FACTION"|"COURIER_CLASS"
  - `target_id: str`
  - `op_type: str`
  - `intensity: float`               # 0..1
  - `budget_cost: float`
  - `reason: str`
  - `score_breakdown: dict[str, float] = field(default_factory=dict)`

- `@dataclass(slots=True) class IntelOpOutcome:`
  - `op_id: str`
  - `day: int`
  - `status: str`                    # ACTIVE|SUCCEEDED|FAILED|DETECTED|DISMANTLED|EXPIRED
  - `effects: dict[str, object] = field(default_factory=dict)`
  - `loot: dict[str, float] = field(default_factory=dict)`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.espionage_cfg`
- `world.intel_ops_active: dict[str, IntelOpPlan]`
- `world.intel_ops_history: list[IntelOpOutcome]` (bounded)
- `world.counterintel_by_ward: dict[str, float]`  # coverage 0..1 (simple v1)
Persist active ops and counterintel coverage.

---

## 3) Counterintelligence budget and coverage

Defenders allocate counterintel via institutions (0269):
- policy dial: `counterintel_spend_bias` (-0.5..+0.5)
- optional: `internal_security_strictness` (0..1)

Each day or week:
- pay `PAY_COUNTERINTEL` via ledger (0273),
- convert spend into coverage per ward/corridor TopK:
  - coverage weighted toward high-risk wards, relays, and borders.

Coverage affects:
- detect rate,
- op failure probability,
- and severity of attacker penalties when caught.

Bounded: 36 wards is fine.

---

## 4) Candidate target generation (TopK)

Attackers consider targets from:
- high-value corridors (war/logistics),
- relays/broadcast hubs (0286),
- wards with high budgets/corruption (0273/0271),
- factions with high propaganda reach (0285/0286),
- courier-heavy routes (0246).

Defenders consider:
- high interception corridors,
- relay nodes,
- wards with fast ideology swings (0285),
- smuggling hotspots (0276),
- prior detected ops.

TopK and deterministic tie breaks.

---

## 5) Op selection (attacker) and defense posture (defender)

Implement:
- `propose_intel_ops_for_day(world, day)`

Attackers choose ops by utility:
- expected value of intel/disruption/loot
- minus cost
- minus detection risk (counterintel coverage)
- minus political blowback if detected

Defenders choose counterintel allocations by risk:
- maximize expected prevented harm per budget

Cap active ops: max_ops_active.

---

## 6) Resolution mechanics (deterministic)

Each op progresses daily:
- compute success probability:
  - base_success_rate * intensity * attacker_capability
  - reduced by counterintel coverage and enforcement pressure (0277/0265)
- compute detect probability:
  - base_detect_rate + coverage bonus + random audits
- resolve with deterministic pseudo-rand keyed on (salt, op_id, day)

Possible transitions:
- ACTIVE → SUCCEEDED (apply effects)
- ACTIVE → DETECTED (defender learns; apply partial effect maybe)
- DETECTED → DISMANTLED (op ends early, penalties)
- ACTIVE → FAILED or EXPIRED

When detected:
- defender can “roll up” a network: temporary reduction to attacker future success (cooldown).

---

## 7) Effects wiring (concrete modifiers)

### 7.1 BRIBE_COURIER
- increases interception_rate and distortion_rate for COURIER messages on a corridor or corridor set
- can cause targeted drops for priority messages

### 7.2 PLANT_INFORMANT
- grants attacker improved “intel feed”:
  - reduces staleness on certain metrics for target ward
  - can boost raid planning accuracy (0278) (optional v1: just add a score bonus)
Represent as: `world.intel_visibility[(attacker, ward)] = level` with expiry.

### 7.3 SABOTAGE_RELAY
- reduces relay bandwidth per day at a relay ward
- increases loss_rate for RELAY hops through that node

### 7.4 STEAL_LEDGER
- transfers budget points from a victim account to attacker (bounded, cap)
- OR exposes corruption: increases crackdown candidate scores (0277) if shared with state

### 7.5 FALSE_FLAG_PROPAGANDA
- emits PROPAGANDA messages (0286) with spoofed sender_id and reduced integrity
- if discovered, legitimacy hits for blamed party; increases culture war intensity (0270/0285)

All effects must be reversible and time-bounded.

---

## 8) Discovery, attribution, and politics

Detection creates:
- attribution probability (who did it?)
- if attribution is wrong, can trigger diplomatic incidents (0274) or internal purges (0271)

v1 minimal:
- store `suspected_attacker` in outcome notes
- apply small legitimacy/unrest adjustments based on detection and attribution confidence.

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["espionage"]["ops_active"]`
- `metrics["espionage"]["ops_started"]`
- `metrics["espionage"]["ops_detected"]`
- `metrics["espionage"]["ops_succeeded"]`
- `metrics["espionage"]["relay_sabotaged_days"]`
- `metrics["espionage"]["message_intercepts_delta"]`

TopK:
- corridors by intercept rate
- wards by counterintel coverage
- factions by op success/detection rate

Cockpit:
- ops list: attacker, target, type, status, reason, score breakdown
- counterintel map: coverage by ward and relay
- message channel diagnostics: show which ops altered loss/interception
- “stolen ledger” report: transfers and audits triggered

Events:
- `INTEL_OP_STARTED`
- `INTEL_OP_SUCCEEDED`
- `INTEL_OP_DETECTED`
- `INTEL_OP_DISMANTLED`
- `INTEL_OP_FAILED`

---

## 10) Persistence / seed vault

Persist:
- active ops,
- counterintel coverage,
- optional recent history.
Seeds can omit ops history.

---

## 11) Tests (must-have)

Create `tests/test_counterintelligence_espionage_v1.py`.

### T1. Determinism
- same budgets/coverage → same ops chosen and outcomes.

### T2. Counterintel reduces success
- higher coverage reduces attacker success rate deterministically.

### T3. Relay sabotage effect
- sabotage reduces relay throughput and increases message loss.

### T4. Courier bribery effect
- bribery increases interception on targeted corridor.

### T5. False flag propaganda
- emits propaganda messages and can shift ideology if not blocked.

### T6. Ledger theft bounded
- ledger steal transfers are capped and never create negative balances unless allowed.

### T7. Snapshot roundtrip
- active ops and coverage persist after load.

---

## 12) Codex Instructions (verbatim)

### Task 1 — Add espionage module + state
- Create `src/dosadi/runtime/espionage.py` with EspionageConfig, IntelOpPlan, IntelOpOutcome
- Add world.intel_ops_active and counterintel coverage to snapshots + seeds

### Task 2 — Implement counterintel budgets and coverage
- Add institution dials and ledger spending for counterintel
- Compute coverage focused on high-risk wards/relays/corridors

### Task 3 — Implement attacker op planning + daily resolution
- Generate TopK targets, score ops, activate under max_ops_active
- Resolve daily deterministically with success/detect transitions
- Emit events and apply reversible modifiers

### Task 4 — Wire effects into media/war/crackdown/ideology
- Apply courier bribery and relay sabotage to media loss/intercept
- Plant informants improves attacker intel inputs
- Ledger theft affects budgets or triggers audits
- False flag propaganda emits messages and affects ideology

### Task 5 — Telemetry + tests
- Cockpit ops list and coverage map
- Add `tests/test_counterintelligence_espionage_v1.py` (T1–T7)

---

## 13) Definition of Done

- `pytest` passes.
- With enabled=True:
  - attackers run active intel ops and defenders allocate counterintel,
  - media channels show targeted interception/sabotage dynamics,
  - war and crackdowns respond to improved intel or scandal,
  - politics reflect detections and (mis)attribution,
  - system creates durable information asymmetry over centuries,
  - cockpit explains the intel war state.

---

## 14) Next slice after this

**Religion & Ritual Power v1** — an orthodoxy engine:
- rituals as coordination tech,
- clergy as parallel institutions,
- and legitimacy as a contested spiritual commodity.
