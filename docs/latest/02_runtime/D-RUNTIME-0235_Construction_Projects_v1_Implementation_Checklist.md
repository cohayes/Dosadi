---
title: Construction_Projects_v1_Implementation_Checklist
doc_id: D-RUNTIME-0235
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-15
depends_on:
  - D-RUNTIME-0231   # Save/Load + Seed Vault + Deterministic Replay
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0233   # Evolve Seeds Harness
  - D-RUNTIME-0234   # Survey Map v1
  - D-AGENT-0020     # Agent model (goals, actions)
---

# Construction Projects v1 — Implementation Checklist

Branch name: `feature/construction-projects-v1`

Goal: turn discovered sites into durable expansion by adding a minimal **construction project pipeline**:
**propose → approve → stage → build → complete**, consuming stock + labor time and creating a new facility/node.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic projects.** Given same inputs and seed, project progression and completion are deterministic.
2. **Save/Load compatible.** Projects must serialize into snapshots and resume without divergence.
3. **No negative resources.** Stock consumption is checked and enforced; never allow negative ledgers.
4. **Bounded computation.** No global scanning loops; projects are scheduled via due-tick / timing wheel patterns.
5. **Minimal v1 scope.** Build a stub facility node at completion; full facility behavior can come later.

---

## 1) Concept model (v1)

A ConstructionProject is a world-level entity that:
- has a **target site** (SurveyNode id)
- has **requirements** (materials + labor-hours)
- progresses via **work contributions** (agents assigned to project)
- produces an **output** (a facility/node in the world graph)

Projects are not “magic builds”: they require:
- approval (institutional decision)
- staging (materials gathered / delivered)
- building (labor applied over time)

---

## 2) Implementation Slice A — Data structures

### A1. Create module: `src/dosadi/world/construction.py`
**Deliverables**
- `class ProjectStatus(Enum): PROPOSED, APPROVED, STAGED, BUILDING, COMPLETE, CANCELED`
- `@dataclass(slots=True) class ProjectCost:`
  - `materials: dict[str, float]`  # e.g., {"polymer": 50, "metal": 20}
  - `labor_hours: float`
- `@dataclass(slots=True) class ConstructionProject:`
  - `project_id: str`
  - `site_node_id: str`
  - `kind: str`  # e.g., "outpost", "pump_station", "workshop"
  - `status: ProjectStatus`
  - `created_tick: int`
  - `last_tick: int`
  - `cost: ProjectCost`
  - `materials_delivered: dict[str, float]`
  - `labor_applied_hours: float`
  - `assigned_agents: list[str]`  # agent ids
  - `deadline_tick: int | None = None`  # optional
  - `notes: dict[str, str] = field(default_factory=dict)`

- `@dataclass(slots=True) class ProjectLedger:`
  - `projects: dict[str, ConstructionProject]`
  - `def add_project(self, p: ConstructionProject) -> None`
  - `def get(self, project_id: str) -> ConstructionProject`
  - `def signature(self) -> str`  # deterministic hash

### A2. World integration
- Add `world.projects: ProjectLedger`
- Ensure it is initialized in scenario init / world init.

---

## 3) Implementation Slice B — State machine transitions

### B1. Transition rules (v1 deterministic)
- **PROPOSED → APPROVED**
  - Triggered by a policy hook / council decision (can be manual for v1)
- **APPROVED → STAGED**
  - When required materials are available in stock and reserved (or delivered to site)
- **STAGED → BUILDING**
  - When at least one agent is assigned and can work
- **BUILDING → COMPLETE**
  - When `labor_applied_hours >= cost.labor_hours` AND delivered materials meet requirement
- Any state → **CANCELED**
  - optional, manual; return reserved materials

### B2. Reservation vs delivery (pick one for v1)
To keep v1 simple, choose **reservation**:
- On staging, deduct materials immediately from global stocks (or reserve bucket)
- Track `materials_delivered` as “reserved”
- No logistics simulation required yet

Later you can replace reservation with actual hauling/delivery.

---

## 4) Implementation Slice C — Work contributions

### C1. Add a project work action
Hook a new action/work detail:
- `WORK_ON_PROJECT(project_id)`
- Each work interval contributes:
  - `labor_delta_hours = agent_skill_factor * interval_hours`
- Keep deterministic: compute skill_factor from fixed agent stats; no randomness.

### C2. Scheduling
Avoid scanning all projects each tick:
- Maintain `next_project_tick` per project or per active project list.
- Process active projects on a cadence:
  - tick-mode: every 100–600 ticks
  - macro-step: integrate labor by elapsed days for assigned agents

---

## 5) Implementation Slice D — Facility creation output (stub)

### D1. Minimal facility stub at completion
On COMPLETE:
- Create a new world node / facility record associated with `site_node_id`
- Add it to:
  - world topology graph OR facilities registry (whatever exists now)
- Record:
  - facility_id, kind, location node

The facility can be inert initially; the important thing is that it exists and persists.

---

## 6) Implementation Slice E — MacroStep integration

In `step_day` / macro-step mode:
- For BUILDING projects:
  - compute `elapsed_hours = days * 24`
  - apply labor from assigned agents as aggregated contributions
  - advance status transitions deterministically
- For STAGED projects:
  - can transition to BUILDING if assigned_agents nonempty

This allows projects to complete during fast-forward runs, enabling “empire growth.”

---

## 7) Save/Load integration

### S1. Snapshot support
- Serialize:
  - ProjectLedger
  - each ConstructionProject fields (status, costs, applied labor, assigned agents)
- Restore with identical ordering.
- Add to snapshot roundtrip and replay tests.

---

## 8) Tests (must-have)

Create `tests/test_construction_projects.py`.

### T1. State machine progression
- Create project with cost, approve, stage, assign, apply labor, complete.
- Assert correct status sequence and final facility created.

### T2. Resource nonnegativity
- Attempt stage without enough stock → stays APPROVED (or fails) without negative stock.

### T3. Determinism
- Same seed/config, same actions schedule → identical project ledger signature.

### T4. Snapshot roundtrip
- Save/load mid-build and confirm:
  - project state identical
  - continuing build yields identical completion tick and output.

### T5. MacroStep completion
- Create project, assign agents, run `step_day(days=n)` and verify completion expected.

---

## 9) “Codex Instructions” (verbatim)

### Task 1 — Add construction project structures
- Create `src/dosadi/world/construction.py` with enums + dataclasses
- Add `world.projects` to world state initialization

### Task 2 — Implement state machine + resource handling
- Implement transitions and staging via reservation (deduct materials on stage)
- Ensure no negative resources

### Task 3 — Add work action
- Add `WORK_ON_PROJECT(project_id)` and deterministic labor contributions
- Schedule project processing without global scans

### Task 4 — Facility stub output
- On COMPLETE, create a new facility/node record and attach to world topology

### Task 5 — MacroStep integration
- In macro-step mode, integrate project labor by elapsed time for assigned agents

### Task 6 — Save/Load + tests
- Add serialization into snapshot
- Add tests: progression, nonnegativity, determinism, snapshot roundtrip, macro completion

---

## 10) Definition of Done

- `pytest` passes.
- Projects can be created, staged, worked, and completed deterministically.
- Projects persist across save/load and continue without divergence.
- Macro-step can advance BUILDING projects and produce completed facilities in evolved seeds.
- No negative stocks occur under any tested path.

---

## 11) Next steps after this

1. Replace reservation with logistics delivery (barrels/material hauling)
2. Tie project proposals to SurveyMap site scoring + governance decisions
3. Add facility-specific behaviors (production, services, security)
