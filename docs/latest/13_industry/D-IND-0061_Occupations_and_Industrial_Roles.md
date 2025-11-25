---
title: Occupations_and_Industrial_Roles
doc_id: D-IND-0061
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-22
depends_on:
  - D-AGENT-0001          # Core_Agent_Spec (placeholder / updated in repo)
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-IND-0001            # Industry_Taxonomy_and_Types
  - D-IND-0002            # Industry_Suitability_and_Evolution
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-ECON-0001           # Logistics_Corridors_and_Safehouses
---

# 01_agents · Occupations and Industrial Roles (D-IND-0061)

## 1. Purpose

This document defines a **shared vocabulary of occupations** on Dosadi and
explains how they connect:

- To **industry families** (D-IND-0001),
- To **military force types** (D-MIL-0001),
- To **ward attributes** (D-WORLD-0002),
- To **agent stats and drives** (D-AGENT-0001).

It is a **bridge layer** between high-level world logic (industries, wards,
military) and concrete agent configurations (jobs, uniforms, income, risks).

This document does **not** define personal backstories or unique NPCs. It
defines **archetypal jobs** that agents can hold or move between.

---

## 2. Occupation Schema

Each occupation archetype is defined by a compact record. This is a conceptual
schema; implementation can store as JSON, YAML, or code structs.

```yaml
id: string                 # e.g. occ_rubble_crew
label: string              # human-readable name
pillar_family: string      # industry/military family, e.g. "SCRAP_MATERIALS", "SUITS", "MIL_GARRISON"
tier: string               # "unskilled" | "semi_skilled" | "skilled" | "elite"
description: string

ward_profile_fit:
  prefers:                 # informal tags tied to WardAttributes
    - string               # e.g. "high_scrap_access", "open_or_mixed_ventilation"
  avoids:
    - string

typical_employers:         # which factions usually hire them
  - string                 # e.g. "duke_house", "cartel", "bishop_guild", "militia"

baseline_compensation:
  water_ration: float      # 0–1 relative to 'standard' adult ration
  food_ration: float       # 0–1
  script_pay: float        # abstract purchasing power index 0–1
  housing_quality: float   # 0–1, proxy for bunk vs private room

risk_profile:
  physical_risk: float     # 0–1: injury/death
  legal_risk: float        # 0–1: arrest/punishment
  social_risk: float       # 0–1: stigma/ostracism

suit_profile:
  baseline_suit_grade: string  # "none" | "ragged" | "standard" | "reinforced" | "exo_bound"
  suit_dependency: string      # "optional" | "work_only" | "always"

skill_hooks:               # how this job maps to agent skills
  primary_skills:
    - string               # e.g. "ScrapHandling", "Pipework", "ExoPiloting"
  secondary_skills:
    - string               # supporting or growth skills
  growth_paths:
    - string               # occupations this job commonly leads to

drive_hooks:               # how drives (loyalty, hunger, ambition, etc.) express here
  loyalty_pressure: string # e.g. "moderate_to_employer", "weak", "split_between_cartel_and_family"
  advancement_pressure: string # narrative of how/why people push up/out
  blackmail_vectors:
    - string               # e.g. "unofficial_perks", "smuggling_opportunities"

notes: string
```

Tags in `ward_profile_fit.prefers/avoids` are **conventions**, not hard-coded
keys. Implementation should resolve them against `WardAttributes` and
`industry_weight` / `military_weight` as needed.

---

## 3. Core Civil / Industrial Occupations

This section sketches representative occupations tied to **industry families**.
It is not exhaustive; more can be added per family as needed.

### 3.1 SCRAP_MATERIALS

#### 3.1.1 Rubble Crew

```yaml
id: occ_rubble_crew
label: "Rubble Crew"
pillar_family: "SCRAP_MATERIALS"
tier: "unskilled"
description: >
  Front-line scavengers and demolition hands who pick through ruins, haul rubble,
  and strip usable scrap under harsh and often contaminated conditions.

ward_profile_fit:
  prefers:
    - high_scrap_access
    - moderate_to_high_toxicity
    - open_or_mixed_ventilation
  avoids:
    - sealed_elite_cores

typical_employers:
  - "cartel"
  - "bishop_guild"
  - "militia"

baseline_compensation:
  water_ration: 0.7
  food_ration: 0.8
  script_pay: 0.3
  housing_quality: 0.3

risk_profile:
  physical_risk: 0.8
  legal_risk: 0.3
  social_risk: 0.4

suit_profile:
  baseline_suit_grade: "ragged"
  suit_dependency: "work_only"

skill_hooks:
  primary_skills:
    - "ScrapHandling"
    - "Climbing"
  secondary_skills:
    - "ImprovisedRepairs"
    - "StreetAwareness"
  growth_paths:
    - "occ_scrap_sorter"
    - "occ_demolition_tech"

drive_hooks:
  loyalty_pressure: "weak_to_employer_strong_to_crew"
  advancement_pressure: "escape_hazard_by_moving_into_sorting_or_security"
  blackmail_vectors:
    - "off_the_books_salvage"
    - "knowledge_of_hidden_caches"

notes: >
  Rubble crews form tight micro-groups; shared risk breeds loyalty but also
  resentment toward whoever profits from their work.
```

#### 3.1.2 Scrap Sorter

```yaml
id: occ_scrap_sorter
label: "Scrap Sorter"
pillar_family: "SCRAP_MATERIALS"
tier: "semi_skilled"
description: >
  Workers who categorize, grade, and route scrap into appropriate fabrication,
  smelting, or disposal streams.

ward_profile_fit:
  prefers:
    - moderate_scrap_access
    - near_fabrication_clusters
  avoids:
    - ultra_high_toxicity_ruins

typical_employers:
  - "bishop_guild"
  - "duke_house"
  - "cartel"

baseline_compensation:
  water_ration: 0.8
  food_ration: 0.9
  script_pay: 0.4
  housing_quality: 0.4

risk_profile:
  physical_risk: 0.5
  legal_risk: 0.4
  social_risk: 0.3

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "work_only"

skill_hooks:
  primary_skills:
    - "MaterialRecognition"
    - "BasicAccounting"
  secondary_skills:
    - "Negotiation"
    - "Inspection"
  growth_paths:
    - "occ_yard_overseer"
    - "occ_fabrication_operator"

drive_hooks:
  loyalty_pressure: "moderate_to_employer_due_to_relative_stability"
  advancement_pressure: "build_reputation_for_honesty_or_discretion"
  blackmail_vectors:
    - "skimming_high_grade_scrap"
    - "regrading_for_cartel_benefit"

notes: >
  Sorters sit at an information chokepoint: they see what flows where. This makes
  them valuable to black markets and auditors alike.
```

### 3.2 WATER_ATMOSPHERE

#### 3.2.1 Barrel Handler

```yaml
id: occ_barrel_handler
label: "Barrel Handler"
pillar_family: "WATER_ATMOSPHERE"
tier: "unskilled"
description: >
  Manual labor moving sealed water and condensate barrels between depots, lifts,
  and distribution points along the cadence routes.

ward_profile_fit:
  prefers:
    - moderate_to_high_corridor_centrality
    - proximity_to_water_depots
  avoids:
    - extreme_dead_ends_far_from_main_cadence

typical_employers:
  - "duke_house"
  - "bishop_guild"
  - "cartel"

baseline_compensation:
  water_ration: 1.0
  food_ration: 0.9
  script_pay: 0.4
  housing_quality: 0.4

risk_profile:
  physical_risk: 0.6
  legal_risk: 0.5
  social_risk: 0.3

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "work_only"

skill_hooks:
  primary_skills:
    - "LoadHandling"
    - "RouteFamiliarity"
  secondary_skills:
    - "SmugglingAwareness"
  growth_paths:
    - "occ_cadence_foreman"
    - "occ_logistics_clerk"

drive_hooks:
  loyalty_pressure: "mixed_between_regime_and_smugglers"
  advancement_pressure: "control_of_shift_assignments_and_routing"
  blackmail_vectors:
    - "unauthorized_barrel_taps"
    - "deliberate_delays_or_misroutes"

notes: >
  Barrel handlers are where water theft and skimming most often happens; they are
  the hands on the lifeblood of the city.
```

#### 3.2.2 Cadence Foreman

```yaml
id: occ_cadence_foreman
label: "Cadence Foreman"
pillar_family: "WATER_ATMOSPHERE"
tier: "skilled"
description: >
  Oversees route scheduling, barrel movements, and staff on a segment of the
  water cadence chain.

ward_profile_fit:
  prefers:
    - high_corridor_centrality
    - moderate_audit_intensity
  avoids:
    - extremely_low_info_admin_zones

typical_employers:
  - "duke_house"
  - "central_audit_guild"

baseline_compensation:
  water_ration: 1.2
  food_ration: 1.1
  script_pay: 0.7
  housing_quality: 0.6

risk_profile:
  physical_risk: 0.4
  legal_risk: 0.7
  social_risk: 0.5

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "Scheduling"
    - "PersonnelManagement"
    - "CorruptionDetection"
  secondary_skills:
    - "LedgerKeeping"
    - "ConflictMediation"
  growth_paths:
    - "occ_water_auditor"
    - "occ_logistics_director"

drive_hooks:
  loyalty_pressure: "strong_to_regime_due_to_exposure_to_fraud"
  advancement_pressure: "maintain_flow_while_keeping_loss_within_tolerances"
  blackmail_vectors:
    - "knowledge_of_coverups"
    - "selective_enforcement_of_rules"

notes: >
  Foremen sit between labor and regime; they are both potential allies and
  primary threats to smugglers and dissenters.
```

### 3.3 SUITS & FABRICATION

#### 3.3.1 Suit Stitcher

```yaml
id: occ_suit_stitcher
label: "Suit Stitcher"
pillar_family: "SUITS"
tier: "skilled"
description: >
  Tailors and technicians who assemble, patch, and custom-fit environmental suits,
  masks, and liners for various castes and jobs.

ward_profile_fit:
  prefers:
    - mixed_or_sealed_ventilation
    - moderate_to_high_skilled_labor_share
  avoids:
    - extreme_toxic_ruins

typical_employers:
  - "bishop_guild"
  - "duke_house"
  - "cartel"

baseline_compensation:
  water_ration: 1.0
  food_ration: 1.0
  script_pay: 0.8
  housing_quality: 0.6

risk_profile:
  physical_risk: 0.3
  legal_risk: 0.4
  social_risk: 0.3

suit_profile:
  baseline_suit_grade: "reinforced"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "FineMotorControl"
    - "SuitAnatomy"
  secondary_skills:
    - "CustomerHandling"
    - "MaterialRecognition"
  growth_paths:
    - "occ_suit_designer"
    - "occ_exo_tech"

drive_hooks:
  loyalty_pressure: "moderate_to_employer_and_key_clients"
  advancement_pressure: "secure_elite_clients_and_exclusive_contracts"
  blackmail_vectors:
    - "under_spec_suits_for_targets"
    - "quiet_modifications_for_black_market"

notes: >
  Because all classes need suits, stitchers see cross-cutting clientele and
  can quietly pass information between strata.
```

#### 3.3.2 Exo-Bay Technician

```yaml
id: occ_exo_tech
label: "Exo-Bay Technician"
pillar_family: "SUITS"
tier: "skilled"
description: >
  Maintains, configures, and troubleshoots heavy exo-suits used in industry and
  military operations.

ward_profile_fit:
  prefers:
    - high_structural_capacity
    - open_or_mixed_ventilation
    - proximity_to_FABRICATION_and_ENERGY_MOTION
  avoids:
    - sealed_admin_cores

typical_employers:
  - "militia"
  - "duke_house"
  - "cartel"

baseline_compensation:
  water_ration: 1.1
  food_ration: 1.1
  script_pay: 0.9
  housing_quality: 0.6

risk_profile:
  physical_risk: 0.6
  legal_risk: 0.6
  social_risk: 0.5

suit_profile:
  baseline_suit_grade: "reinforced"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "ExoMaintenance"
    - "Diagnostics"
  secondary_skills:
    - "ImprovisedRepairs"
    - "SystemHacking"
  growth_paths:
    - "occ_exo_pilot_mil"
    - "occ_clandestine_modder"

drive_hooks:
  loyalty_pressure: "pulled_between_military_clients_and_black_mod_garages"
  advancement_pressure: "access_to_rare_parts_and_high_grade_power_systems"
  blackmail_vectors:
    - "maintenance_logs"
    - "secret_overrides_and_safeties"

notes: >
  Exo techs are essential for any faction fielding heavy suits; their defection
  or sabotage can decide battles before they start.
```

### 3.4 FOOD_BIOMASS

#### 3.4.1 Canteen Worker

```yaml
id: occ_canteen_worker
label: "Canteen Worker"
pillar_family: "FOOD_BIOMASS"
tier: "unskilled"
description: >
  Prepares and serves rationed meals in communal canteens, cleaning utensils and
  surfaces, and handling long, stressed lines of hungry people.

ward_profile_fit:
  prefers:
    - moderate_to_high_habitation_density
    - proximity_to_barracks_and_bunkhouses
  avoids:
    - extremely_low_population_scale

typical_employers:
  - "bishop_guild"
  - "duke_house"
  - "cartel"

baseline_compensation:
  water_ration: 1.0
  food_ration: 1.1
  script_pay: 0.3
  housing_quality: 0.4

risk_profile:
  physical_risk: 0.3
  legal_risk: 0.3
  social_risk: 0.3

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "work_only"

skill_hooks:
  primary_skills:
    - "FoodHandling"
    - "QueueManagement"
  secondary_skills:
    - "GossipListening"
    - "BasicHygiene"
  growth_paths:
    - "occ_canteen_overseer"
    - "occ_supply_clerk"

drive_hooks:
  loyalty_pressure: "to_employer_and_regular_patrons"
  advancement_pressure: "control_over_portion_sizes_and_leftovers"
  blackmail_vectors:
    - "quiet_extra_servings"
    - "selective_denial_of_service"

notes: >
  Canteens are key rumor hubs and pressure valves; workers see who is eating,
  who is missing, and who is suddenly flush or starving.
```

#### 3.4.2 Vat Technician

```yaml
id: occ_vat_tech
label: "Vat Technician"
pillar_family: "FOOD_BIOMASS"
tier: "skilled"
description: >
  Monitors and adjusts nutrient vats, fermentation tanks, and growth cultures
  that produce bulk calories for a ward or cluster of wards.

ward_profile_fit:
  prefers:
    - moderate_to_high_food_buffer
    - mixed_or_sealed_ventilation
  avoids:
    - high_toxicity_ruin

typical_employers:
  - "bishop_guild"
  - "duke_house"

baseline_compensation:
  water_ration: 1.1
  food_ration: 1.2
  script_pay: 0.8
  housing_quality: 0.6

risk_profile:
  physical_risk: 0.4
  legal_risk: 0.6
  social_risk: 0.4

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "ProcessControl"
    - "BioSystems"
  secondary_skills:
    - "Diagnostics"
    - "ContaminationResponse"
  growth_paths:
    - "occ_vat_master"
    - "occ_health_safety_officer"

drive_hooks:
  loyalty_pressure: "strong_to_employer_due_to_sensitivity_of_food_supply"
  advancement_pressure: "maintain_yield_and_prevent_visible_failures"
  blackmail_vectors:
    - "silent_dilution_or_enrichment_of_rations"
    - "quiet_diversion_of_high_grade_output"

notes: >
  Vat techs sit at the intersection of food security and health; subtle sabotage
  or favoritism here can reshape a ward's politics.
```

### 3.5 BODY_HEALTH

#### 3.5.1 Clinic Orderly

```yaml
id: occ_clinic_orderly
label: "Clinic Orderly"
pillar_family: "BODY_HEALTH"
tier: "semi_skilled"
description: >
  Assists medics and physicians in basic care, cleaning, moving patients, and
  maintaining supplies in small ward clinics.

ward_profile_fit:
  prefers:
    - moderate_to_high_population_scale
    - medium_disease_pressure
  avoids:
    - wards_with_no_formal_health_infrastructure

typical_employers:
  - "bishop_guild"
  - "duke_house"

baseline_compensation:
  water_ration: 1.0
  food_ration: 1.0
  script_pay: 0.5
  housing_quality: 0.5

risk_profile:
  physical_risk: 0.4
  legal_risk: 0.3
  social_risk: 0.4

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "BasicCare"
    - "Sanitation"
  secondary_skills:
    - "RecordKeeping"
    - "CalmingPatients"
  growth_paths:
    - "occ_clinic_nurse"
    - "occ_morgue_attendant"

drive_hooks:
  loyalty_pressure: "to_local_health_guild_and_regular_patients"
  advancement_pressure: "access_to_training_and_certification"
  blackmail_vectors:
    - "access_to_patient_records"
    - "quiet_access_to_drugs_and_supplies"

notes: >
  Orderlies hear whispered diagnoses and see who receives or is denied care,
  making them valuable observers for rumor and blackmail.
```

#### 3.5.2 Street Medic

```yaml
id: occ_street_medic
label: "Street Medic"
pillar_family: "BODY_HEALTH"
tier: "semi_skilled"
description: >
  Operates informally or semi-legally in markets, bunkhouses, and back corridors,
  providing first aid and low-grade treatment where formal clinics are absent or
  distrusted.

ward_profile_fit:
  prefers:
    - high_habitation_density
    - low_to_medium_audit_intensity
    - medium_black_market_intensity
  avoids:
    - sealed_admin_cores_with_high_fear_index

typical_employers:
  - "self"
  - "cartel"
  - "militia"   # sometimes on retainer

baseline_compensation:
  water_ration: 0.9
  food_ration: 1.0
  script_pay: 0.7
  housing_quality: 0.4

risk_profile:
  physical_risk: 0.6
  legal_risk: 0.7
  social_risk: 0.3

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "TraumaCare"
    - "ImprovisedMedicine"
  secondary_skills:
    - "StreetAwareness"
    - "Discretion"
  growth_paths:
    - "occ_clinic_nurse"
    - "occ_clandestine_surgeon"

drive_hooks:
  loyalty_pressure: "to_local_community_and_informal_patron_networks"
  advancement_pressure: "secure_regular_patients_and_supply_lines"
  blackmail_vectors:
    - "knowledge_of_who_was_wounded_where"
    - "unreported_deaths_and_injuries"

notes: >
  Street medics bridge official and unofficial worlds; they see the casualties
  of both state and cartel violence.
```

### 3.6 INFO_ADMIN & CIVIL LEDGER WORK

#### 3.6.1 Ration Clerk

```yaml
id: occ_ration_clerk
label: "Ration Clerk"
pillar_family: "INFO_ADMIN"
tier: "semi_skilled"
description: >
  Manages ration books, ID checks, and ledger entries for distribution of water,
  food, and other controlled goods at ward level.

ward_profile_fit:
  prefers:
    - moderate_to_high_audit_intensity
    - mixed_or_sealed_ventilation
  avoids:
    - extremely_low_info_admin_presence

typical_employers:
  - "central_audit_guild"
  - "duke_house"

baseline_compensation:
  water_ration: 1.1
  food_ration: 1.0
  script_pay: 0.8
  housing_quality: 0.6

risk_profile:
  physical_risk: 0.3
  legal_risk: 0.7
  social_risk: 0.5

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "LedgerKeeping"
    - "IDVerification"
  secondary_skills:
    - "CustomerHandling"
    - "DeceptionDetection"
  growth_paths:
    - "occ_audit_scribe"
    - "occ_registry_officer"

drive_hooks:
  loyalty_pressure: "strong_to_central_audit_and_superiors"
  advancement_pressure: "keep_losses_low_and_reports_clean"
  blackmail_vectors:
    - "ration_book_adjustments"
    - "ghost_entries_and_deletions"

notes: >
  Ration clerks decide who eats and who officially exists; small changes in their
  ledgers have outsized consequences.
```

#### 3.6.2 Audit Scribe

```yaml
id: occ_audit_scribe
label: "Audit Scribe"
pillar_family: "INFO_ADMIN"
tier: "skilled"
description: >
  Compiles, cross-checks, and summarizes records from multiple wards for higher
  authorities, flagging anomalies in flows, population, or incidents.

ward_profile_fit:
  prefers:
    - sealed_or_mixed_admin_cores
    - high_info_admin_weight
  avoids:
    - high_toxicity_ruin

typical_employers:
  - "central_audit_guild"
  - "duke_house"

baseline_compensation:
  water_ration: 1.1
  food_ration: 1.0
  script_pay: 1.0
  housing_quality: 0.7

risk_profile:
  physical_risk: 0.2
  legal_risk: 0.8
  social_risk: 0.6

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "work_only"

skill_hooks:
  primary_skills:
    - "DataAnalysis"
    - "ReportWriting"
  secondary_skills:
    - "PatternRecognition"
    - "PoliticalAwareness"
  growth_paths:
    - "occ_investigative_auditor"
    - "occ_policy_advisor"

drive_hooks:
  loyalty_pressure: "to_central_structures_but_sour_if_reports_are_ignored"
  advancement_pressure: "produce_actionable_insights_without_offending_powerful_clients"
  blackmail_vectors:
    - "suppressed_reports"
    - "unexplained_discrepancies"

notes: >
  Audit scribes see the big picture; they know which wards are quietly failing
  and which numbers are fiction.
```

### 3.7 HABITATION & LOCAL CIVIC ROLES

#### 3.7.1 Bunkhouse Steward

```yaml
id: occ_bunkhouse_steward
label: "Bunkhouse Steward"
pillar_family: "HABITATION"
tier: "semi_skilled"
description: >
  Manages shared sleeping spaces, assigns bunks, enforces basic rules, and
  collects small fees or ration cuts in dense habitation blocks.

ward_profile_fit:
  prefers:
    - high_habitation_density
    - medium_black_market_intensity
  avoids:
    - low_population_scale

typical_employers:
  - "bishop_guild"
  - "cartel"
  - "self"

baseline_compensation:
  water_ration: 1.0
  food_ration: 1.0
  script_pay: 0.6
  housing_quality: 0.7

risk_profile:
  physical_risk: 0.5
  legal_risk: 0.4
  social_risk: 0.6

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "ConflictMediation"
    - "RecordKeeping"
  secondary_skills:
    - "GossipListening"
    - "CrowdControl"
  growth_paths:
    - "occ_property_manager"
    - "occ_informal_fixxer"

drive_hooks:
  loyalty_pressure: "to_landlord_or_patron_but_pulled_by_resident_ties"
  advancement_pressure: "fill_beds_and_keep_trouble_below_threshold"
  blackmail_vectors:
    - "who_sleeps_where_and_with_whom"
    - "off_book_tenants_and_hideaways"

notes: >
  Stewards are gatekeepers of shelter; they quietly control who can hide, who
  must move on, and who gets privacy.
```

#### 3.7.2 Corridor Vendor

```yaml
id: occ_corridor_vendor
label: "Corridor Vendor"
pillar_family: "HABITATION"
tier: "unskilled"
description: >
  Operates a small stall or pushcart along busy corridors, selling minor goods,
  snacks, or services to passersby and workers.

ward_profile_fit:
  prefers:
    - high_corridor_centrality
    - moderate_to_high_habitation_density
  avoids:
    - extreme_lockdown_or_permanent_curfew_wards

typical_employers:
  - "self"
  - "cartel"

baseline_compensation:
  water_ration: 0.9
  food_ration: 1.0
  script_pay: 0.7
  housing_quality: 0.4

risk_profile:
  physical_risk: 0.4
  legal_risk: 0.5
  social_risk: 0.3

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "Haggling"
    - "CustomerHandling"
  secondary_skills:
    - "StreetAwareness"
    - "RumorTrading"
  growth_paths:
    - "occ_market_stall_owner"
    - "occ_cartel_informer"

drive_hooks:
  loyalty_pressure: "to_local_power_brokers_who_allow_them_to_trade"
  advancement_pressure: "secure_fixed_pitch_and_regular_customers"
  blackmail_vectors:
    - "knowledge_of_daily_movements"
    - "unlicensed_sales_and_taxes_owed"

notes: >
  Vendors form the living skin of corridors; they watch flows, hear talk, and
  can quietly pass messages or contraband.
```

---

## 4. Military-Linked Occupations


The following are **individual jobs** associated with force types (D-MIL-0001).

### 4.1 Street Enforcer

```yaml
id: occ_street_enforcer
label: "Street Enforcer"
pillar_family: "MIL_GARRISON"
tier: "semi_skilled"
description: >
  Armed personnel stationed in neighborhoods to enforce ration rules, deter petty
  crime, and act as the regime's visible face of coercion.

ward_profile_fit:
  prefers:
    - high_habitation_density
    - medium_corridor_centrality
    - moderate_garrison_presence
  avoids:
    - extreme_toxic_ruins

typical_employers:
  - "militia"
  - "duke_house"

baseline_compensation:
  water_ration: 1.1
  food_ration: 1.1
  script_pay: 0.7
  housing_quality: 0.5

risk_profile:
  physical_risk: 0.6
  legal_risk: 0.3
  social_risk: 0.6

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "WeaponHandling"
    - "Intimidation"
  secondary_skills:
    - "LocalKnowledge"
    - "CrowdControl"
  growth_paths:
    - "occ_corridor_trooper"
    - "occ_military_investigator"

drive_hooks:
  loyalty_pressure: "forced_loyalty_to_chain_of_command_vs_local_ties"
  advancement_pressure: "produce_results_without_triggering_backlash"
  blackmail_vectors:
    - "protection_rackets"
    - "evidence_suppression"

notes: >
  Street enforcers sit at the interface between residents and the military
  hierarchy; corruption and divided loyalties are common.
```

### 4.2 Corridor Trooper

```yaml
id: occ_corridor_trooper
label: "Corridor Trooper"
pillar_family: "MIL_PATROL"
tier: "semi_skilled"
description: >
  Armed troops assigned to patrol logistics corridors, guard checkpoints, and
  secure key junctions along the water and goods flows.

ward_profile_fit:
  prefers:
    - high_corridor_centrality
    - proximity_to_checkpoints_and_bulk_depots
  avoids:
    - deep_dead_ends

typical_employers:
  - "militia"
  - "duke_house"

baseline_compensation:
  water_ration: 1.1
  food_ration: 1.1
  script_pay: 0.8
  housing_quality: 0.5

risk_profile:
  physical_risk: 0.7
  legal_risk: 0.4
  social_risk: 0.5

suit_profile:
  baseline_suit_grade: "reinforced"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "WeaponHandling"
    - "RouteControl"
  secondary_skills:
    - "Inspection"
    - "SmugglingDetection"
  growth_paths:
    - "occ_rapid_response_operator"
    - "occ_checkpoint_commander"

drive_hooks:
  loyalty_pressure: "tied_to_military_payroll_and_punishment_systems"
  advancement_pressure: "control_over_movement_and_informal_taxes"
  blackmail_vectors:
    - "accepting_bribes"
    - "collusion_with_cartels"

notes: >
  Control of corridor troopers effectively decides who moves safely through the
  city and who does not.
```

### 4.3 Exo-Cadre Pilot (Military)

```yaml
id: occ_exo_pilot_mil
label: "Exo-Cadre Pilot"
pillar_family: "MIL_ASSAULT"
tier: "elite"
description: >
  Operators trained to fight and operate in heavy exo-suits, used for breaching,
  suppression, and industrial-scale violence.

ward_profile_fit:
  prefers:
    - wards_with_authorized_exobays
    - high_structural_capacity
  avoids:
    - sealed_admin_cores_except_in_extreme_crackdown

typical_employers:
  - "militia"
  - "duke_house"

baseline_compensation:
  water_ration: 1.2
  food_ration: 1.2
  script_pay: 1.0
  housing_quality: 0.7

risk_profile:
  physical_risk: 0.9
  legal_risk: 0.4
  social_risk: 0.5

suit_profile:
  baseline_suit_grade: "exo_bound"
  suit_dependency: "work_only"

skill_hooks:
  primary_skills:
    - "ExoPiloting"
    - "TargetAcquisition"
  secondary_skills:
    - "TeamCoordination"
    - "EnvironmentalAwareness"
  growth_paths:
    - "occ_exo_cadre_commander"
    - "occ_clandestine_exo_operator"

drive_hooks:
  loyalty_pressure: "heavily_conditioned_toward_regime_but_exposed_to_frontline_truths"
  advancement_pressure: "access_to_better_suits_and_protective_status"
  blackmail_vectors:
    - "war_crimes_knowledge"
    - "off_record_deployments"

notes: >
  Exo pilots are symbols of regime power; their personal arcs can strongly
  influence narrative weight in a scenario.
```

---

## 5. Black Market & Shadow Occupations

Black market roles mirror or parasitize official ones.

### 5.1 Smuggler (Cadence Route)

```yaml
id: occ_cadence_smuggler
label: "Cadence Route Smuggler"
pillar_family: "BLACK_MARKET"
tier: "semi_skilled"
description: >
  Moves contraband and diverted resources along or parallel to official cadence
  routes, relying on handler collusion and checkpoint corruption.

ward_profile_fit:
  prefers:
    - high_corridor_centrality
    - low_to_medium_audit_intensity
    - medium_black_market_intensity
  avoids:
    - sealed_admin_cores_with_total_surveillance

typical_employers:
  - "cartel"

baseline_compensation:
  water_ration: 1.0
  food_ration: 1.0
  script_pay: 1.0
  housing_quality: 0.4

risk_profile:
  physical_risk: 0.6
  legal_risk: 0.9
  social_risk: 0.7

suit_profile:
  baseline_suit_grade: "standard"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "RouteFamiliarity"
    - "Deception"
  secondary_skills:
    - "Negotiation"
    - "Bribery"
  growth_paths:
    - "occ_cartel_overseer"
    - "occ_intel_informant"

drive_hooks:
  loyalty_pressure: "split_between_cartel_and_self_preservation"
  advancement_pressure: "control_over_routes_and_contacts"
  blackmail_vectors:
    - "knowledge_of_corrupt_officials"
    - "records_of_past_runs"

notes: >
  Smugglers are nodal points linking water, food, and suit scarcity to faction
  politics and personal survival strategies.
```

### 5.2 Clandestine Exo Modder

```yaml
id: occ_clandestine_modder
label: "Clandestine Exo Modder"
pillar_family: "BLACK_MARKET_SUITS"
tier: "elite"
description: >
  Black-market technician who performs unauthorized modifications on exo-suits
  and suits, enhancing performance, concealment, or lethality.

ward_profile_fit:
  prefers:
    - open_or_mixed_ventilation
    - low_to_medium_audit_intensity
    - complex_corridor_layouts
  avoids:
    - sealed_heavily_monitored_cores

typical_employers:
  - "cartel"
  - "militia"        # off-book operations
  - "rogue_cells"

baseline_compensation:
  water_ration: 1.1
  food_ration: 1.1
  script_pay: 1.2
  housing_quality: 0.6

risk_profile:
  physical_risk: 0.5
  legal_risk: 1.0
  social_risk: 0.8

suit_profile:
  baseline_suit_grade: "reinforced"
  suit_dependency: "always"

skill_hooks:
  primary_skills:
    - "ExoMaintenance"
    - "SystemHacking"
  secondary_skills:
    - "Discretion"
    - "ContactManagement"
  growth_paths:
    - "occ_cartel_tech_director"
    - "occ_regime_asset_turned_informer"

drive_hooks:
  loyalty_pressure: "to_cartel_protection_and_key_clients"
  advancement_pressure: "monopoly_on_rare_mods_and_knowledge"
  blackmail_vectors:
    - "client_list"
    - "modification_specs"

notes: >
  Modders sit at a dangerous intersection of power, money, and secrecy; they are
  prime recruitment targets for info_security and intelligence actors.
```

---

## 6. Using OccupATIONS in Agent Design

### 6.1 Agent job field

In `D-AGENT-0001` (Core Agent Spec), each agent SHOULD have a field like:

```yaml
occupation_id: string   # may be null/none for children, unemployed, etc.
```

- This document provides the **valid ids** and associated metadata.
- Changing `occupation_id` is a **major life event** with knock-on effects on:
  - Income, water/food access,
  - Social graph, loyalties,
  - Skill growth and health risks.

### 6.2 Deriving constraints and affordances

From `occupation_id`, the simulation can quickly derive:

- **Capabilities**:
  - What tools or suits they can plausibly use.
  - What skills they have a head start in.

- **Constraints**:
  - Typical working hours and locations.
  - Minimum water/food needed to stay functional in that role.

- **Pressures**:
  - Who they must stay on the good side of.
  - What bribes or threats they are most vulnerable to.

### 6.3 Ward-level occupation distributions

Wards can maintain a rough distribution of occupations (counts/fractions). This:

- Links **ward attributes → industries → jobs → agents**.
- Allows scenario configs like:
  - “Ward:12 has a high share of Rubble Crew and Barrel Handlers, low share of
     Suit Stitchers and Cadence Foremen.”

These distributions provide a quick way to seed agents and expected conflicts.

---

## 7. Extension Notes

- This doc intentionally defines only a **handful of archetypes** per family. It
  is expected to grow as new pillars (health, law, info_security) introduce
  more specialized roles (auditors, clinic nurses, interrogators, data clerks).
- Occupation definitions SHOULD avoid hard-coding specific factions or wards;
  those belong in scenario configs or narrative overlays.
- For Codex/implementation, it may be useful to keep a machine-readable version
  of this taxonomy adjacent to this document (e.g. `occupations.yaml`) using
  the schema in §2.
