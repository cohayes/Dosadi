---
title: Civic_Microdynamics_Posting_Boards_and_Permit_Offices
doc_id: D-CIV-0003
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
  - D-CIV-0002    # Civic_Microdynamics_Clinics_and_Triage_Halls
---

# Civic Microdynamics: Posting Boards & Permit Offices

> This document defines **how the regime speaks and grants access** at the micro level:
> - What appears on posting boards and who controls it.
> - How permits, licenses, and approvals are requested, processed, and weaponized.
> - How these interfaces tie into ledgers, law, and rumor.
> - Where everyday life collides with bureaucracy, favoritism, and information war.

Posting boards and permit offices are **the paper face of power**:

- They tell you what is allowed, what is forbidden, and what is expected.
- They decide who gets to work, build, travel, or scavenge legally.
- They leak information in predictable and exploitable ways.

---

## 1. Facility Archetypes

We define three core civic interfaces:

1. **Public Posting Boards** (BOARD)
2. **Permit Counters / Offices** (PERMIT_OFFICE)
3. **Mobile / Embedded Desks** (MOBILE_COUNTER)

All three interact tightly with the clerical branch, civic branch, and law.

### 1.1 Public Posting Boards (BOARD)

Physical surfaces where official and semi-official notices are displayed.

Typical content:

- Quotas, ration rules, distribution schedules.
- Tax and fee announcements.
- Job calls, conscription notices, shift rosters.
- Bans, curfews, emergency orders.
- “Wanted” posters, bounties, rewards.
- Auction and confiscation notices.

Boards range from:

- **Ward Central Boards**
  - Large, curated, relatively authoritative.
- **Neighborhood Boards**
  - Messier, layered, subject to local tampering.
- **Guild / Faction Boards**
  - Semi-closed; focused on internal rules and opportunities.

### 1.2 Permit Counters / Offices (PERMIT_OFFICE)

Administrative desks or offices where agents:

- Apply for:
  - Work permits, stall licenses, scavenging rights, travel passes.
  - Construction/repair approvals, special access to restricted zones.
- Pay:
  - Application fees, recurring license fees, fines.

They maintain:

- Application records, permits issued, revocations, enforcement referrals.

### 1.3 Mobile / Embedded Desks (MOBILE_COUNTER)

Temporary or embedded variants:

- Pop-up counters at:
  - Markets, clinics, survival halls, recruitment drives.
- Used for:
  - Rapid registration, emergency passes, forced compliance (e.g., draft rolls).

Their records are:

- Often sloppier, more error-prone, and easier to manipulate or “lose”.

---

## 2. Roles & Chains of Responsibility

### 2.1 Civic & Clerical Chain

- **Permit Officer / Posting Supervisor**
  - Reports to:
    - Civic Staff Chief of Administration or Licensing.
  - Oversees:
    - Local boards and permit desks in a ward or district.
  - Interfaces with:
    - Clerical bureaus for record-keeping, and militia for enforcement.

- **Clerks (Licensing / Notice)**
  - Maintain:
    - Physical boards, posting schedules, and official notice archives.
  - Process:
    - Applications, renewals, fee collection, basic eligibility checks.

- **Runners / Couriers**
  - Carry:
    - Notices between ward offices and local boards.
  - Provide:
    - A natural point for delays, “lost” messages, and selective delivery.

### 2.2 Oversight & Enforcement

- **Inspectors / Auditors**
  - Check:
    - Whether boards show required notices.
    - Whether permits align with ledgers (who is licensed vs paying).
- **Militia Liaison**
  - Receives:
    - Lists of banned persons, revoked permits, curfew violators, wanted notices.
  - Enforces:
    - Arrests, confiscations, shop closures.

### 2.3 External Actors

- **Fixers / Brokers**
  - Help navigate:
    - Permit bureaucracy for a fee.
  - Often:
    - Know which clerks can be bribed and how much.
- **Espionage Operatives**
  - Watch boards for:
    - Movements, mobilization, shifts in policy.
  - Try to:
    - Insert, remove, or alter notices.
- **Propagandists / Agitators**
  - Post:
    - Counter-notices, graffiti, defacing official orders.

---

## 3. Posting Boards: State & Dynamics

### 3.1 Board State Variables

For each board:

- `board_id`, `ward`, `location_type`:
  - `CENTRAL`, `NEIGHBORHOOD`, `GUILD`, `FACTION`.
- `curation_level`:
  - 0–1 scale; higher = more tightly controlled.
- `posting_capacity`:
  - Max notices before old ones must be removed or layered over.
- `update_frequency`:
  - How often it is officially refreshed.
- `tamper_risk`:
  - Likelihood of unsanctioned posting/removal.

Board content representation:

- `notices_active[]`:
  - Each with:
    - `notice_id`, `type`, `issuer`, `posted_at`, `expires_at`, `priority`.
- `visual_clutter`:
  - Emergent metric from overlapping or outdated notices.

### 3.2 Notice Types

High-level categories:

- **RESOURCE_RULES**
  - Quotas, ration changes, new restrictions.
- **CIVIC_ORDERS**
  - Curfews, bans, movement restrictions, emergency orders.
- **ECONOMIC**
  - Tax schedules, fee changes, auctions, confiscations.
- **LABOR**
  - Job postings, draft notices, shift rosters.
- **LEGAL**
  - Punishments, executions, public shaming, wanted lists.
- **PERMITS**
  - Issued, revoked, suspended license lists.
- **PROPAGANDA**
  - Loyalty messages, ideological framing.
- **UNOFFICIAL**
  - Agitprop, rumor flyers, unauthorized adverts.

Each type has:

- Default **credibility** as perceived by agents.
- Different **attention weights** depending on their current situation.

---

## 4. Permit Offices: State & Dynamics

### 4.1 Office State Variables

For each permit office:

- `office_id`, `ward`, `scope`:
  - e.g. `SCAVENGING`, `STALLS`, `TRAVEL`, `CONSTRUCTION`, `GENERAL`.
- `queue_length`:
  - Number of pending applicants.
- `processing_capacity`:
  - Applications processed per block.
- `backlog`:
  - Unresolved applications older than some threshold.
- `corruption_level_permit`:
  - Influence of bribes, favoritism on outcomes.
- `GovLegit_office`:
  - Perceived legitimacy of the office.

### 4.2 Permit Types

Examples:

- **Work Permits**
  - Authorization to work in certain guilds, hazardous jobs, or regulated roles.
- **Market Stall Licenses**
  - Right to operate a stall in a given bazaar/market.
- **Scavenging Permits**
  - Rights to salvage in specific ruins, scrap zones, or infrastructure.
- **Building / Repair Permits**
  - Authorization to alter structures that may affect water/ventilation or security.
- **Travel Passes**
  - Ability to move between wards or access high-security zones.
- **Special Access Permits**
  - Access to restricted facilities (FX kiosks, high-tier clinics, exo-suit bays).

Permits carry:

- `holder_id`, `issuer`, `valid_from`, `valid_to`.
- `scope`, `zone`, `conditions`, `revocation_flags`.

---

## 5. Agent-Facing Microdynamics

### 5.1 Interacting with Posting Boards

Agents:

- Periodically scan boards depending on:
  - Literacy, curiosity, civic discipline, faction instructions.
- Focus on:
  - Different notice types based on:
    - Needs (food, shelter, work, safety).
    - Faction goals (target lists, mobilization, crackdowns).

Outcomes:

- Update **belief state**:
  - “Curfew now starts earlier.”
  - “New tax on exo-suit repairs.”
  - “My guild is hiring in Ward 19.”
- Generate **new goals**:
  - Seek a permit-office, avoid a patrol, attend a conscription muster, spread the news.

### 5.2 Interacting with Permit Offices

Agents can:

1. **Apply for a permit**
   - Choose type and scope; may need:
     - Sponsors, references, prior records (work history, guild membership).

2. **Wait in queue**
   - Queue experience shaped by:
     - `queue_length`, `GovLegit_office`, `corruption_level_permit`.

3. **Face a decision**
   - Application outcome influenced by:
     - Eligibility, ability to pay, faction endorsements, bribes, black marks.

4. **Receive a result**
   - `APPROVED`, `DENIED`, `DELAYED`, or “lost”.

Results then:

- Update:
  - Agent’s legal ability to act, and their relationship with the office/branch.

---

## 6. Records & Information Surfaces

### 6.1 Record Types

Tie to D-INFO-0005:

- **FORMAL_RECORDS**
  - Permit registers, issuance logs, revocation lists.
- **LEDGER**
  - Fee payments, fines, bribes (disguised entries), office budgets.
- **OP_LOG**
  - Applications processed per block, waiting times, denial rates.
- **LEGAL**
  - Enforcement referrals, “operating without permit” charges.
- **SHADOW**
  - Clerk’s side lists:
    - Bribe payers, blacklisted names, ghost permits.

### 6.2 Key Surfaces

- **Primary Posting Board Surface**
  - Public contact layer.
- **Clerk Desk Window**
  - Dialogue and negotiation point with agents.
- **Back Office Records Shelf**
  - Physical or digital store of permit registers and notices.
- **Courier Bags**
  - Transitional state where notices can be delayed, stolen, or altered.

---

## 7. Tampering, Corruption & Information War

### 7.1 Board Tampering

Actions:

- **Unauthorized Posting**
  - Agitprop, fake curfew updates, “official-looking” forgeries.
- **Selective Removal**
  - Removing:
    - Draft notices, tax announcements, revocation lists targeting allies.
- **Defacement**
  - Obscuring messages, mocking propaganda.

Mechanically:

- Alters:
  - What agents *see* vs what central authorities *believe* has been posted.

### 7.2 Permit Corruption

Common patterns:

- **Queue Skipping**
  - Bribes to be processed first.
- **Rubber-Stamping**
  - Approvals without real checks.
- **Ghost Permits**
  - Permits that exist in shadow records but not in official registers.
- **Strategic Denial**
  - Denial of permits to rivals or enemies of the current local regime.

Effects:

- Local **GovLegit_office** and **GovLegit_regime** shift over time.
- Faction **access** to economic opportunities and mobility is reshaped.

### 7.3 Espionage & Counter-Espionage

- Espionage Branch uses boards to:
  - Track mobilization, upcoming raids, changes in patrol patterns.
  - Leak disinformation or misdirected orders.
- Counter-intelligence:
  - Watches for:
    - Unusual notice patterns, forged seals, or “phantom” orders.

---

## 8. Interaction with ECON & INFO

### 8.1 ECON Hooks

- **Fees & Fines**
  - Every application, renewal, or revocation can:
    - Generate ledger entries and WCR/KCR flows.
- **Market Access**
  - Stall licenses and scavenging permits:
    - Mediate who participates in local markets (D-ECON-0002).
- **Tax Compliance**
  - Permit records:
    - Provide the **denominator** for expected tax and fee income.
  - Telemetry & audits:
    - Compare “licensed” vs “actually operating” entities.

### 8.2 INFO Hooks

- **Report Credibility**
  - Inconsistencies between:
    - Permit records, taxes, and telemetry:
      - Raise suspicion and feed D-INFO-0003 mechanisms.
- **Scholars & Clerks**
  - Maintain:
    - Central registries and historical archives of notice histories.

---

## 9. Simulation Hooks & Minimal Prototype

### 9.1 Minimal Board Schema

```json
{
  "board_id": "W21_CENTRAL_01",
  "ward": "W21",
  "location_type": "CENTRAL",
  "curation_level": 0.8,
  "posting_capacity": 50,
  "update_frequency": 3,
  "tamper_risk": 0.2,
  "notices_active": []
}
```

### 9.2 Minimal Permit Office Schema

```json
{
  "office_id": "W21_PERMIT_SCAVENGE",
  "ward": "W21",
  "scope": "SCAVENGING",
  "processing_capacity": 20,
  "queue_length": 0,
  "backlog": 0,
  "corruption_level_permit": 0.4,
  "GovLegit_office": 0.6
}
```

### 9.3 Minimal Loop

Per sim block:

1. Boards:
   - Add or expire notices based on:
     - Ward policies, events, and random updates.
   - Apply tampering events based on:
     - `tamper_risk` and local faction activity.

2. Permit Office:
   - Generate applications from agents needing work, stalls, travel, etc.
   - Process up to `processing_capacity`:
     - Using policy + corruption rules.
   - Emit:
     - OP_LOG, LEDGER entries, and possible LEGAL referrals.

3. Agents:
   - Sample boards, update goal sets.
   - Decide whether to:
     - Apply for permits, bribe, forge, or operate illegally.

---

## 10. Open Questions

- How fine-grained do we want the **permit taxonomy** to be in practice?
  - Start simple (stall, scavenging, travel) or go full bureaucratic?
- Should wards differ strongly in:
  - **Board culture** (strict, curated vs chaotic, layered)?
- Do we want:
  - A dedicated mechanic for **“official vs believed notice”** discrepancy at higher levels?
- How much **player-facing UI** mimics:
  - Literally reading boards vs summarised “intel” views?

For now, this document aims to:

- Give us enough structure to simulate:
  - How information and permission shape survival options.
- Provide hooks where:
  - Corruption, propaganda, and minor bureaucrats can actually matter.
