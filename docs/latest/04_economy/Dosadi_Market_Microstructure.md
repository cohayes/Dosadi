---
title: Dosadi_Market_Microstructure
doc_id: D-ECON-0002
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-ECON-0001
---
# **Market Microstructure v1**

Pricing and trade mechanics for water, credits, goods, services, and tokens across civic and black‑market venues.  
Integrates with **Economy v1**, **Barrel Cascade Planner v1**, **Agent Action API v1**, **Task Selection & Utility v1**, **Law & Contract Systems v1**, and the **Tick Loop**.

> Cadence: **quotes update per MinuteTick**, **indices per DayTick**.  
> Venues: **Civic Kiosks (posted price)**, **Bazaars (bargaining OTC)**, **Exchanges (orderbook)**, **Black‑Nodes (tokenized escrow)**.

---

## 0) Goals

1. **Coherent Prices** — reflect scarcity, risk, and legitimacy.  
2. **Multiple Venues** — simple posted prices, richer bargaining, optional order books.  
3. **Risk‑Aware** — spreads widen with route risk, reliability, and lawfulness.  
4. **Auditable** — civic venues are public; black‑nodes are restricted but internally consistent.  
5. **Playable** — low overhead defaults; deep knobs for tuning.

---

## 1) Tradables & Units

- **Water**: liters (L).  
- **Credits**: per‑issuer `credit:<lord_id>` redeemable at issuer’s reservoir (floating FX).  
- **Goods/Materials**: itemized SKUs with quality tags.  
- **Services**: labor minutes with skill tier.  
- **Tokens**: escrow receipts for black‑market contracts/payments.

---

## 2) Venues

### 2.1 Civic Kiosk (Posted Price)
- **Mechanism**: price is posted by operator (guild or civic). Buyers pay posted ask; sellers receive posted bid.  
- **Spread**: `spread = base + risk_premium + inventory_pressure`.  
- **Events**: `PricePosted`, `TradeExecuted(PUBLIC)`.

### 2.2 Bazaar (Bargaining OTC)
- **Mechanism**: bilateral bargaining with deadline; price discovered via alternating offers.  
- **Outcome**: success if `reservation_price_buyer ≥ reservation_price_seller`.  
- **Events**: `NegotiationOpened`, `TradeExecuted(PUBLIC)`; failures log `NegotiationFailed` (LOW).

### 2.3 Exchange (Orderbook, optional for key wards)
- **Mechanism**: continuous double auction for liquid pairs (e.g., `water ↔ king‑credit`, `king‑credit ↔ dukeX‑credit`).  
- **Matching**: price‑time priority; minimum lot sizes.  
- **Events**: `OrderPlaced`, `TradeExecuted`, `OrderCancelled`, `TakerFeeApplied`.

### 2.4 Black‑Node (Tokenized Escrow)
- **Mechanism**: anonymous tokens; price = ask of issuer ± escrow fee ± risk premium.  
- **Settlement**: `TokenEscrowSettle` upon proof; failed jobs pay out to issuer per terms.  
- **Events**: `TokenMinted(RESTRICTED)`, `TokenEscrowSettled(RESTRICTED)`; leaks convert to PUBLIC rumors if detected.

---

## 3) Price Formation

### 3.1 Baseline Reference

Daily **reference water price** per ward `P_ref_w` (credits/L) updates on **DayTick**:

```
P_ref_w = P_ref_w_prev * exp( β_demand * ΔNeed_w  + β_supply * ΔReserve_w
                              + β_legit * ΔGovLegit_w + β_risk * ΔRisk_w
                              + β_tax   * ΔTaxRate   + β_shock * Shock_w )
```
- `Need_w` increases price; `Reserve_w` decreases.  
- `GovLegit_w` lowers perceived market risk; `Risk_w` (env/security) raises it.  
- Royal tax changes pass‑through to posted prices.

### 3.2 Minute Quotes

At **MinuteTick**, each venue quotes:

```
mid = α_ref * P_ref_w + (1-α_ref) * last_trade
spread = base + κ_inv * inv_skew + κ_risk * (ρ_env + ρ_sec) + κ_leg * (1 - GovLegit_w) + κ_liq * 1/liquidity
bid = mid - spread/2
ask = mid + spread/2
```
- `inv_skew`: (inventory − target)/target; positive when long inventory → lowers ask, raises bid.  
- `liquidity`: rolling traded volume; low liquidity → wider spreads.

### 3.3 Issuer Credit FX

Price of `credit:<lord>` in **king‑credits**:

```
FX_lord = base_par * exp( γ_rel * (Reliab_lord - 0.5) + γ_leg * (GovLegit_ward - 0.5) - γ_risk * Risk_ward )
```
- Lower reliability/legitimacy → discount; crises can break pegs.

### 3.4 Route Risk Surcharge (for delivered water/goods)

For trades requiring transport `route`:

```
surcharge = η_route * (AmbushProb(route) + SmuggleRisk_avg) + η_seal * (1 - SealQuality_dest)
delivered_price = price * (1 + surcharge)
```

---

## 4) Bazaar Bargaining Model (OTC)

- Buyer and seller generate **reservation prices** `R_b, R_s` from drives, stocks, and reference prices.  
- Alternate offers for `N` rounds or until `offer_b ≥ offer_s`.  
- Concession rule: `offer ← offer ± λ_concede * (reservation − current)` with noise tied to charisma & dominance drives.  
- If deadline expires: failure; parties may retry or escalate to exchange/kiosk.

**Pseudo**

```python
def bargain(R_b, R_s, rounds=5):
    b, s = R_b * 0.9, R_s * 1.1
    for k in range(rounds):
        b += λb * (R_b - b)
        s -= λs * (s - R_s)
        if b >= s: return (b + s) / 2, "SUCCESS"
    return None, "FAIL"
```

---

## 5) Orderbook (Optional)

Maintain per‑ward books for chosen pairs:

- **Ladder** with price levels, cumulative size.  
- **Taker/ Maker fees**; higher fees in outer wards or black‑nodes.  
- **Impact**: large orders slippage proportional to inverse depth.  
- **Arbitrage**: agents can exploit cross‑ward FX or water price differentials net of route surcharge.

---

## 6) Tokenized Escrow Pricing (Black‑Node)

Token `τ` paying on completion of job `J`:

```
Price(τ) = BasePay(J) * (1 + φ_risk * RouteRisk + φ_illicit * Illicitness + φ_deadline * Urgency) + Fee_escrow
Spread_token = ψ_liq / Liquidity(τ) + ψ_reliab * (1 - Reliability(issuer))
```

- Issuers with poor reliability must pay higher premia; urgent and illicit jobs pay more.  
- Settlement: upon `TokenEscrowSettled`, tokens burn; otherwise refund per terms.

---

## 7) Taxes, Fees, and Skims

- **Royal Tax** on official water transfers: fraction of volume to king (credits minted to local issuer).  
- **Venue Fees**: kiosk margin, exchange maker/taker, bazaar stall rent.  
- **Checkpoint Bribes**: modeled as **route cost** (feeds surcharge).  
- **Audit Fees**: if trade flagged, audit fee applied; repeated flags worsen spreads via `κ_risk`.

---

## 8) Events & Logging

- `PricePosted {ward, item, bid, ask, mid, spread}` (PUBLIC for civic).  
- `TradeExecuted {venue, item, qty, price, parties?, visibility}`.  
- `CreditRateUpdated {issuer, FX}` (daily + intraday on jumps).  
- `ArbitrageDetected` (optional diagnostics).  
- Black‑node uses `RESTRICTED` visibility unless detected.

---

## 9) Integration with Drives/Actions

- **Trade/Buy/Sell** query quotes; expected value includes route surcharge.  
- **Escort/Smuggle** profitability driven by `delivered_price − source_price − costs`.  
- **Hoard vs Inflation**: hoarding flags reduce liquidity → widen spreads and lift mid.  
- **Legitimacy Feedback**: PUBLIC price stability and narrow spreads improve perceived legitimacy.

---

## 10) Policy Knobs

```yaml
market:
  α_ref: 0.7
  base_spread: 0.04
  κ_inv: 0.08
  κ_risk: 0.10
  κ_leg: 0.06
  κ_liq: 0.12
  β_demand: 0.20
  β_supply: -0.18
  β_legit: -0.10
  β_risk: 0.12
  β_tax: 0.05
  γ_rel: 0.50
  γ_leg: 0.35
  γ_risk: 0.40
  η_route: 0.50
  η_seal: 0.20
  λb: 0.4
  λs: 0.35
  fee_maker: 0.003
  fee_taker: 0.007
  φ_risk: 0.6
  φ_illicit: 0.4
  φ_deadline: 0.3
  ψ_liq: 0.2
  ψ_reliab: 0.3
```

---

## 11) Sanity & Anti‑Gaming

- **Conservation**: sum of executed trades matches ledger deltas.  
- **No Negative Spreads**: enforce `ask ≥ bid`.  
- **Circuit Breakers**: if minute price change > `x%`, throttle quotes; escalate to Arbiter alerts.  
- **Spoofing Guard** (orderbook): minimum display time or penalties for cancel spam.  
- **Wash Trade Detect**: repeated self‑trades at same venue → flag and widen spreads.

---

## 12) Pseudocode — Minute Quote Update

```python
def minute_quote_update(ward, item, venue):
    mid = α_ref * P_ref_w[ward,item] + (1-α_ref) * last_trade[ward,item]
    spread = base + κ_inv * inv_skew(ward,item)                  + κ_risk * (ρ_env(ward)+ρ_sec(ward))                  + κ_leg * (1 - GovLegit_w[ward])                  + κ_liq * (1/max(ε, liquidity(ward,item)))
    bid, ask = mid - spread/2, mid + spread/2
    emit("PricePosted", {...})
    return bid, ask
```

---

### End of Market Microstructure v1
