---
title: Scholars_and_Clerks_Branch
doc_id: D-INFO-0004
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
depends_on:
  - D-WORLD-0003   # Ward_Branch_Hierarchies
  - D-INFO-0002    # Espionage_Branch
  - D-INFO-0003    # Information_Flows_and_Report_Credibility
  - D-INFO-0001    # Telemetry_and_Audit_Infrastructure (placeholder)
---

# Scholars & Clerks Branch

> Working name: **Scholars & Clerks** / **Clerical Services Pillar**.  
> This doc treats them as a fifth pillar in the overall structure, but one that is primarily loyal to the **crown**, not to any single ward.

---

## 1. Purpose & Scope

The **Scholars & Clerks Branch** (“Clerical Services”) is the institutional memory and measurement system of the regime. While other branches fight, build, feed, and spy, the clerks:

- Maintain **standardized records** of production, distribution, population, and enforcement.
- Define and update the **taxonomies** used in other documents:
  - Reason codes, facility types, branch categories, legitimacy labels.
- Generate **baselines and anomaly flags** used to evaluate report credibility.
- Provide higher authorities (Dukes, king) with a **second opinion** on ward health and honesty, independent of ward lords.

This branch is:

- **Physically present** in most wards (small offices, archives, counting houses).  
- **Structurally upward-facing**: promotion, protection, and prestige primarily flow from the crown and its proxies, not from ward lords.

This is a **simulation-facing design doc** that should be used to:

- Define clerk-type agents and their loyalties.  
- Model how “objective-ish” measurements are produced, manipulated, or suppressed.  
- Provide hooks for audits, statistical suspicion, and external intervention.

---

## 2. Position in the Power Structure

### 2.1 The Fifth Pillar

At the macro level, the polity has five major pillars:

1. Civic Branch  
2. Industrial Branch  
3. Military Branch  
4. Espionage Branch  
5. **Scholars & Clerks Branch**

Unlike the other four, **Scholars & Clerks**:

- Do **not** primarily act *for* the ward.  
- Instead, they act as **custodians of the king’s view of reality**:
  - They maintain the “canonical” ledgers and baselines that the crown trusts.
  - They translate the chaos of ward life into numbers, charts, and trends.

### 2.2 Upward vs Local Loyalty

Clerks have **dual accountability**:

- **Local**:
  - Hosted by the ward:
    - They occupy rooms in administrative complexes, civic halls, or dedicated archives.
  - Depend on ward branches for:
    - Basic security, lodging, food, access to facilities.

- **Upward (Primary)**:
  - Answer to regional **Prefects of Records** and the **Royal Archive**.
  - Career advancement, honors, and protection depend on:
    - The accuracy and usefulness of their work as judged from above.
    - Their ability to resist local capture and maintain standards.

Simulation intent:

- In most cases, **upward loyalty dominates**, but local pressure can corrupt, intimidate, or co-opt individual clerks and even whole offices.

---

## 3. Internal Structure & Tiers

The branch can be mapped onto the familiar tier system, but its **geography** is different: it spans multiple wards and levels of authority.

### 3.1 Macro Tiers (Empire-Wide)

**Tier 0 – The King (or Supreme Authority)**  
- Ultimate owner of all central ledgers and archives.
- Defines the **political demand** for truth vs convenient fiction.
- Can order:
  - System-wide audits,  
  - Ledger purges,  
  - Rewriting of official histories.

**Tier 1 – High Archivist / Master of Records**  
- Head of the Scholars & Clerks Branch.
- Designs and updates:
  - Standard forms, codes, and classification schemes.  
  - Training curricula for clerks.  
- Mediates between:
  - The king’s desire for control,  
  - The practical limits of measurement and honesty.

**Tier 2 – Regional Prefects of Records**  
- Oversee clusters of wards (a duchy, province, or equivalent).
- Responsibilities:
  - Supervise Ward Archivists.  
  - Compare wards against each other (inter-ward baselines).  
  - Flag outlier wards for further scrutiny or reward.

### 3.2 Ward-Level Tiers

**Tier 3 – Ward Archivist / Chief Clerk**  
- Local head of the Scholars & Clerks Branch in a given ward.
- Oversees:
  - Ward ledgers of population, production, enforcement, water allocation, etc.  
  - Local teams of ledger clerks and enumerators.
- Balances:
  - Surviving local politics,  
  - Maintaining enough integrity to satisfy regional Prefects.

**Tier 4 – Senior Ledger Clerks & Analysts**  
- Maintain major ledgers:
  - Production & Quotas  
  - Rations & Water  
  - Residency & Labor Assignments  
  - Fines, Licenses, and Taxation
- Perform:
  - Baseline comparison and anomaly detection (per D-INFO-0003).  
  - Preparation of ward summaries for upward reporting.

**Tier 5 – Enumerators & Copyists**  
- Enumerators:
  - Visit facilities, observe queues, count outputs, sample records.  
  - Perform spot checks and small surveys.  
- Copyists:
  - Duplicate ledgers, produce clean copies for archives and regional dispatches.  
  - Handle routine recording tasks.

They are:

- The most exposed to **local intimidation** and bribery.  
- The ones who physically encounter the raw messiness of ward life.

---

## 4. Core Functions

### 4.1 Standardization of Categories & Forms

The branch defines and maintains:

- **Taxonomies**:
  - Facility types, worker classes, offense categories, reason codes.  
- **Standard forms**:
  - Quota reports, incident reports, population rolls, license registries.  
- **Measurement units and tick frames**:
  - How to count a “shift,” a “ration,” a “maintenance cycle,” etc.

This ensures that:

- Data from different wards can be compared at all.  
- Espionage, Military, and Industrial branches have shared reference frames.

### 4.2 Maintenance of Baselines

Ward-level and regional clerks:

- Aggregate incoming data over time to create **baselines**:
  - Expected failure rates by sector.  
  - Typical food distribution vs population.  
  - Normal ranges of unrest signals (fights, thefts, arrests).

They then:

- Detect **anomalies** when:
  - A facility or ward deviates too far from its peers or history.
  - Reason codes are overused (e.g., too many “equipment malfunction” excuses).

### 4.3 Credibility & Advisory Role

Clerks do not directly command militias or guilds, but they:

- Assign **credibility weights** to:
  - Official reports from branches.  
  - Telemetry data (once Telemetry doc is defined).  
  - Espionage intel (where shared).

- Issue **advisory notes** to:
  - Ward lords (“Your industrial branch reports are unusually smooth.”).  
  - Regional Prefects and the High Archivist (“Ward X shows signs of systemic falsification.”).

Higher authorities may then:

- Order audits, arrests, or replacement of ward leadership based on these signals.

### 4.4 Archival & Historical Control

Clerks maintain **archives**:

- Old ledgers, incident reports, and correspondence.  
- Records of:
  - Past purges, promotions, and disasters,  
  - Historical water allocations, treaties, and decrees.

These archives:

- Allow long-term trend analysis.  
- Can be selectively opened or “lost” according to political needs.

---

## 5. Tools & Methods

### 5.1 Data Sources

Clerks draw on:

- **Branch reports**:
  - Civic, Industrial, Military, Espionage (official summaries).  
- **Telemetry & meters**:
  - Water flow, energy use, ration stamps, access logs.  
- **On-site enumeration**:
  - Spot counts at kitchens, bunkhouses, workshops, queues.  
- **External benchmarks**:
  - Data from other wards of similar type and size.

### 5.2 Sampling & Spot Checks

Enumerators:

- Conduct **routine sampling**:
  - Every N cycles, a random bunkhouse or workshop is visited.  
  - Tally observed outputs, population, queue lengths.

- Conduct **targeted spot checks**:
  - Triggered by anomaly flags or suspicious reports.  
  - May cooperate with Investigators (Espionage) or local Civic staff.

Spot checks feed back into:

- Updated baselines.  
- Credibility adjustments for specific facilities or Bosses.

### 5.3 Seals, Signatures & Chains of Custody

To protect data integrity (on paper at least):

- Important ledgers and documents:
  - Carry **clerk seals** and signatures.  
  - Have **copy counts** maintained (how many copies, where they live).

- **Chains of custody**:
  - Track who had access to key documents and when.  
  - Help identify likely tampering points.

These measures can be:

- Effective defenses against clumsy manipulation.  
- Or theater, when everyone involved is compromised.

---

## 6. Capture, Corruption & Resistance

### 6.1 Methods of Capture

Ward lords, branch heads, and shadow factions may try to **capture** the local clerical office via:

- **Bribery**:
  - Direct payments, gifts, or special rations.  
- **Intimidation**:
  - Threats to family, quiet violence, orchestrated “accidents”.  
- **Career Manipulation**:
  - Blocking upward promotion paths, forcing local dependence.  
- **Replacement**:
  - Pushing for the removal of an “unfriendly” Ward Archivist and installing a more pliable one.

### 6.2 Clerical Resistance

Clerks have some tools to resist:

- **Upward reporting channels**:
  - They can quietly inform Regional Prefects of local interference.  
- **Distributed copies**:
  - Sending copies of sensitive ledgers off-site.  
- **Technical opacity**:
  - Complex systems of notation and cross-references that are hard for lay elites to fully control.

Resistance is not guaranteed:

- Many clerks will fold under sustained pressure.  
- Some offices become essentially **ward-controlled** propaganda engines.

### 6.3 Consequences of Capture

When clerks are captured:

- Baselines and anomaly flags become **unreliable**:
  - Under-reporting of unrest or shortages.  
  - Over-reporting of compliance and productivity.

- Higher authorities may:
  - Remain ignorant for long periods, or  
  - Eventually realize the discrepancy via:
    - Inter-ward comparisons,  
    - Espionage reports,  
    - Catastrophic failures.

Once discovered:

- Wards can be subjected to:
  - Harsh audits,  
  - Leadership purges,  
  - Temporary direct rule by external administrators.

---

## 7. Relationships with Other Branches

### 7.1 Civic Branch

- Provides:
  - Most of the **administrative infrastructure** and local office space.  
  - Access to residency records, licensing offices, local courts.

- In return:
  - Civic branch’s own reports are subject to clerk scrutiny.  
  - Civic Bosses must live with the knowledge that:
    - Their numbers may be cross-checked and challenged.

### 7.2 Industrial Branch

- Provides:
  - Technical maintenance of meters and measurement devices.  
  - Expertise on what failure rates are plausible.

- Gains:
  - A channel to argue:
    - “Yes, the machines are actually breaking this often”  
    - or frame failures as external.

- Also risks:
  - If clerks suspect that industrial actors are gaming telemetry, suspicion rises sharply.

### 7.3 Military Branch

- Uses clerical data for:
  - Assessing recruitment pools,  
  - Planning logistics,  
  - Evaluating unrest indicators.

- Fears:
  - That clerks will expose skimming, ghost soldiers, or falsified readiness reports.

- Can:
  - Act as muscle to protect or intimidate clerks, depending on alignment.

### 7.4 Espionage Branch

- Receives:
  - Anomaly flags and baseline data as **lead generators**.  
  - Clerical notes suggesting where fraud or capture may be occurring.

- Provides:
  - Independent intelligence on whether:
    - Clerk offices are captured,  
    - Ward reports are being heavily spun.

Together, they form the core of the **information integrity system**: one quantitative, one qualitative (and dirty).

---

## 8. Simulation Hooks

### 8.1 Agent Types

Introduce agent types such as:

- `WardArchivist` (Tier 3)  
- `SeniorClerk` / `Analyst` (Tier 4)  
- `Enumerator` / `Copyist` (Tier 5)

With attributes:

- `loyalty_upward` vs `loyalty_local`  
- `susceptibility_bribe`, `susceptibility_threat`  
- `competence` (affects baseline quality)  
- `integrity` (reluctance to falsify)

### 8.2 Clerk Office State

Each ward has a **ClerkOffice** entity with:

- `capture_level` ∈ [0,1]:
  - 0 = fully crown-loyal,  
  - 1 = fully ward/faction captured.

- `baseline_quality`:
  - How accurate and up-to-date the baselines are.

- `audit_frequency`:
  - How often upward authorities check on the ward.

These influence:

- Reliability of `credibility_score` assignments in D-INFO-0003.  
- Likelihood that ward-level fraud is detected early.

### 8.3 Events & Triggers

Possible events:

- **Clerk Rotation**:
  - Regional Prefect reassigns Ward Archivist or key clerks.  
  - Can reset capture level or cause turmoil.

- **Audit Wave**:
  - A special period where:
    - Enumerators flood facilities,  
    - Espionage runs parallel investigations,  
    - Branches experience intense scrutiny.

- **Ledger Loss or Fire**:
  - Accidental or intentional destruction of archives.  
  - Creates uncertainty and potential for rewriting history.

### 8.4 Interplay with Credibility System

- High `baseline_quality` & low `capture_level` →  
  - Credibility scores are **sharp and dangerous**.  
  - Branches lie less (or are caught quickly).

- Low `baseline_quality` or high `capture_level` →  
  - Credibility scores are noisy or biased.  
  - Some factions enjoy long impunity, others suffer unjust suspicion.

---

## 9. Open Design Questions

For future refinement:

- Should some wards be **experimental**:
  - With more automated telemetry and fewer clerks?  
  - Or vice versa, heavily clerk-driven with minimal meters?

- How often do **regional interventions** occur in practice?
  - Are they rare, dramatic events, or a constant slow pressure?

- Do clerks have:
  - A semi-formal **ideology** (e.g., devotion to “the record” as sacred)?  
  - Or are they primarily career bureaucrats with pragmatic ethics?

These choices will strongly shape the *feel* of the branch in play and can be tuned per campaign or simulation scenario.
