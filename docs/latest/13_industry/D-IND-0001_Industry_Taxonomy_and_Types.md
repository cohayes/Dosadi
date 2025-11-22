---
title: Industry_Taxonomy_and_Types
doc_id: D-IND-0001
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-21
depends_on:
  - D-WORLD-0001        # Wards & environment overview
  - D-RUNTIME-0001      # Simulation_Timebase
  - D-ECON-0001         # Logistics_Corridors_and_Safehouses
  - D-ECON-0002         # Black_Market_Networks
  - D-ECON-0003         # Food_Waste_and_Metabolism
---

# 13_industry · Industry Taxonomy and Types (D-IND-0001)

## 1. Purpose and Scope

This document defines a first-pass taxonomy of industries on Dosadi.

- It does **not** assign fixed archetypes to wards.
- Instead, it provides a **catalog of industry types** that can appear in any ward,
  with capacities and configurations that evolve over time as factions exploit their
  relative advantages.
- Each industry entry describes:
  - Core function,
  - Water profile,
  - Labor and infrastructure needs,
  - Political visibility and legal status,
  - Typical ownership patterns and hooks into other pillars.

Simulation and game code can treat each industry entry as a **config row**. Ward
specialization is not hard-coded; it emerges from:

- Local suitability (inputs, geophysical constraints, toxicity/ruin history),
- Initial seed capacities,
- Agent and faction decisions,
- Political, military, and audit pressures.

## 2. Industry Type Schema (Logical Shape)

Each industry should be serializable roughly as:

```yaml
id:               # short machine id, e.g. food_vat_protein
family:           # top-level family, e.g. FOOD_BIOMASS
label:            # human-readable name
summary:          # 1–2 line description
typical_scale:    # shack | workshop | block | ward | network
water_profile:    # recovering | neutral | consuming_light | consuming_heavy | parasitic
labor_skill:      # unskilled | semi_skilled | skilled | specialist | mixed
labor_risk:       # low | medium | high | very_high
audit_visibility: # low | medium | high | very_high
street_visibility:# low | medium | high | very_high
legal_status:     # sanctioned | tolerated | illicit | banned
typical_owners:   # duke_house | bishop_guild | cartel | co_op | militia | central_audit_guild | embedded_staff | rogue_militia | neutral_fixers
notes:            # hooks into other pillars, politics, plot
```

Further D-IND docs can elaborate input/output tables as needed.

---

## 3. Families and Types

Below, each bullet is a single industry row in the schema above.

### A. WATER_ATMOSPHERE · Water & Atmosphere Industries

**A1 · Wellhead Extraction**  
- `id`: water_wellhead_extraction  
- `summary`: High-control draw of water from the central well or deep bore taps, managed under strict quota and audit oversight.  
- `typical_scale`: ward  
- `water_profile`: consuming_heavy  
- `labor_skill`: specialist  
- `labor_risk`: medium  
- `audit_visibility`: very_high  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house  
- `notes`: Macro-political choke point; misreporting or sabotage cascades across all wards.

**A2 · Atmospheric Moisture Farms**  
- `id`: water_atmo_capture  
- `summary`: Banks of dehumidifiers integrated with crowded interiors to harvest moisture from respiration and ambient air.  
- `typical_scale`: block  
- `water_profile`: recovering  
- `labor_skill`: semi_skilled  
- `labor_risk`: low  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild  
- `notes`: Often co-located with bunkhouses and food halls; bodies become water infrastructure.

**A3 · Leak Scavenging Crews**  
- `id`: water_leak_scavenging  
- `summary`: Crews that trace, patch, or quietly exploit leaks in intra-ward pipework, cisterns, and storage.  
- `typical_scale`: crew  
- `water_profile`: parasitic  
- `labor_skill`: skilled  
- `labor_risk`: high  
- `audit_visibility`: low  
- `street_visibility`: medium  
- `legal_status`: tolerated  
- `typical_owners`: embedded_staff  
- `notes`: Blur between official repair and skimming. Inter-ward pipes are rare; most action is internal to high-tier wards.

**A4 · Filtration Plants**  
- `id`: water_filtration_plants  
- `summary`: Plants that turn greywater and lightly contaminated sources into drinkable or process-grade water.  
- `typical_scale`: block  
- `water_profile`: recovering  
- `labor_skill`: semi_skilled  
- `labor_risk`: medium  
- `audit_visibility`: high  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild  
- `notes`: Sludge becomes feedstock for waste digesters and chemical extraction.

**A5 · Chemical Treatment Works**  
- `id`: water_chemical_treatment  
- `summary`: Doses water streams with disinfectants and other additives to manage pathogens, metals, and taste.  
- `typical_scale`: block  
- `water_profile`: consuming_light  
- `labor_skill`: specialist  
- `labor_risk`: medium  
- `audit_visibility`: high  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house  
- `notes`: Over- or under-dosing can be weaponized or become scandal fuel.

**A6 · Salinity & Mineral Balancing**  
- `id`: water_salinity_balancing  
- `summary`: Adjusts dissolved mineral content for drinking, industry, or suit systems.  
- `typical_scale`: workshop  
- `water_profile`: neutral  
- `labor_skill`: skilled  
- `labor_risk`: low  
- `audit_visibility`: medium  
- `street_visibility`: low  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, co_op  
- `notes`: Creates niche leverage for industrial processes and high-grade life support.

**A7 · Ration-Pack Bottling**  
- `id`: water_ration_bottling  
- `summary`: Fills and seals standard canisters or ration-packs with water, embedding identity and audit controls.  
- `typical_scale`: block  
- `water_profile`: consuming_light  
- `labor_skill`: unskilled  
- `labor_risk`: low  
- `audit_visibility`: very_high  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house  
- `notes`: Visible face of the water system; tampering directly feeds black markets.

**A8 · Bulk Transfer Depots (Barrel Cadence)**  
- `id`: water_bulk_depots  
- `summary`: Yards where water is stored and dispatched via barrels and mobile containers according to cadence rules.  
- `typical_scale`: block  
- `water_profile`: neutral  
- `labor_skill`: unskilled  
- `labor_risk`: medium  
- `audit_visibility`: high  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house, militia  
- `notes`: Cross-ward moves are overwhelmingly barrel-based, not piped; depots are natural raid targets.

**A9 · Meter & Audit Workshops**  
- `id`: water_meter_workshops  
- `summary`: Build, calibrate, and seal water meters, barrel tags, and related audit hardware.  
- `typical_scale`: workshop  
- `water_profile`: neutral  
- `labor_skill`: specialist  
- `labor_risk`: medium  
- `audit_visibility`: very_high  
- `street_visibility`: low  
- `legal_status`: sanctioned  
- `typical_owners`: central_audit_guild  
- `notes`: Define what is considered "real" flow; leaks empower token printers and seal forgers.

---

### B. FOOD_BIOMASS · Food, Biomass & Metabolism

**B1 · Vat Protein Growlabs**  
- `id`: food_vat_protein  
- `summary`: Sealed tanks growing fungal, algal, or tissue cultures into dense low-water protein feedstock.  
- `typical_scale`: block  
- `water_profile`: consuming_heavy  
- `labor_skill`: specialist  
- `labor_risk`: medium  
- `audit_visibility`: high  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house, bishop_guild  
- `notes`: Food-security lynchpins; contamination or sabotage is a major incident.

**B2 · Insect Hives**  
- `id`: food_insect_hives  
- `summary`: High-density insect colonies converting organic scraps and waste into protein and fats.  
- `typical_scale`: shack, workshop  
- `water_profile`: recovering  
- `labor_skill`: unskilled  
- `labor_risk`: low  
- `audit_visibility`: low  
- `street_visibility`: high  
- `legal_status`: tolerated, sanctioned  
- `typical_owners`: co_op, cartel  
- `notes`: Anchor of poor wards' protein supply; integrated with waste flows.

**B3 · Chop Houses & Rendering**  
- `id`: food_chop_render  
- `summary`: Break down carcasses and bulk biomass into organs, fats, bone, and feedstocks.  
- `typical_scale`: workshop, block  
- `water_profile`: consuming_light  
- `labor_skill`: unskilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, cartel  
- `notes`: Crosses into medical graft and industrial chemistry inputs.

**B4 · Fermentation Halls**  
- `id`: food_fermentation_halls  
- `summary`: Ferment biomass into preserves, flavor enhancers, mild drugs, and gut-microbe products.  
- `typical_scale`: workshop, block  
- `water_profile`: consuming_light  
- `labor_skill`: semi_skilled  
- `labor_risk`: low  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: co_op, bishop_guild  
- `notes`: Food plus mood infrastructure; adjacent to black-market hospitality.

**B5 · Drying & Powdering Floors**  
- `id`: food_drying_powdering  
- `summary`: Dry and mill biomass into shelf-stable powders and ration bricks for long cadences.  
- `typical_scale`: workshop  
- `water_profile`: recovering  
- `labor_skill`: semi_skilled  
- `labor_risk`: low  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild  
- `notes`: Determines which populations can survive extended delivery gaps.

**B6 · Waste Digesters**  
- `id`: food_waste_digesters  
- `summary`: Anaerobic digesters turning sewage and scraps into biogas and nutrient slurries.  
- `typical_scale`: block  
- `water_profile`: recovering  
- `labor_skill`: semi_skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, duke_house  
- `notes`: Failures create long-lived environmental damage and health crises.

**B7 · Canteens & Food Halls**  
- `id`: food_canteens  
- `summary`: Final-mile kitchens turning stocks into meals and social gatherings, tightly linked to mood and loyalty.  
- `typical_scale`: shack, block  
- `water_profile`: recovering  
- `labor_skill`: unskilled  
- `labor_risk`: low  
- `audit_visibility`: medium  
- `street_visibility`: very_high  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: bishop_guild, co_op, cartel  
- `notes`: Prime rumor and recruitment hubs; also moisture capture nodes.

**B8 · Nutrition Clinics**  
- `id`: food_nutrition_clinics  
- `summary`: Small clinics tuning diets to maximize labor output and survival for key groups.  
- `typical_scale`: shack, workshop  
- `water_profile`: consuming_light  
- `labor_skill`: specialist  
- `labor_risk`: low  
- `audit_visibility`: medium  
- `street_visibility`: low  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild  
- `notes`: Their data ties food, health, and loyalty into a single pipeline.

---

### C. BODY_HEALTH · Body, Health & Mortality

**C1 · Clinic Chains**  
- `id`: health_clinics  
- `summary`: Distributed medical posts handling trauma, infection control, and routine care.  
- `typical_scale`: shack, block  
- `water_profile`: consuming_light  
- `labor_skill`: specialist  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild  
- `notes`: Major lever for patronage and social control.

**C2 · Corpse Processing Houses**  
- `id`: health_corpse_processing  
- `summary`: Reclaim organs, bone, and nutrients from the dead as critical resources.  
- `typical_scale`: workshop  
- `water_profile`: recovering  
- `labor_skill`: semi_skilled  
- `labor_risk`: high  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: bishop_guild, cartel  
- `notes`: Moral horror is subordinate to survival; core law-system battleground.

**C3 · Performance & Conditioning Houses**  
- `id`: health_conditioning_houses  
- `summary`: Train and dose workers and fighters for strength, endurance, and focus.  
- `typical_scale`: workshop, block  
- `water_profile`: consuming_light  
- `labor_skill`: specialist  
- `labor_risk`: high  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: militia, duke_house, cartel  
- `notes`: Side effects feed health and law storylines.

---

### D. SCRAP_MATERIALS · Scrap, Materials & Matter-Handling

**D1 · Rubble Crews**  
- `id`: scrap_rubble_crews  
- `summary`: Break down collapsed structures and ruined zones to recover materials.  
- `typical_scale`: crew  
- `water_profile`: neutral  
- `labor_skill`: unskilled  
- `labor_risk`: high  
- `audit_visibility`: low  
- `street_visibility`: high  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: bishop_guild, cartel  
- `notes`: Ruins come from Dosadi-made disasters, not precursors; toxic zones shape work patterns.

**D2 · E-Waste Pickers**  
- `id`: scrap_ewaste_pickers  
- `summary`: Specialists combing dumps for boards, batteries, and high-value electronics.  
- `typical_scale`: shack, crew  
- `water_profile`: neutral  
- `labor_skill`: skilled  
- `labor_risk`: medium  
- `audit_visibility`: low  
- `street_visibility`: medium  
- `legal_status`: tolerated  
- `typical_owners`: co_op, cartel  
- `notes`: Feed micro-electronics and chemical leaching outfits.

**D3 · Pipe Rats**  
- `id`: scrap_pipe_rats  
- `summary`: Harvest metal and fittings from neglected intra-ward infrastructure.  
- `typical_scale`: crew  
- `water_profile`: parasitic  
- `labor_skill`: unskilled  
- `labor_risk`: high  
- `audit_visibility`: low  
- `street_visibility`: medium  
- `legal_status`: illicit, tolerated  
- `typical_owners`: cartel, embedded_staff  
- `notes`: Directly erode water and power networks.

**D4 · Material Sort Yards**  
- `id`: scrap_sort_yards  
- `summary`: Separate mixed scrap into metal, plastic, and other streams.  
- `typical_scale`: block  
- `water_profile`: neutral  
- `labor_skill`: unskilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild  
- `notes`: Skimming high-grade pieces is an endemic micro-black-market.

**D5 · Shredders & Crushers**  
- `id`: scrap_shred_crush  
- `summary`: Mechanized plants shredding and crushing scrap to expose components and reduce volume.  
- `typical_scale`: block  
- `water_profile`: neutral  
- `labor_skill`: semi_skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house, bishop_guild  
- `notes`: Dust handling impacts long-term health.

**D6 · Burn Pits with Capture**  
- `id`: scrap_burn_pits  
- `summary`: Controlled burn sites with crude capture of metals and minerals.  
- `typical_scale`: block  
- `water_profile`: neutral  
- `labor_skill`: unskilled  
- `labor_risk`: high  
- `audit_visibility`: low, medium  
- `street_visibility`: high  
- `legal_status`: tolerated  
- `typical_owners`: bishop_guild, cartel  
- `notes`: Toxic plumes define micro-climates and morbidity patterns.

**D7 · Micro-Smelters & Foundries**  
- `id`: scrap_micro_smelters  
- `summary`: Small furnaces producing usable alloys from sorted metals.  
- `typical_scale`: workshop, block  
- `water_profile`: consuming_light  
- `labor_skill`: skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, co_op  
- `notes`: Feed core fabrication sectors.

**D8 · Polymer Crackers**  
- `id`: scrap_polymer_crackers  
- `summary`: Break plastics into chemical feedstocks, fuels, or crude solvents.  
- `typical_scale`: workshop  
- `water_profile`: consuming_light  
- `labor_skill`: specialist  
- `labor_risk`: high  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: bishop_guild, cartel  
- `notes`: Provide solvents and suit materials.

**D9 · Chemical Leaching Cells**  
- `id`: scrap_chem_leaching  
- `summary`: Leach rare metals from concentrated scrap using chemical baths.  
- `typical_scale`: workshop  
- `water_profile`: consuming_light  
- `labor_skill`: specialist  
- `labor_risk`: high  
- `audit_visibility`: medium  
- `street_visibility`: low  
- `legal_status`: tolerated  
- `typical_owners`: cartel, co_op  
- `notes`: Poor tailing management generates long-lived toxic ruins.

---

### E. FABRICATION · Fabrication & Device Industries

**E1 · Structural Metal Shops**  
- `id`: fab_structural_metal  
- `summary`: Produce beams, plates, and bars for frames, corridors, and reinforcement.  
- `typical_scale`: workshop, block  
- `water_profile`: consuming_light  
- `labor_skill`: semi_skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, duke_house  
- `notes`: Gate where new construction can happen at all.

**E2 · Pump & Valve Works**  
- `id`: fab_pump_valve_works  
- `summary`: Build and repair pumps, valves, and fittings for local water and sludge systems.  
- `typical_scale`: workshop  
- `water_profile`: neutral  
- `labor_skill`: specialist  
- `labor_risk`: medium  
- `audit_visibility`: high  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house, militia, cartel  
- `notes`: Missing valves conveniently justify ration cuts; intra-ward pipework is luxury.

**E3 · Corridor Kit Yards**  
- `id`: fab_corridor_kits  
- `summary`: Assemble standardized stairs, gates, ladders, and barricades for access corridors.  
- `typical_scale`: block  
- `water_profile`: neutral  
- `labor_skill`: semi_skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, militia  
- `notes`: Control over kits shapes chokepoints and rerouting in crisis.

**E4 · Machine-Tool Shops**  
- `id`: fab_machine_tools  
- `summary`: Produce and maintain lathes, mills, cutters, and molds that other industries rely on.  
- `typical_scale`: workshop, block  
- `water_profile`: consuming_light  
- `labor_skill`: specialist  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, cartel, co_op  
- `notes`: Decay here slowly kills exo-suit, weapons, and pump industries.

**E5 · Micro-Electronics Cells**  
- `id`: fab_micro_electronics  
- `summary`: Repair, modify, or lightly manufacture boards and control modules from salvaged parts.  
- `typical_scale`: shack, workshop  
- `water_profile`: neutral  
- `labor_skill`: specialist  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: low  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: bishop_guild, cartel  
- `notes`: Feed suits, pumps, weapons, and meters with scarce logic.

**E6 · Instrument & Meter Makers**  
- `id`: fab_instrument_makers  
- `summary`: Manufacture gauges, flow meters, and sensors that define official readings.  
- `typical_scale`: workshop  
- `water_profile`: neutral  
- `labor_skill`: specialist  
- `labor_risk`: low  
- `audit_visibility`: high  
- `street_visibility`: low, medium  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house, central_audit_guild  
- `notes`: Direct coupling to audit and info pillars; sample theft powers forgers.

**E7 · Tool & Weapon Forges**  
- `id`: fab_tool_weapon_forges  
- `summary`: Produce tools and improvised melee weapons from available metals.  
- `typical_scale`: workshop  
- `water_profile`: consuming_light  
- `labor_skill`: skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: bishop_guild, cartel, militia  
- `notes`: Output leaks into banditry and shadow enforcement.

---

### F. SUITS · Suit, Exo-Suit & Life Support

**F1 · Mask & Filter Shops**  
- `id`: suit_mask_shops  
- `summary`: Tailor respirators, cartridges, and facial seals tuned to local air chemistry.  
- `typical_scale`: shack, workshop  
- `water_profile`: neutral  
- `labor_skill`: semi_skilled  
- `labor_risk`: low  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: co_op, bishop_guild, cartel  
- `notes`: Highly visible class markers; variant designs travel through rumor networks.

**F2 · Suit Stitchers & Sealers**  
- `id`: suit_stitchers  
- `summary`: Assemble, resize, and repair environmental suits with strong focus on seams and seals.  
- `typical_scale`: workshop  
- `water_profile`: recovering  
- `labor_skill`: semi_skilled  
- `labor_risk`: low, medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: co_op, bishop_guild  
- `notes`: Core to wardrobe identity and survival; directly connects to 06_suits pillar.

**F3 · Micro-Dehumidifier Builders**  
- `id`: suit_micro_dehumidifiers  
- `summary`: Assemble portable dehumidifiers and moisture-capture modules for suits and interiors.  
- `typical_scale`: workshop  
- `water_profile`: recovering  
- `labor_skill`: specialist  
- `labor_risk`: low  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, duke_house  
- `notes`: Implementation detail of "humans as mobile water sources."

**F4 · Air Recycler Manufacturers**  
- `id`: suit_air_recyclers  
- `summary`: Build portable scrubbers and circulation units for suits and sealed spaces.  
- `typical_scale`: workshop  
- `water_profile`: neutral  
- `labor_skill`: specialist  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: low  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, duke_house  
- `notes`: Enable deep excursions into toxic wards, tying into military and exploration play.

**F5 · Internal Plumbing Integrators**  
- `id`: suit_plumbing_integrators  
- `summary`: Integrate tubing, reservoirs, and fittings that route sweat, urine, and condensate into reclaim systems.  
- `typical_scale`: workshop  
- `water_profile`: recovering  
- `labor_skill`: skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: low, medium  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, co_op  
- `notes`: Closed-loop suits concentrated among elites and critical workers.

**F6 · Exo-Suit Service Bays (Authorized)**  
- `id`: suit_exobays_authorized  
- `summary`: High-security bays storing, maintaining, and refitting heavy exo-suits for industry and force projection.  
- `typical_scale`: block  
- `water_profile`: consuming_light  
- `labor_skill`: specialist  
- `labor_risk`: high  
- `audit_visibility`: high  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house, militia  
- `notes`: Hard link between industry and military pillars; bay locations define who can move heavy power.

**F7 · Mod Garages (Black Market)**  
- `id`: suit_mod_garages  
- `summary`: Hidden workshops modifying suits and exo-suits for stealth, performance, or illicit capabilities.  
- `typical_scale`: shack, workshop  
- `water_profile`: neutral  
- `labor_skill`: specialist  
- `labor_risk`: very_high  
- `audit_visibility`: low  
- `street_visibility`: high  
- `legal_status`: illicit, banned  
- `typical_owners`: cartel, rogue_militia  
- `notes`: Strong crossover with black markets and info-security; discovery triggers exemplary punishment.

---

### G. ENERGY_MOTION · Energy & Motion Industries

**G1 · Grid Hubs**  
- `id`: energy_grid_hubs  
- `summary`: Managed nodes distributing power from generation sources to local consumers with rationing.  
- `typical_scale`: block, ward  
- `water_profile`: neutral  
- `labor_skill`: skilled  
- `labor_risk`: medium  
- `audit_visibility`: high  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house  
- `notes`: Blackouts are political tools and riot triggers.

**G2 · Local Generators**  
- `id`: energy_local_generators  
- `summary`: Decentralized engines or fuel cells providing backup or independent power to specific sites.  
- `typical_scale`: shack, workshop  
- `water_profile`: neutral  
- `labor_skill`: semi_skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: bishop_guild, cartel, militia  
- `notes`: Critical for actors that do not trust central allocations.

**G3 · Battery & Accumulator Shops**  
- `id`: energy_battery_shops  
- `summary`: Build, refurbish, and recycle energy storage devices.  
- `typical_scale`: workshop  
- `water_profile`: consuming_light  
- `labor_skill`: skilled  
- `labor_risk`: high  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, cartel  
- `notes`: Power packs are strategic resources for suits, weapons, and vital infrastructure.

**G4 · Cable Crews**  
- `id`: energy_cable_crews  
- `summary`: Lay, maintain, and occasionally tap power lines inside wards.  
- `typical_scale`: crew  
- `water_profile`: neutral  
- `labor_skill`: semi_skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: bishop_guild, embedded_staff  
- `notes`: Power theft and clandestine taps parallel water skimming in economic logic.

**G5 · Lift & Winch Yards**  
- `id`: motion_lift_winch_yards  
- `summary`: Build and maintain pulley systems, cranes, and cargo hoists for vertical movement.  
- `typical_scale`: workshop, block  
- `water_profile`: neutral  
- `labor_skill`: skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, militia  
- `notes`: Control over vertical movement equates to control over escape routes and supply chains.

**G6 · Track & Trolley Works**  
- `id`: motion_track_trolley  
- `summary`: Build rails, carts, and cable systems moving bulk goods within and between levels.  
- `typical_scale`: block  
- `water_profile`: neutral  
- `labor_skill`: semi_skilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild  
- `notes`: Trolley networks are natural taxation and sabotage targets.

**G7 · Pumpway Builders**  
- `id`: motion_pumpway_builders  
- `summary`: Design and install chained pumps for moving liquids and slurries within wards.  
- `typical_scale`: workshop  
- `water_profile`: consuming_light  
- `labor_skill`: skilled  
- `labor_risk`: medium  
- `audit_visibility`: high  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house, bishop_guild  
- `notes`: Inter-ward pumpways are rare luxuries; most work is purely internal circulation.

---

### H. HABITATION · Housing, Habitation & Atmospheric Farming

**H1 · Bunkhouse & Dorm Operators**  
- `id`: hab_bunkhouse_ops  
- `summary`: Run dense sleeping quarters that monetize respiration and body heat as much as rent.  
- `typical_scale`: block  
- `water_profile`: recovering  
- `labor_skill`: unskilled  
- `labor_risk`: low  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, cartel  
- `notes`: Low-caste warehousing; key pressure cooker for social unrest.

**H2 · Environmental Interior Services**  
- `id`: hab_env_services  
- `summary`: Tune air, light, noise, and crowding inside major interiors to optimize output or docility.  
- `typical_scale`: workshop, block  
- `water_profile`: recovering  
- `labor_skill`: skilled  
- `labor_risk`: low  
- `audit_visibility`: low, medium  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, duke_house  
- `notes`: Interface between physical conditions and social engineering.

**H3 · Sanitation & Latrine Enterprises**  
- `id`: hab_sanitation_ops  
- `summary`: Operate public baths and latrines where hygiene and waste capture are both services and industries.  
- `typical_scale`: block  
- `water_profile`: consuming_heavy  
- `labor_skill`: unskilled  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, cartel  
- `notes`: Feed waste digesters and shape infection dynamics.

**H4 · Cleaning Guilds**  
- `id`: hab_cleaning_guilds  
- `summary`: Move filth from high-status zones to sacrificial processing areas, controlling the grime gradient.  
- `typical_scale`: crew  
- `water_profile`: consuming_light  
- `labor_skill`: unskilled  
- `labor_risk`: medium  
- `audit_visibility`: low, medium  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, co_op  
- `notes`: Cleaning crews see everything; natural rumor and intel carriers.

---

### I. INFO_ADMIN · Information, Measurement & Administrative

**I1 · Measurement & Audit Firms**  
- `id`: info_measurement_audit  
- `summary`: Deploy auditors and technicians to verify flows of water, power, labor, and goods against ledgers.  
- `typical_scale`: ward  
- `water_profile`: neutral  
- `labor_skill`: specialist  
- `labor_risk`: high  
- `audit_visibility`: very_high  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: central_audit_guild  
- `notes`: Decisions rewire economic and political landscapes; natural antagonists to skimmers and forgers.

**I2 · Ledger Houses**  
- `id`: info_ledger_houses  
- `summary`: Maintain tax, tithe, and obligation ledgers tying flows to households, wards, and factions.  
- `typical_scale`: block  
- `water_profile`: neutral  
- `labor_skill`: skilled  
- `labor_risk`: medium  
- `audit_visibility`: very_high  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house, central_audit_guild  
- `notes`: Bribery, forgery, and "lost pages" are recurring hooks.

**I3 · Registry Houses**  
- `id`: info_registry_houses  
- `summary`: Issue and record licenses, permits, identities, liens, and other legal statuses.  
- `typical_scale`: block  
- `water_profile`: neutral  
- `labor_skill`: skilled  
- `labor_risk`: medium  
- `audit_visibility`: high  
- `street_visibility`: high  
- `legal_status`: sanctioned  
- `typical_owners`: bishop_guild, duke_house  
- `notes`: Define who is allowed to operate, move, or even exist on paper.

**I4 · Courier Networks**  
- `id`: info_courier_networks  
- `summary`: Human or mechanical messengers moving sealed messages, records, and small valuables.  
- `typical_scale`: network of small sites  
- `water_profile`: neutral  
- `labor_skill`: mixed  
- `labor_risk`: medium  
- `audit_visibility`: medium  
- `street_visibility`: high  
- `legal_status`: sanctioned, tolerated  
- `typical_owners`: bishop_guild, cartel, militia  
- `notes`: Couriers can be bought, threatened, or ideologically bound; central to rumor systems.

**I5 · Signal Hubs**  
- `id`: info_signal_hubs  
- `summary`: Nodes for wired or line-of-sight signaling supporting faster-than-runner coordination.  
- `typical_scale`: block  
- `water_profile`: neutral  
- `labor_skill`: skilled  
- `labor_risk`: medium  
- `audit_visibility`: high  
- `street_visibility`: medium  
- `legal_status`: sanctioned  
- `typical_owners`: duke_house, militia  
- `notes`: Early targets in coups and crackdowns.

**I6 · Data Brokers**  
- `id`: info_data_brokers  
- `summary`: Offices (open or clandestine) that buy, collate, and sell intelligence, rumors, and blackmail.  
- `typical_scale`: shack, workshop  
- `water_profile`: neutral  
- `labor_skill`: skilled  
- `labor_risk`: very_high  
- `audit_visibility`: low  
- `street_visibility`: medium  
- `legal_status`: tolerated, illicit  
- `typical_owners`: cartel, rogue_officials  
- `notes`: Structured hooks into rumor, law, and high-tier politics.

---

### J. BLACK_MARKET · Grey & Black-Market Overlay

These industries overlay others, parasitizing or mirroring them.

**J1 · Water Skimmers**  
- `id`: black_water_skimmers  
- `summary`: Tap intra-ward pipes, cisterns, and barrels to skim small unseen fractions of water.  
- `typical_scale`: network of small sites  
- `water_profile`: parasitic  
- `labor_skill`: skilled  
- `labor_risk`: very_high  
- `audit_visibility`: low  
- `street_visibility`: medium  
- `legal_status`: illicit  
- `typical_owners`: cartel, embedded_staff  
- `notes`: Cluster along rare luxury trunk-lines and internal ward networks; constant adversaries for audit and maintenance crews.

**J2 · Token Printers & Seal Forgers**  
- `id`: black_token_printers  
- `summary`: Counterfeit ration tokens, permits, and meter or barrel seals to gain illicit access to flows.  
- `typical_scale`: microcell  
- `water_profile`: neutral  
- `labor_skill`: specialist  
- `labor_risk`: very_high  
- `audit_visibility`: very_low  
- `street_visibility`: low  
- `legal_status`: banned  
- `typical_owners`: cartel, infiltrated_clerks  
- `notes`: Direct antagonists to meter workshops and ledger houses; discovery prompts wide purges.

**J3 · Protection Crews**  
- `id`: black_protection_crews  
- `summary`: Sell "protection" to industrial outfits, operating as shadow tax and alternative dispute resolution.  
- `typical_scale`: crew  
- `water_profile`: neutral  
- `labor_skill`: mixed  
- `labor_risk`: medium  
- `audit_visibility`: low, medium  
- `street_visibility`: very_high  
- `legal_status`: illicit, tolerated  
- `typical_owners`: cartel, militia_factions  
- `notes`: Determine which industries survive in marginal wards and under what unofficial rule-sets.

**J4 · Smuggling & Corridor Exploitation Rings**  
- `id`: black_smuggling_rings  
- `summary`: Exploit logistics corridors, safehouses, and schedule gaps to move contraband and evade audits.  
- `typical_scale`: network  
- `water_profile`: parasitic  
- `labor_skill`: mixed  
- `labor_risk`: very_high  
- `audit_visibility`: low  
- `street_visibility`: high  
- `legal_status`: illicit  
- `typical_owners`: cartel  
- `notes`: Integrate directly with Logistics Corridors & Safehouses and Black Market Networks docs.

**J5 · Arbitration Dens**  
- `id`: black_arbitration_dens  
- `summary`: Informal courts where shadow actors resolve disputes over territory, debts, and contracts.  
- `typical_scale`: shack, workshop  
- `water_profile`: neutral  
- `labor_skill`: skilled  
- `labor_risk`: high  
- `audit_visibility`: very_low  
- `street_visibility`: medium  
- `legal_status`: illicit, tolerated  
- `typical_owners`: cartel, neutral_fixers  
- `notes`: Parallel legal system often more predictable than official law in under-governed wards.
