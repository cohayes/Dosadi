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
