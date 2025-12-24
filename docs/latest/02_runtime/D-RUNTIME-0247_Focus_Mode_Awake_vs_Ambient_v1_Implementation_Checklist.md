---
title: Focus_Mode_Awake_vs_Ambient_v1_Implementation_Checklist
doc_id: D-RUNTIME-0247
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-24
depends_on:
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0234   # Survey Map v1
  - D-RUNTIME-0240   # Construction Workforce Staffing v1
  - D-RUNTIME-0243   # Event → Memory Router v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0246   # Agent Courier Logistics v1
---

# Focus Mode (Awake vs Ambient) v1 — Implementation Checklist

Branch name: `feature/focus-mode-v1`

Goal: enable a “kaleidoscopic” experience *selectively* by running **high-fidelity ticks**
for a small subset of agents and a bounded region/mission, while the rest of the world runs in
**ambient/macro** mode.

This is the bridge between:
- large-scale empire evolution (macro-step)
- and moment-to-moment lived experience (awake agents)

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Determinism preserved.** Same seed + same focus plan → same outcomes.
2. **Bounded cost.** Awake set is capped; ambient world cannot accidentally fall into per-tick scans.
3. **Time consistency.** The world has one canonical timebase; focus mode must not “desync days”.
4. **Feature flag + safe fallback.** If disabled, simulation behaves exactly as today.
5. **Testable.** Focus sessions can be run headless in tests (no UI required).

---

## 1) Concept model

### 1.1 Two simulation granularities
- **Ambient**: macro-step, mostly daily updates (projects/logistics/incidents/events/beliefs/decisions)
- **Awake**: tick-level loop (movement/action resolution, immediate consequences, rich episodes)

v1 does *not* require full physical pathing. It just provides the scaffolding so we can zoom in later.

### 1.2 FocusSession
A FocusSession is a bounded window:
- a **focus target** (ward, map node, project, delivery, or a courier mission)
- a **time window** (e.g., 10,000 ticks, or “until courier delivers”)
- an **awake cohort** (agents included in the high-fidelity loop)
- a stable deterministic **focus seed salt** (affects only ordering, not RNG streams)

Focus session outputs:
- events (WorldEventLog)
- crumbs/episodes
- updated agent state for those awake agents
- world-level state changes (deliveries/projects/facility ops) applied through existing systems

---

## 2) Implementation Slice A — Data structures + config

### A1. Create module: `src/dosadi/runtime/focus_mode.py`

**Deliverables**
- `@dataclass(slots=True) class FocusConfig:`
  - `enabled: bool = False`
  - `max_awake_agents: int = 40`
  - `max_focus_ticks: int = 50_000`
  - `default_focus_ticks: int = 10_000`
  - `awake_action_budget_per_tick: int = 3`  # safeguard (no infinite loops)
  - `ambient_step_granularity_ticks: int = 1_000`  # during focus, how often ambient substeps run (see section 4)
  - `emit_focus_events: bool = True`

- `class FocusTargetKind(Enum): WARD, NODE, PROJECT, DELIVERY, COURIER_MISSION`

- `@dataclass(slots=True) class FocusTarget:`
  - `kind: FocusTargetKind`
  - `id: str`                  # e.g. "ward:12", "node:7", "project:abc", "delivery:xyz"
  - `radius: int = 0`          # optional (nodes within N hops)

- `@dataclass(slots=True) class FocusSession:`
  - `session_id: str`
  - `start_tick: int`
  - `end_tick: int`
  - `target: FocusTarget`
  - `awake_agent_ids: list[str]`
  - `seed_salt: str = "focus-v1"`
  - `done_reason: str = ""`

- `@dataclass(slots=True) class FocusState:`
  - `active: bool = False`
  - `session: FocusSession | None = None`
  - `last_tick: int = 0`
  - `last_ambient_step_tick: int = 0`

### A2. World integration
- Add `world.focus_cfg: FocusConfig`
- Add `world.focus_state: FocusState`
- Ensure snapshot includes focus state so save/load mid-focus is valid.

---

## 3) Implementation Slice B — Cohort selection

### B1. Deterministic selection function
Add in `focus_mode.py`:

`def select_awake_agents(world, target: FocusTarget, *, day: int, max_n: int) -> list[str]`

Rules by target kind (v1):
- DELIVERY / COURIER_MISSION:
  - include assigned courier agent (from delivery.assigned_carrier_id if it’s an agent)
  - include project workers who requested that delivery (if deterministically findable)
- PROJECT:
  - include currently assigned workforce agents on that project
- WARD:
  - include top-N agents currently located in ward (if location exists)
- NODE:
  - include agents at that node (if location exists)

Tie-breakers:
- sort agent_id ascending
- cut to `max_n`

If location is not yet meaningful:
- use workforce assignments as the primary selector in v1 (that’s okay).

### B2. Awake tag (optional)
- `agent.is_awake: bool` or `agent.sim_mode = "AWAKE"|"AMBIENT"`
Must not be used for global hot-path scans.

---

## 4) Implementation Slice C — Time synchronization strategy

### Recommended v1 approach: Interleaved ambient stepping
During a focus session:
- run awake tick loop at full fidelity
- every `ambient_step_granularity_ticks` (e.g. 1000 ticks):
  - run a *small* ambient step for the whole world that is safe and bounded

**Deliverables**
- `def run_focus_session(world, session: FocusSession) -> None`
  - while tick < end_tick and not done:
    - run awake agents for 1 tick (bounded)
    - if tick - last_ambient_step_tick >= ambient_step_granularity_ticks:
      - run `run_ambient_substep(world, tick)`
  - at end, mark session done and clear awake flags.

### Ambient substep definition (v1)
Ambient substep must be safe at arbitrary tick boundaries:
- process due deliveries up to `current_tick` (heap)
- process project stage transitions that depend on deliveries (bounded)
- (optional) facility reactivation checks keyed by day/tick
- DO NOT run full “daily belief formation” on substeps — keep daily cadence (see section 5)

Implement:
- `def run_ambient_substep(world, *, tick: int) -> None`
  - uses existing due-queues and local deltas
  - never scans all agents

---

## 5) Daily cadence integration during focus

Focus sessions cross day boundaries; we must run daily systems exactly once per day.

**Deliverables**
- `def tick_to_day(world, tick:int) -> int`
- Detect day transitions inside `run_focus_session`:
  - when `day` increments, call the daily pipeline (same as macro-step):
    1) projects/logistics/facilities daily updates (if any)
    2) phase engine
    3) incident engine
    4) event→memory router
    5) belief formation
    6) decision hooks

---

## 6) Awakened action model (v1 minimal)

We don’t need full movement yet. We need just enough to:
- generate immediate events/episodes,
- allow courier deliveries to “feel like they happen” in focus.

### Minimal v1 awake loop
For each awake agent per tick:
- if agent has an active assignment:
  - LOGISTICS_COURIER: increment a `progress` counter toward delivery completion
  - PROJECT_WORK: increment project progress (optional)
- if progress completes:
  - emit an event (DELIVERY_DELIVERED or PROJECT_STAGE_DONE)
  - apply outcome through existing logistics/project APIs (no bespoke world mutation)

Progress storage:
- in assignment notes: `notes["progress_ticks"]`, `notes["target_ticks"]`
- or on delivery itself (preferred if delivery already stores transit time)

Keep deterministic:
- `target_ticks` computed from map distance or fixed constant
- `progress += 1` per tick

---

## 7) Telemetry + debug hooks

Add small focus telemetry:
- `world.metrics["focus"]["sessions_started"]`
- `world.metrics["focus"]["awake_agent_ticks"]`
- `world.metrics["focus"]["ambient_substeps"]`
- `world.metrics["focus"]["day_transitions"]`

If `emit_focus_events=True`, append to WorldEventLog:
- `FOCUS_SESSION_START`
- `FOCUS_SESSION_END`
- `FOCUS_DAY_TRANSITION`

---

## 8) Save/Load requirements

Snapshot must include:
- focus_cfg
- focus_state (including active session and progress counters)

Roundtrip:
- saving mid-focus and reloading continues identically.
- cursor-driven routers (event→memory) must not duplicate.

---

## 9) Tests (must-have)

Create `tests/test_focus_mode.py`.

### T1. Focus session determinism
- World with one courier delivery assigned to agent.
- Run focus for N ticks twice with same seed.
- Compare world signature + agent signature.

### T2. Awake cohort selection determinism
- Same target/world → same ordered awake cohort list.

### T3. Ambient substep safety
- Ensure ambient substep processes due deliveries without scanning all agents.
- Use counters/mocks to assert no full-agent iteration is invoked.

### T4. Day transition pipeline correctness
- Focus spanning > 1 day triggers daily pipeline exactly once per day.
- Compare with macro-step run for those days (coarse equivalence).

### T5. Snapshot mid-focus
- Save at tick T, load, continue to end.
- Final signatures match uninterrupted run.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add focus mode module + world state
- Create `src/dosadi/runtime/focus_mode.py` with FocusConfig/Target/Session/State
- Add `world.focus_cfg` and `world.focus_state` and snapshot support

### Task 2 — Implement cohort selection
- Implement `select_awake_agents(world, target, day, max_n)` deterministically
- Add optional awake flags for agents (no global scans)

### Task 3 — Implement focus session runner
- Implement `run_focus_session(world, session)`
- Interleave awake ticks with ambient substeps (every N ticks)
- Detect and process day transitions with the daily pipeline

### Task 4 — Minimal awake action loop
- Implement progress-based logic for LOGISTICS_COURIER (and optionally project work)
- Emit events through WorldEventLog; apply outcomes through existing APIs

### Task 5 — Telemetry + tests
- Add focus telemetry counters and optional focus events
- Create `tests/test_focus_mode.py` implementing T1–T5

---

## 11) Definition of Done

- `pytest` passes.
- With focus disabled: no behavior change.
- With focus enabled: courier-focused session runs high-fidelity ticks, while ambient world continues safely.
- Day transitions occur correctly and run daily pipeline exactly once per day.
- Save/load mid-focus is deterministic.
- Performance is bounded by awake cohort size and ambient substep granularity.

---

## 12) Next slices after this

1. Courier micro-pathing v1 (nodes/edges, hazards, reroutes)
2. Local interactions (queueing, conflicts, assistance, sabotage)
3. Ward-level “spotlight” UI for debugging and storytelling
