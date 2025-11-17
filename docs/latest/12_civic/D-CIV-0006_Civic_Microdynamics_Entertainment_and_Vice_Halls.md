---
title: Civic_Microdynamics_Entertainment_and_Vice_Halls
doc_id: D-CIV-0006
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
depends_on:
  - D-WORLD-0003  # Ward_Branch_Hierarchies
  - D-ECON-0001   # Ward_Resource_and_Water_Economy
  - D-ECON-0002   # Dosadi_Market_Microstructure
  - D-ECON-0003   # Credits_and_FX
  - D-ECON-0005   # Food_and_Rations_Flow
  - D-ECON-0009   # Financial_Ledgers_and_Taxation
  - D-INFO-0001   # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002   # Espionage_Branch
  - D-INFO-0003   # Information_Flows_and_Report_Credibility
  - D-INFO-0005   # Record_Types_and_Information_Surfaces
  - D-INFO-0004   # Scholars_and_Clerks_Branch
  - D-CIV-0000    # Civic_Microdynamics_Index
  - D-CIV-0001    # Civic_Microdynamics_Soup_Kitchens_and_Bunkhouses
  - D-CIV-0002    # Civic_Microdynamics_Clinics_and_Triage_Halls
  - D-CIV-0003    # Civic_Microdynamics_Posting_Boards_and_Permit_Offices
  - D-CIV-0004    # Civic_Microdynamics_Courts_and_Justice_Halls
  - D-CIV-0005    # Civic_Microdynamics_Body_Disposal_and_Reclamation
---

# Civic Microdynamics: Entertainment & Vice Halls

> This document defines **how entertainment and vice venues operate** at the ward scale:
> - The types of halls where agents drink, gamble, seek company, escape, and scheme.
> - How these venues process stress, wages, rumors, and violence.
> - How they interface with permits, clinics, courts, espionage, and body reclamation.
> - Where agent drives (relief, status, belonging, novelty, control) are expressed and exploited.

On Dosadi, entertainment halls are:

- **Pressure valves** for bunkhouses, workshops, militias, and courts.
- **Mixing chambers** where factions overlap under dim lights and loud noise.
- **Information bazaars** where rumors, secrets, and debts change hands.
- **Addiction engines** that turn wages into leverage and habits.

---

## 1. Facility Archetypes

We define six archetypes under a common “vice/entertainment” umbrella:

1. **Drinking Halls / Taverns** (VICE_DRINK)
2. **Gambling Dens** (VICE_GAMBLE)
3. **Companionship Houses** (VICE_COMPANION)
4. **Stimulation Parlors** (VICE_STIM)
5. **Performance Houses / Theatres** (VICE_STAGE)
6. **Mixed Vice Arcades** (VICE_MIXED)

All of them share:

- A **public front** (music, drink, games, performance).
- A **backstage logic** (tabs, debts, favors, quiet deals).
- A set of **hooks** into ECON, INFO, MIL, and ESPIONAGE.

### 1.1 Drinking Halls / Taverns (VICE_DRINK)

- Core offer:
  - Fermented/synthesized intoxicants; sometimes mild stimulants or relaxants mixed in.
- Clientele:
  - Workers after shift, bunkhouse residents, off-duty militia, small-time fixers.
- Atmosphere:
  - Loud, crowded, half-lit; fights are common but usually contained.
- Functions:
  - Stress relief, social bonding, rumor spread, small-scale recruitment.

### 1.2 Gambling Dens (VICE_GAMBLE)

- Core offer:
  - Games of chance and skill, with stakes in WCR/KCR, ration chits, or gear.
- Clientele:
  - Risk-tolerant workers, petty criminals, ambitious strivers, house agents.
- Features:
  - Dealers, pit bosses, house-backed credit, and in-house enforcers.
- Functions:
  - Economic sink, debt creation, money laundering, information gathering.

### 1.3 Companionship Houses (VICE_COMPANION)

- Core offer:
  - Paid time with hosts/companions (conversation, flattery, intimacy, status aura).
- Clientele:
  - Guild officers, prosperous contractors, nobles’ retainers, ranking militia.
- Features:
  - Private rooms, strong discretion norms, curated clientele.
- Functions:
  - Soft diplomacy, espionage, blackmail, emotional dependence.

*(Content remains non-explicit; focus is on **status, secrecy, and leverage**, not sexual detail.)*

### 1.4 Stimulation Parlors (VICE_STIM)

- Core offer:
  - Inhaled/ingested substances and/or sensory pods (light/sound/VR-like immersion).
- Clientele:
  - Burnt-out workers, trauma victims, thrill-seekers, gang rank-and-file.
- Features:
  - Reclining spaces, controlled lighting/sound, house “guides” watching for trouble.
- Functions:
  - High-intensity escape, addiction pathways, clinic load, exploitable vulnerability.

### 1.5 Performance Houses / Theatres (VICE_STAGE)

- Core offer:
  - Music, drama, narrative feeds, propaganda plays, combat exhibitions.
- Clientele:
  - Mixed; from bunkhouse crews to minor nobles, depending on ward.
- Features:
  - Stages, backstage corridors, VIP balconies, crowd chokepoints.
- Functions:
  - Narrative control, morale management, faction flexing, rally points.

### 1.6 Mixed Vice Arcades (VICE_MIXED)

- Core offer:
  - A little of everything: small bar, a few games, rooms upstairs, cheap shows.
- Clientele:
  - Local neighborhoods, minor fixers, agents meeting under cover of noise.
- Features:
  - Flexible space, low visibility to central authorities.
- Functions:
  - Espionage staging ground, black-market negotiations, informal arbitration.

---

## 2. Roles & Chains of Responsibility

### 2.1 House Hierarchy

- **House Owner / Patron**
  - Often tied to:
    - Civic branch (licensed venue), a guild, a gang, or a minor noble.
  - Negotiates:
    - Permits, protection, informal “tax” with ward officials and militia.

- **Floor Boss / House Manager**
  - Runs nightly operations:
    - Staff schedules, table/room allocation, managing trouble.
  - Decides:
    - Who gets in, who is watched, who is tolerated, who is removed.

- **House Clerk / Bookkeeper**
  - Tracks:
    - Tabs, debts, payouts, supplier contracts, “special accounts” (protected clients).
  - Critical node for:
    - Money laundering, quiet tax fraud, debt-lists used as leverage.

### 2.2 Staff Roles

- **Servers / Bartenders / Dealers**
  - Close to:
    - Conversations, arguments, nervous tells, and flashes of wealth.
  - Naturally:
    - Recruited as informants or internal spies.

- **Performers / Hosts / Companions**
  - Provide:
    - Emotional/sensory services, flattery, status proximity.
  - Hold:
    - Fine-grained knowledge of client moods, secrets, and grudges.

- **Bouncers / House Guards**
  - Enforce:
    - House rules, ejections, “accidental” injuries, and selective cooperation with militia.
  - Choose:
    - When to escalate to external authorities vs handle internally.

- **Lookouts / Runners**
  - Watch:
    - Streets for patrols, rival gangs, or targeted visitors.
  - Carry:
    - Warnings, side messages, bribe deliveries.

### 2.3 External Links

- **Permit Officers / Civic Inspectors**
  - Check:
    - Licensing, permitted capacity, nominal compliance with vice rules.
- **Militia Liaison**
  - Manages:
    - Protection agreements, shakedowns, and targeted raids.
- **Espionage Branch Operatives**
  - Use venues for:
    - Meets, stings, observation of faction patterns.

---

## 3. Facility State Variables

Per vice facility, we define core state and tuning axes:

- Identity:
  - `facility_id`
  - `vice_type`: `DRINK | GAMBLE | COMPANION | STIM | STAGE | MIXED`
  - `ward`

- Capacity & Atmosphere:
  - `capacity_seated`
  - `capacity_standing`
  - `noise_level` (0–1)
  - `luxury_level` (0–1)
  - `crowd_density` (dynamic)

- Alignment & Governance:
  - `faction_alignment_primary`
  - `faction_alignment_secondary`
  - `GovLegit_vice` (0–1):
    - Perceived protection / official acceptance.
  - `corruption_level_vice` (0–1):
    - How deeply it’s woven into bribery and money laundering.
  - `surveillance_level`:
    - Combination of overt militia presence and covert espionage activity.

- Risk & Pressure:
  - `violence_risk_vice` (baseline)
  - `addiction_pressure` (0–1):
    - Likelihood that visits create dependency loops.
  - `raid_pressure`:
    - Likelihood of inspections, shakedowns, or raids in the near future.

- Economics:
  - `price_index_vice`:
    - Local affordability vs exclusivity.
  - `daily_revenue_estimate`
  - `credit_outstanding`:
    - Total value of unpaid tabs and credit extended.
  - `blackmail_stock`:
    - Abstract scalar of exploitable secrets accumulated.

This gives enough axes to differentiate:

- A loud, cheap worker bar.
- A velvet, espionage-heavy high-end house.
- A borderline illegal stim den on the edge of a gang ward.

---

## 4. Agent Drives & Reasons to Visit

Vice halls are where **agent drives surface** visibly.

Key drives expressed here:

- **Relief / Stress Drive**
  - Reduce accumulated stress after:
    - Dangerous shifts, humiliations, losses, or fear spikes.
- **Belonging / Social Drive**
  - Seek:
    - Familiar faces, faction comrades, or neutral ground to not be alone.
- **Status / Display Drive**
  - Spend conspicuously, sit in visible spots, be seen with important people.
- **Novelty / Stimulation Drive**
  - Chase:
    - New sensations, performances, risks, or stories.
- **Instrumental / Opportunistic Drive**
  - Use:
    - The venue as cover to meet contacts, negotiate, recruit, or gather intel.

In simulation terms:

- Each agent maintains:
  - A vector of needs (e.g. `stress`, `loneliness`, `status_insecurity`, `boredom`, `goal_opportunism`).
- When thresholds are crossed:
  - They consider (among other actions) visiting an entertainment/vice facility that:
    - Accepts their faction, fits their budget, and matches their drive profile.

---

## 5. Session Loop: Vice Block

We model a **vice block** as a chunk of time (evening/night cycle or shorter) where the venue runs.

### 5.1 Intake & Access Control

1. **Candidate Arrivals**
   - From:
     - Bunkhouses, kitchens, workshops, patrols, courts, streets.
   - Filtered by:
     - Distance, curfew, current risk tolerance, faction alignment.

2. **Door Decisions**
   - Bouncers/floor boss apply:
     - Entry rules:
       - Dress/cleanliness, known troublemakers, faction enemies, “no-fly” list from house owner or ward.
   - Outcomes:
     - `entry_granted`, `entry_delayed`, `turned_away` (possible resentment).

### 5.2 Placement & Grouping

Inside the venue:

- Agents are arranged into:
  - Tables, clusters at the bar, gambling circles, private rooms, quiet corners.
- Grouping influenced by:
  - Faction tags, existing relationships, current goals (deal vs escape vs spying).
- House staff may:
  - Intentionally place certain agents near/away from each other.

### 5.3 Consumption & Interaction

Per sub-step:

- Each agent decides:
  - What to consume:
    - Drinks, games, time with hosts, stim sessions, performance slots.
- Drives are adjusted:
  - `stress` ↓, `boredom` ↓, `addiction_marker` ↑, `wallet` ↓.
- Social interactions:
  - Conversations, arguments, flirting, threats, negotiations.
- House-level updates:
  - Revenue flows, tabs created/expanded, low-level incidents logged.

### 5.4 Incident Generation

Based on:

- `noise_level`
- `crowd_density`
- Average intoxication / stimulation
- Pre-existing tensions between factions/individuals
- `violence_risk_vice` and `surveillance_level`

We roll for micro-events, e.g.:

- **Brawls & Scuffles**
  - Chairs thrown, knives drawn, quick bouncer response.
- **Cheating Accusations**
  - Especially in gambling dens.
- **Pickpocketing / Theft**
  - Wallets, chits, small items.
- **Targeted Assault**
  - Contracted hits, intimidation campaigns.
- **Recruitment Pitch**
  - Gangs or militias offering protection or work.
- **Informant Contacts**
  - Espionage handler quietly buys info or plants a suggestion.

Each incident:

- May produce:
  - Clinic visits, court cases, deaths, or new obligations.

### 5.5 Exit & Aftermath

At end of block:

- Agents leave with updated:
  - Stress, addiction markers, wealth, debts, faction relations, rumor knowledge.
- Some:
  - Stagger to bunkhouses, clinics, holding cells, alleys, or morgues.

Venue updates:

- `daily_revenue_estimate`, `credit_outstanding`, `blackmail_stock`.
- Short-term `raid_pressure` may:
  - Increase if violence or noise exceeded tolerated thresholds.

---

## 6. Records & Information Surfaces

Tie to D-INFO-0005.

### 6.1 Record Types

- **LEDGER**
  - Revenue, wages paid to staff, supplier bills.
  - Tabs and debts; “comped” sessions for VIPs.
- **OP_LOG**
  - Incidents per block:
    - Fights, ejections, theft reports, notable visitors.
- **FORMAL_RECORDS**
  - Licenses, inspections, fines, warnings; occupancy violations.
- **LEGAL**
  - Only when:
    - Cases escalate to militia/courts.
- **SHADOW**
  - Informant rosters, discreet client notes, blackmail-relevant observations.

### 6.2 Information Surfaces

- **Door & Signage**
  - House branding, price tiers, “no weapons” or “no militia” signs.
- **Bar / Floor**
  - Major rumor surface:
    - Ambient conversations, toasts, songs, chants.
- **Back Office**
  - Tabs, debt ledgers, protected-account lists, supply contracts.
- **Back Rooms / Private Spaces**
  - Where:
    - Sensitive conversations and compromising situations occur.

---

## 7. Hooks into Other Systems

### 7.1 ECON

- **Income**
  - Converts wages/rations into:
    - WCR/KCR inflows for house owners, suppliers, and silent partners.
- **Debt**
  - Tabs become:
    - Enforceable obligations:
      - Labor promises, “do a job for us”, blackmail leverage.
- **Taxation & Laundering**
  - Declarable vs hidden income:
    - Feeds directly into Financial Ledgers & Taxation (D-ECON-0009).

### 7.2 INFO & ESPIONAGE

- Vice halls are:
  - Natural nodes for behavioral observation:
    - Who spends lavishly, who whispers, who is desperate, who is new.
- Espionage branch:
  - May own some houses outright, or have:
    - Deep cover staff among the servers/companions.
- Information flows:
  - Outward as:
    - Rumors, informant reports, and blackmail hooks.

### 7.3 MILITARY & COURTS

- Militia:
  - Run patrol passes past key venues; sometimes internal protection rackets.
- Courts:
  - See:
    - Fights, stabbings, scams, property damage, harassment, debt disputes.
- Street Tribunals:
  - Often:
    - Hold sessions near or inside busy vice halls to manage quick justice.

### 7.4 CIVIC (Kitchens, Clinics, Bodies)

- Kitchens:
  - Some vice venues host their own kitchens:
    - Higher-quality food as a repeat-visit driver.
- Clinics:
  - See:
    - Injuries and overdoses sourced from specific houses, shaping risk reputations.
- Body Reclamation:
  - Vice-originating deaths:
    - Gain special SHADOW attention if high-status or politically sensitive.

---

## 8. Simulation Hooks & Minimal Prototype

### 8.1 Minimal Vice Facility Schema

```json
{
  "facility_id": "W21_VICE_DRINK_01",
  "type": "VICE_DRINK",
  "ward": "W21",
  "capacity_seated": 40,
  "capacity_standing": 60,
  "noise_level": 0.7,
  "luxury_level": 0.3,
  "faction_alignment_primary": "guild_scrap",
  "faction_alignment_secondary": "gang_low",
  "GovLegit_vice": 0.5,
  "corruption_level_vice": 0.6,
  "surveillance_level": 0.5,
  "violence_risk_vice": 0.6,
  "addiction_pressure": 0.4,
  "price_index_vice": 0.4,
  "credit_outstanding": 320.0,
  "blackmail_stock": 0.2
}
```

### 8.2 Minimal Vice Block Loop

Per simulation block:

1. **Select Arrivals**
   - From agents whose drives:
     - Cross thresholds for relief, belonging, status, novelty, or opportunism.
2. **Apply Door Filter**
   - Respect:
     - Capacity, faction alignments, house policies.
3. **Simulate Interactions**
   - Consumption events → update:
     - Money, drives, addiction markers.
   - Social events → update:
     - Relationships, rumors, potential conflicts.
4. **Trigger Incidents**
   - Brawls, scams, recruitment, informant contacts, intimidation.
5. **Emit Events**
   - `ViceIncident`, `ViceRumorSpread`, `ViceDebtCreated`, `ViceRecruitment`, `ViceBlackmailUpdate`.
6. **Update Records**
   - LEDGER:
     - Income, losses, new debts.
   - OP_LOG:
     - Notable incidents.
   - SHADOW:
     - Sensitive observations and leverage.

---

## 9. Open Questions

For later refinement or ADRs:

- How granular should **addiction** be?
  - Single scalar vs per-substance/per-venue markers?
- Do some wards:
  - Outlaw certain vice types, or only push them underground?
- How visible should:
  - Vice halls be in the **player-facing UI**?
    - Literal venue maps vs abstract “vice load” indicators.
- How much do we model:
  - Long-term psychological impacts vs simple scalar drive changes?
- Should we introduce:
  - “Dry” or “austere” wards where vice is suppressed and tension stores up elsewhere?

For now, this microdynamics layer aims to:

- Make entertainment & vice venues a **central stage** for:
  - Agent drives, faction mixing, rumor, and soft control.
- Provide clear hooks for:
  - ECON (spend + debt), INFO (rumor + blackmail), MIL/ESP (control + surveillance),
  - And CIVIC (where your day ends after work, crime, or judgment).
