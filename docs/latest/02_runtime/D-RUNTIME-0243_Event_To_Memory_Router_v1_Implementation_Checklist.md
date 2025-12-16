---
title: Event_To_Memory_Router_v1_Implementation_Checklist
doc_id: D-RUNTIME-0243
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-16
depends_on:
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-AGENT-0020     # Agent Model (STM/Episodes/Beliefs)
---

# Event → Memory Router v1 — Implementation Checklist

Branch name: `feature/event-to-memory-router-v1`

Goal: connect **world events** (incidents, phase transitions, deliveries, project milestones) to
agent **crumbs + episodes**, feeding STM and belief formation *without* blowing performance.

This is the plumbing that makes Phase 2 “feel different” because agents *remember* and adapt.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic routing.** Same seed + same world state → same agents receive the same crumbs/episodes.
2. **Bounded memory cost.** Per agent: O(1) crumbs updates; episodes are rare and capped.
3. **No global agent scans per event.** Routing uses small, precomputed “stakeholder” sets.
4. **Save/Load compatible.** Event log cursor + agent memory state persist and replay identically.
5. **Performance-first STM.** Use the “boring winner” STM heap/buckets; no linear scans to evict.

---

## 1) Concept model (v1)

### 1.1 WorldEventLog (bounded ring)
A world-level ring buffer of events with stable IDs:
- Incident created/resolved
- Delivery delivered/failed/delayed
- Facility downtime/reactivation
- Project approved/staged/complete
- Phase transition

Events are written by systems; the router consumes them and updates agent memory.

### 1.2 Router strategy
Each event kind defines:
- a **stakeholder resolver** (which agents should notice),
- a **salience score** (should become episode or crumb),
- a **memory payload** (tags/counters + optional episode payload).

The router updates:
- **Crumbs** (cheap counters/tags with decay) for most events
- **Episodes** (rarer) for high-salience events, then pushes into STM via boring-winner

v1 does not need fancy natural language; store structured payloads.

---

## 2) Implementation Slice A — WorldEventLog

### A1. Create module: `src/dosadi/world/events.py`
**Deliverables**
- `class EventKind(Enum):`
  - `INCIDENT`
  - `DELIVERY_DELIVERED`
  - `DELIVERY_FAILED`
  - `DELIVERY_DELAYED`
  - `PROJECT_APPROVED`
  - `PROJECT_STAGED`
  - `PROJECT_COMPLETE`
  - `FACILITY_DOWNTIME`
  - `FACILITY_REACTIVATED`
  - `PHASE_TRANSITION`

- `@dataclass(slots=True) class WorldEvent:`
  - `event_id: str`
  - `day: int`
  - `kind: EventKind`
  - `subject_kind: str`      # "delivery" / "project" / "facility" / "phase"
  - `subject_id: str`
  - `severity: float = 0.0`  # 0..1
  - `payload: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class WorldEventLog:`
  - `max_len: int`
  - `events: list[WorldEvent]`
  - `next_seq: int`
  - `base_seq: int = 0`
  - `def append(self, e: WorldEvent) -> None`
  - `def since(self, cursor_seq: int) -> list[WorldEvent]`   # returns events with seq >= cursor_seq
  - `def signature(self) -> str`

**Implementation notes**
- Use `next_seq` to generate stable event_ids: `evt:{day}:{next_seq}`
- Keep only last `max_len` events; when trimming, increase `base_seq`.

### A2. World integration
- Add `world.event_log: WorldEventLog`
- Initialize with `max_len=5000` (or config)
- Ensure Incident Engine and Phase Engine write events here.

---

## 3) Implementation Slice B — Agent memory primitives (Crumbs + Episodes + STM)

If your existing memory system is already implemented, adapt to it. If not, implement minimal v1 stubs.

### B1. Crumbs
Create/ensure module: `src/dosadi/agent/memory_crumbs.py`
- `@dataclass(slots=True) class CrumbCounter:`
  - `count: int`
  - `last_day: int`
- `@dataclass(slots=True) class CrumbStore:`
  - `tags: dict[str, CrumbCounter]`
  - `last_decay_day: int = 0`
  - `def bump(tag: str, day: int, inc: int = 1) -> None`
  - `def maybe_decay(day: int, half_life_days: int) -> None` (bounded; see section 6)

### B2. Episodes
Create/ensure module: `src/dosadi/agent/memory_episodes.py`
- `@dataclass(slots=True) class Episode:`
  - `episode_id: str`
  - `day: int`
  - `kind: str`
  - `salience: float`
  - `payload: dict[str, object]`

- `@dataclass(slots=True) class EpisodeBuffer:`
  - `daily: list[Episode]`
  - `def add(ep: Episode) -> None`

### B3. STM (boring-winner)
Create/ensure module: `src/dosadi/agent/memory_stm.py`
- `@dataclass(slots=True) class STMItem:`
  - `episode_id: str`
  - `score: float`
  - `day: int`

- `@dataclass(slots=True) class STMBoringWinner:`
  - `k: int`
  - `items: list[STMItem]`       # a min-heap by score
  - `def consider(ep: Episode) -> bool`  # push if better than min; return True if stored
  - `def signature(self) -> str`

Key properties:
- **no linear scans** to evict;
- O(log K) insert/evict.

---

## 4) Implementation Slice C — Router core

### C1. Create module: `src/dosadi/runtime/event_to_memory_router.py`
**Deliverables**
- `@dataclass(slots=True) class RouterConfig:`
  - `enabled: bool = True`
  - `max_events_per_day: int = 500`        # safety
  - `episode_salience_threshold: float = 0.65`
  - `stm_k: int = 24`
  - `crumb_half_life_days: int = 30`
  - `max_stakeholders_per_event: int = 20` # bound fan-out

- `@dataclass(slots=True) class RouterState:`
  - `cursor_seq: int = 0`
  - `last_run_day: int = -1`

- `def run_router_for_day(world, *, day: int) -> None`:
  1) pull events since cursor
  2) for each event, resolve stakeholders (bounded)
  3) compute salience
  4) apply crumbs/episodes
  5) advance cursor

### C2. Stakeholder resolvers (v1)
Implement small, deterministic stakeholder sets per event kind:

- Delivery events:
  - if you have courier agent id: include them
  - include project overseer (if exists) or project staffing agents (up to N)
  - include ward steward (optional)
  - fallback: no stakeholders (but still goes to world log)

- Project milestone:
  - include assigned project workers (from workforce ledger)
  - include planner/overseer agent if exists

- Facility downtime/reactivation:
  - include facility staff assignments
  - include maintenance supervisor (optional)

- Incident:
  - resolve based on incident target kind:
    - delivery → as delivery
    - facility → as facility
    - agent → that agent

- Phase transition:
  - v1: do NOT notify all agents (too broad)
  - notify a bounded set:
    - council/steward agents if you have them; else
    - top-N agents by id (deterministic “leaders list” placeholder)

**Important:** never broadcast to all agents in v1.

### C3. Salience model (cheap)
Compute a float 0..1:
- base by event kind:
  - DELIVERY_FAILED: 0.8
  - FACILITY_DOWNTIME: 0.7
  - INCIDENT: map from incident severity
  - PROJECT_COMPLETE: 0.5
- add modifiers:
  - if stakeholder is directly assigned to target: +0.1
  - if event severity high: +0.1
Clamp 0..1.

### C4. Crumb tagging scheme (v1 stable)
Use stable string tags:
- delivery failed: `delivery-fail:{delivery_id}`
- route risk (if edge known): `route-risk:{edge_key}`
- facility downtime: `facility-down:{facility_id}`
- incident: `incident:{incident_kind}:{target_id}`
- phase: `phase:{from}->{to}` (only for notified leaders)

Crumbs are cheap and can be used later for beliefs.

### C5. Episode creation (rare)
If salience >= threshold:
- create Episode with `episode_id = "ep:{agent_id}:{event_id}"`
- payload includes: event kind, subject_id, severity, day
- add to agent daily buffer and consider for STM via boring-winner

---

## 5) Runtime integration order

Daily macro-step order recommendation:
1. facilities/projects/logistics update
2. phase engine update (writes phase transition events)
3. incident engine (writes incident events)
4. **router** consumes events and updates memories
5. (optional) daily consolidation / belief formation later

Router must run once per day and be idempotent (cursor-driven).

---

## 6) Crumb decay (bounded)

Do not decay by iterating all crumb tags daily.
Use one of these v1 approaches:

**Option A (recommended): periodic decay cadence**
- every N days (e.g. 7), decay each agent’s crumbs once.
- Agents with no crumbs skip.

**Option B: lazy decay on access**
- store `last_decay_day` on CrumbStore.
- when bumping a tag, apply decay for that agent first if needed.

Keep it O(#crumb_tags_for_that_agent).

---

## 7) Save/Load integration

Serialize:
- world.event_log (or enough to resume cursor safely)
- router state cursor_seq
- agent crumb stores + episode buffers + STM

**Important:** if event_log is a ring buffer, cursor must be robust to trimming.
v1 approach:
- store `base_seq` in WorldEventLog
- on load, if cursor < base_seq, set cursor = base_seq (dropping old events deterministically)

---

## 8) Tests (must-have)

Create `tests/test_event_to_memory_router.py`.

### T1. Deterministic routing
- Same seed + same events list → same crumbs and episode signatures.

### T2. Bounded fan-out
- Event with huge stakeholder candidates → router caps at max_stakeholders_per_event.

### T3. STM boring-winner behavior
- Feed many episodes with varying salience; ensure:
  - STM size capped at K
  - top-K salience retained deterministically.

### T4. Cursor correctness
- Run router twice on same day → no double application (idempotent via cursor).

### T5. Snapshot stability
- Save after processing some events, load, continue; no duplicates and same final signatures.

### T6. Ring buffer trimming
- Trim event_log and ensure cursor adjusts safely without crashing or reprocessing.

---

## 9) “Codex Instructions” (verbatim)

### Task 1 — Add WorldEventLog
- Create `src/dosadi/world/events.py` with EventKind, WorldEvent, WorldEventLog
- Add `world.event_log` initialization (bounded ring) and signature hashing
- Update Phase Engine + Incident Engine to append events to world.event_log

### Task 2 — Implement agent memory primitives (minimal v1)
- Implement/ensure CrumbStore, EpisodeBuffer, and STMBoringWinner
- Ensure each agent has:
  - `agent.crumbs`
  - `agent.episodes_daily`
  - `agent.stm`

### Task 3 — Implement router
- Create `src/dosadi/runtime/event_to_memory_router.py` with RouterConfig/State and `run_router_for_day`
- Implement stakeholder resolution using workforce assignments and target ownership (bounded)
- Implement salience scoring, crumb tags, and episode creation
- Push episodes into STM using boring-winner heap/buckets

### Task 4 — Wire into daily stepping
- Call router once per simulated day after phase+incidents
- Ensure cursor-driven idempotence

### Task 5 — Save/Load + tests
- Serialize router cursor and event log base_seq/next_seq
- Add `tests/test_event_to_memory_router.py` implementing T1–T6

---

## 10) Definition of Done

- `pytest` passes.
- Incidents and phase transitions produce world events.
- Router deterministically routes events to bounded stakeholders.
- Agents receive crumbs; high-salience events become episodes.
- STM boring-winner keeps top-K episodes without linear scans.
- Save/load preserves router cursor and agent memory without duplication.

---

## 11) Next slice after this

**Belief formation v1** (daily buffer → belief patterns → decay),
now driven by real events and crumbs rather than placeholders.
