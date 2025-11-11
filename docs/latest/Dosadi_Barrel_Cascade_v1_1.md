# **Barrel Cascade v1.1 (Allocation, Logistics, Escorts, and Tax Telemetry)**

**Purpose:** Plan and execute the daily water cascade from the Well (Ward #1) to vassal reservoirs and onward to wards, with explicit integration to escorts/security, Credits & FX taxation, audits, and rumor controls.

Integrates with **Credits & FX v1**, **Security/Escort v1**, **Smuggling Loop v1**, **Environment Dynamics v1**, **Work–Rest Scheduling v1**, **Maintenance v1**, **Law & Contract Systems v1**, **Rumor & Perception v1**, **Clinics v1**, and the **Tick Loop**.

> Cadence: **Daily Plan** at dawn; **Minute** logistics ticks while in transit; **Hourly** audit/telemetry aggregation; final **Daily Close** ledger.

---

## 0) Entities & State

- **Well (Ward #1)**: `{extraction_L, buffer_L, priest_guild, meters, audit_keys}`

- **Issuers / Lords**: `{issuer_id, reservoir_L, redeem_rate, legitimacy, audit_status}`

- **Cascade Plan (Day d)**: list of **Mandates** `{id, objective, liters_L, priority, lanes[], escrow_rules}`

- **Lane**: `{source, sinks[], route, escort_policy, schedule, tax_basis}`

- **Convoy**: `{id, lane_id, barrels[], escort_team, clerk, evidence_kit}`

- **Meters & Telemetry**: flow meters, seal records, route beacons, camera hashes.

---

## 1) Daily Planning (Mandates & Lanes)

1) **Inputs**: production mandates (king), ward signals (shortages, unrest), FX discounts, legitimacy, audits.

2) **Select Wards** to receive allocations; assign **liters_L** and **priority**.

3) **Lane Design** per mandate:

   - Route (gates vs wild bypass, safehouses), schedule window, **escort policy** (size, ROE), **clerk** attached.

   - **Tax basis**: gross liters; applies `RoyalTaxAssessed` to issuer receiving official water.

4) **Escrow Rules**: tokenized bills of lading; chain‑of‑custody and meter snapshots required at each handoff.

Events: `CascadePlanned{day}` with mandate summaries.

---

## 2) Barrel Spec & Handling

- **Barrel**: `{serial, capacity_L, tare, seal_id, temp, GPS, meter_snapshots[]}`

- **Seals**: tamper‑evident + cryptographic logs; breakage auto‑opens case.

- **Handoffs**: Well → issuer depot → downstream venues; each handoff appends meter snapshot + clerk signature + time.

Events: `BarrelFilled`, `BarrelSealed`, `BarrelHandoffLogged`.

---

## 3) Security Integration

- **Escort Policy** derived from lane risk: `close_security`, `overwatch`, `QRF`, **ROE**.

- **Pre‑Run Check**: convoy readiness, suit diagnostics, ammo/meds, camera health; emits `EscortPlanned` & `ROEPosted`.

- **Minute Security Tick** during transit: recon/ambush checks; if engagement → **Escort & Combat v1** takes over.

- **Post‑Run**: evidence bundle (GPS path, video hashes, fired‑rounds, casualties, barrel meter diffs) → audits, rumor counter.

Events: `ConvoyDeparted`, `AmbushDetected|AmbushSprung`, `EngagementEnded`, `EvidenceSubmitted`.

---

## 4) Tax & Credits Telemetry

- On **official receipt** at issuer depot: compute **royal tax** on liters (`5–15%`, policy) and emit `RoyalTaxAssessed`.

- **Payment rails**: issuer pays tax in **king‑credits** at current FX (see Credits & FX v1); clerk logs rate and queue times.

- **FX Signals**: large allocations narrow local water premium; missed deliveries widen it; tax drains can tighten issuer liquidity.

- **Dashboards** publish: `liters_delivered`, `tax_paid (king‑credits)`, `coverage_after`, `redeem_wait_min`.

Events: `RoyalTaxAssessed`, `CreditsRedeemed|CreditRateUpdated` (downstream effects).

---

## 5) Audits & Chain‑of‑Custody

- **Clerks/Auditors Guild** attaches:

  - `LEDGER`: mandate → lane → convoy → barrel events.  

  - `SENSOR`: meter snaps at fill/hand‑off/arrival; variance threshold (`≤ 0.3%`) or open `Case`.

  - `VIDEO`: seal view at each stop; `WITNESS`: named sign‑offs; hashes uploaded hourly.

- **Variance Handling**: 

  - Small: adjust for temp/pressure; log correction.

  - Medium: `Investigate` (possible leaks/bribes).  

  - Large: `CaseOpened` (theft or fraud); possible seizures; legitimacy hit.

Events: `AuditStarted/Completed`, `ChainOfCustodyVerified`, `CaseOpened`.

---

## 6) Minute Logistics Tick (Transit)

- Position update, ETA, fuel/power check, barrel temps, crew heat/fatigue (routes Work–Rest pauses automatically).

- Safehouse stops: maintenance quicks, hydration, camera uploads.  

- If **delay risk** → send `DelayAlert` to sinks; markets/rumors adjust expectations.

Events: `ConvoyTick`, `DelayAlert`, `SafehouseStopLogged`.

---

## 7) Daily Close & Allocation Ledger

- For each mandate: 

  - `allocated_L`, `delivered_L`, `loss_L` (combat/leak/theft), `tax_L_eq`, `FX_at_tax`, `coverage_post`, `wait_post`.

- Publish **Daily Cascade Ledger** per ward; inner wards public, outer may redact (rumor variance ↑).

- Trigger **Policy** knobs for next day (rebalance lanes, increase escorts, open amnesty corridors for food/water if famine).

Events: `CascadeClosed{day}`, `PolicyAdjusted`.

---

## 8) Policy Knobs (defaults)

```yaml
barrel_cascade:
  daily_slots: 14
  royal_tax_pct: 0.10
  variance_tolerance: 0.003
  fx_apply_at: "issuer_receipt"   # or "well_dispatch"
  escort_policy_by_risk:
    low:    { close: 2, overwatch: 0, qrf: true }
    medium: { close: 3, overwatch: 1, qrf: true }
    high:   { close: 4, overwatch: 1, qrf: true }
  roe_templates:
    inner:  { bias_less_lethal: 0.6, evidence_required: true }
    middle: { bias_less_lethal: 0.4, evidence_required: true }
    outer:  { bias_less_lethal: 0.2, evidence_required: false }
  safehouse_interval_km: 12
  delay_alert_min: 30
  meter_correction: { temp_coeff: 0.0003, pressure_coeff: 0.0002 }
```

---

## 9) Event & Function Surface (for Codex)

**Functions**

- `plan_cascade(day, mandates)` → builds lanes & convoys; `CascadePlanned`.

- `dispatch_convoy(lane_id)` → `ConvoyDeparted`; initializes escort plan and clerk ledger.

- `minute_convoy_tick(convoy_id)` → updates transit; triggers security tick; logs safehouse stops.

- `handoff_barrel(convoy_id, sink_id, barrel_id)` → meter snapshot, `BarrelHandoffLogged`.

- `close_cascade(day)` → aggregates results; emits `CascadeClosed` and dashboards.

- `post_tax_receipt(issuer, liters, fx_rate)` → `RoyalTaxAssessed` + Credits & FX hooks.

- `start_audit(convoy_id|lane_id)` → `AuditStarted` and later `Completed`.

**Events**

- `CascadePlanned`, `ConvoyDeparted`, `ConvoyTick`, `DelayAlert`, `SafehouseStopLogged`, `AmbushDetected`, `AmbushSprung`, `EngagementEnded`, `BarrelHandoffLogged`, `RoyalTaxAssessed`, `AuditStarted`, `ChainOfCustodyVerified`, `AuditCompleted`, `CaseOpened`, `CascadeClosed`, `PolicyAdjusted`.

---

## 10) Pseudocode (Plan → Run → Close)

```python
def plan_cascade(day, signals):
    mandates = choose_mandates(signals)
    lanes = []
    for m in mandates:
        r = pick_route(m, risk_map)
        escorts = pick_escort_policy(r.risk)
        lane = Lane(m, r, escorts, clerk=assign_clerk())
        lanes.append(lane)
    emit("CascadePlanned", {...})
    return lanes

def minute_convoy_tick(convoy, env):
    update_eta(convoy)
    security_step(convoy)  # may emit ambush events
    if delay_expected(convoy): emit("DelayAlert", {...})
    if reached_sink(convoy):
        for b in convoy.barrels: handoff(b, sink, clerk=convoy.clerk)

def close_cascade(day, lanes):
    ledger = aggregate(lanes)
    for entry in ledger:
        assess_tax(entry.issuer, entry.delivered_L, fx_at(entry.time))
    emit("CascadeClosed", {"day": day, "ledger": ledger})
```

---

## 11) Typical Scenarios

- **Smooth Inner Lane**: narrow FX spread, on‑time, tax paid, legitimacy +ε.  

- **Outer Lane Ambush**: partial loss; clinics/maintenance spike; FX discount widens; king opens swapline; next day escorts upscaled.  

- **Variance Fraud**: meter tamper detected; Arbiter seizes depot; receivership risk for issuer.

---

## 12) Dashboards & Explainability

- **Cascade Board** (public/ward): allocations vs deliveries, tax paid, ETA, delay alerts, escort incidents.  

- **Evidence Bundle**: route GPS, video hashes, meter deltas, chain‑of‑custody, tax receipts, audit status.  

- **Counterfactuals**: “If high‑risk route had +1 overwatch & closer safehouse spacing, expected loss −35%.”

---

## 13) Test Checklist (Day‑0+)

- Tax ledger equals 5–15% of delivered liters valued at stated FX at receipt.  

- Chain‑of‑custody detects > 0.3% variance reliably; opens cases on breach.  

- Escort integration flips a fraction of `CARGO_SEIZED` → `AMBUSH_REPELLED` proportional to policy.  

- Delay alerts propagate to markets (FX/price spreads) and rumor system.

---

### End of Barrel Cascade v1.1
