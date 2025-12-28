---
title: Scenario_Success_Contracts_v1_Implementation_Checklist
doc_id: D-RUNTIME-0310
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0233   # Evolve Seeds Harness v1
  - D-RUNTIME-0232   # Timewarp MacroStep v1
---

# Scenario Success Contracts v1 — Implementation Checklist

Branch name: `feature/scenario-success-contracts-v1`

Goal: make scenarios *iterable and self-terminating* by turning “what success means”
into executable contracts that:
- evaluate milestone progress during the run,
- stop early on success (or on unrecoverable failure),
- produce a standardized **Success Report** (reasons + evidence),
- and provide stable hooks for the Evolve/Timewarp harnesses to use as KPIs.

This is the single highest-leverage slice for iteration speed.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic evaluation.** Success/failure must not depend on wall-clock timing or ordering noise.
2. **Fast.** Contract evaluation must be O(1) or O(logK) per tick; never scan the world.
3. **Explainable.** Always output *why* a run ended (success, timeout, deadlock, collapse).
4. **Composable.** Works across scenarios; contracts can be swapped per scenario.
5. **Tested.** Unit tests for all milestone types + early-stop behavior.
6. **Telemetry-first.** Milestones rely on existing metrics/events; if metrics are missing, that’s a failing test, not a runtime shrug.

---

## 1) Core concept

A Scenario Success Contract is:
- a set of **milestones** with explicit *evidence sources* and thresholds,
- a set of **terminal failure conditions** (optional, bounded),
- and a set of **stop policies** (stop-on-success, stop-on-failure, stop-on-timeout).

Contracts do **not** compute meaning by inspecting the world deeply.
They consume bounded summaries produced by telemetry/event plumbing.

---

## 2) Data model

Create `src/dosadi/runtime/success_contracts.py`

### 2.1 Contract config
- `@dataclass(slots=True) class ContractConfig:`
  - `enabled: bool = True`
  - `evaluation_cadence_ticks: int = 100`        # evaluate every N ticks (not every tick)
  - `stop_on_success: bool = True`
  - `stop_on_failure: bool = True`
  - `timeout_ticks: int | None = None`           # scenario may already have max_ticks
  - `max_evidence_items: int = 64`               # for bounded evidence in report

### 2.2 Milestone types
- `Enum MilestoneStatus: PENDING, ACHIEVED, FAILED`

- `@dataclass(slots=True) class Milestone:`
  - `milestone_id: str`                          # "council_formed"
  - `name: str`
  - `description: str`
  - `status: MilestoneStatus = PENDING`
  - `achieved_tick: int | None = None`
  - `failed_tick: int | None = None`
  - `priority: int = 0`                          # ordering in reports
  - `evidence: list[dict] = field(default_factory=list)`  # bounded

### 2.3 Contract definition
- `@dataclass(slots=True) class SuccessContract:`
  - `contract_id: str`                           # "founding_wakeup_v1"
  - `scenario_id: str`
  - `milestones: list[Milestone]`
  - `failure_conditions: list[dict]`             # declarative thresholds, bounded
  - `stop_policy: dict[str, object]`             # {"stop_on_success":..., "stop_on_failure":...}
  - `notes: dict[str, object] = field(default_factory=dict)`

### 2.4 Run evaluation result
- `@dataclass(slots=True) class ContractResult:`
  - `contract_id: str`
  - `scenario_id: str`
  - `tick_end: int`
  - `ended_reason: str`                          # SUCCESS|FAILURE|TIMEOUT|MANUAL
  - `ended_detail: str`                          # human-readable string
  - `milestones: list[Milestone]`
  - `kpis: dict[str, float] = field(default_factory=dict)`
  - `evidence: list[dict] = field(default_factory=list)`  # bounded

World / report integration:
- Add `report.contract_result: ContractResult | None`
- Add `world.contract_cfg: ContractConfig`
- Add `world.active_contract: SuccessContract | None`

Persisting contract state is optional; contract *definitions* should be derivable from scenario id.

---

## 3) Evidence sources

Milestones must pull from bounded sources:
- telemetry counters (0260): `world.metrics[...]` or `report.metrics[...]`
- incident events (0242): last N incidents by type
- phase engine state (0241): current phase id
- specific world flags (bounded): e.g., `world.proto_council_id is not None`

Implement a tiny evidence adapter layer:
- `get_metric(world, "metrics.path.like.this") -> float | int | None`
- `get_recent_incidents(world, incident_kind, limit=K) -> list[...]`
- `get_flag(world, "some.flag") -> bool`

If an evidence source is missing (metric absent), the milestone should remain pending,
and a **diagnostic evidence item** should be added (“missing metric key X”).
This becomes a test target in the next slice (KPIs).

---

## 4) Milestone library (v1)

Implement milestone evaluators as small functions:
- `eval_council_formed(world) -> (achieved: bool, evidence: dict)`
- `eval_first_protocol_authored(world) -> ...`
- `eval_first_scout_mission_completed(world) -> ...`
- `eval_first_depot_built(world) -> ...`
- `eval_first_corridor_established(world) -> ...`
- `eval_first_delivery_completed(world) -> ...`
- `eval_first_injury_or_incident(world) -> ...` (optional “world got spicy”)

Each evaluator must:
- check 1–3 bounded metrics/flags/incidents,
- return an evidence dict summarizing the signal,
- never scan across all agents or facilities.

---

## 5) Founding Wakeup contract (v1)

Create contract definition in `src/dosadi/scenarios/founding_wakeup/contracts.py`
(or wherever scenarios live):

Contract ID: `founding_wakeup_contract_v1`

Recommended milestones (ordered):

1. `council_formed`
2. `first_protocol_authored`
3. `first_scout_mission_completed`
4. `first_depot_built`
5. `first_corridor_established`
6. `first_delivery_completed`
7. `first_expansion_project_started` (optional if present)
8. `first_settlement_zone_marked` (optional if present)

Recommended success rule:
- success when milestones 1–6 achieved (ignore optional ones).

Recommended failure conditions (bounded):
- `collapse_corridors_count >= 2` (corridor collapse cascade already fatal)
- `population_alive_ratio < 0.7`
- `water_shortage_severe_days >= 5` (or an equivalent metric)
- `no_progress_ticks >= X` (deadlock detector)

**Deadlock detector (v1):**
- maintain a ring buffer of the last N evaluations of a “progress signature”:
  - e.g., `progress_sig = (milestones_achieved_count, deliveries_completed, depots_built, routes_active)`
- if unchanged for `no_progress_window_ticks`, declare failure with reason DEADLOCK.

This is O(1) per evaluation.

---

## 6) Runtime wiring

### 6.1 Scenario runner integration
Wherever `run_scenario()` / scenario loop lives:
- load contract for scenario id at start
- attach to world as `world.active_contract`
- every `evaluation_cadence_ticks`, call `evaluate_contract(world, tick)`
- if stop condition met:
  - set `report.contract_result`
  - break simulation loop early
- ensure `max_ticks` still respected (timeout)

### 6.2 Report integration
Add to report:
- `ended_reason` and `ended_detail` (source: contract_result)
- include milestone statuses and achieved ticks
- include bounded evidence in JSON-friendly form

### 6.3 Telemetry integration
Add minimal metrics if missing (but don’t invent new systems here):
- deliveries_completed
- depots_built
- active_corridors/routes
- council_formed flag
- protocols_authored count
- scout_missions_completed count

If your current telemetry differs, adapt evaluators to what exists and emit missing-metric diagnostics until next slice (0311) standardizes KPIs.

---

## 7) CLI / admin UX

Add to `AdminDashboardCLI` / `DebugCockpitCLI`:
- contract panel:
  - contract id
  - milestone list with status + achieved tick
  - current progress signature
  - last evaluation tick
  - ended reason if ended

Add a single-line summary in scenario timeline:
- `END: SUCCESS (milestones=6/6) at tick 84211`
or
- `END: FAILURE (DEADLOCK) at tick 120000`

---

## 8) Tests (must-have)

Create `tests/test_scenario_success_contracts_v1.py`

### T1. Determinism
- run a short scenario twice with same seed → same end reason and milestone ticks.

### T2. Stops early on success
- configure a tiny scenario/fixture where milestones are forced true early;
  assert run terminates before max_ticks.

### T3. Timeout if never reaches success
- contract enabled but milestones never achieved; assert ended_reason == TIMEOUT.

### T4. Deadlock detection triggers
- stub progress signature constant across many evaluations; assert FAILURE/DEADLOCK.

### T5. Evidence boundedness
- ensure evidence lists never exceed max_evidence_items.

### T6. Compatibility: missing metrics yields diagnostics, not crash
- remove a metric key; evaluator returns pending with evidence mentioning missing key.

---

## 9) Codex Instructions (verbatim)

### Task 1 — Add success contracts module
- Create `src/dosadi/runtime/success_contracts.py` with ContractConfig, Milestone, SuccessContract, ContractResult and helpers

### Task 2 — Implement milestone evaluators
- Implement a small library of milestone evaluators that only use bounded metrics/flags/incidents

### Task 3 — Wire contracts into scenario runner
- Load contract per scenario; evaluate every evaluation_cadence_ticks; stop early on success/failure; attach ContractResult to report

### Task 4 — Add CLI panels
- Add contract/milestone panel to DebugCockpitCLI/AdminDashboardCLI and add end summary to timeline

### Task 5 — Add tests
- Add `tests/test_scenario_success_contracts_v1.py` (T1–T6)

---

## 10) Definition of Done

- `pytest` passes.
- Founding Wakeup scenario terminates early on success in normal runs.
- Failures are explainable and reproducible (deadlock/timeout/collapse).
- Contracts do not scan agents/facilities; evaluation time is bounded.
- Report includes a contract_result suitable for Evolve harness KPI harvesting.

---

## 11) Next slice after this

**D-RUNTIME-0311 Milestone KPIs & Scorecards v1** — standardized KPI schema that:
- feeds the evolve harness,
- replaces ad-hoc metric keys,
- and makes “seed quality” comparable across runs.
