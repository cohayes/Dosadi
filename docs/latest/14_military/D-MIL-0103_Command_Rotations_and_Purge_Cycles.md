---
title: Command_Rotations_and_Purge_Cycles
doc_id: D-MIL-0103
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-WORLD-0003          # Ward_Evolution_and_Specialization_Dynamics
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-IND-0101            # Guild_Templates_and_Regional_Leagues
  - D-IND-0102            # Named_Guilds_and_Internal_Factions
  - D-IND-0103            # Guild_Charters_and_Obligations
  - D-IND-0105            # Guild-Militia_Bargains_and_Side_Contracts
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-MIL-0102            # Officer_Doctrines_and_Patronage_Networks
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 14_military · Command Rotations and Purge Cycles (D-MIL-0103)

## 1. Purpose

This document defines how **militia command changes over time** on Dosadi via:

- **Command rotations** – periodic or ad hoc reassignment of officers and
  garrison leadership across wards.
- **Purge cycles** – targeted removal, prosecution, or disappearance of
  officers and their networks.

It links these processes to:

- Officer doctrines and patronage networks (D-MIL-0102),
- Guild influence and bargains (D-IND-0003, D-IND-0105),
- Ward evolution and specialization (D-WORLD-0003),
- Legal and emergency regimes (D-LAW-0001/0002/0003),
- Information and rumor flows (D-INFO-*).

The goal is to provide a **time dimension** to MIL behavior so wards can:

- Drift from one doctrine-dominated regime to another,
- Experience shocks when purges sever entrenched networks,
- Exhibit long memory of “good” or “butcher” commanders.

---

## 2. Conceptual Overview

We model MIL leadership as:

- A set of **command nodes**:
  - ward-level garrison commanders,
  - key exo-bay chiefs,
  - corridor/patrol commands for Lift Ring and Industrial Spine segments.

Over time:

- **Rotations** move doctrines and patronage ties between wards.
- **Purges** remove nodes and sometimes entire doctrinal blocs.
- **Promotions/demotions** propagate certain practices upward or bury them.

Command churn is both:

- A **tool of control** by duke_house and central command, and
- A **source of instability**, especially when it disrupts informal bargains
  that previously kept things “quiet enough.”

---

## 3. Command Node Template

We describe a command node with:

```yaml
CommandNode:
  id: string
  type: "garrison" | "exo_bay" | "corridor_command"
  ward_home: string
  doctrine_id: string              # from D-MIL-0102, e.g. MIL_DOC_PATRONAGE
  patronage_alignment:
    with_duke_house: float
    with_guilds: float
    with_bishops: float
    with_cartels: float
  tenure_ticks: int
  max_tenure_ticks: int            # soft or hard limit before rotation
  reputation_tags:
    - "butcher"
    - "fair"
    - "bought"
  associated_bargains:
    - bargain_id                    # from D-IND-0105
```

The **fleet** of CommandNode objects across wards is what rotations and purges
act upon.

---

## 4. Command Rotations

### 4.1 Motivations for rotation

Regime actors (duke_house, central_mil_command, central_audit_guild) rotate
officers to:

- Prevent **overly strong local loyalties**:
  - officers becoming “little dukes” or cartel captains.
- Spread **successful doctrine**:
  - moving “effective” commanders into troubled wards.
- Reward or punish:
  - sending officers to prestigious cores or miserable shadows.

Rotations can be:

- **Scheduled** (every N campaign phases),
- **Performance-based** (after incidents, strikes, or unrest),
- **Political** (following palace intrigue, coup attempts, etc.).

### 4.2 Rotation patterns

Common patterns:

- **Ring rotation**:
  - outer → hinge → core → outer,
  - or the reverse, depending on career arc.
- **Problem solver deployment**:
  - moving Hardline or Zealot officers into wards with rising unrest,
  - moving Patronage officers into economically crucial but fragile wards.
- **Quarantine rotation**:
  - moving “contaminated” officers from cartel-heavy wards into low-impact
    posts, or vice versa as a deliberate punishment.

### 4.3 Mechanical hooks

Rotation effects:

- **Doctrine mix** per ward changes:
  - `dominant_doctrine(w)` may shift,
  - existing guild–MIL bargains may be:
    - renewed,
    - renegotiated,
    - or broken.

- **Patronage network** rewire:
  - edges between officers and local guild factions weaken or break,
  - new edges form with guilds in destination wards.

- **Sentiment and rumor**:
  - new commanders generate:
    - rumor seeds (“they say the new one was a butcher in Ward 09”),
    - uncertainty spikes (`rumor_fear_index(w)` up temporarily).

Implementation:

- At rotation events, update:
  - `CommandNode.ward_home`,
  - patreon alignments (some carry over, some must be rebuilt),
  - associated bargains (many become unstable or dissolve).

---

## 5. Purge Cycles

### 5.1 What is a purge?

A **purge cycle** is an intentionally disruptive campaign to:

- Remove officers deemed:
  - disloyal,
  - corrupt (by currently disfavored standards),
  - too independent or powerful,
- And often to **signal a doctrinal or political shift**.

Purges may target:

- Specific doctrine types (e.g. Patronage officers blamed for cartels),
- Specific patronage alignments (officers tied to a rival ducal faction),
- Particular wards or leagues (Industrial Spine, Shadow wards).

### 5.2 Purge triggers

Typical triggers:

- Major scandals revealed by audits or Quiet Ledger leaks.
- Military failures (rebellion, failed crackdowns, lost corridors).
- Political transitions (succession, coup attempt, ducal realignment).
- Ideological campaigns led by Zealot-aligned cadres.

### 5.3 Purge mechanics

At a high level, a purge:

- Selects a **target set of CommandNodes** based on:
  - doctrine_id,
  - patronage alignment,
  - incident history.

- Applies one of:
  - **Removal** (discharge, exile, reassignment to meaningless posts),
  - **Tribunal** (public trials, executions, or work-camp sentences),
  - **Disappearance** (extrajudicial removal).

- Injects replacement CommandNodes, often with a different doctrinal profile.

Ward-level effects:

- Short-term chaos:
  - bargains collapse,
  - enforcement patterns change unpredictably,
  - rumor and fear spike.

- Medium-term realignment:
  - new bargains form with surviving or new guild factions,
  - ward may shift toward different attractors in D-WORLD-0003.

---

## 6. Rotation & Purge Archetypes

### 6.1 “Salt the Roots” Campaign

- Target:
  - Patronage Pragmatists in Shadow wards with high cartel alignment.
- Method:
  - Audit-backed investigations,
  - Security Tribunals for the most egregious,
  - forced retirement or reassignment for others.

- Replacement:
  - Zealot Purists and Hardline commanders from core garrisons.

- Expected outcomes:
  - Short-term spike in brutality and tribunal frequency,
  - Cartels temporarily disoriented but shift to surviving officers,
  - Some wards tip from shadow-patronage equilibria into **open conflict**.

### 6.2 “Cool the Spine” Rotation Plan

- Target:
  - Hardline commanders in Industrial Spine wards that show:
    - high unrest,
    - repeated strikes/sabotage,
    - declining throughput.

- Method:
  - Planned rotations moving:
    - Professionals and Patronage officers into those wards,
    - Hardlines into more obedient wards or border posts.

- Replacement:
  - Officers known for structured bargains and limited force.

- Expected outcomes:
  - Reduced visible violence in Spine wards,
  - Increased bargaining between MIL and guilds (Yardhook, Brine Chain),
  - Throughput recovers at the cost of increased corruption.

### 6.3 “Clean the Ledger” Purge

- Target:
  - Officers deeply intertwined with Quiet Ledger Redactors and cartels.

- Method:
  - Coordinated raids on info hubs and garrisons,
  - Publicized tribunals alleging “ledger treason.”

- Replacement:
  - Professional Orderists more tightly bound to central_audit_guild.

- Expected outcomes:
  - Significant disruption to INFO channels,
  - Shortage of competent clerks and scribes,
  - Shift in rumor motifs toward “no one trusts the numbers.”

---

## 7. Interaction with Wards, Guilds, and Law

### 7.1 Ward evolution

Rotations and purges alter:

- `garrison_presence(w)` not just in quantity but **quality**,
- `sanction_intensity(w)` and `legal_opacity(w)`,
- stability of `GuildMilitiaBargain` objects.

Under repeated Hardline purges:

- Wards may:
  - lose entrenched corrupt networks,
  - but also lose stabilizing informal arrangements,
  - drift toward more volatile Shadow or revolt-prone configurations.

Under gradual Professional rotations:

- Wards may:
  - settle into predictable patterns,
  - show slower but steadier industrial specialization.

### 7.2 Guild and cartel responses

Guilds:

- Attempt to **anticipate rotations**:
  - cultivate relationships with multiple doctrinal types,
  - keep “insurance factions” (e.g. Purists in Golden Mask, Balancers in
    Stillwater) ready to pivot.

- React to purges by:
  - sacrificing scapegoats,
  - shifting allegiances,
  - intensifying shadow production to survive disruptions.

Cartels:

- Exploit moments of churn:
  - move product through confused checkpoints,
  - recruit dislocated officers and guild workers.

### 7.3 Law and tribunals

Purges feed directly into D-LAW-0002/0003:

- Increase in high-profile **Security Tribunal** cases.
- Use of **curfews and emergency decrees** to:
  - secure areas during command changes,
  - restrict assembly while purges are underway.

Rumor:

- Narratives of:
  - “old commander protected us, new one bleeds us,”
  - “purge was righteous justice” vs “purge was power grab.”

---

## 8. Implementation Sketch (Non-Normative)

1. **Initialize command nodes**:
   - Assign each garrison/command a doctrine and patronage alignment.

2. **Define rotation schedules and triggers**:
   - Global schedule:
     - e.g. evaluate every N campaign phases.
   - Triggers:
     - high unrest, repeated MIL failures, scandal events.

3. **Apply rotations**:
   - Select subset of nodes to move.
   - Reassign `ward_home`, adjust patronage alignment partially:
     - some ties carry, others must be rebuilt.
   - Damp or break existing `GuildMilitiaBargain`s,
     and allow new ones to form.

4. **Apply purge cycles when triggered**:
   - Select target set of nodes by doctrine/alignment criteria.
   - Remove or mark them as degraded.
   - Spawn replacement nodes with scenario-specific doctrinal biases.

5. **Update ward-level indices**:
   - Recalculate:
     - dominant doctrine per ward,
     - sanction and law posture biases,
     - bargain stability,
     - rumor and fear indices.

6. **Log events for narrative/UI**:
   - “Commander of Ward 12 Garrison reassigned to Lift Ring.”
   - “Salt the Roots purge begins; three Shadow ward officers arrested.”
   - “Cool the Spine rotation: Hardline replaced by Patronage commander.”

These events become hooks for player action, AI policies, and scenario
milestones.

---

## 9. Future Extensions

Potential follow-ups:

- `D-MIL-0104_Checkpoint_and_Patrol_Behavior_Profiles`
  - How different doctrines manifest in street-level interactions.

- `D-MIL-0105_Garrison_Morale_and_Fracture_Risk`
  - How repeated rotations and purges affect MIL cohesion and mutiny
    probabilities.

- Scenario-specific officer rosters
  - Named commanders with doctrines, patronage webs, and personal quirks
    for arcs like the Sting Wave scenarios.
