---
title: Phase_Engine_v1_Implementation_Checklist
doc_id: D-RUNTIME-0241
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-16
depends_on:
  - D-RUNTIME-0231   # Save/Load + Seed Vault + Deterministic Replay
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0233   # Evolve Seeds Harness
  - D-RUNTIME-0236   # Expansion Planner v1
  - D-RUNTIME-0237   # Facility Behaviors v1
  - D-RUNTIME-0238   # Logistics Delivery v1
  - D-RUNTIME-0240   # Workforce Staffing v1
  - D-WORLD-0001     # (optional) World/phase arc reference if exists
---

# Phase Engine v1 — Implementation Checklist

Branch name: `feature/phase-engine-v1`

Goal: make long-run evolution produce the intended **three-phase arc**:
- Phase 0: *Golden Age Baseline*
- Phase 1: *Realization of Limits*
- Phase 2: *Age of Scarcity and Corruption*

Phase Engine v1 does **not** create deep narrative. It provides:
1) a deterministic world `phase` state machine,
2) a small set of measurable KPIs,
3) phase-aware policy knobs that plug into existing systems (planner, staffing, facilities, logistics).

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic phase transitions.** Same seed + same policies + same inputs → same transition days.
2. **No oscillation.** Phases only advance forward in v1 (0→1→2).
3. **Bounded compute.** KPI collection must be O(1) or O(facilities/projects), not O(all_agents) per day.
4. **Save/Load compatible.** Phase + KPI snapshots persist and replay identically.
5. **Testable thresholds.** Phase transitions are driven by explicit, unit-testable KPI rules.

---

## 1) Concept model (v1)

### 1.1 Phase state machine
- `world.phase: int` in {0,1,2}
- `world.phase_day: int` = day when current phase began
- `world.phase_history: list[dict]` small, append-only log of transitions

Phases advance when a threshold rule is met **and** a minimum dwell time has elapsed.

### 1.2 KPI snapshots (cheap)
The engine maintains a daily KPI snapshot record, without scanning all agents:
- water availability proxy (from stocks + consumption model)
- maintenance backlog proxy (from projects/facility states)
- logistics stress proxy (from deliveries backlog)
- expansion pressure proxy (crowding / facility load, optional placeholder)
- “corruption pressure” proxy (a scalar that rises in phase 2)

v1 can start with **3 KPIs** and expand later.

---

## 2) Implementation Slice A — Types + storage

### A1. Create module: `src/dosadi/world/phases.py`
**Deliverables**
- `class WorldPhase(IntEnum): PHASE0=0, PHASE1=1, PHASE2=2`
- `@dataclass(slots=True) class PhaseConfig:`
  - `min_days_in_phase0: int = 30`
  - `min_days_in_phase1: int = 60`
  - `hysteresis_days: int = 30`  # guard to prevent rapid transitions (still forward-only)
  - `water_per_capita_p0_to_p1: float = 2.0`   # proxy units
  - `water_per_capita_p1_to_p2: float = 1.0`
  - `logistics_backlog_p0_to_p1: int = 10`
  - `logistics_backlog_p1_to_p2: int = 50`
  - `maintenance_backlog_p1_to_p2: int = 20`
  - `require_multiple_signals: bool = True True`  # require 2-of-3 signals to advance (recommended)

- `@dataclass(slots=True) class KPISnapshot:`
  - `day: int`
  - `water_total: float`
  - `population: int`
  - `water_per_capita: float`
  - `logistics_backlog: int`
  - `maintenance_backlog: int`
  - `notes: dict[str, float] = field(default_factory=dict)`

- `@dataclass(slots=True) class PhaseState:`
  - `phase: WorldPhase = WorldPhase.PHASE0`
  - `phase_day: int = 0`
  - `last_eval_day: int = -1`
  - `history: list[dict] = field(default_factory=list)`     # {day, from, to, reasons}
  - `kpi_ring: list[KPISnapshot] = field(default_factory=list)`  # bounded e.g. last 120 days
  - `def signature(self) -> str`  # deterministic hash of phase+ring+history

### A2. World integration
- Add to world:
  - `world.phase_cfg: PhaseConfig`
  - `world.phase_state: PhaseState`

Initialize in scenario init deterministically.

---

## 3) Implementation Slice B — KPI computation (cheap + bounded)

### B1. Create module: `src/dosadi/runtime/phase_engine.py`
**Deliverables**
- `def compute_kpis(world, *, day: int) -> KPISnapshot`
  - `water_total`: from stocks ledger (or 0 if not present yet)
  - `population`: from agent registry length
  - `water_per_capita`: `water_total / max(1,population)`
  - `logistics_backlog`: count deliveries with status in REQUESTED/ASSIGNED/PICKED_UP/IN_TRANSIT
  - `maintenance_backlog`: v1 proxy:
    - count projects in APPROVED waiting delivery + BUILDING not staffed,
    - plus facilities with status != ACTIVE (if you have that), else 0.

- `def update_kpi_ring(state: PhaseState, snap: KPISnapshot, *, max_len: int = 120) -> None`

**Performance note:** avoid iterating all agents beyond a `len(world.agents)` call; backlog counts iterate deliveries/projects/facilities (already bounded relative to complexity).

---

## 4) Implementation Slice C — Phase transition logic

### C1. Transition checks
Implement `def maybe_advance_phase(world, *, day: int) -> None`:

Rules (v1, forward-only):
- If phase == PHASE0:
  - Only consider transition if `day - phase_day >= min_days_in_phase0`.
  - Signals:
    - water_per_capita < water_per_capita_p0_to_p1
    - logistics_backlog >= logistics_backlog_p0_to_p1
  - Advance to PHASE1 if:
    - require_multiple_signals=True: at least 1 signal (or 2 if you add 3 signals)
    - else: any signal

- If phase == PHASE1:
  - Only consider transition if `day - phase_day >= min_days_in_phase1`.
  - Signals:
    - water_per_capita < water_per_capita_p1_to_p2
    - logistics_backlog >= logistics_backlog_p1_to_p2
    - maintenance_backlog >= maintenance_backlog_p1_to_p2
  - Advance to PHASE2 if:
    - require_multiple_signals=True: at least 2-of-3 signals (recommended)
    - else: any signal

On transition:
- append to `state.history` with reasons
- set `state.phase`, `state.phase_day = day`

### C2. Anti-thrash guard
Even though v1 is forward-only, add:
- `if day == state.last_eval_day: return`
- set `state.last_eval_day = day`

---

## 5) Implementation Slice D — Phase-aware policy hooks

Phase Engine v1 becomes meaningful by *changing knobs*:

### D1. Expansion Planner
Add helper: `apply_phase_to_planner(cfg, phase)`:
- PHASE0: more expansion
  - `max_new_projects_per_cycle += 1`
  - `max_active_projects += 1`
- PHASE1: cautious
  - tighten approvals / increase min confidence
- PHASE2: survival-first
  - reduce expansion
  - allow only critical kinds (pump/repair)
  - increase `min_idle_agents`

### D2. Workforce staffing
Add helper: `apply_phase_to_staffing(cfg, phase)`:
- PHASE0: more builders
- PHASE1: balanced
- PHASE2: fewer builders, more facility staff (maintenance) and idle reserve

### D3. Logistics (soft corruption ramp, v1)
Introduce a config scalar:
- `world.logistics_loss_rate` (0.0 in PHASE0, small in PHASE2)
v1 can implement as:
- a small chance a delivery becomes FAILED before DELIVERED (deterministic RNG based on delivery_id/day).
Keep it **off by default** unless you want immediate Phase 2 texture.

### D4. Facilities (downtime/maintenance, v1 minimal)
Allow facilities to require labor (already in Facility Behaviors v1):
- In PHASE2, set `requires_labor=True` for more kinds or increase staff default.

**Important:** do not hardcode large behavioral differences in v1; just tweak config knobs.

---

## 6) Runtime integration

Hook Phase Engine once per simulated day:
1. Compute KPI snapshot and store in ring
2. Maybe advance phase
3. Apply phase to configs (planner/staffing/logistics/facilities) **in a deterministic order**

Recommended placement in the daily macro-step loop:
- after facility/project/logistics updates (so KPIs reflect outcomes),
- before planner decisions (so planner uses phase-aware settings).

---

## 7) Save/Load integration

- Serialize `world.phase_cfg` (optional) and `world.phase_state` (required).
- Snapshot roundtrip must preserve:
  - current phase
  - phase_day
  - KPI ring contents
  - history

---

## 8) Tests (must-have)

Create `tests/test_phase_engine.py`.

### T1. Deterministic KPI snapshot
- Build a small world with known stocks + deliveries + projects.
- Compute KPIs twice → identical.

### T2. Phase 0 → 1 transition
- Set KPI threshold low so it triggers quickly.
- Advance days and assert phase changes on the expected day with dwell time respected.

### T3. Phase 1 → 2 requires multiple signals
- Provide only 1 signal → no transition.
- Provide 2 signals → transition.

### T4. Forward-only
- Once PHASE2 reached, it never decreases even if KPIs improve.

### T5. Snapshot stability
- Save mid-phase, load, continue days, assert transition day and history identical.

### T6. Policy hook effects
- At each phase, call apply hooks and assert:
  - planner cfg differs as expected
  - staffing cfg differs as expected

---

## 9) “Codex Instructions” (verbatim)

### Task 1 — Add phase types + storage
- Create `src/dosadi/world/phases.py` with `WorldPhase`, `PhaseConfig`, `KPISnapshot`, `PhaseState`
- Add `world.phase_cfg` and `world.phase_state` initialization and deterministic `signature()`

### Task 2 — Implement phase engine runtime
- Create `src/dosadi/runtime/phase_engine.py` with:
  - `compute_kpis(world, day)`
  - `maybe_advance_phase(world, day)`
  - `apply_phase_to_planner/staffing/(optional)logistics/facilities`

### Task 3 — Wire into daily stepping
- Insert phase engine call once per simulated day in macro-step and tick-mode daily hooks
- Ensure order: update systems → KPI snapshot → transition check → apply hooks → planner decisions

### Task 4 — Save/Load + tests
- Serialize phase_state into snapshot
- Add `tests/test_phase_engine.py` implementing T1–T6

---

## 10) Definition of Done

- `pytest` passes.
- Phase transitions are deterministic and forward-only.
- KPI snapshots exist and are bounded (ring buffer).
- Planner/staffing configs change by phase and influence outcomes in evolved seeds.
- Save/load preserves phase trajectory.

---

## 11) Next slice after this

**Incident Engine v1**:
- produces loss/theft/sabotage/disease “texture” and feeds crumbs/episodes deterministically,
- becomes the main driver of Phase 2 emergent politics.
