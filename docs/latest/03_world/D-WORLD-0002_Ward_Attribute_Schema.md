---
title: Ward_Attribute_Schema
doc_id: D-WORLD-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-22
depends_on:
  - D-WORLD-0001          # Wards & environment overview
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-IND-0001            # Industry_Taxonomy_and_Types
  - D-IND-0002            # Industry_Suitability_and_Evolution
  - D-ECON-0001           # Logistics_Corridors_and_Safehouses
  - D-MIL-0001            # Force_Types_and_Infrastructure
---

# 01_world · Ward Attribute Schema (D-WORLD-0002)

## 1. Purpose

This document defines a **canonical schema for ward-level attributes** on Dosadi.

- It is the shared backbone for:
  - Industry suitability and evolution (`13_industry`),
  - Military presence and response (`09_military`),
  - Law, rumor, black market, and agent behavior.
- It is **agnostic** about specific wards and scenarios:
  - No particular ward is defined here.
  - No archetypes are hard-coded.

Simulation configs and content should represent each ward as an instance of this
schema (or a compatible subset/superset).

---

## 2. Ward Identity Fields

Basic identity and bookkeeping for a ward `w`:

```yaml
ward_id: string         # machine id, unique, e.g. "ward:12"
display_name: string    # human-facing label, e.g. "Copper Stair"
tier: integer           # optional coarse layer index (e.g. 0=lowest, 1=mid, 2=upper)
notes: string           # freeform description, flavor, history
```

- `ward_id` SHOULD be stable and referenced across pillars (industry, military, law,
  agents, scenarios).
- `tier` is purely advisory; fine-grained math should use `elevation` and corridor
  structure instead.

---

## 3. Spatial & Topological Attributes

These describe the **physical placement and connectivity** of a ward.

All continuous values are in `[0.0, 1.0]` unless otherwise noted.

```yaml
dist_to_well: float        # 0 = adjacent, 1 = farthest practical along routes
elevation: float           # 0 = lowest tier, 1 = highest tiers (max lift cost)
corridor_centrality: float # 0 = dead-end, 1 = critical routing hub
structural_capacity: float # 0 = fragile, 1 = supports heavy infra and exo-bays
toxicity_ruin: float       # 0 = clean/stable, 1 = heavily contaminated/ruined
ambient_temp: float        # 0 = cool/shaded, 1 = hottest local conditions
```

**Intended use (non-normative):**

- `dist_to_well` and `elevation` drive water cost and barrel cadence risk.
- `corridor_centrality` shapes logistics, smuggling routes, and response times.
- `structural_capacity` gates heavy industry and exo-suit infrastructure.
- `toxicity_ruin` influences habitation, scrap industries, and health outcomes.
- `ambient_temp` modifies comfort, suit load, and suitability for some industries.

---

## 4. Atmosphere & Ventilation Attributes

These capture the **sealed vs unsealed** character of a ward and how it handles
airborne contaminants.

```yaml
ventilation_regime: string    # enum: "open" | "mixed" | "sealed"
hvac_control_level: float     # 0 = none, 1 = advanced zoned HVAC
pollution_sink_index: float   # 0 = retains exhaust, 1 = downwind/sacrificial
```

- `ventilation_regime`:
  - `open`   – largely unsealed; air exchanges freely with neighbors/outside.
  - `mixed`  – mixture of sealed interiors and shared/dirty air.
  - `sealed` – strongly controlled HVAC; limited exchange with outside.

- `hvac_control_level`:
  - Low values: simple fans, ad-hoc vents, no fine control.
  - High values: filtering, selective routing, pressure/flow tuning.

- `pollution_sink_index`:
  - High values indicate that the ward **receives or disposes of** other wards'
    airborne contaminants (downwind drain, roof exhaust, etc.).
  - Low values indicate **protected airspace**; pollution tends to stay inside
    unless deliberately routed away.

These three fields are central to the emergence of **clean admin cores** and
**dirty industrial collars**.

---

## 5. Resource & Infrastructure Attributes

These describe how well the ward is supplied with basic flows and inputs.

```yaml
water_quota: float         # 0 = chronic shortage, 1 = ample for planned loads
power_quota: float         # 0 = frequent blackouts, 1 = stable grid supply
local_generation: float    # 0 = no local gen, 1 = strong decentralized capacity
scrap_access: float        # 0 = scarce scrap, 1 = abundant dumps/flows
food_buffer: float         # 0 = near-starvation, 1 = strong local food resilience
habitation_density: float  # 0 = almost empty, 1 = extremely crowded
population_scale: float    # 0 = tiny, 1 = among the largest wards
```

- `water_quota`: combines allocation policy + barrel cadence + intra-ward networks.
- `power_quota`: baseline availability from central grid hubs.
- `local_generation`: fallback/independent power (generators, digesters, etc.).
- `scrap_access`: proximity to scrap piles, ruins, burn pits, dumps.
- `food_buffer`: ability to ride out disruptions via local stocks and production.
- `habitation_density`: crowding level; interacts with disease, rumor, control.
- `population_scale`: relative population size, independent of density.

These fields are heavily used by `13_industry`, `09_military`, and health/economy
pillars.

---

## 6. Political & Social Attributes

These describe **who effectively runs the ward**, how tightly rules are applied,
and the nature of the population and garrison.

```yaml
dominant_owner: string      # enum: "duke_house" | "bishop_guild" | "cartel" | "militia" | "central_audit_guild" | "mixed"
audit_intensity: float      # 0 = almost no real audits, 1 = constant hard audits
legal_rigidity: float       # 0 = flexible/negotiated rules, 1 = strictly enforced codes
garrison_presence: float    # 0 = barely any troops, 1 = heavy permanent garrison
skilled_labor_share: float  # 0 = almost all unskilled, 1 = highly skilled population
loyalty_to_regime: float    # 0 = hostile/alienated, 1 = strongly aligned
black_market_intensity: float # 0 = negligible, 1 = dominant parallel economy
fear_index: float           # 0 = population feels safe to dissent, 1 = terrified of coercion
```

Notes:

- `dominant_owner` is the **primary structural power**, not the only one. It can
  be used as a prior for faction behavior and infrastructure decisions.
- `audit_intensity` vs `legal_rigidity`:
  - High audit, low rigidity: many inspections but flexible enforcement.
  - Low audit, high rigidity: strict codes exist, but rarely checked.
- `garrison_presence` can be:
  - Directly set in scenario configs, or
  - Derived from military infrastructure (see D-MIL-0001).

- `black_market_intensity` expresses the **density of illicit flows** relative
  to official flows, independent of legality on paper.
- `fear_index` is a coarse cultural/psychological measure, used for agent risk
  calculations, rumor behavior, and likelihood of open protest.

---

## 7. Optional / Derived Indices

Some attributes are convenient **aggregates or derived fields**; the simulation
may recompute these rather than store them as source-of-truth.

### 7.1 Economic Focus Indices

```yaml
industry_weight:
  WATER_ATMOSPHERE: float
  FOOD_BIOMASS: float
  BODY_HEALTH: float
  SCRAP_MATERIALS: float
  FABRICATION: float
  SUITS: float
  ENERGY_MOTION: float
  HABITATION: float
  INFO_ADMIN: float
  BLACK_MARKET: float
```

- Each value is typically in `[0, 1]` and may be normalized so the vector sums
  to 1.0 or less than/equal to 1.0.
- These reflect **current realized capacity or throughput**, not potential.
- They can be:
  - Directly set at scenario start, or
  - Computed from the sum of instantiated industries (D-IND-0001) in the ward.

### 7.2 Military & Security Indices

```yaml
military_weight:
  garrison_units: float
  street_enforcers: float
  corridor_troops: float
  exo_cadres: float
  rapid_response: float
  clandestine_cells: float
```

- These can be derived from infra presence (`D-MIL-0001`) and scenario setup.
- They are **not** strictly required by all systems, but allow quick queries like
  “where are exo-capable forces concentrated?”

### 7.3 Distress / Instability Indicators

```yaml
unrest_index: float        # 0 = quiescent, 1 = near/upon open revolt
shortage_index: float      # 0 = plenty, 1 = acute shortages (water/food/power)
disease_pressure: float    # 0 = minimal, 1 = widespread serious disease
```

- These can be outputs of simulation loops (health, economy, law) but are
  included here to standardize names and ranges across pillars.

---

## 8. Minimal Example

A minimal example of a ward instance in YAML form:

```yaml
ward_id: "ward:12"
display_name: "Copper Stair"
tier: 1
notes: "Mid-elevation corridor hub connecting inner sealed cores to two dirty outer wards."

dist_to_well: 0.35
elevation: 0.45
corridor_centrality: 0.78
structural_capacity: 0.72
toxicity_ruin: 0.40
ambient_temp: 0.55

ventilation_regime: "mixed"
hvac_control_level: 0.4
pollution_sink_index: 0.6

water_quota: 0.65
power_quota: 0.70
local_generation: 0.30
scrap_access: 0.50
food_buffer: 0.55
habitation_density: 0.75
population_scale: 0.60

dominant_owner: "bishop_guild"
audit_intensity: 0.6
legal_rigidity: 0.5
garrison_presence: 0.7
skilled_labor_share: 0.4
loyalty_to_regime: 0.5
black_market_intensity: 0.6
fear_index: 0.7

industry_weight:
  WATER_ATMOSPHERE: 0.4
  FOOD_BIOMASS: 0.5
  BODY_HEALTH: 0.3
  SCRAP_MATERIALS: 0.4
  FABRICATION: 0.5
  SUITS: 0.5
  ENERGY_MOTION: 0.4
  HABITATION: 0.6
  INFO_ADMIN: 0.3
  BLACK_MARKET: 0.5

military_weight:
  garrison_units: 0.6
  street_enforcers: 0.7
  corridor_troops: 0.5
  exo_cadres: 0.3
  rapid_response: 0.4
  clandestine_cells: 0.5

unrest_index: 0.4
shortage_index: 0.3
disease_pressure: 0.2
```

This example is **illustrative only**; actual values should be scenario- and
simulation-specific.

---

## 9. Usage & Extension

- Pillars SHOULD treat this schema as the **authoritative vocabulary** for ward
  attributes. If a new cross-cutting attribute is needed, it SHOULD be added
  here and referenced by id.
- Scenario configs MAY omit attributes; missing values SHOULD be filled with
  defaults or inferred from higher-level patterns (e.g. tier templates).
- Implementation MAY maintain richer internal structures (e.g. full corridor
  graphs, per-block micro-attributes) as long as they can be summarized into
  this ward-level schema for cross-pillar communication.

This document is expected to iterate as new pillars (law, health, info_security,
economy) refine the set of shared ward-level concepts.
