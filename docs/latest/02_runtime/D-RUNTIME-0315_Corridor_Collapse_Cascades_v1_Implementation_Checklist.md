---
title: Corridor_Collapse_Cascades_v1_Implementation_Checklist
doc_id: D-RUNTIME-0315
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-28
depends_on:
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0233   # Evolve Seeds Harness
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0250   # Escort Protocols v1
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0311   # Milestone KPIs & Scorecards v1
  - D-RUNTIME-0312   # Evidence Pipelines for Governance v1
  - D-RUNTIME-0313   # World Event Bus v1
  - D-RUNTIME-0314   # Deterministic RNG Service v1
---

# Corridor Collapse Cascades v1 — Implementation Checklist

Branch name: `feature/corridor-collapse-cascades-v1`

Goal: make **D3 interference harshness** real: corridors can deteriorate, become unsafe,
and eventually *collapse*, causing supply lines to break and territory to contract unless
the polity responds (escorts, repairs, reroutes, crackdown).

This slice creates the “existential corridor ecology” loop:
- risk rises → failures → reduced throughput → shortages → governance pressure → intervention
- or: risk rises → failures → abandonment → collapse → isolation → long-run fragmentation

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Bounded.** Work is O(#corridors) at low cadence; per-tick impact is O(affected routes).
2. **Deterministic.** All stochastic outcomes use RNGService streams (0314).
3. **Event-driven.** Publish key events to the World Event Bus (0313).
4. **Explainable.** Admin view can explain *why* a corridor collapsed.
5. **Recoverable.** Corridors can be stabilized (repairs, escorts, enforcement).
6. **Tested.** Collapse happens under stress; doesn’t happen under normal conditions.

---

## 1) Concept model

Each corridor has a **health state** and **risk state**.

- **Health**: structural + logistical viability (0..1)
- **Risk**: expected loss / danger (0..1)
- **Throughput capacity**: deliveries per day allowed (scaled by health)
- **Interference pressure**: composite pressure from antagonists / raiders / predators / corruption
- **Maintenance / enforcement investment**: dampens pressure and restores health

A corridor collapse is:
- health falls below threshold for long enough, OR
- cumulative “fatal incidents” exceed threshold, OR
- abandonment: throughput drops to ~0 while risk stays high.

---

## 2) Data structures

Create `src/dosadi/runtime/corridor_cascade.py` (or extend existing corridor module if present).

### 2.1 Corridor state extension

Add fields to your existing `Corridor` / `Route` record (names adapt to current codebase):

- `health: float = 1.0`               # 0..1
- `risk: float = 0.0`                 # 0..1
- `pressure: float = 0.0`             # 0..1 (from antagonists/interference)
- `maintenance_debt: float = 0.0`     # accumulates when under-maintained
- `collapse_status: str = "ACTIVE"`   # ACTIVE|DEGRADED|CLOSED|COLLAPSED
- `days_degraded: int = 0`
- `days_closed: int = 0`
- `recent_failures_7d: int = 0`
- `recent_success_7d: int = 0`
- `last_event_day: int = -1`

### 2.2 Config

- `@dataclass(slots=True) class CorridorCascadeConfig:`
  - `enabled: bool = True`
  - `update_cadence_days: int = 1`          # daily update
  - `risk_window_days: int = 7`
  - `health_decay_base: float = 0.002`      # per day
  - `health_repair_base: float = 0.004`     # per day when invested
  - `degraded_threshold: float = 0.55`
  - `closed_threshold: float = 0.35`
  - `collapse_threshold: float = 0.20`
  - `collapse_days: int = 7`                # days below threshold to collapse
  - `abandonment_days: int = 14`            # near-zero throughput days to collapse
  - `escort_effect: float = 0.20`           # escorts reduce effective risk
  - `enforcement_effect: float = 0.15`      # policing reduces pressure
  - `maintenance_effect: float = 0.25`      # investment reduces maintenance_debt
  - `rng_stream_prefix: str = "corridor:"`

World:
- `world.corridor_cascade_cfg`
- No new huge collections; reuse corridor registry.

---

## 3) Daily corridor update

Add a daily update function:
- `update_corridor_cascades(world, day)`

For each corridor:

### 3.1 Compute effective pressure
Combine sources (bounded, use caches / evidence):
- interference module (A1/A2/A3 when present) provides `corridor_pressure[corridor_id]` (0..1)
- local incidents and delivery failures adjust pressure (+)
- enforcement presence reduces pressure (-)
- escort policy reduces **risk**, not pressure (risk mitigation vs root cause)

Example:
- `pressure = clamp01(base_pressure + k_fail*fail_rate - k_enforce*enforcement_presence)`

### 3.2 Update risk
- `risk = clamp01(w1*pressure + w2*maintenance_debt + w3*terrain_hazard)`  
terrain_hazard can be a constant until hazard fields exist.

### 3.3 Update health + maintenance debt
Health decays with pressure and low maintenance:
- `maintenance_debt += debt_gain * pressure - debt_reduction * maintenance_investment`
- `health -= health_decay_base * (1 + pressure + maintenance_debt)`
- `health += health_repair_base * maintenance_investment`
Clamp to [0,1].

### 3.4 Status transitions
- if `health < degraded_threshold` → DEGRADED
- if `health < closed_threshold` → CLOSED (deliveries disallowed unless emergency + escorts)
- if `health < collapse_threshold` for `collapse_days` OR abandonment for `abandonment_days` → COLLAPSED

Track consecutive days under thresholds.

### 3.5 Emit events
Publish to event bus:
- `CORRIDOR_DEGRADED`
- `CORRIDOR_CLOSED`
- `CORRIDOR_COLLAPSED`
Payload includes:
- corridor_id
- health, risk, pressure
- recent_failures_7d
- dominant reason codes (PRESSURE, MAINT_DEBT, ABANDONMENT)

Also record an Incident (0242) for collapse/closure:
- kind: `CORRIDOR_CLOSED` / `CORRIDOR_COLLAPSED`
- severity proportional to affected throughput and connected depots.

Update KPIs:
- `logistics.routes_active`, `logistics.corridors_established`
- add new KPI(s) if desired later:
  - `logistics.corridors_collapsed`

---

## 4) Delivery-time effects

Modify logistics delivery planning/execution:

- If corridor status CLOSED:
  - block normal deliveries; allow only if `escort_required=True` and `priority>=EMERGENCY`
- If corridor DEGRADED:
  - reduce throughput / increase delay and failure probability
- If corridor COLLAPSED:
  - corridor removed from routing graph; must reroute or fail.

Use deterministic RNG for stochastic delivery outcomes:
- stream: `corridor:delivery_outcome`
- scope: `{day, delivery_id, corridor_id}`

Failure probability example:
- `p_fail = clamp01(risk * (1 - escort_mitigation))`
Escort mitigation:
- `escort_mitigation = escort_effect * escort_strength` (0..1)

Publish events:
- `DELIVERY_FAILED` with reason including corridor_id.

---

## 5) Response levers (how the polity fights back)

Expose knobs that existing modules can adjust:

1) **Escort policy** (0250/0261)
- raising escort allocation reduces effective risk but increases cost and maybe slows throughput.

2) **Maintenance projects** (corridor improvements 0267)
- corridor repair projects directly boost health and reduce debt.

3) **Enforcement posture** (0265)
- more patrols/checkpoints reduce pressure.

4) **Crackdowns** (0277)
- targeted actions reduce pressure short-term but can raise grievance (if that system exists).

These are controlled by governance via evidence:
- `evidence.corridor_risk.topk` identifies candidates.
- policy chooses “repair vs escort vs crackdown.”

v1 just provides the corridor-side mechanics and expects existing planners to call:
- `allocate_maintenance_investment(corridor_id, amount)`
- `set_escort_policy(corridor_id, escort_level)`
- `set_enforcement_presence(corridor_id, presence_level)`

Stub these as fields if planners don’t exist yet.

---

## 6) Admin views

Add to cockpit:
- corridor table (TopK by risk)
- status, health, risk, pressure, days degraded/closed
- “collapse reason” breakdown (reason codes)
- sparkline (optional) of health last 14 days (bounded list in corridor notes)

---

## 7) Tests (must-have)

Create `tests/test_corridor_collapse_cascades_v1.py`.

### T1. Collapse occurs under sustained pressure
- Setup: corridor with high base pressure, no maintenance, no enforcement
- Simulate N days; assert status transitions ACTIVE→DEGRADED→CLOSED→COLLAPSED.

### T2. Maintenance prevents collapse
- Same scenario but apply maintenance investment; corridor remains ACTIVE/DEGRADED but not COLLAPSED.

### T3. Escorts reduce delivery failure probability deterministically
- With same seed, compare failure counts with escort_level=0 vs escort_level>0; escorted has fewer failures.

### T4. Enforced reduction reduces pressure and improves health
- Apply enforcement presence; health decays slower and risk lower.

### T5. Event bus emission
- Assert corridor close/collapse publishes expected events with bounded payload.

### T6. Determinism
- Run twice with same seed; corridor status timeline identical.

---

## 8) Codex Instructions (verbatim)

### Task 1 — Add cascade config and corridor fields
- Add `CorridorCascadeConfig` and wire into world
- Extend corridor state with health/risk/pressure/maintenance_debt/status counters

### Task 2 — Implement daily update
- Implement `update_corridor_cascades(world, day)` with deterministic RNG usage
- Emit events `CORRIDOR_DEGRADED/CLOSED/COLLAPSED` and record incidents

### Task 3 — Wire into daily cadence
- Call cascade update at day rollover (phase engine or daily cadence hook)

### Task 4 — Integrate with delivery outcomes and routing
- Respect corridor status in routing
- Apply risk-based failure probability using RNGService
- Publish `DELIVERY_FAILED` reasons and update KPIs

### Task 5 — Admin views
- Add corridor risk/status panel and reason codes view

### Task 6 — Tests
- Add `tests/test_corridor_collapse_cascades_v1.py` (T1–T6)

---

## 9) Definition of Done

- `pytest` passes.
- Corridors can degrade, close, and collapse deterministically.
- Collapse affects routing and causes shortages downstream.
- Governance has clear evidence to respond to and levers to apply.
- Admin views can explain collapse causes with concrete numbers.

---

## 10) Next slice after this

**D-RUNTIME-0316 Well Depletion & Water Carrying Capacity v1** — A1 becomes existential:
- the Well is finite (or throughput-limited),
- water politics become real,
- and growth forces rationing and conflict.
