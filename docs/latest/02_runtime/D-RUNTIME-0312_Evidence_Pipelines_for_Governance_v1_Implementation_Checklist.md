---
title: Evidence_Pipelines_for_Governance_v1_Implementation_Checklist
doc_id: D-RUNTIME-0312
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
  - D-RUNTIME-0310   # Scenario Success Contracts v1
  - D-RUNTIME-0311   # Milestone KPIs & Scorecards v1
---

# Evidence Pipelines for Governance v1 — Implementation Checklist

Branch name: `feature/evidence-pipelines-governance-v1`

Goal: prevent “governance stalls” by standardizing how institutions obtain bounded,
actionable evidence. This slice ensures councils, doctrines, and enforcement can act even when:
- telemetry keys drift,
- incidents are sparse,
- or the world is quiet (no obvious triggers).

v1 introduces:
- a canonical **Evidence Catalog** (keys + semantics),
- an **Evidence Buffer** per polity (bounded TopK),
- automatic evidence producers (lightweight, cadence-based),
- and adapters for legacy metric/event sources.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Bounded.** No scanning all agents or facilities to build evidence. Use caches + TopK.
2. **Deterministic.** Same seed/state → same evidence items and ranks.
3. **Legible.** Evidence items must explain their source and confidence.
4. **Composable.** Works for councils, police doctrine, treaties/customs, and KPI scoring.
5. **Anti-stall.** If core evidence is missing, fallback producers generate coarse evidence.
6. **Tested.** “Council can act” tests: evidence produced, consumed, and persisted.

---

## 1) Concept model

Governance decisions require “proof”:
- corridor risk rising,
- queues unfair,
- depot stockpile unstable,
- shortages recurring,
- raids/insurgency growing,
- customs corruption suspected, etc.

Instead of each institution reaching into the world ad-hoc, we standardize a pipeline:

**Producers** → push bounded evidence items into → **EvidenceBuffer** → consumed by institutions.

This makes governance robust, fast, and testable.

---

## 2) Evidence Catalog (v1)

Create a canonical key registry in `src/dosadi/runtime/evidence.py`.

Evidence keys should be stable strings.

### 2.1 Core keys (minimum)

Logistics / corridors:
- `evidence.corridor_risk.topk` (TopK risky corridors)
- `evidence.delivery_failures.rate_7d`
- `evidence.delivery_delays.p95_7d`
- `evidence.depot_stockout.topk`
- `evidence.route_utilization.topk`

Safety / threats:
- `evidence.incidents.rate_7d`
- `evidence.raids.rate_30d` (stub until raids exist)
- `evidence.predation.pressure_30d` (stub until A2 exists)

Fairness / unrest:
- `evidence.queue_unfairness.topk`
- `evidence.grievance.index_7d` (derived proxy)
- `evidence.protocol_violations.rate_7d`

Governance capacity:
- `evidence.enforcement.load_7d`
- `evidence.audit_discrepancies.topk` (stub until truth regimes)
- `evidence.comms_outages.rate_7d` (if comms module exists)

Economy / scarcity:
- `evidence.shortages.topk`
- `evidence.ration_pressure.index_7d`

Each key has:
- expected payload schema,
- update cadence,
- primary source(s) (KPI store, incidents, module caches),
- and confidence semantics.

---

## 3) Data structures

Create `src/dosadi/runtime/evidence.py`

### 3.1 Evidence item
- `@dataclass(slots=True) class EvidenceItem:`
  - `key: str`
  - `polity_id: str`
  - `day: int`
  - `score: float`                     # 0..1 urgency
  - `confidence: float`                # 0..1 reliability
  - `payload: dict[str, object]`       # bounded
  - `sources: list[str]`               # e.g. ["kpi:logistics.delivery_failures", "incidents:DELIVERY_FAILED"]
  - `reason_codes: list[str] = field(default_factory=list)`

### 3.2 Evidence buffer
- `@dataclass(slots=True) class EvidenceBuffer:`
  - `polity_id: str`
  - `max_items: int = 64`
  - `items: dict[str, EvidenceItem] = field(default_factory=dict)`  # key -> item (latest)
  - `topk_index: list[str] = field(default_factory=list)`          # optional stable ordering
  - `last_update_day: int = -1`

World stores:
- `world.evidence_cfg`
- `world.evidence_by_polity: dict[str, EvidenceBuffer]`

Persist in snapshots and seeds.

### 3.3 Config
- `@dataclass(slots=True) class EvidenceConfig:`
  - `enabled: bool = True`
  - `update_cadence_days: int = 1`      # daily
  - `max_payload_items: int = 16`       # bound payload list sizes
  - `deterministic_salt: str = "evidence-v1"`

---

## 4) Producers (v1)

Create `src/dosadi/runtime/evidence_producers.py`

Each producer must be cheap and use bounded inputs:
- KPI store (0311)
- incidents buffer (0242)
- module caches (logistics, corridors, enforcement)
- optional ward summaries (already aggregated)

### 4.1 Required producers

1. **Corridor risk TopK**
   - Input: corridor module risk cache OR compute from existing corridor stats (bounded list)
   - Output: `evidence.corridor_risk.topk` payload list of up to K corridors:
     - `{corridor_id, risk, failures_7d, escort_policy}`

2. **Depot stockout TopK**
   - Input: depot stockpile policy module cache OR depot summaries
   - Output: `evidence.depot_stockout.topk` list:
     - `{depot_id, stockout_items, days_to_empty}`

3. **Shortages TopK**
   - Input: KPI `economy.water_shortage_severe_days`, ration pressure, stockouts
   - Output: `evidence.shortages.topk` list:
     - `{ward_or_polity, resource, severity}`

4. **Queue unfairness TopK**
   - Input: local interactions / queue telemetry (0250-ish), or a fairness proxy counter
   - Output: `evidence.queue_unfairness.topk` list:
     - `{facility_id, unfairness_score, complaints}`

5. **Incident rate 7d**
   - Input: incident log ring buffer
   - Output: `evidence.incidents.rate_7d` scalar payload:
     - `{count, rate}`

6. **Protocol violations rate 7d**
   - Input: enforcement logs + protocol system counters (if present)
   - Output: `evidence.protocol_violations.rate_7d`

7. **Governance load**
   - Input: enforcement queue length, active cases, patrol assignments
   - Output: `evidence.enforcement.load_7d`

### 4.2 Anti-stall fallback producers

If a producer’s primary source is missing, generate a coarse proxy:
- If corridor stats missing, use deliveries failure rate + known routes_active to infer “risk rising.”
- If depot inventory missing, use ration pressure and missed deliveries to infer “stockout risk.”
- If queue data missing, produce no unfairness evidence but emit `confidence=0.2` diagnostic evidence item:
  - key: `evidence.diagnostics.missing_source`
  - payload: `{missing: "queue.telemetry", impact: "cannot assess unfairness"}`

This ensures councils can still meet and choose conservative defaults.

---

## 5) Scoring and confidence (v1)

Define a simple normalized urgency score:
- `score = clamp01(w1*severity + w2*trend + w3*exposure)`

Where:
- severity from counts/shortage levels,
- trend from deltas vs previous 7d (store last values in buffer notes),
- exposure from affected population share (if available).

Confidence:
- high when produced from direct telemetry (incidents/KPIs),
- low when inferred via fallback proxies.

---

## 6) Consumption API

Expose stable functions for institutions:

- `get_evidence(buffer, key) -> EvidenceItem | None`
- `get_top_evidence(buffer, prefix, k=10) -> list[EvidenceItem]`
- `evidence_score(buffer, key) -> float`

Institutions must not reach into world state for raw data; they read evidence.

Update council/protocol systems to:
- read evidence keys,
- decide if thresholds exceeded,
- propose protocols/enforcement changes based on TopK items.

---

## 7) Wiring points

### 7.1 Daily update
In phase engine day transition (0241) or world daily tick:
- call `run_evidence_update(world, day)`
- producers update `world.evidence_by_polity[polity_id]`

### 7.2 Contracts + KPIs
- Success contract evaluators may optionally read evidence keys instead of raw metrics.
- KPI scoring may include evidence-derived warnings.

### 7.3 Admin views
Add evidence panels:
- “Top Evidence” list per polity
- per-key detail view (payload + score/confidence + sources)

---

## 8) Persistence / seed vault

Export:
- `seeds/<name>/evidence.json` (optional in v1; recommended for debugging replay)

At minimum, persist evidence in snapshots for time-travel debugging.

---

## 9) Tests (must-have)

Create `tests/test_evidence_pipelines_governance_v1.py`

### T1. Determinism
- same seed and same incident stream → identical evidence items.

### T2. Boundedness
- payload list sizes ≤ max_payload_items, buffer size ≤ max_items.

### T3. Producers work with real modules OR adapters
- run a small scenario; evidence keys exist in buffers even if empty.

### T4. Anti-stall diagnostics
- remove a source metric; ensure diagnostics evidence item appears with low confidence.

### T5. Council can act
- simulate corridor failures and stockouts; evidence score crosses threshold; council proposes a protocol (or generates a governance action request).

### T6. Snapshot roundtrip
- evidence buffers persist across snapshot/load.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add evidence core module
- Create `src/dosadi/runtime/evidence.py` with EvidenceConfig, EvidenceItem, EvidenceBuffer, registry of evidence keys and expected payload schemas
- Add `world.evidence_by_polity` and snapshot persistence

### Task 2 — Implement evidence producers
- Create `src/dosadi/runtime/evidence_producers.py` with daily update runner and required producers (corridor risk, depot stockout, shortages, queue unfairness, incident rate, protocol violations, governance load)
- Implement fallback proxy producers and diagnostics evidence

### Task 3 — Wire producers into daily cadence
- Call evidence update on day transitions (or daily cadence hook)

### Task 4 — Update institutions to consume evidence API
- Replace ad-hoc reads with `get_evidence()` / `get_top_evidence()` in council/protocol logic

### Task 5 — Admin panels
- Add evidence list/detail views in DebugCockpitCLI/AdminDashboardCLI

### Task 6 — Tests
- Add `tests/test_evidence_pipelines_governance_v1.py` (T1–T6)

---

## 11) Definition of Done

- `pytest` passes.
- Evidence keys exist and update daily.
- Councils and governance actions can operate without scanning the world.
- Missing telemetry produces diagnostics evidence (anti-stall).
- Admin views show evidence with score/confidence and sources.

---

## 12) Next slice after this

**D-RUNTIME-0313 World Event Bus & Subscriptions v1** — formalize a low-overhead event bus so that:
- KPIs, evidence, and incident capture are fed from a single stream,
- modules subscribe without poll loops,
- and performance budgets become enforceable.
