---
title: Civic_Microdynamics_Body_Disposal_and_Reclamation
doc_id: D-CIV-0005
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
depends_on:
  - D-WORLD-0003  # Ward_Branch_Hierarchies
  - D-ECON-0001   # Dosadi_Economic_Systems
  - D-ECON-0003   # Credits_and_FX
  - D-ECON-0005   # Food_and_Rations_Flow
  - D-ECON-0006   # Maintenance_Fault_Loop
  - D-ECON-0008   # Production_and_Fabrication
  - D-ECON-0009   # Financial_Ledgers_and_Taxation
  - D-INFO-0001   # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002   # Espionage_Branch
  - D-INFO-0003   # Information_Flows_and_Report_Credibility
  - D-INFO-0004   # Scholars_and_Clerks_Branch
  - D-INFO-0005   # Record_Types_and_Information_Surfaces
  - D-CIV-0002    # Civic_Microdynamics_Clinics_and_Triage_Halls
  - D-CIV-0004    # Civic_Microdynamics_Courts_and_Justice_Halls
---

# Civic Microdynamics: Body Disposal & Reclamation Nodes

> This document defines **what happens to bodies after death** in the Dosadi wards:
> - How corpses move from clinics, bunkhouses, streets, and execution grounds into civic/industrial loops.
> - When organs are preserved vs when entire bodies are reclaimed as water and fuel.
> - How body handling intersects with law, taboo, economy, and information systems.
> - Where black markets, cover-ups, and quiet kindness hide inside a brutally utilitarian system.

On Dosadi, a corpse is:

- A **legal object** (proof of death, evidence).
- A **resource** (water, organs, materials).
- A **signal** (about violence, disease, and power).

For most deaths:

- If **organs are in demand and viable**, they are harvested and preserved.
- The remaining mass becomes:
  - **Water** (reclaimed to liters) and
  - **Fuel / feedstock** (char, gas, industrial reagents).

---

## 1. Facility Archetypes

We define four main node types in the post-mortem chain:

1. **Clinic Morgues & Holding Rooms** (MORGUE_CLINIC)
2. **Ward Reclamation Furnaces & Body Reclaimers** (RECLAIMER_BODY)
3. **Organ Banks & Preservation Rooms** (ORG_BANK)
4. **Taboo / Ritual Disposal Sites** (DISPOSAL_TABOO)

### 1.1 Clinic Morgues & Holding Rooms (MORGUE_CLINIC)

- Upstream from:
  - Clinics & triage halls (D-CIV-0002), courts (executions), bunkhouses, streets.
- Roles:
  - Short-term storage; basic washing, tagging, initial inspection.
  - Stabilize bodies (cooling, partial sealing) while legal & economic decisions are made.
- Constraints:
  - Limited capacity; high infection risk if backlog grows.
- Typical time horizon:
  - Hours to a day for “ordinary” corpses before transfer.

### 1.2 Ward Reclamation Furnaces & Body Reclaimers (RECLAIMER_BODY)

Industrial facilities where:

- Corpses are:
  - Decontaminated (if possible),
  - Processed to extract:
    - **Water** (primary yield).
    - **Energy / fuel** (char, gas, sludge for burners or reactors).
    - **Residual solids** (bone, ash) for further use/disposal.

Reclaimers may be:

- Connected to:
  - Ward-wide water infrastructure and power systems.
- Co-located with:
  - Other reclaimers (waste, sewage, offal) to share thermal/hygiene systems.

### 1.3 Organ Banks & Preservation Rooms (ORG_BANK)

Specialized medical-industrial nodes:

- Attached to:
  - High-tier clinics, black-market backrooms, or noble compounds.
- Purpose:
  - Salvage organs/tissues **when there is demand and viable time window**.
- Outputs:
  - Chilled or preserved organs for transplantation or industrial use (hormones, biochem).
- Access:
  - Strictly rationed and politically charged; black-market diversion is endemic.

### 1.4 Taboo / Ritual Disposal Sites (DISPOSAL_TABOO)

Not all wards treat bodies purely as feedstock:

- Some maintain:
  - Ossuaries, char pits, symbolic burial walls, or vaporization chambers.
- Purpose:
  - Manage **taboo pressure** and factional beliefs without sacrificing too much resource efficiency.
- Use:
  - Often reserved for:
    - High-status corpses,
    - “Untouchable” bodies (contaminated, cursed),
    - Politically sensitive dead.

---

## 2. Roles & Responsibility Chains

### 2.1 Civic & Industrial Roles

- **Reclamation Chief (Body)**
  - Reports to:
    - Civic branch (waste/reclamation) and/or Industrial branch (utilities).
  - Responsible for:
    - Throughput, hygiene, yield (L of water per body), safety, smell and risk management.

- **Morgue Steward**
  - Manages:
    - Intake, storage order, basic preparation, tagging, tracking.
  - Decides:
    - Which bodies move to organ bank vs direct reclamation vs ritual handling.

- **Cutters / Autopsy Techs**
  - Perform:
    - Organ harvesting when authorized.
    - Limited forensic cuts for courts.

- **Reclaimer Operators**
  - Run:
    - Furnaces, distillers, scrubbers, filters.
  - Adjust:
    - Thermal curves, dwell times, contamination parameters.

- **Cart Crews / Body Porters**
  - Move:
    - Corpses between clinics, execution sites, morgues, reclaimers, and taboo sites.
  - High exposure:
    - To rumor, hazards, and occasional targeted attacks.

### 2.2 Oversight & External Actors

- **Justice Liaison**
  - Ensures:
    - Legal cases close properly:
      - Identity confirmed, cause of death recorded, orders for cremation/reclamation valid.

- **Health / Epidemic Inspectors**
  - Monitor:
    - Disease markers, unusual mortality spikes, reclaimer hygiene.

- **Clerical Recorders**
  - Maintain:
    - Death registers, yield ledgers, next-of-kin claims, unclaimed lists.

- **Black-Market Actors**
  - Divert:
    - Select corpses or organs before they hit official channels.
  - Launder:
    - “Lost” bodies and forged death certificates.

---

## 3. Body State & Classification

When an agent dies, the simulation creates a **Body object**.

Key fields:

- `body_id`, `agent_id`
- `source_facility`:
  - CLINIC, STREET, BUNKHOUSE, WORKSHOP, COURT_EXECUTION, OUTSIDE, etc.
- `time_of_death`
- `cause_of_death`:
  - Trauma, disease, exposure, execution, “unknown”, etc.
- `contamination_status`:
  - `CLEAN`, `INFECTIOUS`, `TOXIC`, `CHEMICAL`, `UNKNOWN`.
- `organ_viability_timer`:
  - Remaining window (ticks) in which organ harvest yields are viable.
- `organ_demand_score`:
  - From global/ward-level demand (organs needed vs storage vs backlog).
- `water_mass_estimate_L`
- `dry_mass_estimate_kg`
- `suit_and_gear`:
  - Attached inventory; may be stripped before or after processing.
- `legal_flags`:
  - “Evidence required”, “Execution order”, “Unclaimed”, “Clan claim pending”.

This classification drives:

- Whether organs are salvaged.
- Whether the body is routed to high-tier reclaimer, special handling, or taboo disposal.

---

## 4. Flow: From Death to Reclamation

### 4.1 Stage 1 — Pronouncement & Tagging

1. **Death Event**
   - Occurs at:
     - Clinic, street, workplace, bunkhouse, battle, execution ground.
2. **Initial Tagging**
   - Facility staff or militia:
     - Assign minimal fields:
       - `cause_of_death`, `contamination_status` (rough), `legal_flags`.
3. **Transport to Morgue**
   - Cart crew moves body to nearest:
     - MORGUE_CLINIC or direct to RECLAIMER_BODY in crisis conditions.

### 4.2 Stage 2 — Claim Window

At the morgue:

- **Claim Eligibility**
  - Factions, families, guilds may:
    - Claim body for ritual disposal or partial reclamation, if:
      - They can pay fees and/or forego water yield.
- **Economic vs Taboo Tradeoff**
  - Default regime:
    - **Unclaimed bodies → full state reclamation**.
  - Policy knobs:
    - Whether claimants can:
      - Purchase organs, “water share”, or symbolic remnants.

### 4.3 Stage 3 — Organ Salvage Decision

For each body:

1. Check `organ_viability_timer` and `organ_demand_score`.
2. If:
   - `organ_viability_timer > threshold` **and**
   - `organ_demand_score > salvage_min`
   - → route to ORG_BANK “cut table”.
3. Else:
   - Mark for direct reclamation; maybe a quick minimal inspection.

Organ salvage yields:

- `organs_salvaged[]`:
  - Each with target use (transplant/industrial), grade, storage method.
- **Reduced water yield**:
  - Some water is lost to preservation media and discard.

### 4.4 Stage 4 — Suit & Gear Stripping

Before heat-intensive processes:

- Remove:
  - Environmental suits, armor, tools, ID tokens, implants.
- Routing:
  - Reusable suits → maintenance / refurbishment loops.
  - Damaged suits → material reclamation (plastics, metals, filters).
  - Identifying implants/devices → info/security handling.

Suit stripping is:

- A major **loot point**:
  - For both legitimate maintenance culture and opportunists.

### 4.5 Stage 5 — Body Reclamation

At RECLAIMER_BODY:

Procedural view (high-level):

1. **Loading & Pre-Treatment**
   - Batch bodies by:
     - Contamination class, size, and organ state.
   - Apply:
     - Quick disinfectants if economical.

2. **Thermal / Chemical Cycle**
   - Raise to temperature/conditions that:
     - Maximize water vapor and condensate,
     - Neutralize pathogens,
     - Convert remaining mass to char/sludge.

3. **Water Capture**
   - Condense:
     - Vapor to water; push through filters.
   - Grade:
     - As `industrial`, `potable-after-treatment`, or `discard`.

4. **Fuel & Residuals**
   - Char, oils, gas streams routed to:
     - Power plants, industrial burners, or chemical plants.
   - Bone/ash:
     - Used as filler in construction materials or sent to taboo disposal.

Outputs logged as:

- `water_yield_L`, `energy_yield_units`, `residual_mass_kg`.

---

## 5. Organs & Demand

### 5.1 Organ Types & Uses (Abstract)

We avoid explicit biological gore; we care about **state and value**:

- **Transplant-Grade Organs**
  - Directly support high-tier clinics:
    - Respiratory, circulatory, filtration capacity, etc.
- **Biochemical / Industrial Tissues**
  - Sources of:
    - Hormones, catalysts, research material (clandestine).
- **Black-Market Mods**
  - Unofficial augmentations:
    - Enhanced endurance, perception tweaks, questionable implants.

### 5.2 Demand Drivers

Organ demand is driven by:

- Clinic load:
  - Number of critical patients queued for transplants.
- Wealth & status:
  - Nobles, high-value guild workers get priority.
- Black-market orders:
  - Espionage, gangs, and experimental labs.

A simple model:

- `organ_demand_score` per organ type per ward:
  - Rising with:
    - Clinic waiting lists, noble/patron requests, research orders.
  - Falling with:
    - Successful harvests, reduced need, or moral/political clampdowns.

### 5.3 Ethical & Taboo Zones

Wards differ:

- Some:
  - Treat organ harvest as routine.
- Others:
  - Restrict salvage from certain statuses (children, elites, religious sects).
- Black markets:
  - Thrive where official bans create high price spreads.

---

## 6. Records & Evidence

Tie to D-INFO-0005.

### 6.1 Record Types

- **LEGAL**
  - Death certification, cause, identity, relation to cases.
- **LEDGER**
  - Water yield, disposal costs, organ/tissue sales, ritual fees.
- **OP_LOG**
  - Bodies processed per block, yields, contamination incidents.
- **FORMAL_REPORT**
  - Outbreak-related deaths, mass casualty events, execution tallies.
- **SHADOW**
  - Diverted corpses, unsanctioned organ harvests, falsified causes of death.

### 6.2 Information Surfaces

- **Morgue List Boards**
  - Names/IDs of recent dead, claim deadlines.
- **Yield Dashboards**
  - For reclamation chiefs; not generally public.
- **Court & Clinic Interfaces**
  - “Body released?”, “Autopsy required?”, “Execution carried out?”.

---

## 7. Risk, Disease & Smell

### 7.1 Facility State Variables

For RECLAIMER_BODY & MORGUE_CLINIC:

- `capacity_bodies`
- `queue_length_bodies`
- `biohazard_load_body`
- `GovLegit_body_handling`
- `corruption_level_body`
- `odor_index`:
  - Affects:
    - Local environment quality, agent stress, property values.
- `inspection_pressure_body`

### 7.2 Backlog & Outbreaks

If `queue_length_bodies` exceeds thresholds:

- Rising `biohazard_load_body` and `odor_index`:
  - Increase:
    - Disease spread probability to nearby bunkhouses/kitchens.
- May trigger:
  - Health inspector visits, regime crackdowns, or mob violence.

---

## 8. Micro-Events & Hooks

### 8.1 Civic / Social Micro-Events

- **Mercy vs Efficiency**
  - A morgue steward quietly:
    - Diverts a body to taboo disposal instead of full reclamation at family request.
- **Grief & Vengeance**
  - Families discover:
    - Loved one’s body was fully reclaimed despite promises → resentment against regime.

### 8.2 Economic Micro-Events

- **Preferred Corpses**
  - High-yield bodies (well-hydrated, larger mass) may be:
    - Prioritized in crisis to maximize `water_yield_L`.
- **Organ Auctions**
  - Clinics and factions:
    - Bid for scarce transplant-grade organs.

### 8.3 Legal & Espionage Micro-Events

- **Evidence Destruction**
  - Bodies linked to sensitive cases:
    - Pushed early into furnaces to erase physical proof.
- **Identity Confusion**
  - Tags swapped:
    - To fake someone’s death or misdirect investigators.
- **Black-Market Channel**
  - Cart crew “loses” a body:
    - It surfaces later in a different ward’s organ bank.

---

## 9. Simulation Hooks & Minimal Prototype

### 9.1 Minimal Body Schema

```json
{
  "body_id": "B_W21_000873",
  "agent_id": "agent_4321",
  "source_facility": "CLINIC",
  "cause_of_death": "infection_acute",
  "contamination_status": "INFECTIOUS",
  "time_of_death": 128340,
  "organ_viability_timer": 7200,
  "organ_demand_score": 0.65,
  "water_mass_estimate_L": 45,
  "dry_mass_estimate_kg": 12,
  "legal_flags": ["EVIDENCE_REQUIRED"],
  "suit_and_gear": ["suit_mid_021", "id_chip_8872"]
}
```

### 9.2 Minimal Reclaimer Facility Schema

```json
{
  "facility_id": "W21_RECLAIMER_BODY_01",
  "type": "RECLAIMER_BODY",
  "ward": "W21",
  "capacity_bodies": 50,
  "queue_length_bodies": 18,
  "biohazard_load_body": 0.4,
  "GovLegit_body_handling": 0.7,
  "corruption_level_body": 0.3,
  "odor_index": 0.5,
  "inspection_pressure_body": 0.4
}
```

### 9.3 Minimal Loop (Per Processing Block)

1. **Intake**
   - Pull bodies from morgue queue, limited by `capacity_bodies`.
2. **Classification Update**
   - Decrement `organ_viability_timer`.
   - Recompute `organ_demand_score` against ward-level demand.
3. **Salvage Decision**
   - For each body:
     - If salvage conditions met → send to ORG_BANK.
     - Else → direct to reclamation.
4. **Suit & Gear Strip**
   - Update:
     - Suit inventories, salvage parts, legal custody of IDs.
5. **Reclamation Cycle**
   - For each processed body batch:
     - Generate `water_yield_L`, `energy_yield_units`, `residual_mass_kg`.
     - Update ward water stocks & ledgers.
6. **Record & Risk Updates**
   - Emit:
     - LEDGER entries, OP_LOG, LEGAL confirmations, SHADOW where applicable.
   - Adjust:
     - `biohazard_load_body`, `odor_index`, outbreak risk in nearby venues.

---

## 10. Open Questions

For future documents or ADRs:

- How much **epidemiology** do we want:
  - Bodies as contagion vs simple infection scalar?
- Should some wards:
  - Refuse body reclamation entirely for certain factions/classes?
- How do we:
  - Bind body water yields into **Barrel Cascade** accounting and audits?
- Do we model:
  - Long-term psychological impact on workers routinely handling corpses?

For now, this microdynamics layer aims to:

- Close the loop between **death, water, power, and taboo**.
- Provide sharp hooks into:
  - Clinics, courts, economy, rumor, and agent ethics.
