---
title: Faction_Interference_v1_Implementation_Checklist
doc_id: D-RUNTIME-0264
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0249   # Local Interactions v1
  - D-RUNTIME-0250   # Escort Protocols v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0263   # Economy Market Signals v1
---

# Faction Interference v1 — Implementation Checklist

Branch name: `feature/faction-interference-v1`

Goal: introduce a bounded, deterministic layer of *predation and sabotage* that targets:
- high-urgency materials,
- high-value corridors (risk hot edges),
- depots and construction staging sites,
and creates pressures that:
- increase corridor risk,
- motivate escorts,
- seed beliefs/rumors,
- create emergent security dynamics.

This is the first step toward Phase 2 “scarcity and corruption”.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same interference events.
2. **Bounded.** No scanning all agents or all edges; use TopK targets from telemetry.
3. **Configurable intensity.** Phase-based rates; default low.
4. **No deus-ex-machina.** Losses/thefts must come from concrete transfers (remove inventory) or explicit sabotage effects.
5. **Counterplay.** Escorts and security reduce probability and severity.
6. **Save/Load safe.** Interference state serializes; old snapshots load.
7. **Tested.** Rate caps, determinism, escort mitigation, snapshot roundtrip.

---

## 1) Concept model

We model “faction interference” as a small set of **Incident Engine templates** that are triggered by
a scheduler using world signals.

Core v1 incident types:
- `THEFT_CARGO` — steal some material from a delivery payload
- `THEFT_DEPOT` — steal from a depot inventory
- `SABOTAGE_PROJECT` — delay/ruin progress on a construction stage
- `INTIMIDATION_ESCORT` — reduces escort effectiveness (optional)
- `INFORMATION_LEAK` — creates rumor crumbs (optional)

v1 can start with 3: THEFT_CARGO, THEFT_DEPOT, SABOTAGE_PROJECT.

---

## 2) Target selection (bounded)

Use telemetry TopK as target feeders:

### Targets
- Top urgent materials (from market signals)
- Top risky corridors (from corridor risk)
- Top blocked projects (from construction pipeline v2)
- Depots with chronic shortages (from stockpile shortfalls)

Build a bounded “target basket” daily:
- max 30 targets

Each target is a structured object:
- kind: `delivery|depot|project|corridor`
- id: delivery_id / depot_id / project_id / edge_key
- value: urgency or risk score
- payload: material focus if applicable

Deterministic ordering: sort by (value desc, kind order, id asc).

---

## 3) Interference scheduler

Create `src/dosadi/runtime/faction_interference.py`

**Deliverables**
- `@dataclass(slots=True) class InterferenceConfig:`
  - `enabled: bool = False`
  - `base_events_per_day: float = 0.1`          # expected rate (low)
  - `phase_multiplier: dict[str,float] = {"P0":0.2,"P1":1.0,"P2":2.5}`
  - `max_events_per_day: int = 3`
  - `target_cap: int = 30`
  - `min_days_between_hits_same_target: int = 7`
  - `escort_mitigation_per_guard: float = 0.20` # reduces probability/severity
  - `deterministic_salt: str = "interference-v1"`

- `@dataclass(slots=True) class InterferenceState:`
  - `last_run_day: int = -1`
  - `events_spawned_today: int = 0`
  - `recent_target_hits: dict[str,int] = field(default_factory=dict)`  # target_id -> last_day_hit

World stores:
- `world.intf_cfg`, `world.intf_state`

Snapshot them.

---

## 4) Deterministic “randomness” (important)

We must generate events without nondeterministic RNG.

Implement:
- `def pseudo_rand01(key: str) -> float`
  - use stable hash (sha256) → int → /2**64

Use key pattern:
- `f"{deterministic_salt}|day:{day}|target:{target_id}|slot:{k}"`

So “dice rolls” are stable.

---

## 5) Event spawning rule

Compute expected events per day:
- `rate = base_events_per_day * phase_multiplier[current_phase]`

Then deterministically decide how many to spawn:
- Option A: `n = floor(rate)` plus a fractional check using pseudo_rand01
- Option B: cap at max_events_per_day and use pseudo_rand01 to decide each “slot”

Recommended:
- for slot in range(max_events_per_day):
  - if pseudo_rand01(day,slot) < rate/max_events_per_day: spawn one event

Choose targets for each spawned event:
- iterate target basket in order
- pick first eligible target not hit recently
- if none: stop early

---

## 6) Incident templates and effects

### 6.1 THEFT_CARGO
Trigger condition:
- target kind = delivery
or select delivery carrying high-urgency materials.

Effect:
- remove qty from delivery payload before completion, or on an “intercept” step.
- transfer to “shadow stockpile” owner (optional) or just destroy as loss.

Severity:
- base severity proportional to material urgency
- mitigated by escorts:
  - `severity *= clamp(1 - escorts*escort_mitigation_per_guard, 0.2, 1.0)`

### 6.2 THEFT_DEPOT
Trigger:
- target kind = depot
- high urgency materials below min (makes it hurt)

Effect:
- remove a bounded quantity from depot inventory:
  - e.g., min(available, batch) where batch derived from urgency.

### 6.3 SABOTAGE_PROJECT
Trigger:
- target kind = project (especially near completion or high-value facility kind)

Effect options (choose 1 for v1):
- add downtime days (pause stage for N days)
- reduce progress_days_in_stage by X (bounded)
- consume extra materials (simulate ruined batch) — only if you can cleanly implement.

Recommended v1: **downtime** via incident engine pause.

---

## 7) Integration with Incident Engine + Corridor risk

Implement incident creation:
- `incident_engine.spawn(kind, target_ref, payload, day)`

After incident resolves (or immediately on spawn), notify corridor risk:
- incidents on a corridor edge should increase risk score
- theft on delivery that has a route → apply to hottest edge on the route (or first edge)

Ensure this is deterministic:
- choose edge by max risk tie-break by edge_key.

---

## 8) Memory + beliefs + rumors

Emit crumbs (low-cost):
- `rumor:theft:{ward_id}`
- `rumor:sabotage:{facility_kind}:{ward_id}`
- `threat:edge:{edge_key}`

Belief formation can promote these into:
- “This corridor is dangerous”
- “Depot X is raided”
- “Faction Y controls route Z” (future)

v1 doesn’t need real factions yet; treat it as “shadow interference”.

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["interference"]["spawned"]`
- `metrics["interference"]["theft_units_total"]`
- `metrics["interference"]["sabotage_days_total"]`
- TopK:
  - `interference.targets_hit` (by urgency/risk)
  - `interference.materials_stolen` (by qty)

Cockpit additions:
- Recent interference events (last 10)
- Top targets hit

---

## 10) Tests (must-have)

Create `tests/test_faction_interference_v1.py`.

### T1. Determinism
- clone world; run N days; same spawned events and same losses.

### T2. Caps enforced
- max_events_per_day respected.

### T3. Cooldown per target
- same depot cannot be hit twice within min_days_between_hits.

### T4. Escort mitigation
- identical delivery with escorts steals less / triggers less often (deterministically via severity reduction).

### T5. Inventory conservation
- theft reduces inventory (delivery/depot) by expected amount; no negatives.

### T6. Risk integration
- theft incidents on corridor edge increase risk record.

### T7. Snapshot roundtrip
- save mid-state; load; continue; stable.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add interference module + state
- Create `src/dosadi/runtime/faction_interference.py` with config/state/target selection
- Add world.intf_cfg/world.intf_state to snapshots

### Task 2 — Deterministic event spawning
- Implement stable pseudo_rand01 based on sha256
- Spawn up to max_events_per_day using phase-scaled rate
- Choose targets from bounded telemetry baskets with cooldown per target

### Task 3 — Implement incidents
- Add THEFT_CARGO, THEFT_DEPOT, SABOTAGE_PROJECT templates using Incident Engine
- Apply concrete effects: remove materials or add downtime

### Task 4 — Mitigation + risk + memory
- Reduce probability/severity by escort count
- Feed incidents into corridor risk updates
- Emit rumor/threat crumbs and telemetry counters/topK

### Task 5 — Tests
- Add `tests/test_faction_interference_v1.py` (T1–T7)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - occasional theft/sabotage events spawn deterministically,
  - escorts reduce losses,
  - corridor risk rises in response,
  - cockpit shows recent interference and targets,
  - beliefs/rumors receive crumbs,
  - save/load works.

---

## 13) Next slice after this

**Real Factions v1** (named groups with territory + budgets) *or*
**Law & Enforcement v1** (wards invest in patrols, checkpoints, and penalties).
