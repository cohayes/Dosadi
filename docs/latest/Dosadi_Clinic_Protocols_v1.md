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
