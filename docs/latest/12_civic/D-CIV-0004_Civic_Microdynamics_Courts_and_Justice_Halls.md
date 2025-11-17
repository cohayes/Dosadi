---
title: Civic_Microdynamics_Courts_and_Justice_Halls
doc_id: D-CIV-0004
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
  - D-CIV-0003    # Civic_Microdynamics_Posting_Boards_and_Permit_Offices
---

# Civic Microdynamics: Courts & Justice Halls

> This document defines **how law is applied in practice** at the ward scale:
> - The kinds of courts and minor justice halls that exist.
> - How cases flow from accusation to verdict to punishment.
> - How evidence, records, and rumor compete in the judgment process.
> - Where corruption, favoritism, and fear shape “justice”.

In principle, courts exist to:

- Keep violence contained inside **rules**.
- Turn **conflicts and infractions** into:
  - Fines, labor, exile, or death, instead of uncontrolled vendettas.

In practice on Dosadi:

- Law is an instrument of **survival and power**.
- Justice halls are pressure valves, staging grounds, and public theaters.

---

## 1. Facility Archetypes

We define four core justice interfaces:

1. **Street Tribunals** (TRIBUNAL_STREET)
2. **Ward Justice Halls** (JUSTICE_WARD)
3. **Special Courts & Inquisitorial Chambers** (COURT_SPECIAL)
4. **Internal Faction Courts** (COURT_FACTION)

They share common flows but differ in reach, formality, and brutality.

### 1.1 Street Tribunals (TRIBUNAL_STREET)

- Location:
  - Near markets, bunkhouses, kitchens, militia posts.
- Role:
  - Handle **low-severity and immediate** disputes:
    - Petty theft, small fights, minor ration violations, curfew slips.
- Purpose:
  - Prevent escalation, keep the streets from boiling over.
- Tools:
  - Spot fines, brief detention, beatings, short bans, forced apologies.

Often chaired by:

- A **Street Adjudicator**:
  - Senior militia officer, civic boss, or trusted local proxy.

### 1.2 Ward Justice Halls (JUSTICE_WARD)

- Location:
  - Ward civic centers or near the lord’s compound.
- Role:
  - Handle:
    - Serious property cases, industrial accidents, organized violence, fraud, significant permit violations.
- Purpose:
  - Integrate:
    - Evidence from investigators, spies, telemetry, ledgers, and reports.
- Tools:
  - Long-term sentences, labor assignments, exile, confiscations, public executions.

Presided over by:

- **Ward Judges / Arbiters**:
  - Appointed by the lord or higher nobles.

### 1.3 Special Courts & Inquisitorial Chambers (COURT_SPECIAL)

- Location:
  - Semi-secret chambers, militia fortresses, espionage compounds.
- Role:
  - Deal with:
    - Treason, espionage, high-level corruption, factional conspiracies.
- Purpose:
  - Protect the regime.
- Tools:
  - Closed-door procedures, enhanced interrogation, “disappearances”.

Often joint ventures between:

- Espionage Branch, Militia command, and select Judges/Bishops.

### 1.4 Internal Faction Courts (COURT_FACTION)

- Location:
  - Guild halls, gang strongholds, religious/ideological enclaves.
- Role:
  - Adjudicate:
    - Violations of internal codes: disloyalty, profit skimming, taboo breaking.
- Official Status:
  - Sometimes tolerated or quietly integrated:
    - As long as they don’t directly undermine ward law.

Their decisions:

- Might be recognized (or ignored) by ward courts depending on power balances.

---

## 2. Roles & Chains of Responsibility

### 2.1 Formal Justice Chain

- **Ward Judge / Arbiter**
  - Reports to:
    - Lord of the ward or directly to higher nobles.
  - Decides:
    - Outcomes in significant cases.
  - Guards:
    - The “shape” of law in the ward (even if biased).

- **Justice Clerk**
  - Manages:
    - Case files, scheduling, verdict records, sentencing registers.
  - Key node for:
    - Record tampering, delayed filings, selective “misplacement”.

- **Court Scribe**
  - Records:
    - Hearings, testimonies, formal notices of verdicts.

### 2.2 Enforcement & Investigation

- **Militia Representatives**
  - Bring:
    - Detainees, enforcement reports, witness statements.
  - Execute:
    - Arrests, punishments, property seizures.

- **Investigators**
  - Present:
    - Evidence bundles, interrogation reports, cross-referenced records.
  - Argue:
    - For certain narratives of events.

- **Espionage Branch Liaisons**
  - May:
    - Provide sealed intelligence or push for closed trials.

### 2.3 Defenders, Advocates & Fixers

- **Advocates / Pleaders**
  - Not strictly “lawyers” but:
    - People skilled at arguing cases, negotiating plea deals.
  - Some:
    - Are officially recognized; others operate informally.

- **Fixers**
  - Arrange:
    - Bribes, witness “unavailability,” favorable judges, missing files.

- **Community Representatives**
  - In some wards, select elders or bosses:
    - Speak on behalf of groups (bunkhouse residents, guild members).

---

## 3. Case Types & Severity Bands

To keep simulation manageable, we define **bands**, not exhaustive codes.

### 3.1 Severity Bands

- **Band A – Petty Infractions**
  - Minor theft, disorderly conduct, low-level permit violations.
  - Typically handled by:
    - Street Tribunals.
- **Band B – Serious Civic & Economic Offenses**
  - Repeated theft, organized scams, serious permit offenses, unpaid debts affecting stability.
  - Ward Justice Halls domain.
- **Band C – Violence & Public Order**
  - Assault, murder, riots, sabotage, gang warfare spillover.
- **Band D – Regime Threat / High Treason**
  - Conspiracy against lords/king, espionage for enemies, sabotage of vital infrastructure.

Each band:

- Has default response sets:
  - Fines, labor, confinement, exile, execution.

---

## 4. Case Flow: From Event to Court

We sketch a generic pipeline; not all cases traverse all stages.

1. **Incident Occurs**
   - In kitchens, bunkhouses, clinics, markets, streets, industry sites.

2. **Initial Handling**
   - Militia, facility bosses, investigators or espionage agents:
     - Decide whether to repress quietly, handle internally, or escalate.

3. **Record Creation**
   - Telemetry snapshot (if relevant).
   - OP_LOG entries (incident logs).
   - LEGAL stub record (charge draft).
   - SHADOW notes (if someone wants leverage later).

4. **Charge & Referral**
   - Formal charges drafted for:
     - Street Tribunal or Ward Justice Hall.
   - Some cases go straight to:
     - Special Courts, bypassing public venues.

5. **Pre-Hearing Decisions**
   - Detention or release pending.
   - Bail-like mechanisms:
     - Sponsors, bonds, political protection.

6. **Hearing / Trial**
   - Presentation of:
     - Evidence, testimonies, narratives.
   - Judge/Arbiter:
     - Issues ruling.

7. **Sentencing**
   - Type + duration/intensity of punishment.
   - Referral to:
     - Labor pools, militia, clinics (for post-violence processing), or executioners.

---

## 5. Session Loop: Street Tribunal

### 5.1 Tribunal Block

A **tribunal block** represents a short session handling multiple low-level cases.

1. **Case Intake**
   - Batch of Band A cases:
     - From militia, civic facilities, complaints by bosses/patrons.

2. **Quick Screening**
   - Tribunal figure:
     - Tosses obviously trivial or politically problematic cases.
   - Some:
     - Are downgraded to on-the-spot warnings.

3. **Abbreviated Hearing**
   - Accuser and accused both present (ideally).
   - Evidence:
     - Mostly verbal, with occasional written notes.

4. **Immediate Decision**
   - Options:
     - Small fines, minor beatings, restitution, short holding cell time, local bans.

5. **Record Update**
   - OP_LOG (cases handled).
   - LEGAL entries (if needed for repeat-offender tracking).
   - SHADOW notes for:
     - Bribes or favors.

Tribunals emphasize:

- **Speed over rigor**.
- Keeping tensions manageable in volatile zones.

---

## 6. Session Loop: Ward Justice Hall

### 6.1 Pre-Hearing

1. **Case Docketing**
   - Justice clerks:
     - Build docket for the session, balancing:
       - Severity, political sensitivity, and scheduling constraints.

2. **Evidence Compilation**
   - Investigators:
     - Provide linked record packs:
       - Telemetry excerpts, ledgers, op logs, prior legal entries.

3. **Behind-the-Scenes Pressure**
   - Espionage, nobles, branch heads:
     - Attempt to sway outcomes via:
       - Private audiences, sealed memos, or intimidation.

### 6.2 Hearing / Trial Block

For each case:

1. **Reading of Charges**
   - Based on LEGAL record:
     - Code, severity band, alleged facts.

2. **Presentation of Evidence**
   - Investigators, militia, facility bosses, and witnesses.
   - Advocates can:
     - Challenge credibility, point to contradictory records.

3. **Deliberation**
   - Sometimes formal, sometimes perfunctory.
   - Judge weighs:
     - Regime stability, faction balances, personal risk.

4. **Verdict**
   - `GUILTY`, `PARTIAL`, `NOT_GUILTY`, `DEFERRED`.

### 6.3 Sentencing & Effects

Sentences may include:

- **Fines & Confiscations**
  - Direct ECON impact:
    - Confiscate suits, tools, stall rights, water allotments.
- **Labor Assignments**
  - Forced labor:
    - To industry, reclamation, hazardous zones, or megaprojects.
- **Bans & Restrictions**
  - Ward bans, curfew restrictions, “no-permit” lists.
- **Confinement**
  - Time in local holding, ward prisons, or special facilities.
- **Execution / Disappearance**
  - Public or private, depending on intended signalling.

Records:

- LEGAL:
  - Full case file, verdict, sentence.
- FORMAL_REPORT:
  - For high-visibility cases.
- SHADOW:
  - Who intervened, who paid, who owes favors.

---

## 7. Special Courts & Inquisitorial Chambers

### 7.1 Secretive Procedures

- Almost entirely **opaque** to the general population.
- Cases:
  - Often triggered by espionage branch intelligence.

Procedures:

1. Secret detention.
2. Interrogation and coercive “evidence collection”.
3. Minimal or no open hearing.
4. Sentences that:
   - Restructure factions, remove leaders, flip agents.

### 7.2 Regime Management

These courts are:

- Tools for:
  - Pruning dangerous nodes in the social network.
- Risky to use:
  - Overuse undermines:
    - Perceived legitimacy of open justice halls.

Simulation wise:

- Act as:
  - High-impact, low-frequency events.
- Generate:
  - Large reputation and fear ripples.

---

## 8. Faction Courts & Overlapping Jurisdiction

### 8.1 Internal Courts

Factions (guilds, gangs, sects) may:

- Run their own tribunals for:
  - Violations of internal rules.

Their sentences:

- Fines, demotions, beatings, expulsion, or faction-specific taboos.

### 8.2 Interaction with Ward Law

Depending on power dynamics:

- Ward courts may:
  - Respect or ignore faction rulings.
- Factions may:
  - Shield their members from ward justice.
  - Hand them over selectively to curry favor.

Overlapping jurisdiction:

- Provides hooks for:
  - Negotiations, hostages, and strange compromises.

---

## 9. Records & Information Surfaces

Tie to D-INFO-0005.

### 9.1 Record Types

- **LEGAL**
  - Charges, verdicts, sentences, warrants.
- **FORMAL_REPORT**
  - High-profile cases, especially those with political value.
- **LEDGER**
  - Fines, confiscations, value of seized assets.
- **OP_LOG**
  - Cases processed per block, clearance rates.
- **SHADOW**
  - Unofficial case notes, “real reasons” for decisions, blackmail material.

### 9.2 Surfaces

- **Courtroom Floor**
  - Public theatre for selected cases.
- **Docket Boards**
  - Posting of upcoming hearings, high-profile verdicts.
- **Back Chambers**
  - Judge + liaison discussions, sealed record archives.
- **Execution Grounds / Public Squares**
  - Where outcomes are made visible:
    - Bodies, displays, symbolic punishments.

---

## 10. Simulation Hooks & Minimal Prototype

### 10.1 Minimal Court Schema

```json
{
  "facility_id": "W21_JUSTICE_HALL_01",
  "type": "JUSTICE_WARD",
  "ward": "W21",
  "processing_capacity": 10,
  "backlog": 25,
  "GovLegit_courts": 0.5,
  "corruption_level_courts": 0.4,
  "fear_level_courts": 0.7
}
```

### 10.2 Minimal Case Schema

```json
{
  "case_id": "W21_0482_013",
  "severity_band": "B",
  "charges": ["permit_violation", "fraud_minor"],
  "accused_id": "agent_1234",
  "accuser": "W21_PERMIT_SCAVENGE",
  "evidence_links": ["LEDGER:tx_8892", "OP_LOG:perm_040", "SHADOW:note_112"],
  "faction_tags": ["guild_scavengers"],
  "political_sensitivity": 0.3
}
```

### 10.3 Minimal Loop

Per justice block:

1. Build/advance docket up to `processing_capacity`.
2. For each case:
   - Draw judge bias, corruption influences, evidence credibility.
   - Compute verdict and sentence.
3. Update:
   - LEGAL records, fines, resource flows, reputations, fear/legitimacy metrics.
4. Spillover:
   - High-profile sentences may:
     - Trigger faction resentment, compliance, or covert retaliation.

---

## 11. Open Questions

For later elaboration:

- How much **procedural variation** between wards?
  - Some may favor:
    - Brutal street justice; others more formal hearings.
- Should there be:
  - A concept of **appeals** to higher courts (duke/king level)?
- How do we:
  - Integrate **body disposal & reclamation** with executions and prisons?
- At what scale do courts:
  - Start to feel like a **strategic tool** in simulation vs pure flavor?

For now, this microdynamics layer aims to:

- Give a concrete shape to how **conflicts and infractions are processed**.
- Provide hooks where:
  - Evidence systems, faction politics, and fear/legitimacy all plug into one visible arena.
