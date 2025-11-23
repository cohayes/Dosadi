---
title: Campaign_Milestone_and_Crisis_Triggers
doc_id: D-RUNTIME-0102
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-RUNTIME-0001        # Simulation_Timebase
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

# 02_runtime · Campaign Milestone and Crisis Triggers (D-RUNTIME-0102)

## 1. Purpose

This document defines a **campaign-level layer** that sits above the tick-by-tick
simulation:

- **Campaign milestones** – coarse states that describe the political and
  security phase of Dosadi during a run (e.g., Stable Control, Rumbling, Open
  Crackdown, Fragmented Regime).
- **Crisis triggers** – conditions under which the campaign shifts from one
  milestone to another (coups, rebellions, purge waves, negotiated resets).

It connects:

- Low-level indices and dashboards (D-INFO-0014, D-INFO-0015),
- MIL and LAW behavior (D-MIL-*, D-LAW-*),
- WORLD/IND/ECON metrics,

into a simple campaign state machine that scenarios and AI controllers can use
to shape arcs, win/loss conditions, and narrative beats.

---

## 2. Conceptual Overview

We distinguish:

- **Simulation time** (ticks and phases, D-RUNTIME-0001):
  - fine-grained updates to wards, agents, flows.

- **Campaign phases**:
  - coarser periods where:
    - institutions behave differently,
    - available actions and scenarios change.

The campaign system:

- Periodically samples system-wide metrics,
- Evaluates **transition conditions**,
- Advances the campaign phase when crisis triggers fire,
- Optionally spawns scripted or semi-scripted events.

---

## 3. Campaign State Model

We define a simple core campaign state:

```yaml
CampaignState:
  phase: string                    # e.g. "stable_control", "rumbling", "hard_crackdown"
  phase_tick_started: int
  phase_history:
    - phase: string
      start_tick: int
      end_tick: int
      trigger_event_id: string | null
  global_stress_index: float       # 0–1
  regime_legitimacy_index: float   # 0–1
  fragmentation_index: float       # 0–1   # how many power centers de facto
  crisis_flags:
    - "rebellion_risk_high"
    - "coup_risk_high"
    - "collapse_risk_high"
  active_scenarios:
    - string                       # scenario ids or tags
```

Phase is a **label** with associated behavior modifiers.

---

## 4. Example Campaign Phases

These are suggested baseline phases; scenarios can reuse or customize them.

1. **STABLE_CONTROL**
   - Low to moderate unrest,
   - Regime institutions mostly coherent,
   - MIL fractures containable, CI posture mixed.

2. **RUMBLING_UNREST**
   - Multiple wards in high threat and unrest,
   - strikes, sabotage, and rumors escalating,
   - regime still nominally in charge.

3. **HARD_CRACKDOWN**
   - Widespread curfews and emergency decrees,
   - purge campaigns active across multiple wards,
   - high repression and high fracture risk.

4. **FRAGMENTED_REGIME**
   - Some wards effectively under guild/cartel/bishop control,
   - MIL and LAW split along factional lines,
   - dukes and their rivals run overlapping authorities.

5. **OPEN_CONFLICT**
   - Open rebellion, civil war, or coup attempt,
   - regime survival genuinely at stake.

6. **SETTLEMENT_OR_RESET**
   - Post-conflict phase:
     - negotiated truce,
     - new regime consolidation,
     - or shattered stalemate.

Each phase can adjust:

- default CI posture ranges,
- typical MIL alert responses,
- how LAW behaves (strict vs paralyzed),
- what actions are available to player/AI.

---

## 5. Global Indices

To drive transitions, we maintain coarse global indices derived from ward-level
and subsystem metrics:

```yaml
GlobalSecurityMetrics:
  unrest_mean: float
  unrest_high_ward_fraction: float
  repression_mean: float
  garrison_fracture_mean: float
  garrison_fracture_hotspot_count: int
  infiltration_risk_mean: float
  ci_posture_mean: float
  black_market_intensity_mean: float
  law_opacity_mean: float
  rumor_volatility_mean: float
  purge_intensity_index: float      # from purge events and LAW stats
```

From these, we compute:

- `global_stress_index` – combined measure of unrest, fracture, infiltration.
- `regime_legitimacy_index` – inverse of:
  - law opacity,
  - arbitrary sanctions,
  - heavy rumor of regime betrayal.
- `fragmentation_index` – based on:
  - how many wards have de facto non-regime control,
  - divergence in MIL doctrine and alignment across wards.

---

## 6. Crisis Triggers

Crisis triggers are conditions that, when met, propose a **campaign phase
transition**. Each trigger has:

```yaml
CrisisTrigger:
  id: string
  from_phases:
    - string
  to_phase: string
  condition:
    type: "metric" | "event_combo"
  metric_thresholds:
    global_stress_min: float | null
    unrest_high_ward_fraction_min: float | null
    garrison_fracture_hotspot_min: int | null
    purge_intensity_min: float | null
    fragmentation_min: float | null
  event_requirements:
    - "mutiny_in_core_ward"
    - "failed_coup_attempt"
    - "general_guild_strike"
  cooldown_ticks: int
  auto_fire: bool                  # true = transitions automatically, false = needs decision
```

Examples below.

---

## 7. Example Triggers and Transitions

### 7.1 Stable → Rumbling

**Trigger:** “RUMBLING_THRESHOLD_REACHED”

- from_phases: ["STABLE_CONTROL"]
- to_phase: "RUMBLING_UNREST"
- condition:
  - unrest_high_ward_fraction_min ≈ 0.2–0.3,
  - rumor_volatility_mean above threshold,
  - garrison_fracture_hotspot_min ≥ 1.

Interpretation:

- Enough wards are restive that status quo politics is no longer sufficient.

Effect:

- Increase baseline CI posture in some wards,
- more aggressive use of LAW tools suggested via D-INFO-0015 prompts,
- unlock scenarios centered on strikes, riots, and local purges.

---

### 7.2 Rumbling → Hard Crackdown

**Trigger:** “REPRESSIVE_PIVOT”

- from_phases: ["RUMBLING_UNREST"]
- to_phase: "HARD_CRACKDOWN"
- condition:
  - unrest_high_ward_fraction_min high,
  - regime_legitimacy_index already depressed,
  - Duke-house operator accepts escalation prompts favoring MIL/LAW tracks.

Effect:

- Legal defaults:
  - curfews more common,
  - tribunals faster and harsher.

- MIL defaults:
  - more Hardline and Zealot appointments in rotations,
  - more frequent purges.

- Campaign risk:
  - global_stress_index rises,
  - garrison_fracture_mean grows.

---

### 7.3 Rumbling → Fragmented Regime

**Trigger:** “AUTHORITY_SLIP”

Alternative to Hard Crackdown.

- from_phases: ["RUMBLING_UNREST"]
- to_phase: "FRAGMENTED_REGIME"
- condition:
  - high fragmentation_index,
  - multiple wards flagged with:
    - de facto guild/cartel/bishop control,
  - duke-house chooses **restraint** or is paralyzed (declines major escalation).

Effect:

- MIL and LAW:
  - diverge behaviorally between wards,
  - some follow regime orders, others follow local power.

- INFO and CI:
  - struggle to maintain coherent picture,
  - dashboards show large variation and contradictory signals.

---

### 7.4 Hard Crackdown → Open Conflict

**Trigger:** “RESISTANCE_TIPS”

- from_phases: ["HARD_CRACKDOWN"]
- to_phase: "OPEN_CONFLICT"
- condition:
  - multiple large-scale mutinies or alignment switches (D-MIL-0105),
  - widespread guild/cartel backing of armed resistance,
  - one or more `ThreatSurface` objects identified as active rebellion vectors.

Effect:

- Wards split into factions:
  - regime vs rebels vs opportunists,
  - some MIL units switch sides.

- Scenario hooks:
  - open civil war arcs,
  - player/AI may choose faction.

---

### 7.5 Fragmented Regime → Open Conflict

**Trigger:** “FACTIONAL_COLLISION”

- from_phases: ["FRAGMENTED_REGIME"]
- to_phase: "OPEN_CONFLICT"
- condition:
  - fragmentation_index above high threshold,
  - Duke or major faction attempts consolidation by force (coup vector).

Effect:

- Regime vs rival duke or coalition,
- MIL and guild loyalties lock in for major actors.

---

### 7.6 Any → Settlement or Reset

**Trigger:** “NEGOTIATED_SETLEMENT” or “REGIME_REPLACEMENT”

- from_phases: ["RUMBLING_UNREST", "HARD_CRACKDOWN", "FRAGMENTED_REGIME", "OPEN_CONFLICT"]
- to_phase: "SETTLEMENT_OR_RESET"
- condition:
  - win/loss conditions met (scenario-specific),
  - e.g.:
    - rebels control majority of key ThreatSurfaces,
    - duke maintains majority control and suppresses rival centers.

Effect:

- Freeze or slow major MIL/LAW/CI dynamics,
- shift to:
  - reconstruction arcs,
  - or epilogue state.

---

## 8. Interaction with Alerts and Prompts

From D-INFO-0015:

- **SecurityAlerts** are micro-level:
  - “Fracture risk in Ward 12 garrison high.”

- **EscalationPrompts** are meso-level:
  - “Consider MIL crackdowns in Spine wards.”

- **CampaignState** is macro-level:
  - “We are now in HARD_CRACKDOWN phase.”

Flows:

1. Metrics and events → Alerts.
2. Clusters of alerts → EscalationPrompts.
3. Sequences of prompts accepted/ignored + metrics → CrisisTriggers.
4. CrisisTriggers → phase transitions.

This lets:

- AI agents (or player) shape campaign evolution via choices,
- yet still keeps hard structural constraints from metrics.

---

## 9. Effects of Campaign Phase on Systems

Each phase can apply **modifiers**:

```yaml
CampaignPhaseModifiers:
  phase: string
  mil_behavior_bias:
    doctrine_shift: { "HARDLINE": +0.2, "PATRONAGE": -0.1, "PROFESSIONAL": -0.1 }
    purge_frequency_multiplier: float
    alert_level_bias: int
  law_behavior_bias:
    tribunal_frequency_mult: float
    sanction_severity_bias: float
    curfew_default_prob: float
  ci_behavior_bias:
    ci_posture_bias: int
    tolerance_for_false_positives: float
  econ_behavior_bias:
    ration_cut_probability: float
    guild_charter_rewrite_tendency: float
  rumor_behavior_bias:
    fear_theme_weight: float
    revolt_theme_weight: float
```

These modifiers:

- Tilt the **probabilities of behavior** in underlying systems,
- without fully dictating outcomes (still stochastic and driven by local state).

---

## 10. Implementation Sketch (Non-Normative)

1. **Initialize CampaignState**:

   - Start phase typically "STABLE_CONTROL" or scenario-defined.
   - Set initial indices based on starting world.

2. **At each macro-step (e.g., every N ticks)**:

   - Compute GlobalSecurityMetrics from ward-level and subsystem data.
   - Update `global_stress_index`, `regime_legitimacy_index`,
     `fragmentation_index`.

3. **Evaluate CrisisTriggers**:

   - For all triggers whose `from_phases` includes current phase:
     - test metric thresholds and event requirements.
   - If `auto_fire`:
     - queue phase transition if conditions met and cooldown satisfied.
   - If not:
     - create EscalationPrompt offering phase shift via operator decision.

4. **Apply phase transitions**:

   - Update CampaignState history.
   - Apply new CampaignPhaseModifiers to subsystems.

5. **Expose to UI & scenarios**:

   - Show phase name and short description in dashboards.
   - Allow scenarios to:
     - hook specific content to phase transitions,
     - alter trigger thresholds or block transitions.

---

## 11. Future Extensions

Potential follow-ups:

- `D-RUNTIME-0103_Scenario_Framing_and_Win_Loss_Conditions`
  - Mapping campaign phases and triggers to concrete objectives and endings.

- Campaign presets:
  - “Slow Boil Collapse”,
  - “Paranoid Stability”,
  - “Short, Violent Revolt”,

each with different trigger tuning and modifier profiles.
