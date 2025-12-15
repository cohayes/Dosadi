---
title: Logistics_Delivery_v1_Implementation_Checklist
doc_id: D-RUNTIME-0238
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
  - D-RUNTIME-0236   # Expansion Planner v1
  - D-RUNTIME-0237   # Facility Behaviors v1
---

# Logistics Delivery v1 — Implementation Checklist

Branch name: `feature/logistics-delivery-v1`

Goal: replace “reservation staging” with **actual delivery** so construction and facilities become grounded in
routes, travel time, and risk. v1 introduces a minimal deterministic hauling loop:
**request → assign courier → pick up → travel → drop off**.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic logistics.** Same seed + same world state → same delivery schedules/outcomes.
2. **No negative stocks.** Inventory moves must be conserved; world stock never goes negative.
3. **Bounded scheduling.** Use due-tick / timing-wheel style queues; no per-tick global scans of all shipments.
4. **MacroStep aware.** Deliveries advance correctly under `step_day(days=n)` using elapsed-time integration.
5. **Minimal v1 scope.** One origin depot, one destination site node, one courier abstraction. Expand later.

---

## 1) Concept model (v1)

Introduce a shipment/request entity:
- A **DeliveryRequest** is created by a ConstructionProject when it needs materials staged at a site.
- A **Courier** (agent or abstract vehicle) is assigned to fulfill it.
- The courier picks up from an origin stockpile/depot and delivers to the project’s site.

In v1 we can keep this intentionally simple:
- one canonical origin: “central depot” node id (or ward hub)
- travel time derived from SurveyMap edge distance or a fixed heuristic
- no theft/sabotage yet (optional later)

---

## 2) Implementation Slice A — Data structures

### A1. Create module: `src/dosadi/world/logistics.py`
**Deliverables**
- `class DeliveryStatus(Enum): REQUESTED, ASSIGNED, PICKED_UP, IN_TRANSIT, DELIVERED, FAILED, CANCELED`

- `@dataclass(slots=True) class DeliveryRequest:`
  - `delivery_id: str`
  - `project_id: str`
  - `origin_node_id: str`
  - `dest_node_id: str`
  - `items: dict[str, float]`
  - `status: DeliveryStatus`
  - `created_tick: int`
  - `due_tick: int | None = None`
  - `assigned_carrier_id: str | None = None`
  - `pickup_tick: int | None = None`
  - `deliver_tick: int | None = None`
  - `notes: dict[str, str] = field(default_factory=dict)`

- `@dataclass(slots=True) class LogisticsLedger:`
  - `deliveries: dict[str, DeliveryRequest]`
  - `active_ids: list[str]`  # optional; keep deterministic ordering
  - `def add(self, d: DeliveryRequest) -> None`
  - `def signature(self) -> str`

### A2. World integration
- Add `world.logistics: LogisticsLedger`
- Initialize empty in scenario init.

---

## 3) Implementation Slice B — Project staging changes (construction integration)

### B1. Change staging semantics
In Construction Projects v1, staging currently uses reservation/deduct-at-stage.
Change to delivery-based staging:

- When a project is APPROVED and requires materials:
  - Create DeliveryRequest(s) for required materials
  - Project remains in APPROVED (or a new status “WAITING_DELIVERY” if you want)
- When deliveries complete:
  - increment `project.materials_delivered[item]`
  - when delivered meets requirements → project transitions to STAGED

### B2. Deterministic request creation
- Create one DeliveryRequest per project (v1) with the full material list.
- Use deterministic `delivery_id` generation:
  - e.g., `delivery:{project_id}:v1` or an incrementing counter stored on world.

---

## 4) Implementation Slice C — Carrier selection and movement (minimal)

You have two v1 options; pick one and keep it simple:

### Option 1 (recommended v1): Abstract carriers (no agent involvement yet)
- Maintain `world.carriers_available: int` or a small list of carrier tokens
- Assign first available carrier to the next REQUESTED delivery in deterministic order
- Carrier capacity is infinite (v1), later add capacity.

### Option 2: Use agents as couriers
- Choose “idle” agents deterministically (similar to planner)
- Assign them to delivery work and track their location node

If you want fastest progress and least risk to core simulation: **Option 1**.

### C1. Travel time model
Implement `estimate_travel_ticks(origin, dest, survey_map) -> int`:
- If direct edge exists: `ticks = distance_m / speed_m_per_tick`
- If not connected: use a penalty or fallback constant
- Deterministic and side-effect free

Store the computed `deliver_tick = now_tick + travel_ticks`.

### C2. State transitions (deterministic)
- REQUESTED → ASSIGNED: when carrier allocated
- ASSIGNED → PICKED_UP: immediately in v1 (or after pickup delay)
  - consume items from origin stock (must succeed, else FAILED)
- PICKED_UP → IN_TRANSIT: set `deliver_tick`
- IN_TRANSIT → DELIVERED: when world.tick reaches deliver_tick
  - add items to project delivery buffer (not global stock)
  - release carrier

---

## 5) Implementation Slice D — Scheduler integration (no global scans)

### D1. Use due-tick buckets
Maintain a small timing wheel or min-heap for deliveries by `deliver_tick`.
- On assignment, push delivery into `due_queue`.
- Each tick (or cadence), pop due deliveries whose deliver_tick <= now.

In macro-step:
- if stepping by days, process all deliveries whose `deliver_tick <= new_tick`:
  - can pop multiple due items efficiently.

---

## 6) Inventory rules (conservation)

Define three inventory locations (v1):
1. `origin_stock` (global/ward depot ledger)
2. `in_transit` (implicitly held by delivery request when PICKED_UP/IN_TRANSIT)
3. `project_buffer` (materials delivered to a project site)

Rules:
- On pickup: origin decreases, delivery holds items
- On delivery: delivery releases items to project buffer
- On cancellation/failure after pickup: return to origin (deterministic) or mark lost (later)

---

## 7) Save/Load integration

- Serialize LogisticsLedger + all DeliveryRequests
- Serialize any due-queue structure deterministically (or reconstruct it from delivery records on load)
  - Preferred: reconstruct due queue on load to avoid duplicating state.
- Snapshot roundtrip must preserve:
  - delivery statuses, assigned carrier ids, deliver_tick, and inventory conservation

---

## 8) Tests (must-have)

Create `tests/test_logistics_delivery.py`.

### T1. Deterministic delivery schedule
- Same seed/world → same deliver_tick and same status progression.

### T2. Conservation + nonnegativity
- Attempt pickup without enough stock → FAILED, stock unchanged, project buffer unchanged.
- Successful path: origin decreases, then project buffer increases by same amount.

### T3. Project staging integration
- Create project requiring materials, create delivery, advance time to deliver, assert project transitions to STAGED.

### T4. MacroStep processing
- Create delivery with deliver_tick within `step_day(days=n)` interval and ensure it delivers.

### T5. Snapshot roundtrip
- Save mid-transit, load, advance to delivery tick, ensure identical results.

---

## 9) “Codex Instructions” (verbatim)

### Task 1 — Add logistics data structures
- Create `src/dosadi/world/logistics.py` with `DeliveryRequest`, `LogisticsLedger`, and status enum
- Add `world.logistics` initialization

### Task 2 — Integrate with construction projects
- Replace reservation staging with delivery-based staging
- On project approval, create a deterministic DeliveryRequest for required materials
- On delivery completion, update `project.materials_delivered` and transition project to STAGED when satisfied

### Task 3 — Implement delivery scheduling
- Implement deterministic carrier assignment (prefer abstract carriers for v1)
- Implement travel time estimation using SurveyMap edge distances with deterministic fallback
- Implement due-tick queue (min-heap or timing wheel) for IN_TRANSIT deliveries

### Task 4 — Inventory movement
- On pickup: consume from origin (fail safely if insufficient)
- On delivery: move to project buffer (not global stock)
- Enforce conservation; never allow negative stocks

### Task 5 — MacroStep + save/load + tests
- Ensure deliveries process correctly under macro-step
- Serialize logistics ledger; reconstruct queues on load
- Add tests T1–T5

---

## 10) Definition of Done

- `pytest` passes.
- Construction projects stage via delivered materials (not reservation).
- Deliveries progress deterministically and conserve inventory.
- Deliveries process under both tick-mode and macro-step.
- Save/load preserves deliveries and projects without divergence.

---

## 11) Next steps after this

1. Carrier capacity + multi-trip deliveries
2. Multiple depots/wards and routing
3. Risk events: ambush, loss, theft, corruption (phase-aware)
4. Explicit agent couriers and escort/security behaviors
