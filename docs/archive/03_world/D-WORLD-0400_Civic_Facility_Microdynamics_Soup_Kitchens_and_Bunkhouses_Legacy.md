---
title: Civic_Facility_Microdynamics_Soup_Kitchens_and_Bunkhouses_Legacy
doc_id: D-WORLD-0400
version: 0.1.0
status: archived
owners: [cohayes]
last_updated: 2025-11-17
superseded_by:
  - D-WORLD-0003      # Ward_Branch_Hierarchies
notes:
  - "Legacy ward structure draft; kept for reference and flavor only."
---

# Civic Facility Microdynamics: Soup Kitchens & Bunkhouses

> This document defines the **micro-scale behavior** of two canonical civic facilities:
> - Public **Soup Kitchens**
> - Public **Bunkhouses**  
> 
> These serve as the primary testbed environments for early simulations (including the “Dosadi soup kitchen” prototype).

---

## 1. Purpose & Scope

This doc focuses on **one kitchen** and **one bunkhouse** (or a combined complex) as a representative **civic hub** in a ward.

We specify:

- Facility roles and **local hierarchies** (who actually runs the place).  
- **Flows of people, resources, and information** through the facility.  
- Daily **cadence and phases** (queues, rushes, downtime).  
- Emergent **tensions, favors, and conflicts** that arise in these spaces.  
- Integration points to:
  - Civic, Industrial, Military, Espionage, and Clerical branches.  
  - Resource & water economy.  
  - Agent biology & drives.

Simulation intent:

- Provide a **concrete, richly structured node** that can be used:
  - As the first playable environment.  
  - As a template for other civic facilities (clinics, hostels, etc.).

---

## 2. Facility Types & Layouts

### 2.1 Canonical Facility Types

We define three canonical forms:

1. **Standalone Soup Kitchen**
   - Primary functions:
     - Cook and serve rations (food + water or water-equivalents).  
     - Act as a daily convergence node for residents and transients.
   - Typically:
     - Ground level access, queue space, serving line, back kitchen, storage, small office.

2. **Standalone Bunkhouse**
   - Primary functions:
     - Provide sleeping berths and minimal storage for residents.  
     - Harvest **respiration moisture** and latent humidity (dehumidifier arrays).
   - Typically:
     - Multiple dorm rooms, shared latrines, controlled entry/exit, a small clerk’s station.

3. **Combined Civic Hall (Kitchen + Bunkhouse Complex)**
   - Integrated facility where:
     - Lines for food and lines for beds cross and interact.  
     - One Boss and staff hierarchy oversees both functions.
   - Often:
     - The key civic node for lower wards and transient labor.

### 2.2 Spatial Zones

Common internal zones:

- **Queue Zone (Public Front)**
  - Exterior or interior foyer space where lines form.
  - Visibly patrolled by Civic stewards, sometimes militia.

- **Service Zone**
  - Serving counters, ladles, ration stampers, issue windows.
  - Where customers and staff interact under time pressure.

- **Back-of-House (Restricted)**
  - Kitchens, storage rooms, cold rooms, fuel stores.
  - For bunkhouses: laundry, maintenance closets, dehumidifier rooms.

- **Administrative Nook**
  - Desk(s) for records, ration tallies, incident logs, staff rota.
  - Often where:
    - Sub-Boss / Steward works.  
    - Enumerators and Investigators request documents.

- **Dormitories (Bunkhouses / Combined Halls)**
  - Tiered bunks, privacy curtains (if any), lockers or hooks.
  - Ventilation and moisture capture systems integrated into ceiling/walls.

---

## 3. Local Roles & Hierarchy

### 3.1 Role Mapping to Civic Branch

Within the hierarchy defined in D-WORLD-0003, a typical facility maps as:

- **Boss** – Facility Boss (Civic)
- **Sub-Boss** – Senior Steward / Night Steward
- **Line Staff** – Stewards, cooks, cleaners, bunk wardens, clerks

Formal reporting lines:

- Boss → Sub-Chief (Civic) → Staff Chief of Kitchens or Residences → Chief Administrator → Ward Lord

### 3.2 Typical On-Site Roles

1. **Facility Boss**
   - Responsible for:
     - Meeting daily ration and bed quotas.  
     - Staff discipline and rota.  
     - Reporting to Sub-Chief; handling inspections and audits.
   - Has:
     - Limited power to grant or deny access, adjust portions, and issue on-the-spot punishments.

2. **Senior Steward / Night Steward (Sub-Boss)**
   - Supervises:
     - Serving line during rush,  
     - Dormitories at night.
   - Decides:
     - Who gets admitted early, who gets turned away when capacity is exceeded.  
     - How strictly rules are enforced.

3. **Line Stewards (Serving Staff)**
   - Direct contact with residents:
     - Serving food, checking ration tokens/stamps, calming queues.
   - Often:
     - Key **informants** or **gatekeepers** in the local social economy.

4. **Cooks & Prep Crew**
   - Transform raw inputs (grain, slurry, protein pastes) into edible rations.
   - Their efficiency and skill:
     - Affect food quality and portion stability.  
     - Create opportunities for skimming (diverting food for sale or favors).

5. **Bunk Wardens (Bunkhouse-specific)**
   - Assign sleeping spots, enforce curfew and quiet hours.
   - Monitor:
     - Fights, theft, illicit use of bunks, unauthorized guests.

6. **Facility Clerk**
   - Maintains:
     - Daily headcounts, ration tallies, incident logs, maintenance requests.
   - Interface with:
     - Civic Sub-Chiefs, Scholars/Clerks enumerators, and Investigators.

7. **Security Presence**
   - Could be:
     - Civic guards,
     - Local militia detachment,
     - Or no formal presence (in rough wards).
   - Handle:
     - Queue brawls, theft, overt disruption.

---

## 4. Flows: People, Resources, Information

### 4.1 People Flow

Key categories of people:

- **Registered Residents**
  - Have ward papers or tokens; typically entitled to:
    - Regular rations,  
    - Priority in bed assignments.

- **Transient Laborers**
  - In-between contracts or newly arrived; uncertain status.
  - Often receive:
    - Reduced or conditional access.

- **Illicit / Unregistered Persons**
  - Smugglers, fugitives, off-ledger workers.
  - Risk:
    - Denial of service, arrest, or recruitment by black-market or espionage cells.

Flow phases:

1. **Arrival / Queue Formation**
   - Agents arrive based on:
     - Hunger, fatigue, safety needs, curfew constraints.

2. **Queue Dynamics**
   - Priority reordering via:
     - Status, permits, bribes, intimidation, favoritism.  
   - Events:
     - Queue cutting, disputes, queue collapse into brawl.

3. **Service Interaction**
   - Token checks, portion assignment, reprimands, notes of “troublemakers.”
   - Micro-decisions:
     - Slightly larger ladle scoop, or a watery scrape.

4. **Exit / Dispersal**
   - Fed agents disperse into ward, or move to bunkhouse line.
   - Unfed agents:
     - Seek alternatives (black market stalls, theft, violence).

### 4.2 Resource Flow (Food, Water, Moisture)

Inputs:

- **Food Inputs**
  - Allocated from Civic/Industrial stores (per D-SOC-0002).  
  - Vulnerable to:
    - Shortfalls, spoiled consignments, theft.

- **Water Inputs**
  - Allocated ward water quota (per D-ECON-0001).  
  - Kitchen water vs personal consumption vs cleaning.

- **Bunkhouse Moisture Capture**
  - Dehumidifier and ventilation systems:
    - Capture exhaled moisture.  
    - Produce reclaimed water sent up-chain.

Outputs:

- **Served Rations**
  - Calories + minimal hydration.
  - Portion size ties into:
    - Ward-level scarcity, facility-level corruption, Boss’s fear of audit.

- **Reclaimed Moisture**
  - Metered for:
    - Industrial or civic reuse.  
  - Becomes a key telemetry signal.

- **Waste Streams**
  - Leftover slop, inedible scraps, human waste:
    - Routed to reclamation (per Food/Waste docs).

### 4.3 Information Flow

- **Internal Operational Data**
  - Daily:
    - Headcounts, rations served, beds filled, fights, theft incidents.  
  - Maintained by:
    - Facility Clerk, Boss.

- **Upward Reports**
  - Periodic summaries to:
    - Sub-Chief and Staff Chief (Civic).  
  - Reason codes for:
    - Missed quotas, overcrowding, ration changes.

- **Espionage & Gossip Channels**
  - Stewards and wardens as:
    - Informants (paid or voluntary).  
  - Kitchens/bunkhouses as:
    - Prime rumor propagation hubs.

- **Clerical Observation**
  - Enumerators:
    - Spot-check queues, capacity, and conditions.  
    - Compare with official reports.

---

## 5. Daily Cadence & Phases

### 5.1 Example Daily Cycle (1.67 ticks/sec Timebase)

Define phases loosely (exact tick counts left to implementation):

1. **Pre-Opening Prep**
   - Cooks arrive, fires/fuel lit, bulk prep begins.
   - Bunkhouse:
     - Morning clearing of beds, basic cleaning, moisture system checks.

2. **Opening & First Rush**
   - Lines form rapidly:
     - Night-shift workers, early risers, those gaming the line.
   - Stewards:
     - Enforce order, gate access.

3. **Midday Lull**
   - Lower traffic; good time for:
     - Facility maintenance, quiet conversations, clandestine meetings.  
   - Clerk may:
     - Update ledgers, receive enumerators, talk to informants.

4. **Second Rush**
   - Work-shift changes bring a new wave.
   - Tension:
     - Higher late in the cycle if food looks short.

5. **Closing & Lockdown**
   - Queue cut; latecomers turned away.  
   - Cleanup, tally of remaining supplies, incident summary.

6. **Bunkhouse Night Cycle**
   - Check-in:
     - Assign bunks, verify tokens/permissions.  
   - Lights-out:
     - Enforced quiet, patrols, occasional raids/searches.  
   - Moisture capture:
     - Peak overnight, telemetry spikes.

---

## 6. Tension, Favors & Events

### 6.1 Favor Economies

Within the facility:

- Stewards and wardens can:
  - Advance someone in line, save a portion, assign a better bunk.
- In exchange for:
  - Small bribes (credits, contraband, information).  
  - Future favors or silence.

Persistent patterns:

- **Regulars** build soft priority due to:
  - Familiarity, minor service roles, or informant status.

### 6.2 Common Event Types

Potential simulation events:

- **Queue Brawl**
  - Triggered by:
    - Queue-cutting, scarcity, provocation, faction tensions.  
  - Outcomes:
    - Injuries, arrests, facility reputation shifts, militia involvement.

- **Food Shortfall**
  - Causes:
    - Under-delivery, theft, mismanagement, deliberate withholding.  
  - Responses:
    - Smaller portions, ration lottery, turning people away early.

- **Inspection / Audit**
  - Civic inspector + Clerk enumerator + possibly Investigator.
  - Check:
    - Ledgers vs observed headcount, facility conditions, rumor of abuse.

- **Espionage Operation**
  - Handlers using:
    - The queue or dorm as cover to meet informants.  
  - Moles:
    - Embedded as staff or regulars.

- **Curfew Raid (Bunkhouse)**
  - Militia or Investigators:
    - Searching for specific fugitives, contraband, or illicit gatherings.

- **Black-Market Contact**
  - Quiet offers of:
    - Off-ledger beds, better food, access to restricted water or meds, at a price.

---

## 7. Integration with Branches & Pillars

### 7.1 Civic Branch

- Owns and operates the facility:
  - Boss and Clerk are civic appointments.  
- Measured by:
  - Quota compliance, incident rate, complaints, and audit flags.

### 7.2 Industrial Branch

- Supplies:
  - Bulk food, fuel, cleaning chemicals, maintenance services.  
- Maintains:
  - Dehumidifiers, stoves, structural elements.

- Tension:
  - Civic may blame Industrial for shortages or equipment failures; Industrial may claim Civic is misusing supplies.

### 7.3 Military Branch

- Provides:
  - Security presence during peak tensions.  
  - Curfew enforcement in and around the facility.

- Interest:
  - Uses kitchens/bunkhouses to sense unrest and recruit informants or potential auxiliaries.

### 7.4 Espionage Branch

- Treats the facility as:
  - **High-value observation and recruiting ground**.  
- Operatives:
  - Informants among staff and regulars, moles as stewards or wardens, investigators during raids.

### 7.5 Scholars & Clerks

- Enumerators:
  - Sample queues and dorm occupancy, compare with official counts.  
- Clerical office:
  - Uses these facilities as key indicators of:
    - Popular discontent, hidden population, or misreported scarcity.

---

## 8. Simulation Hooks

### 8.1 Facility State Variables

For each kitchen / bunkhouse:

- `capacity_food` (rations per cycle)
- `capacity_beds`
- `current_stock_food`, `current_stock_water`
- `queue_length`, `queue_composition` (residents vs transients vs illicit)
- `facility_reputation` (trusted / disliked / feared / corrupt)
- `tension_level` (low/medium/high)
- `audit_risk_local` (perceived)

### 8.2 Agent-Level Interactions

Agents interact with the facility via:

- **Queue Behavior**
  - Join, leave, cut, defend position, pay for priority.

- **Service Outcomes**
  - Receive:
    - Full ration, partial ration, nothing.  
  - For bunkhouses:
    - Good bunk, poor bunk, no bed.

- **Relationship Changes**
  - With:
    - Stewards, wardens, other queue members.  
  - Affecting:
    - Future priority, safety, and rumor networks.

### 8.3 Event & Trigger Logic

Example triggers:

- `if current_stock_food < expected_demand` → raise `tension_level`.
- `if tension_level high && queue_length large` → probabilistic `QueueBrawl` event.
- `if anomaly_flags from clerks > threshold` → schedule `InspectionAudit` event.
- `if facility_reputation corrupt && audit_risk_local low` → increase `favor_economy_intensity` (more bribes, favoritism).

### 8.4 Hooks to Other Docs

- **D-AGENT-0001_Human_Agent_Biology_and_Drives**:
  - Hunger, thirst, fatigue drive agents to these facilities and shape decision urgency.

- **D-ECON-0001_Ward_Resource_and_Water_Economy**:
  - Determines inbound food/water supply, moisture reclamation value.

- **D-INFO-0003_Information_Flows_and_Report_Credibility**:
  - Facility reports feed into credibility scores; events change perceived honesty.

- **D-INFO-0002_Espionage_Branch**:
  - Defines operative roles active inside facilities.

---

## 9. Open Design Questions

For later refinement:

- Should some kitchens be **privileged nodes** (e.g., “the Duke’s kitchen,” better quality, higher security), while others are near-feral?
- How much **variance** in queue norms exists by ward (strict numeric order vs fluid, violence-based order)?
- Under what conditions does a facility **flip reputation**:
  - From “lifeline” to “trap” (associated with arrests, raids, purges)?
- Do bunkhouses ever become **de facto faction spaces**:
  - e.g., a dorm that is effectively a gang’s territory at night?

These should be answered in tandem with early simulation prototypes and playtests.
