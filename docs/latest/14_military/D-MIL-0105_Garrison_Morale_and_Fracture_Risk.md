---
title: Garrison_Morale_and_Fracture_Risk
doc_id: D-MIL-0105
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
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 14_military · Garrison Morale and Fracture Risk (D-MIL-0105)

## 1. Purpose

This document defines how **garrison morale** and **fracture risk** behave in
Dosadi's militia units, and how they interact with:

- Officer doctrines and patronage networks (D-MIL-0102),
- Command rotations and purge cycles (D-MIL-0103),
- Checkpoint and patrol behavior (D-MIL-0104),
- Guild actions and bargains (D-IND-0104/0105),
- Ward evolution and stress levels (D-WORLD-0003),
- Legal regimes and tribunals (D-LAW-0001/0002/0003).

It provides:

- A state model for **unit morale and cohesion**,
- Sources of **strain and support**,
- Types of **fracture events** (desertion, mutiny, quiet sabotage),
- Hooks for simulation code and scenarios to:
  - predict when units will crack,
  - represent “which side” a garrison is effectively on,
  - show how prolonged pressure reshapes the MIL landscape.

---

## 2. Garrison State Model

We model each MIL unit or garrison segment with a **morale and fracture state**.

```yaml
GarrisonState:
  id: string
  ward_id: string
  commander_node_id: string         # CommandNode from D-MIL-0103
  size_category: "small" | "medium" | "large"
  morale:
    baseline: float                 # 0–1, structural factors
    current: float                  # 0–1, dynamic
  cohesion:
    horizontal: float               # rank-and-file solidarity (0–1)
    vertical: float                 # trust in command chain (0–1)
  stress_load:
    operational: float              # fatigue, caseload, danger
    political: float                # exposure to purges, doctrinal conflict
    economic: float                 # pay, rations, side income volatility
  alignment:
    with_regime: float              # 0–1
    with_local_guilds: float        # 0–1
    with_cartels: float             # 0–1
    with_civilians: float           # 0–1
  fracture_risk:
    desertion: float                # probability weight
    quiet_sabotage: float
    collective_mutiny: float
    switch_sides: float             # alignment flip to guilds/cartels/rebels
  rumor_tags:
    - "tired"
    - "bought"
    - "volatile"
    - "fanatic"
```

`morale.current` and `cohesion` respond to events and conditions described below.

---

## 3. Drivers of Morale and Stress

### 3.1 Structural and baseline factors

Slow-changing contributors:

- **Deployment context** (D-MIL-0002):
  - Outer industrial bastions: high risk, harsh conditions.
  - Lift Ring: intense pressure to avoid failures.
  - Civic Feed: frequent crowd control and close contact with suffering.
  - Shadow wards: blurred lines between MIL and gangs.

- **Unit composition**:
  - percentage of conscripts vs career soldiers,
  - local vs non-local recruits.

- **Doctrine fit**:
  - how well commander doctrine matches ward demands and unit expectations.

These define `morale.baseline` and initial `cohesion`.

### 3.2 Operational stress

Sources:

- Frequent alerts and high alert levels (D-MIL-0003),
- Repeated violent engagements, casualties, and injuries,
- Continuous checkpoint and patrol workloads (D-MIL-0104).

Effects:

- Increases `stress_load.operational`,
- Gradual decline in `morale.current` if not relieved,
- Potential **hardening** (for some doctrines/factions) up to a point.

### 3.3 Political and purge stress

Sources:

- Ongoing purge cycles (D-MIL-0103),
- Investigations by audits and tribunals targeting command or rank-and-file,
- Perceived injustice in punishments and promotions.

Effects:

- Increases `stress_load.political`,
- Erodes `cohesion.vertical` (trust in command),
- May increase `alignment.with_cartels` or guilds if they offer protection.

### 3.4 Economic and corruption stress

Sources:

- Irregular pay or ration cuts (D-ECON-0001),
- Disruption of side income chains (D-IND-0105),
- Competition within unit for access to bribes and favors.

Effects:

- Increases `stress_load.economic`,
- Can reduce `cohesion.horizontal` if inequality and infighting rise,
- May push some sub-factions toward **riskier bargains** with cartels.

---

## 4. Support and Stabilizing Factors

### 4.1 Doctrine and leadership

- **Professional Orderist** commanders:
  - boost `cohesion.vertical` through predictable rules,
  - moderate stress via structured rest cycles where possible.

- **Patronage Pragmatist** commanders:
  - boost morale when side deals are stable and profitable,
  - but create fractures if perceived unfair or selectively applied.

- **Hardline** and **Zealot** commanders:
  - can boost short-term cohesion under external threat,
  - at cost of long-term exhaustion and resentment.

### 4.2 Guild and bishop relationships

- Guild–MIL bargains (D-IND-0105) can:
  - provide better equipment, food, and living conditions,
  - offer informal protection from harsh sanctions.

- Bishop and civic stewards:
  - may run chaplain-equivalents, mediating disputes,
  - provide spaces for off-duty decompression.

These factors raise `morale.current` and sometimes `alignment.with_local_guilds`
or `with_civilians`.

### 4.3 Rotation and rest

- Rotations (D-MIL-0103) that:
  - move units out of high-stress wards,
  - give genuine downtime,

can reduce `stress_load.operational` and boost morale.

By contrast:

- Constant redeployments without rest **increase** stress and erode cohesion.

---

## 5. Fracture Modes

We distinguish several **fracture modes**:

1. **Desertion** – individuals or small groups abandoning posts.
2. **Quiet sabotage** – intentional underperformance or damage to equipment.
3. **Collective mutiny** – unit-level refusal of orders or overthrow of commanders.
4. **Alignment switch** – unit or sub-unit effectively siding with guilds,
   cartels, or rebels while still wearing MIL colors.

Each is influenced by different slices of the GarrisonState.

---

## 6. Desertion

### 6.1 Conditions favoring desertion

- `morale.current` very low.
- `cohesion.horizontal` moderate–low (little peer control).
- High `stress_load.operational` or `stress_load.economic`.
- Viable exit paths:
  - Shadow wards,
  - cartel or guild that will absorb deserters.

### 6.2 Effects

- Reduces unit effective strength.
- Increases:
  - rumor tags: “deserters,” “ghost uniforms,” “empty posts,”
  - recruitment pressure from regime and MIL.

- May feed:
  - cartel and shadow guild manpower,
  - scavenger bands.

---

## 7. Quiet Sabotage

### 7.1 Conditions favoring quiet sabotage

- `cohesion.horizontal` high (bonds among rank-and-file),
- `cohesion.vertical` low (distrust/disgust toward command),
- `alignment.with_regime` low, `alignment.with_local_guilds` or `cartels` higher.

Takes forms like:

- “Losing” equipment,
- Deliberately poor maintenance,
- Misreporting readiness and patrol results.

### 7.2 Effects

- Undermines MIL readiness **without open confrontation**.
- Creates:
  - discrepancy between telemetry and real capacity,
  - more opportunities for guild/c cartel operations.

---

## 8. Collective Mutiny

### 8.1 Conditions favoring mutiny

- Very low `cohesion.vertical`,
- High `cohesion.horizontal` (unit solidarity against command),
- High `stress_load.political` (unpopular purges, scapegoating),
- Perceived lack of exit or survival under current regime.

### 8.2 Types of mutiny

- **Limited mutiny**:
  - refusal to enforce certain decrees,
  - rejection of particular orders (e.g., firing on a crowd).

- **Command overthrow**:
  - removal/replacement of commander,
  - sometimes presented as “internal correction” rather than rebellion.

- **Open revolt**:
  - unit aligns with explicit rebel factions,
  - seizes facilities, weapons, and corridors.

### 8.3 Effects

- Major spike in:
  - `fracture_risk.switch_sides` for neighboring units,
  - emergency/legal states in affected wards.

- Triggers:
  - Security Tribunals,
  - possible large-scale purges,
  - regime propaganda campaigns.

---

## 9. Alignment Switch

### 9.1 Quiet alignment switch

- Unit retains outward appearance of loyalty but:
  - systematically leaks intel to guilds/cartels,
  - selectively enforces law,
  - functions as a **house guard** for a guild, bishop, or duke.

### 9.2 Overt alignment switch

- Unit openly rebrands its loyalty:
  - declares for a rebel banner,
  - joins a ducal faction in civil conflict.

### 9.3 Drivers

- Long-standing patronage links (D-MIL-0102, D-IND-0105),
- Heavy stress and perceived betrayal by regime,
- Strong ideological pull (from zealot movements, charismatic dukes, etc.).

---

## 10. Ward and Network Effects

### 10.1 Ward-level indicators

We can derive **garrison pressure indices** per ward:

```yaml
WardGarrisonStress:
  morale_avg: float
  cohesion_vertical_avg: float
  fracture_risk_total: float
  recent_incidents:
    - "desertion"
    - "mutiny"
    - "alignment_switch"
```

High fracture risk in key wards implies:

- Greater vulnerability of:
  - checkpoints,
  - depots,
  - exo-bays.

Also influences:

- Guild and cartel decision-making:
  - where to push hardest,
  - where to focus recruitment or subversion.

### 10.2 Network contagion

- Mutiny or notable fracture events in one ward:
  - change rumor motifs in neighboring wards,
  - shift `morale.current` and `cohesion` in units sharing:
    - doctrinal ties,
    - training schools,
    - patronage networks.

- Purge responses:
  - may either deter or inflame similar moves elsewhere.

---

## 11. Interaction with Other Systems

### 11.1 Command rotations and purges

From D-MIL-0103:

- **Rotations**:
  - can relieve stress (fresh leadership, lighter duty),
  - or increase it (harder doctrine, breakage of trusted patterns).

- **Purges**:
  - are double-edged:
    - removing deeply corrupt or hated officers may temporarily boost morale,
    - but widespread purges erode trust and increase fracture risk.

### 11.2 Guild bargains and plays

From D-IND-0104/0105:

- Stable, “fair” bargains:
  - raise morale by improving conditions,
  - can still erode alignment with regime if guilds are seen as true patrons.

- Unfair or exploitative bargains:
  - increase internal resentments,
  - fuel fracture risk, particularly toward quiet sabotage or alignment switches.

Guild strikes and slowdowns:

- Put added pressure on MIL to enforce decrees,
- May be seen as unjust work if units sympathize with guild grievances.

### 11.3 Law and tribunals

From D-LAW-0001/0002/0003:

- Heavy use of **Security Tribunals** against MIL members:
  - can terrorize units into compliance,
  - or drive them toward revolt if seen as arbitrary.

- **Curfews and emergency decrees**:
  - increase operational stress, especially if long-lasting and unpopular.

---

## 12. Implementation Sketch (Non-Normative)

1. **Initialize GarrisonState** per unit:
   - Set baseline morale and cohesion from:
     - deployment context,
     - composition,
     - commander doctrine.

2. **Update per macro-step**:
   - Adjust stress_load components with:
     - alert level time spent,
     - casualty and incident rates,
     - purge events and LAW cases,
     - changes in financial/side income conditions.

   - Apply support factors:
     - rest/rotation,
     - guild/bishop support,
     - perceived fairness of leadership.

   - Recompute `morale.current`, `cohesion.horizontal`, `cohesion.vertical`.

3. **Compute fracture risks**:
   - Map combinations of low morale, cohesion, and alignments into:
     - desertion,
     - quiet sabotage,
     - mutiny,
     - alignment switch probabilities.

4. **Trigger fracture events stochastically**:
   - When events occur:
     - update MIL deployment and readiness,
     - adjust ward-level fear/unrest,
     - generate law cases and rumor stories.

5. **Propagate effects**:
   - Adjust:
     - neighboring GarrisonState values (contagion),
     - guild and cartel strategies.

6. **Expose to dashboards and scenarios**:
   - Ward MIL summary: “Garrison tired, fracturing along cartel lines.”
   - Scenario hooks: “Unit at Lift Gate B likely to refuse next massacre order.”

---

## 13. Future Extensions

Potential follow-ups:

- `D-MIL-0106_Field_Justice_and_In-Unit_Discipline`
  - How units internally police desertion, corruption, and dissent.

- `D-RUNTIME-0102_Campaign_Milestone_and_Crisis_Triggers`
  - How large-scale MIL fractures become campaign milestones (civil war,
    regime collapse, negotiated settlements).

- Scenario-specific garrison dossiers
  - Named units with bespoke morale histories and fracture triggers for
    arcs like Sting Wave Day-3 or longer campaigns.
