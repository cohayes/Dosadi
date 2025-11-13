---
title: Dosadi_Logistics_Corridors_and_Safehouses
doc_id: D-INFOSEC-0008
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-13
parent: D-INFOSEC-0001
---
# **Logistics Corridors & Safehouses v1 (Routes, Lanes, Staging, and Loss Models)**

**Version:** v1 — 2025‑11‑12  
**Purpose.** Define how goods, barrels, credits, and people move between wards with quantified risk, capacity, and staging. Formalize route tiers, convoy composition, safehouse quality, ambush/inspection logic, and scheduling—so Cascade, Clinics, Fabrication POs, and Markets have a realistic transport backbone.

Integrates with **Barrel Cascade v1.1**, **Escort & Security v1**, **Telemetry & Audit v1**, **Credits & FX v1.1**, **Production & Fabrication v1**, **Rumor v1.1**, **Law & Contract Systems v1**, **Agent Decision v1**, **Clinics v1.1**, and the **Tick Loop**.

> Timebase: lane headways **per 5–15 minutes**; staging windows **per hour**; risk/ETA dashboards **hourly**; patrol/ambush checks **per minute** during movement.

---
## 0) Entities & State

- **Corridor Graph** `G = (Wards, Edges)` where **Edge = Lane**:  
  `{lane_id, from_ward, to_ward, tier: INNER|MIDDLE|OUTER|SMUGGLER, capacity_units/hr, patrol_level, checkpoint: bool, toll_L, curfew: window, rumor_heat, last_incident_ts}`
- **Convoy** `{convoy_id, carrier: guild|lord|king, manifest{items, value_L, barrels?, meds?, parts?}, escort_units, stealth_score, speed_class, telemetry: on/off, route[], schedule}`
- **Safehouse** `{node_id, ward, class: A|B|C|D, storage_L, cold_chain: yes/no, seal_room: score, beds, armor, clinic_bay?, repair_bay?, audit_grade, bribe_table}`
- **Permit/Pass** `{issuer, valid_lanes, cargo_class, expiry, sigs}`
- **KPIs**: `OnTime%, Loss%, AmbushRate, InspectionRate, DelayMean/Var, CorridorThroughput, StagingUtilization`

---
## 1) Lane Tiers & Risk Profile

- **INNER**: walled/sealed sections; heavy patrol; checkpoint scanners + Arbiter presence; low ambush risk; high inspection risk; curfews strict.  
- **MIDDLE**: mixed control; predictable patrols; ambush risk moderate at choke points; inspections selective; curfews moderate.  
- **OUTER**: sparse patrols; local militias; ambush risk high; inspections rare; curfews loose; travel at your own risk.  
- **SMUGGLER**: off‑map connectors; capacity small; stealth preferred; ambush risk volatile; inspection risk low unless exposed; curfew none.

Risk components per minute while in motion:
```
P(ambush) = f(rumor_heat, last_incident_age, value_L, escort_mismatch, time_of_day, tier)
P(inspection) = g(checkpoint, patrol_level, permit_match, lane_tier, curfew_state)
P(delay) from congestion/weather(seal), checkpoint queues, or safehouse overfill
Loss severity ~ cargo value density, escort defeat prob, seal-tree tamper detection chance
```

---
## 2) Convoy Composition & ROE

- **Escort Units**: quality (gear, training), count, QRF latency; ROE depends on lane tier (deadly force restricted in INNER).  
- **Decoys & Split Loads**: reduce loss severity; increase scheduling complexity, safehouse slots.  
- **Telemetry**: continuous beaconing on official lanes; smuggler lanes may spoof or silence (higher post‑incident audit risk).  
- **Permits**: must match cargo class/lane tier; mismatch increases inspection/confiscation risk.

---
## 3) Safehouses (Staging & Shielding)

- **Class A**: armored, sealed bays, overlapping cameras, clinic & repair bays, Arbiter‑audited; ideal for high‑value barrels/meds.  
- **Class B**: sealed rooms, decent armor, limited repair; acceptable for mid‑value parts.  
- **Class C**: leaky, modest armor, basic bunk/storage; used in MIDDLE/OUTER for rest and small caches.  
- **Class D**: ad‑hoc caches; concealment > defense; preferred by smugglers; high theft/spoilage risk.

Effects:
- **Staging**: buffer against curfew; break long hauls into windows; reduce fatigue (Work–Rest link).  
- **Shielding**: better classes reduce `P(ambush)` at exits, cut delay (fast launch), and provide **dual-sign custody** rooms for barrels.  
- **Services**: cold chain for meds, seal rooms for suit upkeep, basic clinic triage, repair bays for escorts.

---
## 4) Scheduling & Headways

- **Timetables**: official lanes publish departure windows; tickets for high‑security slots (priority for cascade & clinics).  
- **Headway Control**: minimum spacing to avoid bunching and ambush clustering.  
- **Curfew Windows**: INNER lanes close at night; MIDDLE partial; OUTER open. Schedules auto‑route to legal windows.  
- **Stochastic ETAs**: ETA distributions updated hourly from telemetry + incident reports; used by Contracts and Clinics.

---
## 5) Contracts & Liability

- **Transport Contract**: `{route, lane_tier, safehouse_class_min, insurance_pct, delivery_window, penalties, audit_rights}`  
- **Insurance/Guarantee**: payout curve vs loss or delay; higher with telemetry + Class A/B staging.  
- **Arbiter Role**: resolve disputes using Telemetry & Audit bundles (custody chain, beacons, checkpoint scans).

---
## 6) Rumor & Deterrence

- **Rumor Heat** increases after visible ambush/smuggling busts; decays with quiet periods; influences `P(ambush)` and spreads.  
- **Deterrence Ops**: visible QRF drills, public board statistics, escort “victory” posts reduce rumor heat.  
- **Disinformation** (optional later): fake timetables or decoy signals to mislead bandits.

---
## 7) Policy Knobs (defaults)

```yaml
logistics:
  lane_capacity_units_per_hr:
    INNER: 40
    MIDDLE: 25
    OUTER: 15
    SMUGGLER: 4
  patrol_level: { INNER: 0.9, MIDDLE: 0.6, OUTER: 0.3 }
  checkpoint_base_inspect_p: { INNER: 0.25, MIDDLE: 0.12, OUTER: 0.04 }
  curfew_hours: { INNER: [22, 6], MIDDLE: [0, 5], OUTER: [] }
  safehouse_class_weight:
    A: { shield: 0.25, delay_cut: 0.20 }
    B: { shield: 0.15, delay_cut: 0.12 }
    C: { shield: 0.05, delay_cut: 0.05 }
    D: { shield: 0.00, delay_cut: 0.00 }
  rumor_heat_decay_per_hr: 0.10
  ambush_value_elasticity: 0.0005    # marginal risk per liter value
  escort_mismatch_penalty: 0.12      # risk multiplier if value >> escort strength
  telemetry_required_on: [ "INNER", "MIDDLE" ]
  safehouse_min_for_cargo:
    barrels: "A"
    meds: "A"
    high_value_parts: "B"
```

---
## 8) Event & Function Surface (for Codex)

**Functions**  
- `plan_route(origin, dest, cargo_profile)` → lane sequence + required safehouses + permits.  
- `book_staging(convoy_id, safehouse_class, t_window)` → reserves bays; returns slot token.  
- `dispatch_convoy(convoy_id, route)` → starts movement; enables telemetry if required.  
- `tick_movement(convoy_id)` → rolls for ambush/inspection/delay per minute; updates ETA.  
- `arrive_safehouse(convoy_id, node_id)` → restock, repair, custody update (dual‑sign for barrels).  
- `complete_delivery(convoy_id)` → closes contracts; triggers payments/penalties.  
- `update_rumor_heat(lane_id, event)` → increases/decreases heat; publishes to boards.

**Events**  
- `RoutePlanned`, `StagingBooked`, `ConvoyDispatched`, `InspectionOccurred`, `AmbushAttempted`, `AmbushRepelled`, `AmbushLoss`, `DelayLogged`, `SafehouseArrived`, `SafehouseDeparted`, `DeliveryCompleted`, `RumorHeatUpdated`.

---
## 9) Pseudocode (Indicative)

```python
def tick_movement(convoy, lane):
    base_amb = tier_base(lane.tier)
    escort_factor = escort_mismatch(convoy, lane)
    value_factor = convoy.manifest.value_L * policy.ambush_value_elasticity
    heat = lane.rumor_heat
    p_ambush = clamp(base_amb * (1 + escort_factor + value_factor) * (1 + heat))

    if rnd() < p_ambush:
        outcome = resolve_ambush(convoy, lane)
        emit("AmbushAttempted", {"lane": lane.id, "outcome": outcome})
        if outcome == "loss": apply_loss(convoy)

    p_inspect = checkpoint_prob(lane) * permit_mismatch(convoy)
    if rnd() < p_inspect:
        delay = inspect_delay(lane, convoy)
        convoy.eta += delay
        emit("InspectionOccurred", {"lane": lane.id, "delay": delay})

    # congestion & stochastic delay
    convoy.eta += random_delay(lane, safehouse_state(convoy))
```

---
## 10) Dashboards & Explainability

- **Corridor Map**: lane tiers, current rumor heat, incident pins, patrol intensity.  
- **Staging Board**: safehouse occupancy, next departure windows, class availability.  
- **Convoy Tracker**: ETAs with confidence bands, inspection/ambush history, custody chain.  
- **Loss & Insurance**: claims, payouts, hot lanes, escort effectiveness.

---
## 11) Test Checklist (Day‑0+)

- Cascade lanes on INNER with proper permits show low loss/high inspection; OUTER shows reverse.  
- Upgrading escort strength or splitting load reduces loss severity on high‑value hauls.  
- Safehouse class upgrades decrease delays and ambush probability at exits.  
- Rumor heat responds to incidents and decays per policy; deterrence ops cool hot lanes.  
- Telemetry & custody chains enable clear Arbiter rulings on disputes; missing telemetry increases penalties on official lanes.

---
### End of Logistics Corridors & Safehouses v1
