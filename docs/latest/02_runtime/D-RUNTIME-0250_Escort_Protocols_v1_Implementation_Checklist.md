---
title: Escort_Protocols_v1_Implementation_Checklist
doc_id: D-RUNTIME-0250
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-24
depends_on:
  - D-RUNTIME-0238   # Logistics Delivery v1
  - D-RUNTIME-0240   # Construction Workforce Staffing v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0246   # Agent Courier Logistics v1
  - D-RUNTIME-0248   # Courier Micro-Pathing v1
  - D-RUNTIME-0249   # Local Interactions v1
---

# Escort Protocols v1 — Implementation Checklist

Branch name: `feature/escort-protocols-v1`

Goal: introduce an explicit, deterministic **escort/convoy protocol** for risky logistics,
so the world can respond to danger by:
- assigning escorts to courier missions,
- trading delivery speed/capacity for safety,
- producing clear events and memory that influence future routing/planning.

This keeps “security” as a *runtime policy* (not a full combat system yet).

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Feature flag default OFF.** With flag OFF, baseline behavior unchanged.
2. **Deterministic assignment.** Same state → same escort decisions and agent picks.
3. **Bounded compute.** No global scans to find escorts; use WorkforceLedger with bounded candidate pools.
4. **Clear release semantics.** Escorts are assignments that must be released on mission end.
5. **Belief-aware.** Escorts are requested based on route-risk beliefs/hazards (not random).

---

## 1) Concept model

### 1.1 Escort as an assignment
Escort is represented by additional agent assignments tied to a delivery:
- courier: `AssignmentKind.LOGISTICS_COURIER`
- escort(s): `AssignmentKind.LOGISTICS_ESCORT`

A delivery may have:
- 0 escorts (default)
- 1 escort (v1)
- (optional) small convoy size (v2)

### 1.2 What escort does (v1)
Escort affects outcomes in **Local Interactions**:
- reduces sabotage/conflict probability
- reduces delay severity
- reduces probability of delivery failure
Escort does not introduce combat; it is a policy modifier.

### 1.3 When escort is requested
A delivery requests escort if its planned route is “risky enough”, based on:
- mean/max of route hazard + route-risk belief scores
- current phase (phase 2 bias)
- optionally: cargo importance (construction-critical)

---

## 2) Implementation Slice A — Data structures + flags

### A1. Add config
Create module: `src/dosadi/runtime/escort_protocols.py`

**Deliverables**
- `@dataclass(slots=True) class EscortConfig:`
  - `enabled: bool = False`
  - `risk_threshold: float = 0.65`         # above this, request escort
  - `max_escorts_per_delivery: int = 1`
  - `escort_candidate_cap: int = 200`      # bounded agent scan cap
  - `escort_speed_penalty: float = 0.05`   # optional: slightly slower due to convoy
  - `escort_interaction_shift: float = 0.12`  # how much escort reduces sabotage/conflict probabilities
  - `phase2_threshold_delta: float = -0.05`   # easier to trigger escorts in phase 2
  - `min_idle_reserve: int = 2`            # don’t consume last idle agents

- `@dataclass(slots=True) class EscortState:`
  - `last_run_day: int = -1`
  - `requested_today: int = 0`
  - `assigned_today: int = 0`

### A2. Delivery fields (minimal)
Prefer not to churn schema, but we need to track escorts.

Option A (preferred): store escort ids in `delivery.notes`:
- `delivery.notes["escort_agent_ids"] = ["a-12"]`

Option B: add field:
- `delivery.escort_agent_ids: list[str] = field(default_factory=list)`

Pick one and be consistent; Option A is schema-light but slightly messier.

### A3. World integration
- Add `world.escort_cfg: EscortConfig`
- Add `world.escort_state: EscortState`
- Snapshot both.

---

## 3) Implementation Slice B — Risk scoring for a delivery route

### B1. Route risk score helper
Add helper:

`def delivery_route_risk(world, delivery_id: str, perspective_agent_id: str | None) -> float`

Compute from delivery route edges:
- `haz = mean(edge.hazard)` (or max)
- `bel = mean(belief_score(agent, "route-risk:{edge_key}"))`
- `risk = 0.5*haz + 0.5*bel` (configurable weights)

If route not present (fallback mode):
- use default 0.5.

### B2. Threshold adjustment by phase
If world phase == PHASE2:
- `effective_threshold = risk_threshold + phase2_threshold_delta` (delta likely negative)

---

## 4) Implementation Slice C — Escort request + assignment

### C1. When to evaluate
Evaluate escort needs at **delivery assignment time** (best), because:
- route is known,
- courier is selected,
- we can lock escorts immediately.

If a route changes (reroute):
- re-evaluate escort requirement (optional v1: do not reassign mid-mission; log a warning)

### C2. Deterministic escort selection
Implement:

`def choose_escort_agents(world, *, day: int, max_n: int, cap: int) -> list[str]`

Rules:
- Use WorkforceLedger to find idle agents.
- Deterministic ordering:
  - `sorted(agent_ids)` then filter idle.
- Bound by `cap` (inspect first cap agents, stop early when chosen).
- Respect `min_idle_reserve`:
  - if selecting escorts would drop idle count below reserve, skip escort.

Optional selection quality:
- prefer agents with higher `END` or a “security” skill, but keep deterministic.

### C3. Reserve escorts
If escort required and escorts available:
- for each escort agent:
  - `ledger.assign(Assignment(agent_id=..., kind=LOGISTICS_ESCORT, target_id=delivery_id, start_day=day, notes={...}))`
- store escort ids on delivery (notes or field)
- increment escort_state counters

If not available:
- proceed without escort but emit an event `ESCORT_UNAVAILABLE` (optional but recommended).

---

## 5) Implementation Slice D — Release semantics (mission end)

On delivery terminal state (DELIVERED/FAILED/CANCELED):
- release courier (already done in courier v1)
- release escorts:
  - unassign all `LOGISTICS_ESCORT` assignments targeting delivery_id
  - clear delivery escort ids

This must happen on all terminal paths (success, failure, incident cancellation).

---

## 6) Implementation Slice E — Interaction integration

Local Interactions should detect escort presence and shift probabilities.

### E1. Add escort detection helper
`def has_escort(world, delivery_id: str) -> bool`

### E2. Apply shifts
In Local Interactions resolution:
- if opportunity is courier_edge/courier_arrival and has_escort:
  - reduce sabotage/conflict probability by `escort_interaction_shift`
  - increase help probability slightly (optional)
  - clamp all thresholds to [0,1]

Also reduce severity:
- multiply delay_ticks by (1 - escort_interaction_shift) (small effect)

Keep this deterministic and bounded.

---

## 7) Optional: Speed penalty / convoy slowdown

If `escort_speed_penalty > 0`:
- increase per-edge travel ticks by a small factor when escorted.
This is optional and can be deferred; don’t complicate v1 if it risks regressions.

---

## 8) Telemetry + events

Add counters:
- `metrics["escort"]["requested"]`
- `metrics["escort"]["assigned"]`
- `metrics["escort"]["unavailable"]`
- `metrics["escort"]["missions_completed"]`

Emit events (optional):
- `ESCORT_REQUESTED`
- `ESCORT_ASSIGNED`
- `ESCORT_UNAVAILABLE`
- `ESCORT_RELEASED`

These become memory fodder (trust in system, perceived danger, etc.).

---

## 9) Tests (must-have)

Create `tests/test_escort_protocols.py`.

### T1. Flag off = baseline behavior
- With enabled=False, deliveries have no escorts and signatures match baseline.

### T2. Risk threshold triggers escort
- Create a delivery route with high hazard or high route-risk belief.
- Assert escort requested and assigned (if idle agents available).

### T3. Reserve prevents over-consumption
- With only a few idle agents, ensure min_idle_reserve prevents escort assignment.

### T4. Escort reduces sabotage/conflict in local interactions
- Create a deterministic opportunity where sabotage would occur without escort.
- With escort present, assert outcome shifts (e.g., sabotage no longer chosen or delay reduced).

### T5. Escorts released on mission end
- Delivery delivered or failed → escort assignments cleared.

### T6. Snapshot roundtrip
- Save mid-mission with escort assigned; load; complete mission.
- Same final signature.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add escort module + config/state
- Create `src/dosadi/runtime/escort_protocols.py` with EscortConfig/EscortState and helpers
- Add `world.escort_cfg` and `world.escort_state` to snapshots

### Task 2 — Risk scoring + request decision
- Implement `delivery_route_risk(...)`
- Evaluate escort need at delivery assignment time (phase-aware threshold)

### Task 3 — Deterministic escort selection + assignment
- Implement bounded selection using WorkforceLedger idle agents
- Assign `AssignmentKind.LOGISTICS_ESCORT` targeting the delivery
- Store escort IDs on delivery (notes or field)
- Emit optional events + telemetry

### Task 4 — Release semantics
- Ensure escorts are released on all terminal delivery outcomes

### Task 5 — Integrate with local interactions
- Detect escort presence and shift probabilities/severity deterministically

### Task 6 — Tests
- Add `tests/test_escort_protocols.py` implementing T1–T6

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=False: no behavior change.
- With enabled=True:
  - risky routes request escorts,
  - escorts are assigned deterministically when available,
  - local interactions are measurably safer with escorts,
  - escorts are always released on delivery termination,
  - save/load works mid-mission.

---

## 12) Next slice after this

**Construction Materials Economy v1** (resource production/consumption loop),
so escorts and route-risk interact with genuine scarcity and build pace.
