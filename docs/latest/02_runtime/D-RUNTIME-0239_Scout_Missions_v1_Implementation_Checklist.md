---
title: Scout_Missions_v1_Implementation_Checklist
doc_id: D-RUNTIME-0239
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-16
depends_on:
  - D-RUNTIME-0234   # Survey_Map_v1
  - D-RUNTIME-0236   # Expansion_Planner_v1
  - D-RUNTIME-0238   # Logistics_Delivery_v1
---

# Scout Missions v1 — Implementation Checklist

Branch name: `feature/scout-missions-v1`

Goal: close the loop:
**colonists scout land → SurveyMap grows → planner proposes sites → projects stage via logistics → facilities appear**.

Designed to be handed directly to Codex.

---

## 0) Intent

We now have:
- a **SurveyMap** substrate (nodes/edges, confidence),
- an **ExpansionPlanner** that consumes the map and creates projects,
- a **Project** system + **Logistics** system that can stage and deliver.

What’s missing is the *front end* of the loop: **agents (or “parties”) exploring** and *producing map knowledge*.

This document introduces **Scout Missions** as a lightweight “macro” system that:
- selects a small number of agents as scouts,
- advances them over days (Timewarp / MacroStep),
- generates **new SurveyMap nodes/edges** (and updates confidence) deterministically from a seed,
- emits simple “findings” so the rest of the sim can react.

---

## 1) Design Principles

### 1.1 Performance and scale
- **O(#active_missions)** work per day.
- Avoid per-agent continuous pathfinding in macro mode.
- Keep mission state *compact* and deterministic for Seed Vault replay.

### 1.2 Determinism
- All map growth must be reproducible from:
  - world seed
  - mission IDs
  - day index
- No reliance on wall clock or dictionary iteration order.

### 1.3 Awake vs ambient compatibility
- In **Timewarp/MacroStep**, missions run as **ambient** processes.
- Later, a mission can be “focused” (awake agents) and swapped to micro movement.
  - v1 must not preclude this, but does not implement it.

---

## 2) Data Model

### 2.1 New enums / types
- `MissionStatus = PLANNED | EN_ROUTE | RETURNING | COMPLETE | FAILED`
- `MissionIntent = PERIMETER | RADIAL | TARGET_NODE`

### 2.2 Mission dataclass
Create `src/dosadi/world/scout_missions.py`:

```python
@dataclass(slots=True)
class ScoutMission:
    mission_id: str
    status: MissionStatus
    intent: MissionIntent

    origin_node_id: str
    current_node_id: str
    target_node_id: str | None          # optional for TARGET_NODE
    heading_deg: float | None           # optional for RADIAL
    max_days: int

    party_agent_ids: list[str]
    supplies: dict[str, float]          # water, rations, parts (coarse)
    risk_budget: float                  # “how bold are we?” 0..1

    start_day: int
    last_step_day: int
    days_elapsed: int

    discoveries: list[dict[str, object]]  # small journal; appended deterministically
    notes: dict[str, str] = field(default_factory=dict)
```

### 2.3 Ledger
```python
@dataclass(slots=True)
class ScoutMissionLedger:
    missions: dict[str, ScoutMission] = field(default_factory=dict)
    active_ids: list[str] = field(default_factory=list)

    def add(self, mission: ScoutMission) -> None: ...
    def signature(self) -> str: ...  # deterministic sha256 similar to LogisticsLedger/ProjectLedger
```

### 2.4 WorldState fields
- `world.scout_missions: ScoutMissionLedger`
- `world.scout_cfg: ScoutConfig` (optional, defaulted)
- `world.next_mission_seq: int` (monotonic, for deterministic IDs)

---

## 3) ScoutConfig

Create `src/dosadi/runtime/scouting_config.py`:

```python
@dataclass(slots=True)
class ScoutConfig:
    max_active_missions: int = 2
    party_size: int = 2
    max_days_per_mission: int = 5

    # map growth knobs
    new_node_chance: float = 0.35
    new_edge_chance: float = 0.60
    confidence_gain_on_revisit: float = 0.05
    confidence_new_node: float = 0.55
    confidence_cap: float = 0.95

    # risk knobs
    base_fail_chance: float = 0.02
    hazard_fail_multiplier: float = 2.0

    # selection knobs
    allow_reuse_agent_days: int = 2  # cooldown on re-assigning a scout
```

---

## 4) Mission Lifecycle

### 4.1 Mission creation: `maybe_create_scout_missions(world, cfg)`
Location: `src/dosadi/runtime/scouting.py`

Inputs:
- SurveyMap present (`world.survey_map`).
- Origin node:
  - prefer `loc:well-core` if present (matches expansion planner convention).
- Party selection:
  - v1: pick the first N available agents by sorted agent_id
  - respect cooldown via `agent.last_scout_day` if present

Creates missions until `max_active_missions` reached:
- mission_id = `scout:{day}:{seq}` (or sha-based)
- intent:
  - v1 choose `RADIAL` with a deterministic heading based on mission_id hash
- set `status=EN_ROUTE`, `current_node_id=origin`, `max_days=max_days_per_mission`

### 4.2 Daily stepping: `step_scout_missions_for_day(world, day, cfg)`
For each active mission:
- if `day <= mission.last_step_day`: skip (idempotent)
- increment `days_elapsed`
- resolve one “travel step”:
  - choose next_node_id:
    - if an edge exists from current node in heading direction (later), follow it
    - else, probabilistically “discover” a new node and edge
- update SurveyMap:
  - **new node**: create `SurveyNode(node_id=loc:auto:{hash}, confidence=confidence_new_node, …)`
  - **new edge**: connect `current_node_id <-> new_node_id`, distance_m deterministic (e.g., 50..500m)
  - **revisit**: bump confidence toward cap
- append a `discoveries` record:
  - `{"day": day, "kind": "NEW_NODE", "node_id": "...", "confidence": 0.55}`
- resolve failure:
  - probability = base_fail_chance * (1 + hazard_fail_multiplier * local_hazard)
  - on failure: `status=FAILED`, remove from active_ids
- resolve completion:
  - if `days_elapsed >= max_days`: set `status=COMPLETE` and remove

**Important:** Use a local RNG derived from `(world.seed, mission_id, day)` so stepping is reproducible even if mission processing order changes.

### 4.3 Mission effects on agents (minimal v1)
- Mark assigned agents with `agent.is_on_mission = True` and clear on completion/failure.
- Do **not** simulate per-tick physiology; this remains macro-level.

---

## 5) SurveyMap Update Rules

When adding nodes/edges:
- node IDs deterministic and collision-resistant (`sha256(mission_id + ":" + day)`).
- never overwrite an existing node; if collision, derive a second hash.
- edge key follows `edge_key(a,b)` conventions.

Confidence:
- New node starts at `confidence_new_node`.
- Revisit increments by `confidence_gain_on_revisit` up to `confidence_cap`.

---

## 6) Integration Points

### 6.1 Timewarp / MacroStep (daily)
Hook order recommendation per simulated day:
1. `step_scout_missions_for_day(...)`
2. `update_facilities_for_day(...)`
3. `projects.step_projects_for_day(...)`
4. `logistics.process_logistics_for_day(...)`
5. `expansion_planner.maybe_plan(...)` — now benefits from new nodes

### 6.2 Founding wakeup “Gather info” goal
You already have an interior scout work detail hook (SCOUT_INTERIOR). This system is parallel:
- Interior scouting can later influence “internal” map confidence.
- Overland missions grow the external map.

No coupling required in v1; just ensure both can write to `world.survey_map`.

---

## 7) Testing Contract

Add tests under `tests/`:

### 7.1 Deterministic map growth
- Given:
  - `world = WorldState(seed=123)`
  - initial survey with only `loc:well-core`
  - cfg with `max_active_missions=1`, `max_days_per_mission=3`, `new_node_chance=1.0`
- Run 3 days of stepping.
- Assert:
  - exactly 3 new nodes exist
  - exactly 3 edges connect them sequentially from origin
  - `world.survey_map.signature()` stable across two runs.

### 7.2 Mission lifecycle
- Ensure mission completes after `max_days_per_mission`
- Ensure `active_ids` shrinks accordingly
- Ensure agents get `is_on_mission` toggled back to False.

### 7.3 Failure path
- Set `base_fail_chance=1.0` and assert mission fails on first day and is removed.

### 7.4 Integration smoke (macrostep)
- With:
  - scouting enabled
  - expansion planner enabled
- Run N days and assert at least one project is proposed at a discovered node.

---

## 8) Telemetry (optional)

Emit 1–2 events:
- `SCOUT_MISSION_CREATED`
- `SCOUT_DISCOVERY` (node/edge)
- `SCOUT_MISSION_FAILED` / `SCOUT_MISSION_COMPLETE`

---

## 9) Codex Implementation Instructions (verbatim)

**Branch name:** `feature/scout-missions-v1`

1) **Create files**
- `src/dosadi/world/scout_missions.py`
  - `MissionStatus`, `MissionIntent`, `ScoutMission`, `ScoutMissionLedger`
  - `ensure_scout_missions(world)` helper
  - `signature()` using canonical JSON + sha256 (mirror LogisticsLedger approach)
- `src/dosadi/runtime/scouting_config.py`
  - `ScoutConfig`
- `src/dosadi/runtime/scouting.py`
  - `maybe_create_scout_missions(world, cfg)`
  - `step_scout_missions_for_day(world, day, cfg)`
  - deterministic RNG helper: `rng_for(mission_id, day, world_seed)`

2) **Wire into macrostep / timewarp**
- Find the daily stepping function (the one currently calling facility/projects/logistics/planner).
- Insert:
  - `maybe_create_scout_missions(...)` (once per day)
  - `step_scout_missions_for_day(...)` (once per day, before planning)

3) **WorldState initialization**
- In `WorldState.__init__` or `ensure_*` helpers:
  - initialize `world.scout_missions`, `world.scout_cfg` if missing
  - initialize `world.next_mission_seq` if missing

4) **Tests**
- Add:
  - `tests/test_scout_missions_determinism.py`
  - `tests/test_scout_missions_lifecycle.py`
  - `tests/test_scout_missions_integration_smoke.py`
- Ensure tests do not rely on dict iteration: sort keys when needed.

5) **Definition of done**
- `pytest -q` passes.
- Running a short timewarp (e.g., 10 days) shows:
  - new survey nodes
  - planner proposals at discovered nodes
  - deterministic replay for same seed.

---

## 10) Next Likely Slice

After scouting exists, the next “feels alive” step is:
- **Construction workforce & staffing v1** (agents assigned to projects and facilities), or
- **Richer resource production loops v2**, so logistics doesn’t stall.
