---
title: Corridor_Improvements_v1_Implementation_Checklist
doc_id: D-RUNTIME-0267
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0234   # Survey Map v1
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0259   # Expansion Planner v2
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
---

# Corridor Improvements v1 — Implementation Checklist

Branch name: `feature/corridor-improvements-v1`

Goal: let the empire *reshape the map* by building corridor-level infrastructure that reduces:
- travel time,
- suit wear / hazard exposure (A1),
- corridor risk / predation success (A2),
and increases:
- throughput,
- stability of expansion.

This should plug into the existing construction pipeline and planner, and it should be explainable via telemetry.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same state → same improvement choices and effects.
2. **Bounded.** Planner considers TopK candidate corridors; no O(E) daily scans.
3. **Composable.** Improvements should affect routing, wear, risk, and enforcement efficiency.
4. **Upgradeable.** Corridors can be improved in levels (0→1→2) rather than one-off.
5. **Persisted.** Corridor improvements are map-state; they must save/load and belong in seed vault.
6. **Tested.** Effects apply correctly and persist.

---

## 1) Concept model

A “corridor” is an edge between nodes/wards. Improvements are stored per edge_key.

Improvement levels:
- Level 0: unimproved
- Level 1: graded path / marker posts
- Level 2: hardened path + waystation + shade/shelter
- Level 3: fortified corridor + checkpoint infrastructure (optional future)

v1 implements levels 0–2.

Each level confers multipliers:
- travel_time_multiplier
- suit_wear_multiplier
- hazard_multiplier
- predation_multiplier (reduces theft success or increases interdiction odds)
- maintenance_cost_per_day (optional)

---

## 2) Data structures

Create `src/dosadi/world/corridor_infrastructure.py`

### 2.1 Config
- `@dataclass(slots=True) class CorridorInfraConfig:`
  - `enabled: bool = False`
  - `max_candidates_per_day: int = 25`
  - `max_projects_spawned_per_day: int = 2`
  - `upgrade_cooldown_days: int = 14`
  - `deterministic_salt: str = "corridor-infra-v1"`

### 2.2 Edge state
- `@dataclass(slots=True) class CorridorInfraEdge:`
  - `edge_key: str`
  - `level: int = 0`
  - `last_upgrade_day: int = -1`
  - `tags: set[str] = field(default_factory=set)`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.infra_cfg`
- `world.infra_edges: dict[str, CorridorInfraEdge]`

Snapshot + seed vault include these (map-state).

---

## 3) Recipes / project templates

We represent corridor upgrades as Construction Projects (pipeline v2), with a new project kind:
- `CORRIDOR_UPGRADE`

Add a project spec payload:
- `edge_key`
- `from_level`
- `to_level`
- `benefits` (optional for telemetry)

Define material recipes per level:
- L0→L1: markers, basic grading
  - inputs: SCRAP_METAL, FASTENERS, FABRIC (markers)
- L1→L2: hardening + waystation supplies
  - inputs: SCRAP_METAL, SEALANT, FILTER_MEDIA, GASKETS (shelter sealing)
Optionally labor-days.

Implement a registry:
- `corridor_upgrade_recipe(from_level,to_level) -> dict[material,qty]`

Keep deterministic, simple, and easy to tune.

---

## 4) Applying effects

Where effects must be applied:

### 4.1 Routing / travel time (0248, 0238)
- edge traversal time = base_time * travel_time_multiplier(level)

### 4.2 Suit wear / hazard (0254, 0255)
- suit wear increments multiplied by suit_wear_multiplier(level)
- hazard prior reduced by hazard_multiplier(level)

### 4.3 Predation / risk (0261, 0264, 0265)
- corridor risk update can include infra as a “protective prior”:
  - effective_risk = risk * predation_multiplier(level)
OR
  - interference severity reduced by predation_multiplier(level)
- enforcement interdiction can be boosted if corridor has level>=2:
  - checkpoint effectiveness increases (optional v1)

Pick one primary integration in v1:
- **Recommended:** apply to travel time + suit wear + interference severity (3 points of leverage).

---

## 5) Planner integration (bounded)

Add a daily corridor-improvement planner:
- `run_corridor_improvement_planner(world, day)`

Candidate generation (bounded):
- take TopK risky corridors from risk ledger
- take TopK high-traffic corridors (if available)
- take edges on routes to high-priority construction/extraction sites
- take contested edges (faction activity) (0266)

Score each candidate:
- `score = w_risk*risk + w_traffic*traffic + w_value*value - w_level*level`
And include A1 pressure:
- `+ w_wear*suit_wear_observed`

Choose up to `max_projects_spawned_per_day`, respecting cooldown and if project not already active.

Spawn a construction project:
- project kind CORRIDOR_UPGRADE, payload edge_key, to_level=level+1.

All deterministic:
- sort by (score desc, edge_key asc).

---

## 6) Construction pipeline integration

Add a new stage type:
- `BUILD_CORRIDOR_UPGRADE`

Upon completion:
- update `world.infra_edges[edge_key].level = to_level`
- set last_upgrade_day
- emit event `CORRIDOR_UPGRADE_DONE`

If project fails/canceled, no change.

---

## 7) Telemetry + cockpit

Metrics:
- `metrics["infra"]["edges_upgraded_total"]`
- `metrics["infra"]["projects_started"]`
- `metrics["infra"]["projects_done"]`
- TopK:
  - `infra.top_edges` by level and score

Cockpit panel:
- Upgraded corridors (edge_key, level, effects summary)
- Proposed upgrades (queued projects)
- Overlay with risk (edge risk vs level)

Events:
- `CORRIDOR_UPGRADE_PLANNED`
- `CORRIDOR_UPGRADE_STARTED`
- `CORRIDOR_UPGRADE_DONE`

---

## 8) Persistence / seed vault

Because corridor infra is map-state and you want persisted seeds:
- include infra_edges in seed vault persisted layer (0231)
- export stable JSON:
  - `seeds/<name>/corridor_infra.json` sorted by edge_key

---

## 9) Tests (must-have)

Create `tests/test_corridor_improvements_v1.py`.

### T1. Determinism
- same risk/traffic → same chosen upgrade projects.

### T2. Effects apply
- after upgrade, traversal time reduced; suit wear reduced.

### T3. Interference mitigation
- same theft attempt on upgraded edge yields reduced severity (deterministic).

### T4. Cooldown and duplicate protection
- cannot upgrade same edge again within cooldown; no duplicate projects.

### T5. Persistence
- snapshot roundtrip preserves infra_edges.
- seed vault export stable ordering.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add corridor infrastructure state
- Create `src/dosadi/world/corridor_infrastructure.py` with config + CorridorInfraEdge
- Add world.infra_cfg/world.infra_edges to snapshots and seed vault persisted layer
- Add stable export `corridor_infra.json`

### Task 2 — Add corridor upgrade project kind + recipes
- Extend construction pipeline with CORRIDOR_UPGRADE kind and build stage
- Define deterministic material recipes for L0→L1 and L1→L2

### Task 3 — Apply corridor level effects
- Routing/travel time uses travel_time_multiplier(level)
- Suit wear/hazard uses suit_wear_multiplier(level)
- Interference severity uses predation_multiplier(level)

### Task 4 — Planner integration (bounded)
- Build TopK candidate edges from risk/traffic/value
- Score deterministically and spawn up to max projects per day with cooldown and no duplicates

### Task 5 — Telemetry + tests
- Add cockpit panel + metrics/events
- Add `tests/test_corridor_improvements_v1.py` (T1–T5)

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=True:
  - planner spawns corridor upgrade projects deterministically,
  - upgrades reduce travel time and suit wear and weaken predation outcomes,
  - corridor levels persist through save/load and seed vault,
  - cockpit shows upgraded edges and impact.

---

## 12) Next slice after this trunk step

**Tech Ladder v1** — research unlocks new recipes, suits, and facilities.
Now improvements + factions + enforcement can evolve over centuries.
