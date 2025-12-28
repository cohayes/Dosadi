---
title: World_Event_Bus_and_Subscriptions_v1_Implementation_Checklist
doc_id: D-RUNTIME-0313
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0311   # Milestone KPIs & Scorecards v1
  - D-RUNTIME-0312   # Evidence Pipelines for Governance v1
---

# World Event Bus & Subscriptions v1 — Implementation Checklist

Branch name: `feature/world-event-bus-v1`

Goal: formalize a low-overhead, deterministic event stream so that:
- KPIs, evidence, and incident capture all read from one canonical source,
- modules can subscribe without poll loops,
- event retention is bounded (ring buffer),
- and performance budgets become enforceable.

v1 is a simple in-process bus; not async, not distributed.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic ordering.** Event ordering must be stable under identical simulation steps.
2. **Bounded retention.** Ring buffer; no unbounded event lists.
3. **Cheap publish.** Publish must be O(1) amortized; minimal allocations.
4. **Safe subscribe.** Subscribers cannot mutate event payloads; defensive copies not required if using immutability discipline.
5. **Tested.** Ordering, retention, and subscription semantics.
6. **Backwards compatible.** Existing ad-hoc counters/logs can be bridged to events.

---

## 1) Concept model

The sim currently has multiple “streams” of facts:
- incidents,
- telemetry updates,
- logistics delivery completions,
- protocol violations,
- construction completion,
- etc.

Instead, we define a single canonical event stream:

- Producers publish `WorldEvent`s
- Subscribers consume `WorldEvent`s (increment KPIs, generate evidence, log incidents)

This kills whole classes of “forgot to update metric X” bugs and reduces polling cost.

---

## 2) Data structures

Create `src/dosadi/runtime/events.py`

### 2.1 Event kinds

Use string constants or an Enum (prefer string constants for JSON friendliness).

Core kinds (v1):
- `TICK`
- `DAY_ROLLOVER`
- `INCIDENT_RECORDED`
- `DEPOT_BUILT`
- `CORRIDOR_ESTABLISHED`
- `DELIVERY_COMPLETED`
- `DELIVERY_FAILED`
- `PROTOCOL_AUTHORED`
- `PROTOCOL_VIOLATION`
- `ENFORCEMENT_ACTION`
- `CONSTRUCTION_PROJECT_STARTED`
- `CONSTRUCTION_PROJECT_COMPLETED`
- `SCOUT_MISSION_COMPLETED`

Keep v1 small; extend later.

### 2.2 WorldEvent

- `@dataclass(frozen=True, slots=True) class WorldEvent:`
  - `seq: int`                    # monotonic sequence number
  - `tick: int`
  - `day: int`
  - `kind: str`
  - `polity_id: str | None`
  - `ward_id: str | None`
  - `actor_id: str | None`
  - `subject_id: str | None`      # corridor_id, depot_id, etc.
  - `payload: tuple[tuple[str, object], ...] = ()`   # immutable-ish, small payload
  - `tags: tuple[str, ...] = ()`

Notes:
- prefer tuples for immutability and reduced accidental mutation.
- payload should be small and JSON-serializable.

### 2.3 Event bus

- `@dataclass(slots=True) class EventBusConfig:`
  - `enabled: bool = True`
  - `max_events: int = 50000`            # ring buffer size
  - `max_payload_items: int = 12`        # bound payload
  - `drop_policy: str = "DROP_OLDEST"`   # ring

- `class EventBus:`
  - `publish(kind, tick, day, ..., payload: dict|tuple=...) -> None`
  - `subscribe(handler: Callable[[WorldEvent], None], *, kinds: set[str] | None = None) -> sub_id`
  - `unsubscribe(sub_id)`
  - `get_since(seq: int) -> list[WorldEvent]` (bounded, used by tools)
  - `latest_seq() -> int`

Implementation:
- store events in a preallocated list/ring; overwrite oldest
- maintain seq counter
- subscription dispatch:
  - either immediate (publish calls handlers) or deferred (drain at end of tick)
  - v1 recommendation: **deferred drain** to keep ordering stable and avoid reentrancy.

### 2.4 Drain model (recommended)

- During tick, producers call `publish()` which appends into ring and also into a small “pending events” queue.
- At end of tick (or at defined phase boundary), call `bus.drain()`:
  - dispatch pending events in seq order to subscribers
  - clear pending queue

This ensures:
- consistent ordering,
- no module causes new events mid-handler that interleave unexpectedly (unless allowed).

---

## 3) World integration

Add to World:
- `world.event_bus_cfg: EventBusConfig`
- `world.event_bus: EventBus`

Ensure snapshot persistence:
- Do NOT persist full event ring in snapshots by default (optional debug toggle).
- Persist `seq` counter and optionally the last N events if `debug_events=True`.

For seed vault:
- no need to persist event ring.

---

## 4) Bridging existing systems

### 4.1 Incidents (0242)
- When an incident is recorded, also publish `INCIDENT_RECORDED` with payload including `incident_kind` and severity.

Long term: incident engine becomes a subscriber that materializes a structured incident log from events.

### 4.2 KPIs (0311)
- KPI module becomes a subscriber:
  - on delivery events increment counters,
  - on depot built increment,
  - on day rollover compute daily aggregates.

### 4.3 Evidence (0312)
- Evidence module becomes a subscriber or a daily cadence consumer:
  - accumulate rolling windows from relevant events (delivery failures, incidents, protocol violations),
  - produce evidence items with less reliance on scanning.

---

## 5) Performance constraints

- publish must not allocate large dicts per event; payload should be tiny and mostly tuples
- enforce `max_payload_items` and truncate with a `"__truncated__": True` marker
- allow “event sampling” later (not in v1) if event volume too high

---

## 6) Admin tooling

Add a simple event viewer panel:
- latest N events by kind filter
- ability to show payload keys
- show seq/tick/day and subject_id

This massively helps debugging.

---

## 7) Tests (must-have)

Create `tests/test_world_event_bus_v1.py`.

### T1. Deterministic ordering
- publish events in known order; drain; assert subscriber saw seq order.

### T2. Ring buffer retention
- set max_events small; publish > max; assert oldest dropped and seq continues.

### T3. Kind filtering
- subscriber subscribed to certain kinds only receives those.

### T4. Deferred drain semantics
- events published during a handler do not interleave before current drain finishes (or if you allow it, test the intended behavior).

### T5. Bounded payload
- payload truncates beyond max_payload_items and marks truncated.

### T6. KPI integration smoke
- publish depot/delivery events; KPI subscriber increments values correctly.

---

## 8) Codex Instructions (verbatim)

### Task 1 — Add event bus module
- Create `src/dosadi/runtime/events.py` with WorldEvent, EventBusConfig, EventBus (ring buffer + deferred drain)

### Task 2 — Wire bus into world step loop
- Initialize `world.event_bus`
- Ensure `bus.drain()` is called at a stable boundary (end of tick or end of phase)

### Task 3 — Bridge key producers
- Publish events on: incident recorded, depot built, corridor established, delivery completed/failed, protocol authored/violated, enforcement action, construction events, scout completed

### Task 4 — Convert KPIs to subscriber
- KPI module subscribes to relevant events; keep legacy adapter in place during transition

### Task 5 — Add event viewer panel
- Add a cockpit/admin view for recent events with kind filtering

### Task 6 — Tests
- Add `tests/test_world_event_bus_v1.py` (T1–T6)

---

## 9) Definition of Done

- `pytest` passes.
- Event stream exists and is bounded.
- KPIs and Evidence can be driven primarily by events (at least for deliveries/incidents).
- Debug cockpit can show recent events.
- No new polling loops introduced.

---

## 10) Next slice after this

**D-RUNTIME-0314 Corridor Collapse Cascades v1** — make D3 harshness real:
- corridor failures compound into closures,
- supply lines break,
- enforcement decisions matter,
- and the sim can genuinely lose territory.
