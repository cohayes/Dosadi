---
title: Special_Detachments_and_Commissar_Cadres
doc_id: D-MIL-0107
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-WORLD-0003          # Ward_Evolution_and_Specialization_Dynamics
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
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
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 14_military · Special Detachments and Commissar Cadres (D-MIL-0107)

## 1. Purpose

This document defines **special oversight and enforcement elements** embedded in
or attached to militia units on Dosadi:

- **Special detachments** – squads or teams with exceptional mandate:
  - internal security,
  - counter-guild/counter-cartel operations,
  - “clean-up” and purge execution.

- **Commissar cadres** – individuals or small cells tasked with:
  - ideological enforcement,
  - loyalty monitoring,
  - direct reporting to duke_house or central organs.

It explains how these elements:

- Modify behavior of garrisons and checkpoints,
- Mediate or override local officer doctrines (D-MIL-0102),
- Are deployed through rotations and purges (D-MIL-0103),
- Affect morale and fracture risk (D-MIL-0105),
- Intersect with LAW and INFO systems.

Goal: give scenarios and sim code a structured way to represent **“watchers of
the watchers”** and their impact on the military ecology.

---

## 2. Entity Types

We define two primary overlay entities.

### 2.1 Special Detachment

```yaml
SpecialDetachment:
  id: string
  detachment_type: "internal_security" | "counter_guild" | "counter_cartel" | "purge_team" | "rapid_response"
  assigned_to_garrison_id: string
  doctrinal_alignment: string          # often Hardline or Zealot, sometimes Professional
  reporting_chain: "duke_house" | "central_mil_command" | "central_audit_guild"
  size_category: "small" | "medium"
  capabilities:
    - "forensic_audit_support"
    - "raid_leadership"
    - "interrogation"
    - "counter_sabotage"
  authority_overrides:
    can_override_commander_on:
      - "raid_targets"
      - "arrest_of_MIL_personnel"
      - "evidence_handling"
  secrecy_level: "visible" | "discreet" | "clandestine"
  rumor_tags:
    - "black_masks"
    - "duke's_fingers"
```

### 2.2 Commissar Cadre

```yaml
CommissarCadre:
  id: string
  size: int
  ideological_profile: "regime_orthodox" | "zealot_reformist" | "factional_ducal"
  attached_to_garrison_id: string
  reporting_chain: "duke_house" | "central_political_bureau" | "bishop_guild"
  tools:
    - "ideological_briefings"
    - "confession_sessions"
    - "secret_reports"
  intervention_rights:
    - "veto_orders"
    - "initiate_investigations"
    - "recommend_purges"
  visibility: "official" | "semi_denied" | "plausibly_denied"
  rumor_tags:
    - "eyes_on_every_wall"
    - "whispers_before_tribunals"
```

These overlay existing **CommandNode** and **GarrisonState** structures.

---

## 3. Functional Roles

### 3.1 Internal Security and Counter-Corruption

Special detachments may:

- Monitor skims and illicit flows between guilds/cartels and MIL,
- Run surprise inspections on:
  - checkpoints and patrols,
  - storerooms and armories,
  - FieldJusticeEvent patterns (D-MIL-0106).

Commissars may:

- Collect **confessions** and “concerns” from rank-and-file,
- Flag officers for investigation by tribunals or audits,
- Provide ideological framing: “corruption is treason,” etc.

Effects:

- Increases **perceived surveillance** inside units,
- Can curb certain forms of corruption while pushing others **deeper underground**,
- Raises `stress_load.political` in GarrisonState.

### 3.2 Counter-Guild and Counter-Cartel Operations

Detachments:

- Lead raids on known or suspected guild/cartel safehouses,
- Analyse telemetry anomalies (still working with D-INFO-0001),
- Direct checkpoints and patrols toward specific targets.

Commissars:

- Pressure commanders to treat particular guilds as enemies or allies,
- Influence **who is scapegoated** when operations fail.

Effects:

- Strongly shapes **which guilds/cartels thrive** under a given MIL regime,
- Can destabilize established bargains (D-IND-0105) or create new ones.

### 3.3 Purge Execution

During purge cycles (D-MIL-0103):

- Special detachments act as:
  - arrest teams,
  - evidence collectors,
  - execution squads.

- Commissar cadres:
  - help draw up purge lists,
  - conduct “re-education” sessions,
  - stage public confessions.

Effects:

- Sharp spikes in:
  - tribunal activity,
  - fear indices,
  - fracture risk across MIL.

---

## 4. Doctrine Interactions

### 4.1 With Hardline Commanders

- Special detachments:
  - often doctrinally aligned (Hardline or Zealot),
  - used as **force multipliers** for brutal crackdowns.

- Commissars:
  - may serve as direct regime eyes, ensuring Hardlines do not drift into
    independent warlordism.

Result:

- Amplified harshness in Field Justice (D-MIL-0106),
- High short-term control, high long-term fracture.

### 4.2 With Patronage Pragmatists

- Special detachments:
  - viewed with suspicion as “audit hounds” or “ducal spies.”
  - attempts made to co-opt or misdirect them via patronage.

- Commissars:
  - either:
    - get absorbed into the network (and become another patron node), or
    - become focal points for future purges.

Result:

- Increased **complexity** of patronage graphs,
- Potential dual reporting and double games.

### 4.3 With Professional Orderists

- Special detachments:
  - can be integrated into formal procedures,
  - used to strengthen system integrity (if aligned).

- Commissars:
  - source of tension if they push ideology over professionalism,
  - or allies if they support rule-based reforms.

Result:

- Mixed: can either bolster a “clean” MIL or create friction that weakens it.

### 4.4 With Zealot Purists

- Special detachments:
  - may be zealot shock troops for ideological campaigns.

- Commissars:
  - central actors, providing:
    - doctrine,
    - target lists,
    - rituals of punishment and absolution.

Result:

- MIL becomes a vehicle for **crusade-style purges**,
- Non-zealot factions increasingly desperate or covert.

---

## 5. Effects on Garrison Morale and Fracture Risk

Using D-MIL-0105:

- Presence of special detachments and commissars generally:

  - increases `stress_load.political`,
  - reduces `cohesion.vertical` where seen as alien or hostile,
  - may increase `cohesion.vertical` among true believers.

- Morale effects depend on perception:

  - If seen as **protecting** units from arbitrary purges or corrupt officers:
    - morale may improve,
    - alignment with regime might strengthen.

  - If seen as **predatory or capricious**:
    - morale collapses,
    - fracture risk (desertion, mutiny, alignment switch) rises.

- Rumor effects:

  - “Commissars eat their own first,”
  - “Specials never sleep; they just listen,”
  - “You’re safer with the Yardhook than your own command.”

---

## 6. Checkpoint and Patrol Modifiers

From D-MIL-0104:

- SpecialDetachment presence near a checkpoint may:

  - raise **search intensity** and **escalation probability**,
  - shift target bias toward particular guilds or cartel tags,
  - reduce corruption if anti-corruption detachment,
    or redirect it if co-opted.

- Commissar presence:

  - biases enforcement toward ideological enemies,
  - may demand **public discipline displays** at checkpoints
    (humiliations, exemplary arrests).

Behavior hook:

```yaml
CheckpointOverlayEffect:
  special_detachment_modifier:
    stop_chance_delta: float
    invasive_search_delta: float
    corruption_tendency_delta: float
    escalation_to_tribunal_delta: float
  commissar_modifier:
    target_bias_tags:
      - "guild:GF_FOOD_VATCHAIN"
      - "cartel:QuietLantern"
    public_punishment_frequency: float
```

---

## 7. Deployment Patterns

### 7.1 Core and Lift Ring

- High concentration of commissar cadres:
  - guarding access to dukes and core infrastructure.
- Special detachments:
  - focused on counter-coup and internal security.

### 7.2 Industrial Spine

- Mix of:
  - counter-guild detachments (Yardhook, Brine Chain, Lift Crown focus),
  - purge teams after major industrial incidents or sabotages.

### 7.3 Civic Feed and Bishop-Dense Wards

- Commissars often in tension with bishops:
  - competing for moral authority over troops.
- Some detachments focus on:
  - policing ration unrest,
  - monitoring bishop–MIL–guild triads.

### 7.4 Shadow Wards

- Officially:
  - few visible commissars, sporadic detachments.
- Unofficially:
  - clandestine teams inserted for:
    - targeted kidnappings,
    - assassin-style purges,
    - cartel co-option or elimination.

---

## 8. Interaction with Guild and Cartel Systems

### 8.1 Guild strategies

Guilds may:

- Attempt to **co-opt** special detachments:
  - providing selective intel,
  - offering “clean” cases that justify their continued existence.

- Use commissars as:
  - pressure points against rival guilds,
  - conduits to ducal ears for charter disputes (D-IND-0103).

Counter-moves:

- Blackmail based on commissar or detachment abuses,
- Feeding false intel to provoke overreach and backlash.

### 8.2 Cartel strategies

Cartels may:

- Infiltrate detachments via:
  - bribes, threats, or ideological alignment.
- Frame rivals by:
  - planting evidence,
  - guiding detachments to the “wrong” targets.

They treat commissars as:

- high-value elimination targets,
- or as potential patrons if corrupted or disillusioned.

---

## 9. Law and Telemetry Integration

### 9.1 LAW overlays

Special detachments often:

- Have **special legal authorities**:
  - broader arrest powers,
  - ability to initiate tribunals quickly,
  - carve-outs from ordinary oversight.

Commissars:

- May write direct reports to LAW organs and dukes,
- Influence **which incidents** become formal cases.

This amplifies:

- non-linearity in LAW responses between wards,
- the connection between political campaigns and case flows.

### 9.2 Telemetry distortions

From D-INFO-0001/0003:

- Presence of special detachments and commissars may produce:

  - spikes in certain types of logs (raids, arrests),
  - gaps where data is suppressed or overwritten.

- Quiet Ledger Houses and audits may:
  - cross-correlate detachment activity with industrial and ward indices,
  - identify suspicious patterns (e.g., raids coinciding with guild charter
    negotiations).

---

## 10. Implementation Sketch (Non-Normative)

1. **Instantiate overlays**:

   - For key garrisons, attach:
     - zero or more SpecialDetachment entities,
     - zero or more CommissarCadre entities.

2. **Modify CommandNode behavior**:

   - Use overlay presence and alignment to adjust:
     - doctrine bias,
     - law path preferences,
     - purge participation.

3. **Modify GarrisonState and events**:

   - Increase `stress_load.political` when overlays active and high-intensity.
   - Adjust probabilities for:
     - FieldJusticeEvents,
     - referrals to tribunals,
     - purges targeting unit leadership.

4. **Adjust checkpoint/patrol profiles**:

   - As per Section 6, modify encounter/profiling behavior.

5. **Generate overlay-specific events**:

   - “Commissar inspection,”
   - “Special detachment raid,”
   - “Commissar removed in quiet purge.”

6. **Feedback to WORLD and other pillars**:

   - Wards with heavy overlay presence:
     - may trend toward more brittle forms of control,
     - show strong but fragile order.

---

## 11. Future Extensions

Potential follow-ups:

- `D-MIL-0108_Counterintelligence_and_Infiltration_Risk`
  - How guilds and cartels penetrate MIL and its oversight organs.

- Scenario-specific overlay packs
  - Designed commissar cadres and special detachments for key arcs:
    - e.g. “Purge of the Third Spine,” “Quiet Ring Crackdown,”
      or late-stage regime paranoia.
