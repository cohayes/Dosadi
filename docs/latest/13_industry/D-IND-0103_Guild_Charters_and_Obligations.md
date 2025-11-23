---
title: Guild_Charters_and_Obligations
doc_id: D-IND-0103
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
  - D-IND-0102            # Named_Guilds_and_Internal_Factions
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 13_industry · Guild Charters and Obligations (D-IND-0103)

## 1. Purpose

This document defines the **formal relationship** between the regime and its
industrial guilds on Dosadi as expressed through **guild charters**.

It answers:

- What the regime claims guilds **must provide** (outputs, maintenance, data).
- What guilds are **promised** in return (protections, monopolies, privileges).
- How these obligations vary by:
  - Guild archetype (D-IND-0101),
  - Ward type and regional league,
  - Legal and emergency state (D-LAW-*).
- How charters interact with:
  - Enforcement chains (D-LAW-0001/0002/0003),
  - Guild power and bargaining (D-IND-0003),
  - Ward evolution (D-WORLD-0003),
  - Black markets and cartels (D-ECON-0004).

Guild charters are **aspirational contracts**: reality frequently diverges, and
that gap is where most of the drama lives.

---

## 2. Charter Template

Each charter is structured around **obligations**, **entitlements**, and
**conditions**.

```yaml
GuildCharter:
  id: string
  guild_family_id: string           # from D-IND-0102, e.g. GF_SUITS_BRINE_CHAIN
  issuing_authority: "duke_house" | "central_audit_guild" | "militia_high_command"
  scope:
    wards:
      - ward_pattern: "outer_industrial_bastion" | "hinge_interface" | "inner_sealed_core" | "any"
    legal_state_min: 0     # NORMAL
    legal_state_max: 4     # FULL_MARTIAL_STATE
  obligations:
    production_quota:
      metric: string        # e.g. "suits_per_tick", "lift_hours_uptime"
      baseline: float
      surge_margin: float   # % above baseline under emergency orders
    maintenance_duties:
      coverage: string      # e.g. "all militia exo_bays in wards under scope"
      response_time: int    # ticks to respond to critical failures
    telemetry_and_reporting:
      required_feeds:
        - "output_counts"
        - "downtime_events"
        - "incident_logs"
      audit_access: "limited" | "full" | "buffered"
    emergency_obligations:
      - "mandatory_overtime_under_decree"
      - "priority_repairs_for_garrisons"
  entitlements:
    exclusive_rights:
      - "sole_suits_supplier_to_militia_in_scope"
    protected_facilities:
      - "immunity_from_random_raids_except_by_audit_warrant"
    priority_access:
      - "tier_1_water_rations_for_key_workers"
      - "priority_lift_slots_for_parts"
    dispute_forums:
      primary_forum: "Guild_Arbitration" | "Audit_Commission" | "Ward_Admin_Panel"
      escalation_forum: "Ducal_Review" | "Security_Tribunal"
  conditions_and_sanctions:
    breach_thresholds:
      minor_breach: string   # definition in terms of metrics/events
      major_breach: string
    default_sanction_paths:
      minor: "Administrative_Handling"
      major: "Audit_Review"
      critical: "Security_Tribunal"
  notes:
    - "charter_subject_to_renewal_every_N_campaign_phases"
    - "partial_suspension_allowed_under_martial_state"
```

This template is not meant to be serialized verbatim but to guide scenario
and system design.

---

## 3. Charter Archetypes by Guild Type

### 3.1 SUITS-Core Charter Archetype

Applies to guild families like `GF_SUITS_BRINE_CHAIN` and `GF_SUITS_GOLDEN_MASK`.

Key points:

- **Obligations**
  - Maintain a minimum stock of serviceable suits for:
    - militia units in assigned wards,
    - critical condensate and energy crews.
  - Provide **24/7 emergency repair capacity** in outer bastions and hinge wards.
  - Maintain telemetry for:
    - suit uptime,
    - catastrophic failures,
    - unauthorized modifications (in theory).

- **Entitlements**
  - Exclusive right to:
    - service militia exo-bays in scope,
    - certify suits for use in sealed wards.
  - Priority access to:
    - high-grade materials,
    - water and power rations sufficient for fabrication.
  - Designated **Guild Arbitration** as primary dispute path for technical
    matters, with Audit Commissions only for long-term discrepancies.

- **Sanction logic**
  - Minor breach:
    - missed maintenance window without critical consequences →
      administrative fines, short-term ration penalties.
  - Major breach:
    - preventable fatalities, repeated downing of key exo assets →
      audit review, potential loss of exclusive rights.
  - Critical breach:
    - evidence of collusion with cartels to cripple militia assets →
      security tribunal targeting specific factions or leadership.

Notes:

- This archetype makes SUITS guilds **indispensable but tightly watched**.
- Internal factions (Gaugecutters, Ghostfitters) effectively gamble with
  charter compliance.

### 3.2 FABRICATION-MECH Charter Archetype

For families like `GF_FAB_YARDHOOK`.

Key points:

- **Obligations**
  - Meet baseline production quotas for:
    - tools, structural elements, corridor hardware, exo-frame parts.
  - Maintain and staff key yard facilities in Industrial Spine wards.
  - Provide incident logs for:
    - workplace injuries,
    - major equipment failures,
    - production shortfalls.

- **Entitlements**
  - Monopolistic or oligopolistic rights over heavy fabrication in scope.
  - Preferential access to:
    - bulk metals and scrap streams,
    - lifting capacity for parts and barrels.
  - Right to invoke **Guild Arbitration** for:
    - disputes over safety stops and “acceptable risk” levels.

- **Sanction logic**
  - Minor breach:
    - late quotas without systemic impact →
      increased audit sampling, mild ration sanctions.
  - Major breach:
    - repeated “accidents” affecting barrel flows or garrison readiness →
      audit commissions, forced management reshuffles.
  - Critical breach:
    - organized slowdowns during declared emergencies →
      potential martial law in yard wards, targeted raids on Burnhands.

Notes:

- The charter is a tug-of-war over what counts as “safe enough.”
- Yardhook factions weaponize **safety** and **accidents** as negotiation tools.

### 3.3 WATER-CONDENSATE Charter Archetype

For families like `GF_WATER_STILLWATER`.

Key points:

- **Obligations**
  - Maintain minimum condensate yield levels ward-by-ward.
  - Guarantee **priority flows** to:
    - core wards,
    - critical industrial clusters,
    - specified civic facilities (clinics, central canteens).
  - Provide continuous telemetry on:
    - yield,
    - losses,
    - cross-ward differentials.

- **Entitlements**
  - Strong protection from arbitrary sanctions:
    - raids and seizures require Audit or Ducal warrants.
  - Priority access to:
    - repairs and spares,
    - bishop mediation in local disputes.
  - Right to call for **Emergency Decrees** that:
    - restrict non-essential usage,
    - enforce rationing schemes they design (subject to audit oversight).

- **Sanction logic**
  - Minor breach:
    - localized yield drops with rapid recovery.
  - Major breach:
    - sustained shortages in non-core wards, evidence of deliberate bias.
  - Critical breach:
    - manipulative shortages in core wards or regime-critical facilities.

Notes:

- Stillwater’s charter reveals how central they are; sanctioning them is **risky**.
- Skimmer factions push at the edges, feeding black markets while risking
  triggering audit or ducal fury.

### 3.4 FOOD-BIOMASS Charter Archetype

For families like `GF_FOOD_VATCHAIN`.

Key points:

- **Obligations**
  - Deliver a daily ration minimum per registered inhabitant in scope.
  - Maintain health standards (D-HEALTH-0002) to avoid mass illness.
  - Provide yield metrics and spoilage reports.

- **Entitlements**
  - Partial control over composition of rations (within nutritional bands).
  - Bishop-backed protection from militia interference within canteens.
  - Access to low-grade biomass and waste streams without contest.

- **Sanction logic**
  - Minor breach:
    - non-critical quality drift, manageable shortages.
  - Major breach:
    - repeated food poisoning, large-scale underfeeding.
  - Critical breach:
    - perceived intentional starvation of regime-favored wards,
      or coordination with Feeders in political strikes.

Notes:

- The charter recognizes canteens as **political organs**; who eats how much,
  and when, is governance.

### 3.5 ENERGY-MOTION Charter Archetype

For families like `GF_ENERGY_LIFT_CROWN`.

Key points:

- **Obligations**
  - Maintain energy and lift uptime above a threshold, especially:
    - garrison corridors,
    - barrel cadence paths,
    - noble transit routes.
  - Keep **emergency capacity** available for:
    - curfews and lockdowns,
    - mass troop movement.

- **Entitlements**
  - High say in scheduling corridors and lift windows.
  - Protection for critical shafts and substations under MIL guard.
  - Participation in planning MIL deployment zones in hinge/lift wards.

- **Sanction logic**
  - Minor breach:
    - localized outages or delays.
  - Major breach:
    - repeated failures on critical routes, especially during unrest.
  - Critical breach:
    - evidence of collusion with cartels or rebels to cut power/lift access.

Notes:

- Lift Crown’s charter encodes their role as **arteries of control**.
- Spanner factions basically weaponize this charter’s “accident” clause.

### 3.6 INFO-SUPPORT Charter Archetype

For families like `GF_INFO_QUIET_LEDGER`.

Key points:

- **Obligations**
  - Maintain accurate and timely ledgers for:
    - water and ration flows,
    - industrial outputs,
    - sanctions and case logs.
  - Preserve archives for a minimum duration unless ordered otherwise.

- **Entitlements**
  - Relative immunity:
    - their offices cannot be searched without higher-level warrants.
  - Preferential access to:
    - raw data feeds,
    - secure storage and communication channels.

- **Sanction logic**
  - Minor breach:
    - clerical errors, occasional “lost” files.
  - Major breach:
    - systematic discrepancies, patterns of politically skewed records.
  - Critical breach:
    - proven collaboration with cartels to falsify or erase records.

Notes:

- Their charter is about **who controls the story the numbers tell**.
- Redactors and Shadowscript factions live right at the edge of breach.

---

## 4. Charter Lifecycle: Grant, Review, and Revocation

### 4.1 Grant and renewal

Charters are:

- Issued typically by **duke_house**, with input from:
  - central_audit_guild (for oversight clauses),
  - militia (for emergency performance clauses),
  - bishops (for civic impact clauses).

- Granted with:
  - fixed review intervals (e.g. every N campaign phases),
  - conditions for automatic review (e.g. major incidents above a threshold).

Implementation hook:

```yaml
charter_lifecycle:
  review_interval_phases: int
  auto_review_triggers:
    - "major_breach_event"
    - "ward_legal_state >= PARTIAL_MARTIAL_STATE for N phases"
    - "G_power[w][family] < threshold"
```

### 4.2 Suspension and partial revocation

In emergencies:

- Specific entitlements may be **suspended**:
  - e.g. immunity from raids revoked in certain wards.
- Obligations may be **expanded**:
  - surge quotas,
  - mandatory redeployment of key staff.

This is often framed as:

- **Temporary decrees** (D-LAW-0003),
- With or without compensation afterward.

### 4.3 Full revocation and re-chartering

If a guild is deemed:

- Incorrigibly non-compliant,
- Politically dangerous,
- Structurally obsolete,

the regime may:

- Revoke its charter in whole or in key regions.
- Offer a new charter to:
  - a rival guild family,
  - a splinter faction within the same family,
  - or even a temporary “state-run” body.

This process:

- Heavily impacts `G_power[w][F]`,
- Can reconfigure regional leagues (D-IND-0101),
- Often triggers **ShadowGuild** expansion and cartel moves.

---

## 5. Interplay with Sanctions, Law, and Ward Evolution

### 5.1 Charters as levers in sanction chains

Charter clauses are often **explicitly referenced** when applying sanctions:

- “Violation of Charter Clause 7.3: failure to maintain lift uptime…”
- “Emergency activation of Charter Clause 4.1: mandatory overtime…”

D-LAW-0001 chains can:

- Escalate from:
  - warnings and renegotiations,
  - to quota penalties and oversight commissions,
  - to forced management changes,
  - and eventually revocation.

### 5.2 Charters and ward specialization

Charters bias ward evolution (D-WORLD-0003):

- Where charters favor industrial expansion and entitlements are generous,
  wards tend to **specialize** in those industries.
- Where charters are punitive, unstable, or frequently revised,
  industries may stagnate or migrate.

Examples:

- A generous Lift Crown charter in hinge wards reinforces a **Lift Ring League**.
- Tightened Stillwater charter clauses can shift condensate focus from some
  wards to others, reshaping the **Water Crown**.

### 5.3 Rumor and perceived legitimacy

Charter disputes provide rich rumor hooks:

- “The Brine Chain charter was renewed despite the last exo collapse.”
- “Feeders kept their charters by threatening a hunger riot.”
- “Lift Crown owns the ducal signatures; they never lose a charter.”

Rumor system can treat **charter events** as:

- Seeds for:
  - guild pride or resentment,
  - accusations of corruption,
  - martyrdom narratives when charters are revoked.

---

## 6. Implementation Sketch (Non-Normative)

A minimal implementation might:

1. For each major guild family in a scenario:
   - Instantiate one or more **GuildCharter** objects based on archetypes,
   - Attach them to wards/regions as appropriate.

2. At each macro-phase:
   - Evaluate performance vs charter obligations (quota, maintenance, telemetry).
   - Track breach counts and severity.
   - Trigger:
     - warnings,
     - renegotiations,
     - escalations to law paths (Administrative, Audit, Tribunal).

3. On major breaches or political shifts:
   - Consider charter modification, suspension, or transfer to rivals.
   - Update ward industry intensities and guild power accordingly.

4. Generate events and rumors:
   - Charter reviews,
   - Publicized devotions or betrayals,
   - Quiet “charter coups” where a faction seizes the charter from within.

---

## 7. Future Extensions

Possible follow-ups:

- `D-IND-0104_Guild_Strikes_Slowdowns_and_Sabotage_Plays`
  - Detailed catalog of guild-side actions framed as charter interpretation
    and resistance.

- `D-ECON-0101_Contract_Forms_and_Barter_Ledgers`
  - How charters translate into low-level contracts, invoices, and barter
    practices.

- Scenario-specific charter packs
  - Prebuilt charter sets for particular arcs (e.g. “Pre-Sting Wave” vs
    “After First Purge”), showing how regime-guild relations harden over time.
