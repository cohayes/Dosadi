---
title: Survey_Map_v1_Implementation_Checklist
doc_id: D-RUNTIME-0234
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-15
depends_on:
  - D-RUNTIME-0231   # Save/Load + Seed Vault + Deterministic Replay
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0233   # Evolve Seeds Harness
  - D-AGENT-0020     # Agent model (goals, actions)
---

# Survey Map v1 — Implementation Checklist

Branch name: `feature/survey-map-v1`

Goal: create the first durable bridge from “wakeup survival” → “empire expansion” by introducing a shared, persistent **SurveyMap** that scouts can incrementally discover and update. This enables later site selection, construction projects, and territorial politics.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **SurveyMap is deterministic.** Same seed + same scouting schedule → same SurveyMap hash.
2. **SurveyMap is save/load compatible.** It must be included in WorldSnapshot v1 (or v1.1) and seed vault.
3. **SurveyMap grows monotonically** (v1): discoveries only add/strengthen knowledge, never delete it.
4. **Minimal scope.** v1 is about discovery + storage + scoring hooks; not full terrain generation or pathfinding overhaul.
5. **Cheap updates.** Scout completion should update the map in O(discovered_items) time.

---

## 1) Concept model (v1)

SurveyMap is a world-level artifact containing:
- **Nodes**: interesting locations (e.g., “ridge”, “pit”, “ruin”, “wadi”, “well_outflow”)
- **Edges**: traversable connections between nodes (with distances / travel costs)
- **Annotations**: hazards, resources, and confidence/recency of knowledge

v1 assumes a graph-ish world (compatible with Wakeup Prime / facility graphs). Later, it can be extended to tiles.

---

## 2) Implementation Slice A — Add SurveyMap structures

### A1. Create module: `src/dosadi/world/survey_map.py` (or `dosadi/runtime/survey_map.py`)
**Deliverables**
- `@dataclass(slots=True) class SurveyNode:`
  - `node_id: str`
  - `kind: str`  # ridge, ruin, canyon, depot_site, etc.
  - `ward_id: str | None`  # optional, if tied to wards
  - `tags: tuple[str, ...] = ()`
  - `hazard: float = 0.0`  # 0..1
  - `water: float = 0.0`   # 0..1 (or relative potential)
  - `confidence: float = 0.0`  # 0..1
  - `last_seen_tick: int = 0`

- `@dataclass(slots=True) class SurveyEdge:`
  - `a: str`
  - `b: str`
  - `distance_m: float`
  - `travel_cost: float`  # derived or stored
  - `hazard: float = 0.0`
  - `confidence: float = 0.0`
  - `last_seen_tick: int = 0`

- `@dataclass(slots=True) class SurveyMap:`
  - `nodes: dict[str, SurveyNode]`
  - `edges: dict[str, SurveyEdge]`  # key like "a|b" canonical
  - `schema_version: str = "survey_map_v1"`
  - `def upsert_node(self, node: SurveyNode) -> None`
  - `def upsert_edge(self, edge: SurveyEdge) -> None`
  - `def merge_observation(self, obs: dict, *, tick: int) -> None`  # from scout result
  - `def signature(self) -> str`  # deterministic hash of canonical JSON

**Canonical edge key rule**
- `edge_key(a,b) = f"{min(a,b)}|{max(a,b)}"`

### A2. Confidence update rule (v1 monotonic)
When new observation arrives:
- `confidence = min(1.0, confidence + delta)` (e.g., +0.1 per confirm)
- `last_seen_tick = tick`
- hazards/resources can be averaged by confidence weight (or max) — pick a deterministic rule.

Keep it simple and deterministic.

---

## 3) Implementation Slice B — Connect scouting actions to SurveyMap updates

### B1. Identify where scouting actions resolve
Hook at action completion for:
- `SCOUT_INTERIOR`
- `SCOUT_EXTERIOR`
(Whatever your current action taxonomy uses.)

**Deliverables**
- A “scout result” payload that includes discovered nodes/edges:
  - `discovered_nodes: list[dict]`
  - `discovered_edges: list[dict]`
- On completion, call `world.survey_map.merge_observation(...)`

### B2. Deterministic discovery generation (v1)
Discovery can be:
- scenario-provided (preferred): a fixed “world graph” and scout reveals parts
- or RNG-driven but deterministic: use `world.rng` and stable ordering

**Rule:** given same agent + same target area + same tick, discovery must be deterministic.

---

## 4) Implementation Slice C — Save/Load support

### C1. Add SurveyMap to WorldState
- Add `world.survey_map: SurveyMap` (initialized empty in scenario init)
- Ensure it is included in snapshot save/load:
  - `survey_map` serialized under world dict

### C2. Update snapshot tests
- Snapshot roundtrip should preserve `survey_map.signature()` exactly.

---

## 5) Implementation Slice D — Site scoring hook (pure function)

### D1. Create module: `src/dosadi/world/site_scoring.py`
**Deliverables**
- `@dataclass(slots=True) class SiteScoreConfig:`
  - weights: hazard, distance, water, strategic tags
- `def score_site(node: SurveyNode, *, origin_node_id: str | None, survey: SurveyMap, cfg: SiteScoreConfig) -> float`

**Rules**
- Must be deterministic and side-effect free
- Must not require pathfinding in v1 (use direct edge distance if connected, else penalize)

This function becomes the input to later “construction project proposals”.

---

## 6) Tests (must-have)

Create `tests/test_survey_map.py`.

### T1. Deterministic merge
- Given the same observation sequence, map signature is identical.

### T2. Monotonic growth
- Node/edge sets only grow, confidence increases, last_seen_tick moves forward.

### T3. Snapshot roundtrip
- Build a map, snapshot, load, confirm signature unchanged.

### T4. Integration: scout action writes map
- Run a tiny scenario, execute a scout action, verify new nodes/edges exist.

---

## 7) “Codex Instructions” (verbatim)

### Task 1 — Add SurveyMap structures
- Create `src/dosadi/world/survey_map.py`
- Implement `SurveyNode`, `SurveyEdge`, `SurveyMap` with deterministic `signature()`
- Use canonical edge keys and stable JSON hashing

### Task 2 — Hook scouting actions
- Identify action completion for scout actions
- Emit deterministic discovery payloads
- Update `world.survey_map` via `merge_observation`

### Task 3 — Save/load integration
- Add `survey_map` to world state
- Include it in snapshot serialization/deserialization
- Add a snapshot roundtrip test for survey map

### Task 4 — Add site scoring hook
- Create `src/dosadi/world/site_scoring.py` with a pure `score_site(...)`

### Task 5 — Add tests
- Create `tests/test_survey_map.py` with deterministic merge + monotonic + snapshot + integration tests

---

## 8) Definition of Done

- `pytest` passes.
- Scouting updates `world.survey_map` deterministically.
- SurveyMap survives save/load with identical signature.
- `score_site` exists and is deterministic.
- The evolve harness can run and accumulate survey map state over time (even if minimal).

---

## 9) Next branch after this

`feature/construction-projects-v1`:
- proposed → approved → staged → building → complete
- consumes stock + labor time
- creates a new facility node
