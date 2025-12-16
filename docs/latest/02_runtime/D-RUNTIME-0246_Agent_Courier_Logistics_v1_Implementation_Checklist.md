---
title: Agent_Courier_Logistics_v1
doc_id: D-RUNTIME-0246
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-16
depends_on:
  - D-RUNTIME-0234   # Survey_Map_v1
  - D-RUNTIME-0238   # Logistics_Delivery_v1
  - D-RUNTIME-0240   # Construction_Workforce_Staffing_v1
  - D-RUNTIME-0242   # Incident_Engine_v1
  - D-RUNTIME-0245   # Decision_Hooks_v1
---

# Agent Courier Logistics v1 — Implementation Checklist

Branch name: `feature/agent-couriers-v1`

Goal: upgrade **Logistics Delivery v1** from “abstract carriers” to **agent-backed couriers** (via `WorkforceLedger`), while keeping:
- deterministic behavior (same seed/state → same assignments),
- bounded computation (no tick-level O(N) scans),
- save/load compatibility,
- a clean escape hatch (feature flag) so Founding Wakeup MVP can keep “abstract carriers” until we’re ready.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Backwards compatible by default.** If `use_agent_couriers=False`, logistics behaves exactly as it does today (abstract carriers via `world.carriers_available`).  
2. **No double-assignments.** If a courier is an agent, they must be locked via `WorkforceLedger` (`AssignmentKind.LOGISTICS_COURIER`).  
3. **Bounded selection.** Courier selection is deterministic and uses a bounded candidate pool (do **not** scan the entire population every tick).  
4. **Clean release.** Every path that ends a delivery (DELIVERED / FAILED / CANCELED) must release the courier (agent unassigned or carrier pool incremented).  
5. **Tests first.** Add/extend unit tests so this feature can evolve without regressions.

---

## 1) Concept model

### 1.1 Delivery lifecycle (v1)
We keep the current “schedule + due queue” model:

- A delivery request is created (typically by a construction stage).
- When assigned:
  - we reserve a courier (agent or abstract carrier),
  - compute/schedule `deliver_tick`,
  - push `(deliver_tick, delivery_id)` onto `world.delivery_due_queue` (heap).
- When due:
  - deliver succeeds → materials arrive → delivery completes,
  - or a failure incident/rule triggers → delivery fails.
- In either case, the courier is released.

### 1.2 Courier “kinds” (compatibility)
Courier identity is stored in `delivery.assigned_carrier_id` with a simple convention:

- abstract carrier IDs are `"carrier:<int>"` (existing)
- agent courier IDs are the actual `agent_id` strings (e.g. `"a-17"`)

This avoids schema churn (no new fields) while enabling agent-backed carriers.

### 1.3 Event + memory integration (what this unlocks)
The repo already routes events to stakeholders, including agents assigned as `LOGISTICS_COURIER` to a delivery. Once couriers are real agents:

- a courier can *personally* receive `DELIVERY_DELAYED / DELIVERY_FAILED / DELIVERY_DELIVERED` as episodes/crumbs,
- and later decision hooks can use those beliefs to avoid routes, prefer escort, etc.

We *do not* attempt to make courier movement “tick-realistic” in v1. This is macro-level logistics with agent identity.

---

## 2) Implementation Slice A — Flag + deterministic courier selection

### A1. Add a feature flag for agent couriers
Where to put it (pick one and keep it stable):
- Option 1: `dosadi/world/logistics.py` → `@dataclass LogisticsConfig(use_agent_couriers: bool = False)` stored on `world.logistics_cfg`
- Option 2: `WorldState.config` (if you already centralize runtime flags)

**Deliverables**
- A single boolean flag: `use_agent_couriers` defaulting to `False`.
- Tests verifying default behavior stays unchanged.

### A2. Deterministic courier selection helper
Create helper in `src/dosadi/world/logistics.py` (or `src/dosadi/runtime/staffing.py` if you prefer policy ownership):

`def _choose_idle_courier_agent(world, *, day: int, max_candidates: int = 200) -> str | None`

Rules:
- deterministic order: `sorted(world.agents.keys())`
- bounded: only inspect the first `max_candidates` agent IDs (this prevents pathological O(N) scans in giant sims)
- select the first agent that is `ledger.is_idle(agent_id)`

If you want a slightly smarter selection without cost:
- prefer agents with higher `END` (or “stamina”) by stable sort key, but keep it deterministic.

### A3. Reserve the agent in `WorkforceLedger`
When assigning a delivery, if `use_agent_couriers=True` and an idle agent is found:

- `ledger.assign(Assignment(agent_id=..., kind=LOGISTICS_COURIER, target_id=delivery_id, start_day=day, notes={"role":"courier"}))`
- `delivery.assigned_carrier_id = agent_id`
- store `delivery.notes["carrier_kind"] = "agent"` (optional, for debugging)
- proceed to schedule the delivery as usual

If no agent courier is available:
- fall back to abstract carriers (recommended), OR
- leave as REQUESTED and emit a `DELIVERY_DELAYED` event (optional).

**Recommendation (v1):** fall back to abstract carriers so macro-step evolution doesn’t stall early.

---

## 3) Implementation Slice B — Unified release semantics (abstract vs agent)

Right now logistics uses `_release_carrier(world)` (abstract pool). We need a unified release that works for both.

### B1. Replace `_release_carrier(world)` with:
`def release_courier(world, carrier_id: str | None) -> None`

Logic:
- if `carrier_id is None`: return
- if `carrier_id.startswith("carrier:")`: increment `world.carriers_available` (existing behavior)
- else:
  - `ledger = ensure_workforce(world)`
  - unassign the agent (best-effort), but do not crash

### B2. Update every “end-of-delivery” path to call release
Search and update:
- `process_due_deliveries()` success path (`_deliver(...)`)
- `process_due_deliveries()` failure path (phase loss / hazard / incident)
- incident engine resolution for delivery delay/loss (it currently imports `_release_carrier`)

**Deliverables**
- One and only one function that releases couriers, used everywhere.
- No code path leaves a courier locked forever.

---

## 4) Implementation Slice C — Optional agent location stamping (debug-only)

This is optional, but helps validate the system without introducing tick-level pathing.

When the courier is an agent:
- on assignment: set `agent.navigation_target_id = delivery.to_node_id` (or dest), if you want it visible
- on delivery completion: set `agent.location_id = delivery.to_node_id`
- on delivery failure: set `agent.location_id = delivery.from_node_id` or leave unchanged

**Important:** do not mutate agent movement state in the tick-level Founding Wakeup loop unless `use_agent_couriers=True` in that runtime. Prefer enabling this only in macro-step evolution runs.

---

## 5) Tests (required)

Add tests under `tests/` (extend the existing logistics tests).

### T1. Agent courier assignment is deterministic
- Create a world with agents `a-1, a-2, ...`
- Ensure workforce exists; all idle
- Enable `use_agent_couriers=True`
- Create one delivery
- Assert:
  - `delivery.assigned_carrier_id == "a-1"` (or the deterministic top choice)
  - `ledger.get("a-1").kind is LOGISTICS_COURIER`
  - `ledger.get("a-1").target_id == delivery_id`

### T2. Courier is released after delivery
- Run `process_logistics_until(... target_tick=deliver_tick ...)`
- Assert:
  - delivery status is DELIVERED (or FAILED in a failure test)
  - workforce assignment for the courier is IDLE again

### T3. Fallback behavior matches prior semantics
- Enable `use_agent_couriers=True`
- Provide zero agents (or set `max_candidates=0`) so no courier can be selected
- Assert the system uses `carrier:<n>` and decrements `world.carriers_available` as before

### T4. Snapshot roundtrip retains invariants
- Snapshot world, restore world
- Run another day of macro-step
- Assert `world_signature(world) == world_signature(restored)` (or the equivalent deterministic comparison you already use)

---

## 6) Telemetry hooks (optional but strongly recommended)

Add tiny metrics for debugging (world.metrics buckets):
- `metrics["logistics"]["assigned_agent_couriers"] += 1`
- `metrics["logistics"]["assigned_abstract_carriers"] += 1`
- `metrics["logistics"]["courier_release_mismatch"] += 1` (if release sees inconsistent assignment)

Keep metrics updates O(1).

---

## 7) Acceptance checklist

- [ ] With defaults, all existing tests pass (no behavior change).
- [ ] With `use_agent_couriers=True`, new tests pass.
- [ ] Couriers are always released on DELIVERED/FAILED/CANCELED.
- [ ] Determinism preserved (same seed/state → same courier choice).
- [ ] Save/load runs without divergence.
- [ ] No new hot-path O(N) work added to tick loops.

---

## 8) Follow-ons (not in v1)

- “Courier job” as an **awake-agent work detail** (tick-realistic pickup/dropoff).
- Route planning using `SurveyMap` multi-hop paths and hazard-aware rerouting.
- Escort requirements and convoy size protocols for high-risk edges.
- Courier fatigue / suit wear as action-attached physiological costs.
