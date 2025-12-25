---
title: Corridor_Risk_and_Escort_Policy_v2_Implementation_Checklist
doc_id: D-RUNTIME-0261
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0234   # Survey Map v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0246   # Agent Courier Logistics v1
  - D-RUNTIME-0248   # Courier Micro-Pathing v1
  - D-RUNTIME-0249   # Local Interactions v1
  - D-RUNTIME-0250   # Escort Protocols v1
  - D-RUNTIME-0254   # Suit Wear & Repair v1
  - D-RUNTIME-0255   # Exploration & Discovery v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0259   # Expansion Planner v2
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
---

# Corridor Risk & Escort Policy v2 — Implementation Checklist

Branch name: `feature/corridor-risk-escort-policy-v2`

Goal: close the loop between *incidents* and *logistics* by introducing:
- a deterministic, bounded **corridor risk model** (edge/node risk),
- an **escort policy** that escalates escort requirements when risk rises,
- instrumentation so you can see: which corridors are dangerous, why, and what escorts are doing about it.

This makes “empire expansion” self-correct: risky routes become defended routes, or routes are avoided.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same risk scores and escort decisions.
2. **Bounded.** No global per-day scanning of all edges; update only edges that saw traffic/incidents.
3. **Feature-flagged.** v2 logic behind config; v1 escort remains available.
4. **Monotone where sensible.** More incidents/attrition on a corridor must not reduce its risk score.
5. **Save/Load safe.** Risk ledger defaults empty; old snapshots load.
6. **Tested.** Risk updates, policy escalation, no duplication/spam.

---

## 1) Concept model

### 1.1 Corridor = map edge (plus optional node risk)
- Edge risk is the primary target: escorts protect shipments along edges.
- Node risk can exist as “area risk” but v2 can keep it edge-only.

### 1.2 Risk signals (inputs)
We use cheap signals already happening in the sim:
- incidents on deliveries/couriers (attack, theft, breakage, lost cargo)
- suit damage while traversing the corridor (proxy for harsh terrain / exposure)
- stalled deliveries / repeated failures (proxy for unreliability)
- discovery hazard estimates (from 0255 edge hazard)

Risk should be **learned/accumulated**, not randomized.

### 1.3 Risk outputs (used by planners)
- routing: prefer lower-risk edges if cost comparable
- escort policy: decide whether a delivery needs escort and how many
- expansion: planner may build safer corridors or depots to bypass risk (v2.1)

---

## 2) Implementation Slice A — Data structures

Create `src/dosadi/runtime/corridor_risk.py`

**Deliverables**
- `@dataclass(slots=True) class CorridorRiskConfig:`
  - `enabled: bool = False`
  - `risk_decay_per_day: float = 0.01`          # 0..0.1 (slow fade)
  - `max_risk: float = 1.0`
  - `incident_weight: float = 0.25`
  - `suit_damage_weight: float = 0.10`
  - `stall_weight: float = 0.05`
  - `hazard_prior_weight: float = 0.30`         # from discovery edge hazard
  - `min_updates_per_day: int = 0`              # for cadence, optional
  - `max_edges_tracked: int = 5000`             # cap memory
  - `topk_hot_edges: int = 50`
  - `deterministic_salt: str = "corridor-risk-v2"`

- `@dataclass(slots=True) class EdgeRiskRecord:`
  - `edge_key: str`                 # stable key (e.g., "nodeA|nodeB")
  - `risk: float = 0.0`             # 0..1
  - `hazard_prior: float = 0.0`     # 0..1 (from SurveyMap edge hazard)
  - `incidents_lookback: int = 0`   # optional simple counter window
  - `suit_damage_ema: float = 0.0`  # exponential moving average
  - `stall_ema: float = 0.0`
  - `last_updated_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class CorridorRiskLedger:`
  - `edges: dict[str, EdgeRiskRecord]`
  - `hot_edges: list[str] = field(default_factory=list)`  # cached TopK ids
  - `def record(self, edge_key: str) -> EdgeRiskRecord`   # create default
  - `def signature(self) -> str`

Store on world:
- `world.risk_cfg`, `world.risk_ledger`

Snapshot them.

---

## 3) Implementation Slice B — Stable edge keys + hooks

### B1. Edge key normalization
Implement helper:
- `def edge_key(a: str, b: str) -> str:`
  - return `"a|b"` with lexical ordering so `edge_key(a,b)==edge_key(b,a)`.

### B2. Traffic hooks (cheap)
Where to hook:
- courier path step completion (0248) or delivery edge traversal event
- suit wear update on traversal (0254)
- incident engine when an incident is attached to an edge/delivery (0242)

Each hook should call:
- `observe_edge_traversal(edge_key, day, *, suit_damage=..., stalled=...)`
- `observe_edge_incident(edge_key, day, *, severity=...)`

No scanning. Only update observed edges.

---

## 4) Implementation Slice C — Risk update rule (deterministic)

Implement:
- `def update_edge_risk(world, edge_key: str, *, day: int, incident_severity: float=0.0, suit_damage: float=0.0, stall: float=0.0) -> None`

Rules:
1. Create/get record.
2. Apply time-based decay since last_updated_day:
   - `risk *= (1 - risk_decay_per_day) ** days_elapsed` (clamp)
   - also decay EMAs similarly or use standard EMA update.
3. Update EMAs:
   - `ema = alpha*x + (1-alpha)*ema` with alpha fixed (e.g., 0.2)
4. Compute new risk:
   - `base = hazard_prior_weight * hazard_prior`
   - `risk = clamp(base + incident_weight*incidents + suit_damage_weight*suit_damage_ema + stall_weight*stall_ema, 0, max_risk)`
   - where incidents is a bounded function of severity and recent count.

Monotonicity expectation:
- if incident severity increases (same day), risk should not decrease.

Important: avoid floating drift by rounding risk to e.g. 1e-6 or using Decimal? v2 can keep floats but round at serialization/signature time.

---

## 5) Implementation Slice D — Escort policy v2 (uses risk)

Create `src/dosadi/runtime/escort_policy_v2.py`

**Deliverables**
- `@dataclass(slots=True) class EscortPolicyV2Config:`
  - `enabled: bool = False`
  - `risk_threshold_warn: float = 0.35`
  - `risk_threshold_high: float = 0.60`
  - `risk_threshold_critical: float = 0.80`
  - `base_escort_count: int = 0`
  - `warn_escort_count: int = 1`
  - `high_escort_count: int = 2`
  - `critical_escort_count: int = 3`
  - `max_escorts_per_delivery: int = 3`
  - `max_escort_missions_per_day: int = 20`
  - `deterministic_salt: str = "escort-v2"`

- `@dataclass(slots=True) class EscortPolicyV2State:`
  - `last_run_day: int = -1`
  - `escorts_scheduled_today: int = 0`

World stores:
- `world.escort2_cfg`, `world.escort2_state`

Snapshot them.

### D1. Per-delivery escort requirement
Implement:
- `def required_escorts_for_route(world, route_edges: list[str]) -> int`
  - uses max risk across edges (or 90th percentile) to choose escort tier.
  - deterministic, bounded.

### D2. Scheduling escorts
Integrate with Logistics Delivery:
- when creating a delivery, compute required escorts:
  - if 0: no escort
  - if >0: attach escort requirement to delivery payload
- Decision Hooks or a dedicated scheduler assigns escort agents:
  - choose available guards in sorted agent_id order
  - create escort missions tied to delivery_id
  - respect max_escort_missions_per_day

Avoid duplicate escort scheduling:
- delivery payload stores `escort_mission_ids`; if present, do nothing.

---

## 6) Implementation Slice E — Routing / planning integration

### E1. Routing cost includes risk (optional v2)
If your routing supports weighted edges:
- add `risk_cost = risk * k` where k is small (e.g., 0.5–2.0) so high risk edges are avoided when alternatives exist.

Keep deterministic and configurable:
- `route_cfg.risk_weight`

### E2. Planner v2 signal hook
Expose:
- `risk_hot_edges = top-k risk edges`
Planner may:
- prioritize depots that reduce travel on hot edges,
- schedule escorts more aggressively,
- (v2.1) propose corridor improvement projects.

For v2, just surface risk_hot_edges in telemetry + allow escorts.

---

## 7) Performance safeguards

### 7.1 Edge ledger size cap
If edges exceed max_edges_tracked:
- evict lowest-risk edges deterministically:
  - sort by (risk asc, edge_key asc) and drop until cap met
This is O(N log N) rarely; trigger only when exceeding cap.

Alternative: keep a min-heap; implement later if needed.

### 7.2 Update batching
If many traversals per day, you may update risk per traversal OR aggregate per day:
- v2 recommended: aggregate daily per edge:
  - keep `daily_edge_stats[edge_key]` counters and apply one update/day
This reduces overhead. Implement if you already have daily cadence loops.

---

## 8) Telemetry + Admin display

Update DebugCockpit (0260) to show:
- Top 10 risky corridors (edge_key, risk, last incident day)
- Escorts scheduled today / active escort missions
- Deliveries requiring escorts

Metrics:
- `metrics["risk"]["edges_tracked"]`
- `metrics["risk"]["incidents_observed"]`
- `metrics["risk"]["top_edge_risk"][edge_key]` via TopK
- `metrics["escort_v2"]["escorts_scheduled"]`
- `metrics["escort_v2"]["deliveries_escorted"]`

Events:
- `CORRIDOR_RISK_UPDATED`
- `ESCORT_REQUIRED`
- `ESCORT_SCHEDULED`
- `ESCORT_COMPLETED` (optional)

---

## 9) Tests (must-have)

Create `tests/test_corridor_risk_and_escort_v2.py`.

### T1. Deterministic risk updates
- clone world; apply same observations; ledger signatures match.

### T2. Incident increases risk
- observe incident severity > 0; risk increases.

### T3. Decay works
- update day 0 then day+N without new signals; risk decreases deterministically.

### T4. Escort requirement tiers
- set edge risk to 0.2/0.5/0.7/0.9 and ensure required_escorts matches config.

### T5. No duplicate escort scheduling
- create delivery requiring escorts; run scheduler twice; still one set of escort missions.

### T6. Ledger cap eviction deterministic
- create > max_edges_tracked; ensure eviction picks lowest-risk edges deterministically.

### T7. Snapshot roundtrip
- save mid-risk ledger and mid-escort pending; load; continue; stable behavior.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Corridor risk ledger
- Create `src/dosadi/runtime/corridor_risk.py` with config + EdgeRiskRecord + ledger
- Add world.risk_cfg/world.risk_ledger to snapshots
- Implement stable edge_key normalization

### Task 2 — Hook observations
- Add calls to risk observation on traversal, suit damage, and incidents (no scanning)
- Update risk records deterministically with decay and EMAs

### Task 3 — Escort policy v2
- Create `src/dosadi/runtime/escort_policy_v2.py` with config/state
- Compute required escorts from route risk and attach to deliveries
- Schedule escort missions deterministically; prevent duplicates; enforce caps

### Task 4 — Telemetry + cockpit
- Add TopK risky corridors and escort stats to metrics
- Display in DebugCockpit

### Task 5 — Tests
- Add `tests/test_corridor_risk_and_escort_v2.py` (T1–T7)

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=False: v1 behavior unchanged.
- With enabled=True:
  - risk ledger updates only on observed edges,
  - risky corridors appear in cockpit,
  - deliveries on risky routes request escorts,
  - escort missions are scheduled deterministically and bounded,
  - risk decays and escalates sensibly,
  - save/load works.

---

## 12) Next slice after this

**Resource Refining Recipes v2** (turn raw scrap/salvage into higher-tier parts),
so the economy can climb a tech ladder and unlock more complex facilities.
