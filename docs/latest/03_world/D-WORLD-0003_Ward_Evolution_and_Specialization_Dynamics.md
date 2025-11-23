---
title: Ward_Evolution_and_Specialization_Dynamics
doc_id: D-WORLD-0003
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
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

# 02_world · Ward Evolution and Specialization Dynamics (D-WORLD-0003)

## 1. Purpose

This document defines how wards on Dosadi **change over time**.

Rather than being hard-coded into fixed archetypes, wards are treated as
**stateful systems** that:

- Respond to **environmental constraints** (geometry, exposure, HVAC),
- Accrete and lose **industries and guild power**,
- Experience shifting **law, MIL posture, and rumor regimes**,
- Drift toward or away from recognizable **specializations**.

Goals:

- Provide a consistent model of ward **state vectors** and pressures.
- Define update loops that connect existing pillars (IND, ECON, MIL, LAW, INFO).
- Describe how recognizable patterns like “outer industrial bastion” or
  “civic feed ward” can **emerge as attractors**, not initial assumptions.
- Give simulation code and scenario authors clear hooks for:

  - long-run campaign arcs, and
  - localized transformations (e.g., a “calm” ward becoming a crackdown ward).

This is a **logic doc**; numeric specifics are left to implementation.

---

## 2. Ward State Vector

Each ward `w` has a **state vector** `S_w` composed of:

- **Structural attributes** (mostly slow-changing):
  - Topology: distance from core, corridor connectivity, lift/pipe adjacency.
  - HVAC status: sealed/partially sealed/open.
  - Physical capacity: population capacity, industrial floor space.

- **Socioeconomic and institutional attributes** (medium-changing):
  - Industry mix and intensity by category.
  - Guild power and presence.
  - Cartel and black market intensity.
  - Bishop and civic infrastructure footprint.

- **Control and law attributes** (medium-fast changing):
  - Garrison presence and posture.
  - Legal state and sanction/law indices.
  - Case handling patterns and tribunal frequency.

- **Sentiment and rumor attributes** (fast-changing):
  - Unrest, loyalty, fear, rumor density, rumor motifs.

Conceptually:

```text
S_w = (structure_w, industry_w, guilds_w, cartel_w,
       mil_w, law_w, econ_w, sentiment_w, rumor_w)
```

`D-WORLD-0002` defines many of the raw indices; this document focuses on
**how they co-evolve**.

---

## 3. Structural and Baseline Constraints

### 3.1 Structural frame (slow)

The following are treated as **slow** or near-fixed on the timescales of most
scenarios:

- Distance from core / ring position.
- Corridor and lift connectivity (graph structure).
- HVAC regime (sealed / partially sealed / open).
- Major physical footprints (large industrial slabs, cavern shapes, etc.).

These limit which changes are feasible:

- A fully sealed core ward cannot cheaply become a smoke-belching refinery.
- A low-connectivity cul-de-sac ward is a poor candidate for “lift ring” roles.
- Outer wards have better access to external venting and waste dumping.

Implementation may encode these as:

```yaml
structure_w:
  ring_position: "inner" | "mid" | "outer"
  hvac_regime: "sealed" | "partial" | "open"
  corridor_centrality: float
  lift_access: float
  industrial_floor: float
  habitation_capacity: float
```

### 3.2 Baseline suitability (from D-IND-0002)

For each industry family `I`, each ward has a **baseline suitability**:

```yaml
industry_suitability[w][I]: float   # 0–1
```

Derived from:

- structure_w,
- access to barrels and water,
- environmental constraints (venting, heat dissipation),
- proximity to existing related industries.

These suitability scores **do not determine** what is present, but they
shape the **cost** of building and maintaining industries.

---

## 4. Pressure Sources on Ward Evolution

Ward evolution is driven by **pressures**, which we group into four broad
families.

### 4.1 Economic and industrial pressures

- Regime demand for:
  - specific outputs (suits, food, energy, fabrication),
  - throughput at certain corridors or lifts.
- Guild expansion or contraction:
  - seeking new sites for growth,
  - abandoning or downsizing uneconomical sites.
- Cartel opportunities:
  - exploiting weak oversight,
  - filling gaps in supply (food, water, parts, medicine).

These pressures tend to:

- Move industry mix toward **comparative advantages** under constraints.
- Encourage cluster formation (guilds forming local hegemonies).

### 4.2 Security and military pressures

- Perceived or real threats (sabotage, strikes, dissent, cartel violence).
- Strategic considerations:
  - need for garrison staging near outer sectors,
  - securing key lifts and condensate hubs,
  - defending cores and high-ranked nobles.

These pressures adjust:

- `garrison_presence(w)`, `checkpoint_density(w)`, `exo_bay_density(w)`.
- Legal states and sanction intensity (via D-LAW-*).

### 4.3 Law, procedure, and political pressures

- Regime political priorities:
  - punishing disloyal wards,
  - rewarding compliant or productive wards.
- Internal regime factions:
  - audits vs militia vs dukes vs bishops vs guilds.
- Public legitimacy concerns:
  - visible injustices,
  - famines or shortages.

These shape:

- `sanction_intensity(w)`, `legal_opacity(w)`, `due_process_index(w)`,
  `collective_punishment_risk(w)`.
- Which procedural paths dominate (Administrative, Guild Arbitration,
  Security Tribunals, etc.).

### 4.4 Sentiment and rumor pressures

- Unrest spikes after sanctions, accidents, or perceived injustice.
- Rumor motifs that:
  - lionize rebels or martyrs,
  - demonize or ridicule regime or guilds,
  - signal safe vs unsafe spaces for speech and organization.

These can:

- Push wards toward rebellious or sullen-compliant equilibria.
- Influence where cartels and guilds recruit or hide.

---

## 5. Update Loop: From Pressures to Change

We consider a **coarse-grained time step** (e.g. per “campaign phase” or
multi-tick aggregation) in which each ward’s state is nudged by pressures.

At a conceptual level:

```text
S_w(t+1) = S_w(t) + Δ_industry_w + Δ_guilds_w + Δ_mil_law_w + Δ_sentiment_w
           + noise_w
```

Where:

- `Δ_industry_w` : changes in industry presence and intensity.
- `Δ_guilds_w` : shifts in guild power and regional leagues.
- `Δ_mil_law_w` : updates to garrison posture and legal indices.
- `Δ_sentiment_w` : updates to unrest, loyalty, fear.
- `noise_w` : stochastic and unplanned shocks.

Implementation can treat each Δ as a function of:

- Pressures in §4,
- Structural constraints in §3,
- Already-present state (path dependence and inertia).

---

## 6. Industry and Guild Dynamics

### 6.1 Industry gain and loss

For an industry family `I` in ward `w`, track an **intensity**:

```yaml
industry_intensity[w][I]: float  # 0–1
```

Update drivers:

- **Demand signals**:
  - Exogenous scenario needs (e.g. more suits for looming war),
  - Internal network demand (adjacent wards needing spares/energy/food).

- **Costs and friction**:
  - Poor suitability → higher cost, slower growth, higher failure risk.
  - High sanction intensity or frequent raids disrupt operations.

- **Competition and substitution**:
  - Similar industries may cannibalize or complement each other.
  - Cartel shadow production may blur lines between formal and informal.

Rule of thumb:

- Industries with:
  - high suitability,
  - strong guild backing,
  - moderate security pressure,
  - and stable supply chains

  **tend to grow** in that ward.

- Industries with:
  - low suitability,
  - high direct risk (frequent purges),
  - or collapsed guild support

  **tend to shrink or relocate**.

### 6.2 Guild power and presence

From D-IND-0003, each ward has guild power indices:

```yaml
G_power[w][guild_family]: float  # 0–1
```

Guild power responds to:

- Industry intensity in their domains,
- Success or failure in guild-level bargaining and conflict,
- Regime policy (favoring or breaking particular guilds),
- Black market entanglement and cartel pressure.

Positive feedback loops:

- A guild that wins concessions may:
  - Attract more workers,
  - Secure more floor space and licenses,
  - Increase its bargaining power further.

Negative loops:

- A guild that suffers repeated sanctions or failed strikes may:
  - Lose members,
  - Fragment into factions or splinter guilds,
  - See its power diffused into cartels or rivals.

---

## 7. Law, MIL, and Specialization Attractors

While wards are not initially archetyped, **attractor patterns** can emerge.

### 7.1 Example attractor: Outer Industrial Bastion

Characteristic configuration:

- Structure:
  - Outer ring position, high venting capacity, high industrial floor.
- Industry:
  - High FABRICATION_HEAVY, SUITS_FABRICATION, ENERGY_MOTION.
- Guilds:
  - Strong FABRICATION_MECH, SUITS_CORE, ENERGY_MOTION guilds.
- MIL:
  - High garrison presence, medium-high exo_bay density.
- LAW:
  - Moderate–high sanction intensity, mid–high legal opacity.
- Sentiment:
  - Mixture of resentment and dependence; high accident rumors.

Emergence pathway:

- Initial placement of heavy industry in an outer ward for structural reasons.
- Demand-driven expansion of fabrication and suits.
- Regime responds with increased garrison and stricter law due to sabotage risk.
- Guilds consolidate and form a regional league (Industrial Spine).
- Over time, the configuration stabilizes: small shocks do not easily change it.

### 7.2 Example attractor: Civic Feed Ward

Characteristic configuration:

- Structure:
  - High habitation capacity, corridor centrality moderated by lifts/corridors.
- Industry:
  - Medium FOOD_PRODUCTION, WASTE_TO_FOOD, service roles.
- Guilds:
  - FOOD_BIOMASS allied with bishop_guild.
- MIL:
  - Moderate garrison presence, relatively more liaison posts than exo-bays.
- LAW:
  - Sanction intensity focused on **ration cuts** and crowd management.
- Sentiment:
  - High rumor density, frequent talk of “thinner rations” and favoritism.

Emergence pathway:

- Ward gradually filled with bunkhouses and canteens to serve adjacent
  industrial or core wards.
- Food guilds and bishops co-govern survival spaces.
- Regime uses targeted resource sanctions for behavior shaping.
- Cartels emerge to supplement rations and provide “side channels.”
- Over time, the ward becomes the barometer of popular sentiment.

### 7.3 Example attractor: Shadow Ward

Characteristic configuration:

- Structure:
  - Edge or cul-de-sac connectivity, or awkward hinge positioning.
- Industry:
  - Fragmented, low intensity; mix of marginal activities.
- Guilds:
  - Weak guild power, fractured representation.
- MIL:
  - Either low presence (neglect) or high but corrupt presence.
- LAW:
  - High legal opacity and collective punishment risk.
- Cartel:
  - Very high black market intensity, cartel “justice” supplants state law.

Emergence pathway:

- Wards that never receive strong guild investment and are politically
  unfavored gradually become **dumping grounds**.
- Neglected enforcement shapes conditions where cartels fill gaps.
- Rumor frames the ward as lawless, cursed, or “not worth saving.”

---

## 8. Evolution Events and Shocks

In addition to gradual drift, wards can experience **events** that cause sharp
changes:

### 8.1 Industrial shock

- Major accident, catastrophe, or sabotage in a key facility.
- Effects:
  - Sudden drop in specific industry intensity.
  - Spike in `unrest_index(w)` and targeted rumor.
  - Opportunity for regime to:
    - reshape industry mix,
    - reassign guild rights,
    - adjust MIL posture.

### 8.2 Political shock

- High-profile tribunal verdict, purge, or coup attempt.
- Effects:
  - Rapid change in LAW and MIL indices.
  - Potential reclassification of wards as “trusted,” “suspect,” or “enemy.”

### 8.3 Resource shock

- Water or food supply crisis (e.g., condensate failure, contamination).
- Effects:
  - spikes in shortage and unrest,
  - increased cartel leverage,
  - shifts in guild bargaining positions.

### 8.4 Regime policy shift

- New duke decree, audit campaign, or planned industrial redirection.
- Effects:
  - Reallocation of investments and licenses,
  - Intentional attempt to push a ward **toward** a particular attractor
    (industrialization, civic support, or punishing ghettoization).

Implementation should treat shocks as **events** that perturb `S_w` and its
pressures, sometimes pushing it out of one attractor basin toward another.

---

## 9. Implementation Sketch (Non-Normative)

A minimal simulation of ward evolution might:

1. Initialize city:
   - Generate wards with structural attributes (ring position, connectivity,
     hvac, floor space, etc.).
   - Assign initial industry presence based on suitability and scenario seed.
   - Initialize guild presence, garrisons, and law indices at modest levels.

2. At each **macro-step** (e.g., per “campaign season”):
   - For each ward `w`:
     - Evaluate economic, MIL, law, and sentiment pressures.
     - Adjust:
       - industry_intensity[w][I],
       - G_power[w][F],
       - garrison_presence[w], checkpoint behavior,
       - law-related indices (sanction intensity, etc.),
       - sentiment and rumor indices.
   - Apply any scheduled or triggered **shocks**.
   - Optionally classify wards into **current pattern labels** (for reporting
     only), e.g. “looks like an Industrial Spine node.”

3. Use these evolved ward states as:
   - Context for agent behavior and micro-scenarios,
   - Inputs for higher-level strategy (dukes, guild councils, cartels).

The key constraint: **no ward is forced to remain in a role**; patterns are
outputs of dynamics, not baked-in slots.

---

## 10. Future Extensions

Possible follow-ups:

- `D-WORLD-0101_Ward_Classification_and_Reporting_Views`
  - Purely presentational logic for showing ward states in dashboards
    (e.g., “3 wards trending toward Shadow League conditions”).

- `D-RUNTIME-0002_Long_Horizon_Campaign_Phases`
  - How long-run ward evolution is integrated with shorter tactical
    scenarios (e.g., Sting Wave arcs).

- Scenario-specific evolution rules
  - Special case tweaks for particular storylines, like:
    - an engineered famine,
    - an attempted guild revolution,
    - or a slow coup from within the military.
