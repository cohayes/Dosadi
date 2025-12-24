---
title: Local_Interactions_v1_Implementation_Checklist
doc_id: D-RUNTIME-0249
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-24
depends_on:
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0243   # Event → Memory Router v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0246   # Agent Courier Logistics v1
  - D-RUNTIME-0247   # Focus Mode v1
  - D-RUNTIME-0248   # Courier Micro-Pathing v1
---

# Local Interactions v1 — Implementation Checklist

Branch name: `feature/local-interactions-v1`

Goal: add a **bounded, deterministic** local interaction layer around:
- courier travel along edges,
- construction sites / project stages,
- facility downtime/maintenance hotspots,

so the simulation begins to produce *socially meaningful* incidents:
- help / assist,
- conflict / delay,
- sabotage / theft,
- escort / protection.

This is deliberately small-scope and compatible with ambient + focus mode.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed + same world state → same interaction outcomes.
2. **Bounded work.** No per-tick global scans; interactions evaluate only for active missions/sites.
3. **Stakeholder sets only.** Interaction resolution never iterates all agents; it uses a small cohort.
4. **Event-driven.** Outcomes emit WorldEvents; memory/beliefs update via router + belief formation (no direct belief mutation).
5. **Feature flag default OFF.** With flag OFF, behavior matches baseline.

---

## 1) Concept model

Local interactions happen when an “interaction opportunity” exists, typically:
- a courier is traversing an edge segment,
- a courier arrives at a node/site,
- a project stage is in-progress at a node/site,
- a facility is down and maintenance is underway.

An interaction is a small, structured record:
- who is involved (actor + target),
- where (node/edge/site),
- what kind (help/conflict/sabotage/escort),
- outcome (delay, loss, injury, morale, etc.),
- evidence tags to feed memory.

v1 uses **coarse outcomes** that primarily affect:
- delivery ETA (delay),
- delivery success (fail),
- small inventory loss (theft),
- staffing churn (minor injury/unavailability),
- event log + memory.

---

## 2) Implementation Slice A — Data structures + config

### A1. Create module: `src/dosadi/runtime/local_interactions.py`

**Deliverables**
- `class InteractionKind(Enum): HELP, CONFLICT, SABOTAGE, ESCORT`
- `@dataclass(slots=True) class InteractionConfig:`
  - `enabled: bool = False`
  - `max_interactions_per_day: int = 50`
  - `max_candidates_per_opportunity: int = 12`
  - `escort_enabled: bool = True`
  - `theft_enabled: bool = True`
  - `delay_ticks_min: int = 200`
  - `delay_ticks_max: int = 2000`
  - `sabotage_fail_chance: float = 0.35`   # deterministic “chance” via hashed draw
  - `help_reduce_delay_factor: float = 0.50`
  - `conflict_delay_factor: float = 1.25`

- `@dataclass(slots=True) class InteractionOpportunity:`
  - `day: int`
  - `tick: int`
  - `kind: str`                 # "courier_edge", "courier_arrival", "project_site", "facility_site"
  - `node_id: str | None`
  - `edge_key: str | None`
  - `primary_agent_id: str | None`   # e.g., courier
  - `subject_id: str | None`         # delivery_id/project_id/facility_id
  - `severity: float = 0.0`
  - `payload: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class InteractionResult:`
  - `interaction_id: str`
  - `kind: InteractionKind`
  - `actors: list[str]`              # agent ids
  - `node_id: str | None`
  - `edge_key: str | None`
  - `subject_id: str | None`
  - `delay_ticks: int = 0`
  - `delivery_failed: bool = False`
  - `stolen_units: int = 0`
  - `payload: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class InteractionState:`
  - `last_run_day: int = -1`
  - `count_today: int = 0`

### A2. World integration
- Add `world.interaction_cfg: InteractionConfig`
- Add `world.interaction_state: InteractionState`
- Ensure both serialize in snapshots.

---

## 3) Implementation Slice B — Deterministic “chance” (no RNG drift)

### B1. Hashed draw helper
Add helper (pure function):

`def hashed_unit_float(*parts: str) -> float`

Implementation idea:
- `sha256("|".join(parts)).hexdigest()` → take first 8 hex chars → int → / 2^32
- Deterministic across runs and independent of global RNG streams.

Use it to decide outcomes like sabotage success without consuming RNG.

---

## 4) Implementation Slice C — Opportunity sources (bounded)

We do **not** scan the world for opportunities.
We generate opportunities only from known active objects:

### C1. Courier opportunities
In courier stepping (ambient per-edge completion, focus per-tick):
- when a courier completes an edge segment (or arrives at node),
  - create an opportunity:
    - kind = `"courier_edge"` (or `"courier_arrival"`)
    - edge_key and/or node_id set
    - primary_agent_id = courier agent
    - subject_id = delivery_id
  - enqueue it into a small per-day list on world:
    - `world.interaction_queue` (bounded list)

Bound:
- add at most N opportunities per day per courier (e.g., only on edge completion, not every tick).

### C2. Project site opportunities
When a project stage is active at node/site:
- once per day (or per stage transition), create:
  - kind = `"project_site"`
  - node_id = project node
  - subject_id = project_id
This should be done by the Phase/Project Engine, not by scanning.

### C3. Facility site opportunities (optional v1)
When a facility enters downtime or reactivation:
- create `"facility_site"` opportunity once per day until resolved.

---

## 5) Implementation Slice D — Candidate selection (bounded cohorts)

### D1. Cohort resolver per opportunity
Implement:

`def resolve_candidates(world, opp: InteractionOpportunity) -> list[str]`

Rules (v1):
- Start with directly involved stakeholders:
  - courier (primary_agent_id)
  - project workers assigned to subject_id (from WorkforceLedger)
  - facility staff assignments (for facility_site)
- Add local bystanders (if location exists):
  - agents at node_id, limited to max_candidates_per_opportunity
- Deterministic order:
  - sort by agent_id and cut to max.

If location is missing/not reliable:
- use workforce assignments only (still useful).

### D2. Roles
From candidates, derive deterministic roles:
- `actor`: the primary (courier or lead worker)
- `others`: next few agents
- optionally pick one “adversary” deterministically via hashed draw:
  - `adversary = others[int(hashed*len(others))]`

---

## 6) Implementation Slice E — Interaction resolution rules (v1 simple)

### E1. When to resolve
Run interactions **once per day** after incident engine, before router:
- This allows interactions to emit events that get routed into memory that same day.

Recommended insertion:
- daily pipeline step between (3) incident engine and (4) event→memory router.

### E2. Rule set (deterministic, bounded)
For each opportunity, decide one of:
- HELP: if escort present or helper available
- CONFLICT: mild delay event
- SABOTAGE: delay + possible fail + theft
- ESCORT: reduces risk on future edges (v1: implement as crumb tag only)

Decision uses hashed draws:
- `u = hashed_unit_float("interaction", day, opp.kind, opp.subject_id, opp.edge_key, actor_id)`

Example v1 policy:
- If u < 0.10 → SABOTAGE
- elif u < 0.25 → CONFLICT
- elif u < 0.45 → HELP
- else → NO INTERACTION (skip)
Then modify by context:
- If escort present → reduce sabotage/conflict probability (shift thresholds)
- If route hazard high (edge.hazard) → increase conflict/sabotage probability

### E3. Outcome mapping
- CONFLICT:
  - `delay_ticks = clamp(int(delay_base * conflict_delay_factor), min, max)`
- HELP:
  - reduce delay (if any) or add small “speed up” (optional v1) by reducing remaining edge ticks
- SABOTAGE:
  - `delay_ticks` added
  - `sabotage_success = hashed_unit_float(...) < sabotage_fail_chance`
  - if success:
    - set `delivery_failed=True` OR `stolen_units>0` (choose one deterministically)
- ESCORT:
  - v1: no immediate mechanical effect; emit crumb tag `escort:{edge_key}` to seed later design.

All outcomes should be applied through existing APIs:
- add delay by pushing next due tick later
- fail delivery by marking failed and releasing courier
- theft as inventory delta (bounded, small)

---

## 7) Implementation Slice F — Event emission (connect to memory)

For any non-empty interaction result, append a WorldEvent:
- kind = INCIDENT (or add a new kind `LOCAL_INTERACTION` if you want)
- subject_kind = "delivery"/"project"/"facility"
- payload includes:
  - `interaction_kind`
  - `edge_key` / `node_id`
  - `actor_ids`
  - `delay_ticks`
  - `stolen_units`
  - `delivery_failed`

Router should then create crumbs:
- `route-risk:{edge_key}` for conflict/sabotage
- `delivery-fail:{delivery_id}` if failed
- `site-trouble:{node_id}` for project/facility trouble
- `helped-by:{agent_id}` (optional)

Belief formation will aggregate these into durable patterns.

---

## 8) Save/Load integration

- Serialize interaction_cfg/state.
- Serialize any per-day interaction queue if it exists mid-day (recommended).
- Ensure old snapshots load with defaults (enabled=False).

---

## 9) Telemetry

Add O(1) counters:
- `metrics["interactions"]["opportunities"]`
- `metrics["interactions"]["resolved"]`
- `metrics["interactions"]["help"]`
- `metrics["interactions"]["conflict"]`
- `metrics["interactions"]["sabotage"]`
- `metrics["interactions"]["escort"]`
- `metrics["interactions"]["delays_total_ticks"]`
- `metrics["interactions"]["deliveries_failed"]`

---

## 10) Tests (must-have)

Create `tests/test_local_interactions.py`.

### T1. Flag off = no change
- With enabled=False, running pipeline produces identical signature to baseline.

### T2. Deterministic interaction outcomes
- Same world + same opportunity list → same interaction results and event log.

### T3. Bounded candidates
- Provide a node with many agents; ensure resolver caps at max_candidates_per_opportunity.

### T4. Delay application
- Create a delivery with known next due tick; apply interaction delay; verify due tick moved later.

### T5. Failure path releases courier
- Force sabotage success; verify delivery fails and courier assignment is released.

### T6. Router integration
- After interactions emit events, router creates expected crumb tags for stakeholders.

### T7. Snapshot roundtrip mid-day
- Save after generating opportunities, load, resolve; identical final signature.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add local interaction module + world config/state
- Create `src/dosadi/runtime/local_interactions.py` with config, opportunity/result types, state
- Add `world.interaction_cfg` and `world.interaction_state` to snapshots

### Task 2 — Deterministic hashed draws
- Implement `hashed_unit_float(*parts)` helper (no global RNG consumption)

### Task 3 — Opportunity sources
- Enqueue opportunities from courier stepping (edge completion / arrival)
- Enqueue opportunities from active project/facility sites (once/day, bounded)

### Task 4 — Candidate selection + resolution
- Resolve bounded cohorts from workforce + location (if present)
- Resolve interactions once per day in the pipeline (between incident engine and router)
- Apply outcomes through existing APIs (delay/fail/theft) and emit WorldEvents

### Task 5 — Tests + telemetry
- Add counters and `tests/test_local_interactions.py` (T1–T7)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=False, no behavior change.
- With enabled=True, interactions produce deterministic events and bounded effects.
- Deliveries can be delayed/failed via local interactions; couriers always released on terminal states.
- Events flow through router → memory → beliefs without direct mutation.
- Save/load works mid-day.

---

## 13) Next slice after this

**Escort Protocols v1** (formalize “convoy/escort” as a staffing + logistics policy),
using beliefs (route-risk) to request escorts on dangerous corridors.
