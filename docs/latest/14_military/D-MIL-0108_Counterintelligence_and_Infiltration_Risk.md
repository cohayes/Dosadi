---
title: Counterintelligence_and_Infiltration_Risk
doc_id: D-MIL-0108
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
  - D-IND-0104            # Guild_Strikes_Slowdowns_and_Sabotage_Plays
  - D-IND-0105            # Guild-Militia_Bargains_and_Side_Contracts
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-MIL-0102            # Officer_Doctrines_and_Patronage_Networks
  - D-MIL-0103            # Command_Rotations_and_Purge_Cycles
  - D-MIL-0104            # Checkpoint_and_Patrol_Behavior_Profiles
  - D-MIL-0105            # Garrison_Morale_and_Fracture_Risk
  - D-MIL-0106            # Field_Justice_and_In-Unit_Discipline
  - D-MIL-0107            # Special_Detachments_and_Commissar_Cadres
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002           # Espionage_Branch
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 14_military · Counterintelligence and Infiltration Risk (D-MIL-0108)

## 1. Purpose

This document describes how **counterintelligence (CI)** operates in and around
Dosadi's militia forces, and how **infiltration risk** is modeled.

It focuses on:

- How guilds, cartels, and factions attempt to **penetrate MIL** structures.
- How MIL, the Espionage Branch (D-INFO-0002), and oversight organs attempt
  to **detect, contain, or exploit** that penetration.
- The impact of CI campaigns on:
  - garrison morale and fracture risk (D-MIL-0105),
  - guild–MIL bargains (D-IND-0105),
  - ward evolution and specialization (D-WORLD-0003),
  - LAW and rumor systems (D-LAW-*, D-INFO-*).

This is primarily a **MIL-facing** view of CI, with INFO pillar documents
defining central espionage architecture and tradecraft.

---

## 2. Relationship to Other Pillars

- **MIL (D-MIL-0102–0107)**  
  - Doctrines, patronage, rotations, checkpoints, morale, discipline, and
    special detachments provide the **substrate** CI acts on.

- **INFO (D-INFO-0001/0002/0003/0006)**  
  - Telemetry and audit infrastructure supply raw signals.
  - Espionage Branch defines central CI authority and methods.
  - Information flows and rumor networks express how suspicion spreads.

- **IND/ECON (D-IND-0101–0105, D-ECON-0004)**  
  - Guilds and cartels are both **targets** and **sources** of infiltration.

- **WORLD (D-WORLD-0002/0003)**  
  - Ward attributes affect:
    - how easy infiltration is,
    - how much CI presence a ward receives.

- **LAW (D-LAW-0001–0003)**  
  - Determines legal pathways for handling suspected infiltrators:
    - internal discipline vs tribunal vs purge.

---

## 3. Conceptual Model: Surfaces, Actors, and Channels

### 3.1 Infiltration surfaces

CI concerns itself with defending (or co-opting) the following surfaces:

- **Command nodes**:
  - garrison commands, corridor commands, exo-bays (D-MIL-0103).

- **Operational nodes**:
  - checkpoints and patrol routes (D-MIL-0104),
  - special detachments and commissar cadres (D-MIL-0107).

- **Information nodes**:
  - local record-keepers and signal operators,
  - Quiet Ledger liaisons (D-INFO-0001/0003).

- **Logistics nodes**:
  - armories, depots, ration stores,
  - MIL-controlled lift and barrel choke points.

### 3.2 Infiltrating actors

Primary infiltrators:

- **Guild factions**:
  - seeking preferential treatment, early warnings, and charter leverage.

- **Cartels and shadow guilds**:
  - seeking safe transit, protection, and access to weapons or records.

- **Ducal or political factions**:
  - seeking footholds for future coups or power struggles.

- **Rebel/insurgent cells**:
  - seeking information, weapons, and symbolic defections.

### 3.3 Infiltration channels

Common channels:

- **Patronage**:
  - bribes, family ties, ward-origin networks, shared vice habits.

- **Recruitment**:
  - MIL recruits drawn from guild-heavy wards or cartel-linked families.

- **Joint operations**:
  - repeated coordination with specific guilds (e.g. SUITS, Lift Crown)
    creates habitual information exchange.

- **Administrative access**:
  - clerks and ledgermen who manage logs, rosters, and passes.

---

## 4. Infiltration Risk Model

We assign each relevant node a **CI state**:

```yaml
CIState:
  node_id: string                    # maps to CommandNode, Checkpoint, etc.
  node_type: "command" | "checkpoint" | "patrol" | "special_detachment" | "info_cell"
  ward_id: string
  base_exposure: float               # structural exposure 0–1
  oversight_strength: float          # CI coverage 0–1
  patronage_entanglement: float      # strength of guild/cartel ties
  doctrine_modifier: float           # from commander doctrine (D-MIL-0102)
  recent_incident_pressure: float    # scandals, purges, major cases
  infiltration_risk: float           # derived 0–1
  suspicion_score: float             # CI perception 0–1
  investigation_level: "none" | "light" | "focused" | "full"
  rumor_tags:
    - "bought"
    - "clean"
    - "watched"
```

### 4.1 Base exposure

Functions of:

- Ward type (shadow wards → higher exposure),
- Node type (checkpoints on key corridors → high),
- Economic flows (nodes on black market corridors → high).

### 4.2 Oversight strength

Derived from:

- Presence of special detachments and commissar cadres (D-MIL-0107),
- Espionage Branch assets (D-INFO-0002),
- Telemetry coverage quality (D-INFO-0001).

### 4.3 Patronage entanglement

Inherited from:

- Patronage graphs (D-MIL-0102),
- Guild–MIL bargains (D-IND-0105),
- Observed patterns of side payments and favors.

High entanglement raises infiltration risk, but may reduce **suspicion** if the
network is normalized and protected.

---

## 5. Counterintelligence Posture Levels

We define a simple **CI posture** per ward or MIL region:

```yaml
CIPosture:
  ward_id: string
  level: 0 | 1 | 2 | 3       # 0 = lax, 3 = paranoid
  driver: "routine" | "scandal" | "purge_campaign" | "rebel_fear"
  active_assets:
    special_detachments: int
    commissar_cadres: int
    espionage_branch_cells: int
```

- **Level 0 – Lax**
  - Minimal CI presence; patronage and bargains dominate.
- **Level 1 – Attentive**
  - Routine checks on sensitive nodes.
- **Level 2 – Tightened**
  - Focused investigations; increased audits and arrests.
- **Level 3 – Paranoid**
  - Widespread loyalty sweeps, witch-hunts, and high purge risk.

CI posture modulates:

- how quickly suspicion rises,
- how strongly suspected nodes are constrained or purged,
- how much friction guilds and cartels experience.

---

## 6. CI Actions and Tools

### 6.1 Screening and vetting

- **Initial vetting**:
  - background checks on recruits,
  - ward-origin and kinship analysis,
  - guild/cartel proximity analysis.

- **Ongoing vetting**:
  - tracking unusual lifestyle changes (D-ECON-0004),
  - comparing pay vs visible consumption.

Effects:

- Lowers base infiltration risk at some cost to recruitment pools.
- May generate resentment if applied unevenly (doctrinal bias, ward prejudice).

### 6.2 Monitoring and surveillance

- **Telemetry-based**:
  - monitoring checkpoint patterns, raid targets, seizure types,
  - flagging nodes whose data diverges from expected distributions.

- **Human intelligence**:
  - informants inside MIL, guilds, and cartels,
  - confidential debriefs and confession sessions via commissars.

Effects:

- Raises `suspicion_score` for anomalous nodes.
- Can fuel paranoia and rumor if widely known.

### 6.3 Integrity checks and stings

- **Controlled operations**:
  - sending decoy loads through checkpoints,
  - testing responses to bribe offers,
  - staging fake guild/cartel approaches.

- **Data cross-checks**:
  - comparing Quiet Ledger records with observed flows.

Outcomes:

- Confirmed compromise:
  - nodes marked for purge, reassignment, or co-option.
- False positives:
  - embittered officers and units, higher fracture risk.

### 6.4 Co-option and double agents

CI does not always “clean” infiltrated nodes; it may **capture them**:

- Known compromised officers used as:
  - double agents against guilds/cartels,
  - channels to feed disinformation.

Risks:

- High complexity:
  - if control is lost, CI ends up reinforcing enemy networks.

---

## 7. Infiltration and Detection Dynamics

### 7.1 Infiltration attempts

We model attempts as events:

```yaml
InfiltrationAttempt:
  id: string
  actor_type: "guild_faction" | "cartel" | "ducal_faction" | "rebel_cell"
  target_node_id: string
  method: "patronage" | "bribe" | "blackmail" | "ideological_appeal" | "family_bond"
  difficulty: float
  outcome: "success" | "partial" | "failure"
```

Success probability depends on:

- `CIState.infiltration_risk`,
- GarrisonState morale and alignments (D-MIL-0105),
- presence of CI assets (Espionage Branch, special detachments).

### 7.2 Detection and response

Upon success, node becomes either:

- **Compromised**:
  - alignment shifts toward infiltrating actor,
  - behavior changes in subtle ways (e.g., target bias at checkpoints),
  - suspicion may remain low if oversight weak.

- **Compromised but flagged**:
  - CI notices anomalies,
  - node continues operating under watch,
  - candidate for stings and double-agent use.

Responses:

- Internal discipline (D-MIL-0106),
- Referral to tribunals (LAW),
- Targeted purges (D-MIL-0103),
- Controlled exploitation as double agents.

---

## 8. Effects on MIL, Guilds, and Ward Evolution

### 8.1 On MIL behavior

Infiltrated nodes:

- Distort:
  - enforcement patterns,
  - target selection for raids,
  - information flows to command.

- Undermine:
  - doctrine implementation (e.g., Professional turned into Patronage proxy),
  - trust in special detachments and commissars.

High infiltration plus high CI posture → **hyper-politicized MIL**.

### 8.2 On guild and cartel strategies

Guilds:

- Prefer **stable, low-CI wards** for deep infiltration.
- Use infiltrated MIL nodes to:
  - shield key facilities,
  - steer sanctions toward rivals,
  - obtain advance warnings of raids and purge lists.

Cartels:

- Seek to dominate certain checkpoints or special detachments in Shadow or
  Spine wards.
- Exploit rotations:
  - re-test new commanders for vulnerability.

### 8.3 On ward evolution

- Wards with heavily infiltrated MIL and weak CI:
  - drift toward **Shadow** attractors,
  - formal law decays, guild/cartel “law” replaces it.

- Wards with heavy CI and frequent purges:
  - may stabilize into brittle **Bastion** states,
  - or crack into open conflict if MIL fractures.

---

## 9. Interaction with Rumor and Information Systems

From D-INFO-0006:

- CI campaigns are rumor-rich:
  - “The garrison commander is bought by Lift Crown,”
  - “The special detachment answers to the cartels,”
  - “Espionage Branch turned half the ward into informants.”

Rumor effects:

- Raise `suspicion_score` even without evidence.
- May cause CI to waste resources chasing shadows.
- Can be **weaponized** by guilds and ducal factions to:
  - trigger purges against rivals,
  - clear space for their own infiltrations.

From D-INFO-0003:

- Conflicting reports from different INFO channels:
  - MIL logs vs Quiet Ledger vs Espionage Branch summaries,
  - discrepancies are themselves CI signals.

---

## 10. Implementation Sketch (Non-Normative)

1. **Initialize CIState for key nodes**:
   - CommandNodes,
   - checkpoints/patrols,
   - special detachments,
   - key info/logistics cells.

2. **Set CIPosture per ward/region**:
   - Based on:
     - regime priorities,
     - recent scandals/insurgency,
     - world/ward attributes.

3. **Per macro-step**:
   - Update CIState inputs:
     - patronage entanglement (IND/MIL interactions),
     - oversight presence (special detachments, Espionage cells),
     - incident and rumor-driven suspicion.

   - Sample **InfiltrationAttempt** events from guild/cartel/rebel strategies.

   - Resolve outcomes:
     - update compromised status,
     - adjust MIL behavior as nodes shift alignment.

   - Run CI actions:
     - surveillance,
     - integrity checks,
     - stings,
     - purges or double-agent decisions.

4. **Update downstream systems**:
   - GarrisonState morale and fracture risk,
   - LAW case creation and tribunal loads,
   - WORLD ward evolution indices,
   - rumor templates and INFO dashboards.

5. **Expose to UI / scenario layer**:
   - For each ward:
     - CI posture,
     - suspected infiltrated nodes,
     - recent CI operations (“sting at Rat Gate,” “quiet purge in Lift Ring”).

---

## 11. Future Extensions

Potential follow-ups:

- `D-INFO-0009_Counterintelligence_Tradecraft_and_Signatures`
  - INFO-side detail on detection techniques, signal signatures, and
    tradecraft beyond MIL context.

- Scenario-specific CI maps
  - Predefined infiltration and CI overlays for arcs like
    “Pre-Sting Wave Espionage Season” or “Post-Purge Recovery Campaign.”
