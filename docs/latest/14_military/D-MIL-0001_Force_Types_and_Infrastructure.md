---
title: Force_Types_and_Infrastructure
doc_id: D-MIL-0001
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-21
depends_on:
  - D-WORLD-0001          # Wards & environment overview
  - D-WORLD-0002          # Ward_Attribute_Schema (proposed)
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-IND-0001            # Industry_Taxonomy_and_Types
  - D-IND-0002            # Industry_Suitability_and_Evolution
  - D-ECON-0001           # Logistics_Corridors_and_Safehouses
  - D-ECON-0002           # Black_Market_Networks
  - D-AGENT-0001          # Core_Agent_Spec (placeholder)
---

# 09_military · Force Types and Infrastructure (D-MIL-0001)

## 1. Purpose

This document defines the **foundational concepts for organized force on Dosadi**:
what kinds of forces exist, what infrastructure they require, and how these
elements couple to ward-level geography, industry, and politics.

This is a **taxonomy and logic** document. It **does not**:

- Specify individual units or named factions.
- Encode full doctrine, morale, or rules of engagement.

Those will be covered by follow-up documents (see §7).

Key goals:

- Give simulation code a **clean, configurable catalog** of force types and
  infrastructure nodes.
- Ensure military presence and capacity **emerge from the same pressures** that
  shape industry and ward specialization (D-IND-0001 / D-IND-0002), rather than
  being overlaid arbitrarily.
- Support both **regime-aligned** and **non-state** actors using the same
  concepts (militia, cartels, rogue forces).

---

## 2. Force Taxonomy

Force on Dosadi is modeled as **capability bundles** rather than rigid unit
tables. Individual factions may combine these bundles differently.

Each force type has:

```yaml
id:              # e.g. mil_street_enforcers
class:           # garrison | patrol | assault | rapid_response | clandestine | support
role:            # short human label
description:     # core use case
typical_size:    # microcell | squad | platoon | company | dispersed_network
equipment_grade: # low | medium | high | elite
suit_dependency: # none | light | exo_required
infrastructure_reliance:
  - type_id      # infra ids from §3
ward_profile_fit:
  # qualitative hints for coupling to WardAttributes (D-WORLD-0002)
  prefers:       # e.g. high_garrison_presence, open_or_mixed_ventilation, high_corridor_centrality
  avoids:        # e.g. sealed_core, extreme_toxicity
notes:           # hooks into law, industry, black markets
```

### 2.1 Street Enforcers

```yaml
id: mil_street_enforcers
class: garrison
role: "Street Enforcers"
description: >
  Local, semi-permanent armed presence used to enforce ration rules, quell
  small disturbances, and show the flag in dense habitation and market areas.
typical_size: squad
equipment_grade: low
suit_dependency: light
infrastructure_reliance:
  - mil_local_barracks
  - mil_watchposts
ward_profile_fit:
  prefers:
    - high_habitation
    - medium_corridor_centrality
    - moderate_garrison_presence
  avoids:
    - sealed_ultra_elite_core_only
notes: >
  Often recruited locally; loyalty mixed. Can be partially co-opted by cartels
  and black markets in low-audit wards.
```

### 2.2 Corridor Troops

```yaml
id: mil_corridor_troops
class: patrol
role: "Corridor Troops"
description: >
  Units tasked with patrolling and securing key logistics corridors, junctions,
  and transfer points along barrel cadence routes and trolley tracks.
typical_size: squad | platoon
equipment_grade: medium
suit_dependency: light
infrastructure_reliance:
  - mil_corridor_posts
  - mil_armory_nodes
  - mil_signal_hubs
ward_profile_fit:
  prefers:
    - high_corridor_centrality
    - medium_structural_capacity
    - proximity_to_bulk_depots
  avoids:
    - deep_dead_end_wards_with_no_through_traffic
notes: >
  Their presence defines what routes are 'safe' for official traffic and where
  smuggling must route around.
```

### 2.3 Garrison Units

```yaml
id: mil_garrison_units
class: garrison
role: "Ward Garrison"
description: >
  Larger, more static formations maintaining order, defending key infra, and
  acting as a local reserve for response operations.
typical_size: company
equipment_grade: medium
suit_dependency: mixed
infrastructure_reliance:
  - mil_garrison_barracks
  - mil_armory_nodes
  - mil_motor_pools
  - mil_signal_hubs
ward_profile_fit:
  prefers:
    - high_garrison_presence
    - high_structural_capacity
    - moderate_to_high_corridor_centrality
  avoids:
    - extremely_toxic_ruins_with_no_population
notes: >
  Where garrison presence is high, overt organized resistance must be subtle,
  asymmetric, or deeply embedded in logistics and industry.
```

### 2.4 Exo-Suit Cadres

```yaml
id: mil_exo_cadres
class: assault
role: "Exo-Suit Cadres"
description: >
  Heavy mechanized infantry using exo-suits for lifting, breaching, and taking
  or holding difficult positions, especially in dirty industrial and outer wards.
typical_size: squad
equipment_grade: high
suit_dependency: exo_required
infrastructure_reliance:
  - mil_exobays_authorized
  - mil_exo_armories
  - mil_power_feeds
  - mil_heavy_lift_points
ward_profile_fit:
  prefers:
    - high_structural_capacity
    - open_or_mixed_ventilation
    - proximity_to_fabrication_and_suit_industries
  avoids:
    - sealed_high_hvac_admin_cores
notes: >
  Use in sealed cores is rare and politically significant. Their mere staging
  in a ward is a powerful threat signal and requires support from industry
  (FABRICATION, SUITS, ENERGY_MOTION).
```

### 2.5 Rapid-Response Teams

```yaml
id: mil_rapid_response
class: rapid_response
role: "Rapid-Response Teams"
description: >
  Mobile, well-equipped teams used to respond to incidents (riots, sabotage,
  collapses, high-value arrests) across multiple wards.
typical_size: squad
equipment_grade: high
suit_dependency: light
infrastructure_reliance:
  - mil_command_nodes
  - mil_signal_hubs
  - mil_corridor_priority_access
  - mil_motor_pools
ward_profile_fit:
  prefers:
    - high_corridor_centrality
    - sealed_or_mixed_cores_for_staging
  avoids:
    - extreme_dead_ends (hard_to_reach_rapidly)
notes: >
  Their staging location and response routes create 'time-to-crackdown' maps
  across the city, shaping risk calculations for dissent.
```

### 2.6 Clandestine Cells

```yaml
id: mil_clandestine_cells
class: clandestine
role: "Clandestine Cells"
description: >
  Small, covert units conducting surveillance, targeted killings, or sabotage,
  often indistinguishable from black-market muscle or ordinary residents.
typical_size: microcell
equipment_grade: medium
suit_dependency: none
infrastructure_reliance:
  - mil_safehouses
  - civ_bunkhouses
  - civ_canteens
ward_profile_fit:
  prefers:
    - low_to_medium_audit_intensity
    - complex_corridor_graphs
    - mixed_or_open_ventilation
  avoids:
    - hyper_monitored_sealed_admin_cores
notes: >
  Can be regime-aligned (secret police) or opposition; built from same basic
  mechanics as BLACK_MARKET and INFO_SECURITY actors.
```

### 2.7 Support & Logistics Units

```yaml
id: mil_support_logistics
class: support
role: "Support & Logistics Units"
description: >
  Non-frontline teams that maintain equipment, move supplies, and keep bases
  functioning. They heavily overlap with civilian logistics and industry roles.
typical_size: squad | platoon
equipment_grade: medium
suit_dependency: light
infrastructure_reliance:
  - mil_garrison_barracks
  - mil_motor_pools
  - mil_supply_depots
  - civ_bulk_depots
ward_profile_fit:
  prefers:
    - proximity_to_LOGISTICS_CORRIDORS
    - access_to_FABRICATION_and_ENERGY_MOTION_infra
  avoids:
    - extreme_ruins_without_stable_supply_routes
notes: >
  Often share labor pools and infrastructure with civilian logistics workers,
  creating blurred lines between conscription, contract, and coercion.
```

---

## 3. Military Infrastructure Types

Infrastructure nodes are **physical places or installations** which enable force
projection. Multiple factions may compete over or share use of a given node.

Each infrastructure type has:

```yaml
id:              # e.g. mil_garrison_barracks
category:        # housing | armory | exo_bay | checkpoint | signal | logistics | detention | command
label:           # human-readable name
description:     # function
typical_scale:   # room | block | ward
structural_load: # low | medium | high
ventilation_needs: # prefers_open | prefers_mixed | prefers_sealed
ward_profile_fit:
  prefers:       # qualitative hints for WardAttributes
  avoids:
linked_industries:
  # industry families/types from D-IND-0001
  - WATER_ATMOSPHERE
  - FABRICATION
  - SUITS
notes:
```

### 3.1 Garrison Barracks

```yaml
id: mil_garrison_barracks
category: housing
label: "Garrison Barracks"
description: >
  Concentrated housing, mess, and basic training space for garrison units
  and street enforcers, often co-located with armories.
typical_scale: block
structural_load: medium
ventilation_needs: prefers_mixed
ward_profile_fit:
  prefers:
    - moderate_to_high_habitation
    - medium_corridor_centrality
    - open_or_mixed_ventilation
  avoids:
    - extremely_toxic_ruin
linked_industries:
  - FOOD_BIOMASS
  - HABITATION
  - WATER_ATMOSPHERE
notes: >
  Barracks are both a consumption site (food, water) and a source of labor
  demand (conditioning, health, suits).
```

### 3.2 Local Barracks & Watchposts

```yaml
id: mil_local_barracks
category: housing
label: "Local Barracks & Watchposts"
description: >
  Small fortified positions embedded in neighborhoods for street enforcers
  and small patrols.
typical_scale: room | small_block
structural_load: low
ventilation_needs: prefers_mixed
ward_profile_fit:
  prefers:
    - dense_habitation
    - key_intersections
  avoids:
    - abandoned_ruins
linked_industries:
  - HABITATION
  - FOOD_BIOMASS
notes: >
  Important for moment-to-moment perception of regime presence and for rumor
  propagation about 'who is watching'.
```

### 3.3 Armory Nodes

```yaml
id: mil_armory_nodes
category: armory
label: "Armory Nodes"
description: >
  Storage and maintenance sites for weapons, armor, and some suit components.
typical_scale: block
structural_load: medium
ventilation_needs: prefers_mixed
ward_profile_fit:
  prefers:
    - moderate_structural_capacity
    - moderate_to_high_garrison_presence
    - moderate_audit_intensity
  avoids:
    - heavily_cartel_dominated_low_loyalty_wards
linked_industries:
  - FABRICATION
  - SUITS
  - ENERGY_MOTION
notes: >
  Heavy overlap with Tool & Weapon Forges, Pump & Valve Works, and Machine-Tool
  Shops; control of armories marks effective control of organized violence.
```

### 3.4 Authorized Exo-Bays

```yaml
id: mil_exobays_authorized
category: exo_bay
label: "Authorized Exo-Suit Bays"
description: >
  High-security bays for storing, maintaining, and refitting heavy exo-suits
  used in industry and military operations.
typical_scale: block
structural_load: high
ventilation_needs: prefers_open_or_mixed
ward_profile_fit:
  prefers:
    - high_structural_capacity
    - open_or_mixed_ventilation
    - proximity_to_FABRICATION_SUITS_ENERGY
  avoids:
    - sealed_elite_admin_cores
    - very_low_power_quota
linked_industries:
  - FABRICATION
  - SUITS
  - ENERGY_MOTION
notes: >
  Their distribution defines where heavy power can be rapidly projected. Bays
  in outer, dirty wards serve as both industrial and military nodes.
```

### 3.5 Black Mod Garages

```yaml
id: mil_exobays_clandestine
category: exo_bay
label: "Clandestine Mod Garages"
description: >
  Hidden or semi-hidden workshops modifying exo-suits and suits for illicit
  performance, stealth, or unauthorized armament.
typical_scale: room | workshop
structural_load: medium
ventilation_needs: prefers_open_or_mixed
ward_profile_fit:
  prefers:
    - low_to_medium_audit_intensity
    - complex_corridor_graphs
    - open_or_mixed_ventilation
  avoids:
    - sealed_heavily_monitored_cores
linked_industries:
  - SUITS
  - BLACK_MARKET
  - FABRICATION
notes: >
  Functionally overlap with black-market mod garages (D-IND-0001, SUITS family);
  this infra type exists so that military actors can explicitly track, co-opt,
  or hunt them.
```

### 3.6 Corridor Checkpoints & Posts

```yaml
id: mil_corridor_posts
category: checkpoint
label: "Corridor Checkpoints & Posts"
description: >
  Fortified points along corridors where traffic is inspected, taxed, delayed,
  or turned back. Some are permanent; others are temporary or crisis-only.
typical_scale: room | small_block
structural_load: medium
ventilation_needs: prefers_open_or_mixed
ward_profile_fit:
  prefers:
    - high_corridor_centrality
    - junctions_near_bulk_depots
  avoids:
    - dead_end_side_corridors
linked_industries:
  - ENERGY_MOTION
  - WATER_ATMOSPHERE
  - LOGISTICS (via D-ECON-0001)
notes: >
  Checkpoints are where legal regimes and black markets visibly meet. Control
  here largely defines who really controls movement.
```

### 3.7 Signal Hubs & Command Nodes

```yaml
id: mil_signal_hubs
category: signal
label: "Signal Hubs & Command Nodes"
description: >
  Nodes for wired or line-of-sight signaling, command coordination, and
  dispatch of rapid-response teams.
typical_scale: room | block
structural_load: low
ventilation_needs: prefers_sealed_or_mixed
ward_profile_fit:
  prefers:
    - moderate_to_high_corridor_centrality
    - sealed_or_mixed_cores
    - high_loyalty_to_regime
  avoids:
    - extreme_toxic_ruins
linked_industries:
  - INFO_ADMIN
  - ENERGY_MOTION
  - FABRICATION (micro-electronics)
notes: >
  Destroying or co-opting signal hubs is a first step in coups or uprisings.
```

### 3.8 Motor/Track Pools

```yaml
id: mil_motor_pools
category: logistics
label: "Motor/Track Pools"
description: >
  Concentrated storage and maintenance for vehicles, trolleys, powered carts,
  and heavy lifters used by garrison and logistics units.
typical_scale: block
structural_load: high
ventilation_needs: prefers_open_or_mixed
ward_profile_fit:
  prefers:
    - high_structural_capacity
    - proximity_to_LOGISTICS_CORRIDORS
    - moderate_toxicity_ruin (industrial collars)
  avoids:
    - sealed_elite_residential_cores
linked_industries:
  - ENERGY_MOTION
  - FABRICATION
  - SCRAP_MATERIALS
notes: >
  Pools shape actual response times and load capacities across the ward graph.
```

### 3.9 Holding Cells & Interrogation Sites

```yaml
id: mil_detention_sites
category: detention
label: "Holding Cells & Interrogation Sites"
description: >
  Sites where detainees are processed, held, and interrogated; often dual-use
  with civil law systems but under military control in crises.
typical_scale: room | small_block
structural_load: low
ventilation_needs: prefers_sealed_or_mixed
ward_profile_fit:
  prefers:
    - near_admin_or_garrison_nodes
    - medium_to_high_audit_intensity
  avoids:
    - extremely_cartel_dominated_zones_without_regime_presence
linked_industries:
  - BODY_HEALTH
  - INFO_ADMIN
notes: >
  A focal point for fear, rumor, and coercive information gathering.
```

### 3.10 Safehouses

```yaml
id: mil_safehouses
category: housing
label: "Safehouses"
description: >
  Low-profile locations for clandestine cells and covert operations staging,
  often indistinguishable from ordinary habitation or commercial spaces.
typical_scale: room | apartment
structural_load: low
ventilation_needs: any
ward_profile_fit:
  prefers:
    - medium_habitation_density
    - low_to_medium_audit_intensity
    - complex_corridor_layouts
  avoids:
    - ultra_regular_gridded_cores_with_total_surveillance
linked_industries:
  - HABITATION
  - BLACK_MARKET
notes: >
  Mechanically share a lot with safehouses from D-ECON-0001; this type exists
  to express explicitly military/intelligence-flavored usage.
```

---

## 4. Coupling Forces & Infrastructure to Wards

### 4.1 Garrison Presence as Derived Attribute

`garrison_presence` (D-WORLD-0002, proposed) can be treated as both:

- A **ward attribute** fed into other systems (law, rumor, black market).
- A **summary output** of the number and capacity of military infra nodes
  anchored in that ward.

Simplified:

```text
garrison_presence(w) ≈
  w_barracks   * weight_barracks
+ w_armories   * weight_armories
+ w_checkpoints* weight_checkpoints
+ w_exobays    * weight_exobays
```

Where `w_barracks` etc. are normalized measures of capacity.

### 4.2 Clean Cores vs Industrial Collars

Using `ventilation_regime`, `hvac_control_level`, `toxicity_ruin`, and `pollution_sink_index`:

- **Sealed, high-HVAC, low-toxicity cores**:
  - Favor:
    - Signal hubs, command nodes.
    - Small, elite garrison barracks.
    - Admin-leaning detention sites.
  - Avoid:
    - Heavy exo-bays, large motor pools, dirty training grounds.

- **Open/mixed wards with high pollution_sink_index and moderate toxicity**:
  - Favor:
    - Garrison barracks, motor pools, corridor posts.
    - Authorized exo-bays and weapon-heavy armories.
  - Often co-locate with:
    - FABRICATION, SCRAP_MATERIALS, dirty FOOD_BIOMASS industries.

- **Extreme toxic ruins**:
  - Limited to:
    - Low-visibility safehouses.
    - Occasional hardened exo staging in specialized suits.
  - Generally unsuited to permanent, overt garrisons.

### 4.3 Corridor Centrality & Response Time

`corridor_centrality` and logistics topology determine how **rapid-response teams**
and **corridor troops** deploy:

- Wards with high centrality and nearby motor pools become **staging hubs**.
- Dead-ends and long, narrow branches become **slow-response zones**, inviting
  black-market concentration and rebellions that rely on “time to crackdown”.

Simulation can approximate **response time** between a staging ward `s` and a
target ward `w` using:

```text
response_time(s, w) ≈ path_length(s, w) / mobility_factor(s)
```

Where `mobility_factor(s)` increases with local motor pools, corridor control,
and structural capacity.

---

## 5. Military–Industry Dependencies

Force projection is dependent on industry presence. Some links:

- **SUITS + FABRICATION + ENERGY_MOTION**  
  - Required for exo-cadres, mod garages, heavy weapon maintenance.
  - Wards lacking these cannot sustain high-end mechanized forces long-term.

- **FOOD_BIOMASS + HABITATION**  
  - Strongly coupled to garrison barracks and training houses.
  - Food and sleep constraints bind maximum garrison size and surge duration.

- **WATER_ATMOSPHERE**  
  - Garrison size tied to local water quota and atmospheric capture capacity.
  - Crackdowns and troop surges temporarily spike water demand.

- **INFO_ADMIN**  
  - Signal hubs, registry and ledger houses provide visibility on populations
  and logistics; they multiply effectiveness of early warning and response.

- **BLACK_MARKET**  
  - Black mod garages, arms diversion, and cartel protection crews operate
  as *shadow military infrastructure* and *shadow forces*.
  - Sometimes co-opted by official forces for plausible deniability.

This means that military build-up in a ward mechanically competes with or
amplifies local industrial and civic sectors, rather than sitting on top of
them for free.

---

## 6. Usage in Simulation

At a high level, simulation can:

1. **Instantiate WardAttributes** for each ward (D-WORLD-0002).
2. **Evaluate suitability** for each infra type in §3 based on WardAttributes.
3. Allow factions (dukes, bishops, cartels, militias) to:
   - Propose, build, or abandon infrastructure according to their goals and means.
4. From infra presence, **derive garrison_presence** and force type availability.
5. Use force types and infra to:
   - Simulate crackdowns, coups, revolts, and corridor conflicts.
   - Modify risk calculations for agents and industries in each ward.

Over time, the **military geography** of Dosadi emerges from the same forces that
shape economic geography, rather than as a static overlay.

---

## 7. Follow-Up Documents (Non-Normative)

Suggested future military pillar docs:

- `D-MIL-0002_Force_Doctrine_and_Rules_of_Engagement`  
  - How different factions prefer to use force types (deterrence vs terror,
    surgical vs indiscriminate).

- `D-MIL-0003_Response_Cadences_and_Alert_Levels`  
  - Time scales and triggers for escalating responses, from patrol questioning
    to full exo-cadre deployment.

- `D-MIL-0004_Morale_Discipline_and_Defection`  
  - How pay, food, ideology, and fear drive behavior of rank-and-file forces
    and commanders, including desertion and side-switching.

These should all reference concepts and ids defined in `D-MIL-0001`.
