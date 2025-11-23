---
title: Pre_Sting_Quiet_Season
doc_id: D-SCEN-0001
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-RUNTIME-0102        # Campaign_Milestone_and_Crisis_Triggers
  - D-RUNTIME-0103        # Scenario_Framing_and_Win_Loss_Conditions
  - D-RUNTIME-0104        # Scenario_Packaging_and_Metadata
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
  - D-INFO-0014           # Security_Dashboards_and_Threat_Surfaces
  - D-INFO-0015           # Operator_Alerts_and_Escalation_Prompts
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 11_scenarios · Pre-Sting Quiet Season (S-0001 / D-SCEN-0001)

## 1. Scenario Overview

**Scenario ID:** `S-0001_Pre_Sting_Quiet_Season`  
**Package:** `sting_wave_cycle` (see D-RUNTIME-0104)  
**Recommended role:** Espionage Branch analyst cell or small duke_house advisory cell.  

This scenario represents the **last “quiet” window** before the Sting Wave era
fully ignites. Wards are tense but not yet openly on fire:

- Guilds are testing how far they can push slowdowns and quiet diversion.
- Cartels are probing corridors and checkpoints for stable protection.
- MIL garrisons are under growing pressure but still formally coherent.
- LAW is oscillating between proceduralism and ad-hoc crackdowns.
- The regime has not yet chosen between **Hard Crackdown** and **Authority
  Slip** (Fragmented Regime).

The player/AI role is to **navigate this pre-crisis season** and influence
whether Dosadi:

- stabilizes in a brittle but manageable “Rumbling Unrest” phase, or
- tips early into Hard Crackdown or Fragmentation, setting the stage for much
  harsher scenarios.

---

## 2. Fictional Framing (In-World)

> “The dashboards are noisy, but nothing is technically on fire yet.  
>  The dukes are arguing over tax flows and barrel cadences, not open treason.  
>  The guilds grumble, the cartels whisper, the garrisons drink and look away.  
>  If someone were going to keep the next decade from turning into a charnel
>  house, this would be their last good chance.”

- Timeframe: several weeks or months before major Sting Wave events.
- Campaign phase: late **STABLE_CONTROL** edging into **RUMBLING_UNREST**.
- Tone:
  - high anxiety, low clarity,
  - plausible deniability for every actor,
  - everything “almost fine” until it suddenly isn’t.

---

## 3. Scenario Role and View

### 3.1 Default role

**Primary default role:**

- `actor_type: "espionage_branch"`  
  - a small analyst cell tasked with keeping the regime informed and “ahead”
    of unrest without provoking overreaction.

Alternative variant role (optional):

- `actor_type: "duke_house"`  
  - a minor ducal advisory cluster responsible for recommending escalation or
    restraint based on Espionage and MIL reports.

### 3.2 Visibility profile

For the Espionage-analyst version:

- Strong access to:
  - CI & Infiltration Panel (D-INFO-0014),
  - Rumor & Narrative Panel,
  - partial Law & Sanctions Panel.

- Limited access to:
  - full MIL Stability Panel (some metrics masked),
  - high-level ducal political decisions (seen via alerts, not direct control).

---

## 4. Control Profile

As Espionage analysts, the player/AI can:

- Recommend CI posture changes:
  - propose raising or lowering CI posture in specific wards.
- Propose or withhold CI operations:
  - stings, integrity checks, targeted investigations (D-INFO-0009, D-MIL-0108).
- Shape information flows:
  - flag certain alerts as critical vs noise (influences duke_house / MIL
    reaction),
  - seed or dampen specific narratives via “information ops” requests.

The role **cannot** directly:

- Order purges or mass sanctions,
- Command MIL units or declare curfews,
- Rewrite guild charters.

Instead, Espionage recommendations influence:

- which EscalationPrompts are generated and how they are framed (D-INFO-0015),
- how likely ducal/MIL actors are to choose Hard Crackdown vs restraint.

---

## 5. Starting Conditions

### 5.1 Campaign state

- `starting_campaign_phase: "STABLE_CONTROL"`  
- Global metrics near but below rumbling threshold:
  - moderate `unrest_mean`,
  - low but rising `unrest_high_ward_fraction`,
  - low-to-moderate `black_market_intensity_mean`,
  - low `fragmentation_index`,
  - middling `regime_legitimacy_index` (not yet cratered).

### 5.2 Ward landscape (conceptual sketch)

- Core wards:
  - relatively high HVAC/sealing, lower open pollution,
  - administrative, financial, and information-guild heavy,
  - low overt unrest but growing rumor volatility.

- Spine wards:
  - industrial heavy, guild charters active and sometimes stressed,
  - some early slowdowns and quiet sabotage plays (D-IND-0104).

- Shadow wards:
  - higher black market intensity,
  - cartels probing MIL checkpoints and corridors,
  - LAW presence inconsistent.

Exact per-ward attributes are left to worldgen + overrides, but:

- at least one **industrial spine** ward is on track to become a future
  ThreatSurface,
- at least one **shadow-adjacent** ward is already rumor-rich and a
  potential spark point.

---

## 6. Objectives (Conceptual)

These will be translated into a formal `Objective` set (D-RUNTIME-0103), but the
intent is:

### 6.1 Primary objectives

1. **Delay Hard Crackdown**

   - Prevent campaign phase from entering `HARD_CRACKDOWN` before tick N.
   - Keep `global_stress_index` under a defined threshold.
   - Keep `unrest_high_ward_fraction` below a moderate level.

2. **Limit Fragmentation Risk**

   - Avoid high `fragmentation_index` values.
   - Keep the number of wards under de facto non-regime control below K.

3. **Constrain Purge Intensity**

   - Limit `purge_intensity_index` across the run.
   - Limit number of large-scale purges authorized (directly or indirectly)
     via CI recommendations.

### 6.2 Secondary objectives

- Identify and mitigate at least one **Protected Corridor** or **Phantom Loss**
  signature (D-INFO-0009).
- Resolve at least one guild collective action (strike/slowdown) without:
  - triggering a purge, or
  - pushing the ward into overt rebellion.

### 6.3 Forbidden outcomes

- Early transition to `OPEN_CONFLICT` during this scenario.
- Systemic Mosaic Collapse (fragmentation beyond a high threshold).

---

## 7. Embedded ScenarioDefinition Sketch

> This section is a **non-normative** YAML sketch intended for Codex and
> implementation work. Exact numbers and ids can be tuned later.

```yaml
ScenarioDefinition:
  id: "pre_sting_quiet_season"
  name: "Pre-Sting Quiet Season"
  description: >
    An Espionage Branch analyst cell tries to keep Dosadi from tipping into
    premature crackdown or fragmentation during the last 'quiet' season
    before the Sting Wave era.

  starting_campaign_phase: "STABLE_CONTROL"
  starting_tick: 0
  duration_limit_ticks: null           # could be set later if desired
  starting_state_ref: null             # or a named snapshot later

  world_overrides:
    ward_overrides: []                 # reserved for specific tuning

  role_configs:
    - role_id: "espionage_cell"
      actor_type: "espionage_branch"
      visibility_profile: "espionage_view"
      control_profile: "espionage_control"
      ai_or_player: "player"
      ai_personality_ref: null

  objectives:
    primary:
      - id: "delay_crackdown"
        label: "Delay Hard Crackdown"
        type: "state"
        success_condition:
          kind: "state"
          constraints:
            campaign_phase_not_in:
              - "HARD_CRACKDOWN"
              - "OPEN_CONFLICT"
            max_global_stress_index: 0.6
        failure_condition: {}
        priority: "primary"
        scoring_weight: 1.0

      - id: "limit_fragmentation"
        label: "Limit Fragmentation"
        type: "state"
        success_condition:
          kind: "state"
          constraints:
            max_fragmentation_index: 0.5
        failure_condition: {}
        priority: "primary"
        scoring_weight: 0.8

      - id: "constrain_purges"
        label: "Constrain Purge Intensity"
        type: "event"
        success_condition:
          kind: "event"
          constraints:
            max_events:
              purge_campaign_starts: 2
        failure_condition: {}
        priority: "primary"
        scoring_weight: 0.7

    secondary:
      - id: "resolve_guild_action_politically"
        label: "Resolve a Guild Action Without Purge"
        type: "event"
        success_condition:
          kind: "event"
          constraints:
            required_events:
              - "guild_strike_resolved_without_purge"
        failure_condition: {}
        priority: "secondary"
        scoring_weight: 0.4

      - id: "neutralize_suspicious_corridor"
        label: "Neutralize a Suspicious Corridor"
        type: "event"
        success_condition:
          kind: "event"
          constraints:
            required_events:
              - "protected_corridor_exposed_or_disrupted"
        failure_condition: {}
        priority: "secondary"
        scoring_weight: 0.3

    forbidden:
      - id: "no_open_conflict"
        label: "Avoid Open Conflict"
        type: "state"
        success_condition: {}
        failure_condition:
          kind: "state"
          constraints:
            campaign_phase_in:
              - "OPEN_CONFLICT"
        priority: "primary"
        scoring_weight: 1.0

  special_rules:
    trigger_tuning_ref: "pre_sting_quiet_tuning"
    hard_constraints:
      - "no_global_martial_law_declaration"
      - "no_mass_purge_at_start"
    scripted_events_ref: null
```

---

## 8. Design Notes and Tuning Dials

Key dials you (or future you) can adjust:

- **Thresholds** for:
  - when Rumbling → Hard Crackdown becomes likely,
  - how sensitive the scenario is to early purges.

- **Duration**:
  - scenario could be:
    - open-ended until a major crisis,
    - or limited to N ticks representing “one season.”

- **Role variants**:
  - simple variant: same scenario, but role is a small **duke_house** cell:
    - less CI detail,
    - more direct ability to accept/reject escalation prompts.

- **Difficulty knobs**:
  - initial severity of guild/cartel activity,
  - initial CI posture in risky wards,
  - tolerance for false positives in Espionage Branch tradecraft.

---

## 9. Future Links

Likely follow-ups in `11_scenarios`:

- `S-0002_Crackdown_Choice`  
  - picks up when crisis triggers for Rumbling → Hard Crackdown / Fragmentation
    are near or crossing.

- `S-0003_War_for_the_Ring`  
  - OPEN_CONFLICT-era scenario focused on core ThreatSurfaces.

These can reference `S-0001` outcome tags for continuity, as described in
D-RUNTIME-0104.
