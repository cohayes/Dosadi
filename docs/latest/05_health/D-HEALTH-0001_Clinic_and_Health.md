---
title: Clinic_and_Health
doc_id: D-HEALTH-0001
version: 1.1.0
status: stable
owners: [cohayes]
depends_on: 
includes:
  - D-HEALTH-0002  # Day0 Dry Run Playbook
last_updated: 2025-11-11
---
# **Clinic & Health v1.1 (Triage, Outcomes, Billing, and FX Hooks)**

**Purpose.** Operate ward clinics as safety nets and performance levers: convert incidents and illness into recoveries while balancing capacity, supplies, prices, and reputation. Ties clinical hygiene to rumor dynamics and links billing to multi‑issuer Credits & FX.

Integrates with **Agents v1**, **Suit–Body–Environment v1**, **Work–Rest Scheduling v1**, **Escort & Combat v1**, **Barrel Cascade v1.1**, **Credits & FX v1.1**, **Rumor v1.1**, **Law & Contract Systems v1**, **Environment Dynamics v1**, and the **Tick Loop**.

> Timebase: intake & queue updates **per Minute**; treatment steps **per 5 Minutes**; quality dashboards **hourly**.

---
## 0) Entities & State

- **Clinic** `{id, ward, tier: ELITE|HIGH|MID|LOW, capacity_beds, staff_roster, hygiene_score, supply_bins, price_model, payer_rules, legitimacy}`  
- **Patient Episode** `{episode_id, agent_id, acuity: 1..5, dx_set, vitals, suit_state, hydration, injury_flags, infection_risk, arrival_ts, payer_pref}`  
- **Queue** with lanes: `TRIAGE`, `URGENT`, `ROUTINE`, `BILLING`, `DISCHARGE`  
- **Supplies** `{ORS, meds, dressings, filters, parts, power, water_buffer}` with reorder points and FX‑sensitive costs  
- **Payers**: `issuer_credits{I→balance}`, `ration_tokens`, `guild_vouchers`, `charity_pool`, `barter_list`  
- **KPIs**: `LWBS` (left without being seen), `D2D` (door‑to‑doctor), `MortalityAdj`, `Readmit48h`, `HygieneIncidents`, `CostPerCase`

---
## 1) Patient Flow

1) **Arrival**: walk‑in, convoy aftermath, workplace referral, or transport by guard/mercs.  
2) **Triage** (E1–E5): compute **Acuity** from vitals/injury/risk; attach *fast flags* (hemorrhage, seal failure, heat stroke).  
3) **Registration**: pull/attach payer options (credits, vouchers, ration tokens); estimate copay at current **FX mid**.  
4) **Routing**: to **Urgent Bay** (E1–E2), **Minor Care** (E3–E4), or **Routine** (E5), or **Maintenance Desk** for suit fixes.  
5) **Treatment Plan**: steps with resource times & supplies; pre‑authorize cost ceiling; notify patient.  
6) **Billing & Discharge**: settle payment mix; schedule follow‑ups; issue limited **med tokens** if rationed.  
7) **Readmit Watch**: for E1–E3, monitor 48h and trigger welfare checks if risk ↑.

Events: `PatientArrived`, `PatientTriaged`, `PlanAuthorized`, `TreatmentStarted`, `SuppliesConsumed`, `Billed`, `Discharged`, `ReadmitFlag`.

---
## 2) Triage & Outcomes

- **Acuity (1–5)** from a ruleset combining: `T_core`, BP/HR, GCS, bleed rate, suit breach class, hydration stage, infection markers.  
- **Outcome Model** per episode step: success probability improves with clinic tier, staff skill, supply quality, and **hygiene_score**.  
- **Time‑to‑Treat** increases complications non‑linearly for E1–E2; drives **MortalityAdj** and **Readmit48h**.  
- **Suit Faults**: minor → Maintenance Quick; major → **Surgery+Fabrication** path (filter seat recast, seal graft).

---
## 3) Hygiene, Infection, and Rumors

- **Hygiene Score** ∈ [0,1] from cleaning cadence, water use per bed, staff compliance, air exchanges, and waste routing.  
- **Infection Events** increase with crowding & low water buffers; raise `HygieneIncidents`.  
- **Rumor Hooks**: *“dirty clinic”* memes degrade arrivals (non‑urgent avoid care → **Readmit48h↑**); Arbiter can order audits.  
- **Transparency**: inner/mid wards publish **Cleanliness Dash**; outer wards often suppress (variance ↑).

---
## 4) Supplies, Water, and Reordering

- **Consumption**: each treatment step consumes supplies & liters; ORS and sterilization are water‑intensive.  
- **Reorder Policy**: (s,S) with **FX‑sensitive price** and delivery lead tied to **Cascade lanes**; escorts optional for high‑value meds.  
- **Shortage Protocol**: prioritize E1–E2; shift to **boil/sterile‑packs**; hygiene_score suffers → rumor risk ↑.

---
## 5) Pricing & Payers (FX Integration)

- **List Price** per procedure by tier; **dynamic copay** in issuer credits using `quote_mid(C_I/H2O)` from **Credits & FX v1.1**.  
- **Elasticity**: higher prices reduce elective arrivals; emergent acuity insensitive.  
- **Payer Mix** resolution: `credits` (any issuer at FX mid ± fee), `ration_tokens` (par value liters), `guild_vouchers` (discounts), `charity_pool` (subsidies), `barter` (rare; parts/repairs).  
- **Bad Debt**: if payment fails → installment token; rumor risk (dead‑beat clinic) if abused; Arbiter may mediate.

---
## 6) Staffing, Shifts, and Safety (Work–Rest Link)

- **Roster** by skill (medic, nurse, fabricator tech, sterilization crew); scheduler uses **Work–Rest v1** heat/strain tables.  
- **Safety Stops** for overheat, dehydration, or contamination breaches; push to **Recovery** tasks and **Maintenance Quick**.  
- **Mentorship Slots** gated by hygiene_score and staffing surplus; boosts long‑term outcomes.

---
## 7) Escorted Aftermath & Mass Casualty

- **Escort & Combat v1** feeds batches of E1–E2 after engagements; triage surge protocol pre‑allocates bays & kits.  
- **Overload**: open *tent extension* (lower tier, lower hygiene); request **Safehouse Water** & **cascade priority**; publish status to rumor board to deter panic.

---
## 8) Policy Knobs (defaults)

```yaml
clinic:
  tier_mod:
    ELITE: { outcome: +0.20, hygiene: +0.15, price_mult: 1.5 }
    HIGH:  { outcome: +0.12, hygiene: +0.08, price_mult: 1.2 }
    MID:   { outcome: +0.05, hygiene: +0.03, price_mult: 1.0 }
    LOW:   { outcome:  0.00, hygiene:  0.00, price_mult: 0.7 }
  queues:
    triage_slots: 3
    urgent_beds: 8
    minor_beds: 12
  hygiene:
    water_l_per_bed_hour: 2.0
    clean_interval_min: 30
    min_score_for_surgery: 0.70
  prices:
    base_visit_L: 1.0
    emerg_premium: 0.30
    issuer_fee: 0.01
  fx_pass_through: 0.6     # portion of FX change passed to copays
  lwbs_threshold_min: 45   # wait beyond which LWBS probability spikes
  rumor_weights:
    dirty_memes_penalty: 0.15
    clean_dash_bonus: 0.10
```

---
## 9) Event & Function Surface (for Codex)

**Functions**  
- `clinic_arrival(agent_id, vitals, injury_flags, payer_pref)` → triage + queue.  
- `clinic_plan(episode_id)` → treatment steps, supplies, time & cost estimate.  
- `clinic_start_step(episode_id, step)` / `clinic_end_step(...)` → outcomes, supply burn, water usage.  
- `clinic_bill(episode_id, payer_mix)` → computes FX‑converted copay; posts credit debits.  
- `clinic_discharge(episode_id)` → follow‑ups & tokens.  
- `reorder_supplies(clinic_id)` → emits purchase orders with FX quotes & cascade lane options.  
- `publish_clinic_dash(clinic_id)` → KPIs, queues, hygiene, prices.  

**Events**  
- `PatientArrived`, `PatientTriaged`, `PlanAuthorized`, `TreatmentStarted`, `SuppliesConsumed`, `FXQuoted`, `Billed`, `Discharged`, `HygieneIncident`, `ClinicDashPublished`, `SupplyOrderPlaced`, `SupplyOrderArrived`.

---
## 10) Pseudocode (Intake, Billing, Hygiene)

```python
def clinic_arrival(agent, vitals, flags):
    acuity = score_acuity(vitals, flags)
    lane = route_lane(acuity)
    enqueue(lane, agent)
    emit("PatientTriaged", {"acuity": acuity, "lane": lane})

def clinic_bill(episode, payers):
    L_cost = estimate_liters(episode.plan, tier=clinic.tier)
    mix = choose_payer_mix(payers, L_cost, fx=quote_mid(payers))
    debit_accounts(mix)
    emit("Billed", {"episode": episode.id, "mix": mix, "L_cost": L_cost})

def hygiene_tick(clinic):
    clinic.hygiene_score = compute_hygiene(clinic, crowd, water, compliance)
    if clinic.hygiene_score < policy.min_score_for_surgery:
        pause_elective_surgery()
        emit("HygieneIncident", {...})
```

---
## 11) Dashboards & Explainability

- **Clinic Board**: queues, D2D, LWBS, outcome rates, hygiene score, prices (in liters & issuer credits), FX pass‑through.  
- **Surge Panel**: casualty influx, supply burn‑down, bed occupancy; ETA on resupply & cascade priority.  
- **Equity View**: charity pool flow, denial rates, arrears.

---
## 12) Test Checklist (Day‑0+)

- Dirty memes ↓ arrivals for non‑urgent, ↑ Readmit48h; publishing Cleanliness Dash mitigates.  
- FX shocks (issuer risk, tax drain) raise copays; elasticity reduces elective arrivals but not emergent.  
- Work–Rest stops reduce staff incidents and keep MortalityAdj stable under heat stress.  
- Mass casualty surge routes E1–E2 to urgent bays with LWBS staying below threshold when surge protocol enabled.

---
### End of Clinic & Health v1.1

---

# **Clinic Protocols v1 (Triage, Queues, Treatments, and Outcomes)**

**Purpose:** Turn Suit–Body–Environment status effects and injuries into clinic demand, triage decisions, resource consumption, and outcomes—feeding legitimacy, rumor, and market signals.

Integrates with **Suit–Body–Environment v1**, **Suit Maintenance v1**, **Environment Dynamics v1**, **Labor v1**, **Law & Contract Systems v1**, **Rumor & Perception v1**, **Credits & FX v1** (med pricing), **Security Loop v1** (incident casualties), and the **Tick Loop**.

> Timebase: `Minute = 100 ticks`; triage/intake per minute; treatment steps batched per 5 minutes; outcomes consolidated per hour.

---

## 0) Clinic Entities & State

- **Clinic**: `{id, ward, grade: LOW|MID|HIGH|ELITE, beds, ER_bays, staff{medic,nurse,tech}, pharmacy, supplies, oxygen, water_buffer_L, hygiene, power}`

- **Visit**: `{visit_id, agent_id, esi, arrival_min, status: WAIT|TREAT|OBS|DISCHARGED|TRANSFERRED|DECEASED, dx, tx_plan, evidence[]}`

- **Pharmacy**: `{meds{analgesic, antipyretic, antibiotic, rehydration, stimulant, sedative}, inventory_units, spoilage}`

- **Supplies**: `{fluids_L, dressings, sutures, hemostatics, burn_gel, antivenin?, kits}`

- **Equipment**: `{monitors, ventilators, TEC_coolers, dialysis?, lab_basic, lab_rapid, imaging_basic}`

- **Queues**: `{triage, fast_track, acute, critical, obs}` round‑robin with strict priority.

---

## 1) Triage (ESI‑like) & Routing

Assign **Emergency Severity Index (1–5)** based on vitals, suit telemetry, and symptoms:

- **ESI‑1 (Immediate)**: core temp ≥ 40°C or ≤ 32°C, airway compromise, massive bleed, shock, severe CO₂/O₂ issue.

- **ESI‑2 (Emergent)**: T_core 39–40° with CNS symptoms, deep lacerations, moderate burns, dehydration ≥ 6%, severe pain.

- **ESI‑3 (Urgent)**: T_core 38–39°, dehydration 4–6%, suturable wounds, moderate pain, non‑threatening suit breach.

- **ESI‑4 (Less Urgent)**: mild heat/cold stress, dehydration 2–4%, minor lacs, follow‑ups.

- **ESI‑5 (Non‑Urgent)**: comfort care, prescriptions, work notes.

**Routing:**

- **ESI‑1** → `critical` bay; **ESI‑2** → `acute`; **ESI‑3** → `acute/fast_track` by load; **ESI‑4/5** → `fast_track/obs`.

**Deprioritization hazards:** overcrowded fast‑track under‑treats ESI‑3 → escalations (queues backfill). 

---

## 2) Vital Inputs & Suit Telemetry

- Vitals: HR, BP, RR, O₂ sat, Temp (core/skin), mental status, pain score.

- Suit telemetry: `Seal`, `Integrity`, `FilterLoad`, cooling/heating status, last hydration intake, exposure class.

- **Signal Confidence**: downgrade weight if sensors drift/forged; order confirmatory measurements.

Evidence items are attached to the visit (`SENSOR`, `WITNESS`, `VIDEO`, `LAB`).

---

## 3) Treatment Bundles (protocol sets)

**Heat Illness**

- I: cool (evap + TEC), IV fluids, electrolytes, rest; monitor.  

- II: active cooling (cold packs/TEC), IV fluids 20–40 mL/kg over 1–2h, NSAIDs if no renal risk; labs (CK, creatinine).  

- III (stroke): rapid aggressive cooling to 38.5°C, airway mgmt, IV bolus + maintenance, consider dialysis if rhabdo; **admit/transfer**.

**Cold Exposure**

- Passive rewarm (blankets), warm fluids, avoid rapid limb reheating if frostbite; monitor arrhythmia risk; **avoid sedatives**.

**Dehydration**

- ORS for 2–4%; IV crystalloids for ≥ 4%; correct electrolytes (Na/K); antiemetic PRN.

**Bleeds & Wounds**

- Pressure, hemostatic dressings, suture/closure, tetanus update, antibiotics by contamination grade; armor bruise care.

**Burns/Chemical**

- Irrigate (note water use), burn gel, dressings; chelation/neutralization per agent; pain control; infection watch.

**CO₂/O₂**

- Filter/power restore; O₂ support; scrubber swap; hypercapnia monitoring.

**Psych/Overuse**

- Rest, NSAIDs, counseling brief; narcotic caution (dependency flags).

---

## 4) Resource Accounting (Water, Meds, Time)

- **Water**: 

  - ORS prep: `0.25–0.5 L` per patient (ESI‑3/4).  

  - IV crystalloids: `1–3 L` per moderate; up to `4–6 L` severe over hours (facility‑tier dependent).  

  - Cooling irrigation: `0.5–2 L` (recovery possible in sealed rooms; efficiency by clinic grade).  

  - Wound irrigation: `0.1–0.5 L`.  

- **Meds**: unit decrements from pharmacy by bundle; spoilage tracked by day.

- **Time**: provider minutes; staffing modulates throughput; queues update per 5‑min batch.

- **Recovery Capture**: sealed clinics reclaim % of irrigation/evap; logs to water ledger.

---

## 5) Infection Control & Hygiene

- Hand‑off protocols; dirty/clean zone separation; suit decon air‑locks (sealed interiors favored).  

- Biofilm sensing on reservoirs; contaminated suits flagged for **Hygiene Service** task (maintenance loop).  

- Outbreaks produce **clinic capacity penalties**; rumors of “dirty clinic” harm legitimacy.

Events: `ClinicHygieneAudit`, `ClinicOutbreakSuspected`.

---

## 6) Queueing & Scheduling

- Priority scheduling: `critical > acute > fast_track > obs` with **aging** to prevent starvation.

- **Left‑without‑care** after threshold wait emits high‑salience rumor and legitimacy −ε to clinic & ward.

- **Transfer** rules: ESI‑1/2 overload → send to higher‑grade clinic; escort risk calculated with Security Loop.

---

## 7) Outcomes & Scoring

- **Outcome**: `RECOVERED | IMPROVED | STABLE | DETERIORATED | DECEASED | TRANSFERRED`.

- **LOS (length of stay)** by dx and grade; **Readmit risk** based on hydration/compliance and environment return.

- **Quality KPI**: mortality/ESI mix, wait times, guideline adherence, water use per case, infection rate, patient rumors sentiment.

Events: `ClinicOutcome`, `ClinicKPIUpdated`.

---

## 8) Pricing & Access

- Payment in local credits with FX to king‑credits as needed; **emergency care floor** free by royal decree (political choice).  

- Tiers: low‑grade clinics cheaper, less recovery efficiency; elite clinics expensive, better outcomes/throughput.  

- Black‑nodes: clandestine triage for smugglers; limited capability; high mortality risk.

---

## 9) Policy Knobs

```yaml
clinic:
  beds: { LOW: 8, MID: 20, HIGH: 40, ELITE: 80 }
  bays: { LOW: 2, MID: 4, HIGH: 8, ELITE: 16 }
  staff_per_shift: { medic: 1, nurse: 3, tech: 1 }
  reclaim_eff: { LOW: 0.2, MID: 0.5, HIGH: 0.75, ELITE: 0.9 }
  wait_alert_min: 90
  lwbs_min: 180             # left-without-being-seen threshold
  transfer_threshold: { ESI1: 0.8, ESI2: 0.7 }  # load factor
  ors_per_case_L: 0.3
  iv_min_L: 1.0
  iv_max_L: 6.0
  cooling_L: [0.5, 2.0]
  wound_irrigation_L: [0.1, 0.5]
  hygiene_audit_freq_days: 7
```

---

## 10) Event & Function Surface (for Codex)

**Functions**

- `clinic_intake(agent_id, clinic_id)` → `Visit` with ESI; routes to queue.  

- `minute_clinic_tick(clinic_id)` → advances queues, starts/ends treatments, adjusts resources.  

- `apply_bundle(visit_id, bundle_id)` → decrements meds/water; updates status.  

- `discharge(visit_id, result)` → closes visit; schedules follow‑up; emits `ClinicOutcome`.  

- `transfer(visit_id, to_clinic)` → starts escorted move; creates case if adverse event.  

- `audit_hygiene(clinic_id)` → evidence & rumor hooks.

**Events**

- `ClinicIntake`, `TriageAssigned`, `TreatmentStarted/Completed`, `ClinicDiverted`, `ClinicOutcome`, `ClinicHygieneAudit`, `ClinicKPIUpdated`.

---

## 11) Pseudocode (Minute & 5‑Minute Batch)

```python
def clinic_intake(agent, clinic):
    esi = triage(agent.vitals, agent.suit.telemetry)
    q = pick_queue(esi, clinic.load)
    enqueue(q, agent)
    emit("ClinicIntake", {..., "esi": esi})

def minute_clinic_tick(clinic):
    for q in [critical, acute, fast_track, obs]:
        while resources_available(clinic, q) and q.not_empty():
            v = q.pop()
            start_treatment(v)
            consume_resources(v.plan)
    complete_finished_treatments()
    update_waits_and_aging()

def discharge(visit, result):
    free_bed(visit)
    emit("ClinicOutcome", {"visit": visit.id, "result": result, "water_used_L": visit.water_used})
```

---

## 12) Explainability & Rumor Hooks

- For each visit: attach **evidence bundle**; public (anonymized) dashboards publish wait times, mortality, water use per case.

- Rumor sensitivity: ESI‑1 deaths, LWBS counts, and hygiene scandals propagate fast; cross‑check with Arbiters for defamation control.

---

## 13) Test Checklist (Day‑0+)

- Heat‑stroke (ESI‑1) stabilized within 10 minutes at HIGH/ELITE, 20–30 minutes at MID, worse at LOW.  

- Dehydration ≥ 6% consumes ≥ 3 L IV over first hour; clinic water buffer decreases accordingly.  

- Overload triggers `ClinicDiverted` and lawful transfers; LWBS emits rumor with legitimacy hit.  

- Hygiene audit failure increases infection rate until maintenance/hygiene service closes the loop.

---

### End of Clinic Protocols v1

---

# **Health & Clinic Flow v1**

Injury/illness lifecycle, clinic operations, and population health feedback.  
Integrates with **Agents v1 (Body/Suit)**, **Environment Dynamics v1**, **Security Loop v1**, **Maintenance Fault Loop v1**, **Market v1**, **Law & Contract Systems v1**, **Rumor & Perception v1**, and the **Tick Loop**.

> Cadence: health deltas per **MinuteTick**; triage queues update each minute; aggregate health/legitimacy effects **per DayTick**.

---

## 0) Goals

1. **Physical Plausibility** — hydration, nutrition, fatigue, exposure, trauma, infection modeled simply but credibly.  
2. **Playable Clinics** — triage, queues, resources (staff, beds, meds), and outcomes with clear knobs.  
3. **Feedback** — outages and epidemics affect legitimacy, prices, and behavior (drives).  
4. **Explainable** — every death or recovery traces to causes, delays, and interventions.

---

## 1) Agent Health Model (Recap + Extensions)

Per agent, tracked continuously (0–1 unless noted):

- **H (Health)** overall integrity; drops from trauma, exposure, disease; recovers with rest/treatment.  
- **N (Nutrition)**, **W (Hydration)**, **Sta (Stamina)**, **ME (Mental Energy)** (see Agents v1).  
- **Exposure Risk** from **Suit**: `Seal`, `Integrity`, `EnvProt` vs heat/cold/chem/rad.  
- **Injury Flags**: `BLUNT|PENETRATING|BURN|CHEM|RADIATION`. `severity ∈ {MINOR, MODERATE, SEVERE, CRITICAL}`.  
- **Illness Flags**: `DEHYDRATION|MALNUTRITION|INFECTION|OVERDOSE|WITHDRAWAL|HEATSTROKE|HYPOTHERMIA`.  
- **Contagion State**: `SUSC|EXPOSED|INFECTIOUS|RECOVERED|IMMUNE` (SEIR-lite).  
- **Chronic Conditions** (optional): e.g., `lung_damage`, `renal_stress` accumulate with repeated insults.

**Minute dynamics (simplified)**

```
ΔH = + κ_rest*Rest  + κ_treat*Treatment  - κ_exp*Exposure  - κ_trauma*Trauma  - κ_path*Pathology
ΔW = - perspiration_loss(Env,Suit) - activity_loss + reclaim_gain(Suit)
ΔN = - basal_metabolic - labor_cost + intake_gain
ΔSta, ΔME from activity & rest (see Agents v1)
Hard floors: if W or N < θ_crit → accelerated H decline
```

---

## 2) Injury & Illness Generation

**Sources**
- **Security incidents**: ambush, clash, riot → trauma with distribution over severities.  
- **Environment**: heat/cold/dust/chem/power outages (HVAC) → exposure illnesses.  
- **Maintenance**: facility faults (reclaimer/clinic off) → infection risk, treatment delay.  
- **Narcotics**: overdose/withdrawal events tied to usage patterns and supply purity.  
- **Crowding**: high density + low hygiene → outbreaks via SEIR.

**SEIR-lite per ward**

```
β_w = β0 * crowding * hygiene_factor * (1 - clinic_effectiveness)
E → I at rate σ; I → R at rate γ; immunity wanes slowly
Clinic campaigns reduce β_w; curfews reduce crowding (Security Loop)
```

---

## 3) Clinic Model

**Clinic** has capacities and resources:

```json
{
  "clinic_id":"cl_07",
  "tier":"LOW|MID|HIGH|ELITE",
  "beds": 24,
  "triage_desks": 2,
  "staff": {"medic":6,"nurse":8,"tech":4},
  "pharmacy": {"saline":120,"antibiotic":60,"analgesic":200,"antirad":20,"antitox":30},
  "surgery_rooms": 1,
  "icu_beds": 2,
  "state": "ONLINE|DEGRADED|OFFLINE",
  "kpi":{"wait_min":0,"throughput_hr":0,"mortality_24h":0.0,"utilization":0.0}
}
```

Tier controls **skill multipliers**, **procedure set**, and **outcome ceilings**.

**Triage Levels (ESI‑like 1–5)**  
`1=Immediate (life‑threat)`, `2=Emergent`, `3=Urgent`, `4=Less‑urgent`, `5=Minor/self‑care`.

**Queues (per clinic)**  
- `queue_1_2` (red), `queue_3` (yellow), `queue_4_5` (green). Each minute: pull as staffing & rooms allow.

---

## 4) Intake & Triage

When an agent seeks care (or is delivered):

1. **Check-in**: create `VisitID` with vitals, injury/illness flags, time since onset.  
2. **TriageScore** computed from vitals (H, W, N), mechanism, suit status, infection suspicion.  
3. **Queue assignment**: `ESI` level; if level 1 and `surgery/ICU available` → immediate rooming.  
4. If clinic **DEGRADED/OFFLINE** or full → **divert** to nearest clinic; add travel delay or **wait**.

Events: `ClinicIntake`, `TriageAssigned(level)`.

---

## 5) Treatment Actions & Resources

Each minute for a patient in room/bed, choose a **Care Plan** with resource costs and efficacy:

- **Resuscitate** (fluids, airway, shock) → heavy staff focus; consumes `saline`, `analgesic`.  
- **Surgery/Procedure** (trauma repair) → `surgery_room`, `medic`, `tech`, parts/supplies.  
- **Wound Care/Antibiotics** → meds & nurse time; reduces infection risk.  
- **Detox/Stabilize** (overdose/withdrawal) → meds & monitoring.  
- **Hydration/Nutrition** → rations, water; improves recovery curve.  
- **Isolation** for infectious cases; consumes `isolation_bed` if tier supports.  
- **Discharge with Rations/Rx** or **Transfer** to higher tier.

**Outcomes (per minute probability updates)**

```
P_improve = base_tier * skill_mult * care_quality * f(H,W,N) * g(illness/injury)
P_deteriorate = baseline_pathology * delay_penalty * exposure_in_clinic
Mortality triggers if H ≤ H_min or shock unresolved; otherwise gradual.
```

---

## 6) Wait Costs & Deterioration

While in queue:
- Apply **delay damage** based on ESI: level 1 degrades fastest.  
- **Rumor**: severe waits spawn negative clinic narratives; deaths in waiting rooms are critical scandals.  
- **Diversion**: if `wait_min > threshold[level]`, attempt transfer to other clinic (adds travel risk).

---

## 7) Discharge, Recovery, and Work Capacity

On discharge:
- Assign **recovery plan** length with daily `ΔH, ΔSta, ΔME` bonuses; restrictions on labor/violence.  
- **Follow‑up** visit scheduled; missed follow‑ups reduce outcomes.  
- **Work Capacity %** derived from `H, Sta, injuries`; affects labor supply and agent utility selection (tends to `Rest`).

**Chronic accumulation**: when injury/illness exceeds thresholds, add to chronic damage pools reducing future max stats or raising future risk.

---

## 8) Pharmacy & Supply

- **Inventory** decremented by treatment; reorder via contracts when below `reorder_point`.  
- **Shortages** degrade care quality and increase mortality (and prices in Market).  
- **Counterfeit meds** risk at black‑nodes; success/failure influences **Reliability** of suppliers.

---

## 9) Billing, Access, and Legitimacy

- **Pricing** per tier; may accept ward credits or water. Unpaid bills open **Cases** (restorative by default).  
- **Civic Clinics** (PUBLIC) lower prices, boost legitimacy; **Private/Elite** improve outcomes/perks but are restricted.  
- Daily **Legitimacy Δ** includes:
  - `+` survival of high‑profile cases, low mortality, responsive triage.  
  - `−` visible deaths due to diversion/outages/shortages; scandals (e.g., bribe‑for‑care).

---

## 10) Epidemic Control

- **Campaigns**: vaccination, hygiene drives, rationed clean water; reduce `β_w`.  
- **Quarantine/Curfew** via Security Loop; reduces crowding but increases economic costs.  
- **Public Info**: evidence‑scored announcements change behavior (Rumor system).

---

## 11) Events

- `ClinicIntake {agent, clinic, ESI}`  
- `TriageAssigned {visit, level}`  
- `TreatmentStarted/Completed {visit, plan}`  
- `ClinicDiverted {from,to,reason}`  
- `ClinicOutcome {visit, result: RECOVERED|IMPAIRED|DECEASED}`  
- `PharmacyLow {drug}`  
- `EpidemicMetric {ward, R_t}`

Most are PUBLIC for civic clinics; private/elite may be RESTRICTED with controlled leaks.

---

## 12) Policy Knobs

```yaml
clinic:
  tier_multiplier:
    LOW: 0.6
    MID: 0.8
    HIGH: 1.0
    ELITE: 1.2
  esi_wait_threshold_min:
    "1": 1
    "2": 10
    "3": 30
    "4": 90
    "5": 180
  delay_penalty:
    "1": 0.08
    "2": 0.05
    "3": 0.03
    "4": 0.01
    "5": 0.005
  seir:
    β0: 0.02
    σ: 0.15
    γ: 0.10
  pricing:
    LOW:  {base: 10,  meds_mult: 1.0}
    MID:  {base: 25,  meds_mult: 1.1}
    HIGH: {base: 60,  meds_mult: 1.2}
    ELITE:{base: 150, meds_mult: 1.5}
  diversion_max_travel_min: 25
  rumor_salience_on_wait_death: 0.9
```

---

## 13) Pseudocode

```python
def minute_clinic_tick(clinic):
    # Room patients first by ESI then by wait time
    room_patients(clinic)
    # Apply care
    for v in clinic.active_visits:
        apply_care(v, clinic)
        if outcome_terminal(v):
            discharge(v, result="DECEASED")
        elif ready_for_discharge(v):
            discharge(v, result="RECOVERED" if v.H>0.85 else "IMPAIRED")
    # Queued patients deteriorate
    for q in clinic.queues:
        for v in q:
            apply_queue_delay_costs(v)
            if should_divert(v, clinic): divert(v)
    update_kpis(clinic)
```

---

## 14) Explainability

For each **VisitID** maintain:
- presenting complaint & vitals timeline, care plan steps, delays (with reasons: capacity, outage, diversion), meds consumed.  
- counterfactual: “If admitted 12 minutes earlier, survival probability +18%.”  
- rumor hooks: `ClinicOutcome` links to public narratives with evidence scoring.

---

### End of Health & Clinic Flow v1
