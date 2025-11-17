---
title: Civic_Microdynamics_Soup_Kitchens_and_Bunkhouses
doc_id: D-CIV-0001
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
---

# Civic Microdynamics: Soup Kitchens & Bunkhouses

> This document defines **how civic survival halls actually run** at the micro level:
> - The internal state and loops of soup kitchens and bunkhouses.
> - How queues, chits, and rations are managed.
> - How telemetry, ledgers, and rumors intersect inside these facilities.
> - Where the most interesting pressure points, corruptions, and stories occur.

These facilities are **where most agents feel the regime in their bones**:
- You stand in line.
- You are measured, sorted, fed (or not), housed (or not).
- You witness small injustices, favors, and quiet deals.

---

## 1. Facility Archetypes

We define three archetypes, all using similar machinery:

1. **Soup Kitchen** (KITCHEN)
2. **Bunkhouse** (BUNK)
3. **Combined Survival Hall** (HALL: both functions)

In the simulation we can implement all three via one parametric structure.

### 1.1 Soup Kitchen (KITCHEN)

Core functions:

- Convert:
  - Water + food stocks → meals (LOW/MID/HIGH tier).
- Allocate meals to:
  - Ration chit holders, paying customers, and sometimes “charity” cases.
- Generate:
  - Operational logs, ledger entries, and a thick cloud of rumor.

Key traits:

- Strong **queue dynamics**.
- Face-to-face contact zone for:
  - Espionage, recruitment, petty extortion, and gossip.

### 1.2 Bunkhouse (BUNK)

Core functions:

- Convert:
  - Floor space + bedding + minimal facilities → bunk-nights (tiers).
- Allocate bunks to:
  - Chit holders, paying lodgers, and favored regulars.
- Regulate:
  - Curfews, wake times, access to storage lockers.

Key traits:

- High **overnight vulnerability** of patrons.
- Natural venue for:
  - Theft, protection rackets, covert meetings, and quiet interrogation.

### 1.3 Combined Survival Hall (HALL)

A facility that:

- Provides both:
  - Meals and bunks.
- Shares:
  - Staff, security, some stock and bookkeeping.
- Acts as:
  - A persistent social node for a specific population segment.

In code terms:

- A HALL is:
  - `KITCHEN + BUNK` with shared state and a common boss/sub-boss structure.

---

## 2. Roles Within the Facility

We map facility roles to the broader ward hierarchies (D-WORLD-0003).

### 2.1 Civic Chain

- **Boss (Facility Boss)**
  - Reports to:
    - Sub-Chief or Staff Chief of Civic branch.
  - Responsibilities:
    - Keep quotas and budgets within limits.
    - Maintain staff discipline.
    - Interface with inspectors, auditors, and local spies.
- **Sub-Bosses**
  - Oversee shifts, queues, floor operations.
  - Act as local arbiters in disputes.
- **Line Staff**
  - Cooks, servers, cleaners, bunk wardens.
- **Clerks**
  - Handle:
    - Chit validation, ledgers, operational logs, posted information.

### 2.2 Security & Oversight

- **House Guards / Militia Liaisons**
  - Maintain order in queues and dorms.
  - Enforce bans and curfews.
- **Investigators / Inspectors**
  - Drop-in presence:
    - Check rations, occupancy, treatment of patrons.
  - May:
    - Cross-check telemetry vs ledgers vs logs.

### 2.3 External Actors

- **Informants / Spies**
  - Blend in as:
    - Patrons, staff, or nearby stall operators.
  - Collect:
    - Headcounts, faction presence, illicit trades.
- **Black-Market Fixers**
  - Sell:
    - Extra rations, bunk upgrades, queue skips.
  - Operate:
    - Just outside official boundaries or via compromised staff.

---

## 3. State Variables (Facility Level)

Each facility maintains a minimal set of state variables.

### 3.1 Resource & Capacity State

- `water_quota_tick`:
  - Allocated water for this tick/block.
- `stocks`:
  - `stocks.rations_LOW/MID/HIGH`
  - `stocks.ingredients`, `stocks.fuel`
  - `stocks.bunks_FREE/BUSY` per tier.
- `throughput_targets`:
  - Planned meals/bunks for current cycle.
- `maintenance_state`:
  - Wear level of critical infrastructure.

### 3.2 Queue & Access State

- `queue_main`:
  - Standard patrons.
- `queue_priority`:
  - Favored groups (workers on shift, militia, guild members).
- `queue_backdoor`:
  - Illicit or “special consideration” entries (if enabled).
- `lockout_lists`:
  - Patrons banned or temporarily suspended.

### 3.3 Governance & Risk State

- `GovLegit_facility`:
  - Perceived legitimacy score of the facility.
- `corruption_level`:
  - Effective propensity for:
    - Bribes, skims, queue manipulation.
- `inspection_pressure`:
  - How often audits/inspections occur.
- `threat_level`:
  - Risk of riot, attack, or targeted sabotage.

---

## 4. State Variables (Patron Level, In-Facility)

When a patron interacts with a facility, we care about:

- `identity`:
  - Known or anonymous; affiliations (guild, branch, faction).
- `wallet`:
  - `KCR`, `WCR`, relevant chits (`kitchen_W21_01:LOW`, `bunk_W21_03:STD`).
- `need_state`:
  - Hunger level, fatigue, health, stress.
- `priority_flags`:
  - Civic priority (critical worker), militia, noble retainer, etc.
- `reputation_local`:
  - Relationship with:
    - Facility staff, local gangs, civic branch.
- `suspicion_markers`:
  - For spies, suspects, or banned patrons.

These feed into:

- Queue position.
- Outcome of disputes.
- Probability of being selected for:
  - Recruitment, extortion, interrogation, or help.

---

## 5. Session Loop: Soup Kitchen

We describe a **meal block** loop; the sim can run several per cycle.

### 5.1 Pre-Opening

1. **Stock Check**
   - Compare:
     - `stocks.rations_*` vs expected demand from prior blocks.
   - Emit:
     - OP_LOG and potentially TELEMETRY on storage levels.

2. **Quota Confirmation**
   - Confirm:
     - Water and fuel available for cooking.
   - Possibly:
     - Request top-up from Civic branch (may be denied or delayed).

3. **Staff Briefing**
   - Boss/sub-boss assign:
     - Queue management, serving lines, door guards, clerks.

### 5.2 Intake & Queuing

1. Patrons arrive and are **sorted** into:
   - `queue_priority`
   - `queue_main`
   - `queue_backdoor` (if corruption active).

2. Sorting depends on:
   - Visible status (uniforms, badges, documents).
   - Chits/tickets presented.
   - Relationships & bribes.

3. Optional:
   - Quick **security scan** for banned individuals or known troublemakers.

### 5.3 Service Phase

For each patron in queue order:

1. **Eligibility Check**
   - Chit validation or payment check:
     - Civic chits, guild-issued chits, WCR, or “house favors”.
   - If short:
     - Patron may:
       - Negotiate, plead, bribe, or be turned away.

2. **Allocation Decision**
   - Decide which tier of meal:
     - Based on chit tier, price paid, or favoritism.
   - Update:
     - `stocks`, OP_LOG, LEDGER:
       - Ration decrement, water usage, payment received.

3. **Telemetry Hooks**
   - Optionally count:
     - Patrons served via turnstiles or bowl counters.
   - Emit TELEMETRY for:
     - `MEALS_SERVED` vs `RATIONS_DECREMENTED`.

4. **Micro-Events**
   - Queue cutting, arguments, staff looking the other way.
   - Rumor exchanges and observation of who eats what.

### 5.4 Closing & Logging

1. **Close Door**
   - Remaining patrons turned away, may react (anger, despair, dealing).
2. **Reconciliation**
   - Compare:
     - OP_LOG vs LEDGER vs TELEMETRY for the block.
   - If discrepancies:
     - Generate VarianceAlert (D-INFO-0001).
3. **Reporting**
   - Facility boss/sub-boss send summary:
     - To Civic Sub-Chief or Staff Chief.
   - Possibly fudge:
     - Numbers to hide skims or failures.

---

## 6. Session Loop: Bunkhouse

We describe a **sleep block** loop (e.g., one night).

### 6.1 Pre-Check-In

1. **Bunk Availability Update**
   - Count bunks:
     - `FREE` vs `RESERVED` vs `OUT_OF_SERVICE`.
2. **Security Briefing**
   - Guards review:
     - Current tensions, expected raids, special orders.
3. **Sanitation/Inspection**
   - Quick pass:
     - Remove corpses, check for contraband, repair critical damage.

### 6.2 Check-In Window

1. Patrons arrive; facility staff:

   - Validate:
     - Bunk chits, WCR payments, special orders from branch or lord.
   - Assign:
     - Tier and specific bunk.

2. **Queue & Priority Handling**

   - Priority bunk:
     - For critical workers, militia, “friends of the house”.
   - Overflow:
     - Patrons may be:
       - Redirected, told to sleep on floor (informally), or turned away.

3. **Ledger & Log Entries**

   - For each check-in:
     - LEDGER update:
       - Payment or chit redemption.
     - OP_LOG:
       - Occupancy by tier.

### 6.3 Night Cycle

Within the sleep block:

- Events tick:

  - **Theft / Conflict**
    - Patrons rob each other, fight, or extort.
  - **Recruitment**
    - Gangs, militias, cults, and factions target:
      - Vulnerable or ambitious individuals.
  - **Espionage**
    - Information traded under cover of darkness.
  - **Quiet Interrogations**
    - Sometimes a bunkhouse doubles as:
      - A convenient holding site for questioning.

Outcomes can:

- Update:
  - Reputations, injuries, arrests, new rumors.

### 6.4 Morning Check-Out

1. Patrons leave:

   - Staff note:
     - Missing persons, injuries, suspicious behavior.

2. **Reconciliation**

   - OP_LOG:
     - Occupancy vs bunks expected.
   - LEDGER:
     - Income vs expected for occupancy.
   - TELEMETRY (if present):
     - Water usage, power consumption, headcounts.

3. **Reports Upward**

   - Bunkhouse boss may:
     - Flag troublemakers, suspected gangs, or suspicious quiet nights.

---

## 7. Micro-Events & Hooks

We define recurring micro-events that tie into broader systems.

### 7.1 Resource Micro-Events

- **Substitution**
  - Staff downgrade meal tier (serve LOW instead of MID):
    - Skimming higher tier rations for resale.
- **Quota Shortfall**
  - Facility runs out before serving nominal quota.
  - Generates:
    - Crowding, despair, anger, potential riot.

### 7.2 Social Micro-Events

- **Favoritism**
  - Staff bump certain patrons in queue or upgrade meals/bunks.
- **Discipline**
  - Guards eject troublemakers, inflict beatings, or hand them to militia.
- **Whispered Deals**
  - “Pay me tomorrow, I’ll mark you as served today.”
  - “Give me information, you get priority bunk.”

### 7.3 Information Micro-Events

- **Rumor Propagation**
  - Kitchens and bunkhouses are fertile ground for:
    - Ward rumors, political gossip, prices, raids.
- **Informant Activation**
  - Informants decide:
    - Which snippets to pass up to handlers.
- **Record Tampering**
  - Clerk alters:
    - Counts, ledger entries, or bans list.

---

## 8. Telemetry, Logs & Records In-Facility

Tie to D-INFO-0005 (Record Types & Information Surfaces).

### 8.1 Intra-Facility Record Types

- TELEMETRY:
  - Headcounts, tank levels, energy usage.
- OP_LOG:
  - Meals served by tier, occupancy, incidents.
- LEDGER:
  - Chit redemptions, payments, supply movements.
- FORMAL_REPORT:
  - Periodic performance reports to branch/ward.
- LEGAL:
  - Incident write-ups, charges stemming from fights or riots.
- SHADOW:
  - Boss’s personal books, black ledgers, rumor notes.

### 8.2 Local Information Surfaces

Surfaces within/around the facility:

- **Front Desk / Hatch**
  - Interaction with queue; public posting of rules, prices, bans.
- **Back-Office / Clerk Desk**
  - Core record creation and tampering zone.
- **Kitchen/Bunk Floor**
  - Primary social space and rumor exchange.
- **Guard Post**
  - Local view on:
    - Security incidents and “unofficial” orders.

---

## 9. Simulation Hooks & Minimal Prototype

To get a first micro-sim running, we can:

### 9.1 Minimal Facility Schema

```json
{
  "facility_id": "W21_KITCHEN_01",
  "type": "KITCHEN",
  "ward": "W21",
  "capacity": {
    "meals_per_block": 500
  },
  "stocks": {
    "rations_LOW": 800,
    "rations_MID": 150,
    "rations_HIGH": 40,
    "water_L": 1200
  },
  "governance": {
    "GovLegit_facility": 0.7,
    "corruption_level": 0.4,
    "inspection_pressure": 0.3,
    "threat_level": 0.2
  }
}
```

### 9.2 Minimal Loop

Per meal/sleep block:

1. Generate **arrival set** of patrons.
2. Sort into queues using:
   - Need, status, reputation, and bribery.
3. Step through service or check-in:
   - Update stocks, wallets, logs, ledgers.
4. Trigger micro-events stochastically.
5. Emit:
   - TELEMETRY, OP_LOG, LEDGER rows, and possible FORMAL_REPORT stubs.
6. Update:
   - Facility legitimacy and patron relationship scores.

### 9.3 Tuning Axes

Interesting parameters for balancing:

- `corruption_level`:
  - More corruption → more backdoor queue, more skimming, higher rumor volume.
- `inspection_pressure`:
  - High → fewer blatant abuses but more clever falsification.
- `GovLegit_facility`:
  - High → patrons trust posted rules more; lower riot probability.
- `stocks` vs demand:
  - Scarcity increases:
    - Conflict, bribes, and rumor intensity.

---

## 10. Open Questions

For later refinement (or separate docs):

- Should we model **distinct kitchen cultures** per ward?
  - Strict ration halls vs chaotic feeding pits.
- How deeply to model:
  - **Dormitory social networks** (regular bunk neighbors, cliques)?
- Should some facilities be:
  - **Private guild halls** with different norms and records?
- Where do we draw the line between:
  - **Simulation detail** and **playable comprehension** for a human player?

For now, this microdynamics layer aims to provide:

- Enough structure to:
  - Hook into ECON and INFO.
  - Support agent-level RL or heuristic policies.
- Enough flavor that:
  - “A night at the hall” can be a meaningful story unit in the Dosadi world.
