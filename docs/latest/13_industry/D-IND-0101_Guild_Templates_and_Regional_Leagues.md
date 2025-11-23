---
title: Guild_Templates_and_Regional_Leagues
doc_id: D-IND-0101
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-IND-0001            # Industry_Taxonomy_and_Types
  - D-IND-0002            # Industry_Suitability_and_Evolution
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 13_industry · Guild Templates and Regional Leagues (D-IND-0101)

## 1. Purpose

This document provides a set of **reusable guild templates** and **regional league
patterns** for Dosadi's industrial landscape.

It is a **bridge** between:

- Abstract guild logic (D-IND-0001/0002/0003),
- Ward attributes (D-WORLD-0002),
- Economy and black markets (D-ECON-*),
- Military posture (D-MIL-0002),
- Law and sanctions (D-LAW-*),
- And the occupations that populate guild spaces (D-AGENT-0101).

Goals:

- Offer a compact library of **guild archetypes** (suits, fabrication, water,
  energy, food, info-support, etc.).
- Show **typical ward footprints** and power relations for each archetype.
- Define **regional leagues** (multi-ward configurations of allied or rival
  guilds).
- Provide hooks for scenario authors and simulation code to **instantiate
  plausible industrial-political ecosystems** without hardcoding a single map.

This is not exhaustive or prescriptive; it is a set of **patterns** that can be
combined, twisted, or subverted.

---

## 2. Guild Archetype Template

Each guild archetype is described using the following schema:

```yaml
GuildArchetype:
  id: string
  label: string
  industry_focus:
    primary:
      - string   # keys from D-IND-0001 taxonomy
    secondary:
      - string
  typical_wards:
    - "outer_industrial_bastion"
    - "hinge_interface"
    - "inner_sealed_core"
  power_profile:
    capital_intensity: "low" | "medium" | "high"
    labour_intensity: "low" | "medium" | "high"
    criticality_to_regime: "low" | "medium" | "high"
  default_stance_toward_branches:
    duke_house: "depend" | "bargain" | "resist"
    militia: "cooperate" | "tolerate" | "avoid" | "subvert"
    bishop_guild: "ally" | "compete" | "ignore"
    central_audit_guild: "placate" | "game" | "fear"
    cartel: "partner" | "parasite_target" | "rival" | "infiltrated"
  escalation_style:
    strike_risk: "low" | "medium" | "high"
    sabotage_risk: "low" | "medium" | "high"
    preferred_pressure_tactics:
      - "slowdown"
      - "withhold_repairs"
      - "threaten_shutdown"
  rumor_signature_tags:
    - "accident_prone"
    - "safety_scandals"
    - "elite_favoritism"
```

Scenarios can treat these archetypes as **families** which specific named guilds
instantiate (e.g. "Brine Chain Fabricators" as a variant of FABRICATION-MECH).

---

## 3. Core Guild Archetypes

### 3.1 SUITS Guild Archetype

```yaml
GuildArchetype:
  id: "SUITS_CORE"
  label: "Suit Fabrication and Maintenance Houses"
  industry_focus:
    primary: ["SUITS_FABRICATION", "SUITS_MAINTENANCE"]
    secondary: ["MATERIALS_HIGH_GRADE", "MICROFLUIDICS"]
  typical_wards:
    - "outer_industrial_bastion"
    - "hinge_interface"
    - "inner_sealed_core"
  power_profile:
    capital_intensity: "high"
    labour_intensity: "medium"
    criticality_to_regime: "high"
  default_stance_toward_branches:
    duke_house: "bargain"      # indispensable technical partners
    militia: "cooperate"       # supply and maintain exo gear
    bishop_guild: "ally"       # suits tied to safe work in civic spaces
    central_audit_guild: "game"
    cartel: "partner"          # clandestine mods, off-ledger parts
  escalation_style:
    strike_risk: "medium"
    sabotage_risk: "medium"
    preferred_pressure_tactics:
      - "withhold_repairs"
      - "slow_maintenance_cycles"
      - "prioritize_favored_clients"
  rumor_signature_tags:
    - "ghost_mods"
    - "favored_suits"
    - "safety_cut_corners"
```

Notes:

- In outer bastions, SUITS houses are tightly interwoven with exo-bays (D-MIL-0002).
- In cores, they pivot to **elite life-support and sealed suit lines** for nobles.
- The cartel leverages SUITS guilds for **unlogged mods** and access to heavy kit.

### 3.2 FABRICATION-MECH Guild Archetype

```yaml
GuildArchetype:
  id: "FABRICATION_MECH"
  label: "Mechanical Fabrication Yards"
  industry_focus:
    primary: ["FABRICATION_HEAVY", "TOOLS", "SPARES"]
    secondary: ["METALS_RECYCLING", "SCRAP_SORTING"]
  typical_wards:
    - "outer_industrial_bastion"
    - "hinge_interface"
  power_profile:
    capital_intensity: "medium"
    labour_intensity: "high"
    criticality_to_regime: "high"
  default_stance_toward_branches:
    duke_house: "bargain"
    militia: "cooperate"
    bishop_guild: "compete"
    central_audit_guild: "placate"
    cartel: "parasite_target"
  escalation_style:
    strike_risk: "high"
    sabotage_risk: "high"
    preferred_pressure_tactics:
      - "equipment_slowdown"
      - "selective_breakage"
      - "refuse_high_risk_jobs"
  rumor_signature_tags:
    - "yard_fires"
    - "crushed_workers"
    - "quota_crackdowns"
```

Notes:

- These yards are the **muscle and bones** of infrastructure.
- High sabotage potential: "accidents" that halt corridors or water flows.
- Cartels skim parts and tools; militia fear losing control of these facilities.

### 3.3 WATER-CONDENSATE Guild Archetype

```yaml
GuildArchetype:
  id: "WATER_CONDENSATE"
  label: "Condensate and Capture Consortia"
  industry_focus:
    primary: ["WATER_CONDENSATE_SYSTEMS", "DEHUMIDIFIER_NETWORKS"]
    secondary: ["FILTER_MEDIA", "PIPEWORK_LOCAL"]
  typical_wards:
    - "hinge_interface"
    - "inner_sealed_core"
    - "select_outer_collection_nodes"
  power_profile:
    capital_intensity: "high"
    labour_intensity: "medium"
    criticality_to_regime: "very_high"
  default_stance_toward_branches:
    duke_house: "depend"
    militia: "cooperate"
    bishop_guild: "ally"
    central_audit_guild: "fear"
    cartel: "partner"
  escalation_style:
    strike_risk: "medium"
    sabotage_risk: "very_high"
    preferred_pressure_tactics:
      - "maintenance_slowdown"
      - "unexplained_efficiency_loss"
      - "quiet_failure_in_high_status_wards"
  rumor_signature_tags:
    - "secret_taps"
    - "invisible_leaks"
    - "elite_wards_drink_first"
```

Notes:

- These guilds manage **air-to-water lifelines**; any slowdown is existential.
- They are closely watched by audits, but also seduced by cartels and nobles.

### 3.4 FOOD-BIOMASS Guild Archetype

```yaml
GuildArchetype:
  id: "FOOD_BIOMASS"
  label: "Biomass, Food, and Feed Operators"
  industry_focus:
    primary: ["FOOD_PRODUCTION", "BIO_MASS_PROCESSING"]
    secondary: ["WASTE_TO_FOOD", "NUTRIENT_RECYCLING"]
  typical_wards:
    - "outer_industrial_bastion"
    - "reserve_overflow"
    - "civic_support_hubs"
  power_profile:
    capital_intensity: "medium"
    labour_intensity: "medium"
    criticality_to_regime: "high"
  default_stance_toward_branches:
    duke_house: "depend"
    militia: "cooperate"
    bishop_guild: "ally"
    central_audit_guild: "placate"
    cartel: "partner"
  escalation_style:
    strike_risk: "medium"
    sabotage_risk: "medium"
    preferred_pressure_tactics:
      - "quality_drift"
      - "quiet_dilution"
      - "selective_shortages"
  rumor_signature_tags:
    - "ration_dilution"
    - "tainted_vats"
    - "favored_canteens"
```

Notes:

- Food guilds and bishop_guild co-govern survival.
- Cartels use them for **off-ledger food** and priority access.

### 3.5 ENERGY-MOTION Guild Archetype

```yaml
GuildArchetype:
  id: "ENERGY_MOTION"
  label: "Energy and Motion Systems Syndicates"
  industry_focus:
    primary: ["ENERGY_DISTRIBUTION", "MOTION_SYSTEMS"]
    secondary: ["LIFT_SYSTEMS", "PUMP_FARMS"]
  typical_wards:
    - "outer_industrial_bastion"
    - "hinge_interface"
  power_profile:
    capital_intensity: "high"
    labour_intensity: "medium"
    criticality_to_regime: "high"
  default_stance_toward_branches:
    duke_house: "bargain"
    militia: "cooperate"
    bishop_guild: "ignore"
    central_audit_guild: "game"
    cartel: "parasite_target"
  escalation_style:
    strike_risk: "low"
    sabotage_risk: "high"
    preferred_pressure_tactics:
      - "targeted_outages"
      - "elevator_failures"
      - "pressure_spikes"
  rumor_signature_tags:
    - "lights_go_dark"
    - "stuck_lifts"
    - "silent_pumps"
```

### 3.6 INFO-SUPPORT Guild Archetype

```yaml
GuildArchetype:
  id: "INFO_SUPPORT"
  label: "Clerical, Telemetry, and Record Houses"
  industry_focus:
    primary: ["INFO_CLERICAL", "TELEMETRY_MAINTENANCE"]
    secondary: ["DEVICE_MAINTENANCE", "SMALL_ELECTRONICS"]
  typical_wards:
    - "inner_sealed_core"
    - "hinge_interface"
  power_profile:
    capital_intensity: "medium"
    labour_intensity: "medium"
    criticality_to_regime: "medium"
  default_stance_toward_branches:
    duke_house: "depend"
    militia: "cooperate"
    bishop_guild: "ally"
    central_audit_guild: "cooperate"
    cartel: "infiltrated"
  escalation_style:
    strike_risk: "low"
    sabotage_risk: "medium"
    preferred_pressure_tactics:
      - "data_delays"
      - "selective_blindness"
      - "record_ambiguity"
  rumor_signature_tags:
    - "lost_records"
    - "forged_reports"
    - "ghost_entries"
```

---

## 4. Regional League Patterns

A **regional league** is a multi-ward configuration where several guilds dominate
and coordinate (or clash) across space.

### 4.1 Industrial Spine League

Pattern:

- A line or arc of **outer_industrial_bastion** wards, each hosting:
  - FABRICATION-MECH,
  - SUITS_CORE,
  - ENERGY-MOTION guilds.

Features:

- High `garrison_presence` and `exo_bay_density` (D-MIL-0002).
- Strong `guild_power(w, F)` for FABRICATION and SUITS families.
- Vulnerable to:
  - Coordinated guild slowdowns,
  - Cartel skimming of critical parts,
  - Law regimes using **martial states** to keep production running.

Use in scenarios:

- Backbone that keeps the city physically functioning.
- If disrupted, ripples through water flows, food logistics, and movement.

### 4.2 Water Crown League

Pattern:

- Cluster of hinge/core wards centered on major condensate operations.
- Dominated by WATER-CONDENSATE guilds and aligned bishops.

Features:

- High `criticality_to_regime`; regime is reluctant to overtly punish them.
- Strong overlap with bishop_guild civic infrastructure.
- Frequent conflict with:
  - central_audit_guild (over leaks and skims),
  - cartels offering alternative channels.

Use in scenarios:

- Strategic prize in political struggles.
- Guild or bishop riots here are regime nightmares.

### 4.3 Civic Feed League

Pattern:

- Chain of wards with dense habitation, bunkhouses, and canteens.
- FOOD-BIOMASS and bishop_guild share influence, sometimes with small
  WATER-CONDENSATE or INFO-SUPPORT guild partners.

Features:

- High `rumor_density` and `gossip_hub_intensity`.
- Sanctions in these wards (ration cuts, curfews) immediately shift:
  - `unrest_index(w)`,
  - `loyalty_to_regime(w)`,
  - demand for black market food.

Use in scenarios:

- Engine for **popular sentiment** shifts.
- Target for both regime crackdowns and cartel “welfare programs.”

### 4.4 Lift Ring League

Pattern:

- Set of hinge/choke wards that host major lifts and motion systems.
- ENERGY-MOTION guilds dominate, with INFO-SUPPORT assisting.

Features:

- High `corridor_centrality` and checkpoint density.
- Control over movement of:
  - barrels,
  - exo units,
  - elites and their entourages.

Use in scenarios:

- Strategic target for coups, sabotage arcs, or cartel infiltration.
- Laws and curfews here often framed as “safety” measures.

### 4.5 Shadow League (Cartel-Heavy)

Pattern:

- Not a formal league but an emergent one where:
  - Black market intensity is high,
  - Guilds are fragmented or weak,
  - Cartels fill gaps in supply and justice.

Features:

- High `informal_resolution_rate` (D-LAW-0002) and low due process.
- Guilds may be parasitized or partially captured.
- Rumor networks heavily mediated by cartel-linked nodes.

Use in scenarios:

- Fertile ground for clandestine missions, assassinations, or covert alliances.
- Often sits between stronger leagues as a buffer or sponge.

---

## 5. Hooks into Simulation and Scenario Design

### 5.1 Instantiating guilds from templates

Implementation can:

1. Choose a subset of guild archetypes to be present in a scenario.
2. For each archetype, roll:
   - Number of instances,
   - Wards they anchor in (respecting `typical_wards` and worldgen).
3. Assign each instance:
   - Slightly varied stances toward branches,
   - Localization of rumor tags and escalation styles.

### 5.2 Using leagues to shape arcs

Scenario authors can:

- Declare that a given scenario takes place in:
  - An Industrial Spine region,
  - On the edge of a Water Crown,
  - Inside a Civic Feed League under stress.

- Use this to:
  - Bias which incidents fire (industrial accidents vs food riots),
  - Choose likely sanction patterns,
  - Pick rumor templates that feel grounded.

### 5.3 Evolution over time

Leagues and guild archetype dominance can **change**:

- Prolonged sanctions, strikes, or sabotage can:
  - Reduce a guild's `G_power(w, F)` (D-IND-0003),
  - Open space for rival guilds or cartels.

- Regime policy shifts (favoring certain guilds) can:
  - Create new leagues,
  - Collapse others.

A future D-WORLD or IND doc may formalize **ward evolution rules** that
use these templates as targets or attractors.

---

## 6. Future Extensions

Likely follow-ups:

- `D-IND-0102_Named_Guilds_and_Internal_Factions`
  - Specific guild names, cultures, and factional splits derived from the
    archetypes here.

- `D-WORLD-0003_Ward_Evolution_and_Specialization_Dynamics`
  - How guild presence, law, MIL posture, and economy jointly drive ward
    evolution across longer timelines.

- Scenario-specific league briefs
  - Mini-docs describing the industrial and political map for major arcs
    (e.g. Sting Wave scenarios, regime transitions).
