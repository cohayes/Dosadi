---
title: Named_Guilds_and_Internal_Factions
doc_id: D-IND-0102
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-WORLD-0003          # Ward_Evolution_and_Specialization_Dynamics
  - D-IND-0001            # Industry_Taxonomy_and_Types
  - D-IND-0002            # Industry_Suitability_and_Evolution
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-IND-0101            # Guild_Templates_and_Regional_Leagues
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 13_industry · Named Guilds and Internal Factions (D-IND-0102)

## 1. Purpose

This document instantiates **concrete named guilds** and their **internal factions**
as realizations of the guild archetypes (D-IND-0101) and guild power logic
(D-IND-0003).

Goals:

- Provide a small, reusable cast of **named guild families** for scenarios.
- Describe **internal faction lines** (pragmatists, hardliners, cartel-linked,
  reformists, etc.).
- Show how factions interact with:
  - Regime branches (duke_house, militia, bishops, audits),
  - Cartels and black markets,
  - Ward evolution and regional leagues (D-WORLD-0003, D-IND-0101).
- Offer hooks for **agent backgrounds**, plot arcs, and simulation events.

These names are *suggestive defaults*; scenarios may rename, merge, or reskin
them while keeping the underlying structures.

---

## 2. Guild Family Template

We describe each named guild family using this template:

```yaml
GuildFamily:
  id: string
  display_name: string
  archetype_id: string           # from D-IND-0101, e.g. SUITS_CORE
  emblem_motif: string           # symbolic hook (for UI/lore)
  core_industries:
    - string                     # from D-IND-0001 taxonomy
  primary_footprint_wards:
    - "outer_industrial_bastion"
    - "hinge_interface"
    - "inner_sealed_core"
  typical_allies:
    - "bishop_guild"
    - "duke_house"
    - "cartel:QuietLantern"
  typical_rivals:
    - "central_audit_guild"
    - "rival_guild_family_id"
  internal_factions:
    - name: string
      tagline: string
      stance_toward_regime: "loyalist" | "pragmatic" | "dissident" | "parasitic"
      stance_toward_cartels: "hostile" | "tolerant" | "embedded"
      preferred_tactics:
        - "slowdown"
        - "creative_compliance"
        - "leak_to_audit"
        - "backdoor_dealings"
      recruitment_pools:
        - "apprentice_techs"
        - "militia_quartermasters"
        - "bunkhouse_scavs"
  rumor_tags:
    - string
```

This is a **story-facing** layer: we expect scenario and UI code to reference
these IDs for flavor, while underlying sim logic still works with archetypes
and numeric guild power indices.

---

## 3. SUITS-Core Families

### 3.1 The Brine Chain Fabricators

```yaml
GuildFamily:
  id: "GF_SUITS_BRINE_CHAIN"
  display_name: "Brine Chain Fabricators"
  archetype_id: "SUITS_CORE"
  emblem_motif: "linked condensate coils over a stylized droplet"
  core_industries:
    - "SUITS_FABRICATION"
    - "SUITS_MAINTENANCE"
    - "MATERIALS_HIGH_GRADE"
  primary_footprint_wards:
    - "outer_industrial_bastion"
    - "hinge_interface"
  typical_allies:
    - "militia"
    - "duke_house"
  typical_rivals:
    - "central_audit_guild"
    - "GF_SUITS_GOLDEN_MASK"
  internal_factions:
    - name: "Linekeepers"
      tagline: "Keep the suits running, whatever the politics."
      stance_toward_regime: "pragmatic"
      stance_toward_cartels: "tolerant"
      preferred_tactics:
        - "quiet_repair_priorities"
        - "backchannel_requests_to_militia"
      recruitment_pools:
        - "apprentice_techs"
        - "old_line_workers"
    - name: "Gaugecutters"
      tagline: "Skim a little, upgrade a little; everyone wins."
      stance_toward_regime: "parasitic"
      stance_toward_cartels: "embedded"
      preferred_tactics:
        - "underreport_spares"
        - "ghost_mods_for_favored_clients"
        - "sell_overcapacity_to_cartels"
      recruitment_pools:
        - "bunkhouse_scavs"
        - "militia_quartermasters"
    - name: "Sealwrights"
      tagline: "Protect sealed cores and noble lines above all."
      stance_toward_regime: "loyalist"
      stance_toward_cartels: "hostile"
      preferred_tactics:
        - "leak_to_audit"
        - "refuse_risky_mods"
        - "lobby_duke_house_for_monopolies"
      recruitment_pools:
        - "core_ward_technicians"
        - "bishop_guild_clinics"
  rumor_tags:
    - "their suits never fail for dukes"
    - "outer ward crews die in thin plates"
    - "some coils are wound with stolen metal"
```

Notes:

- Strong presence in Industrial Spine leagues.
- Internal factions give you natural conflicts:
  - Linekeepers vs Gaugecutters over how much to skim,
  - Sealwrights vs Gaugecutters over elite vs frontier loyalties.

### 3.2 The Golden Mask Atelier

```yaml
GuildFamily:
  id: "GF_SUITS_GOLDEN_MASK"
  display_name: "Golden Mask Atelier"
  archetype_id: "SUITS_CORE"
  emblem_motif: "ornate face-mask with radiating vein-lines"
  core_industries:
    - "SUITS_FABRICATION"
    - "SUITS_CUSTOM_ELITE"
  primary_footprint_wards:
    - "inner_sealed_core"
  typical_allies:
    - "duke_house"
    - "bishop_guild"
  typical_rivals:
    - "central_audit_guild"
    - "GF_SUITS_BRINE_CHAIN"
  internal_factions:
    - name: "Purists"
      tagline: "Form follows doctrine. No black mods."
      stance_toward_regime: "loyalist"
      stance_toward_cartels: "hostile"
      preferred_tactics:
        - "court_patronage"
        - "denounce_rivals_as_irresponsible"
      recruitment_pools:
        - "core_artisans"
    - name: "Designers"
      tagline: "Beauty, prestige, and survivability—for a price."
      stance_toward_regime: "pragmatic"
      stance_toward_cartels: "tolerant"
      preferred_tactics:
        - "quiet_premium_upgrades"
        - "exclusive_contracts_with_elites"
      recruitment_pools:
        - "social_climbers"
        - "failed_nobility"
    - name: "Ghostfitters"
      tagline: "One more system in, no one needs to know."
      stance_toward_regime: "parasitic"
      stance_toward_cartels: "embedded"
      preferred_tactics:
        - "hidden_compartments"
        - "masking_telemetry_signatures"
      recruitment_pools:
        - "expelled_brine_chain_techs"
  rumor_tags:
    - "nobles suffocate slow in their art"
    - "golden masks never show true readings"
    - "their apprentices vanish if they talk too much"
```

Notes:

- Perfect origin for **elite-only suits**, ducal vanity, and dangerous secrets.
- Natural rival to Brine Chain over high-grade materials and contracts.

---

## 4. WATER and FOOD Families

### 4.1 The Stillwater Syndic

```yaml
GuildFamily:
  id: "GF_WATER_STILLWATER"
  display_name: "Stillwater Syndic"
  archetype_id: "WATER_CONDENSATE"
  emblem_motif: "a perfectly flat water surface crossed by tally lines"
  core_industries:
    - "WATER_CONDENSATE_SYSTEMS"
    - "DEHUMIDIFIER_NETWORKS"
  primary_footprint_wards:
    - "hinge_interface"
    - "inner_sealed_core"
  typical_allies:
    - "bishop_guild"
    - "central_audit_guild"
  typical_rivals:
    - "cartel:QuietLantern"
    - "GF_WATER_DRAINCHAIN"
  internal_factions:
    - name: "Balancers"
      tagline: "Keep the flows stable; everything else follows."
      stance_toward_regime: "pragmatic"
      stance_toward_cartels: "tolerant"
      preferred_tactics:
        - "quiet_rebalancing"
        - "warning_bishops_before_cuts"
      recruitment_pools:
        - "condensate_techs"
        - "audit_liaison_clerks"
    - name: "Metricists"
      tagline: "If it isn’t logged, it doesn’t exist."
      stance_toward_regime: "loyalist"
      stance_toward_cartels: "hostile"
      preferred_tactics:
        - "aggressive_metering"
        - "leak_to_audit_when_squeezed"
      recruitment_pools:
        - "telemetry_scribes"
        - "precision_fixers"
    - name: "Skimmers"
      tagline: "Drop by drop, we pay ourselves."
      stance_toward_regime: "parasitic"
      stance_toward_cartels: "embedded"
      preferred_tactics:
        - "small_unlogged_losses"
        - "special_lines_for_favored_clients"
      recruitment_pools:
        - "bunkhouse_maintainers"
  rumor_tags:
    - "they can make a ward thirsty overnight"
    - "their meters lie for those who pay"
    - "Metricists know every stolen drop"
```

### 4.2 The Vat Chain Cooperative

```yaml
GuildFamily:
  id: "GF_FOOD_VATCHAIN"
  display_name: "Vat Chain Cooperative"
  archetype_id: "FOOD_BIOMASS"
  emblem_motif: "linked fermentation vats with stylized steam"
  core_industries:
    - "FOOD_PRODUCTION"
    - "WASTE_TO_FOOD"
  primary_footprint_wards:
    - "civic_support_hubs"
    - "reserve_overflow"
  typical_allies:
    - "bishop_guild"
  typical_rivals:
    - "central_audit_guild"
    - "GF_FOOD_GILDED_PLATE"
  internal_factions:
    - name: "Feeders"
      tagline: "Full bellies first; quotas second."
      stance_toward_regime: "dissident"
      stance_toward_cartels: "tolerant"
      preferred_tactics:
        - "quiet_overfills_for_starving_wards"
        - "resist_ration_cuts"
      recruitment_pools:
        - "canteen_staff"
        - "bunkhouse_cooks"
    - name: "Counters"
      tagline: "We live and die by exact measures."
      stance_toward_regime: "pragmatic"
      stance_toward_cartels: "hostile"
      preferred_tactics:
        - "leak_data_to_bishops"
        - "blame_spoiled_batches_on_politics"
      recruitment_pools:
        - "ration_clerks"
    - name: "Scrapbrewers"
      tagline: "What the regime discards, we ferment."
      stance_toward_regime: "parasitic"
      stance_toward_cartels: "embedded"
      preferred_tactics:
        - "off_book_vats"
        - "trade_stronger_brews_for_favors"
      recruitment_pools:
        - "bunkhouse_scavs"
        - "corridor_vendors"
  rumor_tags:
    - "they thin the vats when audits come"
    - "Feeders hide extra ladles in plain sight"
    - "Scrapbrewers can turn anything into a drink—or a weapon"
```

---

## 5. ENERGY and FABRICATION Families

### 5.1 The Lift Crown Syndicate

```yaml
GuildFamily:
  id: "GF_ENERGY_LIFT_CROWN"
  display_name: "Lift Crown Syndicate"
  archetype_id: "ENERGY_MOTION"
  emblem_motif: "crowned lift cage ascending a stylized shaft"
  core_industries:
    - "LIFT_SYSTEMS"
    - "MOTION_SYSTEMS"
    - "ENERGY_DISTRIBUTION"
  primary_footprint_wards:
    - "hinge_interface"
    - "lift_ring"
  typical_allies:
    - "militia"
    - "duke_house"
  typical_rivals:
    - "cartel:QuietLantern"
    - "GF_ENERGY_PULSELINE"
  internal_factions:
    - name: "Schedulers"
      tagline: "If it doesn’t move on time, someone pays."
      stance_toward_regime: "pragmatic"
      stance_toward_cartels: "hostile"
      preferred_tactics:
        - "rerouted_priority_lifts"
        - "quiet_delays_for_troublemakers"
      recruitment_pools:
        - "lift_operators"
        - "shift_clerks"
    - name: "Spanners"
      tagline: "Accidents happen. Especially to enemies."
      stance_toward_regime: "parasitic"
      stance_toward_cartels: "embedded"
      preferred_tactics:
        - "mechanical_harassment"
        - "selective_breakages"
        - "sudden_service_restorations_for_favors"
      recruitment_pools:
        - "yard_mechanics"
        - "cartel_scouts"
    - name: "Linewards"
      tagline: "Keep the lines alive, whatever the ducal mood."
      stance_toward_regime: "pragmatic"
      stance_toward_cartels: "tolerant"
      preferred_tactics:
        - "emergency_repairs_in_ignored_wards"
        - "discreet_support_to_bishop_initiatives"
      recruitment_pools:
        - "outer_ring_techs"
  rumor_tags:
    - "lifts listen for names"
    - "Spanners can stall a duke mid-shaft"
    - "Linewards save wards the regime forgets"
```

### 5.2 The Yardhook Assembly

```yaml
GuildFamily:
  id: "GF_FAB_YARDHOOK"
  display_name: "Yardhook Assembly"
  archetype_id: "FABRICATION_MECH"
  emblem_motif: "hooked crane silhouetted against stacked barrels"
  core_industries:
    - "FABRICATION_HEAVY"
    - "TOOLS"
    - "SPARES"
  primary_footprint_wards:
    - "outer_industrial_bastion"
  typical_allies:
    - "militia"
  typical_rivals:
    - "central_audit_guild"
    - "GF_FAB_FINEGEAR"
  internal_factions:
    - name: "Rigbosses"
      tagline: "Control the rigs, control the ward."
      stance_toward_regime: "pragmatic"
      stance_toward_cartels: "tolerant"
      preferred_tactics:
        - "crew_reassignments"
        - "unofficial_safety_pauses"
      recruitment_pools:
        - "crane_operators"
        - "long_haul_fabricators"
    - name: "Burnhands"
      tagline: "We bleed for the quotas; time they bleed for us."
      stance_toward_regime: "dissident"
      stance_toward_cartels: "embedded"
      preferred_tactics:
        - "wildcat_strikes"
        - "open_sabotage_when_pushed"
      recruitment_pools:
        - "injured_workers"
        - "unionist_remnants"
    - name: "Ledgerhooks"
      tagline: "Every hook has a ledger attached."
      stance_toward_regime: "pragmatic"
      stance_toward_cartels: "tolerant"
      preferred_tactics:
        - "creative_invoicing"
        - "hide_real_yield_in_internal_codes"
      recruitment_pools:
        - "yard_clerks"
  rumor_tags:
    - "Burnhands engineer ‘accidents’ on command"
    - "Rigbosses can stop all barrels in a night"
    - "Ledgerhooks know where the missing metal went"
```

---

## 6. INFO-SUPPORT Families

### 6.1 The Quiet Ledger Houses

```yaml
GuildFamily:
  id: "GF_INFO_QUIET_LEDGER"
  display_name: "Quiet Ledger Houses"
  archetype_id: "INFO_SUPPORT"
  emblem_motif: "closed ledger with three sealed tabs"
  core_industries:
    - "INFO_CLERICAL"
    - "TELEMETRY_MAINTENANCE"
  primary_footprint_wards:
    - "inner_sealed_core"
    - "hinge_interface"
  typical_allies:
    - "central_audit_guild"
    - "bishop_guild"
  typical_rivals:
    - "cartel:QuietLantern"
  internal_factions:
    - name: "Balancers"
      tagline: "Every line must match—or someone must pay."
      stance_toward_regime: "loyalist"
      stance_toward_cartels: "hostile"
      preferred_tactics:
        - "internal_investigations"
        - "leak_to_audit_under_duress"
      recruitment_pools:
        - "audit_clerks"
        - "data_scribes"
    - name: "Redactors"
      tagline: "We control what exists on paper."
      stance_toward_regime: "pragmatic"
      stance_toward_cartels: "tolerant"
      preferred_tactics:
        - "selective_record_loss"
        - "dual_ledgers"
      recruitment_pools:
        - "bureaucrats"
        - "failed_auditors"
    - name: "Shadowscript"
      tagline: "We write what others are too afraid to say."
      stance_toward_regime: "dissident"
      stance_toward_cartels: "tolerant"
      preferred_tactics:
        - "leaks_to_cartels_and_guilds"
        - "samizdat_reports"
      recruitment_pools:
        - "disillusioned_scribes"
  rumor_tags:
    - "Quiet Ledgers know every missing barrel"
    - "Redactors can erase you twice—on paper and in memory"
    - "Shadowscript pamphlets read like prophecy"
```

---

## 7. Cartel-Linked Shadow Counterparts (Optional)

For each major guild family, scenarios may define **shadow counterparts**:

- Cartel-front workshops,
- Breakaway guild cells,
- “Black” chapters of otherwise legal guilds.

Example:

```yaml
ShadowGuild:
  id: "SG_SUITS_GUTTERFRAME"
  parent_guild_family: "GF_SUITS_BRINE_CHAIN"
  cartel_partner: "cartel:QuietLantern"
  specialization:
    - "illegal_exo_mods"
    - "unlogged_suit_rentals"
  rumor_tags:
    - "borrowed suits never come back clean"
    - "their frames creak with other people’s bones"
```

These can be slotted into Shadow League wards or anywhere black market
intensity is high.

---

## 8. Hooks for Agents, Events, and Scenarios

### 8.1 Agent backgrounds

Agents can have:

```yaml
agent_guild_affiliation:
  guild_family_id: "GF_SUITS_BRINE_CHAIN"
  faction_name: "Gaugecutters"
  standing: "member" | "exiled" | "favoured" | "blacklisted"
```

This affects:

- Access to certain facilities and jobs,
- Who they can plausibly call on for help,
- How guilds respond when sanctions or investigations land.

### 8.2 Event templates

Events may reference:

- Specific factions (“Burnhands are planning a wildcat strike”),
- Cross-faction alliances (“Linewards quietly back the Feeders”),
- Purge or favor campaigns (“duke_house moves against Skimmers”).

These events can:

- Shift `G_power[w][F]`,
- Adjust ward evolution pressures (D-WORLD-0003),
- Create hooks for player action or RL agent policies.

---

## 9. Future Extensions

Potential follow-ups:

- `D-IND-0103_Guild_Charters_and_Obligations`
  - Formal obligations between guilds and regime (quotas, exemptions,
    emergency duties).

- `D-IND-0104_Guild_Strikes_Slowdowns_and_Sabotage_Plays`
  - Detailed action patterns for guild pressure campaigns, with clear
    mechanical impacts.

- Scenario-specific guild briefs
  - Focused dossiers on which families and factions matter most in,
    e.g., Sting Wave Day-3 scenarios or particular ward clusters.
