---
title: Scenario_Packaging_and_Metadata
doc_id: D-RUNTIME-0104
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-RUNTIME-0102        # Campaign_Milestone_and_Crisis_Triggers
  - D-RUNTIME-0103        # Scenario_Framing_and_Win_Loss_Conditions
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-WORLD-0003          # Ward_Evolution_and_Specialization_Dynamics
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-INFO-0014           # Security_Dashboards_and_Threat_Surfaces
  - D-INFO-0015           # Operator_Alerts_and_Escalation_Prompts
---

# 02_runtime · Scenario Packaging and Metadata (D-RUNTIME-0104)

## 1. Purpose

This document defines how **scenarios and campaigns are organized** into
packages, with metadata that supports:

- discovery and selection in a UI,
- automated testing and sweeps,
- long-term narrative arcs (e.g. the Sting Wave cycle),
- modding / extension without breaking core assumptions.

It layers on top of:

- core runtime and timebase (D-RUNTIME-0001),
- campaign phases and triggers (D-RUNTIME-0102),
- scenario framing and win/loss conditions (D-RUNTIME-0103),
- world, MIL, IND, and INFO structures.

---

## 2. Scenario Package Concept

A **scenario package** is a collection of related scenarios, along with shared:

- lore and narrative framing,
- recommended play order,
- difficulty progression,
- cross-scenario continuity hooks (e.g. “if Scenario A ends in Bitter Order,
  Scenario B starts in Hard Crackdown”).

We distinguish:

- **Single scenarios** – atomic units that can be played alone.
- **Scenario chains** – ordered sequences with optional branching.
- **Campaign bundles** – larger collections that share a theme and time period.

---

## 3. Scenario Metadata Schema

We define per-scenario metadata, complementing D-RUNTIME-0103:

```yaml
ScenarioMetadata:
  id: string
  title: string
  short_label: string
  description: string
  tags:
    - "sting_wave"
    - "guild_ascendancy"
    - "tutorial"
    - "high_complexity"
  estimated_length_ticks: int | null
  recommended_order_index: int | null
  difficulty_rating: int              # 1–5 rough heuristic
  role_focus:
    - "duke_house"
    - "espionage_branch"
    - "mil_command"
    - "guild_faction"
  visibility_profile_hint: string
  control_profile_hint: string
  recommended_for_first_time: bool
  canon_status: "core" | "alt" | "experimental"
```

This sits next to or wrapped around the `ScenarioDefinition` body.

---

## 4. Scenario Package Schema

We define a top-level package:

```yaml
ScenarioPackage:
  id: string
  title: string
  description: string
  theme_tags:
    - "sting_wave_cycle"
    - "pre_collapse"
    - "guild_ascendancy"
  default_start_state_ref: string | null   # optional shared world snapshot
  scenarios:
    - PackageScenarioEntry
```

Where:

```yaml
PackageScenarioEntry:
  scenario_id: string                  # references ScenarioDefinition/Metadata
  recommended_order_index: int | null
  required_prior_scenarios:
    - string                           # scenario ids that should be played first
  unlock_conditions:
    # simple example; can be expanded later
    requires_campaign_phase_in:
      - "RUMBLING_UNREST"
      - "HARD_CRACKDOWN"
    requires_outcome_tags:
      - "regime_survives"
      - "rebels_defeated"
```

Packages can be used for:

- UI grouping,
- structured playthroughs,
- automated multi-run experiments.

---

## 5. Outcome Tags and Cross-Scenario Continuity

From D-RUNTIME-0103, each scenario end can produce **outcome tags**, e.g.:

- "regime_heroic_stability"
- "regime_bitter_order"
- "rebels_shadow_ascendancy"
- "mosaic_collapse"

We define a simple `ScenarioOutcomeSummary`:

```yaml
ScenarioOutcomeSummary:
  scenario_id: string
  outcome_label: string
  outcome_tags:
    - string
  end_campaign_phase: string
  end_tick: int
  key_metrics_snapshot_ref: string | null
```

Packages can refer to these in `unlock_conditions` to:

- choose which scenarios unlock,
- parameterize starting conditions for follow-ups (e.g. start from end snapshot).

---

## 6. Example Package: Sting Wave Cycle (Sketch)

```yaml
ScenarioPackage:
  id: "sting_wave_cycle"
  title: "Sting Wave Cycle"
  description: "A sequence of scenarios tracing Dosadi from pre-Sting tensions
    through the Sting Wave crisis and its aftermath."
  theme_tags:
    - "sting_wave"
    - "pre_collapse"
    - "high_complexity"
  default_start_state_ref: null
  scenarios:
    - scenario_id: "pre_sting_quiet_season"
      recommended_order_index: 1
      required_prior_scenarios: []
      unlock_conditions: {{}}
    - scenario_id: "crackdown_choice"
      recommended_order_index: 2
      required_prior_scenarios:
        - "pre_sting_quiet_season"
      unlock_conditions:
        requires_outcome_tags:
          - "regime_survives"
    - scenario_id: "war_for_the_ring"
      recommended_order_index: 3
      required_prior_scenarios:
        - "crackdown_choice"
      unlock_conditions:
        requires_campaign_phase_in:
          - "OPEN_CONFLICT"
```

Later, additional branches could be added for:

- guild-dominant Sting Wave paths,
- bishop-led civic settlements,
- deep Shadow takeover.

---

## 7. Testing and Simulation Sweeps

Scenario metadata is also useful for **non-player runs**:

- classification tags like "tutorial" or "experimental":
  - help CI/test harnesses decide what to run by default.

- difficulty and complexity tags:
  - help benchmark AI policies at different sophistication levels.

- theme tags:
  - help cluster scenarios for specific research questions:
    - e.g. "test robustness of regime survival policies across all
      pre_collapse scenarios."

We can define a simple `ScenarioTestConfig`:

```yaml
ScenarioTestConfig:
  package_id: string | null
  scenario_ids:
    - string
  num_runs_per_scenario: int
  random_seed_strategy: "fixed" | "sweep"
  policy_profile_ref: string | null
```

---

## 8. Modding and Extension

To allow external contributors or future you to add content without breaking
core assumptions:

- Treat:
  - doc_ids as stable core specification anchors,
  - scenario_ids and package_ids as stable within a given major version.

- Encourage new content to:
  - depend on core docs (AGENT, WORLD, IND, MIL, INFO, LAW, RUNTIME),
  - avoid redefining core mechanics in scenario-local ways.

Suggested guidelines:

- New scenarios should:
  - clearly label canon status: "core", "alt", or "experimental".
  - avoid assuming unique outcomes (e.g. "Sting Wave definitely happens").

- New packages:
  - can re-order or remix scenarios,
  - but should document their specific **continuity assumptions**.

---

## 9. Implementation Sketch (Non-Normative)

1. **File organization**

   - `docs/latest/02_runtime/scenarios/`:
     - `S-<id>_Scenario_<name>.yaml` or `.json`
   - `docs/latest/02_runtime/packages/`:
     - `P-<id>_Package_<name>.yaml`

2. **Loading sequence**

   - Load all ScenarioDefinitions and ScenarioMetadata.
   - Load all ScenarioPackages and validate references.
   - Build:
     - indices by tag, difficulty, role_focus,
     - dependency graphs for package sequences.

3. **UI integration**

   - Provide:
     - "Play random single scenario" menus,
     - "Play package/campaign" menus with recommended order,
     - filters by tag, role, complexity.

4. **Run-time integration**

   - At scenario end:
     - generate ScenarioOutcomeSummary,
     - update any package-level continuity state.

---

## 10. Future Extensions

Potential follow-ups:

- Scenario and package **versioning and compatibility** management:
  - how older scenarios adapt to updated core mechanics.

- Tools for:
  - automatically generating "mirror" scenarios (e.g. play same period from
    guild vs MIL vs Espionage perspective),
  - based on shared ScenarioDefinition and different RoleConfigs.
