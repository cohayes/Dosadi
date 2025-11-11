---
title: Dosadi_Work_and_Labor_Markets
doc_id: D-ECON-0004
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-ECON-0001
---
# **Work & Labor Markets v1**

Job discovery, wages, shifts, SLAs, reliability, and workforce allocation across wards.  
Integrates with **Agents v1 (Drives/Affinities/Skills)**, **Market Microstructure v1**, **Contracts & Cases v1**, **Security Loop v1**, **Maintenance Fault Loop v1**, **Rations v1**, **Clinic Flow v1**, **Rumor & Perception v1**, **Worldgen v1**, and the **Tick Loop**.

> Cadence: postings & wages update **per MinuteTick**; unemployment & productivity aggregate **per DayTick**.

---

## 0) Goals

1. **Make Work Real** — jobs have venues, qualifications, risk, gear needs, and shift structures.  
2. **Dual Currency** — pay in ward credits and/or water with floating FX; premiums for risk/urgency.  
3. **SLA‑Aware** — many jobs are sub‑tasks of contracts with deadlines and penalties.  
4. **Signal‑Rich** — reliability, reputation, and legitimacy shape job access and pay.  
5. **Playable Defaults** — simple heuristic matching; extendable to auctions/contracting.

---

## 1) Job Taxonomy

**JobKind** (examples; extensible):  
`MAINT_REPAIR`, `COOK_LINE`, `PORTER`, `ESCORT_GUARD`, `SCOUT`, `CRAFT_SMITH`, `CLERK`, `AUDITOR`, `DRIVER`, `RECLAIM_TECH`, `CLINIC_MEDIC`, `FARM_PROC`, `CONTRACT_RUNNER`, `ARBITER_AIDE`, `CULT_ACOLYTE`, `SMUGGLE_RUNNER` (illicit).

Each posting `JobID` specifies:
```json
{
  "job_id":"j_01993",
  "venue":"CIVIC|GUILD|MERC|BLACK_NODE|ROYAL",
  "employer":"FactionID",
  "kind":"MAINT_REPAIR",
  "ward":"W12",
  "shift":{"start_min":540, "len_min":360, "n_slots":3, "recurring":"DAILY|ONCE"},
  "requirements":{"skills":{"mechanic":2}, "affinities":{"Dexterity":0.4}, "suit":"min_tier:MID"},
  "risk":{"ρ_env":0.2,"ρ_crime":0.3,"route":"W12-W18"},
  "pay":{"credits":{"issuer":"lord_W12","min":120,"max":180},"water_L":{"min":4,"max":6},"split":"CREDITS|WATER|MIX"},
  "per":"SHIFT|HOUR|TASK|PIECE",
  "bonus":{"urgency_pct":0.10,"hazard_pct":0.15},
  "sla":{"contract_id":"c_2028","due_min":32400,"penalties":{"late_pct":0.10}},
  "lawfulness":"LAWFUL|GREY|ILLICIT",
  "visibility":"PUBLIC|RESTRICTED",
  "reputation_min":{"R_employer":0.3,"R_worker":0.2}
}
```

---

## 2) Venues & Posting Mechanics

- **CIVIC BOARDS** (PUBLIC): broad access, posted wage bands; clerks verify employers; restorative defaults for disputes.  
- **GUILD HALLS**: skilled roles; apprenticeships; wages higher but require reputation and dues.  
- **MERC EXCHANGES**: guards/escorts/contract muscle; hazard premiums; blacklists tracked.  
- **BLACK‑NODES** (RESTRICTED): token‑escrow jobs; anonymous; illicit work priced with premiums.  
- **ROYAL DISPATCH**: high‑priority maintenance/security; best pay, strict screening & penalties.

Events: `JobPosted`, `JobUpdated`, `JobClosed`.

---

## 3) Wage Formation

### 3.1 Baseline
`w_base = α_ref * MarketRef("labor:<kind>, ward") + (1-α_ref)*rolling_median(kind,ward)`

### 3.2 Adjustments
```
w = w_base * ( 1 + β_skill * skill_gap
                 + β_risk * composite_risk
                 + β_urg  * urgency
                 - β_supply * worker_surplus
                 + β_fx * FX(credits:issuer)
             ) + bonus_flat
```

- **skill_gap** = required tier − worker tier (cap at 0 if matched; negative reduces pay offer).  
- **composite_risk** from Security Loop for ward/route.  
- **worker_surplus** from unemployment ratio for this kind.  
- **FX** converts between credit issuers and king‑credit baseline.  
- **Hazard/Urgency bonuses** add on top; water split priced by local `P_ref_w`.

---

## 4) Matching & Acceptance

Each minute:
1. Build **candidate list** of jobs within movement horizon and requirements.  
2. Compute worker **reservation wage split** given drives (Hoard/Maintenance/Survival), needs (W,N), and FX.  
3. For each job, compute **expected income** minus costs (route surcharge, narcotics habit, suit wear).  
4. Apply **softmax** over jobs + “decline today” option.
5. Acceptance creates `ShiftAssignment {worker, job, start_min}` and optional **TokenEscrow** on black‑nodes.

**Failure reasons** logged: requirements not met, reputation too low, pay below reservation, travel time exceeds start.

---

## 5) Shifts, Timekeeping, and SLAs

- **Shift states**: `SCHEDULED → ON_DUTY → COMPLETE` or `NO_SHOW`.  
- **Timekeeping**: entry/exit scans; black‑nodes use signed tokens.  
- **SLA tracking**: if job tied to contract milestones, completion emits `MilestoneMet` else **late penalties** apply.  
- **No‑shows**: wage forfeits and **Reliability(worker)** down; repeated → blacklist at venue.

Events: `ShiftAssigned`, `ShiftStarted`, `ShiftCompleted`, `NoShow`.

---

## 6) Safety, Gear, and Clinics

- Employers may **provide gear** (suits/tools); deposits withheld for damage/loss.  
- **Safety score** per employer lowers injury probability; poor safety → clinic inflows & Arbiter cases.  
- **Hazard premiums** scale with route & incident history; **escort pairing** reduces risk (higher wages net).

---

## 7) Training & Progression

- **Apprenticeships**: lower pay; on completion, skill tier +1; reliability bonus.  
- **Certifications** (clerks/guilds): unlock wage floors and ROYAL jobs.  
- **Cross‑training**: temporary assignments to new kind with mentor; reduces skill gap penalties.

Events: `ApprenticeshipStarted/Completed`, `CertificationGranted`.

---

## 8) Reputation & Reliability

- **Reliability(worker)**: on‑time starts, shift completion, incident conduct.  
- **Reputation(employer)**: wage fairness, safety record, dispute outcomes.  
- **Rumor** integration: job scams, bribe‑for‑jobs scandals, heroic saves propagate with evidence scoring.

Tie‑ins: wage offers can require `R_worker ≥ θ`; top performers get **priority matching** and **premiums**.

---

## 9) Disputes & Enforcement

- **Wage theft** or unsafe conditions open **Cases** (restorative default).  
- **Illicit breaches** settled via **TokenEscrow** (bounty/arbitration at black‑node).  
- **Strikes & Slowdowns**: if pay fairness metric low and incidents high, generate `LaborAction` events; governors can mediate, grant temporary subsidies, or repress (Security feedback).

---

## 10) Metrics & Feedback (DayTick)

Per ward and job kind:
- **Employment Rate**, **Underemployment**, **Wage Index**, **Hazard Premium Index**, **No‑show rate**, **Training uptake**.  
- Feedbacks:
  - Employment up → **crime** down (small) and **legitimacy** up.  
  - Wage collapse or rampant no‑shows → **hoarding** and **crime** up.  
  - Strong training → **maintenance debt** down over time.

Emit `LaborStatsUpdated` and adjust Market & Security parameters modestly.

---

## 11) Policy Knobs

```yaml
labor:
  α_ref: 0.6
  β_skill: 0.10
  β_risk: 0.20
  β_urg: 0.12
  β_supply: 0.15
  β_fx: 0.08
  bonus_flat: 0
  min_wage_floor_by_venue:
    CIVIC: 20
    GUILD: 30
    MERC: 35
    ROYAL: 50
    BLACK_NODE: 0
  training:
    apprentice_len_min: 2400
    skill_gain: 1
    reliability_bonus: 0.05
  penalties:
    no_show_reliab_drop: 0.07
    unsafe_employer_legit_drop: 0.02
  hazard_premium_cap: 0.35
  escrow_fee_black: 0.03
```

---

## 12) Pseudocode

```python
def minute_labor_tick(ward):
    update_postings(ward)
    for worker in available_workers(ward):
        jobs = feasible_jobs(worker, ward)
        if not jobs: continue
        choice = pick_job_via_utility(worker, jobs)
        if choice: assign_shift(worker, choice)

def shift_complete(assignment):
    pay_out(assignment)
    update_reliability(assignment)
    close_if_sla_met(assignment)
```

---

## 13) Explainability

For each **ShiftAssignment** keep:
- wage breakdown (base + risk + urgency + FX), costs (travel, gear wear), net income.  
- why worker picked it (drives & reservation), why employer offered it (SLA, risk, reputation).  
- counterfactual: “If trained one tier higher, wage +12% and injury risk −8%.”

---

### End of Work & Labor Markets v1
