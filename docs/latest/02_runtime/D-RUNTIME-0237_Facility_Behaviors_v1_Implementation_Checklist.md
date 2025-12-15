---
title: Facility_Behaviors_v1_Implementation_Checklist
doc_id: D-RUNTIME-0237
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-15
depends_on:
  - D-RUNTIME-0231   # Save/Load + Seed Vault + Deterministic Replay
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0233   # Evolve Seeds Harness
  - D-RUNTIME-0235   # Construction Projects v1
  - D-RUNTIME-0236   # Expansion Planner v1
---

# Facility Behaviors v1 — Implementation Checklist

Branch name: `feature/facility-behaviors-v1`

Goal: make completed facilities *do something compounding* each day so empire growth is meaningful.
v1 adds a minimal, deterministic **daily production/service** loop for a small set of facility kinds.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic outputs.** Same seed + same world state → same daily facility effects.
2. **Save/Load compatible.** Facility state and any queues must serialize and resume without divergence.
3. **Bounded updates.** No O(all_agents) scans inside facility updates; facility updates should be O(facilities + local queues).
4. **MacroStep aware.** Facilities advance correctly under `step_day(days=n)`.
5. **Minimal scope.** v1 uses a small “facility kind → behavior” registry, not a giant simulation.

---

## 1) Concept model (v1)

A Facility is an entity at a location node that can:
- **Produce** resources daily (stocks increase)
- **Consume** inputs daily (stocks decrease)
- Optionally provide a simple **service** with a local queue (later expansion)

v1 focuses on production/consumption with deterministic rates.

---

## 2) Implementation Slice A — Facility schema + registry

### A1. Create module: `src/dosadi/world/facilities.py`
**Deliverables**
- `@dataclass(slots=True) class Facility:`
  - `facility_id: str`
  - `kind: str`               # "outpost", "pump_station", "workshop"
  - `site_node_id: str`
  - `created_tick: int`
  - `status: str = "ACTIVE"`  # ACTIVE/INACTIVE/DAMAGED (v1 keep simple)
  - `state: dict = field(default_factory=dict)`  # per-kind state (durability, etc.)
  - `last_update_day: int = -1`

- `@dataclass(slots=True) class FacilityLedger:`
  - `facilities: dict[str, Facility]`
  - `def add(self, f: Facility) -> None`
  - `def get(self, facility_id: str) -> Facility`
  - `def list_by_kind(self, kind: str) -> list[Facility]`
  - `def signature(self) -> str`

- `@dataclass(slots=True) class FacilityBehavior:`
  - `kind: str`
  - `inputs_per_day: dict[str, float]`
  - `outputs_per_day: dict[str, float]`
  - `requires_labor: bool = False`
  - `labor_agents: int = 0`         # if used
  - `labor_efficiency: float = 1.0` # multiplier if labor present

- `def get_facility_behavior(kind: str) -> FacilityBehavior`
  - A small deterministic lookup table for v1.

### A2. World integration
- Add `world.facilities: FacilityLedger` if not already present.
- Update Construction Projects v1 completion hook to create a Facility and register it.

---

## 3) Implementation Slice B — Stocks interface (light glue)

Facilities need a stable way to read/write resources.

### B1. Define minimal stock API (use existing if present)
Create `src/dosadi/world/stocks.py` (only if you lack an existing ledger), with:
- `def has(world, item: str, qty: float) -> bool`
- `def add(world, item: str, qty: float) -> None`
- `def consume(world, item: str, qty: float) -> bool`  # returns success
- `def snapshot_totals(world) -> dict[str, float]`      # for KPIs/tests

If you already have a stock system, adapt facility updates to call it.

---

## 4) Implementation Slice C — Daily facility update loop

### C1. Create module: `src/dosadi/runtime/facility_updates.py`
**Deliverables**
- `def update_facilities_for_day(world, *, day: int) -> None`
  - Update each facility exactly once per day (guard via `last_update_day`)
  - Apply deterministic inputs/outputs:
    1) Check inputs available; if not, either:
       - no-op (facility produces nothing that day), or
       - partial production (optional; v1 can be all-or-nothing)
    2) Consume inputs
    3) Produce outputs

### C2. Integrate into runtime
- Tick-mode: call `update_facilities_for_day` when day boundary passes.
- MacroStep: in `step_day(days=n)`, iterate days (or apply `n` in one shot):
  - Preferred v1: apply `n` days in one shot for each facility:
    - `consume inputs_per_day * n` if available
    - `produce outputs_per_day * n`
  - Must remain deterministic and respect resource availability.

**Bounded rule:** do not loop over all days if `n` can be large; compute totals and apply once.

---

## 5) Default facility kinds (v1 table)

Keep v1 intentionally small:

1. **Outpost**
- Inputs: none
- Outputs: `"survey_progress": 1` (optional abstract) OR `"intel": 1`
- Alternative: no production; provides “presence” (skip if not useful)

2. **Pump Station**
- Inputs: `"filters": 0.1` (optional)
- Outputs: `"water": 5`

3. **Workshop**
- Inputs: `"metal_scrap": 1`, `"polymer": 0.5`
- Outputs: `"filters": 0.2` or `"tools": 0.1`

If these resource names don’t match your current ledger, treat them as placeholders and keep the mechanism generic.

---

## 6) Save/Load integration

- Serialize `world.facilities` and each `Facility` state.
- Ensure facility ledger signature matches after snapshot roundtrip.
- Ensure “last_update_day” persists so you don’t double-apply.

---

## 7) Tests (must-have)

Create `tests/test_facility_behaviors.py`.

### T1. Deterministic daily outputs
- Create facility + set stocks.
- Run 1 day update twice from identical snapshots → identical totals.

### T2. Resource constraints
- If inputs missing, outputs are not produced (or partial production rule if chosen).

### T3. MacroStep equivalence (small)
- Run 7 days via macro-step and via 7 daily calls, compare stock totals.

### T4. Snapshot roundtrip
- Save mid-run, load, run another day, compare to straight-through.

### T5. Integration with expansion planner
- Run a short evolve where planner builds at least one facility.
- Assert facilities > 0 and stock totals change over time.

---

## 8) “Codex Instructions” (verbatim)

### Task 1 — Add facility schema + ledger
- Create `src/dosadi/world/facilities.py` with `Facility`, `FacilityLedger`, and `FacilityBehavior`
- Add a small behavior registry: kind → inputs/outputs

### Task 2 — Connect construction completion
- When a ConstructionProject completes, create a Facility and register it in `world.facilities`

### Task 3 — Implement daily facility updates
- Create `src/dosadi/runtime/facility_updates.py`
- Implement `update_facilities_for_day(world, day=...)` with deterministic input/consume/output logic
- Integrate into tick-mode day boundary and macro-step day stepping without looping per-day for large n

### Task 4 — Save/Load + tests
- Serialize facility ledger and facility state in snapshot
- Add tests for determinism, constraints, macro equivalence, and snapshot roundtrip

---

## 9) Definition of Done

- `pytest` passes.
- Facilities created by construction projects persist and apply daily effects deterministically.
- Facility updates work under macro-step and tick-mode.
- Stock totals change over time in evolved seeds due to facility behaviors.

---

## 10) Next steps after this

1. Logistics delivery v1 (replace reservation with hauling to sites)
2. Facility service queues (repairs, rations, clinic) and local staffing
3. Damage/maintenance loops and sabotage (politics + conflict)
