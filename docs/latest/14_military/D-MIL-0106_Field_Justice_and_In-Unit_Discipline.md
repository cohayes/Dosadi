---
title: Field_Justice_and_In-Unit_Discipline
doc_id: D-MIL-0106
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
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 14_military · Field Justice and In-Unit Discipline (D-MIL-0106)

## 1. Purpose

This document defines how **discipline is enforced inside militia units** on
Dosadi, below the level of formal tribunals and high-law procedures.

It covers:

- **Field justice**:
  - summary punishments,
  - on-the-spot decisions by officers and NCOs,
  - ad hoc “corrections” carried out in the field.

- **In-unit discipline systems**:
  - internal codes and norms,
  - unofficial councils and cliques,
  - parallel justice run by sergeants, specialist cadres, or patronage blocs.

It links to:

- Officer doctrines (D-MIL-0102),
- Rotations and purges (D-MIL-0103),
- Checkpoint/patrol behavior (D-MIL-0104),
- Garrison morale and fracture risk (D-MIL-0105),
- Legal sanction chains (D-LAW-0001/0002/0003),
- Rumor and ward memory (D-INFO-0006).

Goal: give scenarios and simulation code a clear logic for **how MIL polices
itself**, when it does so, and how that shapes whether units hold—or implode.

---

## 2. Conceptual Layers of Discipline

We distinguish three overlapping layers:

1. **Formal** – governed by written regulations and LAW:
   - referrals to tribunals,
   - recorded sanctions,
   - documented curfew/order violations.

2. **Field** – governed by commander and NCO discretion:
   - informal punishments,
   - “corrective measures,”
   - summary executions in edge cases.

3. **Sub-unit** – governed by group norms and cliques:
   - peer enforcement,
   - hazing and ostracism,
   - protection of favored members and persecution of scape-goats.

How these layers interact depends heavily on doctrine and morale.

---

## 3. Offense and Discipline Taxonomy

### 3.1 Common in-unit offenses

Typical categories:

- **Operational**:
  - cowardice under fire,
  - dereliction of checkpoint/patrol duties,
  - mishandling of weapons/equipment.

- **Disciplinary**:
  - insubordination,
  - brawling inside unit,
  - intoxication on duty.

- **Political**:
  - refusal to enforce certain orders,
  - open sympathy with guilds or cartels,
  - sharing banned pamphlets or rumor motifs.

- **Economic/corruption**:
  - skimming bribes not shared with the chain,
  - theft from unit stores,
  - unsanctioned deals with guilds or cartels.

### 3.2 Sanction spectrum

Sanctions range from:

- Verbal reprimand,
- Extra duty / undesirable shifts,
- Docked pay or ration cuts,
- Beatings or stress positions,
- “Field accidents” (arranged exposure to danger),
- On-the-spot executions,
- Referral to external LAW mechanisms.

We model **preferred response patterns** via doctrine and unit culture.

---

## 4. Doctrine-Based Discipline Styles

### 4.1 Hardline Suppressionist

Core traits:

- Sees discipline as **fear-driven**.
- Uses harsh punishments early to deter others.

Likely responses:

- Operational offenses:
  - beatings, public humiliation, dangerous postings.
- Disciplinary offenses:
  - collective punishment (whole squad suffers for one).
- Political offenses:
  - rapid escalation to **Security Tribunals** when noticed.
- Economic offenses:
  - tolerated only if they run through the proper patronage channels;
    independent skimming punished harshly.

Effect on GarrisonState:

- Temporarily high `cohesion.vertical` (fear-based),
- Long-term decline in `morale.current`,
- Increased `fracture_risk` toward desertion and quiet sabotage.

---

### 4.2 Patronage Pragmatist

Core traits:

- Sees discipline as **resource management and loyalty enforcement**.
- Focus on protecting the cohesion of the **patronage network**.

Likely responses:

- Operational offenses:
  - punished if they risk the network’s income or reputation.
- Disciplinary offenses:
  - resolved through informal councils; penalties may be fines/bribes.
- Political offenses:
  - tolerated if aligned with patron; punished if threaten bargains.
- Economic offenses:
  - main concern is **unauthorized skimming**;
    discipline is about keeping flows predictable.

Effect on GarrisonState:

- `cohesion.horizontal` often strong within in-group,
- `alignment.with_cartels` or guilds can increase,
- fracture risk concentrated in **sub-groups excluded from patronage**.

---

### 4.3 Professional Orderist

Core traits:

- Sees discipline as **system integrity**.
- Attempts to align field justice with written codes.

Likely responses:

- Operational offenses:
  - recorded, graded; sanctions escalate by severity and repetition.
- Disciplinary offenses:
  - targeted punishments; group penalties used sparingly.
- Political offenses:
  - handled carefully; preference for formal review rather than ad hoc purge.
- Economic offenses:
  - disciplined as breaches of trust; confiscated gains may be returned to unit
    or recorded.

Effect on GarrisonState:

- Higher `cohesion.vertical` where leadership is seen as consistent,
- `morale.current` more resilient under stress,
- fracture risk lower but not zero where regime orders conflict with
  internal ethics (e.g. massacres).

---

### 4.4 Zealot Purist

Core traits:

- Sees discipline as **moral cleansing**.
- Punishment doubles as propaganda.

Likely responses:

- Operational offenses:
  - framed as moral weakness; intense shaming and harsh sanctions.
- Disciplinary offenses:
  - interpreted through purity lens (e.g. “decadence,” “weakness”).
- Political offenses:
  - crushed brutally; public confessions and exemplary punishments.
- Economic offenses:
  - selectively tolerated if for “the cause”; ruthlessly punished if seen
    as selfish corruption.

Effect on GarrisonState:

- Strong cohesion among true believers,
- Growing terror or resistance among non-believers,
- fracture risk polarized: pockets of fanatic loyalty vs explosive mutiny.

---

## 5. Sub-Unit Discipline Mechanisms

### 5.1 Informal councils and sergeant courts

Within squads/platoons:

- **Sergeant courts**:
  - trusted NCOs convene small circles to judge minor offenses.
  - outcomes: extra duty, redistribution of loot, private beatings.

- **Peer councils**:
  - rank-and-file resolve disputes without officers,
  - outcomes: ostracism, retribution, protective deals.

These mechanisms:

- Can bolster `cohesion.horizontal` if seen as fair,
- Or create fractures if dominated by specific ethnic, ward-origin, or
  patronage subgroups.

### 5.2 Hazing and integration rites

- New arrivals may be hazed:
  - petty theft, forced labor, sleep deprivation.
- Purpose:
  - test loyalty,
  - establish hierarchy,
  - create “shared suffering.”

In outcomes terms:

- Moderate, controlled hazing → stronger unit identity.
- Extreme or abusive hazing → lowered morale, increased desertion risk.

### 5.3 Shadow “codes of honor”

Where formal doctrine is weak or distrusted, units may develop:

- “We don’t turn in our own to tribunals.”
- “Skimming is fine if shares are fair.”
- “No executions of unarmed civilians unless ordered and unavoidable.”

These unwritten codes:

- Interact with guild and civilian alignments,
- Can produce open defiance of orders perceived as code-breaking.

---

## 6. Field Justice Events

We model **field justice events** as micro-incidents with local effects:

```yaml
FieldJusticeEvent:
  id: string
  garrison_state_id: string
  offense_type: "operational" | "disciplinary" | "political" | "economic"
  decision_level: "officer" | "nco" | "peer_group"
  sanction_type: "reprimand" | "extra_duty" | "beating" | "danger_posting" | "execution"
  recorded_in_law: bool
  rumor_intensity: float            # 0–1
  perceived_fairness: float         # 0–1 (from troop POV)
```

### 6.1 Fair vs unfair outcomes

Perceived fairness depends on:

- Do similar offenses by **in-group vs out-group** get equal treatment?
- Is punishment proportional?
- Is sanction shared, or are scapegoats chosen to protect patrons?

Effects:

- Fair events:
  - boost `cohesion.horizontal` and sometimes `vertical`,
  - buffer morale against stress.

- Unfair events:
  - reduce `cohesion.vertical`,
  - increase `fracture_risk` (especially for quiet sabotage or mutiny).

### 6.2 Visibility and rumor

Some punishments are **public**:

- line-ups, visible beatings, executions,
- rumor_intensity is high and cross-ward.

Others are **hidden**:

- night-time disappearances,
- rumor spreads unevenly, often distorted.

The rumor system (D-INFO-0006) can treat FieldJusticeEvents as seeds for:

- “The commander protects his own,”
- “They shot their own man for refusing to fire,”
- “They let the sergeant go because he shares.”

---

## 7. Interaction with Garrison Morale and Fracture Risk

Using D-MIL-0105:

- Each FieldJusticeEvent updates:

  - `morale.current`: up or down depending on fairness and severity.
  - `cohesion.horizontal`:
    - up if peers see discipline as protecting group integrity,
    - down if they see betrayal.
  - `cohesion.vertical`:
    - up if commander is seen as just,
    - down if seen as arbitrary or self-protective.

- Patterns of events over time create trajectories:

  - units with many **unfair, harsh** events:
    - high `stress_load.political`,
    - increased `fracture_risk.collective_mutiny` or `switch_sides`.

  - units with consistent **proportional, clear** discipline:
    - higher resilience to external shocks,
    - more likely to hold together in crises.

---

## 8. Interaction with LAW and External Oversight

### 8.1 Referral vs internal handling

Commanders decide when to:

- **Handle internally**:
  - keep incidents off the formal books,
  - maintain autonomy and avoid external scrutiny.

- **Refer to tribunals or audits**:
  - signal alignment with central authority,
  - deflect blame upward.

Doctrinal preferences:

- Hardline: favors external tribunals for political offenses,
  internal brutality for operational failures.
- Patronage: prefers internal handling whenever possible.
- Professional: follows guidance; more likely to refer serious cases.
- Zealot: uses tribunals as stages for ideology and purging “impure” elements.

### 8.2 Audit and bishop interference

- **Audits** may:
  - investigate patterns of field justice,
  - use them as levers in purge cycles (D-MIL-0103).

- **Bishops/civic stewards** may:
  - advocate for or against certain commanders,
  - offer confession-like outlets that slightly decompress pressure.

---

## 9. Ward-Level Discipline Climate

We can define a **discipline climate index** per ward:

```yaml
WardDisciplineClimate:
  harshness_index: float         # average severity of sanctions
  fairness_index: float         # perceived fairness across events
  internal_vs_external_ratio: float   # internal handling vs LAW referrals
  rumor_profiles:
    - "commanders seen as butchers"
    - "unit takes care of its own"
    - "tribunals feared more than bullets"
```

Effects:

- High harshness + low fairness:
  - drives civilians toward guilds/cartels,
  - destabilizes MIL alignment with regime.

- Moderate harshness + high fairness:
  - maintains MIL cohesion and limited legitimacy.

- Low harshness + low fairness (indifference):
  - fosters corruption and uncontrolled patronage.

---

## 10. Implementation Sketch (Non-Normative)

1. **Initialize discipline style** from doctrine:

   - For each GarrisonState, derive base probabilities for:
     - sanction types,
     - internal vs external handling,
     - fairness bias.

2. **Generate FieldJusticeEvents**:

   - Triggered by:
     - incidents at checkpoints/patrols (D-MIL-0104),
     - guild/cartel interactions,
     - stress thresholds in GarrisonState.

3. **Update GarrisonState**:

   - Adjust morale, cohesion, stress, and fracture risks per event.
   - Track patterns of perceived fairness/harshness.

4. **Integrate with LAW**:

   - When events are referred:
     - spawn formal LAW cases,
     - feed into purge/rotation logic (D-MIL-0103).

5. **Propagate rumor and ward climate**:

   - Each event contributes to WardDisciplineClimate and rumor motifs.
   - Wards known for brutal or lax internal discipline affect:
     - agent route choices,
     - guild strategies,
     - player expectations.

---

## 11. Future Extensions

Potential follow-ups:

- `D-MIL-0107_Special_Detachments_and_Commissar_Cadres`
  - Units embedded specifically to monitor, enforce, or override local MIL
    discipline (e.g., ducal observers, ideological commissars).

- `D-LAW-0101_Military_Justice_Overlays`
  - How MIL-specific justice interacts and collides with civilian LAW
    frameworks in mixed tribunals.

- Scenario-specific unit discipline profiles
  - Named garrisons with reputations like “Butchers of Spine 3” or
    “Quiet Gate Warders,” each with bespoke discipline histories.
