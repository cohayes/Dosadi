---
title: Decision_Hooks_v1_Implementation_Checklist
doc_id: D-RUNTIME-0245
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-16
depends_on:
  - D-RUNTIME-0236   # Expansion Planner v1
  - D-RUNTIME-0238   # Logistics Delivery v1
  - D-RUNTIME-0240   # Workforce Staffing v1
  - D-RUNTIME-0243   # Event → Memory Router v1
  - D-RUNTIME-0244   # Belief Formation v1
---

# Decision Hooks v1 — Implementation Checklist

Branch name: `feature/decision-hooks-v1`

Goal: make the simulation *visibly adaptive* by wiring beliefs into a few high-leverage decisions:
- expansion site selection,
- route selection / delivery planning,
- staffing allocation and risk posture.

This is intentionally a small set of hooks that:
- are deterministic and testable,
- preserve performance,
- don’t require full “awake agent” micro-simulation.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic decisions.** Same seed + same beliefs → same chosen actions.
2. **Bounded computation.** Beliefs are queried O(1) per candidate; no global scans.
3. **Graceful fallback.** If beliefs missing, behavior matches old planner/logistics defaults.
4. **No hard coupling.** Hooks read beliefs but do not mutate memory directly.
5. **Measurable impact.** Add telemetry and tests that prove beliefs change outcomes.

---

## 1) Belief query API (small & explicit)

Create a tiny helper module: `src/dosadi/runtime/belief_queries.py`

### Deliverables
- `def belief_value(agent, key: str, default: float = 0.5) -> float`
- `def belief_weight(agent, key: str, default: float = 0.0) -> float`
- `def belief_score(agent, key: str, default: float = 0.5) -> float`
  - recommended: blend value with weight so weak beliefs don’t dominate
  - example: `score = default*(1-weight) + value*weight`

Also add helpers that compute composite scores:
- `route_risk(agent, edge_key) -> float`
- `facility_reliability(agent, facility_id) -> float`

---

## 2) Hook A — Expansion Planner: belief-aware site ranking

### A1. Add “planner perspective agent”
To avoid “all agents” consensus, choose a *single deterministic perspective*:
- `planner_agent_id`:
  - if a steward/council agent exists, use it;
  - else choose the lexicographically smallest agent_id.

### A2. Site scoring function (v1)
In `ExpansionPlanner`, when evaluating candidate nodes/sites, compute:

`score(site) = base_score(site) - w_route * route_risk_to_site - w_supply * supply_risk - w_fac * facility_failure_risk`

- `route_risk_to_site`:
  - if you have a path of edges, take mean/max of `route-risk:{edge_key}` beliefs
  - if no path, use default 0.5
- `supply_risk` (optional v1):
  - if site is far (distance proxy), raise risk
- `facility_failure_risk`:
  - if planning depends on an existing facility, use `facility-reliability:{facility_id}` (interpreted as risk)

Config knobs:
- `planner_cfg.belief_route_weight: float = 0.25`
- `planner_cfg.belief_supply_weight: float = 0.10`
- `planner_cfg.belief_facility_weight: float = 0.15`

Keep weights small in v1.

### A3. Deterministic tie-breaks
After score sort, tie-break by:
- node_id (stable)
- project_kind priority

### A4. Telemetry
Emit 1 event per planning cycle:
- `PLANNER_SITE_RANKING` with top 3 sites and their components.

---

## 3) Hook B — Logistics: route selection and risk-aware cost

### B1 (minimal): Risk-aware route preference
When choosing among multiple candidate edges/routes:
- prefer lower route risk belief, using the *delivery owner perspective*:
  - if delivery has courier agent id, use that agent
  - else use planner_agent_id

Implementation:
- if you already compute a route (list of edges), add an alternate route set only if available.
- if not, adjust a “route cost” for each edge:

`edge_cost = base_cost * (1 + w_route_risk * (risk - 0.5))`

Where `risk = belief_score(agent, "route-risk:{edge_key}")`.

Config:
- `logistics_cfg.route_risk_cost_weight: float = 0.30`

### B2 (optional): Risk-informed incident likelihood (still deterministic)
Rather than randomizing outcomes, bias **incident engine target selection**:
- when sampling delivery-related incidents, weight candidate deliveries by mean route risk.

This preserves determinism and makes beliefs predictive.

---

## 4) Hook C — Workforce staffing: risk posture and reserve tuning

Add a **risk posture scalar** derived from beliefs to staffing decisions.

### C1. Derive posture
From planner agent’s beliefs:
- `avg_route_risk` over last known critical corridor edges (or sample of top-K route-risk beliefs)
- `avg_facility_risk` over active facilities

Then:
- `posture = clamp(0.5 + (avg_risk - 0.5), 0.0, 1.0)`  # 0=bold, 1=cautious

### C2. Apply to staffing config
Adjust:
- `min_idle_agents = base + round(posture * extra_reserve)`
- reduce `project_workers_default` slightly when posture high
- increase `facility_staff_default` when posture high

Keep bounds tight to avoid thrash; apply no more than once/day.

---

## 5) Guardrails against feedback loops

Beliefs should not instantly flip decisions in unstable ways.

v1 stabilization rules:
- require belief weight >= 0.2 before applying it strongly (else treat as default)
- cap per-cycle changes:
  - planner: cannot change more than 1 project choice solely due to beliefs (optional)
  - staffing: `max_changes_per_cycle` already bounds reassignment churn

---

## 6) Runtime integration order

Per simulated day (macro-step):
1. systems update (projects/logistics/facilities)
2. events + router + belief formation
3. **apply decision hooks**
   - planner runs with belief-aware scoring
   - logistics planning uses belief-aware costs
   - staffing posture adjusts config

This ensures beliefs reflect yesterday’s outcomes before influencing today.

---

## 7) Save/Load integration

No new save formats required if beliefs are already serialized.
Ensure any new config fields and posture caches are either:
- stored in snapshot, or
- derived deterministically each day (preferred).

---

## 8) Tests (must-have)

Create `tests/test_decision_hooks.py`.

### T1. Planner site preference changes with beliefs
- Build a small SurveyMap with two candidate sites A and B with equal base score.
- Give planner agent a higher route-risk belief on path to A.
- Assert planner chooses B.

### T2. Logistics edge cost changes deterministically
- Given two edges with same base cost:
  - set route-risk for edge1 higher than edge2
  - assert chosen route prefers edge2.

### T3. Staffing reserve increases with high risk
- Set average route risk high, run staffing policy, assert min_idle_agents increased (within cap).

### T4. Fallback behavior
- With empty beliefs, planner/logistics decisions match baseline (compare signatures).

### T5. Snapshot stability
- Save mid-run, load, continue; ensure identical choices.

---

## 9) Codex Instructions (verbatim)

### Task 1 — Add belief query helpers
- Create `src/dosadi/runtime/belief_queries.py` with `belief_value/weight/score`
- Add small helpers for route risk and facility reliability

### Task 2 — Wire into Expansion Planner
- Choose deterministic `planner_agent_id`
- Add belief-weighted components to site scoring with small weights
- Add deterministic tie-breaks and telemetry

### Task 3 — Wire into Logistics
- Adjust edge/route costs with route-risk belief scores
- (Optional) bias delivery incident sampling by mean route risk

### Task 4 — Wire into Workforce staffing
- Derive risk posture from beliefs and adjust reserve / default worker splits
- Keep within tight bounds to avoid thrash

### Task 5 — Tests
- Add `tests/test_decision_hooks.py` implementing T1–T5

---

## 10) Definition of Done

- `pytest` passes.
- Planner choices change in predictable ways when beliefs change.
- Logistics prefers lower-risk routes deterministically.
- Staffing becomes more conservative under high perceived risk.
- With no beliefs, behavior matches baseline.

---

## 11) Next slice after this

**Agent Courier Logistics v1** (replace abstract carriers with assigned agents),
so agents accumulate lived route experiences and route-risk beliefs become grounded.
