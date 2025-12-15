---
title: Expansion_Planner_v1_Implementation_Checklist
doc_id: D-RUNTIME-0236
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-15
depends_on:
  - D-RUNTIME-0231   # Save/Load + Seed Vault + Deterministic Replay
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0233   # Evolve Seeds Harness
  - D-RUNTIME-0234   # Survey Map v1
  - D-RUNTIME-0235   # Construction Projects v1
---

# Expansion Planner v1 — Implementation Checklist

Branch name: `feature/expansion-planner-v1`

Goal: add a minimal, deterministic “institution brain” that turns:
**SurveyMap knowledge → site ranking → project proposals → approvals → ConstructionProjects → labor assignment**.

This is the smallest loop that allows the sim to *expand into an empire* automatically during evolve/timewarp runs.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Planner is deterministic.** Same seed + same world state → same chosen projects.
2. **Planner is bounded.** It evaluates at most `N` candidate sites per planning cycle.
3. **Planner is safe.** It never violates invariants (no negative stock; respects project limits).
4. **Save/Load compatible.** Planner state (if any) persists; decisions are replay-stable.
5. **Minimal scope.** v1 is site selection + project spawning + labor assignment. No deep economics.

---

## 1) Concept model (v1)

The planner runs on a slow cadence (daily/weekly/monthly) and:
1. Collects candidate sites from `world.survey_map`
2. Scores each site via `score_site(...)`
3. Creates a ranked list of proposals
4. Applies “approval” constraints:
   - budget (materials available or reserved)
   - max concurrent projects
   - phase policy (Golden Age vs Scarcity) (optional in v1)
5. Spawns `ConstructionProject` instances
6. Assigns a small labor pool (agents) to active projects

---

## 2) Implementation Slice A — Planner module + config

### A1. Create module: `src/dosadi/world/expansion_planner.py`
**Deliverables**
- `@dataclass(slots=True) class ExpansionPlannerConfig:`
  - `planning_interval_days: int = 30`
  - `max_candidates: int = 50`
  - `max_new_projects_per_cycle: int = 1`
  - `max_active_projects: int = 3`
  - `min_site_confidence: float = 0.5`
  - `project_kinds: tuple[str, ...] = ("outpost",)`
  - `materials_budget: dict[str, float] = field(default_factory=dict)`  # optional cap
  - `labor_pool_size: int = 8`
  - `min_idle_agents: int = 10`  # don't starve core ops

- `@dataclass(slots=True) class ExpansionPlannerState:`
  - `next_plan_day: int`
  - `last_plan_day: int = -1`
  - `recent_choices: list[str] = field(default_factory=list)`  # node_ids; bounded

- `def maybe_plan(world, *, cfg: ExpansionPlannerConfig, state: ExpansionPlannerState) -> list[str]`
  - Returns list of created `project_id` values (or empty).

### A2. World integration
- Add to world:
  - `world.expansion_planner_cfg`
  - `world.expansion_planner_state`
- Initialize in scenario init with a deterministic offset (hash(world.seed) % interval).

---

## 3) Implementation Slice B — Candidate selection + scoring

### B1. Candidate gathering (deterministic)
- Take SurveyMap nodes:
  - filter `confidence >= cfg.min_site_confidence`
  - exclude nodes already hosting facilities (if tracked)
  - exclude nodes in `state.recent_choices` (optional)
- Deterministic ordering:
  - sort by `node_id` before scoring
- Select up to `cfg.max_candidates`

### B2. Scoring
- Use `score_site(node, origin_node_id=..., survey=..., cfg=SiteScoreConfig)`
- Choose an origin:
  - v1: a fixed “capital” node id or primary ward hub
  - fallback: None (score without origin penalty)
- Sort candidates by:
  1) highest score
  2) tie-breaker: lowest node_id (deterministic)

---

## 4) Implementation Slice C — Proposal → approval → project creation

### C1. Proposal structure (in-module, v1)
- `@dataclass(slots=True) class ProjectProposal:`
  - `site_node_id: str`
  - `kind: str`
  - `score: float`
  - `estimated_cost: ProjectCost`

### C2. Costing (v1 simple)
Implement `estimate_cost(kind) -> ProjectCost`:
- For v1, hardcode a small table:
  - outpost: materials {"polymer": 10, "metal": 5}, labor_hours 80
  - pump_station: materials {...}, labor_hours ...
(Use placeholders if your economy/stock types differ.)

### C3. Approval rules (v1)
Approve if:
- active projects < cfg.max_active_projects
- new projects this cycle < cfg.max_new_projects_per_cycle
- stock has required materials (or within budget cap)
- labor pool is available (idle agents >= cfg.labor_pool_size + cfg.min_idle_agents)

### C4. Project creation
- Create `ConstructionProject` in PROPOSED then immediately APPROVE+STAGE if rules pass (or create APPROVED and let staging happen automatically).
- Add to `world.projects`.
- Record `site_node_id` in `state.recent_choices` (cap length to, e.g., 10).

---

## 5) Implementation Slice D — Labor assignment policy

### D1. Deterministic worker selection
- Define “idle” as agents not currently assigned to critical queues/work.
- Select labor pool by deterministic ordering:
  - sort eligible agent ids by (role_priority, skill, id)
  - choose first `cfg.labor_pool_size`

Assign to project:
- `project.assigned_agents = selected_ids`

### D2. Do not break core operations
Respect `cfg.min_idle_agents` so planner doesn’t consume the whole workforce.

---

## 6) MacroStep + tick-mode integration

### 6.1 MacroStep (timewarp)
- Ensure `step_day` invokes `maybe_plan(...)` at the appropriate day boundaries.
- Planner cadence should run in macro-step and in normal tick-mode runs (if day boundaries are reached).

### 6.2 Tick-mode
- If tick-mode has a “daily hooks” mechanism, attach planner there.
- Otherwise, check `world.day` changes and call planner once per day with a guard (like `last_plan_day`).

---

## 7) Save/Load integration

### S1. Snapshot support
- Serialize:
  - planner cfg (optional; can be scenario config)
  - planner state (required: next_plan_day, last_plan_day, recent_choices)
- Ensure snapshot roundtrip preserves the state exactly.

---

## 8) Tests (must-have)

Create `tests/test_expansion_planner.py`.

### T1. Deterministic planning
- Same world (or snapshot) → planner chooses same site and project kind.

### T2. Bounded candidate evaluation
- Given a large SurveyMap, ensure only max_candidates are evaluated and runtime is bounded.

### T3. Approval safety
- If materials insufficient, planner does not create/stage project.

### T4. Snapshot stability
- Save mid-run, load, run to next planning boundary, confirm planner picks same project(s).

### T5. Integration with evolve harness
- Run a short evolve (e.g., 1–5 years) and assert:
  - at least one project created (if survey map provides candidates)
  - projects persist in milestones and facility count grows.

---

## 9) “Codex Instructions” (verbatim)

### Task 1 — Add expansion planner module
- Create `src/dosadi/world/expansion_planner.py`
- Implement `ExpansionPlannerConfig`, `ExpansionPlannerState`, and `maybe_plan(...)`
- Candidate selection uses SurveyMap with deterministic ordering
- Scoring uses `score_site(...)`
- Proposal costing uses a small deterministic table
- Approval rules enforce budget, max active projects, and labor availability
- On approval, create ConstructionProject and assign workers deterministically

### Task 2 — Integrate planner into runtime
- Add planner cfg/state to world initialization
- Call planner on planning boundaries in macro-step day advancement and in tick-mode daily hooks

### Task 3 — Save/Load
- Serialize planner state into snapshot; restore identically
- Add snapshot roundtrip tests covering planner state

### Task 4 — Add tests
- Create `tests/test_expansion_planner.py` and implement tests T1–T5

---

## 10) Definition of Done

- `pytest` passes.
- Planner creates deterministic construction projects from survey map sites.
- Planner does not violate invariants (materials, labor, max projects).
- Planner runs under macro-step and produces growth across evolved seeds.
- Save/load preserves planner state and decisions.

---

## 11) Next steps after this

1. Facility behaviors v1 (completed facilities do something daily)
2. Logistics delivery v1 (replace reservation with actual hauling)
3. Phase-aware policies (Golden Age vs Scarcity constraints)
