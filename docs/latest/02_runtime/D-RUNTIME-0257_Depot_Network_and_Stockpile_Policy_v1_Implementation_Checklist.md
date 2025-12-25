---
title: Depot_Network_and_Stockpile_Policy_v1_Implementation_Checklist
doc_id: D-RUNTIME-0257
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0236   # Expansion Planner v1
  - D-RUNTIME-0238   # Logistics Delivery v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0246   # Agent Courier Logistics v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0256   # Resource Extraction Sites v1
---

# Depot Network & Stockpile Policy v1 — Implementation Checklist

Branch name: `feature/depot-stockpile-policy-v1`

Goal: stop logistics from being purely reactive by introducing a deterministic **stockpile policy**
that:
- defines a depot network (depots are facilities of kind DEPOT),
- sets min/target/max thresholds per material for each depot (policy),
- generates pull/push deliveries automatically (bounded),
- creates stable “supply corridors” that expansion can reinforce,
- produces clear telemetry and memory signals (reliable depot, chronic shortage).

This is the “make the economy self-correcting” slice.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Feature flag default OFF.** With flag OFF, existing delivery behavior unchanged.
2. **Deterministic.** Same world/state → same depot policy actions and delivery requests.
3. **Bounded compute.** No global inventory scans; iterate only over depots and policy materials.
4. **No delivery spam.** Avoid duplicate requests; cap deliveries/day and per-depot.
5. **Save/Load safe.** Policies and pending state serialize; old snapshots load.
6. **Tested.** Determinism, bounds, no duplicates, snapshot roundtrip.

---

## 1) Concept model

### 1.1 Depot network
A “depot” is a facility with `FacilityKind.DEPOT`. Depots are where materials accumulate and from
which projects/repairs are supplied.

Each depot has:
- an inventory owner_id: `facility:{depot_facility_id}`
- a policy profile defining desired stock levels for key materials

### 1.2 Stockpile policy per material
For each (depot, material), define:
- `min_level` — if below, request inbound supply (pull)
- `target_level` — preferred steady-state level
- `max_level` — if above, push surplus outward or stop pulling

Policy is not a market; it is a deterministic control loop.

### 1.3 Supply sources
Inbound supply can come from:
- extraction sites (site inventories)
- producer facilities (workshops/recyclers) if configured as “upstream”
- other depots with surplus

v1 recommended order:
1) nearest extraction sites feeding this depot
2) nearest producer facilities
3) other depots with surplus above their target (or above max)
4) (optional) fallback “central stockpile” ward:0

All selection must be deterministic and bounded.

---

## 2) Implementation Slice A — Data structures

Create `src/dosadi/runtime/stockpile_policy.py`

**Deliverables**
- `@dataclass(slots=True) class StockpilePolicyConfig:`
  - `enabled: bool = False`
  - `materials: list[str] = ["SCRAP_METAL","PLASTICS","FASTENERS","SEALANT","FABRIC"]`
  - `max_deliveries_per_day: int = 30`
  - `max_deliveries_per_depot_per_day: int = 5`
  - `min_batch_units: int = 10`
  - `max_batch_units: int = 200`
  - `source_candidate_cap: int = 50`      # bounded search cap
  - `depot_candidate_cap: int = 25`
  - `prefer_same_ward: bool = True`
  - `deterministic_salt: str = "stockpile-v1"`

- `@dataclass(slots=True) class StockpilePolicyState:`
  - `last_run_day: int = -1`
  - `deliveries_requested_today: int = 0`

- `@dataclass(slots=True) class MaterialThreshold:`
  - `min_level: int`
  - `target_level: int`
  - `max_level: int`

- `@dataclass(slots=True) class DepotPolicyProfile:`
  - `depot_facility_id: str`
  - `thresholds: dict[str, MaterialThreshold]`   # key by Material.name (string)
  - `notes: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class DepotPolicyLedger:`
  - `profiles: dict[str, DepotPolicyProfile]`    # depot_facility_id -> profile
  - `def profile(self, depot_id: str) -> DepotPolicyProfile`  # create default profile if missing
  - `def signature(self) -> str`

Store on world:
- `world.stock_cfg`, `world.stock_state`, `world.stock_policies`

Snapshot them.

---

## 3) Implementation Slice B — Default policy generation

When a depot exists but has no profile:
- generate a default profile deterministically.

v1 defaults:
- SCRAP_METAL: min 50, target 150, max 400
- PLASTICS:   min 30, target 100, max 250
- FASTENERS:  min 20, target 60,  max 150
- SEALANT:    min 10, target 40,  max 120
- FABRIC:     min 10, target 30,  max 80

Phase 2 adjustment (optional):
- raise mins slightly (or reduce targets) to represent scarcity management.

---

## 4) Implementation Slice C — Daily policy runner

Implement:
- `def run_stockpile_policy_for_day(world, *, day: int) -> None`

### C1. Enumerate depots (bounded)
- depots = facilities where kind == DEPOT, sorted by facility_id
- for each depot, compute per-day delivery budget (max_deliveries_per_depot_per_day)

### C2. For each policy material, decide action
Let `inv = world.inventories.inv("facility:{depot_id}")`
For each material in policy list:
- qty = inv.get(material)
- thresholds = profile.thresholds[material]
Actions:
- if qty < min_level → PULL
- elif qty > max_level → PUSH (optional v1; can defer)
- else: no action

Compute desired amount:
- deficit = target_level - qty
- request_qty = clamp(deficit, min_batch_units, max_batch_units)
- if deficit <= 0: skip

### C3. Choose a source deterministically (bounded)
Implement:
- `def choose_source_for_material(world, depot_id, material, request_qty, day) -> tuple[source_owner_id, amount] | None`

Candidate sources (in order):
1) extraction sites (site inventories) with material available
2) producer facilities (WORKSHOP/RECYCLER) inventories with material available
3) other depots with surplus above their target (or above max)
4) fallback owner (optional): `ward:0`

Selection rules:
- candidates must be bounded by source_candidate_cap
- deterministic ordering:
  - same ward first (if prefer_same_ward), then by (distance, owner_id) if distance exists
  - else by owner_id lexicographic

Amount to pull:
- `amount = min(request_qty, source_available - source_reserve)`
  - where source_reserve is optional: keep sources from draining to zero (e.g., leave 10 units)

### C4. Avoid duplicate deliveries (critical)
For each (depot_id, material), ensure only one pending inbound request exists.
Implement a simple guard:
- `profile.notes["pending_inbound"][material] = delivery_id`
- clear it when delivery completes or fails.

Also avoid multiple deliveries from the same source to the same depot in one day unless explicitly allowed.

### C5. Create delivery requests
Create delivery:
- source_owner_id → `facility:{depot_id}`
- payload includes:
  - `kind="stockpile_pull"`
  - `material`
  - `qty`
  - `depot_id`
  - `policy_day`
- priority: medium/high (configurable)

Increment counters and stop when:
- global max_deliveries_per_day reached

### C6. Optional PUSH logic (v1.1)
If you implement push:
- if qty > max_level:
  - send surplus to a “downstream” depot or to a project site that needs it
This can be deferred to keep v1 small.

---

## 5) Integration with deliveries + inventories

Delivery completion must transfer materials:
- remove from source inventory owner
- add to destination inventory owner

If your delivery system doesn’t yet handle material transfer, add it here:
- deliveries of kind stockpile_pull should be treated as material transfer operations.

Keep it deterministic and atomic per delivery completion.

---

## 6) Events → Memory → Beliefs

Emit events:
- `STOCKPILE_PULL_REQUESTED` (depot_id, material, qty, source_owner)
- `STOCKPILE_PULL_COMPLETED` (depot_id, material, qty)
- `STOCKPILE_SHORTAGE` (depot_id, material, deficit) when no source found

Router crumbs:
- `depot-short:{material}:{depot_id}`
- `source-reliable:{owner_id}` (on successful pulls)

Belief formation can then influence escorts, routing, and investment.

---

## 7) Telemetry

Counters:
- `metrics["stockpile"]["deliveries_requested"]`
- `metrics["stockpile"]["deliveries_completed"]`
- `metrics["stockpile"]["shortages"]`
- `metrics["stockpile"]["depots_covered"]`

---

## 8) Save/Load requirements

Snapshot must include:
- stockpile config/state
- depot policy ledger + pending notes
- deliveries already snapshot via delivery system

Old snapshots:
- policy ledger empty; defaults created lazily.

---

## 9) Tests (must-have)

Create `tests/test_stockpile_policy.py`.

### T1. Flag off = baseline
- enabled=False → no new deliveries requested.

### T2. Deterministic requests
- clone world; run policy; same deliveries created and same signatures.

### T3. No duplicate deliveries
- run policy twice same day; still only one pending inbound per (depot, material).

### T4. Bounded caps enforced
- set max_deliveries_per_day small; ensure deterministic cutoff.

### T5. Source selection respects ordering
- create two sources; ensure deterministic preference (same ward or lexicographic).

### T6. Completion transfers materials
- complete delivery; source decreases, depot increases.

### T7. Snapshot roundtrip mid-pending
- save after delivery requested; load; complete; identical final signature.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add stockpile policy module + world state
- Create `src/dosadi/runtime/stockpile_policy.py` with config/state/threshold/profile/ledger
- Add `world.stock_cfg`, `world.stock_state`, `world.stock_policies` to snapshots

### Task 2 — Default policy profiles
- Implement deterministic defaults for depots (lazy creation)
- Add phase-aware adjustments if desired

### Task 3 — Daily policy runner
- Implement `run_stockpile_policy_for_day(world, day)`
- Iterate depots + policy materials boundedly
- Create PULL deliveries when below min_level
- Choose sources deterministically and avoid duplicates
- Enforce per-depot and global daily caps

### Task 4 — Delivery completion transfers
- Ensure stockpile deliveries transfer materials source→dest inventories atomically

### Task 5 — Events, telemetry, and tests
- Emit events for requests/completions/shortages
- Add `tests/test_stockpile_policy.py` implementing T1–T7
- Add metrics counters

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=False: no behavior change.
- With enabled=True:
  - depots maintain minimum stock levels via deterministic pull deliveries,
  - duplicate delivery spam is prevented,
  - daily caps are enforced,
  - inventories transfer correctly on completion,
  - events/telemetry make shortages and flows legible,
  - save/load works mid-pending.

---

## 12) Next slice after this

**Construction Project Pipeline v2** (staging, partial deliveries, blocked-reason reporting),
so you can see *why* projects stall and how stockpiles fix it.
