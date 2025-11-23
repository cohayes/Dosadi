---
title: Production_and_Fabrication
doc_id: D-ECON-0008
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-ECON-0001
---
# **Production & Fabrication v1 (Workshops, Quality, and Learning Curves)**

**Version:** v1 — 2025‑11‑11  
**Purpose.** Model how raw materials and parts are transformed into components, suits, tools, meds, and maintenance kits. Make quality & skill *matter* (seal integrity, durability, hygiene efficiency), connect throughput to Work–Rest schedules, price to FX, and legitimacy to delivery performance.

Integrates with **Credits & FX v1.1**, **Barrel Cascade v1.1**, **Suit–Body–Environment v1**, **Maintenance v1**, **Clinics v1.1**, **Law & Contract Systems v1**, **Rumor v1.1**, **Agent Decision v1**, and the **Tick Loop**.

> Timebase: job steps **per 5 Minutes**; QA/lot posting **hourly**; learning updates **per Shift**.

---
## 0) Entities & State

- **Workshop** `{id, ward, guild, tier: ELITE|HIGH|MID|LOW, stations, staff_roster, power_mode, water_buffer, hygiene, legitimacy}`  
- **Station** `{kind: CUT|MILL|PRINT|SEAL|STERILIZE|ASSEMBLE|QA, cycle_time, failure_rate, energy_L, water_L}`  
- **Recipe** `{product_id, grade: S|A|B|C, steps[], BoM{material: qty}, req_skills{type: lvl}, heat_profile, water_profile}`  
- **Job** `{job_id, recipe, qty, due_ts, client, contract_id?, escrow?, priority}`  
- **Lot** `{lot_id, product_id, grade, qa_score, warranty_ticks, seals, traceability}`  
- **Materials** `{id, type, grade, stock, reorder_s, reorder_S, fx_source}`  
- **KPIs**: `Throughput`, `Yield`, `Scrap%`, `Rework%`, `OnTime%`, `Energy/L`, `Water/L`, `Defect Density`

---
## 1) Flow & Scheduling

1) **Intake**: accept `Job` via contract or market. Validate BoM availability at FX‑priced inputs.  
2) **Dispatch**: assign to stations using a queueing rule (e.g., SPT, critical ratio, or priority).  
3) **Processing**: step cycles consume energy/water/materials; failures → `Rework` or `Scrap` based on grade.  
4) **QA & Traceability**: sample or 100% test; hash step telemetry; bind `Lot` with seals and warranty.  
5) **Delivery**: post to market, fulfill contract, or install (e.g., suit repair).  
6) **Learning Update**: adjust cycle times/failure rates with experience (see §4).

Work–Rest link: shifts throttle max cycles, and heat/water constraints cap effective throughput.

---
## 2) Grades, Quality, and Effects

- **Grades**: `S > A > B > C` mapped to tolerances and failure probabilities.  
- **Suit Components**:
  - **Seal Rings / Gaskets**: higher grade → **Suit_seal** decays slower; failure risk under heat ↓.  
  - **Filters**: higher grade → **exhalation/urine capture eff.** ↑; clinic hygiene loads ↓.  
  - **Armor Panels**: higher grade → **Suit_defense** vs (bludgeon/slash/pierce) ↑ but weight ↑ unless ELITE composites.  
- **Tools/Weapons**: higher grade → reliability ↑, maintenance interval ↑; rumor of “lemon lots” harms guild reputation.  
- **Clinic Consumables**: sterile pack quality → infection risk ↓; bad lot triggers **HygieneIncident** and Arbiter audit.

---
## 3) Materials, FX, and Reordering

- Each material has **FX‑sensitive** price (see Credits & FX).  
- **Reorder policy**: `(s,S)` per material with lead time via **Cascade lanes**; optional escorts for high value.  
- **Substitutions**: black‑market or scavenged parts can fill gaps with grade penalty and legal risk.

---
## 4) Learning Curves & Mastery

- **Artisan Skill** improves with successful cycles; failure/rework improves slower.  
- **Guild Mastery**: EWMA of shop output; unlocks **recipe optimizations** (shorter cycle, less scrap) and **new grades/models**.  
- **Knowledge Retention**: if staff churns or shop idles, decay mastery toward tier baseline.  
- **Innovation Hooks**: R&D jobs consume reagents for chance to unlock model upgrades (links to *Innovation Drive*).

---
## 5) Contracts, QA, and Liability

- **Performance Bonds**: for S/A grade deliveries; penalties for late or high defect density.  
- **Warranty**: lot warranty ticks; failures within window trigger **Replace/Repair** at maker cost.  
- **Traceability**: lot seals and telemetry allow Arbiter to arbitrate disputes and detect counterfeit/forgery.

---
## 6) Black‑Market Parts (Optional)

- **Pros**: fast availability, lower cost, relaxed paperwork.  
- **Cons**: grade uncertainty, higher failure, legal/rumor risk; clinics may refuse install; escorts may down‑rate eligibility.  
- **Memes**: “ghost gaskets” storylines amplify failure perceptions beyond reality; can be countered with QA proofs.

---
## 7) Policy Knobs (defaults)

```yaml
fabrication:
  queue_rule: "critical_ratio"   # or "SPT", "FIFO"
  shift_hours: 8
  station_uptime: 0.9
  qa_sampling: { S: 1.0, A: 0.5, B: 0.25, C: 0.1 }   # fraction tested
  warranty_ticks: { S: 10000, A: 7000, B: 4000, C: 2000 }
  learning:
    artisan_rate: 0.02
    guild_rate: 0.01
    decay_idle_days: 3
  fx_markup: 0.05
  escort_required_value_L: 200
  black_market_allowed: false
```

---
## 8) Event & Function Surface (for Codex)

**Functions**  
- `submit_job(guild_id, recipe_id, qty, due_ts, client)` → returns job_id.  
- `dispatch_job(job_id)` → route to stations; create WIP records.  
- `process_step(job_id, step)` → consume inputs; roll failure vs grade; produce telemetry.  
- `qa_and_pack(job_id)` → sample/test; create lot with seals, warranty.  
- `deliver(job_id)` → close contract, post rumor of on‑time delivery.  
- `reorder_materials(guild_id)` → creates POs with FX quotes and cascade escort options.  
- `post_lot_market(lot_id)` → list with grade/price; buyers can verify trace hashes.

**Events**  
- `JobAccepted`, `StepProcessed`, `ReworkStarted`, `ScrapLogged`, `LotPacked`, `LotDelivered`, `WarrantyClaim`, `POPlaced`, `POArrived`, `LotPosted`.

---
## 9) Pseudocode (Indicative)

```python
def process_step(job, step):
    consume_materials(job, step)
    consume_energy_water(step)
    p_fail = base_fail(step, grade=job.recipe.grade) * station_fail_factor(step.station) * (1 - artisan_skill)
    if rnd() < p_fail:
        if can_rework(step): mark_rework(job)
        else: mark_scrap(job)
    else:
        advance(job)
    log_telemetry(job, step)

def qa_and_pack(job):
    if sample(job, policy.qa_sampling[job.recipe.grade]):
        pass = run_tests(job)
        if not pass: mark_rework_or_scrap(job)
    lot = make_lot(job)
    seal_and_hash(lot)
    return lot
```

---
## 10) Dashboards & Explainability

- **Shop Board**: WIP, cycle times, yields, scrap/rework, FX material costs, energy/water per unit.  
- **Quality Board**: defect density by station, warranty claims by lot/grade.  
- **Delivery Board**: on‑time %, penalties, client satisfaction, meme polarity for reliability.

---
## 11) Test Checklist (Day‑0+)

- Quality grade maps to observable durability/seal decay in suits and infection risk in clinics.  
- Learning curves reduce cycle times and scrap under steady flow; idling causes decay.  
- FX and cascade shocks propagate to material cost and delivery delays; escorts reduce loss for high‑value POs.  
- Black‑market toggles shift failure distributions and legal/rumor risks as expected.

---
### End of Production & Fabrication v1
