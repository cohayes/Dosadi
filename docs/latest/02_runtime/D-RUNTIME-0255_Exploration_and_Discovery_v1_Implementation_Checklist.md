---
title: Exploration_and_Discovery_v1_Implementation_Checklist
doc_id: D-RUNTIME-0255
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-24
depends_on:
  - D-RUNTIME-0234   # Survey Map v1
  - D-RUNTIME-0236   # Expansion Planner v1
  - D-RUNTIME-0239   # Scout Missions v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0247   # Focus Mode v1
  - D-RUNTIME-0248   # Courier Micro-Pathing v1
  - D-RUNTIME-0254   # Suit Wear & Repair v1
---

# Exploration & Discovery v1 — Implementation Checklist

Branch name: `feature/exploration-discovery-v1`

Goal: make “agents scout/explore land” real by introducing:
- discoverable map nodes/edges beyond the initial known graph,
- scout missions that expand the known SurveyMap deterministically,
- discovery of resource tags (scrap fields, brine pockets, salvage, geothermal vents, etc.),
- events → memory → beliefs that shape future route choice and expansion planning.

v1 is designed to be cheap, deterministic, and compatible with ambient + focus mode.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic discovery.** Same seed + same mission plan → same discovered nodes/edges/resources.
2. **Bounded compute.** Discovery is mission-driven; no “scan the world for new land”.
3. **Save/Load safe.** Discovered map state serializes and loads identically.
4. **Feature flag default OFF.** With flag OFF, map knowledge remains static.
5. **Tested.** Determinism, bounds, snapshot roundtrip, and planner integration.

---

## 1) Concept model

### 1.1 Known vs Unknown SurveyMap
SurveyMap contains:
- a fixed “true map” (optional in v1) OR
- a deterministic “map generator” used when discovery happens.

Agents/world store **known map**:
- nodes discovered so far
- edges discovered so far
- node resource tags discovered so far

We do not need to fully materialize the whole planet; discovery can generate local neighborhoods.

### 1.2 Discovery outputs
A discovery can add:
- 1–N new nodes
- edges connecting them
- resource tags on nodes
- hazard estimates on edges (for routing/incident risk)

---

## 2) Implementation Slice A — SurveyMap upgrades for discovery

### A1. Add “unknown frontier” concept
Extend SurveyMap data model with:
- `known_nodes: set[node_id]` (or a dict of Node records)
- `known_edges: set[edge_key]`
- `frontier_nodes: set[node_id]` (known nodes that still have undiscovered adjacent slots)

If you already store full nodes/edges, then add:
- `node.discovered: bool`
- `edge.discovered: bool`

### A2. Node schema additions
Add to Node record (safe defaults):
- `resource_tags: set[str] = set()` (e.g., {"scrap_field", "salvage_cache"})
- `resource_richness: float = 0.0` (0..1, optional v1)
- `hazard: float = 0.0` (node-level, optional)

### A3. Serialization
Ensure discovered sets/flags serialize in snapshots.
Old snapshots should load as “everything currently in map is discovered”.

---

## 3) Implementation Slice B — Deterministic local map generation

Create: `src/dosadi/world/discovery.py`

**Deliverables**
- `@dataclass(slots=True) class DiscoveryConfig:`
  - `enabled: bool = False`
  - `max_new_nodes_per_day: int = 3`
  - `max_new_edges_per_day: int = 5`
  - `max_frontier_expansions_per_mission: int = 8`
  - `resource_tag_probs: dict[str,float]`  # small set
  - `hazard_range: tuple[float,float] = (0.0, 0.8)`
  - `deterministic_salt: str = "discover-v1"`

- `def hashed_unit_float(*parts: str) -> float` (reuse shared helper if already exists)

### B1. Generate neighbors deterministically
Core function:

`def expand_frontier(world, *, from_node: str, budget_nodes: int, budget_edges: int, day: int, mission_id: str) -> list[str]`

Behavior:
- using hashed draws keyed by (world_seed, salt, from_node, day, mission_id, k)
- decide number of new neighbor nodes to generate (0..N) within budgets
- assign stable new node IDs:
  - `node:{hash_prefix}` or `node:{from_node}:{k}:{day}` (must be stable, collision-safe)
- create edges from from_node to new nodes with:
  - base_cost (distance) derived deterministically
  - hazard derived deterministically within hazard_range

### B2. Resource tags
Assign resource tags deterministically:
- e.g., tags: `scrap_field`, `salvage_cache`, `brine_pocket`, `thermal_vent`
- probability weights in config
- store on node resource_tags and resource_richness

All resource assignments must be deterministic from inputs.

---

## 4) Implementation Slice C — Scout mission integration

You already have Scout Missions v1. Upgrade it so missions can produce discovery work.

### C1. Mission fields
Extend scout mission schema (safe defaults):
- `target_frontier_node_id: str | None`
- `discovery_budget_nodes: int = 2`
- `discovery_budget_edges: int = 3`
- `discovered_nodes: list[str] = []`
- `status: ...` (existing)

### C2. When discovery runs
Two viable policies:

**Policy A (recommended): daily mission progress**
- each day a mission is active, it spends one “exploration step”
- each step calls `expand_frontier(...)` with small budgets
- mission completes when budget exhausted

**Policy B: focus-mode step**
- if mission is in focus mode, discovery can happen on arrival/edge completion events
- still bounded by budgets

v1: implement Policy A; Policy B is optional.

### C3. Candidate selection for where to explore
Decision Hooks should choose a frontier node:
- based on:
  - proximity (routing cost),
  - expected resources (if any hints),
  - current shortages (materials economy needs scrap/plastics),
  - route risk and suit condition.

Deterministic tie-break:
- sort by (score, node_id).

---

## 5) Planner integration (why exploration matters)

### 5.1 Expansion Planner uses discoveries
When new nodes with resource tags are discovered:
- planner can consider building:
  - depots near scrap fields,
  - recycler/workshop near salvage,
  - route corridors to connect high-value nodes.

v1 minimal:
- add “resource score” into expansion scoring.
- prefer building a depot on/near nodes with `scrap_field` or `salvage_cache`.

### 5.2 Materials economy synergy
Resources can be modeled as passive “extraction” sites later.
v1 can just emit events and tags; production recipes can optionally include a “resource bonus”
if facility is located at such a node.

---

## 6) Events → Memory → Beliefs

Emit events:
- `DISCOVERY_NODE` (new_node_id, from_node_id, tags)
- `DISCOVERY_EDGE` (edge_key, hazard)
- `DISCOVERY_RESOURCE` (node_id, tag, richness)

Router should create crumbs:
- `resource:{tag}:{node_id}`
- `route-hazard:{edge_key}` (if hazard high)
Belief formation can form:
- “profitable route”, “danger corridor”, “rich salvage zone”

---

## 7) Save/Load requirements

Snapshot must include:
- discovery config/state
- new SurveyMap discovered nodes/edges/tags
- missions’ discovered_nodes list

Do NOT serialize caches.

---

## 8) Telemetry

Counters:
- `metrics["discovery"]["nodes_added"]`
- `metrics["discovery"]["edges_added"]`
- `metrics["discovery"]["resources_found"]`
- `metrics["discovery"]["missions_completed"]`

---

## 9) Tests (must-have)

Create `tests/test_exploration_discovery.py`.

### T1. Deterministic expansion
- same world + same mission inputs → same discovered node ids, edges, tags.

### T2. Budgets enforced
- ensure max_new_nodes_per_day / mission budgets cap changes.

### T3. Snapshot roundtrip
- save after partial discovery; load; continue; identical final signature.

### T4. Routing integrates new edges
- after discovery, compute_route can traverse newly discovered edges.

### T5. Planner uses resource tags
- discovery yields a scrap_field node; planner scoring prefers it deterministically.

### T6. Flag off = static map
- with enabled=False, scout missions do not change map.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Upgrade SurveyMap for discovery
- Add discovered flags/sets and node resource tag fields with safe defaults
- Ensure snapshot serialization (old snapshots load as fully discovered)

### Task 2 — Add discovery module
- Create `src/dosadi/world/discovery.py` with DiscoveryConfig and `expand_frontier(...)`
- Implement deterministic node/edge/tag generation with bounded budgets

### Task 3 — Integrate with Scout Missions
- Extend scout mission schema to track discovery budgets and outputs
- Implement daily mission progress that calls `expand_frontier(...)` boundedly

### Task 4 — Planner integration
- Update decision hooks to choose frontier targets deterministically
- Add resource-tag scoring to Expansion Planner

### Task 5 — Events + tests
- Emit discovery events and route through memory router
- Add `tests/test_exploration_discovery.py` implementing T1–T6

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=False: map is static.
- With enabled=True:
  - scout missions expand the known map deterministically within budgets,
  - discoveries emit events and tags,
  - routing and expansion planner can leverage new edges/nodes,
  - save/load works mid-discovery.

---

## 12) Next slice after this

**Resource Extraction Sites v1** (turn discovered tags into daily material trickles),
so exploration directly powers the construction economy and empire growth.
