---
title: Sanction_Types_and_Enforcement_Chains
doc_id: D-LAW-0001
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
  - D-HEALTH-0002         # Food_Waste_and_Metabolism
---

# 09_law · Sanction Types and Enforcement Chains (D-LAW-0001)

## 1. Purpose

This document defines **how the regime punishes, coerces, and deters** on
Dosadi. It describes:

- The main **types of sanctions** (from mild economic penalties to disappearances),
- Which **branches and offices** can apply which sanctions,
- How sanctions **escalate** in response to incidents and alert level changes,
- How these actions feed back into:
  - Ward attributes (unrest, loyalty, fear, black market intensity),
  - Garrison posture and deployment (D-MIL-0002),
  - Rumor and information flows (D-INFO-0006),
  - Agent records and life chances.

The aim is to provide a consistent **enforcement backbone** that can be used by
simulation code and scenario design without prescribing a single canonical
legal code or ideology for all runs.

---

## 2. Relationship to Other Pillars

- **World & Runtime**
  - D-WORLD-0002 defines ward attributes like `unrest_index`, `loyalty_to_regime`,
    `shortage_index`, etc. Sanctions push these indices around.
  - D-RUNTIME-0001 defines time slices and phases in which sanctions and
    enforcement actions are scheduled and resolved.

- **Military**
  - D-MIL-0001 defines forces and assets used to enforce sanctions
    (troops, investigators, exo-cadres).
  - D-MIL-0002 defines where those forces live (garrisons, checkpoints,
    holding sites).
  - D-MIL-0003 defines how alert levels change and trigger more severe chains.

- **Economy & Industry**
  - D-ECON-0001 and related docs define water, rations, supply and work.
    Sanctions often take **economic form**: ration cuts, work assignment,
    loss of access to facilities.
  - D-ECON-0004 defines black market networks, which both evade and
    profit from sanctions.
  - D-IND-0003 defines guild power; sanctions can either crush or court
    guilds depending on their leverage.

- **Info-Security**
  - D-INFO-0001 and D-INFO-0003 define how telemetry and formal reports
    give the regime cause (real or manufactured) to sanction.
  - D-INFO-0006 defines rumor networks; enforcement aims to shape
    `rumor_fear_index` and to make examples of certain cases.

- **Agents & Health**
  - D-AGENT-0101 defines occupations and roles that are common sanction
    targets (street vendors, smugglers, clerks, guild techs, etc.).
  - D-HEALTH-0002 defines how food and metabolic needs link to survival;
    ration-based sanctions are therefore existential.

This document is the **bridge** between incident detection and bodily or
economic consequences.

---

## 3. Sanction Type Taxonomy

Sanctions operate along several axes. For clarity we define five broad
categories; scenarios can instantiate concrete codes beneath them.

### 3.1 Economic and Resource Sanctions

These are the **most common** and often the first resort.

Examples:

- **Ration downgrades**
  - Reduced food quality or quantity for individuals, households,
    work crews, or entire wards.
- **Water quota reductions**
  - Lower per capita allocation; higher prices for access to taps,
    wash facilities, or sealed spaces.
- **Work assignment penalties**
  - Reassignment to more dangerous, exhausting, or lower-status work.
- **Fines and confiscations**
  - Seizing stored goods, tools, or personal water credits.

Typical mechanical effects:

- Increase local `shortage_index(w)`,
- Decrease `loyalty_to_regime(w)` if seen as arbitrary,
- Increase `black_market_intensity(w)` as people seek workarounds,
- Shift guild/cartel bargaining positions.

### 3.2 Access and Movement Sanctions

These restrict **where people can go** and **what they can use**.

Examples:

- **Checkpoint flags**
  - Individuals or groups marked for extra searches, delays, or
    denial of passage.
- **Zone exclusion**
  - Bans from certain wards, markets, corridors, or facilities.
- **Loss of permit/identity privileges**
  - Downgrading or revoking work, travel, or residency permits
    (ties into D-AGENT-0107 Identity/Permits when in play).

Mechanical effects:

- Increase travel time and risk on certain paths,
- Concentrate disfavored populations in specific wards,
- Make black market routes more valuable.

### 3.3 Legal and Record Sanctions

These live in **paper and data** but have long-term impact.

Examples:

- **Blacklisting**
  - Marks in employment or guild records that restrict access to good jobs.
- **Disciplinary records**
  - Official notations that increase future sanction severity.
- **Debt and obligation tagging**
  - Assigning long-term “owed labor” or service to the regime or its agents.

Mechanical effects:

- Modify future event probabilities:
  - Higher chance of harsher punishment on next offense,
  - Lower chance of being believed in formal reports,
  - Increased vulnerability to coercion (cartel or regime).

### 3.4 Bodily and Coercive Sanctions

Direct, physical punishments.

Examples:

- **Beatings and rough handling**
  - Street-level punishment by militia or enforcers.
- **Short-term detention**
  - Time in holding sites, often with poor conditions.
- **“Accidents” in work assignments**
  - Being sent to highly dangerous duty as informal punishment.

Mechanical effects:

- Immediate impacts on agents (injury, health penalties),
- Increase `rumor_fear_index(w)` if widely known,
- Can either suppress or inflame `unrest_index(w)` depending on context.

### 3.5 Terminal and Disappearance Sanctions

The darkest end of the spectrum.

Examples:

- **Long-term disappearance**
  - Removal to unknown facilities; often never returned.
- **Public executions or “demonstrative” violence**
  - Rare but high-impact spectacles designed to shift rumor and fear.
- **Collective punishments**
  - Punishing an entire bunkhouse, crew, or ward for actions of a few.

Mechanical effects:

- Strong increase to `rumor_fear_index(w)`,
- Potentially large swings in `unrest_index(w)`:
  - Sharp suppression in short term,
  - Deepened long-term hatred and willingness to rebel or collude
    with regime enemies.

---

## 4. Authority and Jurisdiction

Different branches and roles have **different sanction budgets**.

### 4.1 Branch sanction profiles

Non-normative example matrix:

```yaml
branch_sanction_profile:
  duke_house:
    economic: "high"
    movement: "high"
    legal_record: "high"
    bodily: "medium"
    terminal: "medium"
  bishop_guild:
    economic: "medium"
    movement: "low"
    legal_record: "low"
    bodily: "low"
    terminal: "none"
  militia:
    economic: "low"
    movement: "high"
    legal_record: "medium"
    bodily: "high"
    terminal: "medium"
  central_audit_guild:
    economic: "medium"
    movement: "low"
    legal_record: "high"
    bodily: "low"
    terminal: "low"
  cartel:
    economic: "medium"
    movement: "medium"
    legal_record: "none"
    bodily: "high"
    terminal: "high"
```

Interpretation:

- Duke_house shapes **policy-level** and structural sanctions,
  often applied via others.
- Bishop_guild controls access to food, beds, and clinics, but
  rarely performs extreme punishments directly.
- Militia specializes in **movement control, bodily coercion, and
  on-the-spot enforcement**.
- Central_audit_guild controls **paper and process**, and can set
  people up for harsher treatment by others.
- Cartel sanctions operate outside the law but follow their own logic.

### 4.2 Levels of authority

Sanctions also vary by **scale**:

- **Individual** (named agent),
- **Group** (crew, bunkhouse, guild cell),
- **Ward-level** (entire ward or category of residents),
- **City-wide** (rare emergency measures).

Each branch/office should be tagged in scenarios with:

```yaml
sanction_scope:
  max_scale: "individual" | "group" | "ward" | "city"
  requires_approval_from:
    - "duke_house"
    - "central_audit_guild"
```

This helps prevent “every minor official can do anything” chaos,
unless that is a deliberate setting.

---

## 5. Enforcement Chains and Escalation

Sanctions often follow **chains**: soft measures failing lead to
harsher ones, moderated by alert levels and politics.

### 5.1 Generic escalation ladder

For a given type of offense (e.g. cartel activity, guild strike,
anti-regime agitation), a scenario can define an escalation chain:

```yaml
enforcement_chain_cartel_activity:
  step_0:
    description: "Tolerance / quiet skimming"
    typical_sanctions:
      - "blacklisting for small-time smugglers"
  step_1:
    description: "Targeted interdictions"
    typical_sanctions:
      - "checkpoint flags"
      - "short-term detention"
  step_2:
    description: "Symbolic crackdowns"
    typical_sanctions:
      - "public beatings"
      - "group ration cuts in target wards"
  step_3:
    description: "Structural pressure"
    typical_sanctions:
      - "large-scale water and ration reductions"
      - "guild charter threats"
  step_4:
    description: "Purges and disappearances"
    typical_sanctions:
      - "mass detentions"
      - "select disappearances of perceived leaders"
```

Simulation logic can move **up** or **down** the ladder based on:

- Effectiveness of previous steps,
- Current `alert_level(w)`,
- Political constraints (e.g. duke_house reluctance to damage key guilds).

### 5.2 Link to alert levels (D-MIL-0003)

At higher alert levels:

- **ALERT_0 / ALERT_1**:
  - Emphasis on economic, record-level, and limited bodily sanctions.
- **ALERT_2**:
  - More movement sanctions, checkpoint intensity rises,
  - Increased short-term detention,
  - More aggressive group penalties.
- **ALERT_3+**:
  - Terminal sanctions, disappearances, and large-scale collective
    punishments become more likely, especially in wards tagged as
    rebellious or expendable.

---

## 6. Ward-Level Law and Sanction Attributes

We introduce a small set of **law-related ward indices**.

```yaml
sanction_intensity: float       # 0–1, how frequently sanctions are applied
legal_opacity: float           # 0–1, how unknowable the rules feel
due_process_index: float       # 0–1, perceived chance of fair treatment
impunity_index: float          # 0–1, perceived chance authorities act without consequence
collective_punishment_risk: float  # 0–1, how likely groups suffer for individuals
```

Interpretation:

- **sanction_intensity**  
  - High: constant fines, searches, detentions; a sense of living under siege.

- **legal_opacity**  
  - High: rules feel arbitrary; people cannot predict what is forbidden.

- **due_process_index**  
  - High: people believe they might prove innocence or mitigate punishment.

- **impunity_index**  
  - High: authorities seem above any constraint, increasing fear and hatred.

- **collective_punishment_risk**  
  - High: people hesitate to act because their crew or family will pay.

These indices strongly affect:

- `unrest_index(w)`,
- `loyalty_to_regime(w)`,
- `rumor_fear_index(w)`,
- The attractiveness of guild/cartel protection.

---

## 7. Agent-Level Hooks and Records

Sanctions leave marks on **individual lives**.

### 7.1 Personal sanction record

Agents may carry a **sanction record** object:

```yaml
SanctionRecord:
  strikes: int
  last_sanction_tick: int
  last_sanction_type: string
  blacklist_flags:
    work: bool
    travel: bool
    guild_membership: bool
  owed_labour: float      # abstract quantity of future labour owed
  trauma_index: float     # 0–1, accumulated harm and fear
```

This record influences:

- Job availability and promotion chances,
- Propensity to collaborate with regime vs cartel/guild opponents,
- Psychological drives (risk appetite, fear, hatred).

### 7.2 Drives and loyalty

Sanctions modulate **loyalty as long-term self-interest**:

- Agents heavily sanctioned by the regime:

  - Are more likely to pivot toward guilds, cartels, or rebels,
  - Unless collective punishment makes them fear dragging others down.

- Agents who see **others** punished:

  - May become more cautious and compliant,
  - Or more convinced that revolt is the only rational move, depending
    on social context and rumor narratives.

Implementation should treat sanction exposure as a key driver in
agent decision rules, not just cosmetic flavor.

---

## 8. Implementation Sketch (Non-Normative)

A minimal integration loop might:

1. **Ingest incidents** from MIL/INFO:
   - e.g. strikes, sabotage, raids, riots, cartel killings.

2. Use scenario-defined **enforcement chains** to choose response steps
   based on:
   - incident type,
   - ward `alert_level`,
   - guild/cartel power and alignments,
   - political constraints (duke/bishop preferences).

3. Apply selected sanctions:
   - Update ward indices (`sanction_intensity`, `legal_opacity`, etc.).
   - Update agent `SanctionRecord`s and occupational constraints.

4. Feed effects into:
   - Future incidents (resentment, fear, shortages),
   - Rumor system (D-INFO-0006, using templates about disappearances,
     martyrs, crackdowns),
   - Economic behaviors (increased black market reliance).

5. Occasionally adjust **policy-level parameters**:
   - e.g., regime decides to reduce collective punishments after high-profile
     backlash; or conversely, to increase them in “expendable” wards.

The exact numeric details are left to scenario tuning; this document
defines the conceptual structure and key variables.

---

## 9. Future Extensions

Potential follow-up documents:

- `D-LAW-0002_Procedural_Paths_and_Tribunals`  
  - How cases move (or bypass) through formal hearings, appeals,
    and special commissions.

- `D-LAW-0003_Curfews_Emergency_Decrees_and_Martial_States`  
  - Legal tools for locking down wards or the whole city and how they
    interact with garrisons and supply.

- `D-LAW-0101_Community_Rulesets_and_Factional_Codes`  
  - On top of state law, how guilds, cartels, and communities enforce
    their own codes (and clash with the regime).

These should all treat the sanction taxonomy and ward/agent-level indices
defined here as their shared backbone.
