---
title: Civic_Microdynamics_Clinics_and_Triage_Halls
doc_id: D-CIV-0002
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
depends_on:
  - D-WORLD-0003  # Ward_Branch_Hierarchies
  - D-ECON-0001   # Ward_Resource_and_Water_Economy
  - D-ECON-0002   # Dosadi_Market_Microstructure
  - D-ECON-0003   # Credits_and_FX
  - D-ECON-0009   # Financial_Ledgers_and_Taxation
  - D-INFO-0001   # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002   # Espionage_Branch
  - D-INFO-0003   # Information_Flows_and_Report_Credibility
  - D-INFO-0004   # Scholars_and_Clerks_Branch
  - D-INFO-0005   # Record_Types_and_Information_Surfaces
  - D-CIV-0001    # Civic_Microdynamics_Soup_Kitchens_and_Bunkhouses
---

# Civic Microdynamics: Clinics & Triage Halls

> This document defines **how ward-level medical spaces operate** at the micro scale:
> - The internal loops of clinics and triage halls.
> - How patients are sorted, treated, billed, or discarded.
> - How medical facilities intersect with water quotas, labor priorities, and law.
> - Where the juiciest points of leverage, corruption, and information flow live.

Clinics are **where Dosadi decides who is worth saving**:

- Your injuries, faction, and usefulness are weighed against water and supplies.
- Some walk out with patched suits and a second chance.
- Some walk out marked, indebted, or watched.
- Some leave in pieces.

---

## 1. Facility Archetypes

We define four core archetypes:

1. **Street Clinic** (CLINIC_LOW)
2. **Ward Triage Hall** (TRIAGE)
3. **Referral / Specialist Ward** (CLINIC_HIGH)
4. **Backroom / Covert Practice** (CLINIC_BLACK)

They share machinery but differ in who they serve and what records they generate.

### 1.1 Street Clinic (CLINIC_LOW)

- Location:
  - Lower/mid wards, near bunkhouses, kitchens, markets.
- Services:
  - Triage-level care, basic wound treatment, minor infections.
- Payment:
  - Ration/clinic chits, small WCR, sometimes “public health” subsidies.
- Vibe:
  - Crowded, noisy, improvisational.  
  - High throughput, low resources, constant risk of infection.

### 1.2 Ward Triage Hall (TRIAGE)

- Location:
  - Often attached to militia barracks or civic hubs.
- Services:
  - High-volume intake during:
    - Accidents, riots, combat events, outbreaks.
- Role:
  - **Sorting node**:
    - Who gets patched and returned to duty.
    - Who is stabilized and referred up.
    - Who is sedated, warehoused, or written off.
- Payment:
  - Typically funded by ward or branch budgets; individuals may not pay directly.

### 1.3 Referral / Specialist Ward (CLINIC_HIGH)

- Location:
  - Better-off wards, near industry hubs or noble compounds.
- Services:
  - Surgery, implants, suit-work, chronic care.
- Access:
  - Guild members, critical workers, nobles, high-value prisoners.
- Payment:
  - KCR, substantial WCR, high-tier chits, political favors.

### 1.4 Backroom / Covert Practice (CLINIC_BLACK)

- Location:
  - Behind bunkhouses, in safehouses, under markets.
- Services:
  - Unregistered treatments, removal of tracking devices, falsified exam results.
- Ties:
  - Black Market Networks, Espionage, gangs, and corrupt officials.
- Records:
  - Shadow-only or heavily doctored; strong link to SHADOW/BLACK_LEDGER types.

---

## 2. Roles Within Medical Facilities

### 2.1 Medical Chain

- **Medical Chief / Head Medic**
  - Reports to:
    - Civic branch (staff chief of clinics) or Military branch (if under militia).
  - Sets:
    - Triage policies, treatment priorities, allocation of scarce supplies.

- **Triage Officers / Senior Nurses**
  - Frontline sorters:
    - Decide who is urgent, who can wait, who is likely a lost cause.
  - Interface with:
    - Guards, clinic clerks, occasionally investigators.

- **Medics / Nurses / Orderlies**
  - Carry out treatments, handle sanitation, move bodies.
  - Directly experience:
    - Inequality of care and branch directives.

- **Clinic Clerks**
  - Manage:
    - Patient intake records, treatment logs, supply ledgers, billing.
  - Core node for:
    - Record tampering and information leaks.

### 2.2 Security & External Control

- **Militia / House Guards**
  - Secure high-priority patients.
  - Enforce:
    - Isolation orders, barring unwanted visitors, patient arrests.

- **Investigators / Inspectors**
  - Investigate:
    - Suspicious injury patterns, deaths in custody, outbreaks.
  - Demand:
    - Records, testimonies, cross-checks with other facilities.

- **Black-Market Doctors & Fixers**
  - May be:
    - Moonlighting staff or fully external actors.
  - Trade:
    - Clean records, quiet deaths, removal of evidence.

---

## 3. Facility State Variables

### 3.1 Resource & Capacity State

- `water_quota_med`:
  - Water reserved for cleaning, instruments, patients.
- `stocks_medical`:
  - `bandages`, `antiseptic`, `antibiotics`, `painkillers`, `surgical_kits`.
- `bed_capacity`:
  - Counts per acuity tier: `LOW`, `MID`, `HIGH`, `ISOLATION`.
- `queue_capacity`:
  - Max waiting area before overflow triggers outside crowding.
- `biohazard_load`:
  - Accumulated infectious load (affects infection risk).

### 3.2 Operational State

- `triage_policy`:
  - Rule set describing:
    - Which classes of patients are prioritized (critical workers, militia, nobles).
- `throughput_targets`:
  - Expected number of patients to process per block.
- `infection_alert_state`:
  - `NONE | WATCH | OUTBREAK_SUSPECTED | OUTBREAK_CONFIRMED`.

### 3.3 Governance & Risk State

- `GovLegit_facility`:
  - Perceived legitimacy/trust of the clinic.
- `corruption_level_med`:
  - Likelihood of:
    - Bribes changing priority or medical outcomes.
- `inspection_pressure_med`:
  - Frequency/intensity of:
    - Medical audits, external oversight.
- `violence_risk`:
  - Likelihood of patients or factions attacking staff/facility.

---

## 4. Patient-Level State (In-Facility)

When an agent becomes a patient, we track:

- `injury_profile`:
  - Type/severity: blunt trauma, burns, lacerations, organ damage, etc.
- `health_state`:
  - Vitals, infection status, chronic conditions.
- `contagion_risk`:
  - Probability of spreading disease if not isolated.
- `labor_value`:
  - Estimated future productivity:
    - Role, skills, faction importance.
- `faction_tags`:
  - Guild, militia, noble retainer, criminal, unaligned.
- `ability_to_pay`:
  - Wallet state, chit ownership, backing sponsors (guilds, patrons).
- `legal_status`:
  - Wanted, suspected, under investigation, clean.
- `consent_profile`:
  - How much they can refuse:
    - Treatment, interrogation, body harvesting (if at all).

---

## 5. Session Loop: Clinic / Triage Block

We consider a **treatment block** (a chunk of simulated time).

### 5.1 Intake & Triage

1. **Arrival Set**
   - Patients arrive from:
     - Street accidents, workplaces, bunkhouses, kitchens, militia skirmishes.

2. **Identity & Status Check**
   - Clerk or guard verifies:
     - Name (or alias), affiliations, wanted lists, insurance-like arrangements (guild cover).

3. **Triage Decision**
   - Triage officer classifies:
     - `CRITICAL`, `URGENT`, `ROUTINE`, `PALLIATIVE`, `NO_TREATMENT`.
   - Influenced by:
     - `injury_profile`, `labor_value`, `faction_tags`, ability to pay, external orders.

4. **Queue Assignment**
   - Each class goes to:
     - Different queue (or ward) with distinct wait times and resource levels.

### 5.2 Treatment / Non-Treatment

For each patient in order of triage priority:

1. **Treatment Plan**
   - Decide:
     - Minimal effective intervention vs maximal care.
   - Consume:
     - Relevant stocks + water + staff time.

2. **Outcome Roll**
   - Based on:
     - Injury severity, supplies, staff skill, contamination level, time-to-treatment.
   - Outcomes:
     - Recovery (partial/full), disability, death, or infection.

3. **Billing / Ledger Updates**
   - Apply:
     - Chit redemption, WCR/KCR charges, guild/crown subsidies.
   - Update:
     - Facility ledger and patient’s wallet/debt state.

4. **Records**
   - OP_LOG:
     - Patient categories, outcomes, supplies used.
   - LEDGER:
     - Cost entries, subsidies, write-offs.
   - LEGAL (if applicable):
     - Incident reports, deaths in custody, assault evidence.

### 5.3 Overflow & Denial

If capacity or stocks are exceeded:

- **Overflow Protocol**
  - Patients may be:
    - Turned away, redirected, left in overflow queue with rising mortality.
- **Denial of Care**
  - Factions or policies may explicitly:
    - Deny treatment to certain groups.
- **Crowd Dynamics**
  - Overflow can:
    - Lead to unrest, targeted attacks, or pressure for policy change.

---

## 6. Micro-Events & Hooks

### 6.1 Resource Micro-Events

- **Drug Substitution**
  - Use cheaper/weaker meds than claimed, pocket the rest.
- **Body-Water Harvest**
  - In extreme scarcity:
    - Dead/near-dead patients are processed for water and organs.
  - Tightly tied to:
    - Ward taboos vs survival ethics.

- **Quarantine Shortcuts**
  - Skipping proper isolation to increase throughput:
    - Raises `biohazard_load`.

### 6.2 Social & Political Micro-Events

- **Priority Overrides**
  - Orders arrive from:
    - Lords, guild bosses, militia:
      - “Treat my people first.”
- **Selective Neglect**
  - Staff “forget” certain patients:
    - Rival faction members, suspected traitors.

- **Recruitment via Treatment**
  - Militia/gangs offer:
    - Guaranteed treatment in exchange for future service.

### 6.3 Information & Legal Micro-Events

- **Record Scrubbing**
  - Altering:
    - Cause of injuries, time of death, who was present.
- **Evidence Creation**
  - Falsifying records:
    - To implicate or protect specific factions or individuals.

- **Silent Deaths**
  - Some patients die “off the books”:
    - No legal record, only shadow notes (if any).

---

## 7. Telemetry, Logs & Records In-Clinic

Tie-in to D-INFO-0005.

### 7.1 Intra-Facility Record Types

- **TELEMETRY**
  - Bed occupancy, power/water usage, sterilization cycles.
- **OP_LOG**
  - Patients processed by category, procedures performed, complications.
- **LEDGER**
  - Medical stock movements, billing, subsidies, bribes (sometimes misclassified).
- **FORMAL_REPORT**
  - Outbreak updates, casualty reports after major incidents.
- **LEGAL**
  - Death certificates, injury reports, chain-of-custody for evidence.
- **SHADOW**
  - Covert procedure notes, black ledger for off-book surgeries and quiet deaths.

### 7.2 Information Surfaces

- **Intake Desk**
  - Public-facing rules, prices, waiting times.
- **Nurses’ Station**
  - Operational status and short-term decisions:
    - Who really gets pulled in next.
- **Back Office**
  - Detailed patient records and ledgers:
    - Primary tampering site.
- **Morgue / Disposal Interface**
  - Where death meets:
    - Waste/reclamation and legal reporting.

---

## 8. Interaction with Economy & Labor

Clinics are not just humanitarian; they’re **infrastructure for labor and control**.

### 8.1 Labor Preservation

- Wards and guilds treat critical workers as:
  - **Assets worth repairing**.
- `labor_value` influences:
  - Triage priority, access to higher-tier clinics.

### 8.2 Pricing & Access Regimes

- Different wards may adopt variants:

  - **Civic-First Model**
    - Minimal free triage; better care costs.
  - **Guild-First Model**
    - Guild members heavily favored; others pushed to low-capa street clinics.
  - **Militia-First Model**
    - Combatants get priority to keep security apparatus intact.

### 8.3 Debt & Obligation

- Treatment may create:
  - **Debts**:
    - Payable in labor, espionage favors, future bribes.
- Clinics can become:
  - Quiet engines of:
    - Recruitment and soft coercion.

---

## 9. Simulation Hooks & Minimal Prototype

### 9.1 Minimal Clinic Schema

```json
{
  "facility_id": "W21_CLINIC_LOW_01",
  "type": "CLINIC_LOW",
  "ward": "W21",
  "capacity": {
    "beds_LOW": 20,
    "beds_MID": 10,
    "beds_HIGH": 3,
    "beds_ISO": 2
  },
  "stocks_medical": {
    "bandages": 200,
    "antiseptic": 150,
    "antibiotics": 40,
    "painkillers": 80
  },
  "water_quota_med": 400,
  "governance": {
    "GovLegit_facility": 0.6,
    "corruption_level_med": 0.3,
    "inspection_pressure_med": 0.4,
    "violence_risk": 0.3
  },
  "triage_policy": "civic_default"
}
```

### 9.2 Minimal Loop

Per treatment block:

1. Draw **arrivals** (with injury profiles).
2. Run **triage**:
   - Assign priority + queues using policy and corruption sliders.
3. Process as many as capacity/resources allow.
4. Update:
   - Patient health, debt, legal status; facility stocks; logs and ledgers.
5. Check for:
   - Infection thresholds, violence triggers, inspection events.
6. Emit:
   - TELEMETRY, OP_LOG, LEDGER, and `MedicalIncident` / `OutbreakAlert` events.

### 9.3 Tuning Axes

- `corruption_level_med`:
  - More bribe-driven triage, more “accidental” deaths of undesired factions.
- `inspection_pressure_med`:
  - Fewer blatant abuses but more subtle record games.
- `infection_alert_state`:
  - Governs risk of wards sliding into chronic or acute outbreaks.
- `triage_policy` variants:
  - Ward personality encoded via:
    - Who is considered “salvageable”.

---

## 10. Open Questions

For later docs or ADRs:

- How deeply do we model **epidemiology**?
  - Simple “infection chance” vs more structured disease states.
- Should some wards:
  - Rely heavily on **backroom clinics** with minimal official presence?
- How are **body disposal & reclamation** integrated?
  - Likely needs its own doc linking:
    - Clinics, waste systems, and taboo structures.
- To what extent do clinics act as:
  - **Mandatory reporting nodes** for militia (all gunshot wounds, etc.)?

For now, this microdynamics layer is meant to:

- Plug cleanly into ECON (water & supplies) and INFO (records & investigations).
- Provide a believable backbone for:
  - “You got hurt; now the system decides what you’re worth.”
