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
