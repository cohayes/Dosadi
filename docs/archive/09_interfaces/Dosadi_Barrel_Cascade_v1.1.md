---
title: Dosadi_Barrel_Cascade
doc_id: D-PLANNER-0002
version: 1.1.0
status: archived
superseded_by:
  - D-INTERFACE-0001   # Hydraulic_Interfaces
owners: [cohayes]
last_updated: 2025-11-11
parent: D-PLANNER-0001
---
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

---

# **Barrel Cascade Planner v1 (Algorithm Spec)**

Daily planning algorithm for allocating Well draw to wards and vassals.  
Integrates with SVR v1, Event Bus v1, Scoring v1, and Tick Loop v1.

> Timebase: runs on **DayTick** (144k ticks). Emits `BarrelCascadeIssued` and seeds mandate contracts.

---

## 0) Objectives

1. **Stability** — prevent unrest by keeping wards above critical reserve.  
2. **Productivity** — route water where marginal output per liter is highest.  
3. **Legibility** — allocations must be explainable and auditable.  
4. **Control** — enable royal bias (political steering) without crashing stability.  
5. **Fairness over time** — rotation and minimum floors prevent starvation or dynastic lock‑ins.  

---

## 1) Inputs (Read‑Only)

From **SVR v1** / world state at DayTick:

- `reserve_w` — ward water stock (L).  
- `target_reserve` — policy buffer per ward (L) (can be tiered by ring).  
- `Spec_w ∈ [0,1]` — specialization score (rolling output signal).  
- `Loyal_w ∈ [0,1]` — loyalty to king (royal alignment).  
- `Risk_w ∈ [0,1]` — crisis intensity composite (env faults, security incidents).  
- `Need_w = norm(target_reserve - reserve_w; 0, target_reserve)` (Scoring v1).  
- `ProdMarginal_w` — liters → output conversion gradient (see §3).  
- `Reliab_w ∈ [0,1]` — reliability of ward governor faction (contract history).  
- `GovLegit_w ∈ [0,1]` — legitimacy of governor.  
- `RotationDebt_w ∈ [0,1]` — how long since last material allocation (fairness).  
- `LeakRate_w` — expected infra loss (fraction/day).  
- `SmuggleRisk_w ∈ [0,1]` — likelihood water exits intended recipients (intel).  
- `RoyalBias_w ∈ [-1,1]` — explicit policy knob for the “bowling” effect.  
- `Q_day` — total drawable liters from Well (policy/engineering cap).  
- `Tax_rate` — official skim on downstream transfers (0–0.2).

---

## 2) Hard Constraints

- **Conservation**: `sum(alloc_w) ≤ Q_day`.  
- **Safety Floor**: `alloc_w ≥ Floor_w` if `reserve_w < SafetyThreshold_w`.  
- **Max Throughput**: `alloc_w ≤ PipeCap_w` (logistics capacity).  
- **Bias Cap**: cumulative bias cannot reduce any ward below `MinRotationFloor` for more than `MaxStarveDays`.  
- **Leakage Adjustment**: expected delivered liters `eff_alloc_w = alloc_w * (1 - LeakRate_w)` must still satisfy floors.  

---

## 3) Productivity Model (Marginal Output per Liter)

For each ward, estimate the **marginal productivity** of an additional liter into its active pipelines today.

```
ProdMarginal_w = θ_spec * Spec_w + θ_rel * Reliab_w + θ_leg * GovLegit_w
                 + θ_chain * UpstreamSynergy_w - θ_risk * Risk_w
```
- `UpstreamSynergy_w` is computed from contracts that consume outputs of ward `w`.  
- Coefficients defaults: `θ_spec=0.4, θ_rel=0.25, θ_leg=0.15, θ_chain=0.15, θ_risk=0.2`.  
- Bound to `[0,1]`. Nonlinear option: apply `sqrt` or `log1p` to reduce runaway specialization.

---

## 4) Composite Allocation Score

Daily priority score before constraints:

```
NeedTerm   = aN * Need_w
ProdTerm   = aP * ProdMarginal_w
LoyalTerm  = aL * Loyal_w
RotateTerm = aR * RotationDebt_w
RiskTerm   = - aK * Risk_w
BiasTerm   = aB * RoyalBias_w
LeakTerm   = - aLeak * LeakRate_w
SmugTerm   = - aS * SmuggleRisk_w

Score_w = NeedTerm + ProdTerm + LoyalTerm + RotateTerm + RiskTerm + BiasTerm + LeakTerm + SmugTerm
```

**Defaults**: `aN=0.35, aP=0.25, aL=0.15, aR=0.10, aK=0.10, aB=0.08, aLeak=0.04, aS=0.03`.  
Clamp `Score_w` to `[0,1]` after affine rescale across wards each day (rank‑preserving).

---

## 5) Allocation Procedure

1. **Pre‑Floor Pass**  
   - Compute `Floor_w = max(0, SafetyThreshold_w - reserve_w)` bounded by `PipeCap_w`.  
   - Allocate floors to all `w` with `reserve_w < SafetyThreshold_w`. Subtract from `Q_day`.

2. **Scoring Pass**  
   - Compute `Score_w` for all wards (above).  
   - Compute soft shares:  
     `share_w = Score_w^γ / Σ Score^γ` with `γ ∈ [0.8, 2.0]` (γ>1 sharpens winners).

3. **Capacity Pass**  
   - Proposed `alloc_w = min(share_w * Q_remain, PipeCap_w)`.

4. **Leakage Correction**  
   - If `eff_alloc_w = alloc_w * (1 - LeakRate_w)` drops any ward below safety, top it up from remaining pool by taking proportionally from high‑Score wards (without violating their safety).

5. **Rotation & Fairness**  
   - Update `RotationDebt_w` (↓ for recipients; ↑ for others).  
   - Enforce `MinRotationFloor` for wards that exceed `MaxStarveDays`. This is a *small* guaranteed share (e.g., 0.5–2% of `Q_day`).

6. **Bias Budgeting**  
   - Cap the effect of `RoyalBias_w` by a daily **bias budget** `B_max` so political steering cannot crash safety.  
   - Implementation: recompute `Score_w` with `BiasTerm=0`, then add `BiasTerm` contributions and renormalize within `±B_max` liters moved from neutral plan.

7. **Mandate Seeding**  
   - For each recipient ward, generate downstream **mandate contracts** coherent with its specialization signals (e.g., if `Spec_w` high in suit repair, create maintenance mandates first).  
   - Publish civic notices; create tokenized black‑market proxies where appropriate.

8. **Emission**  
   - Emit `BarrelCascadeIssued { draw_L, targets, policy_bias, tax_rate }` (PUBLIC).  
   - Post `ContractActivated` for mandates.  
   - Record `CreditRateUpdated` if expected pricing shifts > ε.

---

## 6) Anti‑Gaming & Oversight

- **Reliability Dampener**: if a ward’s `Reliab_w` rises while **inspection rate** is low, apply skepticism factor until audits catch up.  
- **Leakage Audits**: randomize checks; if measured loss ≫ expected, raise `Corruption` and `SmuggleRisk`.  
- **Hoarding Detector**: if `reserve_w` climbs steadily while deliveries outpace consumption and contracts stall, trigger:  
  - `ContractDisputed` by royal clerks for nonperformance, or  
  - shift future allocations toward wards that convert liters to outputs.  
- **Crisis Guardrail**: if `Risk_w` > threshold, ensure minimal allocation to stabilize (security, clinics).

---

## 7) Parameterization (Policy Knobs)

```yaml
cascade:
  Q_day: 100000.0        # liters
  safety_threshold_by_ring:
    inner:  8000
    middle: 5000
    outer:  2500
  min_rotation_floor_pct: 0.005
  max_starve_days: 6
  gamma_share: 1.2
  bias_daily_budget_L: 4000
  epsilon_price_shift: 0.02
  pipecap_by_ward: {}    # liters/day
```

---

## 8) Worked Example (Small)

Wards A..E. `Q_day=10,000 L`. After floors, `Q_remain=7,000 L`. Scores → shares (`γ=1.2`).

| Ward | Score | Share | Cap | Alloc | Eff(−leak) |
|---|---:|---:|---:|---:|---:|
| A | 0.82 | 0.29 | 2500 | 2500 | 2400 |
| B | 0.74 | 0.23 | 3000 | 3000 | 2910 |
| C | 0.63 | 0.19 | 2000 | 1500 | 1470 |
| D | 0.41 | 0.12 | 3000 | 1000 |  950 |
| E | 0.33 | 0.09 | 1500 | 1000 |  950 |

Bias budget shifts +500 L from C→B (political favor), staying within `B_max`. Emit events and seed mandates that reflect A (maintenance), B (suit fabrication), etc.

---

## 9) Pseudocode

```python
def plan_cascade(world):
    Q = world.cascade.Q_day
    floors = {}
    for w in wards:
        floor = max(0, safety_threshold(w) - reserve(w))
        floors[w] = min(floor, pipecap(w))
    alloc = floors.copy()
    Q -= sum(floors.values())

    scores = {w: score_w(world, w) for w in wards}
    shares = softmax_pow(scores, gamma=cfg.gamma_share)
    for w in wards:
        if Q <= 0: break
        extra = min(Q * shares[w], pipecap(w) - alloc[w])
        alloc[w] += extra
    # Leakage correction
    for w in wards:
        eff = alloc[w] * (1 - leak(w))
        if reserve(w) + eff < safety_threshold(w):
            need = safety_threshold(w) - (reserve(w) + eff)
            donors = sorted(wards, key=lambda x: scores[x], reverse=True)
            for d in donors:
                if d == w: continue
                give = min(need, alloc[d] - floors[d])
                alloc[d] -= give
                alloc[w] += give
                need -= give
                if need <= 0: break
    # Bias budget
    neutral = alloc.copy()
    bias_move = budgeted_bias(neutral, scores, royal_bias, B_max=cfg.bias_daily_budget_L)
    alloc = combine(neutral, bias_move)

    seed_mandates(world, alloc)
    emit_barrel(world, alloc)
    return alloc
```

---

## 10) Emitted Data & Audit Trail

- `BarrelCascadeIssued`: includes `draw_L`, `targets`, `policy_bias` map, `tax_rate`.  
- **Royal Ledger**: store inputs, scores, floors, caps, final alloc, and reasons (top 3 contributing terms) for explainability.  
- **Civic Record** (public): ward‑level totals and rationale categories (safety/productivity/rotation).  
- **Black‑Market Mirror** (restricted): expected tokenized offers seeded from mandates.

---

## 11) Integration Touchpoints

- Consumes **Scoring v1 §8** scores (or its components) and **SVR** variables.  
- Emits events consumed by Law (contracts), Economy (prices), Rumor (public narratives), Governance (legitimacy).  
- Feeds back `RotationDebt_w` and updates specialization via `ProductionReported` downstream.

---

### End of Barrel Cascade Planner v1
