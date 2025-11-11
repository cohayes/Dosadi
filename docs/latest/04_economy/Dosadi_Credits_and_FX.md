---
title: Dosadi_Credits_and_FX
doc_id: D-ECON-0003
version: 1.1.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-ECON-0001
---
# **Credits & FX v1.1 (Issuer Money, Floating Rates, Liquidity, and Hoarding Controls)**

**Purpose.** Define Dosadi’s multi‑issuer credit system (king/dukes/lords), floating exchange among credits, redemption to water, taxation links to the Barrel Cascade, and stabilization/anti‑hoarding tools. Adds market microstructure, swaplines, redemption queues, and crisis playbooks.

Integrates with **Barrel Cascade v1.1**, **Law & Contract Systems v1**, **Rumor v1.1**, **Security/Escort v1**, **Market v1**, **Clinics v1**, **Work–Rest v1**, **Succession v1.1**, and the **Tick Loop**.

> Timebase: quotes **per Minute**; books clear **per 5 Minutes**; indices **hourly**; policy ops **on demand**.

---
## 0) Entities & State

- **Issuer** `I`: `{id, title, reservoir_L, redeem_rate_L_per_credit, policy_band, legitimacy, audit_status}`  
- **Credit** `C_I`: bearer token (electronic/physical) redeemable from issuer reservoir at **posted redeem_rate**; subject to queues.
- **FX Venue**: continuous double auction over pairs `C_I ↔ C_J` and `C_I ↔ H2O` (spot redemption implied).  
- **Order Book** per pair: bids/asks with sizes, maker IDs, fee tier, last trade, micro‑vol metrics.  
- **Indices**: `WaterBasis_I = implied L/credit at spot` vs posted redeem; `FXI_ward` basket for local prices.  
- **Queues**: `RedemptionQueue_I` with service rate from staff, meter throughput, and security posture.  
- **Swapline**: credit facility between King and issuer `I` with haircut; collateralized in barrels, tax receipts, or future mandates.
- **Controls**: hoarding levy, issuance caps, open‑market ops (OMO), corridor targets, emergency ration tokens.

---
## 1) Money Mechanics

- **Issuance:** Issuer mints **credits** when paying wages, buying goods, or settling taxes owed to itself. Mint size constrained by `reservoir_L`, expected cascade allocations, audit status, and **policy_band** (soft cap).  
- **Redemption:** Holder presents `C_I` at issuer depot; receives water at `redeem_rate_L_per_credit`, net of fees; enters queue if backlog.  
- **FX:** Credits float. `Spot(C_I/C_J)` set by order book; arbs tie it to relative redeemables adjusted by queues and risk (`legitimacy`).  
- **Fees:** maker/taker fees; redemption fee; foreign issuer fee for off‑ward redemption.  
- **Seigniorage:** Issuer P&L = issuance vs redemption + fees − tax & audit penalties.

---
## 2) Price Formation & Order Flow

- **Natural Flow:** wages (sell to food/clinic), cascade days (king pays in king‑credits), contracts (tokenized invoices).  
- **Makers:** guild treasuries, money‑changers, reclaimers; provide quotes around `WaterBasis` with spread for risk/queue time.  
- **Takers:** households and mercs; urgency spikes after clinic bills, escort casualties, or famine rumors.  
- **Microstructure:** price impact function with depth; wide spreads during security incidents; cross‑pair arbitrage allowed.  
- **Rumors:** negative memes about issuer → widen spreads, reduce depth, elevate redemption queues.

---
## 3) Hoarding & Inflation Dynamics

- **Hoarding (Despair):** agents increase buffer balances and reduce offers; velocity ↓; output falls; clinics/maintenance underfunded.  
- **Inflation (Token Flood):** issuers over‑mint vs reservoir & mandate; FX weakens; redemption queues lengthen; prices in H2O ↑.  
- **Signals:** Monitor `Velocity_I`, `QueueLen_I`, `WaterBasis_I` vs posted redeem, and `Spread_I` dispersion.

---
## 4) Stabilizers & Policy Toolkit

- **King OMO:** King buys/sells issuer credits for king‑credits or water to pull FX back into **corridor**.  
- **Swaplines:** temporary lines with haircut `h`; collateral = sealed barrels in bonded safehouse + tax receipts.  
- **Corridor Targeting:** policy aims `Spot(C_I/H2O)` within `[lower_I, upper_I]`; breaches trigger ops.  
- **Hoarding Levy:** time‑varying fee on idle balances above threshold; waive for critical services/inventory.  
- **Redemption Rationing:** issue numbered tickets with ETA; market can trade place in line (secondary market).  
- **Issuer Discipline:** if `WaterBasis_I` persistently below posted ⇒ `AuditFlag`; Arbiter may impose issuance cap/receivership.  
- **Emergency Rations:** king can drop **ration tokens** (non‑transferable) redeemable for fixed liters to break famine spirals.  
- **Transparency:** publish **Liquidity Dashboard**; inner wards show depth/queues; outer wards partial.

---
## 5) Tax & Cascade Linkage

- On official receipt of cascade water, **Royal Tax** computed (see Barrel Cascade v1.1). Issuer pays **king‑credits** at current FX.  
- **Credit Drain:** tax payment reduces issuer liquidity; spreads may widen; swaplines pre‑positioned to smooth.  
- **Clerk Telemetry:** credits rate logged per handoff; rumor boards ingest to anchor expectations.

---
## 6) Algorithmic Quotes & Risk

Indicative mid for pair `C_I/H2O`:
```
Mid_I = (redeem_rate_I / (1 + queue_penalty_I) ) * (1 - risk_disc_I)
```
where `queue_penalty_I = f(queue_len, service_rate)` and `risk_disc_I = g(legitimacy, audits, security)`.  
Spread `≈ base + k * volatility + rumor_heat`. Depth shaped by maker capital and policy incentives.

---
## 7) Crises & Playbooks

- **Run on Issuer:** `QueueLen_I↑`, `WaterBasis_I↓`, spreads blow out. Playbook: king swapline + ration tokens; announce cascade priority; Arbiter audit.  
- **FX Seize‑up:** cross‑pair liquidity vanishes. Playbook: corridor widening; maker fee rebates; temporary central clearing at Festival Board.  
- **Hoarding Wave:** velocity crash without over‑issuance. Playbook: levy + ration work credits (pay extra for hot/risky tasks) + public dashboards.  
- **Fraud Exposure:** meter/ledger tamper. Playbook: receivership; freeze issuance; convert credits at haircut; replace leadership per Succession v1.1.

---
## 8) Policy Knobs (defaults)

```yaml
credits_fx:
  corridor_pct: { lower: -0.05, upper: 0.05 }  # allowed deviation from WaterBasis
  maker_fee: 0.002
  taker_fee: 0.004
  redemption_fee: 0.005
  foreign_issuer_fee: 0.01
  queue_penalty_coeff: 0.002   # per minute of ETA
  risk_disc_map:
    legitimacy: { a: 0.15, b: 0.50 } # risk = a*(1-L)^b
    audit_flag: 0.05
    security_alert: 0.03
  hoarding_levy:
    threshold_days_velocity: 5
    rate_per_day: 0.0015
    exemptions: [ "clinics", "escorts", "food_guilds" ]
  swapline:
    haircut: 0.08
    max_ratio_to_reservoir: 0.25
    tenor_hours: 24
  omo_rebate_on_makers: 0.0005
  publish_liquidity_dashboard: true
```

---
## 9) Event & Function Surface (for Codex)

**Functions**  
- `post_redeem_rate(issuer, L_per_credit)` → updates official rate & corridor.  
- `submit_order(pair, side, px, qty, agent_id)` → order book add; returns order_id.  
- `cancel_order(order_id)`; `match_books(pair)` every 5 minutes.  
- `quote_mid(pair)` → indicative mid with penalties.  
- `redeem(issuer, credits_qty)` → enqueue; returns ticket with ETA; logs water outflow.  
- `apply_swapline(issuer, qty)` → credits against collateral with haircut.  
- `open_market_op(side, pair, qty)` → king buys/sells to defend corridor.  
- `update_indices()` → WaterBasis, spreads, queue ETAs; publish dashboards.
- `assess_hoarding(ward)` → levy fees on excessive idle balances.

**Events**  
- `RatePosted`, `OrderAccepted`, `OrderMatched`, `OrderCancelled`, `MidQuoted`, `RedeemQueued`, `RedeemServed`, `SwaplineGranted`, `OMOExecuted`, `LiquidityDashboardPublished`, `HoardingLevyApplied`, `AuditFlag`, `ReceivershipStarted`.

---
## 10) Pseudocode (Indicative)

```python
def quote_mid(issuer):
    q_pen = coeff * eta_minutes(issuer.queue)
    risk  = a * (1 - issuer.legitimacy)**b
    mid = issuer.redeem_rate / (1 + q_pen) * (1 - risk)
    return mid

def open_market_op(side, pair, qty, corridor):
    mid = quote_mid(pair.base_issuer)
    dev = (last_trade(pair) - mid) / mid
    if abs(dev) > corridor: 
        place_market_orders(side, qty)
        emit("OMOExecuted", {...})

def redeem(issuer, qty):
    eta = queue_eta(issuer.queue, qty)
    ticket = issue_ticket(issuer, qty, eta)
    enqueue(issuer.queue, ticket)
    emit("RedeemQueued", {"issuer": issuer.id, "qty": qty, "eta": eta})
    return ticket
```

---
## 11) Dashboards & Explainability

- **Liquidity Board**: depth by price level, spreads, last trade, maker IDs (hashed), queue ETAs, swapline usage.  
- **Water Basis**: posted vs implied; variance sparks audit/rumor hooks.  
- **Crisis Panel**: triggers & playbooks executed; counterfactual impact estimates.

---
## 12) Test Checklist (Day‑0+)

- Mid quotes track posted redeem minus queue/risk penalties; deviations corrected by OMOs within corridor.  
- Hoarding levy lowers idle balance ≥ X% without crippling makers; exemptions honored.  
- Swaplines reduce spreads/queues measurably during cascade tax drains.  
- Fraud/Audit flags propagate to wider spreads and receivorship when persistent.

---
### End of Credits & FX v1.1
