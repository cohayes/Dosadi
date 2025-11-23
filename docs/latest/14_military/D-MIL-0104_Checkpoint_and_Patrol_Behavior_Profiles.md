---
title: Checkpoint_and_Patrol_Behavior_Profiles
doc_id: D-MIL-0104
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
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 14_military · Checkpoint and Patrol Behavior Profiles (D-MIL-0104)

## 1. Purpose

This document describes how **militia checkpoints and patrols actually behave**
on Dosadi, given:

- Officer doctrines (D-MIL-0102),
- Patronage networks and guild–MIL bargains (D-IND-0105),
- Ward attributes and evolution (D-WORLD-0002/0003),
- Legal/emergency states (D-LAW-0001/0002/0003).

It provides:

- Behavior profiles for checkpoints and patrols under different doctrines.
- How these profiles vary across ward types (Industrial Spine, Lift Ring,
  Civic Feed, Shadow, etc.).
- Hooks for simulation code and scenarios to:
  - determine search frequency and intensity,
  - choose who gets shaken down, spared, or “disappeared,”
  - generate incident events, rumors, and case flows.

This is the **street-level expression** of higher-level MIL and guild logic.

---

## 2. Checkpoint and Patrol Entities

We define two main MIL control entities:

```yaml
Checkpoint:
  id: string
  ward_id: string
  location_type: "corridor" | "lift_entry" | "barrel_cadence_node" | "ward_gate"
  controlling_node_id: string        # references CommandNode from D-MIL-0103
  posture:
    alert_level: string              # from D-MIL-0003
    doctrine_id: string              # from controlling CommandNode
  local_bargain_tags:
    - "protected_guild:GF_FAB_YARDHOOK"
    - "protected_guild:GF_SUITS_BRINE_CHAIN"
    - "cartel_favored"
  rumor_tags:
    - "brutal" | "lenient" | "bought" | "by_the_book"

PatrolRoute:
  id: string
  ward_id: string
  path_type: "interior_corridor" | "bunkhouse_loop" | "industrial_loop" | "perimeter"
  controlling_node_id: string
  patrol_frequency: float            # passes per tick
  doctrine_id: string
  local_bargain_tags:
    - "looks_the_other_way_for:GF_FOOD_VATCHAIN"
```

These entities inherit behavior biases from:

- doctrine of the controlling CommandNode,
- local bargains with guilds/cartels,
- ward legal/emergency state.

---

## 3. Behavior Axes

Checkpoint and patrol behavior can be decomposed along several axes:

1. **Encounter Frequency**
   - How often civilians and guild traffic are stopped or questioned.
2. **Search Intensity**
   - No search / visual inspection / pat-down / invasive search.
3. **Target Selection Bias**
   - Who is more likely to be stopped:
     - unaffiliated, guild workers, known cartel affiliates, nobility, etc.
4. **Corruption and Side Extraction**
   - Likelihood of:
     - bribe solicitation,
     - confiscation for personal resale,
     - protection rackets.
5. **Escalation Probability**
   - Likelihood that an encounter becomes:
     - arrest, beating, “disappearance,” or case routed into LAW.
6. **Information Behavior**
   - Reporting discipline:
     - what gets logged accurately,
     - what gets distorted or suppressed.

---

## 4. Doctrine-Derived Behavior Profiles

### 4.1 Hardline Suppressionist Checkpoints

Characteristics:

- **Encounter Frequency:** high, especially for:
  - large groups,
  - known guild activists,
  - “outsiders” from other wards.
- **Search Intensity:** aggressive by default.
- **Target Selection Bias:**
  - high suspicion of guild workers and anyone moving industrial parts,
  - moderate suspicion of clergy/bishops,
  - deferential but watchful toward nobility.

Behavior sketch:

```yaml
CheckpointBehaviorProfile:
  doctrine_id: "MIL_DOC_HARDLINE"
  base_stop_chance:
    unaffiliated: 0.5
    guild_worker: 0.7
    cartel_flagged: 0.9
    noble_retainers: 0.3
  search_intensity_distribution:
    light: 0.1
    normal: 0.3
    invasive: 0.6
  corruption_tendency: 0.3
  escalation_probability:
    to_beating: 0.3
    to_arrest: 0.4
    to_disappearance: 0.1
  reporting_discipline: 0.7
```

Effects:

- Sharp increase in fear and resentment.
- Guilds and cartels shift movement to **unpatrolled paths** and Shadow wards.
- High volume of LAW cases (tribunals, administrative sanctions).

---

### 4.2 Patronage Pragmatist Checkpoints

Characteristics:

- **Encounter Frequency:** moderate overall, but:
  - low for in-network guilds and cartel-linked flows,
  - higher for unaffiliateds and rival networks.
- **Search Intensity:** variable; often performative.
- **Target Selection Bias:**
  - strong favoritism based on patronage edges,
  - uses enforcement as an economic and political tool.

Behavior sketch:

```yaml
CheckpointBehaviorProfile:
  doctrine_id: "MIL_DOC_PATRONAGE"
  base_stop_chance:
    unaffiliated: 0.6
    guild_worker: 0.4
    protected_guild_worker: 0.1
    cartel_favored: 0.05
    noble_retainers: 0.2
  search_intensity_distribution:
    light: 0.4
    normal: 0.4
    invasive: 0.2
  corruption_tendency: 0.8
  escalation_probability:
    to_beating: 0.15
    to_arrest: 0.2
    to_disappearance: 0.05
  reporting_discipline: 0.4
```

Effects:

- Wards feel “manageable” but unjust.
- Patronage networks deepen; protected actors treat checkpoints as toll booths.
- Shadow markets bloom around predictable leniency.

---

### 4.3 Professional Orderist Checkpoints

Characteristics:

- **Encounter Frequency:** tuned to formal guidance and threat assessments.
- **Search Intensity:** proportional to flags (e.g. info from audits, intel).
- **Target Selection Bias:** relatively neutral; focuses on specific risk markers.

Behavior sketch:

```yaml
CheckpointBehaviorProfile:
  doctrine_id: "MIL_DOC_PROFESSIONAL"
  base_stop_chance:
    unaffiliated: 0.4
    guild_worker: 0.4
    cartel_flagged: 0.9
    noble_retainers: 0.2
  search_intensity_distribution:
    light: 0.3
    normal: 0.5
    invasive: 0.2
  corruption_tendency: 0.2
  escalation_probability:
    to_beating: 0.1
    to_arrest: 0.3
    to_disappearance: 0.02
  reporting_discipline: 0.9
```

Effects:

- Predictable environment; people learn usable rules.
- Law cases and sanctions align more closely with telemetry and INFO flows.

---

### 4.4 Zealot Purist Checkpoints

Characteristics:

- **Encounter Frequency:** high against “corrupting” influences.
- **Search Intensity:** high for guilds, cartels, nobles deemed decadent.
- **Target Selection Bias:** aligns with ideological foes.

Behavior sketch:

```yaml
CheckpointBehaviorProfile:
  doctrine_id: "MIL_DOC_ZEALOT"
  base_stop_chance:
    unaffiliated: 0.4
    guild_worker: 0.7
    cartel_flagged: 0.9
    noble_retainers: 0.7
  search_intensity_distribution:
    light: 0.1
    normal: 0.3
    invasive: 0.6
  corruption_tendency: 0.1
  escalation_probability:
    to_beating: 0.3
    to_arrest: 0.5
    to_disappearance: 0.15
  reporting_discipline: 0.8
```

Effects:

- Destroys patronage stability.
- Increases martyr narratives and zealot vs “corrupt” guild/audit conflict.

---

## 5. Patrol Behavior Profiles

Patrols differ from checkpoints:

- They **go to** trouble rather than waiting for it.
- They can:
  - disperse gatherings,
  - raid bunkhouses and canteens,
  - sweep industrial yards.

We define:

```yaml
PatrolBehaviorProfile:
  doctrine_id: string
  patrol_frequency_modifier: float
  proactive_raid_bias: float       # how often patrol initiates raids
  dispersal_vs_observation_bias: float
  target_selection_biases:
    guild_sites: float
    bunkhouses: float
    canteens: float
    corridors: float
  brutality_index: float
  rumor_signature_tags:
    - string
```

### 5.1 Hardline Patrols

- High frequency, high proactive raids, high brutality.
- Strong focus on **guild sites** and known trouble spots.

### 5.2 Patronage Patrols

- Focused on **maintaining rackets**:
  - raids on non-protected scavs and unauthorized markets,
  - visible “order” operations to justify protection.

### 5.3 Professional Patrols

- Task-driven:
  - respond to specific intel or telemetry flags,
  - sweep areas with documented incident histories.

### 5.4 Zealot Patrols

- Seek ideological enemies:
  - guild faction headquarters,
  - places associated with “decadence” (black markets, certain canteens).

---

## 6. Ward-Type Variations

Checkpoint and patrol profiles are modulated by **ward context**:

### 6.1 Industrial Spine Wards

- High density of:
  - FABRICATION, SUITS, ENERGY operations.
- Checkpoints focus on:
  - movement of parts, barrels, and exo units.
- Effects:
  - Heavy Hardline presence → intense searches of workers and yards.
  - Patronage presence → guilds use checkpoints as channels for skims.

### 6.2 Lift Ring / Hinge Wards

- Checkpoints are choke points:
  - lifts, main corridors.
- Small changes in behavior have big systemic impact:
  - delays cascade city-wide.

### 6.3 Civic Feed Wards

- Checkpoints cluster around:
  - bunkhouse entrances,
  - canteen districts.

- Patronage profiles:
  - shake down unaffiliateds while leaving bishop- and guild-linked canteens
    mostly alone.
- Hardline profiles:
  - use checkpoints to control movement during ration unrest.

### 6.4 Shadow Wards

- Patrols often:
  - serve cartel or patronage agendas.
- Checkpoints:
  - may be more about toll extraction than security.
- When Zealot/Hardline officers appear:
  - they are perceived as invaders into a quasi-autonomous zone.

---

## 7. Interaction with Guild and Cartel Logic

### 7.1 Guild adaptations

Guilds respond to checkpoint/patrol behavior by:

- Adjusting **shift timing** and routes for workers.
- Using **protected corridors** negotiated via bargains.
- Developing **counter-routines**:
  - crowds forming to witness/limit brutality,
  - rumor campaigns targeting specific checkpoints.

### 7.2 Cartel adaptations

Cartels:

- Identify:
  - lenient checkpoints (Patronage-dominated),
  - doctrinal weak spots (Professional officers with low corruption).

- Exploit:
  - gaps during command rotations and purges,
  - confusion when doctrine mix shifts.

---

## 8. Law, Telemetry, and Rumor Hooks

### 8.1 Law and case flows

Checkpoint and patrol incidents feed:

- Case creation:
  - Administrative cases (fines, ration cuts),
  - Tribunal cases (serious offenses),
  - Disappearances (record-light).

Doctrine and patronage determine:

- which incidents **get logged**,
- which **die at checkpoint level**,
- which become **public trials**.

### 8.2 Telemetry and INFO

From D-INFO-0001/0003:

- Professional and Zealot doctrines generate more logs (though not always
  honest).
- Patronage doctrine:
  - shows suspicious gaps in logs,
  - correlation between unlogged flows and black market surges.

### 8.3 Rumor and ward memory

Checkpoints and patrols are key rumor generators:

- Named checkpoints:
  - “Rat Gate,” “Hookline Post,” “Crown-Cage.”
- Stories:
  - “No one comes back from being taken at Rat Gate.”
  - “If you slip the right sergeant a coil, Hookline never sees your crate.”

These stories affect:

- route choice for agents,
- risk assessments for RL policies,
- ward-level sentiment indices.

---

## 9. Implementation Sketch (Non-Normative)

1. **Instantiate checkpoints and patrol routes** per ward:
   - Use ward topology (WORL D), MIL deployment (D-MIL-0002),
   - Mark key corridor, lift, barrel, and habitation nodes.

2. **Assign controlling nodes and doctrines**:
   - Link each checkpoint/patrol to a CommandNode (D-MIL-0103),
   - Inherit doctrine and patronage alignment.

3. **Derive behavior profile**:
   - Base on doctrine archetype,
   - Modify with:
     - local guild–MIL bargains (D-IND-0105),
     - ward legal state and alert level (D-LAW-0003, D-MIL-0003).

4. **Run encounter logic**:
   - For each agent or flow crossing a checkpoint or patrol:
     - sample encounter probability,
     - determine search intensity, corruption events,
     - possibly spawn incidents and LAW cases.

5. **Feedback into world**:
   - Update:
     - rumor indices,
     - guild/cartel pathfinding preferences,
     - local perception of `sanction_intensity` and `impunity_index`.

6. **Expose for UI / scenarios**:
   - Show:
     - key checkpoint names, doctrine tags (“Hardline,” “Bought”),
     - simple descriptors (“brutal,” “lenient,” “by-the-book”),
     - incident history (“3 disappearances in last 10 ticks”).

---

## 10. Future Extensions

Potential follow-ups:

- `D-MIL-0105_Garrison_Morale_and_Fracture_Risk`
  - How checkpoint and patrol behavior feeds back into MIL morale and
    possibility of mutinies.

- Scenario-specific checkpoint atlases
  - Pre-defined checkpoint/patrol maps and behavior tags for major arcs
    (e.g. Sting Wave corridors, key Lift Ring choke points).
