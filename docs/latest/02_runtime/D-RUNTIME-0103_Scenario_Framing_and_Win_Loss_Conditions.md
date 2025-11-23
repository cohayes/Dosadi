---
title: Scenario_Framing_and_Win_Loss_Conditions
doc_id: D-RUNTIME-0103
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-RUNTIME-0102        # Campaign_Milestone_and_Crisis_Triggers
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

# 02_runtime · Scenario Framing and Win/Loss Conditions (D-RUNTIME-0103)

## 1. Purpose

This document defines how **scenarios** are framed on top of the Dosadi
simulation and campaign systems, and how **win/loss conditions** are expressed.

It provides:

- A standard schema for **scenario definitions**.
- Ways to bind:
  - initial world/campaign setup,
  - role and visibility constraints,
  - objectives (win/loss),
  - special rules or event scripts.
- Patterns for using:
  - campaign phases (D-RUNTIME-0102),
  - dashboards and threat surfaces (D-INFO-0014),
  - alerts and prompts (D-INFO-0015),
  - MIL/LAW/INFO dynamics

to create playable arcs and testable simulations.

---

## 2. Scenario Concept

A **scenario** is a packaged slice of Dosadi with:

- A **starting configuration**:
  - world/ward attributes,
  - guild and MIL positions,
  - campaign phase.
- One or more **roles**:
  - which actor(s) the player or AI inhabits (duke, Espionage, MIL, guild,
    outsider).
- A set of **objectives**:
  - conditions that define success, failure, or graded outcomes.
- Optional **special rules**:
  - modified triggers and modifiers,
  - scripted events or constraints.

Scenarios can be:

- Short, tactical one-offs (single ward or corridor),
- Operational (multi-ward, limited time),
- Full-campaign arcs (entire system over long time).

---

## 3. Scenario Definition Schema

```yaml
ScenarioDefinition:
  id: string
  name: string
  description: string
  starting_campaign_phase: string         # e.g. "STABLE_CONTROL", "RUMBLING_UNREST"
  starting_tick: int                      # usually 0 for standalone runs
  duration_limit_ticks: int | null        # optional time limit
  starting_state_ref: string | null       # reference to a saved world/campaign snapshot
  world_overrides:                        # optional patch to base worldgen
    ward_overrides:
      - ward_id: string
        attributes_patch: object
  role_configs:
    - RoleConfig
  objectives:
    primary: 
      - Objective
    secondary:
      - Objective
    forbidden:
      - Objective
  special_rules:
    trigger_tuning_ref: string | null
    hard_constraints:
      - "no_use_of_mass_purges"
      - "cannot_declare_martial_law_globally"
    scripted_events_ref: string | null
```

Where:

```yaml
RoleConfig:
  role_id: string
  actor_type: "duke_house" | "espionage_branch" | "mil_command" | "law_apparatus" | "guild_faction" | "cartel" | "outsider"
  visibility_profile: string         # maps to dashboards/indices visible
  control_profile: string            # what levers can be pulled
  ai_or_player: "player" | "ai"
  ai_personality_ref: string | null
```

---

## 4. Objective Model

Objectives are expressed in terms of:

- **State conditions** on:
  - campaign phase and indices,
  - ward-level indices,
  - control of ThreatSurfaces,
  - factional status (guild charters, MIL loyalty, LAW behavior).

- **Event counts or sequences**:
  - number of purges, mutinies, strikes,
  - specific crisis triggers fired or avoided.

```yaml
Objective:
  id: string
  label: string
  type: "state" | "event" | "compound"
  success_condition:
    # examples below
  failure_condition:
    # optional, or handled by forbidden objectives
  priority: "primary" | "secondary"
  scoring_weight: float
```

### 4.1 Example state objective conditions

```yaml
success_condition:
  kind: "state"
  constraints:
    campaign_phase_in:
      - "STABLE_CONTROL"
      - "RUMBLING_UNREST"
    max_global_stress_index: 0.5
    max_unrest_high_ward_fraction: 0.3
    max_fragmentation_index: 0.4
    min_regime_legitimacy_index: 0.4
```

### 4.2 Example event objective conditions

```yaml
success_condition:
  kind: "event"
  constraints:
    required_events:
      - "guild_strike_resolved_without_purge"
    max_events:
      mutiny_events: 1
      open_conflict_transitions: 0
```

### 4.3 Compound objectives

```yaml
success_condition:
  kind: "compound"
  logic: "AND"
  subconditions:
    - {{ ref: "keep_core_stable" }}
    - {{ ref: "limit_purge_intensity" }}
    - {{ ref: "prevent_open_conflict" }}
```

---

## 5. Role, Visibility, and Control Profiles

Scenarios can **feel very different** depending on who you are and what you see.

### 5.1 Visibility profiles

Examples:

- `ducal_view`:
  - Global Security Overview with filtered CI detail,
  - high-level LAW and ECON summaries.

- `espionage_view`:
  - CI/Infiltration Panel rich,
  - partial access to MIL Stability Panel,
  - some LAW and Rumor views.

- `mil_ward_view`:
  - local WardSecuritySummary,
  - detailed GarrisonState, discipline, and LAW impacts for that ward,
  - limited CI suspicion.

- `guild_security_view`:
  - partial WORLD/IND/ECON flows,
  - local black market intensity and rumor patterns,
  - inferred MIL/LAW behavior from outcomes.

### 5.2 Control profiles

Examples:

- `ducal_control`:
  - can accept/reject high-level escalation prompts,
  - appoint/rotate some commanders, authorize purge campaigns,
  - tweak CI posture and LAW defaults.

- `espionage_control`:
  - run CI operations, stings, and investigations,
  - recommend purges, push narrative ops.

- `mil_regional_control`:
  - set alert levels,
  - order redeployments, crackdowns, or restraint,
  - request or reject special detachments.

- `guild_control`:
  - call strikes/slowdowns/sabotage,
  - negotiate or break bargains,
  - bribe/infiltrate MIL/LAW nodes.

---

## 6. Win/Loss Patterns

Rather than single binary outcomes, we support **graded results**:

1. **Regime Survival Spectrum** (for ducal/central roles)
   - Heroic Stability: regime keeps control with relatively low repression.
   - Bitter Order: regime survives but with high repression and low legitimacy.
   - Pyrrhic Survival: regime “wins” but with shattered economy/wards.

2. **Rebel/Guild Success Spectrum**
   - Shadow Ascendancy: guild/cartel dominance from the shadows.
   - Civic/Bishop Ascendancy: more “civilian” local order replaces MIL/ducal control.
   - Failed Revolt: uprising crushed; future runs may start from Hard Crackdown.

3. **System Collapse Spectrum**
   - Mosaic Collapse: fragmented authorities, persistent low-grade warfare.
   - Flash Collapse: brief, violent civil war, then new regime or stalemate.

These patterns can be encoded as **objective sets** and mapped to narrative
epilogues.

---

## 7. Example Scenario Skeletons

### 7.1 “Pre-Sting Wave: The Quiet Season”

- Focus: early RUMBLING_UNREST phase in select wards.
- Role: Espionage Branch analyst or small duke-house staff cell.
- Objectives:
  - prevent regime from sliding into Hard Crackdown too early,
  - keep global_stress_index under threshold for N ticks,
  - avoid major mutinies/open conflicts.

Special rules:

- some crisis triggers have higher thresholds,
- player’s choices push or delay RUMBLING → HARD_CRACKDOWN.

---

### 7.2 “The Crackdown Choice”

- Start phase: RUMBLING_UNREST, near threshold.
- Role: duke_house or central regime cluster.
- Objectives:
  - decide between Hard Crackdown vs Fragmented Regime paths,
  - maintain control of core ThreatSurfaces,
  - limit MIL fracture risk.

Special rules:

- scenario ends when:
  - phase becomes HARD_CRACKDOWN or FRAGMENTED_REGIME,
  - scoring based on severity of repression vs fragmentation.

---

### 7.3 “Open Conflict: War for the Ring”

- Start phase: OPEN_CONFLICT.
- Roles: multiple (regime, rebel coalition, key guild).
- Objectives:
  - regime: retain majority of Lift Ring and core barrels,
  - rebels: control designated ThreatSurfaces for K ticks,
  - guild: ensure survival of specific industrial nodes.

Special rules:

- many crisis triggers disabled (already in major crisis),
- campaign phase may snap to SETTLEMENT_OR_RESET when win/loss achieved.

---

## 8. Scenario Hooks to Campaign Phases

Scenarios can be attached to **phase entry** or **phase presence**:

- “When campaign enters RUMBLING_UNREST, enable scenario seeds A and B.”
- “While in HARD_CRACKDOWN, some player options are disabled or altered.”
- “If campaign flips to FRAGMENTED_REGIME while this scenario is active,
   branch to alternative objective set.”

This allows:

- nested scenarios inside a larger campaign,
- or stand-alone scenarios that **emulate** particular campaign phases.

---

## 9. Implementation Sketch (Non-Normative)

1. **Scenario loading**:

   - Load ScenarioDefinition (YAML or similar).
   - Apply `starting_state_ref` or worldgen + world_overrides.
   - Set CampaignState to `starting_campaign_phase`.

2. **Role setup**:

   - Instantiate RoleConfigs:
     - visibility and control profiles,
     - assign player/AI.

3. **Objective tracking**:

   - At each macro-step, evaluate objective conditions.
   - Track partial progress, successes, and failures.

4. **Integration with CampaignState**:

   - CampaignState evolves per D-RUNTIME-0102.
   - Scenario may:
     - override or tune certain CrisisTriggers,
     - listen to phase transitions as events.

5. **Scenario end and scoring**:

   - End conditions:
     - time limit reached,
     - win/loss conditions met,
     - external triggers (e.g., phase → SETTLEMENT_OR_RESET).
   - Compute:
     - objective satisfaction,
     - map to outcome label + epilogue data.

---

## 10. Future Extensions

Potential follow-ups:

- `D-RUNTIME-0104_Scenario_Packaging_and_Metadata`
  - Naming, tagging, and organizing multiple scenarios/campaigns.

- Scenario collections:
  - “Sting Wave Cycle,”
  - “Guild Ascendancy Stories,”
  - “Collapse and Reconstruction Paths.”
