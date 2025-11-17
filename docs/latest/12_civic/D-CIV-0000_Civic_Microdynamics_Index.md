---
title: Civic_Microdynamics_Index
doc_id: D-CIV-0000
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
depends_on:
  - D-WORLD-0003  # Ward_Branch_Hierarchies
  - D-ECON-0001   # Ward_Resource_and_Water_Economy
  - D-ECON-0002   # Dosadi_Market_Microstructure
  - D-INFO-0001   # Telemetry_and_Audit_Infrastructure
  - D-INFO-0005   # Record_Types_and_Information_Surfaces
---

# Civic Microdynamics Index

> This index describes the **CIVIC microdynamics cluster**:
> - What each document covers.
> - How civic facilities chain together (food → shelter → health → law → death).
> - Suggested reading and implementation order for simulation prototypes.

The CIVIC pillar handles **day-to-day survival surfaces** at ward scale:

- Where you **eat, sleep, heal, ask permission, get judged, and disappear**.
- Where ward policies become:
  - Queues, line fights, fines, triage decisions, and reclaimed liters of water.

---

## 1. Document List

A quick catalog of current CIVIC microdynamics docs.

### D-CIV-0001 – Soup Kitchens & Bunkhouses

- Scope:
  - Public food halls, ration kitchens, and low-end sleeping spaces.
- Core Loops:
  - Queueing for food and beds.
  - Ration distribution vs branch and faction influence.
  - Basic survival vs recruitment, rumor, and petty crime.
- Key Hooks:
  - ECON:
    - Food & ration flows, wage/ration chits.
  - INFO:
    - Rumor propagation, low-level incident logging.
  - MIL/ESP:
    - Patrol presence, informant recruitment in the lines.

---

### D-CIV-0002 – Clinics & Triage Halls

- Scope:
  - Street clinics, ward triage halls, specialist wards, covert backroom practices.
- Core Loops:
  - Intake → triage → treatment / denial → billing → record updates.
  - Triage decisions based on injury, labor value, faction, and ability to pay.
- Key Hooks:
  - ECON:
    - Medical stocks, water quotas, clinic debts.
  - INFO:
    - Medical incident logs, outbreak alerts, legal death records.
  - COURTS:
    - Injuries & deaths tied back to violence and legal cases.
  - CIVIC:
    - Feeds corpses into body disposal (D-CIV-0005).

---

### D-CIV-0003 – Posting Boards & Permit Offices

- Scope:
  - Ward and neighborhood posting boards, permit/licensing desks, mobile counters.
- Core Loops:
  - Notices generated and posted, tampered with, or ignored.
  - Agents applying for permits, paying fees, getting approved/denied/delayed.
- Key Hooks:
  - ECON:
    - Fees, fines, stall licenses, scavenging rights.
  - INFO:
    - Boards as information surfaces; permit ledgers vs telemetry and taxes.
  - COURTS:
    - Operating without permit → legal cases.
  - ESPIONAGE:
    - Disinformation, forged notices, tracking mobilizations.

---

### D-CIV-0004 – Courts & Justice Halls

- Scope:
  - Street tribunals, ward justice halls, special/inquisitorial courts, faction courts.
- Core Loops:
  - Incident → charge → hearing → verdict → sentencing.
  - Balancing evidence, faction pressure, fear, and regime stability.
- Key Hooks:
  - INFO:
    - LEGAL records, case logs, high-profile reports.
  - ECON:
    - Fines, confiscations, labor sentences feeding industry & reclamation.
  - CIVIC:
    - Sentences sending people to clinics, bunkhouses, prisons, or execution.
  - ESPIONAGE:
    - Secret courts and sealed intelligence influencing outcomes.

---

### D-CIV-0005 – Body Disposal & Reclamation Nodes

- Scope:
  - Morgues, organ banks, body reclaimers, taboo disposal sites.
- Core Loops:
  - Death → tagging → claim window → organ salvage → reclamation.
  - Converting corpses into water, fuel, and residual solids, modulated by taboo.
- Key Hooks:
  - ECON:
    - Water yields, fuel yields, disposal costs; connects into barrel accounting.
  - INFO:
    - Death registers, execution confirmations, yield ledgers, black-market diversions.
  - CIVIC:
    - Ties back to clinics (source of bodies) and courts (executions).
  - SOCIAL:
    - Taboo pressure, grief, and resentment against the regime.

---

## 2. Recommended Reading / Implementation Order

For onboarding a new human or codebase, we suggest:

1. **D-CIV-0001 – Soup Kitchens & Bunkhouses**
   - Easiest mental anchor:
     - Simple queues + rations + sleep + low-level conflict.

2. **D-CIV-0003 – Posting Boards & Permit Offices**
   - Adds:
     - A light-weight permission & information layer over everyday life.

3. **D-CIV-0002 – Clinics & Triage Halls**
   - Introduces:
     - Health, triage, and medical records linked to survival value.

4. **D-CIV-0004 – Courts & Justice Halls**
   - Binds:
     - Infractions and conflicts into structured punishments and fear/legitimacy loops.

5. **D-CIV-0005 – Body Disposal & Reclamation**
   - Closes:
     - The death → water/energy loop, connecting back into ECON and taboo.

This order is also a reasonable **prototype build path** for the simulation.

---

## 3. Civic Chain Overview (Flows)

At a high level, the civic microdynamics form a chain:

1. **Basic Survival:**
   - Agents seek food and beds  
     → *D-CIV-0001* (Queues, rations, bunkhouses).

2. **Permissions & Access:**
   - Agents seek work, stalls, movement, and building rights  
     → *D-CIV-0003* (Boards & permits).

3. **Health & Injury:**
   - Work, violence, and living conditions create injuries & disease  
     → *D-CIV-0002* (Clinics & triage).

4. **Law & Punishment:**
   - Infractions, accidents, and conspiracies escalate beyond local handling  
     → *D-CIV-0004* (Courts & justice halls).

5. **Death & Recycling:**
   - Some agents die in clinics, streets, prisons, or executions  
     → *D-CIV-0005* (Body disposal & reclamation).

Events, rumors, and records can loop back:

- Harsh courts push people:
  - Into bunkhouses, black markets, or rebellion.
- Reclamation smells and morgue lists:
  - Affect local legitimacy and fear.
- Permit and notice changes:
  - Reshape who ends up in queues, clinics, or courts.

---

## 4. Simulation Integration Notes

For Codex / implementation docs:

- **State Surfaces**
  - CIVIC docs define:
    - “Where agents spend their time when not in explicit missions.”
- **Event Types**
  - Many high-level events (riot, crackdown, outbreak, famine) are:
    - Visible first in civic facilities:
      - Longer queues, harsher triage, more bodies, more trials.

Recommended practice:

- Use this index as the:
  - **Entry point** for anything tagged CIVIC in code or design.
- Each CIVIC facility type should:
  - Emit **standardized event types**:
    - `CivicIncident`, `CivicQueueStress`, `CivicOutbreakAlert`, `CivicDeathYield`, etc.
  - These are then:
    - Consumed by INFO/ECON/MIL docs for higher-level behavior.

---

## 5. Future CIVIC Microdynamics Candidates

Not yet written, but likely siblings:

- **Entertainment & Vice Halls**
  - Bars, gambling dens, brothels, drug parlors.
- **Education & Indoctrination Halls**
  - Training spaces, literacy dens, ideological schools.
- **Public Works Nodes**
  - Bathing stations, laundry, small-scale water taps, communal workshops.

When these are added, they should be:

- Appended here with:
  - Scope, loops, and hooks in the same compact format.
