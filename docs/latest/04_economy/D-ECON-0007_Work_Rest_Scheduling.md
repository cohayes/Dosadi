---
title: Work_Rest_Scheduling
doc_id: D-ECON-0007
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-ECON-0001
---
# **Work–Rest Scheduling v1 (Heat, Fatigue, Safety, and Output)**

**Purpose:** Allocate labor minutes across tasks and venues while respecting thermal/fatigue limits, minimizing injury/clinic risk, and achieving production/escort targets. Converts physiology into planning constraints and feedback loops.

Integrates with **Agents v1**, **Suit–Body–Environment v1**, **Suit Maintenance v1**, **Environment Dynamics v1**, **Clinic Protocols v1**, **Security/Escort v1**, **Market v1**, **Credits & FX v1**, **Rumor & Perception v1**, and the **Tick Loop**.

> Timebase: `Minute = 100 ticks`. Scheduler runs **every 15 minutes** (coarse), with micro‑adjusts each minute for safety stops.

---

## 0) Core Concepts & State

- **Shift**: `{ward, venue, start_min, end_min, demand_vector, safety_policy}`

- **Task**: `{id, type: PROD|ESCORT|MAINT|CLINIC|CIVIC, venue, workload: REST|LIGHT|MODERATE|HEAVY|EXTREME, heat_idx, risk_idx, skill_req}`

- **Worker** (agent): `{affinities, skills, T_core, Stamina, MentalEnergy, Hydration_L, suit_state, reliability, risk_tolerance}`

- **Roster**: set of available workers with suitability scores per task.

- **Safety State**: rolling windows of `HeatStrain`, `Dehydration`, `CumulativeLoad`, `NearMisses`.

- **Output Model**: marginal output per minute vs workload (diminishing returns when heat/fatigue rise).

---

## 1) Constraints & Objectives

**Hard Constraints**

- Legal/contract hours, venue capacity, tool availability, escort minimums, clinic staffing floors.

- Physiological: `T_core ≤ T_core_stop`, `Dehydration < stage3`, `Stamina ≥ floor`, `Seal ≥ min`, not in clinic.

**Soft Constraints**

- Fairness (rotate hot tasks), circadian preference, reputation (avoid overworking key figures), mentorship pairing.

**Objectives (lexicographic / weighted)**

1) Meet minimum safety thresholds.  

2) Satisfy critical demand (water cascade, security lanes, clinics).  

3) Maximize expected output (production or safe delivery).  

4) Minimize expected incidents (clinic visits, maintenance overload).  

5) Balance worker fatigue/fairness.

---

## 2) Safety Policy (Heat–Work–Rest Tables)

Derived from **Suit–Body–Environment v1**. Policy yields **allowed minutes** before a mandatory rest at current `heat_idx` and workload, adjusted by suit tier.

- Table entries: `allowed_work_min(heat_idx, WL, suit_tier)` and `required_rest_min(heat_idx, WL, suit_tier)`.

- Safety stops can be preemptive if **trend** predicts crossing thresholds within next 5–10 min.

- Rest venues: prefer **SEALED_INTERIOR** recovery cells with high RH control and cold fluids (reclaim on).

---

## 3) Scheduler Mechanics (15‑min Window)

1) Build **task pool** from demand vector (production quotas, patrol routes, service queues).  

2) Score worker×task with a **composite score**: 

   `S = skill_fit × (1 + affinity_bonus) × safety_margin × reliability × (1 − heat_penalty) × fx_wage_affordability`.

3) Solve assignment (ILP/greedy with backtracking) under hard constraints and min escort/clinic floors.  

4) Insert **work–rest blocks** per worker using policy table and predicted heat strain.  

5) Emit schedules + safety timers; publish to venues and workers.

Events: `ShiftScheduled`, `WorkerAssigned`, `SafetyTimerSet`.

---

## 4) Minute Safety Loop (Micro‑Adjust)

- Pull telemetry (`T_core`, `Stamina`, `Hydration`, `Seal`, environment).  

- If any **stop condition** nears: trigger **SafetyPause** → switch to `REST` task; notify foreman.  

- If **Seal warning** or `FilterLoad` high: auto‑route to **Maintenance Quick** or **Clinic Intake** depending on symptom.

Events: `SafetyPause`, `AutoRerouteToMaintenance`, `AutoRerouteToClinic`.

---

## 5) Rest & Recovery Blocks

- **Passive Rest**: cool, hydrate `ORS`, snack (glycogen).  

- **Active Recovery**: suit flush, filter swap, TEC cool booth.  

- **Cognitive Rest**: low‑stim tasks; reduces `MentalEnergy` debt.

Recovery efficiency depends on venue class (SEALED > LEAKY > OUTSIDE) and suit state.

---

## 6) Fatigue, Reliability, and Incidents

- **Cumulative Load**: EWMA of work minutes weighted by workload; caps schedule intensity for next window.  

- **Reliability** updates with on‑time arrivals and incident history; modifies future assignment priority.  

- **NearMiss** events (slip, overheat warnings, minor breaches) increase **incident risk** until rest/maintenance.

Events: `NearMissLogged`, `ReliabilityUpdated`.

---

## 7) Output & Economic Links

- Output per minute `Out = base × f(skill) × g(fatigue, heat)`; escorts affect **loss probability** on routes.  

- **Wage premium** for hot/dirty/risky tasks; FX discount of paying issuer alters willingness to accept shifts.  

- Safety breaches raise clinic demand and maintenance load; negative rumors reduce recruitment pool.

---

## 8) Policy Knobs (defaults)

```yaml
work_rest:
  plan_interval_min: 15
  safety_thresholds:
    T_core_stop: 38.8
    stamina_floor: 0.25
    dehydration_stop_stage: 2     # 0..3
    seal_min: 0.85
  heat_table_allow_min:
    LIGHT:     [60, 45, 30, 20]   # by heat_idx bins 0..3
    MODERATE:  [45, 30, 20, 15]
    HEAVY:     [30, 20, 15, 10]
    EXTREME:   [20, 15, 10, 5]
  rest_table_req_min:
    LIGHT:     [10, 15, 20, 30]
    MODERATE:  [15, 20, 30, 40]
    HEAVY:     [20, 30, 40, 50]
    EXTREME:   [30, 40, 50, 60]
  suit_tier_bonus_allow_min: { LOW: 0, MID: 5, HIGH: 10, ELITE: 15 }
  recovery_eff:
    SEALED_INTERIOR: 1.0
    LEAKY_INTERIOR:  0.6
    OUTSIDE:         0.25
  wage_premium_hot: 0.15
  wage_premium_risk: 0.10
  fairness_window_hours: 24
```

---

## 9) Event & Function Surface (for Codex)

**Functions**

- `build_shift(ward, venue, demand_vector)` → returns tasks with loads.

- `plan_roster(shift_id, workers)` → `ShiftScheduled`; emits `WorkerAssigned` and timers.  

- `minute_safety_tick(worker_id)` → evaluates stop conditions; may emit `SafetyPause` and reroutes.  

- `start_rest(worker_id, rest_kind)` / `end_rest(worker_id)` → logs recovery and water use.  

- `update_output(venue_id)` → aggregates minute outputs and incident risks.

**Events**

- `ShiftScheduled`, `WorkerAssigned`, `SafetyTimerSet`, `SafetyPause`, `AutoRerouteToMaintenance`, `AutoRerouteToClinic`, `NearMissLogged`, `ReliabilityUpdated`.

---

## 10) Pseudocode (Planner & Safety)

```python
def plan_roster(shift, workers, policy):
    tasks = expand_tasks(shift.demand_vector)
    scores = {(w,t): score(w,t,policy) for w in workers for t in tasks}
    assign = solve(scores, constraints=policy.hard)
    for w,t in assign:
        blocks = work_rest_blocks(t, w, policy.heat_table_allow_min, policy.rest_table_req_min)
        schedule(w, t, blocks)
        emit("WorkerAssigned", {...})

def minute_safety_tick(w, env):
    telem = read_telem(w, env)
    if will_cross_threshold(telem, horizon_min=5): 
        start_rest(w, kind="safety")
        emit("SafetyPause", {...})
    if w.suit.seal < policy.seal_min or w.suit.filter_load > warn: 
        route_to_service(w)
```

---

## 11) Explainability & Rumor Hooks

- Per worker **safety card**: predicted time‑to‑threshold, last rest, hydration status, suit alerts, fairness counters.  

- **Venue dashboard**: output vs safety breaches; rumor sensitivity spikes when workers collapse on shift.  

- **Public pledge**: inner wards publish safety uptime; outer wards often hide failures → wider rumor variance.

---

## 12) Test Checklist (Day‑0+)

- Under heat_idx=3 & HEAVY workload, workers receive ≤ 10 min work blocks with ≥ 50 min rest across two cycles.  

- Safety micro‑loop preempts tasks ~5 min before reaching `T_core_stop` with high recall and few false positives.  

- Escort shifts include mandated relief windows; clinic overflows decrease when scheduling is enabled.  

- Fairness rotation prevents any worker from exceeding policy hot‑minutes within 24h.

---

### End of Work–Rest Scheduling v1
