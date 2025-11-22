---
title: Industry_Suitability_and_Evolution
doc_id: D-IND-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-21
depends_on:
  - D-WORLD-0001
  - D-RUNTIME-0001
  - D-ECON-0001
  - D-ECON-0003
  - D-IND-0001
---

# 13_industry · Industry Suitability and Evolution (D-IND-0002)

## 1. Purpose

This document specifies **how wards drift into industrial specializations over time** without
hard-coded archetypes.

It defines:

- A **Ward Attribute Vector** capturing geography, environment, and politics.
- A **Family-Level Suitability Model** that scores how well a ward supports each
  industry family from D-IND-0001.
- A **Drift & Cluster Model** that explains how initial suitability, reinforcement,
  and shocks cause specializations to emerge.

This is a logic document for simulation code and content design; it does not define
specific ward instances.

---

## 2. Ward Attribute Vector

Each ward `w` is described by a compact attribute vector. Actual code can keep these
as configs or derived values.

### 2.1 Spatial & environmental attributes

- `dist_to_well` (0–1)  
  Normalized distance to the central well along actual logistics routes, not just
  Euclidean distance. 0 = adjacent; 1 = farthest practical ward.

- `elevation` (0–1)  
  Normalized vertical offset. 0 = lowest tier; 1 = highest tiers with highest lift cost.

- `corridor_centrality` (0–1)  
  Graph-centrality of major corridors that pass through the ward (degree, betweenness,
  or similar). 0 = dead-end; 1 = critical hub.

- `structural_capacity` (0–1)  
  Aggregate ability to host heavy equipment:
  - 0 = fragile, patchwork, prone to collapse.
  - 1 = engineered for heavy loads, anchor points everywhere.

- `toxicity_ruin` (0–1)  
  Long-term contamination and physical ruin level:
  - 0 = clean, stable.
  - 1 = heavily contaminated, unstable ruins.

- `ambient_temp` (0–1)  
  Local warmth relative to Dosadi norm:
  - 0 = cool, shaded.
  - 1 = hot, near industrial heat/waste.

- `ventilation_regime` (enum)  
  - `open`   – largely unsealed; air exchanges freely.
  - `mixed`  – some sealed interiors; much shared/dirty air.
  - `sealed` – strongly controlled HVAC; limited exchange with outside.

- `hvac_control_level` (0–1)  
  - 0 = none / ad-hoc fans.
  - 1 = advanced, zoned HVAC with filtration and selective routing.

- `pollution_sink_index` (0–1)  
  How easy it is for the ward to **dispose of airborne contaminants** elsewhere:
  - 0 = exhaust recirculates locally; sealed, politically protected.
  - 1 = “downwind drain” for dirty neighbors; open and sacrificial.

### 2.2 Resource access & allocations

- `water_quota` (0–1)  
  Fraction of ideal industrial water demand regularly supplied (barrel cadence +
  intra-ward circulation).

- `power_quota` (0–1)  
  Fraction of ideal industrial power demand regularly supplied from grid hubs.

- `local_generation` (0–1)  
  Strength of decentralized generation (local generators, digesters, etc.).

- `scrap_access` (0–1)  
  Access to scrap and waste flows (proximity to dumps, burn pits, ruined levels).

- `food_buffer` (0–1)  
  Reliability of local calorie availability (combination of canteens, growlabs,
  import cadence).

### 2.3 Political & social attributes

- `dominant_owner` (enum)  
  - `duke_house`
  - `bishop_guild`
  - `cartel`
  - `militia`
  - `central_audit_guild`
  - `mixed` (no dominant owner)

- `audit_intensity` (0–1)  
  - 0 = effectively un-audited, records ignored.
  - 1 = hard audits, frequent inspections, high fear of discovery.

- `legal_rigidity` (0–1)  
  - 0 = rules are flexible, negotiated, or ignored.
  - 1 = rules are strictly applied with little informal leeway.

- `garrison_presence` (0–1)  
  - 0 = minimal armed presence.
  - 1 = heavy permanent garrison and rapid-response capability.

- `skilled_labor_share` (0–1)  
  Share of skilled/specialist workers in population.

- `loyalty_to_regime` (0–1)  
  Effective alignment of ward elites and key actors with central regime goals.

---

## 3. Industry Family Suitability

We treat each **family** from D-IND-0001 as a coarse sector. A more detailed model
can later adjust individual industries inside each family.

Families:

- `WATER_ATMOSPHERE`
- `FOOD_BIOMASS`
- `BODY_HEALTH`
- `SCRAP_MATERIALS`
- `FABRICATION`
- `SUITS`
- `ENERGY_MOTION`
- `HABITATION`
- `INFO_ADMIN`
- `BLACK_MARKET`

For each ward `w` and family `F`, we compute:

```text
base_suitability(w, F) in [-1.0, +1.0]
```

Higher = better place to start or expand that family. Negative values do not forbid,
but make survival less likely without special reasons.

Below are qualitative formulas intended for implementation as weighted sums.

### 3.1 WATER_ATMOSPHERE

Core drivers:
- Needs decent water quota, mechanical/power support, and political protection.
- Avoids highly toxic ruins for key assets like wellheads and major plants.

Example scoring:

- Positive terms:
  - High `water_quota`
  - Moderate to high `power_quota`
  - Moderate `corridor_centrality` (for barrel depots and bottling)
  - `dominant_owner` in `{duke_house, bishop_guild}`

- Negative terms:
  - Very high `toxicity_ruin` for sensitive facilities (wellheads, major treatment)
  - Very low `audit_intensity` (regime distrust to host core water infra)
  - `ventilation_regime = sealed` with high `hvac_control_level` for dirty subtypes
    (burny, chemical-heavy operations) – these are pushed to open/unsealed neighbors.

Interpretation:
- Inner wards with good allocations and duke/bishop control become water infra hubs.
- Filthy or politically unreliable wards get only low-grade or peripheral pieces
  (leak scavenging, minor storage, illicit tapping).

### 3.2 FOOD_BIOMASS

Core drivers:
- Needs calories, water, and labor; often tolerant of some pollution.
- Interfaces strongly with habitation and waste flows.

Positive:
- Moderate `water_quota`
- Good `food_buffer` (for initial stocking and resilience)
- Access to `scrap_access` (organic waste streams)
- `dominant_owner` in `{bishop_guild, duke_house}`

Negative:
- Extremely high `toxicity_ruin` (makes food and health perceptions untenable)
- `ventilation_regime = sealed` + high `hvac_control_level` for dirtier subtypes
  (chop houses, fermentation, digesters)

Interpretation:
- Many wards support food industries; cleaner cores tilt toward higher-grade processing
  and nutrition clinics; dirtier wards handle chop, hives, and digesters.

### 3.3 BODY_HEALTH

Core drivers:
- Clinics need cleaner, accessible locations and political backing.
- Corpse processing can tolerate more grime but not extreme ruin that kills workers.

Positive:
- Low to moderate `toxicity_ruin`
- Moderate to high `skilled_labor_share`
- `ventilation_regime` in `{mixed, sealed}` for clinics
- `dominant_owner` includes `bishop_guild`
- Medium `corridor_centrality` (patients and supplies can reach the ward)

Negative:
- Extremely high `pollution_sink_index` for clinics (too hostile for sustained health infra)
- Very low `water_quota` (no hygiene, no care)

Interpretation:
- Clinics cluster where regime wants people to survive and work; corpse processing
  and conditioning houses push closer to dirty/unstable areas but not right into
  the worst ruins.

### 3.4 SCRAP_MATERIALS

Core drivers:
- Thrive where `scrap_access` and toxicity are high, labor is cheap, and cores want
  to externalize externalities.

Positive:
- High `scrap_access`
- Moderate to high `toxicity_ruin`
- Moderate to high `pollution_sink_index`
- `ventilation_regime` in `{open, mixed}`
- Low to medium `audit_intensity`

Negative:
- `ventilation_regime = sealed` with high `hvac_control_level`
- Very high `water_quota` and regime focus on cleanliness (sealed core wards)

Interpretation:
- Scrap industries naturally cluster in “downwind, dirty, structurally robust” wards.
- Clean cores still use the outputs but *export* the processes.

### 3.5 FABRICATION

Core drivers:
- Needs structural capacity, power, and input streams (metal ingots, plastics, etc.).
- Pollution varies by subtype (precision vs heavy).

Positive:
- High `structural_capacity`
- Moderate to high `power_quota` or `local_generation`
- Moderate `scrap_access` (for feedstock)
- `corridor_centrality` for moving finished goods
- `dominant_owner` in `{duke_house, bishop_guild, militia}`

Negative:
- Very high `toxicity_ruin` for precision fabrication and machine tools
- Extreme `pollution_sink_index` for high-precision fabs (they need cleaner air)
- `ventilation_regime = sealed` **plus** low tolerance for industrial noise/pollution
  (policy choice, not just physics)

Interpretation:
- Heavy, dirty fabrication tilts toward industrial collars around cleaner cores.
- Fine machine tools and precision micro-fabs can live in better-controlled,
  semi-clean industrial wards.

### 3.6 SUITS

Core drivers:
- Split between **light suit tailoring** and **exo-suit / heavy bays**.

Light suits, masks, stitching:
- Positive:
  - High `skilled_labor_share` (for quality)
  - `ventilation_regime` in `{mixed, sealed}` (cleaner workshops)
  - Moderate `audit_intensity` (for sanctioned producers)
- Negative:
  - Extreme `toxicity_ruin` (kills craftsmen)

Heavy exo-bays & mod garages:
- Positive:
  - High `structural_capacity`
  - Good `power_quota` + `local_generation`
  - `garrison_presence` high (for sanctioned bays) or `audit_intensity` low (for black mods)
  - `ventilation_regime` in `{open, mixed}` (they dump heat and fumes)
- Negative:
  - `ventilation_regime = sealed` cores (too valuable/clean to host exo smoke and risk)

Interpretation:
- Clean-ish wards attract status suit tailoring and mask shops.
- Industrial/militarized collars host heavy exo-bays and mod garages.

### 3.7 ENERGY_MOTION

Core drivers:
- Grid hubs and pumpways align with political core and structural capacity.
- Local generators and cable crews are more flexible.

Positive:
- High `power_quota` for grid hubs
- High `structural_capacity` for substations and big transformers
- `dominant_owner = duke_house` for core hubs
- `corridor_centrality` high for routing
- `scrap_access` and `local_generation` high for battery shops and generators

Negative:
- Very high `toxicity_ruin` for critical grid nodes (regime prefers them safer)
- Very low `loyalty_to_regime` (hard to entrust grid hubs)

Interpretation:
- Core wards host the main hubs; outlying wards rely on local generators and cable
  crews, with theft and parasitic taps in low-law zones.

### 3.8 HABITATION

Core drivers:
- Needs structural volume plus some water; interacts strongly with ventilation regime.

Positive:
- Moderate `structural_capacity` (for stacked bunks)
- Moderate `water_quota`
- `ventilation_regime` any, but:
  - `sealed + high hvac_control_level` → high-status, admin/elite housing
  - `open + high pollution_sink_index` → low-status bunkhouses and slums

Negative:
- Extremely high `toxicity_ruin` (uninhabitable, except for desperate/temporary use)
- Very low `food_buffer` (population cannot be stably housed)

Interpretation:
- Habitation tends to follow industry and politics: elites in sealed cores, masses
  near dirty work and moisture capture systems.

### 3.9 INFO_ADMIN

Core drivers:
- Needs cleanliness (social and physical), stability, loyal cadres, and strong links
  to regime.

Positive:
- Low to moderate `toxicity_ruin`
- `ventilation_regime` in `{mixed, sealed}` with higher `hvac_control_level`
- High `audit_intensity` and `legal_rigidity`
- High `loyalty_to_regime`
- High `skilled_labor_share`
- Moderate `corridor_centrality` (connectivity for couriers and records)

Negative:
- Very high `pollution_sink_index` (sacrifice zones are not where you put ledgers)
- `dominant_owner` strongly cartel-driven (regime distrust)

Interpretation:
- Clean, well-controlled wards become record-keeping/admin cores almost automatically.
- Even if we never declare “Admin Ward”, suitability pulls admin families inward.

### 3.10 BLACK_MARKET

Core drivers:
- Thrive where law/audit is patchy, but some flows exist to parasitize.

Positive:
- Low to medium `audit_intensity`
- Low to medium `legal_rigidity`
- High `corridor_centrality` (for smuggling) or dead-end with easy concealment
- High `scrap_access` and moderate `water_quota` (enough wealth to skim)
- `ventilation_regime` in `{open, mixed}` with decent `pollution_sink_index`
  (you can hide exhaust and people)

Negative:
- Very high `audit_intensity` + high `loyalty_to_regime` (risk > reward)
- Severely low `water_quota` and `food_buffer` (too poor to support parasitic networks)

Interpretation:
- Black markets lace through many wards, but become *dense* in industrial collars,
  logistics choke points, and permissive law environments.

---

## 4. Effective Suitability, Clusters & Drift

### 4.1 Base suitability

For each ward `w` and family `F`:

```text
base_suitability(w, F) = weighted_sum(ward_attributes, F-specific weights)
```

Weights are chosen to encode the qualitative logic above. Implementation details are
left to code and tuning docs.

### 4.2 Reinforcement & cluster bonus

Industries already present in a ward make it easier for that family (and complements)
to expand.

Let `presence_t(w, F)` be a normalized measure of how much industry `F` exists in ward `w`
at time `t` (capacity, workers, infrastructure).

We define a reinforcement term:

```text
cluster_bonus_t(w, F) = α_F * presence_t(w, F) + β_F * sum_over_G( complementarity(F, G) * presence_t(w, G) )
```

Where:

- `α_F` ≥ 0 : strength of direct self-reinforcement for family `F`.
- `β_F` ≥ 0 : strength of reinforcement from complementary families `G`.
- `complementarity(F, G)` in [0, 1] encodes strong/weak links, e.g.:
  - SCRAP_MATERIALS ↔ FABRICATION (high)
  - FOOD_BIOMASS ↔ HABITATION (high)
  - INFO_ADMIN ↔ WATER_ATMOSPHERE (medium)
  - BLACK_MARKET ↔ almost everything (varies).

**Effective suitability** is then:

```text
effective_suitability_t(w, F) = base_suitability(w, F) + cluster_bonus_t(w, F)
```

This means once a ward hosts a strong cluster of FABRICATION + SCRAP_MATERIALS,
it becomes ever more compelling for related industries to pile in.

### 4.3 Agent decision rule (conceptual)

Factions and actors evaluating where to start or expand industry `F` compare wards by:

```text
score_t(w, F) = effective_suitability_t(w, F)
                + faction_bias(w, F)
                - competition_penalty_t(w, F)
                + transient_opportunity_t(w, F)
```

Where:

- `faction_bias(w, F)` captures:
  - Ownership (e.g. cartel preferring low-audit wards).
  - Strategic doctrine (militia building exo-bays where garrison presence is high).

- `competition_penalty_t(w, F)` penalizes overcrowded sectors/orders of magnitude
  beyond local demand or logistics capacity.

- `transient_opportunity_t(w, F)` captures short-lived opportunities:
  - Shock events (disaster elsewhere, regime subsidies, new corridor opening).

Actors choose the `w` where `score_t(w, F)` is high enough to justify risk and investment.

### 4.4 Shock events & reconfiguration

Shocks can strongly perturb `base_suitability` or `presence` and force re-specialization:

Examples:
- Major industrial accident → spike in `toxicity_ruin` for a ward.
- Collapse of a corridor → drop in `corridor_centrality` and `scrap_access`.
- Regime reform → adjustments to `audit_intensity`, `legal_rigidity`, and `water_quota`.

These shocks:

1. Temporarily depress `presence_t(w, F)` for damaged families.
2. Alter `base_suitability(w, F)` for the future.
3. Change incentives in neighboring wards (spillover migration of industries).

Over time, wards that **lose** suitability in one family may gain it in another, causing
a **drift** in specialization, rather than static archetypes.

---

## 5. Sealed vs Unsealed Wards: Special Case Logic

Because Dosadi’s atmosphere is a key axis of survival, `ventilation_regime` and
`hvac_control_level` deserve explicit summary rules:

**Sealed, high-HVAC wards** (core/admin-like):
- Penalize:
  - SCRAP_MATERIALS (dirty subtypes)
  - Heavy FABRICATION (smelters, large furnaces)
  - Burn-heavy WATER_ATMOSPHERE subtypes
  - Heavy SUITS exo-bays
- Boost:
  - INFO_ADMIN
  - BODY_HEALTH (clinics, nutrition)
  - Light SUITS (tailors, mask shops)
  - Fine FABRICATION (machine tools, micro-electronics)

**Open / mixed wards with high pollution_sink_index** (sacrifice zones):
- Boost:
  - SCRAP_MATERIALS
  - Heavy FABRICATION
  - Burn pits, digesters, dirty FOOD_BIOMASS
  - Heavy SUITS (exo-bays, mod garages)
  - Certain BLACK_MARKET activities that leverage “nobody cares what vents here.”
- Often paired with:
  - Higher `garrison_presence` to contain unrest.
  - Lower `audit_intensity` de facto, even if nominal laws say otherwise.

This sealed/unsealed axis is central to how **clean admin cores** and **dirty industrial
collars** emerge without being explicitly declared in advance.

---

## 6. Implementation Sketch (Non-Normative)

A possible lightweight implementation path:

1. For each ward, store `WardAttributes` as a struct or JSON row.
2. For each family `F`, maintain a small weight vector over attributes.
3. At run time:
   - Compute `base_suitability(w, F)` via dot product + simple non-linearity (clamp).
   - Track `presence_t(w, F)` as aggregated capacity/throughput.
   - Compute `cluster_bonus_t(w, F)` via a small complementarity matrix.
4. Factions periodically evaluate `score_t(w, F)` and choose to:
   - Expand, contract, or relocate particular industries.
   - Respond to shocks and regime policies.

Balancing and tuning are expected to be iterative and scenario-specific.

---

## 7. Design Notes

- No ward is forced into a single archetype; **specialization is a trend**, not a rule.
- Admin cores, industrial collars, and sacrificial ruins emerge as **consequences** of
  geography, atmosphere control, and political choices—not static map labels.
- For early prototypes, it is acceptable to hand-assign WardAttributes and derive
  specializations from this model, then later let agents and shocks evolve them.

