---
title: Incident_Engine_v1_Implementation_Checklist
doc_id: D-RUNTIME-0242
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-16
depends_on:
  - D-RUNTIME-0231   # Save/Load + Seed Vault + Deterministic Replay
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0234   # Survey Map v1 (optional: hazards)
  - D-RUNTIME-0238   # Logistics Delivery v1
  - D-RUNTIME-0240   # Workforce Staffing v1
  - D-RUNTIME-0241   # Phase Engine v1
  - D-AGENT-0020     # Agent model (episodes/crumbs hooks if present)
---

# Incident Engine v1 — Implementation Checklist

Branch name: `feature/incident-engine-v1`

Goal: introduce a deterministic, bounded **incident/event system** that provides “texture” and consequences
(especially in Phase 2) while feeding **crumbs/episodes** for agent memory and belief formation.

v1 focuses on incidents that are:
- easy to model deterministically,
- cheap to simulate under macro-step,
- impactful to logistics/projects/facilities.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic outcomes.** Same seed + same world state → same incidents and outcomes.
2. **Bounded compute.** O(#incidents_due + #active_targets) per day; no global scans.
3. **Phase-aware rates.** Incidents are rare in Phase 0, more common in Phase 2.
4. **Save/Load compatible.** Scheduled incidents, history, and any derived RNG must persist.
5. **Testable.** Incidents can be forced via config for unit tests.

---

## 1) Concept model (v1)

An Incident is a scheduled event that:
- targets a system entity (delivery, facility, project, ward, agent),
- occurs on a specific day (or tick),
- applies deterministic effects (loss, downtime, delay),
- emits a memory “signal” (crumb/episode) to affected agents or to the world log.

v1 incident kinds:
1. **DeliveryLoss**: a shipment fails or is partially lost
2. **DeliveryDelay**: shipment arrives later than planned
3. **FacilityDowntime**: facility goes inactive for N days (maintenance/sabotage)
4. **WorkerInjury** (optional): removes an agent from labor pool for N days (lightweight)

Keep v1 minimal; add richer incidents later.

---

## 2) Implementation Slice A — Types + ledger

### A1. Create module: `src/dosadi/world/incidents.py`
**Deliverables**
- `class IncidentKind(Enum): DELIVERY_LOSS, DELIVERY_DELAY, FACILITY_DOWNTIME, WORKER_INJURY`
- `@dataclass(slots=True) class Incident:`
  - `incident_id: str`
  - `kind: IncidentKind`
  - `day: int`
  - `target_kind: str`       # "delivery" / "facility" / "project" / "agent" / "ward"
  - `target_id: str`
  - `severity: float`        # 0..1
  - `payload: dict[str, object] = field(default_factory=dict)`  # e.g. delay_days
  - `created_day: int = 0`
  - `resolved: bool = False`
  - `resolved_day: int | None = None`

- `@dataclass(slots=True) class IncidentLedger:`
  - `scheduled: dict[int, list[str]]`     # day -> incident_ids (stable order)
  - `incidents: dict[str, Incident]`
  - `history: list[str]`                 # incident_ids in resolution order
  - `def add(self, inc: Incident) -> None`
  - `def due_ids(self, day: int) -> list[str]`
  - `def signature(self) -> str`

### A2. World integration
- Add `world.incidents: IncidentLedger`
- Add `world.incident_cfg: IncidentConfig` and `world.incident_state: IncidentState`

---

## 3) Implementation Slice B — Config + scheduling (phase-aware)

### B1. Create module: `src/dosadi/runtime/incident_engine.py`
**Deliverables**
- `@dataclass(slots=True) class IncidentConfig:`
  - `enabled: bool = True`
  - `max_incidents_per_day: int = 2`
  - `history_limit: int = 2000`
  - Phase-scaled rates (per target per day):
    - `p_delivery_loss_p0: float = 0.000`
    - `p_delivery_loss_p1: float = 0.002`
    - `p_delivery_loss_p2: float = 0.010`
    - `p_delivery_delay_p2: float = 0.020`
    - `p_facility_downtime_p2: float = 0.005`
  - Severity ranges:
    - `delay_days_min: int = 1`
    - `delay_days_max: int = 5`
    - `downtime_days_min: int = 2`
    - `downtime_days_max: int = 10`

- `@dataclass(slots=True) class IncidentState:`
  - `last_run_day: int = -1`

- `def run_incident_engine_for_day(world, *, day: int) -> None`
  1) schedule new incidents (bounded)
  2) resolve due incidents
  3) append to history + emit memory signals

### B2. Deterministic RNG
All incident scheduling and effects must use derived RNG seeds:
- day-seed = hash(world.seed, day, "incident-engine")
- per-target seed = hash(world.seed, day, target_id, kind)

This makes results stable even if target iteration order changes.

### B3. Target sampling (bounded)
Do not iterate over “everything” to roll dice.
Pick bounded candidate sets each day:
- deliveries: consider up to K active deliveries (REQUESTED/ASSIGNED/PICKED_UP/IN_TRANSIT)
- facilities: consider up to K active facilities
- agents: only those assigned to BUILDING projects (optional)

K can be `max_incidents_per_day * 10` as a simple bound.

---

## 4) Implementation Slice C — Resolution effects

### C1. DeliveryLoss
Target: `DeliveryRequest`
Effect:
- If delivery is in transit or assigned:
  - mark `status=FAILED` (or new LOST)
  - remove in-transit inventory (or optionally return some fraction)
  - do not credit the project buffer
- Record payload:
  - `lost_items` dict (deterministic fraction based on severity)

### C2. DeliveryDelay
Effect:
- Add `delay_days` (deterministic integer within min/max)
- Convert to ticks: `deliver_tick += delay_days * ticks_per_day`
- Ensure due-queue reconstruction handles updated deliver_tick.

### C3. FacilityDowntime
Target: `Facility`
Effect:
- set `facility.status="INACTIVE"` and `facility.state["reactivate_day"]=day+downtime`
- facility update loop should skip inactive facilities
- add a reactivation check (either in facility updates or as a scheduled incident)

### C4. WorkerInjury (optional v1)
Target: `agent_id`
Effect:
- workforce ledger: set assignment to IDLE (or INJURED kind) until `recover_day`
- reduces available labor pool
- keep it macro; no physiology integration required.

---

## 5) Memory/Telemetry emission (crumbs/episodes)

v1: keep this minimal and non-invasive.
Emit a world event record (bounded ring) that later can be routed to agents:
- `world.events.append({"day": day, "kind": "INCIDENT", "incident_id": ..., ...})`

If your crumbs/episodes system already exists, also emit:
- a **crumb** to affected agents (couriers, project overseers, facility staff, etc. if identifiable).
If not, storing in the world event log is enough for v1.

---

## 6) Runtime integration order

Recommended daily order:
1. Projects / logistics / facilities update
2. Phase engine updates + policy hooks
3. **Incident Engine** schedules/resolves incidents for the day

Choose one consistent ordering and test it.

---

## 7) Save/Load integration

- Serialize IncidentLedger + IncidentState
- If you reconstruct any due-queues (logistics), ensure incident-modified deliver_tick persists and reconstruction reads it.

Snapshot roundtrip must preserve:
- scheduled incidents
- resolved incidents history
- no duplicate resolution after load

---

## 8) Tests (must-have)

Create `tests/test_incident_engine.py`.

### T1. Deterministic scheduling
- With fixed seed and forced nonzero probabilities, run 30 days twice → identical incident ledger signature.

### T2. Max incidents per day bound
- Configure high rates, ensure incidents/day <= max_incidents_per_day.

### T3. Delivery loss effect
- Create an in-transit delivery, force a loss incident, run day, assert delivery becomes FAILED and project buffer unchanged.

### T4. Delivery delay effect
- Create delivery with deliver_tick, force delay, ensure deliver_tick increases by expected amount.

### T5. Facility downtime effect + reactivation
- Create facility active, force downtime for N days, ensure:
  - inactive during downtime days
  - reactivates on reactivate_day

### T6. Snapshot stability
- Save mid-schedule, load, continue; ensure no duplicates and same history.

### T7. Phase awareness
- In Phase 0, with p0 rates, expect zero (or near-zero) incidents over short run.
- In Phase 2, expect at least one incident over same run with test config.

---

## 9) “Codex Instructions” (verbatim)

### Task 1 — Add incidents ledger + types
- Create `src/dosadi/world/incidents.py` with `IncidentKind`, `Incident`, `IncidentLedger`
- Add `world.incidents` initialization and deterministic `signature()`

### Task 2 — Implement incident engine runtime
- Create `src/dosadi/runtime/incident_engine.py` with IncidentConfig/State and `run_incident_engine_for_day`
- Use derived deterministic RNG seeds (world.seed + day + target_id) so order changes don’t affect results
- Enforce `max_incidents_per_day` and bounded candidate sets

### Task 3 — Add resolution effects
- Implement effects for:
  - DELIVERY_LOSS (mark delivery failed; apply deterministic loss)
  - DELIVERY_DELAY (increase deliver_tick deterministically)
  - FACILITY_DOWNTIME (inactive until reactivate_day)
  - (optional) WORKER_INJURY

### Task 4 — Wire into daily stepping
- Call incident engine once per day in macro-step and tick-mode daily hooks
- Ensure consistent ordering relative to phase/planner/logistics

### Task 5 — Save/Load + tests
- Serialize incident ledger/state in snapshots
- Add `tests/test_incident_engine.py` implementing T1–T7

---

## 10) Definition of Done

- `pytest` passes.
- Incidents are deterministic, phase-aware, and bounded per day.
- Incidents produce visible consequences (delays, failures, downtime).
- Save/load preserves scheduled/resolved incidents without duplicates.
- Evolve harness runs show Phase 2 texture without destabilizing determinism.

---

## 11) Next slices after this

1. Crumbs+Episodes integration pass (route incident events into agent memory)
2. Corruption & shadow economy hooks (Phase 2 amplifiers)
3. Focus mode for “awake” agents (zoom into a ward or mission)
