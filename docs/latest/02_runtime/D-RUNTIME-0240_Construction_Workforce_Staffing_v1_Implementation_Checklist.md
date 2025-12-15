---
title: Construction_Workforce_Staffing_v1_Implementation_Checklist
doc_id: D-RUNTIME-0240
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-16
depends_on:
  - D-RUNTIME-0235   # Construction_Projects_v1
  - D-RUNTIME-0236   # Expansion_Planner_v1
  - D-RUNTIME-0237   # Facility_Behaviors_v1
  - D-RUNTIME-0238   # Logistics_Delivery_v1
  - D-RUNTIME-0239   # Scout_Missions_v1
---

# Construction Workforce + Staffing v1 — Implementation Checklist

Branch name: `feature/workforce-staffing-v1`

Goal: add a deterministic, testable **workforce assignment layer** so that:
- projects only progress if they have assigned workers,
- facilities can require staffing to operate,
- scouting/logistics can reserve people without double-assigning agents,
- macro-step evolution remains fast and deterministic.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **No double assignment.** An agent can have at most one active assignment at a time.
2. **Deterministic staffing.** Same world state + same seed → same assignments.
3. **Reserve capacity.** Keep `min_idle_agents` available; do not starve core survival loops.
4. **Bounded computation.** No O(all_agents) scans every tick; staffing runs on a slow cadence (daily/weekly).
5. **Save/Load compatible.** Assignment state persists and resumes without divergence.

---

## 1) Concept model (v1)

A new world-level system:
- **WorkforceLedger** that tracks current assignments and their intended duration.
- A **StaffingPolicy** that decides how many agents to allocate to:
  - construction projects
  - facility operation
  - scout missions (already chooses party, but should lock them here too)
  - logistics (if/when you switch from abstract carriers to agents)

In v1 we keep it simple and deterministic:
- rank candidate agents by stable key (role tags, skill score, agent_id)
- assign top-K to open staffing requests.

---

## 2) Implementation Slice A — Data structures

### A1. Create module: `src/dosadi/world/workforce.py`
**Deliverables**
- `class AssignmentKind(Enum): IDLE, PROJECT_WORK, FACILITY_STAFF, SCOUT_MISSION, LOGISTICS_COURIER`
- `@dataclass(slots=True) class Assignment:`
  - `agent_id: str`
  - `kind: AssignmentKind`
  - `target_id: str | None`      # project_id / facility_id / mission_id / delivery_id
  - `start_day: int`
  - `end_day: int | None = None` # optional planned end
  - `notes: dict[str, str] = field(default_factory=dict)`

- `@dataclass(slots=True) class WorkforceLedger:`
  - `assignments: dict[str, Assignment]`  # agent_id -> assignment
  - `def get(self, agent_id: str) -> Assignment`
  - `def is_idle(self, agent_id: str) -> bool`
  - `def assign(self, a: Assignment) -> None`   # enforces no double assignment
  - `def unassign(self, agent_id: str) -> None`
  - `def signature(self) -> str`

### A2. World integration
- Add `world.workforce: WorkforceLedger`
- Initialize all agents as `IDLE` at day 0 (or lazily on first access).

---

## 3) Implementation Slice B — Staffing requests + policy

### B1. Create module: `src/dosadi/runtime/staffing.py`
**Deliverables**
- `@dataclass(slots=True) class StaffingConfig:`
  - `min_idle_agents: int = 10`
  - `policy_interval_days: int = 1`   # run daily in macrostep
  - `max_changes_per_cycle: int = 10` # bounded churn
  - `project_workers_default: int = 6`
  - `facility_staff_default: int = 2`
  - `prefer_keep_assignments: bool = True`

- `@dataclass(slots=True) class StaffingState:`
  - `last_run_day: int = -1`

- `def run_staffing_policy(world, *, day: int, cfg: StaffingConfig, state: StaffingState) -> None`

### B2. Staffing priorities (v1 deterministic)
Priority order (highest first):
1. **Scout missions** (party members must be locked as SCOUT_MISSION)
2. **Building projects** (PROJECT_WORK)
3. **Active facilities** that require labor (FACILITY_STAFF)
4. Logistics couriers (only if you use agents for logistics; otherwise skip)
5. Everything else stays IDLE

Tie-breaks:
- stable sort by `(role_priority, skill_score, agent_id)`

### B3. Skill score (v1 cheap)
Implement `skill_score(agent, kind)` as a deterministic linear combination:
- PROJECT_WORK: `construction_skill + END + WIL` (or whatever exists)
- FACILITY_STAFF: `craft + INT`
- SCOUT_MISSION: `perception + END`
If you don’t have these skills yet, just use `END + WIL` placeholders.

---

## 4) Implementation Slice C — Integrations (lock/unlock)

### C1. Construction projects
- When project transitions to BUILDING:
  - ensure it has workers assigned through workforce system.
- Project labor integration (tick or macro):
  - only apply labor from assigned workers.
  - labor per day = `workers * base_hours_per_day * efficiency`.

### C2. Facility behaviors
- If a facility behavior has `requires_labor=True`:
  - output multiplier depends on staff count (v1 can be 0% with 0 staff; 100% at target staff).
- Staffing request:
  - facilities request `facility_staff_default` workers.

### C3. Scout missions
- When a mission is created, assign party members:
  - `AssignmentKind.SCOUT_MISSION` with `target_id=mission_id`
- On mission completion/failure:
  - unassign party members (return to IDLE or next policy run).

### C4. Logistics delivery (optional in v1)
If logistics uses abstract carriers, skip.
If using agent couriers:
- assign `LOGISTICS_COURIER` similarly with deterministic selection.

---

## 5) Implementation Slice D — Bounded churn and stability

To avoid thrash:
- If `prefer_keep_assignments=True`, do not unassign an agent unless:
  - the target has completed, or
  - staffing is below reserve, or
  - higher priority demand appears and you need to reallocate.

Implement `max_changes_per_cycle` to cap reassignments per run.

---

## 6) Save/Load integration

- Serialize:
  - WorkforceLedger assignments
  - StaffingState (last_run_day)
- Snapshot roundtrip must preserve:
  - exact assignments (agent_id → kind/target_id)

---

## 7) Tests (must-have)

Create `tests/test_workforce_staffing.py`.

### T1. No double assignment
- Assign agent to a project, then attempt assign to mission → must fail or require explicit unassign.

### T2. Determinism
- Same world snapshot + day → `run_staffing_policy` yields identical workforce signature.

### T3. Reserve enforcement
- With `min_idle_agents=N`, policy never assigns below reserve.

### T4. Project labor depends on workers
- Create project, run day with 0 workers → no progress.
- Assign workers, run day → progress increases deterministically.

### T5. Facility labor gating
- Facility requires labor; with 0 staff → outputs 0 (or reduced).
- With staff → outputs expected.

### T6. Snapshot stability
- Save mid-run, load, run policy again → no divergence in assignments.

---

## 8) “Codex Instructions” (verbatim)

### Task 1 — Add WorkforceLedger
- Create `src/dosadi/world/workforce.py` with AssignmentKind, Assignment, WorkforceLedger
- Add `world.workforce` initialization and a deterministic `signature()`

### Task 2 — Implement staffing policy
- Create `src/dosadi/runtime/staffing.py` with StaffingConfig/State and `run_staffing_policy`
- Implement deterministic selection and priority order
- Enforce reserve (`min_idle_agents`) and no double assignment

### Task 3 — Integrate with systems
- Construction: apply labor only from assigned workers
- Facilities: gate/scale outputs based on staff count if `requires_labor`
- Scouts: lock/unlock party members via workforce ledger
- Logistics: optional (if agent couriers exist)

### Task 4 — Save/Load + tests
- Serialize workforce + staffing state in snapshots
- Add tests T1–T6

---

## 9) Definition of Done

- `pytest` passes.
- Workforce assignments are deterministic and persist across save/load.
- Projects and facilities respond to staffing (no staffing → no/low output).
- Scouting parties are locked and released correctly.
- Macrostep runs remain fast (bounded staffing work per day).

---

## 10) Next slices after this

1. Phase Engine v1 (Phase 0/1/2 with KPI-triggered policies)
2. Incident Engine v1 (loss/theft/sabotage/disease as event sources feeding crumbs/episodes)
