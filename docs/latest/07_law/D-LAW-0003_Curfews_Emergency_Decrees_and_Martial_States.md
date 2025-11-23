---
title: Curfews_Emergency_Decrees_and_Martial_States
doc_id: D-LAW-0003
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
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

# 09_law · Curfews, Emergency Decrees, and Martial States (D-LAW-0003)

## 1. Purpose

This document defines how the regime on Dosadi uses **macro-level legal tools**
to reshape everyday life:

- **Curfews** that restrict movement in time,
- **Emergency decrees** that alter rules of conduct, work, and access,
- **Martial states** where military and law systems partially or fully fuse.

It specifies:

- Types and scales of curfews and decrees,
- Who can declare, extend, or revoke them,
- How they interact with:
  - Sanctions (D-LAW-0001),
  - Procedural paths (D-LAW-0002),
  - Garrison structure (D-MIL-0002),
  - Ward attributes (D-WORLD-0002),
  - Rumor and information flows (D-INFO-*),
  - Economy and survival infrastructure (D-ECON-0001, D-HEALTH-0002).

The goal is to give scenarios and simulation code a coherent **switchboard** of
high-level legal states without prescribing a single canonical crisis story.

---

## 2. Relationship to Other Law and MIL Docs

- **D-LAW-0001_Sanction_Types_and_Enforcement_Chains**  
  - Defines the *content* of punishments; this doc defines when those punishments
    are applied under heightened legal regimes.

- **D-LAW-0002_Procedural_Paths_and_Tribunals**  
  - Defines the *routes* cases take; this doc defines how emergencies deform or
    override those routes.

- **D-MIL-0001/0002/0003**  
  - Provide the military tools, spatial deployments, and alert levels.
  - Curfews and martial states are often **legal reflections of MIL posture**.

- **D-ECON-0001, D-HEALTH-0002**  
  - Curfews and decrees heavily impact water, food, and work; misuse can
    generate famine, unrest, or black market surges.

- **D-INFO-0001/0003/0006**  
  - Emergencies reshape what must be reported, how censorship works, and how
  rumors about decrees spread.

---

## 3. Legal Emergency Levels

We define a layered model of **legal emergency levels** that usually but not
always align with MIL alert levels.

Conceptual levels (non-binding):

```yaml
legal_state:
  NORMAL: 0
  HEIGHTENED_SECURITY: 1
  LOCAL_EMERGENCY: 2
  PARTIAL_MARTIAL_STATE: 3
  FULL_MARTIAL_STATE: 4
```

These can apply:

- **Per ward** (e.g. LOCAL_EMERGENCY in Ward 07),
- **Regionally** (clusters of wards),
- **City-wide** (for extreme events).

The simulation may track `legal_state(w)` per ward separately from
`alert_level(w)`, with scenario-specific mapping between them.

---

## 4. Curfew Types

Curfews restrict **movement by time window**. We distinguish several archetypes.

### 4.1 Night Curfew

- Prohibits non-authorized movement during designated hours (e.g. 3rd–7th
  watch).
- Commonly applied under **HEIGHTENED_SECURITY** or **LOCAL_EMERGENCY**.

Effects:

- Reduces night-time black market traffic and cartel operations **on the surface**,
  but may drive them into more hidden or protected routes.
- Increases checkpoint encounters for late workers and shift-changers.
- Alters rumor patterns (more bunkhouse gossip, less canteen loitering).

### 4.2 Rolling Curfew

- Curfew that **moves through time or space**:
  - e.g. one sector locked down for two watches, then another.
- Used to avoid completely freezing city-wide productivity while still applying
  pressure.

Effects:

- Complicates scheduling and work shifts.
- Can be used to selectively punish or test specific wards.
- Rumors about where the curfew will “roll” next become a strategic info asset.

### 4.3 Total Lockdown (Ward or Sector)

- No civilian movement without explicit authorization within a ward or cluster.
- Often linked with **sweeps**, mass searches, or major investigations.

Effects:

- Sharp spike in `sanction_intensity(w)` and `legal_opacity(w)`.
- Supply and waste handling must be actively managed to avoid rapid degradation.
- Black market and cartel circuits may reroute around locked wards, or exploit
  insider collusion.

### 4.4 Soft Curfew

- Officially there is no curfew, but:
  - Checkpoints become aggressive at certain hours,
  - “Advised” staying indoors is broadcast,
  - People know movement is risky.

Effects:

- Increases `rumor_fear_index(w)` without formal declarations.
- Useful for plausible deniability and testing population responses.

---

## 5. Emergency Decrees

Emergency decrees **alter rules**, either temporarily or “until revoked.”

### 5.1 Decree Axes

Decrees typically affect:

- **Movement and assembly**
  - Limits on gatherings, restrictions on meetings, licensing of assemblies.
- **Work and production**
  - Mandatory overtime, forced reassignments, priority production orders.
- **Speech and information**
  - Bans on certain rumors, pamphlets, songs, or conversations.
  - Expanded powers for censorship and confiscation of records.
- **Resource rationing**
  - Changes to distribution rules, priority queues, or exemptions.
- **Procedural shortcuts**
  - Reduced requirements for warrants, shortened appeal windows.

### 5.2 Decree Object

Conceptual schema:

```yaml
EmergencyDecree:
  id: string
  scope: "ward" | "region" | "city"
  affected_wards:
    - ward_id
  start_tick: int
  end_tick: int | null    # null = open-ended
  declared_by: "duke_house" | "militia_high_command" |
               "central_audit_guild" | "bishop_guild" | "other"
  decree_axes:
    movement_controls: "none" | "limited" | "strict"
    assembly_controls: "none" | "licensed_only" | "banned"
    work_controls: "normal" | "priority" | "forced"
    speech_controls: "normal" | "censored" | "draconian"
    ration_controls: "normal" | "tightened" | "emergency_priority"
    procedure_shortcuts: "none" | "moderate" | "extreme"
```

Scenarios may define presets like:

- **“Protection Order”** – tightened checkpoints and licensed assemblies.
- **“Production Surge Order”** – forced overtime in certain guilds.
- **“Silence Order”** – harsh controls on rumor and speech.

---

## 6. Martial States

Martial states blend **military command** with civil administration.

### 6.1 Partial Martial State

Applied when:

- Civil authorities are deemed weak, compromised, or overwhelmed,
- The regime wants a sharper, faster legal response without fully discarding
  civil structures.

Characteristics:

- Militia officers gain veto or override powers in ward-level decisions.
- Curfews and decrees become easier to declare and extend.
- Procedural paths (D-LAW-0002) skew toward **Security Tribunals** and
  **Administrative Handling** dominated by militia.

Mechanical hooks:

- Increase `impunity_index(w)` for militia and allied actors.
- Reduce `appeal_success_rate(w)` and perceived due process.
- Can temporarily reduce unrest via fear, but may increase long-term volatility.

### 6.2 Full Martial State

Applied under extreme threats (real or manufactured).

Characteristics:

- Civil administration effectively subordinated or suspended.
- Most cases of significance routed to Security Tribunals or extrajudicial
  handling.
- Broad, strict curfews and emergency decrees, often city-wide or region-wide.
- Guilds and bishops forced into explicit alignment decisions.

Mechanical hooks:

- Very high `sanction_intensity(w)` and `legal_opacity(w)` in affected wards.
- Extreme `tribunal_frequency(w)` and `collective_punishment_risk(w)`.
- If prolonged:
  - Severe economic disruption,
  - Rising reliance on cartels and informal governance for basic survival,
  - Potential for regime fracture or coup.

---

## 7. Authority, Triggers, and Constraints

### 7.1 Who can declare what

Scenarios should define which actors can initiate which states:

```yaml
emergency_authority:
  curfews:
    ward_level:
      primary: "ward_admin"
      override: "militia_commander"
    city_level:
      primary: "duke_house"
      consults:
        - "militia_high_command"
        - "central_audit_guild"
  decrees:
    resource_rationing:
      primary: "central_audit_guild"
      consults:
        - "duke_house"
        - "bishop_guild"
    speech_and_info:
      primary: "duke_house"
      consults:
        - "espionage_branch"
    work_controls:
      primary: "duke_house"
      executes:
        - "industry_guilds"
  martial_state:
    partial:
      primary: "militia_high_command"
      requires_consent_of:
        - "duke_house"
    full:
      primary: "duke_house"
      consults:
        - "militia_high_command"
        - "central_audit_guild"
```

This can be tuned per scenario to reflect different regimes (paranoid dukes,
military-leaning rule, or audit-heavy technocracy).

### 7.2 Triggers

Typical triggers include:

- Repeated or severe incidents in MIL logs,
- Telemetry anomalies (missing barrels, repeated system failures),
- Rumor spikes about revolt, assassination, or mutiny,
- Guild strikes or cartel escalations,
- Political events (succession crises, external threats).

### 7.3 Constraints and rollback

If emergencies are **too frequent or prolonged**, the system may:

- Erode `loyalty_to_regime(w)` beyond repair,
- Overstretch garrisons and supply,
- Create openings for alternative power centers.

Scenarios may specify:

- Maximum duration or frequency of states before stability penalties apply,
- Political costs within duke_house or among nobles.

---

## 8. Effects on Wards, Agents, and Flows

### 8.1 Ward-level effects

When a ward enters a higher legal state:

- Update or scale:
  - `sanction_intensity(w)` (up),
  - `legal_opacity(w)` (up),
  - `due_process_index(w)` (down),
  - `impunity_index(w)` (up),
  - `collective_punishment_risk(w)` (often up),
  - `rumor_fear_index(w)` (up).

- Adjust:
  - `garrison_presence` posture (more visible patrols, stops),
  - `checkpoint_density` behavior (more searches, closures),
  - `black_market_intensity(w)` (may go up or down depending on risk vs need),
  - `shortage_index(w)` (risk of supply disruption).

### 8.2 Agent-level effects

Agents experience emergencies as:

- Higher chance of:
  - Being stopped, searched, or questioned,
  - Being sanctioned for minor offenses,
  - Having cases routed to harsher paths.

- Changing incentives:
  - Risk of defiance vs survival benefit of compliance,
  - Opportunities for smuggling, bribery, or collaboration,
  - Heightened stakes for rumor propagation (heroes vs scapegoats).

Occupations like `occ_corridor_vendor`, `occ_canteen_worker`,
`occ_bunkhouse_steward`, `occ_exo_tech`, `occ_ration_clerk`, and various
militia roles become pivotal in how emergencies actually feel on the ground.

---

## 9. Implementation Sketch (Non-Normative)

A minimal integration could:

1. Track `legal_state(w)` for each ward as an integer 0–4.
2. At each simulation phase:
   - Evaluate triggers for increasing or decreasing `legal_state(w)` based on:
     - incidents, shortages, unrest, rumor intensity, and political inputs.
3. When `legal_state(w)` changes:
   - Apply immediate modifiers to ward attributes (sanction, law, rumor,
     garrison posture).
   - Spawn decree/curfew objects with relevant parameters.
4. Modify:
   - Case routing (D-LAW-0002) to favor harsher paths at higher legal states.
   - Sanction selection (D-LAW-0001) to allow harsher punishments.
   - Rumor generation (D-INFO-0006) with appropriate templates (lockdowns,
     curfews, raids, purges).
5. Periodically attempt rollback:
   - If triggers subside, scenario rules may reduce `legal_state(w)` or
     require explicit political decisions to maintain it.

Numeric thresholds and precise interaction weights are left to implementation.

---

## 10. Future Extensions

Potential follow-ups:

- `D-LAW-0102_States_of_Exception_and_Suspension_of_Rights`  
  - More detailed treatment of when certain groups are declared “outside
    the law” and what that means mechanically.

- `D-LAW-0103_Regime_Fracture_and_Coup_Dynamics`  
  - How prolonged martial states can lead to internal conflict within
    duke_house, militia, and guilds.

- Scenario-level emergency playbooks  
  - Predefined chains of decrees and curfews for major plotlines
    (e.g. the lead-up to Sting Wave scenarios).
