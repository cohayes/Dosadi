---
title: Tier3_Office_Sheets
doc_id: D-AGENT-0108
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-AGENT-0001       # Dosadi_Agent_Core
  - D-AGENT-0002       # Agent_Attributes_and_Skills (placeholder; adjust to actual)
  - D-AGENT-0105       # Drives_and_Facility_Impact (if present)
  - D-RUNTIME-0001     # Simulation_Timebase
  - D-RUNTIME-0103     # Scenario_Framing_and_Win_Loss_Conditions
  - D-RUNTIME-0105     # AI_Policy_Profiles
  - D-RUNTIME-0106     # Office_Precedent_and_Institutional_Memory
  - D-INFO-0001        # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003        # Information_Flows_and_Report_Credibility
  - D-INFO-0006        # Rumor_Networks_and_Informal_Channels
---

# 01_agents · Tier-3 Office Sheets (D-AGENT-0108)

## 1. Purpose

This document defines **Tier-3 office sheets** for major power seats in the
Dosadi system. Each office sheet describes:

- the **core goals** of that office,
- the **levers** it can pull in the simulation,
- the **signals** it sees via dashboards and reports,
- its typical **access** to archives and rumor networks, and
- baseline **learning/bias tendencies** that shape how incumbents use history
  (per D-RUNTIME-0105 and D-RUNTIME-0106).

These sheets do **not** describe individual characters (duke_042, bishop_017,
etc.) but the *chairs* they sit in. Individual agents instantiate these office
templates with their own attributes, skills, and personality profiles.

The intent is to support:

- autonomous long-run **campaigns** driven by Tier-3 decision-makers, and
- later, player-facing roles that map cleanly onto existing office interfaces.

---

## 2. Common Office Interface

All Tier-3 offices share a common structural interface, even if the content
differs.

### 2.1 Office metadata

```yaml
OfficeSheet:
  office_id: string           # e.g. "crown:king", "duchy:river_ring", "esp_branch:central"
  branch: string              # "crown", "ducal", "civic", "military", "espionage", "guild", "cartel"
  pillar: string              # primary design pillar: "law", "mil", "info", "ind", "econ", "world"
  description: string
```

### 2.2 Core goals

Each office has a small weighted set of **structural goals**. Individual
incumbents modify these via AiPolicyProfiles, but the office defines the
default.

```yaml
core_goals:
  survival_weight: float          # personal survival in-seat
  dynasty_weight: float           # continuity of house / line
  regime_stability_weight: float  # macro stability of the regime
  doctrine_weight: float          # adherence to ideology / charter / creed
  economic_weight: float          # prosperity of controlled domains
  prestige_weight: float          # honors, status, visible dominance
```

These correspond roughly to the value weights in `AiPolicyProfile`, but at the
**institutional** level rather than per-person idiosyncrasies.

### 2.3 Control levers

Each office has a set of **lever families** it is allowed to use. The exact
mechanics live in runtime / law / mil docs; here we list them so AI and
scenario design know what knobs exist.

```yaml
levers:
  # campaign-level
  campaign_decisions:            # e.g. accept_crackdown, seek_restraint, accept_fragmentation

  # force / security
  security_posture_controls:     # e.g. set_mil_alert_level, approve_purge_sweeps
  ci_posture_controls:           # e.g. set_ci_stance, expand_ci_mandate

  # appointments & patronage
  appointment_controls:          # e.g. appoint_duke, reassign_captain, promote_commissar
  charter_controls:              # e.g. grant_guild_charter, revoke_charter, modify_quota

  # economy / water / taxation
  resource_controls:             # e.g. adjust_barrel_cadence, set_tax_rate, allocate_relief

  # law & procedure
  law_intensity_controls:        # e.g. procedural_vs_draconian, set_summary_judgement_bands
```

V1 implementations may only wire a subset; the office sheet is the superset
contract.

### 2.4 Signals / dashboards

Each office sees a tailored view of world and campaign state.

```yaml
signals:
  global_indices:                # e.g. stress, legitimacy, fragmentation, entropy, water_security
  ward_metrics_view:             # which ward-level stats and at what granularity
  force_metrics_view:            # garrison readiness, morale, mutiny risk, etc.
  guild_cartel_view:             # charter stress, black-market intensity where relevant
  personal_risk_view:            # seat_risk, patron_satisfaction, threat_index
```

These tie directly to D-INFO-0014 (Security Dashboards) and related runtime
metrics.

### 2.5 Access & learning defaults

Office sheets define *default* ranges for access and learning/bias traits; each
incumbent samples within or near these ranges.

```yaml
access_defaults:
  archive_access_level: [min, max]      # 0–3
  rumor_circle_tags:                    # typical starting circles for this office

learning_defaults:
  learning_drive_range: [min, max]      # [0, 1]
  source_trust_archive_range: [min, max]
  source_trust_rumor_range: [min, max]
  bias_strength_range: [min, max]
  bias_style_biases:                    # e.g. ["zealous", "dogmatic"] or ["cynical", "opportunistic"]
```

---

## 3. Crown & Ducal Offices

### 3.1 Crown: King / Regent

```yaml
office_id: "crown:king"
branch: "crown"
pillar: "law"
description: >
  Supreme formal authority over Dosadi's regime. Controls appointments at the
  ducal level, high law, and key water/tax policies. Rarely touches ward-level
  details directly but exerts immense patronage pressure downward.

core_goals:
  survival_weight: 0.9
  dynasty_weight: 1.0
  regime_stability_weight: 0.8
  doctrine_weight: 0.5
  economic_weight: 0.6
  prestige_weight: 0.9

levers:
  campaign_decisions:
    - "accept_crackdown"
    - "seek_restraint"
    - "accept_fragmentation"      # as last resort or controlled decentralization
  security_posture_controls:
    - "set_global_mil_alert_band"
    - "authorize_nationwide_purges"   # broad limits, executed by MIL/CI
  ci_posture_controls:
    - "expand_or_restrict_ci_mandate"
  appointment_controls:
    - "appoint_or_dismiss_duke"
    - "appoint_bishop_guild_heads"
    - "shuffle_high_command"
  charter_controls:
    - "grant_or_revoke_guild_charter"
    - "set_ducal_quota_targets"
  resource_controls:
    - "adjust_realm_barrel_cadence"
    - "set_realm_tax_bands"
    - "declare_relief_or_siege_policy"
  law_intensity_controls:
    - "set_realm_law_intensity_band"  # procedural vs draconian defaults

signals:
  global_indices:
    - "global_stress_index"
    - "regime_legitimacy_index"
    - "fragmentation_index"
    - "water_security_index"
  ward_metrics_view:
    - "ducal_rollups_only"            # aggregated per duchy, not individual wards
  force_metrics_view:
    - "high_level_mil_readiness"
    - "mutiny_risk_by_duchy"
  guild_cartel_view:
    - "guild_charter_stress_by_duchy"
    - "black_market_index_by_duchy"
  personal_risk_view:
    - "coup_risk_index"
    - "dynasty_security_index"
    - "elite_faction_tension_index"

access_defaults:
  archive_access_level: [2, 3]
  rumor_circle_tags:
    - "palace_salons"
    - "high_clergy_circles"
    - "ducal_council"

learning_defaults:
  learning_drive_range: [0.3, 0.8]
  source_trust_archive_range: [0.5, 1.0]
  source_trust_rumor_range: [0.2, 0.6]
  bias_strength_range: [0.3, 0.8]
  bias_style_biases:
    - "prestige_seeking"
    - "paranoid"
    - "dogmatic"
```

### 3.2 Ducal Seat (Generic Duchy)

```yaml
office_id: "duchy:generic"
branch: "ducal"
pillar: "mil"
description: >
  Regional power-holder responsible for a cluster of wards. Manages local
  garrisons, implements crown policy, and manages guild pressure. Success is
  judged by quota delivery, unrest control, and loyalty to the crown.

core_goals:
  survival_weight: 0.8
  dynasty_weight: 0.7
  regime_stability_weight: 0.6
  doctrine_weight: 0.4
  economic_weight: 0.7
  prestige_weight: 0.6

levers:
  campaign_decisions:
    - "recommend_crackdown_or_restraint_to_crown"
  security_posture_controls:
    - "set_ducal_mil_alert_band"
    - "authorize_local_purge_ops"
  ci_posture_controls:
    - "request_ci_intensification"
    - "shield_favored_wards_from_ci"
  appointment_controls:
    - "appoint_ward_lords"
    - "reassign_garrison_captains"
    - "back_or_block_bishop_candidates"
  charter_controls:
    - "negotiate_guild_charters_in_duchy"
    - "enforce_quota_on_guilds"
  resource_controls:
    - "distribute_barrels_across_wards"
    - "shift_tax_pressure_between_wards"
  law_intensity_controls:
    - "set_local_law_intensity_bias"

signals:
  global_indices:
    - "global_stress_index"
    - "regime_legitimacy_index"
  ward_metrics_view:
    - "ward_unrest"
    - "ward_black_market_index"
    - "ward_loyalty_index"
  force_metrics_view:
    - "garrison_readiness_by_ward"
    - "mutiny_risk_by_ward"
  guild_cartel_view:
    - "guild_charter_stress_by_ward"
    - "black_market_index_by_ward"
  personal_risk_view:
    - "seat_risk_index"
    - "patron_satisfaction_index"   # crown
    - "local_coup_risk_index"

access_defaults:
  archive_access_level: [1, 2]
  rumor_circle_tags:
    - "ducal_officers_mess"
    - "guild_lodge"
    - "select_taverns"

learning_defaults:
  learning_drive_range: [0.2, 0.7]
  source_trust_archive_range: [0.4, 0.8]
  source_trust_rumor_range: [0.3, 0.7]
  bias_strength_range: [0.2, 0.8]
  bias_style_biases:
    - "pragmatic"
    - "paranoid"
    - "opportunistic"
```

---

## 4. Civic / Bishop Offices

### 4.1 Bishop Guild: Civic Steward (Generic)

```yaml
office_id: "bishop:civic_steward"
branch: "civic"
pillar: "health"
description: >
  Civic steward responsible for large-scale services (food halls, medical
  networks, scavenger guilds, or other non-military, non-industrial branches).
  Interfaces between crown/dukes and the gritty logistics of keeping people
  alive enough to work.

core_goals:
  survival_weight: 0.7
  dynasty_weight: 0.3
  regime_stability_weight: 0.7
  doctrine_weight: 0.6
  economic_weight: 0.6
  prestige_weight: 0.5

levers:
  campaign_decisions:
    - "advise_crown_on_relief_vs_repression"
  security_posture_controls:
    - "flag_abusive_garrisons_to_crown_or_esp"
  appointment_controls:
    - "appoint_hall_masters_and_clinic_heads"
  charter_controls:
    - "allocate_civic_resources_to_wards"
    - "negotiate_civic_support_with_guilds"
  resource_controls:
    - "prioritize_relief_barrels"
    - "shift_civic_services_between_wards"
  law_intensity_controls:
    - "advocate_for_leniency_or_harshness_on_civic_offenses"

signals:
  global_indices:
    - "global_stress_index"
    - "regime_legitimacy_index"
  ward_metrics_view:
    - "ward_morbidity_index"
    - "ward_starvation_risk"
    - "ward_unrest"
  guild_cartel_view:
    - "civic_guild_load"
    - "service_failure_risk"
  personal_risk_view:
    - "seat_risk_index"
    - "regime_blame_risk_index"

access_defaults:
  archive_access_level: [1, 2]
  rumor_circle_tags:
    - "civic_halls"
    - "medical_guild"
    - "street_storytellers"

learning_defaults:
  learning_drive_range: [0.4, 0.9]
  source_trust_archive_range: [0.5, 0.9]
  source_trust_rumor_range: [0.4, 0.8]
  bias_strength_range: [0.1, 0.6]
  bias_style_biases:
    - "empathic"
    - "procedural"
```

---

## 5. Military & Espionage High Offices

### 5.1 MIL High Command

```yaml
office_id: "mil:high_command"
branch: "military"
pillar: "mil"
description: >
  Central command over organized armed forces. Responsible for setting alert
  levels, doctrine, force rotations, and implementing crackdowns ordered by
  the crown or recommended by espionage.

core_goals:
  survival_weight: 0.8
  dynasty_weight: 0.2
  regime_stability_weight: 0.8
  doctrine_weight: 0.7    # military doctrine, not necessarily ideology
  economic_weight: 0.4
  prestige_weight: 0.7

levers:
  campaign_decisions:
    - "argue_for_or_against_crackdown"
  security_posture_controls:
    - "set_mil_alert_level_by_duchy"
    - "activate_special_detachments"
  appointment_controls:
    - "appoint_battalion_and_garrison_commanders"
    - "rotate_units_between_wards"
  resource_controls:
    - "allocate_mil_supplies"
    - "prioritize_exo_suit_maintenance"
  law_intensity_controls:
    - "set_field_justice_bands"

signals:
  global_indices:
    - "global_stress_index"
    - "threat_index"
    - "fragmentation_index"
  ward_metrics_view:
    - "ward_unrest"
    - "ward_attack_incident_rate"
  force_metrics_view:
    - "garrison_readiness_by_unit"
    - "morale_by_unit"
    - "mutiny_risk_by_unit"
  personal_risk_view:
    - "coup_suspicion_index"
    - "purge_risk_index"

access_defaults:
  archive_access_level: [1, 2]
  rumor_circle_tags:
    - "officers_mess"
    - "veterans_taverns"

learning_defaults:
  learning_drive_range: [0.2, 0.7]
  source_trust_archive_range: [0.4, 0.9]
  source_trust_rumor_range: [0.3, 0.7]
  bias_strength_range: [0.2, 0.8]
  bias_style_biases:
    - "professional"
    - "paranoid"
```

### 5.2 Espionage Branch Chief

```yaml
office_id: "esp:branch_chief"
branch: "espionage"
pillar: "info"
description: >
  Head of the Espionage Branch, controlling counterintelligence, informant
  networks, and covert operations. Balances infiltration containment against
  political fallout from overreach.

core_goals:
  survival_weight: 0.8
  dynasty_weight: 0.2
  regime_stability_weight: 0.7
  doctrine_weight: 0.5
  economic_weight: 0.3
  prestige_weight: 0.6

levers:
  campaign_decisions:
    - "warn_crown_about_crackdown_risks"
    - "urge_preemptive_crackdown"
  ci_posture_controls:
    - "set_ci_stance"
    - "prioritize_ci_signatures"
    - "recommend_purges"
  appointment_controls:
    - "assign_case_officers"
    - "create_or_disband_cells"
  resource_controls:
    - "allocate_ci_assets_between_wards"
  law_intensity_controls:
    - "expand_or_constrain_ci_legal_authority"

signals:
  global_indices:
    - "global_stress_index"
    - "regime_legitimacy_index"
    - "infiltration_index"
  ward_metrics_view:
    - "ward_infiltration_risk"
    - "ward_rumor_volatility"
  force_metrics_view:
    - "ci_signature_risk_by_node"
  guild_cartel_view:
    - "suspected_guild_infiltration"
    - "cartel_intel_presence"
  personal_risk_view:
    - "backlash_risk_index"
    - "scapegoat_risk_index"

access_defaults:
  archive_access_level: [2, 3]
  rumor_circle_tags:
    - "officers_mess"
    - "informant_networks"
    - "elite_salons"

learning_defaults:
  learning_drive_range: [0.4, 0.9]
  source_trust_archive_range: [0.5, 0.9]
  source_trust_rumor_range: [0.4, 0.9]
  bias_strength_range: [0.2, 0.7]
  bias_style_biases:
    - "analytic"
    - "paranoid"
```

---

## 6. Guild & Cartel High Offices

### 6.1 Guild Master (Production / Trade)

```yaml
office_id: "guild:master_generic"
branch: "guild"
pillar: "ind"
description: >
  Leader of a major production or trade guild. Manages charters, quotas, and
  the guild's internal discipline. Balances regime demands against member
  survival and profit, with an eye on black-market leakage.

core_goals:
  survival_weight: 0.7
  dynasty_weight: 0.4
  regime_stability_weight: 0.5
  doctrine_weight: 0.3
  economic_weight: 0.9
  prestige_weight: 0.6

levers:
  campaign_decisions:
    - "signal_support_or_resistance_to_regime"
  appointment_controls:
    - "appoint_foremen_and_cell_leads"
  charter_controls:
    - "accept_or_resist_quota_changes"
    - "negotiate_exemptions"
  resource_controls:
    - "allocate_production_between_markets"
    - "sanction_or_protect_members"
  guild_collective_actions:
    - "declare_strike"
    - "declare_slowdown"
    - "authorize_sabotage"

signals:
  ward_metrics_view:
    - "guild_output_by_ward"
    - "guild_member_mortality"
  guild_cartel_view:
    - "guild_charter_stress"
    - "black_market_margin_index"
  personal_risk_view:
    - "charter_revocation_risk"
    - "internal_coup_risk"

access_defaults:
  archive_access_level: [1, 2]
  rumor_circle_tags:
    - "guild_lodge"
    - "merchant_quarters"

learning_defaults:
  learning_drive_range: [0.3, 0.8]
  source_trust_archive_range: [0.3, 0.7]
  source_trust_rumor_range: [0.4, 0.9]
  bias_strength_range: [0.2, 0.7]
  bias_style_biases:
    - "opportunistic"
    - "cynical"
```

### 6.2 Cartel Boss (Underworld Consortium)

```yaml
office_id: "cartel:boss_generic"
branch: "cartel"
pillar: "econ"
description: >
  Coordinator of a major black-market consortium. Brokers routes, protection,
  and information between smugglers, corrupt officials, and desperate wards.
  Lives in the overlap of profit and regime blind spots.

core_goals:
  survival_weight: 0.9
  dynasty_weight: 0.5
  regime_stability_weight: 0.3
  doctrine_weight: 0.1
  economic_weight: 1.0
  prestige_weight: 0.7

levers:
  appointment_controls:
    - "appoint_route_masters"
    - "replace_local_fixers"
  resource_controls:
    - "route_goods_through_alt_corridors"
    - "choke_supply_to_apply_pressure"
  guild_collective_actions:
    - "coordinate_sabotage"
    - "fund_strikes_or_riots"
    - "escalate_to_violence"

signals:
  ward_metrics_view:
    - "black_market_index_by_ward"
    - "mil_and_ci_pressure_levels"
  guild_cartel_view:
    - "profit_margins_by_route"
    - "exposure_risk_index"
  personal_risk_view:
    - "assassination_risk_index"
    - "betrayal_risk_index"

access_defaults:
  archive_access_level: [0, 1]
  rumor_circle_tags:
    - "dockside_taverns"
    - "smuggler_safehouses"
    - "corrupt_officials"

learning_defaults:
  learning_drive_range: [0.3, 0.7]
  source_trust_archive_range: [0.0, 0.4]
  source_trust_rumor_range: [0.6, 1.0]
  bias_strength_range: [0.3, 0.9]
  bias_style_biases:
    - "cynical"
    - "paranoid"
    - "opportunistic"
```

---

## 7. Usage Notes (v1)

- Scenario configs (D-RUNTIME-0103) should reference these office_ids when
  defining `RoleConfig` entries for Tier-3 actors.
- AiPolicyProfiles (D-RUNTIME-0105) for specific characters should be **built
  on top of** these office sheets, not contradict them without an explicit
  story reason.
- Office sheets define the **default access and learning ranges**; individual
  incumbents can sit near the edges or just outside them for variety.
- Future work may:
  - split some offices (e.g. multiple specialized bishop roles),
  - add more detailed lever lists,
  - or extend the signals to include finer-grained ward attributes.

