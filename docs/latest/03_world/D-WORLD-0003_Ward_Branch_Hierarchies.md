---
title: Ward_Branch_Hierarchies
doc_id: D-WORLD-0003
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-14
depends_on:
  - D-RUNTIME-0001   # Simulation_Timebase
---

# Ward Branch Hierarchies

## 1. Purpose & Scope

This document defines the **three legitimized power branches** within a ward:

- **Civic Branch** – services, administration, housing, food, basic justice.  
- **Industrial Branch** – production, infrastructure, maintenance, technical guilds.  
- **Military Branch** – militias, security forces, ward-level armed power.

It describes:

- The **hierarchy** within each branch (who negotiates with whom).  
- How **legitimacy** works as a resource and a weapon.  
- How **information loss and distortion** increase up the chain.  
- How **corruption and disloyalty** are punished at different levels.  
- The relationship between the **official tree** and **shadow coalitions**.

This is primarily a **simulation-facing design doc**: Codex and runtime systems should use these structures when assigning roles, computing loyalties, and resolving negotiations within a ward.

---

## 2. Core Concepts

### 2.1 Legitimized vs. Non-Legitimized Factions

Each ward has a **lord**. The lord formally recognizes certain factions as **legitimized** under one of the three branches:

- **Legitimized factions**:
  - Appear on the official branch hierarchy.
  - Have formal contracts and obligations with the ward lord.
  - Receive legal protection, access to resources, and bargaining channels.

- **Non-legitimized factions** (neutral, hostile, or semi-tolerated):
  - Exist **outside** the official tree.
  - Have **reduced direct bargaining power** with the lord.
  - Rely on intermediaries, crisis leverage, or shadow deals to affect policy.

Legitimacy is **not binary** in practice; it can be modeled as a ladder (see §5):

- `outlawed` → `tolerated` → `recognized` → `favored` → `indispensable`

The lord (and sometimes higher powers) can **move factions up or down** this ladder in response to performance, loyalty, and leverage.

---

### 2.2 Hierarchy as Negotiation Graph

The hierarchies described here are **not** pure obedience trees. They are:

- **Communication channels** – who can regularly speak to whom.  
- **Negotiation paths** – who must be placated or persuaded to obtain resources.  
- **Reporting structures** – who provides information upward, and in what form.

At every link in the chain:

- Orders can be delayed, reinterpreted, or quietly sabotaged.  
- Reports can be filtered, biased, or falsified.  
- Bargaining and side deals can alter how policy is actually implemented.

---

### 2.3 Information Gradient

Higher levels have **broader control** but **poorer visibility**:

- **Top tiers (Lord, Branch Heads)**:
  - See aggregated indicators and anecdotes.
  - Depend entirely on subordinate reports and select informants.
  - Have the greatest power to alter legitimacy and budgets.

- **Mid tiers**:
  - See regional performance metrics and facility rollups.
  - Can distort or curate what flows upward.

- **Low tiers (Bosses, Sub-bosses, Sergeants, Stewards)**:
  - See **true local conditions**: queues, morale, equipment failures, violence.
  - Have very limited formal authority but can severely skew actual outcomes.

Simulation rule of thumb:

> **Perceived state** at Tier N is a noisy, biased function of **true state** at Tier N+1 and below.

---

### 2.4 Corruption, Discipline & Realignment

Corruption or disloyalty at different levels is handled differently:

- **Low / mid levels**:
  - **Preferred remedy**: replace or reshuffle individuals (Bosses, Sub-bosses, Warband Leaders, Guild Leaders).
  - **Escalated remedy**: de-legitimize specific facilities (e.g., a bunkhouse or workshop drops out of the civic/industrial tree and slides toward the shadow coalitions).

- **Top level (branch heads)**:
  - **Preferred remedy**: bring charges, force resignation, or replace with a rival from within the branch.
  - **If too entrenched**: the lord may **un-legitimize the entire branch leader**, causing:
    - The leader to defect with loyal subordinates/facilities.
    - The formation of a new semi-autonomous power block.
    - New alliances between the lord and previously neutral or hostile factions.

This creates **branch-level crises** that can realign the ward’s politics and power balance.

---

## 3. Common Command Tiers

Each branch shares a **five-tier hierarchy** under the ward lord. Names differ by branch, but the underlying semantics are the same.

### 3.1 Tier Semantics

**Tier 0 – Ward Lord (not part of any branch)**  
- Owns ultimate legitimacy within the ward.  
- Grants and revokes recognition for factions.  
- Negotiates major contracts, taxes, and obligations.  

**Tier 1 – Branch Head (Ward-wide operations)**  
- Negotiates directly with the lord on behalf of the branch.  
- Allocates budgets, priorities, and major appointments downwards.  
- Sees broad, delayed, and filtered information.

**Tier 2 – Sector Chiefs / High Command**  
- Translate branch-level policy into regional quotas and directives.  
- Manage multiple regions, sectors, or large formations.  
- Oversee several Tier 3 leaders and their domains.

**Tier 3 – Regional / Guild / Formation Leaders**  
- Control multiple facilities, guilds, or warbands.  
- Decide which units/facilities receive scarce resources.  
- Can significantly distort the picture seen at Tiers 1–2.

**Tier 4 – Facility / Unit Bosses**  
- Run single facilities or units (bunkhouse, workshop, kitchen, patrol group).  
- Execute daily orders and manage rosters.  
- Are primary points of contact for frontline workers/soldiers.

**Tier 5 – Frontline Supervisors & NCOs**  
- Oversee small teams and day-to-day operations.  
- Directly manage queues, work details, squad maneuvers, etc.  
- Are the hands through which branch policy becomes lived experience.

---

## 4. Branch Definitions

### 4.1 Civic Branch

#### 4.1.1 Scope

The **Civic Branch** includes all ward-legitimized **service providers** to the general public:

- Housing & lodging: bunkhouses, dormitories, hostels.  
- Public kitchens, food halls, and soup lines.  
- Clinics and basic medical services.  
- Media outlets and posting boards for contracts, notices, propaganda.  
- Local bureaucracy and recordkeeping:
  - Residency, property, scavenging rights, licenses, permits.  
  - Case management for minor law violations and fines.
- Local justice and mediation (low-severity cases).  
- Commercial retail operators under ward license.  
- Waste reclamation logistics, in partnership with industrial guilds.

Civic leaders are **ostensibly loyal to the ward lord**, but in practice their loyalty is to **power and continued access to resources**. They gatekeep survival for the majority of the population.

#### 4.1.2 Civic Hierarchy (Titles)

Under the lord, the Civic Branch hierarchy is:

- **Tier 1: Chief Administrator**  
  - Primary civic liaison with the lord.  
  - Negotiates ward-wide budgets for housing, food, clinics, and bureaucracy.  
  - Sets civic policy priorities: which neighborhoods are fed, housed, or ignored.

- **Tier 2: Staff Chiefs** (by specialization)  
  - Staff Chief of **Residences** (bunkhouses, dorms, hostels).  
  - Staff Chief of **Kitchens & Food Halls**.  
  - Staff Chief of **Clinics & Care**.  
  - Staff Chief of **Justice & Administration** (courts, mediation).  
  - Staff Chief of **Licensing & Records** (permits, property, scavenging rights).  
  - Staff Chief of **Reclamation & Sanitation** (waste, recyclers).  
  - Staff Chief of **Communications & Notices** (posting boards, media).  
  - Staff Chief of **Retail & Distribution** (licensed markets).

- **Tier 3: Sub-Chiefs (Regional)**  
  - Each Sub-Chief oversees several related facilities in a local region or district.  
  - They compile reports on performance, failures, unrest, and shortages.  
  - They make **requisitions** upward for staff, food, medicine, equipment.

- **Tier 4: Facility Bosses**  
  - Boss of a bunkhouse, kitchen, clinic, office, or market cluster.  
  - Responsible for day-to-day operations, staffing, and basic security.  
  - Report to their relevant Sub-Chief or Staff Chief (if specialized and few).

- **Tier 5: Sub-Bosses & Stewards**  
  - Dorm wardens, line stewards, triage nurses, shift supervisors.  
  - Directly control who gets beds, food portions, clinic priority, or attention.  
  - Their informal decisions heavily impact local loyalty and unrest.

#### 4.1.3 Civic Functionaries (Cross-Cutting Roles)

Certain roles appear at multiple levels but are structurally important:

- **Clerks & Registrars**  
  - Maintain registries: residents, ration books, work permits, fine ledgers.  
  - Are primary targets for bribery, forgery, and data manipulation.  

- **Auditors & Inspectors (Civic)**  
  - Visit facilities to check for skimming, fake residents, or under-reported capacity.  
  - Report up to Staff Chiefs or directly to the Chief Administrator.  
  - Can trigger punitive actions or recommendations for de-legitimization.

- **Street-Level Stewards**  
  - Queue managers, intake desks, assignment officers.  
  - Control the immediate experience of public interactions with the state.  
  - Their petty tyrannies or quiet kindnesses shape ward reputation of the civic branch.

---

### 4.2 Industrial Branch

#### 4.2.1 Scope

The **Industrial Branch** includes ward-legitimized **production and technical** factions:

- Technician guilds and workshops.  
- Dominant worker unions serving core industries.  
- R&D ventures working on processes, suits, exo-suits, environmental controls.  
- Any legitimized group that converts **raw resources into finished products**, and that guards the **knowledge and methods** of those transformations.

Industrial leaders are responsible for:

- Sourcing **pay**, **means of production**, and **raw reagents**.  
- Providing **technical training** and protecting proprietary knowledge.  
- Maintaining industrial vehicles:
  - Trucks, lifts, drills, construction rigs, service crawlers.  
- Maintaining and upgrading facilities:
  - Workshops, warehouses, staging areas, fabrication plants.  
- Delivering on contracts with the ward lord:
  - Walls, utilities, roads, environmental control systems, suit maintenance plants.

They may optionally provide food and housing for skilled workers:

- Cafeterias, dormitories, or rest areas in lower wards.  
- Private apartments or secure compounds in upper wards.

#### 4.2.2 Industrial Hierarchy (Titles)

Under the lord, the Industrial Branch hierarchy is:

- **Tier 1: Chief of Works**  
  - Ward-wide head of industrial activity.  
  - Negotiates industrial contracts with the lord: quotas, timelines, budgets.  
  - Balances competing demands from military (armaments, vehicles) and civic (infrastructure, utilities).

- **Tier 2: Sector Chiefs / Industry Consuls**  
  - Sector Chief of **Atmosphere & Water Systems**.  
  - Sector Chief of **Suit & Exo-Suit Fabrication and Maintenance**.  
  - Sector Chief of **Heavy Construction & Structural Works**.  
  - Sector Chief of **Recycling & Rendering**.  
  - Sector Chief of **General Manufacturing & Tools**.  
  - Sector Chief of **Research & Development**.
  - Each Sector Chief represents the interests of their technicians, unions, and guilds in negotiations with the Chief of Works.

- **Tier 3: Guild Leaders & Regional Overseers**  
  - Lead specific guilds or large facilities within a sector.  
  - Control hiring, training, and assignment of technical specialists.  
  - Decide which workshops get scarce parts, tools, and apprentices.

- **Tier 4: Facility Bosses (Foremen / Shop Bosses)**  
  - Run single workshops, plants, yards, or repair bays.  
  - Enforce safety rules (or neglect them), manage shifts and quotas.  
  - Report production figures and maintenance needs upward.

- **Tier 5: Sub-Bosses / Lead Technicians**  
  - Lead small crews on specific lines or projects.  
  - Directly supervise work, sign off on repairs, and certify critical systems.  
  - Their quality or corner-cutting heavily influences failure rates and accidents.

#### 4.2.3 Guardians of Knowledge & Infrastructure

Industrial actors are also:

- **Guardians of Technical Knowledge**  
  - Apprenticeships, proprietary processes, calibration recipes, environmental tuning.  
  - Defection or capture of key workers is strategically important.

- **Owners of Infrastructure Contracts**  
  - Their contracts with the lord define who repairs walls, maintains wells, and services dehumidifier farms.  
  - They can use these contracts as leverage against other branches (e.g. refusing to fix militia barracks without concessions).

---

### 4.3 Military Branch

#### 4.3.1 Scope

The **Military Branch** includes all ward-legitimized **militant forces**:

- Local militias and security forces.  
- Guard units at checkpoints, armories, and critical infrastructure.  
- Any militant faction formally recognized by the lord.

Responsibilities include:

- Sourcing **pay**, **food**, **shelter**, **equipment**, and **training** for soldiers.  
- Maintaining military vehicles:
  - Tanks, trucks, APCs, patrol craft.  
- Maintaining military facilities:
  - Bunkers, barracks, weapon emplacements, depots, armories.
- Providing both:
  - **Internal security** – patrols, riot control, arresting lawbreakers.  
  - **External force projection** – ward-on-ward operations, raids, convoy protection.

Military leadership is **nominally loyal to the lord**, but in practice loyalty is to **power** (often the king, or whoever can guarantee long-term survival and victory).

#### 4.3.2 Military Hierarchy (Titles)

Under the lord, the Military Branch hierarchy is:

- **Tier 1: Marshal of the Ward**  
  - Overall commander of ward military forces.  
  - Negotiates troop levies, armament quotas, and security priorities with the lord.  
  - Represents the ward’s martial interests to external powers (Dukes, king, etc.).

- **Tier 2: Field Commanders & Logistics Chief**  
  - **Field Commanders** oversee major formations or geographic sectors.  
  - A **Chief of Logistics** (or equivalent) controls fuel, ammunition, spare parts, and supply convoys.
  - This tier converts political directives into deployments and supply plans.

- **Tier 3: Warband Leaders**  
  - Command warbands or battalion-equivalents.  
  - Decide which units get the best gear, missions, and opportunities for plunder or promotion.  
  - Can heavily influence morale and loyalty within their ranks.

- **Tier 4: Captains (Unit Commanders)**  
  - Lead companies, platoons, or fixed-post units (e.g., checkpoint garrisons).  
  - Responsible for maintaining discipline, training, and readiness.  
  - Interact frequently with civic authorities (for patrols) and industrial (for maintenance).

- **Tier 5: Sergeants & NCOs**  
  - Squad leaders and senior enlisted; run daily drills, watches, and patrols.  
  - Directly manage soldiers, enforcement of orders, and on-the-ground use of force.  
  - Their choices in crisis often matter more than formal orders.

#### 4.3.3 Internal vs External Roles

- **Internal Roles**  
  - Policing, riot control, curfew enforcement, escorting officials.  
  - Guarding key infrastructure (wells, dehumidifier farms, workshops, civic offices).

- **External Roles**  
  - Offensive campaigns, punitive raids, convoy escorts.  
  - Inter-ward conflicts and enforcing higher-level decrees (from Dukes, king).

---

## 5. Legitimacy State Machine

Each faction or facility may have a **legitimacy state** relative to the ward lord:

- `outlawed` – Actively hunted, no formal protections.  
- `tolerated` – Functionally allowed to operate; legal cover is weak or informal.  
- `recognized` – On the branch tree, basic contracts and obligations.  
- `favored` – Preferred contractor or ally; receives extra resources or legal shields.  
- `indispensable` – So essential that purging them would cripple the ward.

### 5.1 Upward Transitions

Conditions that can move a faction up:

- Consistently meeting or exceeding quotas.  
- Demonstrated loyalty during crises or purges.  
- Control of unique or difficult-to-replace skills, infrastructure, or information.  
- Strong patronage from higher powers (Dukes, king).

### 5.2 Downward Transitions

Conditions that can move a faction down:

- Persistent underperformance, sabotage, or betrayal.  
- Corruption scandals that threaten the legitimacy of the lord.  
- The rise of a more useful rival faction.  
- Shifts in external politics (king’s displeasure, rival ward pressure).

### 5.3 De-Legitimization as Weapon

When high-level corruption or disloyalty is discovered:

- The lord may strip a faction of recognition in **targeted ways**:
  - Remove a specific facility from contracts.  
  - Revoke the status of a branch head while elevating a rival.

This can create **new shadow coalitions** (exiled leaders + loyalists) and motivate neutral groups to seek new deals.

---

## 6. Information Flow & Distortion

### 6.1 Observation Radius vs Granularity

- **Low tiers (Tier 4–5)**:
  - Observe exact conditions in narrow domains (queues, workshops, squads).  
  - Their data is granular but hyper-local.

- **Mid tiers (Tier 2–3)**:
  - Aggregate over multiple facilities/units.  
  - Often rely on summaries, rollups, and simple metrics.

- **Top tiers (Tier 0–1)**:
  - See broad indicators:
    - Ward stability, production fulfillment, food distribution stats, reported crime.  
  - Received information is delayed, smoothed, and vulnerable to manipulation.

### 6.2 Signal Distortion

At each hop upward:

- **Delay** – Data may arrive late or batched, masking short crises.  
- **Smoothing** – Bad weeks averaged with good weeks to avoid panic or punishment.  
- **Bias** – Subordinates under-report failures and over-report loyalty and success.

Mid-tier actors can:

- Hide their own corruption.  
- Exaggerate a rival’s failures.  
- Understate the importance of neutral factions they are quietly allied with.

---

## 7. Shadow Coalitions (Out-of-Tree Actors)

Outside the three official branches is a **“shadow forest”** of non-legitimized powers:

- Black-market guilds and brokers.  
- Militant gangs and unofficial enforcers.  
- External patron networks (agents of Dukes, king, off-ward traders).  

Key properties:

- Almost every legitimized facility has **some tie** to the shadow layer:
  - A bunkhouse Boss takes bribes from smugglers.  
  - A Guild Leader sells scrap to suit modders.  
  - A Captain cooperates with a gang to keep rivals weak.

- These ties:
  - Provide **fallback options** when factions are de-legitimized.  
  - Serve as channels for information, contraband, and covert influence.  
  - Give the lord leverage: by promoting or suppressing certain shadow actors, they can threaten branch heads or reward loyalists.

Future documents (`info_security`, `law`, and dedicated black market docs) can define:

- Spy networks, informant chains, and reporting systems.  
- How anecdotal intelligence reaches lords and branch heads.  
- The mechanics of misinformation, double agents, and compromised informants.

---

## 8. Implementation Notes (Simulation)

For Codex and runtime systems, this document implies:

1. **Role Assignment**  
   - Agents can be tagged with:
     - `branch` ∈ {civic, industrial, military, none}  
     - `tier` ∈ {0..5}  
     - `legitimacy` ∈ {outlawed, tolerated, recognized, favored, indispensable}

2. **Negotiation Graph**  
   - Edges between tiers define who can negotiate or report to whom.  
   - Cross-branch edges (e.g., Chief of Works ↔ Marshal ↔ Chief Administrator ↔ Lord) define high-level bargaining.

3. **Information Model**  
   - “True state” exists at local nodes (Tier 4–5).  
   - “Perceived state” for higher tiers is a function of:
     - Aggregation + noise + deliberate distortion along the path.

4. **Punishment & Realignment Logic**  
   - Events can trigger:
     - Replacement of individual agents.  
     - De-legitimization of specific facilities.  
     - Downward legitimacy shifts or removal of branch heads.  
     - Creation of new shadow coalitions and alliance opportunities.

5. **Hooks for Future Docs**  
   - Information & reporting systems (spies, informants, auditors) will plug into this hierarchy, providing **non-structural** intelligence that sometimes confirms and sometimes contradicts official reports.
