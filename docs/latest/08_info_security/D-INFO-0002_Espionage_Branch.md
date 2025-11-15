---
title: Espionage_Branch
doc_id: D-INFO-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-15
depends_on:
  - D-WORLD-0003   # Ward_Branch_Hierarchies
  - D-INFO-0001    # Telemetry_and_Audit_Infrastructure (placeholder)
---

# Espionage Branch

## 1. Purpose & Scope

This document defines the **Espionage Branch** as a distinct ward-level power pillar, alongside:

1. Civic Branch  
2. Industrial Branch  
3. Military Branch  
4. **Espionage Branch**  
5. Scholars/Clerks (meta-branch, primarily in the king’s service; see separate doc)

The Espionage Branch:

- Operates **decentralized, cell-based networks** of informants, moles, spies, and investigators.  
- Gathers, filters, and trades **information** about individuals, factions, facilities, and events.  
- Serves both the **ward lord** and other branches, as long as it remains **useful and controllable**.  
- Competes and cooperates with **private informant networks** maintained by branch heads and independent actors.

This is a **simulation-facing design** document that should be used to:

- Assign espionage-related roles and behaviors to agents.  
- Model information gathering, distortion, and trade.  
- Integrate espionage with **legitimacy mechanics** and **branch hierarchies** defined in D-WORLD-0003.

---

## 2. Position in the Ward Power Structure

### 2.1 Fourth Branch, Shadow Orientation

The Espionage Branch is a **formally legitimized fourth branch** in the ward’s structure:

- It has a **Tier 1 head** who negotiates with the ward lord.  
- It appears on the same **hierarchy chart** as Civic, Industrial, and Military branches.  
- It can own **legitimized facilities** (safehouses, interrogation chambers, archives).

However, its **operational reality** is different:

- Most of its power flows through **decentralized cells**, not rigid command lines.  
- Loyalty is usually to **immediate handlers and local cells**, not to abstract branches.  
- Many cells and operatives exist in **grey zones of legitimacy**:
  - Officially recognized or tolerated,
  - Deniable when politically convenient,
  - Often entangled with black-market and shadow coalitions.

### 2.2 Relationship to Scholars/Clerks

The **Scholars/Clerks** meta-branch (king-facing) provides:

- Historical baselines, statistical anomalies, and reference ledgers.  
- Comparative data to evaluate whether excuses and reports are plausible.

Espionage uses this as a **hunting ground**:

- Clerkly anomaly flags → espionage investigations and targeted operations.  
- Espionage findings → calibrate future credibility models and suspicion weights.

---

## 3. Internal Structure & Tiers

The Espionage Branch reuses the **five-tier structure** of D-WORLD-0003, but with cell-based semantics.

### 3.1 Tier Overview

**Tier 0 – Ward Lord**  
- Grants the Espionage Branch its **mandate** and **budget**.  
- Decides which factions are “safe” to surveil and which are politically sensitive.  
- May maintain **separate, personal informants** outside the branch.

**Tier 1 – Spymaster of the Ward**  
- Legitimized head of the Espionage Branch.  
- Negotiates directly with the lord:  
  - Scope of operations,  
  - Priority targets,  
  - Legal cover for investigations and raids.  
- Balances loyalty between:
  - The ward lord,  
  - Higher-level powers (Dukes, king),  
  - The branch’s own survival and secrecy.

**Tier 2 – Domain Chiefs**

Examples:

- Chief of **Internal Surveillance** (civic & industrial).  
- Chief of **Military Observation & Counter-Intelligence**.  
- Chief of **External / Inter-Ward Espionage**.  
- Chief of **Investigations & Enforcement**.

Responsibilities:

- Translate broad mandates into **campaigns and target lists**.  
- Supervise groups of **case officers** and **investigative teams**.  
- Decide how much risk to accept in each operation.

**Tier 3 – Case Officers / Cell Controllers**

- Each controls **multiple handlers and cells** in a specific sector:
  - Particular guilds or unions,  
  - Civic facilities (bunkhouses, kitchens, courts),  
  - Military units,  
  - Black-market networks.
- They:
  - Recruit and manage informants and moles,  
  - Package their reports into coherent narratives,  
  - Decide which intel to escalate, suppress, or sell privately.

**Tier 4 – Handlers & Team Leads**

- **Handlers / Brokers**:
  - Directly maintain relationships with informants, moles, and some spies.  
  - Evaluate source reliability and negotiate payment or favors.  
  - Often operate out of “fronts” (taverns, pawn shops, clinics, workshops).

- **Investigative Team Leads**:
  - Command small squads of **overt investigators** and militia support during raids.  
  - Execute warrants, seize records, and detain targets.

**Tier 5 – Operatives**

- **Informants, Moles, Spies, Investigators’ foot teams**.  
- Many are:
  - Part-time, opportunistic, unaware of the larger branch structure.  
  - Loyal to their handler or immediate supervisor, not to the branch head.  
- Some are career professionals specialized in espionage.

---

## 4. Operative Archetypes

The Espionage Branch employs multiple **styles of operative**. These archetypes may be used as agent subtypes, traits, or roles.

### 4.1 Informants

**Definition:**  
People who **report valuable or sensitive information in exchange for payment or favors**.

**Characteristics:**

- Often **opportunistic**, not full-time professionals.  
- Usually embedded in other branches or neutral positions:
  - Civic stewards, shopkeepers, dock workers, factory hands, low-rank militia.  
- Provide:
  - Rumors, observations, overheard conversations, minor secrets.

**Loyalty & Risk:**

- Loyalty is transactional: **coin, protection, or small privileges**.  
- Being known as an informant severely harms **trust and reputation** with those who know.  
- Low-level danger individually, but high cumulative risk if many informants are rolled up at once.

**Simulation Hooks:**

- `role = informant` can be layered on top of any base profession.  
- Reputation penalty if identity is exposed within a faction.  
- Lower reliability, higher volume of reports.

---

### 4.2 Moles

**Definition:**  
Recruited agents placed (or already present) inside a **specific target organization**, given cover identities or roles.

**Characteristics:**

- Tasked to infiltrate and report on:
  - Specific guilds, civic offices, military units, or black-market rings.  
- They provide **regular or semi-regular reports**, depending on:
  - Operational tempo,  
  - Risk of being seen contacting handlers.

**Loyalty & Risk:**

- Primary loyalty: handler and espionage cell.  
- Secondary loyalty: cover organization (to protect cover and personal survival).  
- Danger spikes if:
  - Their identity is suspected,  
  - They refuse to become double agents when pressured.

**Information Quality:**

- More focused than informants, but limited to their **position and access**.  
- Ambitious moles may overreach to gather extra intel, increasing risk of exposure.

**Simulation Hooks:**

- `role = mole` with:
  - target_org,  
  - handler_id,  
  - cover_rank.  
- High-risk events if cover is compromised:
  - Execution, torture, forced double-agency.

---

### 4.3 Spies

**Definition:**  
Career professionals conducting **high-value, targeted operations**.

**Characteristics:**

- Capable of:
  - False identities, deep cover.  
  - Long-range surveillance (visual, auditory, electronic).  
  - Covert entry: lock-cracking, bypassing security systems, sabotaging devices.
- Assigned to:
  - Secure archives, war rooms, high-ranking residences, fortified vaults.

**Loyalty & Risk:**

- Often ideologically committed or heavily invested in the branch.  
- May also **freelance**, selling information to:
  - Rival branches,  
  - External powers,  
  - Black-market brokers (for high payouts or leverage).

- Extremely high personal risk:
  - Targets for retribution, torture, and long-term imprisonment if caught.

**Simulation Hooks:**

- `role = spy` with:
  - infiltration_skill, stealth_skill, lockpicking_skill, etc.  
- Low-frequency, high-impact intel events.  
- Temptation mechanics:
  - `p_sell_to_highest_bidder` increasing with greed and decreased loyalty.

---

### 4.4 Investigators

**Definition:**  
Overt, warrant-backed officers specializing in **raids, interrogations, and formal inquiries**.

**Characteristics:**

- Break through locks and security systems **openly**, not stealthily.  
- Experts in:
  - Interviews, cross-examinations, intimidation, psychological pressure.  
- Called in for:
  - Specific cases flagged by anomalies, audits, or political directives.

**Authority:**

- Usually operate with **explicit backing from the lord and militia**:
  - Warrants or orders grant legal cover for raids and seizures.  
- Without such backing:
  - Their authority is questionable; factions may **resist or retaliate**.

**Loyalty & Risk:**

- High visibility:
  - Known faces, known enforcers.  
- Need secure residences or protection:
  - Released prisoners, their allies, or disgraced elites may seek revenge.

**Simulation Hooks:**

- `role = investigator` with:
  - intimidation_skill, interrogation_skill, legal_cover flag.  
- Can trigger overt conflict:
  - Raids, facility shutdowns, mass arrests.

---

### 4.5 Handlers & Brokers

**Definition:**  
Intermediaries who **manage sources** (informants, moles, some spies) and trade in compiled intel.

**Characteristics:**

- Often pose as:
  - Tavern keepers, pawnbrokers, repair shop owners, medics, scribes.  
- Maintain multiple sources, track:
  - Source reliability,  
  - Risk levels,  
  - Payment histories.

**Position in the Web:**

- Sit near the **center of local espionage networks**.  
- Can become major **information brokers**, selling:
  - Packaged intel to the Espionage Branch,  
  - Side intel to branches and shadow factions.

**Simulation Hooks:**

- `role = handler` with:
  - known_sources[], trust_scores[], secrecy_level.  
- If exposed or eliminated, entire subsections of the web collapse.

---

### 4.6 Analysts & Espionage Clerks

**Definition:**  
Specialists who **organize, cross-check, and classify** incoming reports.

**Characteristics:**

- Compare reports against:
  - Historical data and baselines (from Scholars/Clerks),  
  - Known faction behaviors,  
  - Other sources’ statements.

- Produce:
  - Credibility ratings,  
  - Threat assessments,  
  - Priority targets for investigations.

**Simulation Hooks:**

- `role = analyst` with:
  - analysis_skill, access_to_scholar_data flag.  
- Their work sets `report_credibility` values used in decision-making.

---

## 5. Cell Structure & Loyalty Web

### 5.1 Cells vs Formal Hierarchy

Below Tier 2, the branch is less a tree and more a **web of semi-autonomous cells**:

- Each cell:
  - Contains a handler, a few operatives, and perhaps a case officer link.  
  - Operates from one or more fronts.  
  - Knows only **one or two links upward**.

- Cells are:
  - Locally loyal and self-protective.  
  - Designed to **limit damage** when one cell is compromised.

### 5.2 Loyalty Dynamics

Loyalty gradients:

- **Upward loyalty**:
  - To immediate handler or case officer, not to spymaster or lord.  
- **Sideways loyalty**:
  - To fellow cell members, especially those who share danger and profits.  
- **Conflicting loyalties**:
  - To original branch or faction (e.g., a mole still cares about some coworkers).  
  - To external patrons (black-market bosses, distant Dukes, etc.).

---

## 6. Legitimacy & Mandate

The Espionage Branch and its leader use the same **legitimacy state machine** defined in D-WORLD-0003:

- `outlawed` → `tolerated` → `recognized` → `favored` → `indispensable`

### 6.1 Spymaster’s Legitimacy

The Spymaster’s legitimacy is tied to:

- The **value** of information delivered to the lord and branches.  
- The **perceived control** the lord has over the branch:
  - Scandals and rogue operations reduce perceived control.  
- The branch’s ability to avoid:
  - Major leaks, rogue freelancers, unauthorized coups.

If the branch is seen as:

- **Useful and controllable** → `favored` or `indispensable`.  
- **Dangerous and disloyal** → risk of:
  - Downward legitimacy shifts,  
  - Budget cuts,  
  - Attempts to replace the Spymaster or un-legitimize the branch head.

### 6.2 Freelancing & Shadow Integration

When:

- The branch is underfunded, or  
- The Spymaster is weak or distrusted,

Cells and brokers increasingly **freelance**:

- Selling intel to:
  - Black-market networks,  
  - Rival branches,  
  - External powers.  

This increases:

- Short-term income and survival chances,  
- Long-term risk of purges if discovered.

---

## 7. Relationships with Other Branches

### 7.1 Official vs Private Intelligence

Branch heads and lords obtain information via two channels:

1. **Official Espionage Branch**:
   - Contracts with the Spymaster:
     - “Tell me everything about my rivals.”  
   - Pros:
     - Professional, wider reach.  
   - Cons:
     - Records exist; loyalties may flow upward (to the king) more than sideways.

2. **Private Informant Networks**:
   - Branch heads maintain their own informants, separate from the Espionage Branch.  
   - Pros:
     - More deniable, directly controlled.  
   - Cons:
     - Narrower scope, prone to personal bias, lower quality.

Balance between these channels reflects **trust** in the Spymaster and perceived **alignment** of their interests.

### 7.2 Counter-Intelligence

The Espionage Branch also:

- Tracks and counters:
  - Foreign spies and moles,  
  - Internal leak sources,  
  - Rogue cells and freelancers.

This brings it into conflict or alliance with:

- Military (for security enforcement),  
- Civic branch (for surveillance within public spaces),  
- Industrial branch (to protect or exploit technical secrets).

---

## 8. Reporting Media & Truthfulness (Summary Hooks)

(Full model in D-INFO-0003_Information_Flows_and_Report_Credibility)

Key patterns relevant to Espionage:

- **Street-level / high-risk reports** → mostly verbal, transient, often unrecorded.  
- **Mid-tier reports** → verbal discussion first, then “cleaned” written summaries.  
- **High-tier reports** → written, archived, sometimes ciphered.

Truthfulness depends on:

- Agent **loyalty** to handler/branch.  
- **Perceived risk** of being caught lying (audit pressure, investigator presence).  
- **Perceived payoff** for falsifying or spinning the report.

---

## 9. Implementation Notes (Simulation)

For Codex and runtime systems:

1. **Agent Attributes**  
   - `branch` can be `espionage` or another branch with espionage overlay roles:  
     - `role` ∈ {informant, mole, spy, investigator, handler, analyst}.  
     - `tier` as per D-WORLD-0003.  
   - `legitimacy` and `loyalty` scores to:
     - Espionage Branch,  
     - Cover organization (for moles),  
     - External patrons (if any).

2. **Cell Modeling**  
   - Cells as small graphs:
     - handler ↔ multiple sources,  
     - handler ↔ case_officer.  
   - Limited visibility: sources know handler, not higher tiers.

3. **Intel Events**  
   - Periodic or triggered “report” events with:
     - content_type (gossip, operational detail, secret),  
     - medium (verbal, written, encoded),  
     - `truthfulness` probability derived from loyalty/risk/payoff.

4. **Branch Interactions**  
   - Official contracts:
     - Branch heads → Spymaster.  
   - Private networks:
     - Branch heads ↔ personal informants, bypassing Espionage.

5. **Legitimacy Dynamics**  
   - Success/Failure in espionage operations adjusts:
     - Spymaster’s legitimacy,  
     - Risk of branch-level purges or realignments.

6. **Hooks to Scholars/Clerks**  
   - Analysts request baselines & anomaly data.  
   - Confirmed fraud or corruption feeds back into:
     - Future suspicion weights,  
     - Target selection for investigations.
