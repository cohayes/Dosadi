---
title: Ward_Resource_and_Water_Economy
doc_id: D-ECON-0001
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
depends_on:
  - D-WORLD-0001   # Planetary_Environment (placeholder)
  - D-WORLD-0002   # Ward_Structure_and_Territories (placeholder)
  - D-WORLD-0003   # Ward_Branch_Hierarchies
  - D-WORLD-0004   # Civic_Facility_Microdynamics_Soup_Kitchens_and_Bunkhouses
  - D-INFO-0001    # Telemetry_and_Audit_Infrastructure
  - D-INFO-0004    # Scholars_and_Clerks_Branch
  - D-HEALTH-0002  # Food_Waste_and_Metabolism
  - D-AGENT-0001   # Human_Agent_Biology_and_Drives (placeholder)
---

# Ward Resource & Water Economy

> This document defines how **water and closely coupled resources** move from the
> single planetary source down to wards, branches, facilities, and agents.
> It provides the constraints and knobs that drive scarcity in everyday play,
> with a focus on:
> - Ward-level **water budgets**
> - Internal **allocation between branches**
> - **Moisture capture and recycling**
> - Hooks for **telemetry, audits, and black markets**

---

## 1. Purpose & Scope

Water is the **master resource** of Dosadi:

- All other resources (food, energy, labor) are bottlenecked by water.
- Control of water allocations is the **primary lever of political power**.
- At the simulation level, water supply and distribution:
  - Drive queue pressure at kitchens and bunkhouses.
  - Shape industrial capacity, military readiness, and household survival.

This document focuses on the **ward scale**:

- How a ward’s water budget is defined and updated.
- How that budget is divided between branches and facilities.
- How moisture capture, recycling, and leakage modify the budget over time.
- How shortages propagate into visible tension in civic facilities (e.g. soup kitchens).

Higher-level macro politics (king vs dukes) and fine-grained pricing inside
each micro-market are referenced but not fully specified here.

---

## 2. Levels of the Water System

We treat the water system as layered:

1. **Planetary Source Layer**
   - One central well / engineered source with finite daily yield.
   - Output constrained by:
     - Geological/engineering limits.
     - Maintenance, sabotage, or deliberate throttling.

2. **Macro Allocation Layer (Crown → Wards)**
   - The king (and associated central bureaucracy) sets:
     - **Ward quotas** for a given planning horizon (days/weeks).
   - Quotas may be:
     - Stable (normal periods).
     - Punitive or preferential (reward/punish specific wards).
     - Adjusted after major incidents (disaster, rebellion, sabotage).

3. **Ward Allocation Layer (Ward → Branches)**
   - Ward lord divides the incoming water budget between:
     - Civic, Industrial, Military, and elite/private uses.
   - Small portion may be earmarked for:
     - Official “buffer reserves” (tanks, cisterns).
     - Emergency use or special projects.

4. **Facility & Agent Layer**
   - Branch heads allocate water to facilities (kitchens, bunkhouses, workshops, barracks).
   - Facilities convert water to:
     - Food preparation, cleaning, cooling, industrial processes, and direct drinking.
   - Agents experience this as:
     - Ration availability, queue length, thirst, and health impacts.

---

## 3. Planetary & Macro Allocation Model

### 3.1 Planetary Yield

At the planetary level we define:

- `W_total_per_cycle`:
  - Max usable water output for the entire system per simulation cycle (or day).
- Optional variability:
  - `yield_noise` (environmental fluctuations).
  - `maintenance_downtime` (reduced output during repairs or sabotage).

For simulation purposes, `W_total_per_cycle` may be:

- Static for early prototypes.
- Later extended with:
  - Long-term degradation or upgrades.
  - Rare catastrophic failures.

### 3.2 Ward Quotas

The regime maintains a vector of **ward quotas**:

- For each ward `i`:
  - `W_quota[i]` = share of `W_total_per_cycle` assigned to that ward.

Allocation rules may be:

- **Political**:
  - Loyal wards get generous allocations.
  - Disfavored or rebellious wards get squeezed.
- **Functional**:
  - Industrially important wards get minimum guaranteed water to keep production online.
- **Demographic**:
  - Wards with larger populations need higher baseline allocations.

Quotas can be:

- Adjusted slowly (normal policy changes).
- Adjusted abruptly (sanctions, rewards, crisis response).

---

## 4. Ward-Level Water Budget

For each ward and time step:

```text
W_inflow      = W_quota[i]  + W_imports  + W_reclaimed_external
W_internal    = W_storage_prev + W_inflow
W_outflows    = W_civic + W_industrial + W_military + W_elite
                + W_losses + W_exports + W_blackmarket
W_storage_new = max(0, W_internal - W_outflows)
```

Where:

- `W_storage_prev`, `W_storage_new`:
  - Water in ward tanks/cisterns at start/end of cycle.
- `W_losses`:
  - Leakage, evaporation, theft that never reaches meters.
- `W_blackmarket`:
  - Water siphoned into off-ledger channels for illicit trade.

If `W_internal < desired allocation`:

- Branches receive **less than planned**, propagating scarcity downward.

---

## 5. Internal Branch Allocations

Within each ward, the lord (or designated economic council) divides available water into branch budgets.

### 5.1 Priority Order

A default **priority hierarchy** (tunable per ward):

1. **Survival Baseline**
   - Minimal water to prevent mass die-off:
     - Basic rations, limited bunkhouse hygiene.
   - Allocated via Civic branch.

2. **Industrial Sustainment**
   - Enough to keep critical industrial processes online:
     - Maintenance of infrastructure, spare parts, recycling plants.
   - Provided via Industrial branch.

3. **Military Readiness**
   - Drinking, cleaning, and limited equipment cooling for militias.
   - Priority rises in wartime or after unrest.

4. **Elite & Discretionary Uses**
   - Private baths, ornamental water features (rare), luxury foods.
   - Heavily politicized and resented if visible during scarcity.

### 5.2 Branch Budgets

Each cycle, the ward defines:

- `W_civic_budget`
- `W_industrial_budget`
- `W_military_budget`
- `W_elite_budget`

Subject to:

```text
W_civic_budget + W_industrial_budget + W_military_budget + W_elite_budget
    <= W_internal - W_reserve_target
```

Where:

- `W_reserve_target`:
  - Target buffer for emergencies (often ignored or raided in crisis).

### 5.3 Negotiation & Corruption

Branch heads lobby for larger budgets using:

- Political leverage (past favors, blackmail, loyalty).
- Economic arguments (“cut us and your quotas crater next cycle”).

Corruption hooks:

- Branch heads can:
  - Secretly divert part of their budget to:
    - Black market, patronage networks, or private tanks.
- Ward lord can:
  - Turn a blind eye in exchange for loyalty or kickbacks.

---

## 6. Facility-Level Water Use

Within branches, water is further partitioned to facilities.

### 6.1 Civic Facilities (Kitchens & Bunkhouses)

From `D-WORLD-0004`:

- **Kitchens**:
  - Use water for:
    - Cooking, cleaning, limited drinking.
  - Water usage structure:
    - `W_kitchen = W_food_preparation + W_cleaning + W_staff_use`
- **Bunkhouses**:
  - Use water for:
    - Basic hygiene, cleaning, minimal drinking.
  - Produce:
    - **Moisture reclaimed** via dehumidifiers.

Each facility has:

- `W_facility_quota` (assigned by Civic branch for the cycle).
- `W_facility_min` (survival minimum for safe operation).
- `W_facility_max` (comfortable operation level).

### 6.2 Industrial Facilities

Industrial facilities use water for:

- Cooling, cleaning, processing, reclamation.

They may:

- Produce **reclaimed water** as a by-product:
  - `W_reclaimed_industrial` routed back to ward storage or specific branches.

### 6.3 Military Facilities

Use:

- Drinking, cleaning, some equipment maintenance.

In crisis:

- Military may **override** normal rules and seize water:
  - Directly from civic or industrial storage.
  - Creating strong resentment and unrest.

---

## 7. Moisture Capture & Recycling

In Dosadi’s hyper-dry environment, **human respiration** and interior humidity are valuable.

### 7.1 Bunkhouse Respiration Harvest

Each bunkhouse:

- Hosts `N_sleepers` during night cycle.
- Has a `capture_efficiency` parameter for dehumidifiers and vents.

Per night, approximate:

```text
W_reclaimed_bunkhouse = N_sleepers * moisture_per_agent * capture_efficiency
```

Where:

- `moisture_per_agent`:
  - Derived from `D-AGENT-0001` (typical nightly water vapor exhalation).
- `capture_efficiency`:
  - Depends on:
    - Technology level, maintenance quality, and corruption.

This reclaimed water:

- Flows back into:
  - Ward storage (`W_reclaimed_external`) or
  - Specific branch budgets (if the bunkhouse is directly exploited by a branch).

### 7.2 Industrial Condensers

Industrial processes may:

- Condense moisture from air or exhaust streams.

Per facility:

- `W_reclaimed_industrial = f(process_type, throughput, capture_efficiency)`

These often serve as:

- Key telemetry points (per `D-INFO-0001`).
- Major targets for sabotage, theft, or secret taps.

### 7.3 Recycling Limits

Recycling is:

- Highly valuable but *not* fully lossless:
  - Each pass has:
    - Efficiency < 1, some irrecoverable loss.

This ensures:

- The system still depends on `W_total_per_cycle`.
- Hoarding/hyper-recycling can mitigate but not fully escape scarcity.

---

## 8. Non-Water Resources (Brief Coupling)

Though water is the master constraint, other key resources interact:

- **Food**:
  - Requires water to grow (if any local agriculture exists) or process.
  - Water shortages → lower food throughput → higher hunger and unrest.

- **Energy / Fuel**:
  - Needed to pump, purify, and transport water.
  - Energy shock → effective water distribution shock.

- **Scrap & Industrial Feedstock**:
  - Reclamation processes may need water.
  - Industrial water cuts → slower repair and infrastructure decay.

These resources should eventually be given their own economic docs; for now they
are assumed to be **downstream** of water adequacy.

---

## 9. Scarcity, Shocks & Signals

### 9.1 Types of Shocks

1. **Macro Shock**
   - Well output reduced (maintenance, sabotage, geological limit).
   - King deliberately cuts quotas for rebellious wards.

2. **Ward-Level Shock**
   - Major pipe break, storage contamination, or pump failure.
   - Loss or sabotage of key industrial condenser.

3. **Branch-Level Shock**
   - One branch’s allocation slashed:
     - As punishment, policy shift, or mismanagement.

### 9.2 Behavioral & System Responses

Faced with water stress:

- **Civic Branch**:
  - Shrinks ration size, cuts service hours, tightens queue rules.
- **Industrial Branch**:
  - Shuts down non-critical lines, prioritizes essential repair production.
- **Military Branch**:
  - Maintains its quota as long as possible, may seize additional water.
- **Agents**:
  - Spend more time queueing/searching; increase theft, black-market activity, and violence.

These responses feed into:

- Telemetry (reduced flows, changed patterns).
- Reports (excuses vs actual failures).
- Credibility system and audits.

---

## 10. Inter-Ward Trade & Black Markets

### 10.1 Official Inter-Ward Transfers

Occasionally:

- The crown or high nobles authorize:
  - **Emergency transfers**:
    - Water canisters routed from one ward’s tanks to another.
  - Recorded in:
    - High-level manifests, heavily monitored.

These are rare and politically charged.

### 10.2 Smuggling & Off-Ledger Trade

Because water is portable (in canisters):

- Smugglers and black-market networks:
  - Steal water from:
    - Branch storage, industrial condensers, or distribution lines.
  - Move it through:
    - **Logistics corridors and safehouses** (per D-SOC-0003).

Price dynamics:

- Black market water price spikes:
  - During local shortages or visible favoritism.
- Some lords quietly tolerate or even tax black-market routes:
  - To offload unrest.

Simulation-wise:

- `W_blackmarket` term in the ward budget is:
  - Driven by:
    - Scarcity, enforcement intensity, and network strength.

---

## 11. Simulation Hooks

### 11.1 Ward-Level State

For each ward:

- `W_quota`               # upstream allocation from crown
- `W_storage`             # current stored water
- `W_reserve_target`
- `W_civic_budget`
- `W_industrial_budget`
- `W_military_budget`
- `W_elite_budget`
- `W_losses`              # leaks, theft, evaporation
- `W_blackmarket`         # diverted to black-market networks
- `recycle_efficiency_bunk`
- `recycle_efficiency_industrial`
- `telemetry_coverage_water`   # from D-INFO-0001
- `telemetry_quality_water`

These influence:

- Facility-level rationing.
- Tension levels in civic hubs.
- Credibility of reason codes like “equipment malfunction” or “unexpected losses.”

### 11.2 Facility-Level Parameters

Each facility (kitchen, bunkhouse, plant):

- `W_quota_facility`
- `W_min_facility`
- `W_max_facility`
- `W_actual_use`
- `recycle_efficiency` (if applicable)
- `telemetry_meters` (links to Meter entities)

Shortfalls (`W_quota_facility < W_min_facility`) feed into:

- **Event triggers**:
  - Food Shortfall, Queue Brawl, “Closed for Maintenance,” etc.

### 11.3 Agent-Level Interactions

Agents’ biological and behavioral systems (per D-AGENT-0001) use:

- `hydration_level` (0–1)
- `thirst_drive`
- `queue_tolerance` modulated by hydration and hunger.

Logic examples:

- High `thirst_drive` →
  - Higher priority to seek water-serving facilities.
  - Increased willingness to fight, bribe, or steal.

- Persistent low hydration →
  - Health penalties, lowered work capacity, increased mortality risk.

### 11.4 Telemetry & Audits Integration

From `D-INFO-0001`:

- Flow meters on:
  - Well → ward, ward storage, major branch off-takes, condensers, bunkhouses.
- Audit events:
  - Compare:
    - Measured flows vs reported allocations and facility usage.

Discrepancies can:

- Lower credibility of branches/facilities.
- Trigger:
  - Investigations, leadership changes, or reallocation of water budgets.

---

## 12. Open Design Questions

For later ADRs or refinements:

- Should some wards be **structurally water-poor** (permanent low quota) vs others that are “normal” but currently punished?
- How granular should **branch-level bargaining** be in the sim?
  - Simple fixed priority rules vs explicit negotiation events.
- To what extent can players/agents **alter the water system**?
  - Sabotaging condensers, tapping lines, lobbying for quota shifts?
- Should we introduce **long-term well degradation or upgrade paths**?
  - Turning water into a slowly worsening global crisis or a hard-but-stable constraint.

These questions can be resolved as early prototypes reveal which levers generate the most interesting and legible pressure.
