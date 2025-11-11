---
title: Dosadi_Compact_API_Checklist
doc_id: D-PLANNER-0001
version: 1.0.0
status: stable
owners: [cohayes]
depends_on: 
includes:
  - D-PLANNER-0002  # Barrel_Cascade
last_updated: 2025-11-11
---
# **Compact API Checklist (Dosadi v1)**

A terse, implementation‑oriented index of entities, events, and function signatures referenced across v1 specs. Designed to be taped next to the keyboard while wiring the prototype + Day‑0 Playbook.

> **Timebase**: `Tick=0.6s`, `Minute=100 ticks`, `Day=1440 minutes`.  
> **ID format**: prefix + short base36 (e.g., `ward_W21`, `fac_F0a9`, `case_C5k7`).  
> **Visibility**: `PUBLIC | RESTRICTED` (black‑node/military) with rumor leak chance per venue policy.  
> **All functions return** `{ok: bool, err?: code, data?: ...}`; **events** are emitted via `emit(event_name, payload)`.

---

## 0) Core State (SVR)

- **World**: `{ seed, time_min, wards:[Ward], routes:[Route], policy:{...} }`
- **Ward**: `{ id, ring, sealed, env:{temp, humidity, o2, rad}, stocks:{water_L, biomass_kg, credits:{}}, legitimacy, reliability, risks:{ρ_env,ρ_crime,ρ_mil,ρ_reb,ρ_health}, facilities:[Facility], factions:[Faction], agents:[Agent?] }`
- **Route**: `{ id, src, dst, distance_min, checkpoint_lvl, capacity, ambush_prob }`
- **Facility**: see Maintenance v1.
- **Faction**: `{ id, type, ward, legitimacy, reliability, lawfulness, credits_issuer? }`
- **Agent**: see Agents v1 (body/suit/drives minimal for Day‑0).

---

## 1) Time & Ticks

```python
tick() -> MinuteTick every 100 ticks; DayTick every 1440 MinuteTicks
on_minute() -> run quotes, risks, maintenance wear, queues, labor matching
on_day() -> recompute references (prices, legitimacy), rotate contracts
```

Events: `MinuteTick`, `DayTick` (DIAGNOSTIC).

---

## 2) Worldgen

```python
generate_world(cfg, seed) -> World
```
Emits: `WorldCreated`, `CreditRateUpdated*`, `ContractActivated*`, `MaintenanceTaskQueued*`

---

## 3) Barrel Cascade (Planner + Delivery)

```python
plan_cascade(day) -> [DeliveryPlan]
start_delivery(plan_id) -> {escort_job_id, manifest}
complete_delivery(plan_id, loss_frac=0.0) -> BarrelDelivered
```
Events: `DeliveryPlanned`, `EscortJobPosted`, `EscortAssigned/Completed`, `BarrelDelivered`, `RoyalTaxAssessed`

Payload: `BarrelDelivered{ from, to, liters, credits_tax, loss_frac, route_id }`

---

## 4) Market

### 4.1 Reference & Quotes
```python
update_daily_reference(ward_id, item_id) -> P_ref
minute_quote_update(ward_id, item_id, venue_id) -> {bid, ask, mid, spread}
```
Events: `PricePosted{ ward, item, venue, bid, ask, mid, spread }`, `CreditRateUpdated{ issuer, FX }`

### 4.2 Trades
```python
kiosk_trade(ward, item, side, qty, account) -> TradeExecuted
bazaar_bargain(buyer, seller, item, qty, deadline_min) -> {price, status}
place_order(venue, pair, side, price, qty) -> OrderPlaced
cancel_order(order_id) -> OrderCancelled
```
Event: `TradeExecuted{ venue, item/pair, qty, price, parties?, visibility }`

---

## 5) Labor

```python
post_job(JobSpec) -> JobPosted
minute_labor_tick(ward_id) -> [ShiftAssigned]
start_shift(assignment_id) -> ShiftStarted
complete_shift(assignment_id) -> ShiftCompleted
```
Events: `JobPosted/Updated/Closed`, `ShiftAssigned/Started/Completed`, `NoShow`

---

## 6) Maintenance

```python
queue_task(TaskSpec) -> MaintenanceTaskQueued
start_maintenance(task_id) -> MaintenanceStarted
complete_maintenance(task_id, parts_used) -> MaintenanceCompleted
```
Events: `FaultDetected`, `MaintenanceTaskQueued/Started/Completed`, `FacilityStateChanged`

---

## 7) Security

```python
minute_security_update() -> [SecurityIncidentCreated]
respond_to_incident(incident_id, policy) -> IncidentResolved
post_bounty(incident_id, reward) -> BountyPosted
```
Events: `SecurityIncidentCreated{ type, ward/route, severity }`, `IncidentResolved`

---

## 8) Clinics

```python
clinic_intake(agent_id, clinic_id) -> {visit_id, ESI}
minute_clinic_tick(clinic_id) -> updates queues & outcomes
discharge(visit_id, result) -> ClinicOutcome
```
Events: `ClinicIntake`, `TriageAssigned`, `TreatmentStarted/Completed`, `ClinicDiverted`, `ClinicOutcome`

---

## 9) Kitchens & Rations

```python
minute_kitchen_tick(kitchen_id) -> {produced_lots, served_meals}
audit_hygiene(kitchen_id) -> HygieneGraded
```
Events: `MealServed`, `KitchenQueueUpdate`, `HygieneGraded`, `LotExpired`, `LotReclaimed`

---

## 10) Law & Cases (incl. Evidence Scoring)

```python
open_case(plaintiff, defendant, cause, contract_id?) -> CaseOpened
submit_evidence(case_id, Evidence) -> EvidenceAccepted
score_case(case_id) -> {strength, confidence}
issue_ruling(case_id, order) -> ArbiterRulingIssued
close_case(case_id, status) -> CaseClosed
```
Events: `CaseOpened`, `EvidenceSubmitted/Accepted`, `CaseScoresUpdated`, `ArbiterRulingIssued`, `CaseClosed`

**Evidence**: `{ type: LEDGER|SENSOR|VIDEO|WITNESS|MEDICAL|TOKEN|INTEL|ANALYSIS, src, time_min, supports?, coc, venue }`

---

## 11) Rumor & Perception

```python
emit_rumor(source_id, topic, cred, sal) -> RumorEmitted
minute_perception_update(ward_id) -> memory decay & propagation
```
Events: `RumorEmitted`, `MemoryCreated/Updated/Expired`

---

## 12) Metrics & Legitimacy

```python
recalc_legitimacy(ward_id) -> LegitimacyRecalculated
publish_labor_stats(ward_id) -> LaborStatsUpdated
```
Events: `LegitimacyRecalculated`, `LaborStatsUpdated`, `MarketIndexUpdated`

---

## 13) Common Schemas

**Money**
```json
{"credits":{"issuer":"king|lord_W21|...","amount":1200},"water_L":240}
```

**JobSpec** (abbr.)
```json
{"venue":"CIVIC","employer":"fac_Maint","kind":"MAINT_REPAIR","ward":"W21",
 "shift":{"start_min":540,"len_min":360,"n_slots":2},
 "requirements":{"skills":{"mechanic":2},"suit":"MID"},
 "pay":{"credits":{"issuer":"lord_W21","min":120},"water_L":{"min":4},"split":"MIX"}}
```

**TaskSpec** (abbr.)
```json
{"facility":"fac_res_W21","component":"seal_A","kind":"REPAIR","priority":"HIGH",
 "eta_min":180,"parts":[{"sku":"seal_A","qty":1}],"skills":{"mechanic":2}}
```

**DeliveryPlan**
```json
{"from":"W1","to":"W21","liters":5000,"route":"R_1_21","escort_req":true}
```

---

## 14) Error Codes (minimal)

- `E_NOT_FOUND`, `E_NO_CAPACITY`, `E_BAD_STATE`, `E_BAD_PERMS`, `E_INVALID`, `E_INSUFF_FUNDS`, `E_ROUTE_BLOCKED`, `E_TIMEOUT`

---

## 15) Visibility & Audit

Every event/function accepts optional:
```json
{"visibility":"PUBLIC|RESTRICTED","auditable":true|false,"evidence_refs":[...]} 
```
- **PUBLIC** goes to rumor bus; **RESTRICTED** can still leak if flagged.

---

## 16) Policy Knobs Access

```python
get_policy(module) -> dict
set_policy(module, patch) -> ok   # restricted to admin/king for Day-0
```

---

## 17) Logging & Snapshots

```python
snapshot(kind) -> blob   # 'wards|routes|stocks|prices|risk|legitimacy|labor|cases'
replay(events[]) -> deterministic sim for tests
```

---

## 18) Day‑0 Playbook Hooks (Step ↔ API)

- **Worldgen** → `generate_world`
- **Cascade** → `plan_cascade`, `start_delivery`, `complete_delivery`
- **Market** → `update_daily_reference`, `minute_quote_update`, `kiosk_trade`, `bazaar_bargain`
- **Labor** → `post_job`, `minute_labor_tick`
- **Maintenance** → `queue_task`, `start_maintenance`, `complete_maintenance`
- **Escort** → via `EscortJobPosted` + `ShiftAssigned` (labor) + `SecurityIncidentCreated` if ambush
- **Kitchens** → `minute_kitchen_tick`
- **Clinic** → `clinic_intake`, `minute_clinic_tick`, `discharge`
- **Law** → `open_case`, `submit_evidence`, `score_case`, `issue_ruling`, `close_case`
- **Daily** → `recalc_legitimacy`

---

### End of Compact API Checklist
