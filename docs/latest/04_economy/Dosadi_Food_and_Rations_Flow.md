---
title: Dosadi_Food_and_Rations_Flow
doc_id: D-ECON-0005
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-ECON-0001
---
# **Food & Rations Flow v1**

Production → Processing → Packaging → Distribution → Consumption → Reclaim.  
Integrates with **Agents v1**, **Market v1**, **Worldgen v1**, **Maintenance Fault Loop v1**, **Security Loop v1**, **Clinic Flow v1**, **Rumor & Perception v1**, and **Tick Loop**.

> Cadence: kitchens tick **per Minute**; ration decay **per Hour**; price indices **per Day**.

---

## 0) Goals

1. **Survival‑centric**: nutrition & hydration are first‑class; meals affect agent stats and drives.  
2. **Quality & Efficiency**: equipment + skill → conversion efficiency, shelf‑life, and contamination risk.  
3. **Queues & Throughput**: kitchens are bottlenecks with line dynamics & security exposure.  
4. **Closed Loop**: scraps/expired/biowaste → reclaimer → greywater/biomass.

---

## 1) Items & Units

- **Raw Materials**: `grain_kg`, `protein_kg` (cultured/bulk), `veg_kg`, `oil_L`, `spices_g`, `water_L`.  
- **Additives**: `electrolyte_mix_g`, `vitamin_mix_g`, `thickener_g`.  
- **Energy**: `fuel` (biofuel kWh) or grid power.  
- **Rations**: SKUs by **Tier** (`LOW|MID|HIGH|ELITE`) and **Form** (`SOUP|BAR|GEL|MEAL`).

**Nutritional spec per ration**  
`kcal`, `protein_g`, `electrolytes`, `water_L`, `micro_mix_score`.

---

## 2) Kitchen Model

```json
{
  "kitchen_id":"kit_21",
  "tier":"LOW|MID|HIGH|ELITE",
  "state":"ONLINE|DEGRADED|OFFLINE",
  "stations":{"prep":2,"cook":2,"pack":1,"seal":1,"wash":1},
  "staff":{"cook":4,"prep":6,"pack":3,"san":2},
  "equipment":{"boiler":1,"mixer":1,"oven":0,"autoclave":0,"sealer":1,"chiller":1,"filters":1},
  "kpi":{"throughput_min":0,"avg_wait_min":0,"contam_rate":0.0,"yield_eff":0.0},
  "hygiene":"A|B|C|D",
  "power_source":"GRID|BIOFUEL|SOLAR"
}
```

**Tier effects**: max hygiene, sealing tech, thermal control, labor productivity, contamination baseline.

---

## 3) Process Stages & Yields

**Stage A — Prep**: wash/trim; losses `loss_prep` (reduced by hygiene & skill).  
**Stage B — Cook**: combine & heat; `yield_cook` improves digestibility; consumes `fuel/power`.  
**Stage C — Fortify**: add electrolyte & vitamin mixes; optional (cost vs health benefit).  
**Stage D — Package**: portion into `sealed` or `unsealed` formats.  
**Stage E — Seal/Chill**: extends shelf‑life; requires `sealer/chiller`.  
**Stage F — Serve/Ship**: queue customers; create outgoing lots with route risk.

**Minute throughput**

```
cap = f(stations, staff, state) * tier_mult
yield_eff = base * equipment_quality * staff_skill * hygiene_factor
contam_prob = base_contam / hygiene_factor * (DEGRADED?1.5:1.0)
```

---

## 4) Shelf‑Life & Decay

For lot `L` produced at minute `t0`:

```
half_life_hours = h0 * seal_quality * chill_factor * hygiene_factor
quality(t) = exp(-ln(2) * (t/60) / half_life_hours)
contam_risk(t) = contam_prob * (t/60) ^ γ
```

- **Sealed**: long half‑life; **Unsealed**: short; **ELITE** gear increases `seal_quality`.  
- **Environment**: high temp/dust lowers `half_life`; power faults remove `chill_factor` temporarily.

Outcomes: **Expired** → reclaim; **Contaminated** → sickness risk if consumed (Clinic Flow integration).

---

## 5) Meal Effects on Agents

On consumption, apply:

```
ΔW = + water_L * absorption_eff(suit, health)
ΔN = + kcal_to_nutrition(kcal, protein, micro_mix_score)
Sta, ME recovery bonuses scaled by ration tier and palatability
Illness risk = contam_risk(current) * (1 - suit_filter_food) * (1 - clinic_campaign_factor)
```

**Palatability**: affects **Apathy vs Consume** action choice and small **Conciliation** boost if shared.

---

## 6) Queues & Venue Dynamics

- **Serving Modes**: `SOUP_LINE`, `CANTEEN`, `VENDING`, `CONTRACT_DELIVERY`.  
- **Queue Model**: arrivals Poisson; service time varies by tier and staff; security incidents possible at long waits.  
- **Priority Lanes**: for guards/workers on shift; reduces `avg_wait_min` but may create resentment (rumor).

Events: `KitchenQueueUpdate`, `MealServed`, `QueueBrawl` on extreme stress.

---

## 7) Supply & Contracts

- **Inputs** from farms/biomass processors/reclaimers via contracts; shortages ripple to **Market** and **Health**.  
- **Standing Civic Meals**: subsidized rations for outer wards; affect legitimacy.  
- **Private Catering**: ELITE rations for nobles/mercs; boosts performance.

Contracts specify **quality floor**, **lot size**, **delivery window**; breach triggers **Cases**.

---

## 8) Pricing & Subsidy

Minute quotes follow **Market v1** with item `ration:<tier>` priced in local credits or water;  
**subsidy** lowers posted prices at civic venues; **shortages** widen spreads.

**Nutrient Index**: clinics publish `NI_w` per ward; low `NI` raises sickness risk for the poor and increases **Security ρ_health**.

---

## 9) Maintenance & Hygiene

- **Hygiene audits** (clerks) set `hygiene` A–D; poor grade → contamination up, legitimacy down.  
- **Equipment wear** via **Maintenance Loop**; broken sealer/chiller harms shelf‑life & contamination.  
- **Water quality** (from reservoirs) affects prep/cook yields and illness risk.

---

## 10) Rumor & Legitimacy

- **Good meal lines** (fast, tasty) build civic legitimacy; **spoiled meals** or **queue fights** damage it.  
- Rumors spread via **Perception v1** with evidence from inspections, clinic reports, and videos.

---

## 11) Policy Knobs

```yaml
rations:
  tier_mult:
    LOW: 0.8
    MID: 1.0
    HIGH: 1.2
    ELITE: 1.4
  base_yield: 0.85
  base_contam: 0.02
  hygiene_factor:
    A: 1.3
    B: 1.1
    C: 1.0
    D: 0.8
  seal_quality:
    LOW: 0.8
    MID: 1.0
    HIGH: 1.2
    ELITE: 1.4
  half_life_hours:
    sealed: 72
    unsealed: 4
  queue_incident_threshold_min: 30
  palatability_bonus_by_tier:
    LOW: 0.00
    MID: 0.02
    HIGH: 0.05
    ELITE: 0.08
  clinic_campaign_factor: 0.15
```

---

## 12) Pseudocode

```python
def minute_kitchen_tick(kitchen):
    cap = compute_capacity(kitchen)
    produce_lots(kitchen, cap)
    update_queues_and_serve(kitchen)
    decay_lots(kitchen)
    if hygiene_due(kitchen): audit_and_grade(kitchen)
```

---

## 13) Explainability

For each **LotID** track:
- inputs (suppliers, batches), yields, hygiene grade, seal/chill settings, decay curve.  
- when/where served, consumer outcomes (health deltas, illness links).  
- “If sealed & chilled correctly, shelf‑life +48h; clinic cases −12%.”

---

### End of Food & Rations Flow v1
