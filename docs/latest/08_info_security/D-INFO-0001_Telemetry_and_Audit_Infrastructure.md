---
title: Telemetry_and_Audit_Infrastructure
doc_id: D-INFO-0001
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
depends_on:
  - D-WORLD-0003   # Ward_Branch_Hierarchies
  - D-ECON-0001    # Ward_Resource_and_Water_Economy (placeholder)
  - D-WORLD-0004   # Civic_Facility_Microdynamics_Soup_Kitchens_and_Bunkhouses
  - D-INFO-0003    # Information_Flows_and_Report_Credibility
  - D-INFO-0004    # Scholars_and_Clerks_Branch
---

# Telemetry & Audit Infrastructure

> This document defines the **“hard measurement” layer** of the Dosadi regime:
> - What is instrumented and counted.
> - How measurements travel and are stored.
> - How audits use those measurements to challenge or confirm human reports.

---

## 1. Purpose & Scope

While reports from branches (Civic, Industrial, Military, Espionage) are mediated by loyalty, fear, and self-interest, **telemetry & audit infrastructure** provides:

- A set of **physical and procedural instruments** (meters, stamps, logs) that approximate “ground truth.”
- A framework for **audits** that compare:
  - Reported numbers vs instrument readings vs on-site observation.

This doc describes:

- **Measurement domains** (what gets measured).  
- **Devices and log systems** used across wards.  
- **Data paths** from facility-level readings to ward and crown-level summaries.  
- **Tampering and failure modes** and how audits respond.  
- Simulation hooks for:
  - Telemetry coverage, reliability, tamper difficulty, and audit events.

---

## 2. Measurement Domains

### 2.1 Water & Moisture

Core to Dosadi’s survival:

- **Well Output & Allocation**
  - Meters at:
    - The central well(s) or primary water processing nodes.
    - Ward intake points (pipes, tanks, cisterns).
  - Track:
    - Flow volumes per time unit (per simulation tick or cycle).

- **Ward Distribution**
  - Meters and tallies at:
    - Branch-level allocations (Civic, Industrial, Military).  
    - Major sub-allocations (e.g., bunkhouse dehumidifier returns, industrial condensers).

- **Moisture Capture**
  - Dehumidifier counters at:
    - Bunkhouses and dormitories (respiration harvest).  
    - Industrial condensers, dedicated moisture farms.
  - Counts:
    - Total moisture recovered per cycle, per facility.

### 2.2 Food & Rations

- **Bulk Inventory**
  - Weights/containers logged at:
    - Civic warehouses, industrial processing plants, kitchen storerooms.
- **Ration Issuance**
  - Systems:
    - Physical ration tokens or stamp-books per person.  
    - Ledger lines for bulk “served rations” per service.
  - Optionally:
    - Crude portion counters (e.g. ladle counts, serving counters).

### 2.3 Population & Access

- **Resident Rolls & Work Rosters**
  - Maintained primarily by Civic and Clerks:
    - Official residents, registered workers, assigned dorm occupants.

- **Access Logs**
  - For higher-control facilities:
    - Entry/exit tallies at bunkhouses, industrial sites, secure civic hubs.
  - Range from:
    - Manual tallies by gate stewards,  
    - To mechanical turnstile counters.

### 2.4 Movement & Logistics

- **Cargo Manifests**
  - Log sheets for:
    - Food, water, fuel, scrap, and manufactured goods in transit.
  - Associated with:
    - Vehicle IDs, driver/crew identities, origin and destination.

- **Transport Utilization**
  - Trips per vehicle per cycle.  
  - Routes and approximate load (where measured).

### 2.5 Enforcement & Coercion

- **Patrol Logs**
  - Recorded patrol routes, times, and personnel.
- **Arrest / Incident Logs**
  - Counts of:
    - Arrests, fines, fights, injuries, deaths.
- **Weapon & Ammo Tallies** (for some wards)
  - Issuance and return ledgers for:
    - Firearms, ammunition, stun weapons, etc.

These domains provide **low-level signals** that can be compared against:
- Branch reports,  
- Espionage anecdotes,  
- Clerk baselines.

---

## 3. Telemetry Devices & Record Systems

### 3.1 Mechanical & Hybrid Meters

Devices include:

- **Flow Meters**
  - Mechanical or hybrid devices on pipes and condensation lines.  
  - Typically simple, rugged designs with:
    - Dial readouts, stamped reading tickets.

- **Counter Wheels / Turnstiles**
  - For counting entries/exits.
  - Used at:
    - Bunkhouses, ration halls, certain work sites.

- **Tank/Reservoir Gauges**
  - Float-based or weight-based level indicators for:
    - Water tanks, fuel stores, bulk food hoppers.

### 3.2 Tokens, Stamps & Ledger-Integrated Systems

- **Ration Tokens / Stamp Books**
  - Each registered resident:
    - Has a ration record (physical booklet, token bandolier, or equivalent).  
  - Kitchens:
    - Stamp or mark each claim.
- **License Documents**
  - Property, equipment, scavenging rights:
    - Often include counters (max draws, days active, etc.).

- **Facility Ledgers**
  - Every serious facility (kitchen, bunkhouse, workshop) maintains:
    - A daily ledger of input, output, and notable incidents.
  - May be:
    - On paper, slate, or mechanical register.

### 3.3 Ownership & Maintenance

- **Industrial Branch**
  - Maintains most physical devices:
    - Meters, dehumidifiers, gauges, turnstiles.
- **Civic Branch**
  - Maintains:
    - Access logs, ration stamps, local facility ledgers.
- **Scholars & Clerks**
  - Define:
    - Standard measurement units, form layouts, and logging procedures.

---

## 4. Data Path & Storage

### 4.1 From Device to Facility Ledger

At the lowest level:

1. A **device reading** is taken:
   - A flow meter’s dial is read,  
   - A turnstile counter is recorded,  
   - A tank gauge reading is noted.
2. A **facility clerk or steward** writes:
   - The reading into the facility’s operational ledger,  
   - Alongside time, shift and staff.

Frequency:

- **Routine**:
  - Once per cycle or per shift.
- **Special**:
  - Before/after suspected tampering, audits, or major incidents.

### 4.2 Facility → Branch → Scholars & Clerks

Data flows upward in **summarized form**:

- Facility → Sub-Chief (branch)  
- Sub-Chief → Staff Chief → Branch Head  
- Branch Head → Ward Clerks (numeric tables) → Regional / Central Clerks (aggregates)

At each stage:

- Numbers can be:
  - Passed through faithfully,  
  - Rounded, “massaged,” or selectively omitted.

Scholars & Clerks:

- Maintain:
  - **Ward ledgers** that represent the crown’s version of measurements.  
- Use:
  - Baseline models to detect anomalies in telemetry readings vs expectations.

---

## 5. Tampering & Failure Modes

### 5.1 Physical Bypass

- **Illegal Taps**
  - Hidden pipes drawing water before/after meters.
- **Shadow Lines**
  - Parallel unmetered conduits feeding:
    - Black-market kitchens, private baths, or protected enclaves.

### 5.2 Device Manipulation

- **Meter Rolling / Freezing**
  - Jamming or reversing mechanical counters to under-report usage.
- **Calibration Drift**
  - “Accidentally” leaving devices miscalibrated in a favorable direction.
- **Partial Disassembly**
  - Leaving a cover “loose” so a friendly operator can adjust readings.

### 5.3 Ledger Manipulation

- **Ghost Entries**
  - Inventing shipments, residents, or facilities.
- **Omitted Lines**
  - Skipping undesirable readings.
- **Rewritten Pages**
  - Replacing previous entries after a bad day.

### 5.4 Genuine Failures

- **Wear & Tear**
  - Old devices simply failing in unforgiving conditions.
- **Environmental Impacts**
  - Dust, heat, corrosion affecting precision.
- **Operator Error**
  - Misread dials, swapped numbers, illiterate staff.

These genuine failures:

- Provide cover for deliberate manipulation.
- Feed directly into reason codes (e.g., “equipment malfunction”).

---

## 6. Audit Processes

### 6.1 Routine Audits

Scheduled at intervals defined by:

- Ward risk profile,  
- Branch criticality,  
- Clerk office capacity.

Routine audit pattern:

1. **Notice (optional)**:
   - Ward leadership may be informed of a general audit window.
2. **Sampling Plan**:
   - Clerks select a subset of facilities/devices:
     - Kitchens, bunkhouses, key industrial sites.
3. **On-Site Checks**:
   - Enumerators and technical reps:
     - Read devices directly, inspect condition, compare to ledger entries.
4. **Reconciliation**:
   - Compare:
     - Device readings vs facility ledger vs branch summaries.
5. **Reporting**:
   - Clerk produces:
     - An audit report with anomalies, suspected manipulations, and recommendations.

### 6.2 Triggered Audits

Triggered when:

- **Credibility system flags**:
  - Repeated improbable reason codes,  
  - Statistically out-of-range performance,  
  - Conflicts between espionage reports and branch numbers.
- **Political pressure**:
  - Complaints from rivals, unrest spikes, or king’s curiosity.

Triggered audits:

- Are often **more intense and adversarial**:
  - May involve Investigators and militia support.  
  - May include:
    - Surprise inspections, seizure of ledgers, temporary device control.

### 6.3 Audit Outcomes

Possible outcomes:

- **Clean Bill of Health**
  - No significant discrepancies found.
- **Noted Irregularities**
  - “Fix your devices,” “update procedures,” warnings issued.
- **Confirmed Manipulation**
  - Sanctions:
    - Fines, demotions, removal of facility Bosses, or branch-level punishment.
- **Structural Findings**
  - “Devices systematically miscalibrated across ward”:
    - Leads to ward-level restructuring, upgrades, or external oversight.

---

## 7. Telemetry in the Credibility System

### 7.1 Telemetry Confidence

Not all telemetry is equal. Each **telemetry channel** or device may have:

- `reliability` (how often it fails honestly).
- `tamper_difficulty` (how hard it is to manipulate unnoticed).
- `capture_level` (degree of subversion by local actors).

Scholars & Clerks:

- Maintain meta-knowledge:
  - Which devices and channels are trustworthy.
  - Which ones have a history of suspicious “failures.”

### 7.2 Weighting vs Human Reports

When evaluating a claim:

- If **high-confidence telemetry** contradicts a report:
  - Credibility of the human report drops sharply.
- If **telemetry is known to be compromised**:
  - Reports from some branches (e.g., Espionage, on-site witnesses) may be preferred.

In simulation terms:

- A **credibility evaluator** takes:
  - `report`, `telemetry_snapshot`, `source_history`, `device_history`
- And outputs:
  - Updated `credibility_score`,  
  - Optional `audit_trigger` flag.

---

## 8. Simulation Hooks

### 8.1 Telemetry Entities

Introduce entities such as:

- `Meter`:
  - Fields:
    - `domain` (water, moisture, ration, access, etc.)
    - `location` (facility), `owner_branch`
    - `reliability`, `tamper_difficulty`
    - `capture_level` (0–1)
- `TelemetryChannel`:
  - Aggregates:
    - All meters & logs for a given domain in a ward.
- `AuditEvent`:
  - Represents:
    - A routine or triggered audit, with:
      - `scope`, `participants`, `findings`.

### 8.2 Ward-Level Parameters

Per ward:

- `telemetry_coverage` (0–1):
  - Fraction of key flows (water, food, beds, population movements) that are metered/logged.
- `telemetry_quality`:
  - Average reliability of devices and logging practices.
- `audit_intensity`:
  - Frequency and depth of audits.

These factors influence:

- The **effective strength** of the credibility system.  
- How risky sustained lying is for branches.

### 8.3 Example Logic Sketch (Non-Canonical)

For each reporting cycle:

1. **Generate True State**
   - Actual water flows, rations, headcounts, etc.
2. **Telemetry Layer**
   - Each `Meter` samples that state with:
     - Noise (due to reliability),  
     - Potential manipulation (due to capture_level and agent decisions).
3. **Reporting Layer**
   - Facilities and branches file reports using their internal truthfulness models (D-INFO-0003).
4. **Evaluation Layer**
   - Clerks compare:
     - Aggregated telemetry vs reported values.  
   - Compute deviation metrics and update:
     - `credibility_score` per facility/branch.
   - May queue `AuditEvent`s.

5. **Audit Layer**
   - For triggered audits:
     - Override normal flow:
       - Direct device readings, ledger seizures, cross-interviews.

### 8.4 Interactions with Other Docs

- **D-INFO-0003_Information_Flows_and_Report_Credibility**
  - Telemetry feeds directly into the credibility scoring pipeline.
- **D-INFO-0004_Scholars_and_Clerks_Branch**
  - Defines who maintains baselines and runs audits.
- **D-WORLD-0004_Civic_Facility_Microdynamics_Soup_Kitchens_and_Bunkhouses**
  - Specifies which facility elements are measured (queue counts, moisture capture, rations served).
- **D-ECON-0001_Ward_Resource_and_Water_Economy**
  - Defines constraints that telemetry readings must roughly obey.

---

## 9. Open Design Questions

- How **granular** should telemetry be in early prototypes?
  - Fully simulated meters per facility vs simple ward-level aggregates.
- Should some wards be deliberately **under-instrumented**?
  - To create “dark zones” where reports are hard to verify.
- How do **technological upgrades** (better meters, automated logs) roll out?
  - As rare events, policy choices, or long-term progress?
- To what degree should **players/agents** be able to:
  - Target devices and audit processes directly (e.g., sabotage, bribe auditors)?

These can be tuned once early simulations reveal where telemetry adds the most tension and interesting decisions.
