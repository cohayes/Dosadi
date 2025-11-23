---
title: Security_Dashboards_and_Threat_Surfaces
doc_id: D-INFO-0014
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
  - D-MIL-0108            # Counterintelligence_and_Infiltration_Risk
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002           # Espionage_Branch
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-INFO-0009           # Counterintelligence_Tradecraft_and_Signatures
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 08_info_security · Security Dashboards and Threat Surfaces (D-INFO-0014)

## 1. Purpose

This document defines how **security-relevant state** is surfaced to:

- In-world actors:
  - duke_house staff,
  - Espionage Branch and audit analysts,
  - certain MIL command echelons, bishops, and guild security arms.

- The **simulation UI**:
  - developer/observer dashboards,
  - scenario briefings and overlays,
  - potential player-facing “intel views.”

It specifies:

- Core **dashboard views** for MIL/INFO/LAW/WORLD security states.
- The concept of **threat surfaces**:
  - where the system is most vulnerable to disruption, infiltration, or revolt.
- How CI signatures (D-INFO-0009) and MIL CI states (D-MIL-0108) are aggregated
  into usable indicators rather than raw firehose.

---

## 2. Design Principles

1. **Layered visibility**
   - Different roles see different layers:
     - dukes vs Espionage analysts vs garrison commanders vs bishops.
   - The simulation UI can see more, but scenarios may constrain views.

2. **Aggregated, not omniscient**
   - Dashboards show indices, trends, and flags, not perfect truth.
   - CI misreads and partial data are baked in.

3. **Hook-friendly**
   - Each dashboard component should be referenceable by:
     - scenario scripts,
     - AI policy modules,
     - narrative triggers.

4. **Multi-pillar integration**
   - Security is not just MIL:
     - industry, economy, law, rumor, and world structure all feed in.

---

## 3. Core Concepts: Threat Surfaces and Indices

### 3.1 Threat surfaces

A **threat surface** is a part of the system where:

- Small changes can create large systemic effects, and
- Multiple hostile or competing actors have plausible access.

Threat surfaces often coincide with:

- high leverage **WORLD** nodes:
  - Lift Ring corridors,
  - barrel cadence hubs,
  - major exo-bays.

- dense **IND/ECON** flows:
  - industrial spine wards,
  - food and water distribution nodes.

- complex **MIL/INFO/LAW** overlaps:
  - garrisons with heavy patronage,
  - wards under partial martial law,
  - sites of recent purges or large strikes.

### 3.2 Security indices

We define a generic per-ward dashboard aggregate:

```yaml
WardSecuritySummary:
  ward_id: string
  threat_level: "low" | "moderate" | "high" | "critical"
  unrest_index: float
  repression_index: float
  infiltration_risk_index: float
  ci_posture_level: int                 # from CIPosture
  garrison_stability_index: float       # inverse of fracture risk
  black_market_intensity_index: float
  law_opacity_index: float
  rumor_volatility_index: float
```

These indices are composed from:

- WORLD, IND, ECON metrics,
- MIL and CI states,
- LAW and INFO signals.

---

## 4. Dashboard Views

### 4.1 Global Security Overview

Audience:

- Duke-house strategists,
- top Espionage Branch and central audits,
- simulation master view.

Contains:

- **Map of wards** colored by `threat_level`.
- For each ward on hover:
  - `unrest_index`,
  - `repression_index`,
  - `infiltration_risk_index`,
  - `garrison_stability_index`,
  - notable rumors (“Commander bought by Lift Crown,” “Guild strike brewing”).

Use:

- quick identification of:
  - failing wards,
  - brittle bastions,
  - brewing rebellion zones.

---

### 4.2 CI and Infiltration Panel

Audience:

- Espionage Branch CI cells,
- special detachments command,
- dev/observer.

Contains:

- List of **highest infiltration risk nodes**:
  - command nodes, checkpoints, detachments.

- For each node:
  - `CIState.infiltration_risk`,
  - `suspicion_score`,
  - current `investigation_level`,
  - recent relevant signatures (D-INFO-0009),
  - linked patronage and guild/cartel ties.

Use:

- prioritize CI actions:
  - where to deploy stings, purges, or double-agent operations.

---

### 4.3 MIL Stability and Discipline Panel

Audience:

- central_mil_command,
- some Espionage elements,
- simulation master.

Contains:

- Per-ward **GarrisonState aggregates**:
  - morale, cohesion (horizontal & vertical),
  - fracture risks (desertion, mutiny, alignment switch),
  - WardDisciplineClimate metrics (D-MIL-0106),
  - overlay presence (special detachments, commissars).

Use:

- see where units are:
  - over-stressed,
  - likely to crack,
  - dangerously zealot-heavy or patronage-captured.

---

### 4.4 Law and Sanctions Panel

Audience:

- LAW apparatus,
- Espionage Branch analysts,
- some MIL liaison roles.

Contains:

- Distribution of recent sanctions by:
  - ward,
  - type (administrative, tribunal, extrajudicial),
  - target roles (guild, MIL, civilian, cartel).

- Indicators of **law opacity**:
  - ratio of internal to external discipline,
  - concentration of tribunals in specific factions.

Use:

- detect structural justice anomalies,
- infer possible LAW capture or political repression patterns.

---

### 4.5 Rumor and Narrative Panel

Audience:

- INFO/propaganda arms,
- some CI units,
- narrative / scenario designers.

Contains:

- Ward-level **rumor motifs** and intensity:
  - fear, resentment, hope, martyrdom, betrayal themes.

- Highlighted rumor hubs:
  - key canteens, lifts, bunkhouses, and black market squares.

Use:

- anticipate unrest,
- target narrative operations (leaflets, arrests, staged trials),
- feed emergent storytelling/UI.

---

## 5. Role-Based Views

### 5.1 Duke-house Strategic View

Sees:

- Global Security Overview,
- high-level CI pointers (“Spine 3 MIL compromised by Yardhook”),
- summary of LAW patterns and industrial output.

Does not see:

- asset names,
- detailed CI tradecraft,
- all internal MIL fractures (filtered reports).

Biases:

- data often filtered to match ducal expectations and political agendas.

---

### 5.2 Espionage Branch Analyst View

Sees:

- most of CI/Infiltration Panel,
- telemetry and ledger anomaly summaries,
- cross-ward network signatures.

Still constrained by:

- compartmentalization:
  - may see slices, not global omniscience.

---

### 5.3 Garrison Commander View

Sees:

- local ward-level SecuritySummary (sanitized),
- some MIL Stability/Discipline metrics (not all CI suspicion),
- LAW and rumor signals relevant to their ward.

Does not see:

- full CI suspicion scores on themselves,
- cross-ward political patterns.

---

### 5.4 Player/Scenario Operator View

Configurable:

- debug mode: near-omniscient across all dashboards,
- scenario mode: emulate a given role’s visibility,
- narrative mode: partial information with some “fog of war” and misreporting.

---

## 6. Threat Surface Identification

We define a **ThreatSurface** object:

```yaml
ThreatSurface:
  id: string
  name: string
  ward_ids:
    - string
  node_ids:
    - string               # MIL, IND, INFO, LAW, WORLD nodes
  leverage_score: float    # systemic impact if disrupted (0–1)
  exposure_score: float    # accessibility to hostile actors (0–1)
  stability_score: float   # inverse of current volatility (0–1)
  dominant_threat_types:
    - "guild_capture"
    - "cartel_smuggling"
    - "mil_mutiny"
    - "rebellion"
    - "coup_vector"
```

Use:

- highlight key complexes (e.g. “Lift Crown – Spine 2 – Stillwater Branch 1”),
- drive scenario hooks (“Protect/Exploit ThreatSurface X”).

---

## 7. Data Flow into Dashboards

High-level pipeline:

1. **Collect metrics**:
   - from WORLD, IND, ECON, MIL, LAW, INFO, RUMOR layers.

2. **Update local indices**:
   - `WardSecuritySummary`, `CIState`, `GarrisonState`, LAW stats.

3. **Compute ThreatSurface scores**:
   - using:
     - leverage (topological importance, resource flows),
     - exposure (alignment with Shadow, black markets, CI posture),
     - stability (fracture risk, rumor volatility, purge history).

4. **Render dashboards**:
   - apply role-based filters,
   - convert raw numbers into statuses, colors, and narrative tags.

---

## 8. Imperfect Information and Misleading Dashboards

Dashboards are not truth; they are **products** of:

- partial data,
- political interference,
- CI tradecraft biases.

Examples:

- Under-reporting:
  - compromised nodes forging telemetry to make wards look stable.

- Over-reporting:
  - zealot analysts inflating threat levels to justify purges.

- Time lags:
  - events propagate from rumor → logs → dashboards with delay.

Simulation hooks:

- misalignment between **ground truth** and **dashboard view** can:
  - cause missteps (mis-targeted crackdowns),
  - create openings for guilds/cartels/rebels.

---

## 9. UI / Implementation Sketch (Non-Normative)

1. **Define dashboard schemas** in code mirroring the YAML snippets.

2. **At each simulation tick**:
   - recalc security indices and threat surfaces,
   - cache per-role filtered views.

3. **Expose via interfaces**:
   - CLI summaries (for early builds),
   - later map-based or panel-based UI components.

4. **Scenario tools**:
   - allow scenarios to:
     - subscribe to threshold crossings (“threat_level(w) becomes critical”),
     - script events based on specific ThreatSurface or CI changes.

---

## 10. Future Extensions

Potential follow-ups:

- `D-INFO-0015_Operator_Alerts_and_Escalation_Prompts`
  - How dashboards generate alerts, and how operators are nudged toward
    certain actions (including bad ones).

- `D-RUNTIME-0102_Campaign_Milestone_and_Crisis_Triggers`
  - Using security indices and threat surfaces to define high-level campaign
    arcs (regime survival, collapse, negotiated transformations).
