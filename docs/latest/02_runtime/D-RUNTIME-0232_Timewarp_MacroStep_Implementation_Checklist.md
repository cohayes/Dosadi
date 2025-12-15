---
title: Timewarp_MacroStep_Implementation_Checklist
doc_id: D-RUNTIME-0232
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-15
depends_on:
  - D-RUNTIME-0230   # Cadence_Contract
  - D-RUNTIME-0231   # Save/Load + Seed Vault + Deterministic Replay
  - D-RUNTIME-0001   # Simulation_Timebase
  - D-AGENT-0020     # Agent model
---

# Timewarp / MacroStep — Implementation Checklist

Branch name: `feature/timewarp-macrostep`

Goal: make long-horizon evolution feasible (years/centuries) by adding **coarse time advancement** (“macro-steps”) that respects core invariants and remains testable against tick-mode for small worlds.

This is the first step toward generating “200-year empire seeds” without simulating billions of ticks.

---

## 0) Non-negotiables

1. **MacroStep is explicit and opt-in.** It should not silently change tick-mode semantics.
2. **MacroStep preserves invariants.** No negative stocks, no impossible states, deterministic RNG progression.
3. **MacroStep is testable.** At least one equivalence-style test exists vs tick-mode on small worlds.
4. **MacroStep is staged.** Start with “DayStep v1” that only updates a limited set of subsystems; expand iteratively.
5. **Work is bounded per step.** MacroStep must scale with population and should prefer aggregated statistics.

---

## 1) Design: MacroStep contract (what it is / isn’t)

### 1.1 MacroStep is a different simulation mode
- Tick-mode: resolves acute actions (movement, queues, fights) and rich local causality.
- MacroStep: advances world state by **integrating chronic systems** with approximations.
- MacroStep should treat most agents as **Ambient** (Cadence Contract), except a pinned interest set.

### 1.2 What MacroStep does in v1 (DayStep v1 scope)
In v1, the day-step should update:
- **Time cursor**: advance tick by `ticks_per_day * days`
- **Physiology/needs**: integrate hunger/thirst/rest via elapsed-time rates
- **Facility/economy rollups** (very minimal):
  - queued production totals (if you have production)
  - stock transfers (aggregate)
- **Memory**:
  - optional: run sleep-driven belief formation for agents who slept during the interval
  - otherwise: leave memory untouched in v1
- **Disease/health rollups**:
  - apply day-scale progression only (if present)
- **Governance rollups**:
  - run once-per-day policy update hooks (if present)

**Explicit non-goals for v1**
- No per-agent movement pathing
- No per-tick queue micro-behavior
- No detailed perception loops

---

## 2) Implementation Slice A — Timewarp module + DayStep v1

### A1. Create module: `src/dosadi/runtime/timewarp.py`
**Deliverables**
- `@dataclass(slots=True) class TimewarpConfig: ...`
  - `max_awake_agents: int = 200` (pinned interest set)
  - `physiology_enabled: bool = True`
  - `economy_enabled: bool = False` (toggle until implemented)
  - `memory_enabled: bool = False` (toggle until implemented)
  - `health_enabled: bool = False`
  - `governance_enabled: bool = False`
- `def step_day(world, *, days: int = 1, cfg: TimewarpConfig | None = None) -> None`
- `def step_to_day(world, *, target_day: int, cfg: TimewarpConfig | None = None) -> None`

**Core rules**
- Advance `world.tick` by `days * ticks_per_day`
- For all integration-based systems: use `elapsed_days` or `elapsed_ticks` from the prior tick.
- Use deterministic RNG draws in a stable order (agent id order) for any stochastic rollups.

### A2. Agent integration helpers
Add helper functions (can live in timewarp module initially):
- `def integrate_needs(agent, *, elapsed_ticks: int) -> None`
- `def integrate_physiology(agent, *, elapsed_ticks: int) -> None`
- `def integrate_health(agent, *, elapsed_days: int) -> None` (optional)
- `def integrate_memory(agent, *, elapsed_days: int) -> None` (optional)

**Important:** These must be *pure-ish* and deterministic. Prefer:
- rates derived from agent + suit + environment
- no random draws unless required (and if used, stable ordering)

### A3. Awake/Ambient pinning (minimal)
For v1, you can ignore full awake/ambient; but add a placeholder:
- `def select_awake_set(world, cfg) -> list[AgentId]`
  - choose agents with active conflicts, key roles, or in “critical facilities”
  - cap at `cfg.max_awake_agents`

In v1, the awake set can simply receive more frequent integration granularity (e.g., split day into 24 “hour steps” for them), while ambient agents get single day integration.

---

## 3) Implementation Slice B — Equivalence tests vs tick-mode (small world)

Create `tests/test_timewarp_macrostep.py`.

### B1. Day equivalence test (v1)
**Test name**
- `test_timewarp_step_day_matches_tick_mode_kpis_small_world()`

**Procedure**
1. Initialize a small scenario/world (low agent count) with fixed seed.
2. Run tick-mode for exactly 1 day (`ticks_per_day`) from tick T0.
3. Record KPIs + signature subset:
   - tick
   - agent counts, alive counts
   - aggregate needs statistics (avg hunger/thirst/rest)
   - stocks totals (if applicable)
4. Reinitialize fresh with same seed.
5. Run macro-step `step_day(days=1)`.
6. Compare KPIs within tolerances:
   - exact match for deterministic invariants (tick, counts, nonnegativity)
   - approximate match for continuous fields (needs) within epsilon

> In v1, do NOT require full state equality; require invariants and high-level KPIs.

### B2. Determinism test
**Test name**
- `test_timewarp_deterministic_replay_same_seed_same_result()`

Run macro-step twice from identical snapshots and confirm world signature matches exactly.

---

## 4) Implementation Slice C — Optional: fast-forward harness

If useful now, add a helper script/CLI entry later:
- `evolve_seed(scenario_id, seed, years, cfg) -> snapshot`
- Save to seed vault after evolution.

This is optional for v1; do it once core tests are green.

---

## 5) Implementation notes (practical guidance)

### 5.1 “Best possible” integration pattern
Avoid snapping by integrating based on elapsed time:
- `need += rate_per_tick * elapsed_ticks`
- clamp to [0, 1] or your canonical ranges
- apply action-debt if you track it; in macro-step v1 you can ignore action-debt or treat it as zero.

### 5.2 Stochastic rollups (if any)
If you must do randomness in macro mode:
- iterate agents by sorted id
- draw RNG in a fixed order
- store RNG state in snapshot (from 0231)

### 5.3 Adaptive granularity
For awake agents:
- split day into `H` substeps (e.g., 24) *only for those agents*
- this preserves “high-fidelity few, low-fidelity many” without O(population * 24).

---

## 6) “Codex Instructions” (verbatim)

### Task 1 — Add timewarp module
- Create `src/dosadi/runtime/timewarp.py`
- Implement `TimewarpConfig`, `step_day`, `step_to_day`
- In `step_day`, advance `world.tick` by `days * ticks_per_day`
- Integrate agent needs/physiology via elapsed-time integration
- Ensure stable ordering for any loops that could affect determinism

### Task 2 — Add tests
- Create `tests/test_timewarp_macrostep.py`
- Implement:
  - `test_timewarp_step_day_matches_tick_mode_kpis_small_world`
  - `test_timewarp_deterministic_replay_same_seed_same_result`
- Use KPI comparisons with tolerances for continuous values

### Task 3 — Keep v1 scope tight
- Do not attempt movement, pathing, or queue micro-sim in macro-step v1
- Expand macro-step subsystems only after tests are green

---

## 7) Definition of Done

- `pytest` passes.
- Can macro-step a scenario world forward 1–30 days without errors.
- Determinism test passes for macro-step runs.
- KPI equivalence test passes for small-world 1-day comparisons (within tolerances).
- Macro-step does not introduce negative stocks or impossible states.

---

## 8) Next steps after this branch

Once DayStep v1 is stable:
1. Add WeekStep/MonthStep variants (optional)
2. Integrate facility production/economy rollups
3. Tie in sleep-driven daily belief formation
4. Build “survey + construction projects” on top of fast-forward so empires can form
