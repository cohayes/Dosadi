---
title: Dosadi_Food_Waste_and_Metabolism
doc_id: D-HEALTH-0002
version: 1.0.0
status: draft
owners: [cohayes]
parent: D-HEALTH-0001
last_updated: 2025-11-13
---
# **Food, Waste & Metabolism v1 (Rations, Sanitation, Greywater, Bioloops)**

**Version:** v1 — 2025‑11‑13  
**Purpose.** Close the loop between what agents eat, how they expend energy and water, and how settlements reclaim waste into greywater, biomass, biogas, and fertilizers. Connect diet quality and kitchen tech to performance, disease risk, clinic load, and barrel‑level water accounting.

Integrates with **Environment Dynamics v1**, **Suit–Body–Environment v1**, **Work–Rest v1**, **Clinics & Health v1.1**, **Production & Fabrication v1**, **Credits & FX v1.1**, **Barrel Cascade v1.1**, **Rumor v1.1**, **Law & Contract Systems v1**, **Telemetry & Audit v1**, **Agent Decision v1**, and the **Tick Loop**.

> Timebase: food prep & decay **per 30 minutes**; eating & hydration **per 5 minutes**; metabolism & sanitation **per 15 minutes**; facility dashboards **hourly**.

---
## 0) Entities & State

- **Ration Item** `{id, recipe_id, class: ELITE|HIGH|MID|LOW|SCRAP, kcal, L_water_bound, macros{carb, fat, prot}, micronutrients, narcotic_dose?, shelf_life, sealed: bool, price_L}`  
- **Recipe** `{id, facility_req, BoM{materials}, water_use_prep_L, fuel_use, skill_req, QoS_score}`  
- **Kitchen/Facility** `{id, tier: ELITE|HIGH|MID|LOW, sealed_room: score, sterilization: score, capture_eff: {steam, rinse}, staff_skill, power_mode, water_buffer}`  
- **Agent Nutrition State** `{stomach_load, glycogen, fatigue_mod, illness_flags, hydration_L, micronutrient_reserve}`  
- **Waste Streams** `{greywater_L, organic_solids_kg, urine_L, feces_kg}` by venue (home, kitchen, clinic, street).  
- **Sanitation Node** `{id, type: HOUSEHOLD|BLOCK|WARD_PLANT|RECLAIMER, input_caps, process_eff, pathogen_kill, output: {greywater, biogas, compost, clean_water_L}}`  
- **KPIs**: `MealQualityIndex`, `FoodLoss%`, `IllnessIncidence`, `HydrationDeficit`, `GreywaterYield`, `BiogasYield`, `ClinicGI_Load`.

---
## 1) Diet Classes & Effects

- **ELITE/HIGH**: sealed prep, balanced macros & micronutrients; **stamina & recovery +**, **illness −**, **hydration carry +**.  
- **MID**: decent prep; **baseline effects**; small illness risk if crowded.  
- **LOW**: leaky kitchens; low micro density; **fatigue +**, **illness +**, **hydration −**.  
- **SCRAP**: scavenged; high illness risk; may include **narcotic additives** (Transcendence drive).

Effects are applied as multipliers to **Work–Rest** stamina decay, **Clinics** readmit risk, and **Agent Decision** (willingness to work/socialize).

---
## 2) Cooking, Sealing & Decay

- **Water Use**: `prep_L = base * (1 - capture_eff.steam - capture_eff.rinse)` per portion.  
- **Sealing**: sealed items respect **shelf_life** at ambient; unsealed decay by `exp(-k * hygiene)`; hot/sealed transport reduces spoilage.  
- **Cold Chain**: clinics & Class‑A safehouses maintain perishable meds/foods; loss on break triggers rumor “spoiled stores.”

---
## 3) Eating, Hydration & Metabolism

- **Meal Event**: `consume(ration)` updates `stomach_load`, adds `kcal`, `hydration_L`, `micros`; introduces **narcotic** if present.  
- **Metabolism Tick (15m)**: convert kcal to **energy**; update **fatigue**; deduct **hydration** by activity level & suit capture.  
- **Deficits**:  
  - **Hydration deficit** → cognitive/physical penalties; heat illness thresholds lower.  
  - **Micronutrient deficit** → long‑term reliability and recovery −; illness susceptibility +.  
  - **Undereating** → stamina cap −, aggression/impulsivity bias + (optional later).

---
## 4) Waste, Greywater & Reclamation

- **At Source**: kitchens capture steam & rinses → **greywater**; suits route urine/feces to **sac attachments**; households to **household nodes**.  
- **Processing**: sanitation nodes convert inputs to `{clean_water_L, greywater_L, compost, biogas}` with **process_eff** and **pathogen_kill** by tier.  
- **Reclaimer Plants**: high‑grade conversion of organics (including bodies per Law) to **clean water** and **biomass** streams.  
- **Routing**: outputs push back to **ward reservoirs** (water) or **workshops/farms** (biogas/compost/polymers).

---
## 5) Disease Pressure & Clinics

- **Foodborne & Waterborne Risks** scale with kitchen hygiene, water capture, crowding, and transport time.  
- **Symptoms** produce **Clinic episodes** (GI load); clinics see spikes after **procurement shocks** or **spoilage events**.  
- **Vaccination/Prophylaxis** (optional module) reduces incidence; requires **clinic permits** and supply chain.

---
## 6) Markets & Pricing (FX Hooks)

- **Ration Prices** in liters via **Credits & FX**; elastic demand across diet classes.  
- **Fuel & Water Inputs** priced via FX; cascade surcharges propagate to meal prices.  
- **Vouchers**: civic/issuer meal tokens (non‑transferable) redeemable at approved kitchens; rumors punish fraud.

---
## 7) Policy Knobs (defaults)

```yaml
food_waste_metabolism:
  meal_window_hours: 4
  decay_k_unsealed_per_hr: 0.25
  kitchen_capture_eff:
    ELITE: { steam: 0.8, rinse: 0.7 }
    HIGH:  { steam: 0.6, rinse: 0.5 }
    MID:   { steam: 0.4, rinse: 0.3 }
    LOW:   { steam: 0.2, rinse: 0.1 }
  sanitation_process_eff:
    HOUSEHOLD: 0.4
    BLOCK:     0.6
    WARD:      0.8
    RECLAIMER: 0.95
  pathogen_kill_prob:
    HOUSEHOLD: 0.6
    BLOCK:     0.8
    WARD:      0.95
    RECLAIMER: 0.99
  hydration_activity_L_per_hr:
    REST: 0.05
    LIGHT: 0.1
    MODERATE: 0.2
    HEAVY: 0.4
  micronutrient_decay_per_day: 0.05
  narcotic_effects:
    fatigue_mult: 0.85
    judgment_mult: 0.8
    rebound_fatigue_mult: 1.2
```

---
## 8) Event & Function Surface (for Codex)

**Functions**  
- `cook(recipe_id, qty, facility_id)` → produces sealed/unsealed rations; posts water/fuel usage.  
- `seal(ration_id, sealed: bool)` → sets shelf behavior; cost/time.  
- `consume(agent_id, ration_id)` → updates metabolism & hydration; applies narcotic effects if present.  
- `metabolism_tick(agent_id, activity_level)` → energy/hydration updates & deficits.  
- `route_waste(source_id, stream_bundle)` → sends to sanitation node; records outputs.  
- `process_sanitation(node_id)` → yields `{clean_water_L, greywater_L, biogas, compost}`; anchors to boards.  
- `post_spoilage(kitchen_id, lot_id)` → rumor hook & penalty per permits.  
- `redeem_voucher(agent_id, kitchen_id, voucher_token)` → payment + ration allocation.

**Events**  
- `MealCooked`, `MealSealed`, `MealConsumed`, `MetabolismUpdated`, `WasteRouted`, `SanitationProcessed`, `SpoilagePosted`, `VoucherRedeemed`.

---
## 9) Pseudocode (Indicative)

```python
def consume(agent, ration):
    agent.stomach_load += ration.kcal
    agent.hydration_L += ration.L_water_bound * absorption(agent)
    agent.micronutrient_reserve += ration.micronutrients
    if ration.narcotic_dose:
        agent.apply_narcotic(ration.narcotic_dose)

def metabolism_tick(agent, activity):
    cals = activity_cals(activity) * suit_efficiency(agent.suit)
    agent.glycogen = max(0, agent.glycogen - cals)
    agent.hydration_L -= policy.hydration_activity_L_per_hr[activity] / 4.0
    update_fatigue_and_performance(agent)
```

---
## 10) Dashboards & Explainability

- **Kitchen Board**: throughput, capture efficiency, spoilage, water/fuel per meal, voucher redemptions.  
- **Sanitation Board**: inputs, outputs, pathogen kill rate, clean water yield, biogas production.  
- **Health Board**: GI clinic load vs food classes, hydration deficits, micronutrient status proxies.  
- **Equity View**: share of LOW/SCRAP diets by ward; voucher coverage; rumor polarity on kitchens.

---
## 11) Test Checklist (Day‑0+)

- Better kitchens reduce water use per meal and illness incidence; sealed transport cuts spoilage.  
- Hydration & nutrient deficits translate to Work–Rest penalties and increased clinic visits.  
- Sanitation nodes convert waste with expected efficiency; reclaimers outperform ward plants.  
- Cascade/FX shocks raise meal prices and lower ELITE/HIGH consumption share; vouchers buffer poorest wards.  
- Narcotic meals show short‑term fatigue relief but worsen long‑term performance and reliability.

---
### End of Food, Waste & Metabolism v1
