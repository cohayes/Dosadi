---
title: Officer_Doctrines_and_Patronage_Networks
doc_id: D-MIL-0102
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-WORLD-0003          # Ward_Evolution_and_Specialization_Dynamics
  - D-IND-0001            # Industry_Taxonomy_and_Types
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
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 14_military · Officer Doctrines and Patronage Networks (D-MIL-0102)

## 1. Purpose

This document describes the **internal cultures** of Dosadi's militia officer
corps and how those cultures manifest as:

- **Doctrines** – mental models of order, threat, and “correct” use of force.
- **Patronage networks** – webs of loyalty, favors, and side contracts that
  bind officers to:
  - guild factions (D-IND-0102),
  - dukes and nobles,
  - bishops and civic stewards,
  - cartels and black markets.

It is a bridge between:

- Force structures and deployments (D-MIL-0001, D-MIL-0002),
- Response cadences and alert levels (D-MIL-0003),
- Guild charters and bargains (D-IND-0103, D-IND-0105),
- Ward evolution and specialization (D-WORLD-0003),
- Law and rumor dynamics (D-LAW-*, D-INFO-*).

The goal is to give scenarios and simulation code a **doctrine + network layer**
that explains why different garrisons behave very differently under the same
formal rules.

---

## 2. Conceptual Overview

We treat militia behavior as the result of two interacting components:

1. **Officer Doctrine**  
   - How an officer (or command node) believes order is maintained:
     - fear and exemplary violence,
     - predictable bargains and stability,
     - “professional” proportionality,
     - ideological purification, etc.

2. **Patronage Network Position**  
   - Who the officer owes and who owes the officer:
     - duke_house patrons,
     - guild patrons,
     - bishop intermediaries,
     - cartel fixers.

These shape:

- Which **incidents** from D-MIL-0003 get escalated,
- How **curfews, raids, and tribunals** (D-LAW-0003) are applied in practice,
- How **guild plays and bargains** are received (D-IND-0104, D-IND-0105),
- How wards drift toward Bastion, Civic Feed, or Shadow attractors
  (D-WORLD-0003).

---

## 3. Officer Doctrine Archetype Template

Each doctrine archetype is described using this schema:

```yaml
OfficerDoctrineArchetype:
  id: string
  label: string
  summary: string
  default_escalation_bias:
    toward_law_paths:
      administrative: float
      guild_arbitration: float
      audit_commission: float
      security_tribunal: float
      extrajudicial: float
    toward_alert_levels:
      routine: float
      heightened: float
      local_emergency: float
      partial_martial: float
      full_martial: float
  treatment_of_guilds:
    baseline_trust: float          # 0–1
    preferred_bargain_types:
      - "protection_noninterference"
      - "uptime_guarantees"
      - "side_payment_channels"
      - "intelligence_deals"
  treatment_of_civilians:
    crowd_controls:
      prefers_curfew_over_raids: bool
      prefers_sanction_over_mass_detention: bool
    tolerance_for_unrest: float    # how much unrest before escalation
  corruption_profile:
    personal_gain_weight: float
    institutional_loyalty_weight: float
    regime_loyalty_weight: float
  rumor_signature_tags:
    - string
```

This is a **behavioral lens** for garrisons, checkpoints, and patrols.

---

## 4. Core Doctrine Archetypes

### 4.1 Hardline Suppressionist

```yaml
OfficerDoctrineArchetype:
  id: "MIL_DOC_HARDLINE"
  label: "Hardline Suppressionist"
  summary: "Order through fear, exemplary punishment, and rapid escalation."
  default_escalation_bias:
    toward_law_paths:
      administrative: 0.0
      guild_arbitration: 0.0
      audit_commission: 0.1
      security_tribunal: 0.6
      extrajudicial: 0.3
    toward_alert_levels:
      routine: 0.1
      heightened: 0.3
      local_emergency: 0.3
      partial_martial: 0.2
      full_martial: 0.1
  treatment_of_guilds:
    baseline_trust: 0.2
    preferred_bargain_types:
      - "uptime_guarantees"
      - "intelligence_deals"
  treatment_of_civilians:
    crowd_controls:
      prefers_curfew_over_raids: false
      prefers_sanction_over_mass_detention: false
    tolerance_for_unrest: 0.2
  corruption_profile:
    personal_gain_weight: 0.3
    institutional_loyalty_weight: 0.5
    regime_loyalty_weight: 0.7
  rumor_signature_tags:
    - "likes to make examples"
    - "raids first, questions later"
    - "tribunals follow in their wake"
```

Behavior:

- Quick to use force and tribunals.
- Sees guild strikes and slowdowns as **incipient rebellion**.
- Prefers strict enforcement of charters, willing to break existing bargains.

Ward-level effects:

- High `sanction_intensity(w)` and `legal_opacity(w)`.
- Short-term reduction in visible unrest, long-term drift toward **Shadow** or
  explosive revolt.

---

### 4.2 Patronage Pragmatist

```yaml
OfficerDoctrineArchetype:
  id: "MIL_DOC_PATRONAGE"
  label: "Patronage Pragmatist"
  summary: "Order through predictable favors, deals, and selective enforcement."
  default_escalation_bias:
    toward_law_paths:
      administrative: 0.4
      guild_arbitration: 0.2
      audit_commission: 0.2
      security_tribunal: 0.15
      extrajudicial: 0.05
    toward_alert_levels:
      routine: 0.4
      heightened: 0.3
      local_emergency: 0.2
      partial_martial: 0.1
      full_martial: 0.0
  treatment_of_guilds:
    baseline_trust: 0.6
    preferred_bargain_types:
      - "protection_noninterference"
      - "side_payment_channels"
      - "strike_management"
      - "intelligence_deals"
  treatment_of_civilians:
    crowd_controls:
      prefers_curfew_over_raids: true
      prefers_sanction_over_mass_detention: true
    tolerance_for_unrest: 0.5
  corruption_profile:
    personal_gain_weight: 0.6
    institutional_loyalty_weight: 0.4
    regime_loyalty_weight: 0.4
  rumor_signature_tags:
    - "knows who to pay"
    - "their wards simmer but rarely erupt"
    - "justice depends on who you drink with"
```

Behavior:

- Sees guilds as **partners** in keeping the lid on.
- Leans heavily on D-IND-0105 style bargains.
- Uses administrative and guild forums to smooth over conflicts.

Ward-level effects:

- Lower apparent `sanction_intensity(w)` for in-network actors,
  higher for outsiders.
- Wards drift toward **stable but corrupt equilibria**, with strong
  Shadow and cartel underlayers.

---

### 4.3 Professional Orderist

```yaml
OfficerDoctrineArchetype:
  id: "MIL_DOC_PROFESSIONAL"
  label: "Professional Orderist"
  summary: "Order through predictable rules, limited force, and clear chains."
  default_escalation_bias:
    toward_law_paths:
      administrative: 0.5
      guild_arbitration: 0.2
      audit_commission: 0.2
      security_tribunal: 0.1
      extrajudicial: 0.0
    toward_alert_levels:
      routine: 0.5
      heightened: 0.3
      local_emergency: 0.15
      partial_martial: 0.05
      full_martial: 0.0
  treatment_of_guilds:
    baseline_trust: 0.5
    preferred_bargain_types:
      - "uptime_guarantees"
      - "intelligence_deals"
  treatment_of_civilians:
    crowd_controls:
      prefers_curfew_over_raids: true
      prefers_sanction_over_mass_detention: true
    tolerance_for_unrest: 0.6
  corruption_profile:
    personal_gain_weight: 0.2
    institutional_loyalty_weight: 0.7
    regime_loyalty_weight: 0.7
  rumor_signature_tags:
    - "sticks to the book, mostly"
    - "predictable if you know the rules"
    - "does not like surprises from above"
```

Behavior:

- Closer to textbook usage of D-MIL-0003 response cadences.
- Prefers charter-aligned bargaining rather than naked skims.
- Can clash with both Hardline and Patronage officers.

Ward-level effects:

- Moderate sanction indices, more consistent case handling.
- Wards may evolve toward **Bastion** or **Civic Feed** attractors with
  relatively legible law.

---

### 4.4 Zealot Purist (Minority Doctrine)

```yaml
OfficerDoctrineArchetype:
  id: "MIL_DOC_ZEALOT"
  label: "Zealot Purist"
  summary: "Order through ideological purification and crusade against corruption."
  default_escalation_bias:
    toward_law_paths:
      administrative: 0.2
      guild_arbitration: 0.0
      audit_commission: 0.4
      security_tribunal: 0.3
      extrajudicial: 0.1
    toward_alert_levels:
      routine: 0.2
      heightened: 0.3
      local_emergency: 0.3
      partial_martial: 0.15
      full_martial: 0.05
  treatment_of_guilds:
    baseline_trust: 0.1
    preferred_bargain_types:
      - "intelligence_deals"
  treatment_of_civilians:
    crowd_controls:
      prefers_curfew_over_raids: false
      prefers_sanction_over_mass_detention: true
    tolerance_for_unrest: 0.3
  corruption_profile:
    personal_gain_weight: 0.1
    institutional_loyalty_weight: 0.5
    regime_loyalty_weight: 0.9
  rumor_signature_tags:
    - "raids guild halls in the name of purity"
    - "breaks old bargains"
    - "loves public confessions"
```

Behavior:

- Acts as a **disruptor** of long-standing patronage networks.
- Often aligned with certain audit or duke factions.
- Can produce short-term “clean-up” followed by chaos as old informal
  stabilizers collapse.

Ward-level effects:

- Spike in `sanction_intensity(w)` and `tribunal_frequency(w)`.
- Potential shift of wards into unstable transitional states.

---

## 5. Patronage Network Model

### 5.1 Nodes and edges

We conceptualize patronage as a graph:

- Nodes:
  - individual officers or MIL units,
  - guild families and key factions,
  - ducal agents,
  - bishops or civic stewards,
  - cartel nodes.

- Edges:
  - **patronage** (flows of protection, promotion, favor),
  - **tribute** (flows of skims, gifts, loyalty acts),
  - **information** (flows of gossip, reports, warnings).

Conceptual fragment:

```yaml
PatronageNode:
  id: string
  type: "officer" | "guild_faction" | "duke_proxy" | "bishop" | "cartel_cell"
  ward_home: string

PatronageEdge:
  from: string
  to: string
  relation: "protects" | "pays" | "reports_to" | "shares_intel_with"
  strength: float
  secrecy: "open" | "discreet" | "clandestine"
```

The density and orientation of this graph influence:

- Which doctrine archetypes are **viable** in a given ward,
- Which guild–MIL bargains (D-IND-0105) are feasible,
- How quickly **leaks and betrayals** propagate.

### 5.2 Alignment and friction

We can define:

```yaml
officer_patronage_alignment:
  with_duke_house: float
  with_guilds: float
  with_bishops: float
  with_cartels: float
```

High alignment with:

- **Dukes + audits** → Hardline or Zealot may thrive.
- **Guilds + bishops** → Patronage Pragmatists dominate.
- **Cartels** → Shadow wards and corrupted garrisons emerge.

---

## 6. Spatial and Ward-Level Patterns

### 6.1 Outer industrial bastions

Typical mix:

- Hardline + Patronage Pragmatist officers.
- Strong guild influence (Yardhook, Brine Chain, Lift Crown).
- Patronage edges heavily entangled with **industrial guild factions**.

Consequences:

- Industrial Spine wards can be:
  - tightly controlled via fear and exemplary punishment, or
  - “kept running” via dense bargain webs that quietly tolerate skims.

### 6.2 Hinge / Lift Ring wards

Typical mix:

- Professional Orderists and Patronage officers.
- Strong Lift Crown and Stillwater presence.
- Officers balancing:
  - pressure from dukes for secure transit,
  - offers from guilds for preferential flows,
  - oversight from audits.

Consequences:

- High leverage points for coups or regime changes.
- Doctrinal shifts here have ** outsized impact ** on city dynamics.

### 6.3 Civic Feed and bishop-heavy wards

Typical mix:

- Patronage Pragmatists and some Professionals.
- Bishops act as **social mediators** in patronage networks.
- FOOD and WATER guilds are central.

Consequences:

- Wards may feel relatively “civil” but deeply dependent on who
  controls canteens and bunks.
- When doctrines shift Hardline or Zealot, these wards are where
  cruelty is most visible.

### 6.4 Shadow wards

Typical mix:

- Patronage officers with heavy cartel alignment,
- Demoralized Professionals, occasional rogue Hardlines.

Consequences:

- MIL categories blur into **armed gangs with uniforms**.
- Patronage graphs show:
  - strong edges between officers and cartels,
  - severed or weak links to dukes/audits.

---

## 7. Interaction with Guild Plays and Bargains

### 7.1 Doctrine as filter on guild plays

From D-IND-0104:

- **Hardline**:
  - Interprets slowdowns as covert rebellion → greater use of raids and
    tribunals.
  - Treats shadow production as treason rather than a negotiable offense.

- **Patronage**:
  - Sees strikes and slowdowns as negotiation tactics.
  - Prefers side payments and limited concessions over crackdowns.

- **Professional**:
  - Evaluates plays in terms of charter language and hazard to MIL
    readiness.
  - More likely to distinguish between symbolic actions and strategic threats.

- **Zealot**:
  - Treats guild plays as moral failures or corruption → high likelihood of
    crusade-style purges.

### 7.2 Doctrine and bargain stability

From D-IND-0105:

- Patronage doctrines **stabilize bargains**:
  - high bargain retention and inheritance across command rotations.

- Professional doctrines **formalize bargains**:
  - may convert them into written side-agreements or modified charters.

- Hardline / Zealot doctrines **destabilize or weaponize bargains**:
  - use previous deals as evidence of corruption,
  - selectively expose or punish rivals.

---

## 8. Implementation Sketch (Non-Normative)

1. **Assign doctrines to MIL nodes**:
   - Each garrison or key officer gets:
     - a primary doctrine archetype ID,
     - small random or scenario-based variation.

2. **Construct patronage graph**:
   - Using:
     - ward attributes (WORLD),
     - guild presence and power (IND),
     - LAW and ECON indices.
   - Seed edges:
     - officer ↔ guild_faction,
     - officer ↔ duke_proxy,
     - officer ↔ bishop,
     - officer ↔ cartel_cell (esp. in Shadow wards).

3. **Modify MIL behavior**:
   - When handling incidents (D-MIL-0003):
     - use doctrine to bias escalation choices.
   - When responding to guild plays (D-IND-0104):
     - use doctrine and patronage alignment to choose between negotiation
       and crackdown.
   - When evaluating or forming bargains (D-IND-0105):
     - use doctrine to determine acceptable bargain types and secrecy.

4. **Evolve over time**:
   - Promotions, demotions, and reassignment:
     - shift doctrine mix across wards.
   - Major events (purges, coups):
     - remove certain doctrine types from key nodes,
     - insert new doctrinal cadres.

5. **Expose for UI / scenarios**:
   - For each ward, provide:
     - dominant doctrine,
     - summary of patronage alignment (duke/guild/cartel),
     - hinting rumor tags:
       - “Officers drink with Lift Crown,”
       - “Garrison answers to the bishop first,”
       - “Tribunals follow this commander.”

---

## 9. Future Extensions

Possible follow-ups:

- `D-MIL-0103_Command_Rotations_and_Purge_Cycles`
  - How doctrinal mixes are reshaped over time by regime decisions.

- `D-MIL-0104_Checkpoint_and_Patrol_Behavior_Profiles`
  - Turning doctrine + patronage into concrete checkpoint and patrol
    behavior patterns.

- Scenario-specific officer rosters
  - Named commanders, their doctrines, and their patronage ties for
    arcs like the Sting Wave scenarios or regime transition campaigns.
