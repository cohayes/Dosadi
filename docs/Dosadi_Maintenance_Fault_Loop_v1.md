# **Maintenance Fault Loop v1**

Closed-loop model for infrastructure wear, faults, detection, repair, and systemic effects.  
Integrates with **Environment Dynamics v1**, **Worldgen v1**, **Agent Action API v1** (`MaintainFacility`, `InstallComponent`), **Security Loop v1**, **Market Microstructure v1**, **Barrel Cascade v1**, and the **Tick Loop**.

> Cadence: wear updates each **MinuteTick**; inspections queue **Tasks**; repairs change facility KPIs immediately on completion.

---

## 0) Goals

1. **Physicality** — facilities have components with health, wear, and operating regimes.  
2. **Actionable** — faults emit tasks that agents/guilds can pick up; upgrades change failure rates.  
3. **Systemic Effects** — faults affect leakage, power, risk, prices, and legitimacy.  
4. **Explainable** — each outage traces to components, usage, and maintenance debt.

---

## 1) Facility Model

Each **Facility** (Reservoir, Reclaimer, Kitchen, Power, Workshop, Clinic, Gate/Checkpoint, HVAC/Canopy) holds **Components**:

```json
{
  "facility_id": "fac_011",
  "type": "RESERVOIR|RECLAIMER|POWER|KITCHEN|WORKSHOP|CLINIC|GATE|HVAC",
  "M": 0.82,                          // overall maintenance score [0,1]
  "state": "ONLINE|DEGRADED|OFFLINE",
  "components": [
    {
      "cid":"cmp_pump_A",
      "kind":"PUMP|SEAL|FILTER|VALVE|MEMBRANE|GENSET|HEAT_EXCH|CAMERA|LOCK",
      "H":0.74,                        // component health [0,1]
      "wear":0.26,                     // cumulative wear
      "mtbf_min": 18000,               // baseline mean-time-between-failure (minutes)
      "mttr_min": 240,                 // mean-time-to-repair (minutes)
      "stress": 1.0,                   // multiplier from load/heat/dust
      "fault_state":"OK|WARN|FAIL"
    }
  ],
  "kpi": {
    "leak_rate": 0.012,               // per day (fraction)
    "efficiency": 0.93,               // process efficiency
    "power_draw": 1.0,                // normalized
    "throughput": 1.0                 // normalized
  }
}
```

**M** aggregates component health; **state** derives from critical path logic (see §3).

---

## 2) Wear & Failure Dynamics (MinuteTick)

Per component `c`:

```
wear_dot = base_wear(kind) * utilization * stress * env_factor(dust, heat, vibration)
H ← H - wear_dot
fault_prob_min = 1 - exp(-Δt / (mtbf_min / stress / f(H)))
if Bernoulli(fault_prob_min): fault_state = FAIL
WARN if H < warn_threshold or sensor drift detected
```

- `f(H)` increases failure probability as health declines (e.g., `f(H)=1/(ε+H)`).  
- **Utilization** rises with throughput demand and poor upstream conditions (e.g., low water quality → higher filter wear).  
- **Upgrades** modify `mtbf_min`, `stress`, or `base_wear` (see `InstallComponent`).

---

## 3) Facility State & KPI Mapping

- **ONLINE**: all critical components `OK`; KPIs derived from average `H` with soft penalties.  
- **DEGRADED**: any critical component `WARN` or noncritical `FAIL`; throughput/efficiency down; leak up.  
- **OFFLINE**: any critical component `FAIL` or safety interlock trips.

KPI update examples:
```
efficiency = base_eff * (0.8 + 0.2*M)
leak_rate_day = base_leak * (1 + α_leak * (1 - M))
throughput = base_tp * Π(1 - β_kind * fail_fraction_kind)
power_draw = base_pow * (1 + γ_pow * (1 - M))
```

---

## 4) Fault Detection & Task Queue

**Detection paths**:
- **Sensors** (if present) → immediate `FaultDetected` with location and severity.  
- **Inspections** (action `Scout`/`MaintainFacility(inspect)`) → probabilistic discovery by skill.  
- **Rumors** (workers complain) → low-cred hints, create `InspectionTask`.

**Task object**

```json
{
  "task_id":"t_883",
  "facility":"fac_011",
  "component":"cmp_pump_A",
  "kind":"REPAIR|REPLACE|INSPECT|CLEAN|SEAL|UPGRADE",
  "priority":"CRITICAL|HIGH|MEDIUM|LOW",
  "eta_min": 180,
  "parts":[{"sku":"pump_A","qty":1}],
  "skills":{"mechanic":2},
  "reward":{"credits":120,"reputation":{"guild:maint":+0.02}},
  "created_min": 112340
}
```

Tasks are posted to civic boards (PUBLIC) or black‑nodes (RESTRICTED) per venue policy.

---

## 5) Repair, Replace, Upgrade (Actions)

- `MaintainFacility(subsystem)` consumes **parts**, **time**, and **labor** to restore `H` or `M`.  
- `InstallComponent` swaps in upgraded parts (better `mtbf`, lower wear coefficients).  
- **Field Repair**: allowed with penalty caps (cannot exceed `H_max_field`).  
- **Downtime Windows**: to avoid curfew/peak loads; if violated, penalties to efficiency during work.

**Completion effects**: set `fault_state=OK`, boost `H`, recompute KPIs, emit `MaintenanceCompleted` (WARD scope).

---

## 6) Systemic Effects & Feedback

- **Reservoir/Seal faults** → leak rate ↑ → **Barrel Cascade** leakage corrections ↑; **market** price ↑.  
- **Power faults** → env stress ↑ (heat), production down → **Security** `ρ_env↑`, **Economy** throughput down.  
- **Reclaimer faults** → greywater backlog → hygiene ↓ → **Security** `ρ_health↑`.  
- **Gate faults** → checkpoint latency ↑ → **route risk** and **surcharge** ↑.  
- **Clinic faults** → `ρ_health↑`, narcotic crash deaths ↑ → **reclaimer** inflows.  
- **Rumor**: `MaintenanceCompleted` and `FacilityOffline` generate public narratives affecting legitimacy.

Legitimacy bump when critical faults repaired quickly; loss when outages long (see §10).

---

## 7) Prioritization Policy (Clerks/Governors)

Daily at **DayTick**, create a **Maintenance Plan**:

```
score_task = w_crit*criticality + w_kpi*ΔKPI_gain + w_safety*ΔRisk_drop + w_audit*visibility
           + w_cost*(-parts_cost) + w_time*(-eta_min) + w_politics*royal_bias
```

Select top tasks within budget `credits/parts/labor`. Publish plan; adjust **Tax** rebates for guilds hitting SLAs.

---

## 8) Spare Parts & Supply Lines

- Parts stocked per ward with reorder points; **lead times** trigger upstream contracts.  
- **Substitutions** allowed with efficiency penalties.  
- **Smuggled Parts** for illicit upgrades; detection raises `lawfulness` risks.  
- Market spreads widen when parts scarcity ↑.

---

## 9) Events

- `FaultDetected {facility, component, severity}`  
- `MaintenanceTaskQueued {task_id,...}`  
- `MaintenanceStarted/Completed`  
- `FacilityStateChanged {state, KPIs}`  
- `PartsStockLow {sku, reorder_point}`

All PUBLIC unless facility is black‑node or military (RESTRICTED with chance to leak as rumor).

---

## 10) Legitimacy & Reliability Updates

- **Fast repair of critical civic infra** → `GovLegit_w += δ_legit_repair` (small).  
- **Repeated or prolonged OFFLINE** → `GovLegit_w -= δ_legit_outage`.  
- **Guild reliability R** updated from task outcomes (on-time, within budget).

---

## 11) Policy Knobs

```yaml
maint:
  base_wear:
    PUMP: 1.0e-4
    SEAL: 1.2e-4
    FILTER: 1.4e-4
    VALVE: 0.8e-4
    MEMBRANE: 1.8e-4
    GENSET: 0.9e-4
    HEAT_EXCH: 0.7e-4
    CAMERA: 0.2e-4
    LOCK: 0.3e-4
  warn_threshold: 0.35
  stress_env_map:
    heat: 0.3
    dust: 0.4
    vibration: 0.2
  α_leak: 1.2
  β_kind: 0.4
  γ_pow: 0.6
  mttr_field_penalty: 1.4
  H_max_field: 0.75
  plan_weights:
    w_crit: 0.35
    w_kpi: 0.20
    w_safety: 0.15
    w_audit: 0.10
    w_cost: 0.08
    w_time: 0.07
    w_politics: 0.05
```

---

## 12) Pseudocode

```python
def minute_maint_update(fac):
    for c in fac.components:
        wear_dot = base_wear[c.kind] * load(fac) * c.stress * env_factor(fac.location)
        c.H = max(0, c.H - wear_dot)
        p = 1 - math.exp(-1.0 / (c.mtbf_min / c.stress / f_H(c.H)))
        if bernoulli(p): c.fault_state = "FAIL"
        elif c.H < warn_threshold: c.fault_state = "WARN"

    fac.state = evaluate_state(fac)
    fac.kpi = compute_kpis(fac)
    if fac.state_changed:
        emit("FacilityStateChanged", fac.id, fac.state, fac.kpi)
        if fac.state != "ONLINE":
            queue_inspection_or_repair_tasks(fac)
```

---

## 13) Explainability

For each outage, keep a **fault tree**:
- component lineage, wear history, recent loads, missed tasks, and parts availability.  
- show counterfactual: “Had task *t_883* been completed yesterday, outage probability ↓ by 62%.”

---

### End of Maintenance Fault Loop v1
