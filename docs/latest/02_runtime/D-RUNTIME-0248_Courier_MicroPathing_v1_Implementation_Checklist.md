---
title: Courier_MicroPathing_v1_Implementation_Checklist
doc_id: D-RUNTIME-0248
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-24
depends_on:
  - D-RUNTIME-0234   # Survey Map v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0243   # Event → Memory Router v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1 (route-risk cost)
  - D-RUNTIME-0246   # Agent Courier Logistics v1
  - D-RUNTIME-0247   # Focus Mode v1 (Awake vs Ambient)
---

# Courier Micro-Pathing v1 — Implementation Checklist

Branch name: `feature/courier-micropathing-v1`

Goal: give couriers *real* (but still cheap) movement over the SurveyMap:
- choose a route (edges),
- traverse it over time (ticks or macro ticks),
- react to hazards / closures via deterministic reroute,
- produce better events + more grounded route-risk beliefs.

This is still not “full awake-agent sim” for everyone — it’s **mission-local pathing** for couriers
and (optionally) a small focus cohort.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic routing.** Same seed + same map → same chosen path.
2. **Bounded compute.** No unbounded A* per tick; pathfinding is done at assignment time and on rare reroutes.
3. **Stable tie-breaks.** If multiple shortest paths exist, choose consistently.
4. **Save/Load safe.** Courier progress along a path persists; reroute state persists.
5. **Works in both ambient + focus.** Ambient uses coarse stepping; focus uses per-tick stepping.

---

## 1) Concept model

### 1.1 Path = list of edges
A courier route is represented by:
- `nodes: [n0, n1, n2, ...]` or `edges: [e0, e1, ...]`
- `total_cost` (distance/time units)
- optional per-edge metadata: hazard score, closure flags, etc.

Store the path on the **delivery** (recommended) so it is world-state and survives save/load:
- `delivery.route_nodes: list[str]` (or ints)
- `delivery.route_edge_keys: list[str]` (stable key form)
- `delivery.route_index: int` (current segment)
- `delivery.remaining_edge_ticks: int` (progress within current edge)

### 1.2 Hazards and closures
SurveyMap edges can have:
- `base_cost` (distance)
- `hazard` in 0..1 (risk)
- `closed_until_day` (optional, phase/incident driven)

In v1:
- hazard affects **incident likelihood** and **belief** generation,
- closure forces reroute (deterministic).

### 1.3 Route selection cost function (v1)
Edge cost for pathfinding:

`cost(edge) = base_cost * (1 + w_risk * risk_component)`

Where:
- `risk_component` is either:
  - map hazard (edge.hazard), or
  - belief score (route-risk belief) from Decision Hooks, or
  - blend: `0.5*hazard + 0.5*belief_risk`
- `w_risk` small (0.25–0.5) in v1.

This makes route choice reflect both “objective hazard” and “learned fear”.

---

## 2) Implementation Slice A — SurveyMap routing API

### A1. Add a stable edge key
If not already present, define:
- `edge_key = "edge:{a}->{b}"` (directional) or sorted if undirected.
Make it consistent across the whole codebase.

### A2. Precompute adjacency for fast pathing
Add to SurveyMap:
- `adj: dict[node_id, list[(neighbor_id, edge_key)]]`

Build once when map is created/loaded.

### A3. Add a routing function
Create `src/dosadi/world/routing.py`

**Deliverables**
- `@dataclass(slots=True) class Route:`
  - `nodes: list[str]`
  - `edge_keys: list[str]`
  - `total_cost: float`

- `@dataclass(slots=True) class RoutingConfig:`
  - `enabled: bool = True`
  - `max_expansions: int = 5000`       # hard bound
  - `risk_weight: float = 0.35`
  - `hazard_weight: float = 0.50`      # blend factor
  - `belief_weight: float = 0.50`      # blend factor
  - `tie_break: str = "lex"`           # stable tie-break strategy
  - `cache_size: int = 2000`

- `def compute_route(world, *, from_node: str, to_node: str, perspective_agent_id: str | None) -> Route | None`
  - Uses Dijkstra/A* with deterministic tie-break.
  - Reads:
    - `edge.base_cost`
    - `edge.hazard`
    - `belief_score(perspective_agent, "route-risk:{edge_key}")` if available
  - Enforces `max_expansions`; returns None if exceeded.

### A4. Cache routes (bounded)
Add a simple LRU cache on world or routing module:
- key: `(from_node, to_node, risk_profile_hash)`
- value: Route

Where `risk_profile_hash` can be:
- `"none"` if no beliefs used
- or a coarse bucket of beliefs (v1: just `"beliefs:on"` to keep it simple)

Keep cache bounded by `cache_size`.

Important: caching must not break determinism. Use it as an optimization only; outputs must match.

---

## 3) Implementation Slice B — Delivery schema upgrade (route + progress)

### B1. Extend DeliveryRequest / Delivery state
Add fields (all optional/default empty so old snapshots can load):
- `route_nodes: list[str] = field(default_factory=list)`
- `route_edge_keys: list[str] = field(default_factory=list)`
- `route_index: int = 0`
- `remaining_edge_ticks: int = 0`
- `route_version: int = 1`

### B2. Assign route at delivery assignment time
In Logistics assignment:
- determine `from_node`, `to_node`
- choose a perspective agent:
  - courier agent if assigned, else planner agent
- call `compute_route(...)`
- if route None:
  - fallback to direct “old ETA” delivery (v1), emit `DELIVERY_DELAYED` event, and continue
- else:
  - store route on delivery
  - set `route_index=0`
  - set `remaining_edge_ticks = edge_travel_ticks(edge0)`

### B3. Edge travel time function
Define:
- `edge_travel_ticks = int(round(base_cost * ticks_per_distance_unit))`
or use existing travel constants.
Must be deterministic and stable.

---

## 4) Implementation Slice C — Movement stepping (ambient + focus)

### C1. Ambient stepping (coarse)
Keep the heap model, but reinterpret `deliver_tick` as “next edge completion tick”:

- When an edge completes:
  - advance `route_index += 1`
  - if route_index == len(edges): delivery arrives (DELIVERED)
  - else: schedule next edge completion tick by pushing into heap again.

This preserves the due-queue model and avoids per-tick updates.

### C2. Focus stepping (fine)
In Focus Mode awake loop for couriers:
- each tick, decrement `remaining_edge_ticks` for the courier’s current delivery
- when it hits 0, advance segment as above and emit a `COURIER_EDGE_COMPLETE` event (optional)
- do not rescan deliveries; courier knows its assigned delivery via WorkforceLedger

To keep focus and ambient consistent, both should call the same helper:
- `advance_delivery_along_route(world, delivery_id, *, tick, day)`

---

## 5) Hazards, closures, reroutes

### 5.1 Closures
Add to edges:
- `closed_until_day: int = -1` (open if < current day)

When computing route:
- skip edges that are closed.

### 5.2 Mid-route closure (reroute)
If an edge becomes closed while a courier is en route:
- on next edge completion (or periodic check), detect closure on upcoming edge
- compute new route from current node to destination
- store it on delivery, reset route_index appropriately
- emit `DELIVERY_DELAYED` and/or `INCIDENT` (kind=ROUTE_BLOCKED) event

Determinism:
- reroute uses same routing config and same perspective agent id.

### 5.3 Hazard-driven incidents (optional v1 but recommended)
Without making outcomes random:
- bias incident engine sampling for delivery-related incidents by mean hazard along remaining route.
This makes hazards meaningful.

---

## 6) Memory + beliefs grounding

### 6.1 Event emission
Emit events that reflect route reality:
- `DELIVERY_DELAYED` if reroute happens
- `DELIVERY_FAILED` if a loss incident triggers
- optionally `COURIER_EDGE_COMPLETE` for focus telemetry (keep off by default)

### 6.2 Route-risk belief attribution
When an incident happens:
- include `payload["edge_key"]=...` if you can attribute it (e.g., current edge)
If not, attribute to the route as a whole (v1 acceptable).

Router can then emit:
- `route-risk:{edge_key}` crumbs
Belief formation aggregates these into stable route-risk values.

---

## 7) Save/Load integration

- Delivery route fields must serialize.
- Routing cache should NOT be serialized (derive at runtime); safe to drop.
- Ensure old snapshots lacking route fields load with defaults.

---

## 8) Tests (must-have)

Create `tests/test_courier_micropathing.py`.

### T1. Deterministic route selection
- Build a map with 2 equal-cost paths.
- Ensure compute_route returns the same path every run (tie-break by lex node_id).

### T2. Hazard avoidance affects route
- Path A shorter but high hazard; Path B slightly longer but low hazard.
- With risk_weight > 0, ensure route chooses B.

### T3. Closure forces reroute
- Compute initial route.
- Close an upcoming edge before it’s traversed.
- Advance delivery until reroute point.
- Assert route changes and delivery still completes.

### T4. Ambient stepping uses heap and does not tick-scan
- Ensure no per-tick iteration over all deliveries.
- Delivery advances via due-queue edge completions.

### T5. Focus stepping matches ambient outcomes (coarse equivalence)
- Run one courier delivery in focus mode to completion.
- Run same world in ambient only.
- End state signatures match (delivery delivered, inventories updated).

### T6. Snapshot roundtrip mid-route
- Save mid-route, load, continue.
- Same final signature.

### T7. max_expansions guard
- Construct a large map; set max_expansions small.
- compute_route returns None without hanging.

---

## 9) Codex Instructions (verbatim)

### Task 1 — Add routing module
- Create `src/dosadi/world/routing.py` with Route, RoutingConfig, compute_route
- Precompute adjacency in SurveyMap
- Implement deterministic Dijkstra/A* with stable tie-break and max_expansions guard
- Add bounded route cache (LRU)

### Task 2 — Extend delivery schema to store routes
- Add route_nodes/route_edge_keys/route_index/remaining_edge_ticks fields with safe defaults
- Ensure snapshot supports these fields (old snapshots still load)

### Task 3 — Route assignment + stepping
- On delivery assignment, compute and store route; initialize progress
- Implement `advance_delivery_along_route(...)` helper
- Update ambient delivery due-queue to schedule per-edge completion ticks
- Update focus-mode courier stepping to reuse the same helper

### Task 4 — Closures + reroute
- Add closed_until_day to edges
- Skip closed edges in routing
- Implement reroute when an upcoming edge closes mid-route (emit events)

### Task 5 — Tests
- Add `tests/test_courier_micropathing.py` implementing T1–T7

---

## 10) Definition of Done

- `pytest` passes.
- Couriers traverse multi-edge routes in ambient mode via due-queue segment ticks.
- Focus mode can run a courier mission with tick-level progress using the same logic.
- Route choices are deterministic with stable tie-breaks.
- Closures trigger deterministic reroutes and produce events.
- Save/load works mid-route and old snapshots remain loadable.

---

## 11) Next slice after this

**Local Interactions v1** (conflict/help/sabotage around deliveries and construction sites),
now that couriers actually “travel through” places and edges.
