---
title: Dosadi_Day0_Dry_Run_Playbook
doc_id: D-HEALTH-0002
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-HEALTH-0001
---
# **Day‑0 Dry‑Run Playbook v1**

A scripted end‑to‑end scenario to validate the minimal Dosadi loop using the specs we’ve authored. The playbook executes on a fresh world and should run in **sim minutes** with deterministic outcomes (given seed).

> **Tick**: 0.6s real‑time per tick; **Minute** = 100 ticks.  
> **Seed**: `worldgen.seed = 7719` (from Worldgen v1).  
> **Scope**: Worldgen → Barrel Cascade → Market → Labor → Rations → Maintenance → Escort → Clinic → Law/Case → Security feedback.  
> **Artifacts**: Emit and capture events + snapshots for assertions at each step.

---

## 0) Minimal Config

```yaml
worldgen:
  seed: 7719
  routes.gate_density: 0.6
  factions.per_ward: {guilds: 4-5, militias: 1-2, civic: 1, cults: 0-1, mercs: 0-1}
  policy.tax_rate: 0.10

market: { α_ref: 0.7, base_spread: 0.04 }
labor:  { min_wage_floor_by_venue: { CIVIC: 20, GUILD: 30, MERC: 35, ROYAL: 50, BLACK_NODE: 0 } }
security: { response_latency_target_min: 10 }
clinic: { esi_wait_threshold_min: { "1": 1, "2": 10, "3": 30, "4": 90, "5": 180 } }
maint:  { warn_threshold: 0.35 }
law:
  dispute_window_min: 720
  grace_min_default: 240
```

**Ward Focus**: run with Ward #1 (Well), one inner ward `W2`, one middle `W8`, one outer `W21`.

---

## 1) Boot & Sanity

**Step 1.1 — Worldgen**  
- Call `generate_world(cfg, seed)` → expect events: `WorldCreated`, `CreditRateUpdated`, `ContractActivated`(standing), `MaintenanceTaskQueued`(initial).  
- **Snapshot**: `routes.json`, `wards.json` for focused wards; ensure connectivity & reservoirs capacity sane.

**Assertions**  
- At least 1 kitchen & workshop in `W21`, and 1 reclaimer in `W8`.  
- Legitimacy `GovLegit` roughly inner > middle > outer (tolerances ±0.1).

---

## 2) Day‑0 Barrel Cascade (Single Shot)

**Step 2.1 — Plan**  
- From Ward #1, plan deliveries to `W2`, `W8`, `W21`. Create 3 `Escort` contracts; post 1 civic **escort job** per route.

**Step 2.2 — Execute**  
- Emit `BarrelDelivered` to `W2` and `W8` **without incident**.  
- Route to `W21` encounters a **minor ambush** with loss 5% volume; `AMBUSH` incident created.

**Assertions**  
- Royalties collected @10% credits to king per transfer.  
- `W21` reservoir delta reflects 95% of manifest (loss at route surcharge).  
- `SecurityIncidentCreated{AMBUSH}` exists on `W1→W21` route; risk adjusted down if escort succeeds in repel.

---

## 3) Market Quotes & Trades

**Step 3.1 — Quotes**  
- Post `PricePosted` for `water` and `ration:LOW` in `W21`. Expect wider spreads vs `W2`.  
- `CreditRateUpdated` for `credit:lord_W21` shows discount vs `king‑credit` (lower legitimacy).

**Step 3.2 — Trades**  
- Execute a **kiosk sale** of 500 L to a civic kitchen in `W21`.  
- Execute a **bazaar trade** (OTC) for `ration:LOW` from `W21` to a queue of 40 agents (simulate service for 30 min).

**Assertions**  
- Delivered price to `W21` includes route surcharge.  
- `TradeExecuted` entries have `venue` correct; inventory deltas reconcile with ledgers.

---

## 4) Labor: Shift Assignments

**Step 4.1 — Postings**  
- Post 2 jobs in `W21`: (a) **MAINT_REPAIR** for a leaking reservoir seal; (b) **ESCORT_GUARD** (fulfilled earlier).

**Step 4.2 — Matching**  
- Spawn 30 available workers in `W21` (mixed suits & skills). Run `minute_labor_tick` for 20 minutes.  
- Expect 1–2 **ShiftAssigned** to maintenance, 2–3 to kitchen line, 1 to escort.

**Assertions**  
- Wage for MAINT includes urgency + hazard premiums; **FX** contains discount for `credit:lord_W21`.  
- No‑shows ≤ 10%; reliability updates applied on completion.

---

## 5) Maintenance: Reservoir Seal Fault

**Step 5.1 — Fault**  
- Force `FaultDetected{RESERVOIR, SEAL}` in `W21` (DEGRADED). Queue `MaintenanceTaskQueued` with parts `seal_A`.

**Step 5.2 — Repair**  
- Assigned worker completes `MaintainFacility(SEAL)` in 180 sim minutes. Emit `MaintenanceCompleted`, KPIs updated.

**Assertions**  
- Ward `leak_rate` drops (compare before/after); **Market** narrows spread slightly post‑repair.  
- Legitimacy + small bump for timely repair in outer ward.

---

## 6) Kitchens & Rations

**Step 6.1 — Produce & Serve**  
- `W21` kitchen produces `ration:LOW` sealed and unsealed lots for 2 hours.  
- Queue serves 60 agents; average wait < 25 min; 1 queue brawl risk check (should not fire).

**Step 6.2 — Decay & Reclaim**  
- Advance 6 hours; unsealed lots **expire** → `Reclaim` 15% mass to greywater.

**Assertions**  
- `MealServed` count matches stock decrements; clinic intake (below) links to this lot batch if illness occurs.

---

## 7) Escort & Minor Clinic Case

**Step 7.1 — Escort Outcome**  
- From §2 ambush: one guard receives **blunt trauma (MODERATE)**; emits `ClinicIntake` at `W21` clinic.

**Step 7.2 — Clinic**  
- Triage `ESI=3`; treat for 40 min; **RECOVERED** with 1‑day work restriction. Inventory meds decremented.

**Assertions**  
- `ClinicOutcome` recorded; `Work Capacity` reduced for the agent; rumor generated with moderate salience.

---

## 8) Law/Case: Dispute from Late Delivery

**Step 8.1 — Open Dispute**  
- Because of ambush delay, `W21` kitchen files `Case` vs carrier for **late water** (contract had narrow window).

**Step 8.2 — Ruling**  
- `Case` proceeds: evidence includes **LEDGER** (high cred), **WITNESS** (medium), and **SENSOR** gate logs.  
- Arbiter issues **RESTORATIVE** ruling: small fee + deadline extension; both parties comply → `SETTLED`.

**Assertions**  
- `Reliability` for carrier neutral/slightly up; public ruling nudges `Legitimacy` up (fast resolution).

---

## 9) Security Feedback

**Step 9.1 — Daily Aggregation**  
- On **DayTick**, compute `LegitimacyRecalculated` for `W21`:  
  - `+` timely seal repair; `+` resolved case; `−` ambush (minor). Net small positive.  
- `Market` narrows spreads a touch; `Security` decreases route ambush probability slightly.

**Assertions**  
- ΔL in `[+0.01, +0.05]`; price change for water in `W21` within a few percent.

---

## 10) Log Capture & Assertions Checklist

**Events to capture (IDs & timestamps):**
- Worldgen: `WorldCreated`, `ContractActivated*`, `CreditRateUpdated*`  
- Cascade: `BarrelDelivered*`, `EscortAssigned/Completed`  
- Market: `PricePosted*`, `TradeExecuted*`  
- Labor: `JobPosted*`, `ShiftAssigned*`, `ShiftCompleted*`  
- Maintenance: `FaultDetected`, `MaintenanceTaskQueued`, `MaintenanceCompleted`  
- Security: `SecurityIncidentCreated(AMBUSH)`, `IncidentResolved`  
- Clinic: `ClinicIntake`, `TriageAssigned`, `TreatmentCompleted`, `ClinicOutcome`  
- Law: `CaseOpened`, `EvidenceSubmitted*`, `ArbiterRulingIssued`, `CaseClosed`  
- Daily: `LegitimacyRecalculated`, `CreditRateUpdated`

**State snapshots:** `wards.json`, `stocks.json`, `prices.json`, `risk.json`, `legitimacy.json` (before/after key steps).

**Assertions (summary):**
- Conservation: stocks reconcile with all trades & leaks.  
- Ledgers: credits minted (royal tax), FX used consistently.  
- Timers: contractual due/grace windows respected.  
- Queues: kitchen and clinic wait times within thresholds.  
- Risk: route ambush prob down after escort success.  
- Metrics: legitimacy Δ positive; spreads narrow accordingly.

---

## 11) Optional Variants (A/B)

**Variant A — Harsh Day**  
- Fail seal repair; clinic DEGRADE due to power fault; case delayed → expect `Legitimacy −`, price spike, more incidents.

**Variant B — Quiet Day**  
- No ambush; extra patrols; successful maintenance; **Legitimacy +**, spreads narrow, labor uptake up.

---

## 12) How to Use

- Feed this playbook’s steps to Codex as a **test harness**: for each step, call the relevant API from the specs, log events, and run the assertions.  
- Start with only the three wards; once green, expand to all 36 and enable stochastic incidents.

---

### End of Day‑0 Dry‑Run Playbook v1
