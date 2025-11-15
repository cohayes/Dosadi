---
title: Information_Flows_and_Report_Credibility
doc_id: D-INFO-0003
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-15
depends_on:
  - D-WORLD-0003   # Ward_Branch_Hierarchies
  - D-INFO-0002    # Espionage_Branch
  - D-INFO-0001    # Telemetry_and_Audit_Infrastructure (placeholder)
---

# Information Flows & Report Credibility

## 1. Purpose & Scope

This document defines how **information flows** through a ward’s power structure and how the **credibility of reports** is evaluated.

It focuses on:

- **Who reports to whom**, and by what **medium** (verbal, written, encoded).  
- How **loyalty, risk, and payoff** shape the **truthfulness** of reports.  
- How **reasons** and **excuses** are encoded in reports (e.g., quota failures).  
- How **Scholars/Clerks** and Espionage jointly evaluate credibility using:
  - Historical baselines,  
  - Anomaly detection,  
  - Cross-source comparisons.

This doc is tightly coupled with:

- D-WORLD-0003 (Ward_Branch_Hierarchies)  
- D-INFO-0002 (Espionage_Branch)  
- D-INFO-0001 (Telemetry_and_Audit_Infrastructure, placeholder)

and is intended as a **simulation design reference** for:

- Generating report events.  
- Determining their likelihood of being truthful.  
- Computing “credibility scores” that influence branch decisions and investigations.

---

## 2. Reporting Media & Channels

### 2.1 Types of Media

Reports are broadly categorized by **medium**:

1. **Verbal (Ephemeral)**
   - Face-to-face conversations, whispered updates, off-the-record briefings.
   - Leaves no direct documentary trail.
   - Common where:
     - Content is highly incriminating, or  
     - Trust is low and fear of interception is high.

2. **Written (Persistent)**
   - Ledgers, formal reports, official letters, signed statements.
   - Can be stored, copied, audited.
   - Common at higher tiers and in routine operations.

3. **Encoded / Obfuscated**
   - Coded messages, ciphered ledgers, marginalia with dual meaning.
   - Often used by Espionage and black-market actors.
   - Adds another layer of failure:
     - Mis-encoding, mis-decoding, or partial reconstruction.

### 2.2 Media by Tier

As a rule of thumb:

- **Tier 5–4 (Frontline, Bosses, Sub-bosses)**
  - Dominated by **verbal** reporting:
    - Immediate incidents, complaints, whispers about trouble.  
  - Written records are:
    - Minimal (short notes, sign-in sheets, ration tallies).  
    - Often incomplete or sanitized.

- **Tier 3–2 (Sub-Chiefs, Guild Leaders, Warband Leaders, Sector Chiefs)**
  - Mixed media:
    - Verbal consultation first (“How do we phrase this?”),
    - Then **formalized written reports** upward.
  - This is where “raw truth” is most aggressively **shaped** into official versions.

- **Tier 1–0 (Branch Heads, Lord)**
  - Primarily **written summaries**, digests, and dossiers.  
  - Supplemented by:
    - Occasional private verbal briefings,  
    - Selected anecdotal intelligence from Espionage and personal informants.

### 2.3 Incriminating Content & Drafting Process

Highly incriminating information (e.g., corruption, security failures, near-rebellions):

- Often delivered **verbally first**, to:
  - Sound out the superior’s reaction.  
  - Negotiate language, blame assignment, and mitigation strategies.

Only after this consultation does a **written version** appear:

- Adjusted to:
  - Protect key individuals,  
  - Spread responsibility,  
  - Emphasize external causes over internal negligence.

---

## 3. Truthfulness Model

### 3.1 Core Factors

The **truthfulness** of a report is influenced by:

1. **Loyalty**
   - To the branch, to immediate superior, to external patrons.
   - High loyalty → greater willingness to report unpleasant truths for long-term stability.
   - Low loyalty → more willing to falsify, spin, or omit if beneficial.

2. **Perceived Audit Risk**
   - Presence of auditors, investigators, and strong telemetry/ledger systems.  
   - Recent examples of:
     - Others being caught lying and punished,  
     - Reports being cross-checked and falsifications exposed.

3. **Perceived Payoff for Lying**
   - Personal benefits:
     - Avoiding blame, gaining promotion, protecting allies.  
   - Branch or faction benefits:
     - Securing extra resources, avoiding sanctions.

4. **Personal Risk & Fear**
   - Fear of:
     - Superiors’ anger,  
     - Reprisal from those implicated,  
     - Exposure of one’s own side activities.

5. **Competence & Information Quality**
   - Some false reports stem from:
     - Genuine misunderstanding,  
     - Poor data,  
     - Over-reliance on a single bad source.

### 3.2 Behavioral Rules of Thumb

Qualitative rules that simulation logic may implement:

- When **perceived audit risk is high** and **payoff for lying is low**:
  - Reports are **mostly truthful** (with minor self-serving spin).

- When **perceived audit risk is low** or **payoff is high**:
  - Probability of **significant falsification** rises sharply.

- When **loyalty to long-term survival of the organization is high**:
  - Agents are more willing to report unpleasant truths (even if locally painful).

- When **loyalty is primarily self-serving or external**:
  - Reports are more likely to be:
    - Cherry-picked,  
    - Delayed,  
    - Edited to support external patrons.

### 3.3 Suggested Simulation Sketch (Informal)

For a given report:

- Let:
  - `L` = loyalty_to_superior_or_branch (0–1)  
  - `R` = perceived_audit_risk (0–1)  
  - `P` = perceived_payoff_for_lying (0–1)

Then qualitatively:

- `P_truthful` grows with `L` and `R`, shrinks with `P`.  
- A simple monotone example (for Codex to refine):

> `P_truthful ≈ clamp( 0.2 + 0.5*L + 0.4*R - 0.5*P, 0.0, 1.0 )`

This is **not canonical math**, just guidance for implementation: the doc’s intent is that **fear of exposure** and **loyalty** usually beat greed, but not always.

---

## 4. Report Structure & Reason Codes

### 4.1 Standardized Report Elements

To enable credibility checks, reports should contain:

1. **Outcome Metrics**
   - e.g., Production achieved vs quota,  
   - Food served vs assigned ration,  
   - Patrol coverage vs planned routes.

2. **Reason Codes**
   - Categorical explanations for deviation from expected outcomes:
     - Equipment malfunction  
     - Worker absenteeism  
     - Supply shortfall  
     - Security incident  
     - Weather/environmental anomaly  
     - Unrest/violence  
     - Administrative delay  
     - Sabotage suspected  
     - Unknown / not reported

3. **Qualitative Narrative**
   - Short free-text or coded narrative:
     - “Main condenser pump failed mid-cycle; awaiting parts from guild.”  
     - “Militia requisitioned trucks unexpectedly; two delivery runs missed.”

4. **Attribution**
   - Who is implicitly or explicitly blamed:
     - External conditions,  
     - Another branch,  
     - Specific facility,  
     - Unnamed “bad actors”.

5. **Proposed Remedies**
   - Additional resources requested.  
   - Personnel changes or punishments suggested.  
   - Policy changes recommended.

### 4.2 Per-Facility vs Branch-Level Reports

- **Facility-level reports**:
  - Generated by Bosses and Sub-bosses, aggregated by Sub-Chiefs.  
  - Highly detailed, but often sanitized.

- **Branch-level summaries**:
  - Compiled at Staff Chief and Branch Head tiers.  
  - Aggregate across many facilities:
    - Rare events vanish, trends become visible (or appear to).

---

## 5. Credibility Evaluation

### 5.1 Statistical Baselines (Scholars/Clerks)

The **Scholars/Clerks meta-branch** maintains:

- Historical **baselines** for:
  - Failure rates by facility type and sector.  
  - Frequency of each reason code (e.g., equipment malfunction) for similar operations.  
  - Typical productivity and loss profiles.

Their ward offices:

- Regularly receive **numeric summaries** and standardized reports.  
- Compare current patterns against:
  - Long-term ward averages,  
  - Inter-ward averages (if available),  
  - Expected ranges given known constraints (e.g., age of infrastructure).

### 5.2 Anomaly Detection

A report or series of reports may be flagged as suspicious if:

- A specific **reason code** is used significantly more often than peers:
  - e.g., one workshop reports 5× more “equipment malfunction” than similar workshops.  
- A facility’s performance swings are out of line with:
  - Local conditions,  
  - Nearby facilities,  
  - Historical patterns.

Suspicion metrics:

- **Local anomaly score**:
  - Deviations within a ward or sector.  
- **Global anomaly score**:
  - Deviations compared to similar wards or facilities elsewhere.

These scores are provided to:

- Branch Heads (as advisory notes).  
- Espionage and Investigations (as lead generators).

### 5.3 Cross-Source Consistency

Espionage and Scholars/Clerks jointly assess:

- **Consistency across sources**:
  - Do informants and moles’ stories align with official reports?  
  - Are independent metrics (e.g., water drawn, cargo moved) consistent with claimed outputs?

- **Temporal consistency**:
  - Do reported reasons repeat mechanically?
    - e.g., same excuse every cycle.  
  - Do reported fixes actually lead to improvement?
    - If not, suspicion increases.

### 5.4 Credibility Score

Each significant report (or facility over a time window) can be assigned a **credibility score**, e.g.:

- `0.0` = utterly untrusted (likely falsified).  
- `0.5` = ambiguous; requires corroboration.  
- `1.0` = highly trusted, has passed multiple checks.

Factors:

- Statistical anomaly measures.  
- Cross-source alignment (official vs espionage vs telemetry).  
- Source’s historical honesty (past lies/truths).  
- Source’s current incentives and risk profile.

---

## 6. Role of Scholars/Clerks in the Flow

### 6.1 Ward-Level Offices

Within each ward:

- Scholars/Clerks maintain a small **clerical office** that:
  - Receives standardized numeric and categorical data from all branches.  
  - Maintains **ward ledgers** that may not be fully visible to the lord.  
  - Periodically submits **upward reports** to higher authorities (Dukes, king).

### 6.2 Dual Accountability

Clerks are:

- **Locally embedded** (they physically reside in the ward), but  
- **Structurally loyal upward** (career advancement depends on higher-level approval).

Consequences:

- They may quietly flag:
  - Overuse of certain excuses,  
  - Underreported unrest,  
  - Consistent underperformance hidden by creative reporting.

This gives higher powers a **second opinion** on ward health and branch honesty, outside the lord’s narrative.

---

## 7. Anecdotes, Rumors & Espionage Overlays

### 7.1 Anecdotal Channels

Information also flows through **unstructured channels**:

- Rumors in queues, bunkhouses, and markets.  
- Gossip among workers, soldiers, and clerks.  
- Quiet confessions to medics or priests (if present).

Espionage and branch heads tap these by:

- Maintaining **informants** in:
  - Queues and soup kitchens,  
  - Workshops and guild halls,  
  - Barracks and patrol units.

### 7.2 Espionage as Overlay

The Espionage Branch:

- Collects anecdotes and **packages them into reports** for paying clients:
  - Ward lord, branch heads, external patrons.

- Uses:
  - Moles to penetrate organizations,  
  - Spies for high-value targets,  
  - Investigators to act on credible suspicions.

This creates a **parallel flow** of information that:

- Sometimes **confirms** official records.  
- Sometimes **contradicts** them, forcing difficult choices:
  - Believe the ledger, or the whispers?

---

## 8. Effects of Credibility in Simulation

### 8.1 Branch Decision-Making

Credibility scores affect:

- **Resource allocation**:
  - Highly credible reports of failure → more aid or stricter oversight.  
  - Low-credibility reports → aid withheld, suspicion increases.

- **Punishment and Promotion**:
  - Managers who file consistently honest but painful reports:
    - May be rewarded (if branch values truth) or quietly sidelined (if it values face).  
  - Those whose reports are later exposed as lies:
    - Risk demotion, removal, or de-legitimization of their facility.

- **Investigation Triggers**:
  - Low credibility + high stakes → Espionage or Investigators deployed.

### 8.2 Miscalibration & Drift

If:

- Scholars/Clerks are weak or corrupted, or  
- Espionage is captured by one faction,

Then:

- Credibility assessments drift:
  - Some branches or factions are **systematically shielded**.  
  - Others are **unfairly targeted**.

This can cause:

- Long-term structural decay disguised as stability.  
- Sudden catastrophic revelations when a new clerk or spymaster arrives.

---

## 9. Implementation Notes (Simulation)

1. **Report Objects**
   - Fields:
     - `source_id`, `source_branch`, `tier`,  
     - `target_facility_or_sector`,  
     - `metrics` (outputs, quotas, etc.),  
     - `reason_codes[]`,  
     - `narrative`,  
     - `medium` (verbal/written/encoded),  
     - `timestamp`,  
     - `truthfulness_prob` (hidden),  
     - `credibility_score` (visible to decision logic).

2. **Source Models**
   - Each agent or facility keeps:
     - `honesty_history` (true vs discovered lies),  
     - `loyalty_profile`,  
     - `risk_perception` parameters.

3. **Credibility Pipeline**
   - Step 1: Generate “true” underlying state.  
   - Step 2: Agent composes report using truthfulness model.  
   - Step 3: Scholars/Clerks + Espionage apply:
     - Baseline comparisons,  
     - Cross-source checks,  
     - Historical honesty.  
   - Step 4: Update `credibility_score`.  
   - Step 5: Branch decision logic consumes `credibility_score`.

4. **Hooks to Other Docs**
   - D-INFO-0002 (Espionage_Branch):
     - Defines sources beyond official channels.  
   - D-WORLD-0003 (Ward_Branch_Hierarchies):
     - Defines who reports to whom and visibility by tier.  
   - Telemetry & Audit docs:
     - Define how hard “ground truth” metrics are to falsify or hide.

