---
title: Dosadi_Market_Microstructure
doc_id: D-ECON-0002
version: 1.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
parent: D-ECON-0001   # Ward_Resource_and_Water_Economy
---

# Market Microstructure v1.1 (Venues, Quotes, Spreads, and Flow)

> Define how prices *actually form* on Dosadi: who posts quotes, how spreads
> depend on inventory, risk, legitimacy, liquidity, and taxes, and how trades
> reconcile back into ledgers and FX.

This document upgrades the earlier Market Microstructure v1 to integrate with:

- D-ECON-0001_Ward_Resource_and_Water_Economy
- D-ECON-0003_Credits_and_FX 
- D-ECON-0004_Black_Market_Networks
- D-ECON-0005_Food_and_Rations_Flow (planned/placeholder)
- D-ECON-0006_Maintenance_Fault_Loop (planned/placeholder)
- D-ECON-0007_Work_Rest_Scheduling
- D-ECON-0008_Production_and_Fabrication (planned/placeholder)
- D-ECON-0009_Financial_Ledgers_and_Taxation (planned/placeholder)
- D-ECON-0010_Work_and_Labor_Markets
- D-INFO-0001_Telemetry_and_Audit_Infrastructure
- D-INFO-0002_Espionage_Branch
- D-INFO-0003_Information_Flows_and_Report_Credibility
- D-INFO-0004_Scholars_and_Clerks_Branch

Timebase notes:

- Market quotes: **per minute**
- Order book clear: **per 5 minutes**
- Venue KPIs: **hourly**
- Policy operations: **on demand**

---

## 0. Scope and Position in the Stack

Market Microstructure sits between:

- **Economic primitives**
  - Water and ward budgets, rations, labor, maintenance tasks.
- **Agent behavior**
  - Agents decide *what* to buy/sell/hire; this doc decides *at what price* and *with what friction*.
- **Accounting & audits**
  - Every trade generates journal entries (water-basis & credit-basis) and checkpoints for telemetry.

We model:

1. **Venues & Order Types**  
   Kiosks, bourses, auctions, black-nodes, royal desks.
2. **Quote Formation & Spreads**  
   Mid from reference price and last trade; spread from inventory, risk, legitimacy, liquidity, and tax.
3. **Matching & Execution**  
   Continuous double auction where possible; simplified kiosk/bazaar logic elsewhere.
4. **Risk, Legitimacy & Regulation**  
   How environment/security risk and governance legitimacy push spreads.
5. **Emissions & Dashboards**  
   Events and KPIs that other systems and players can watch.

---

## 1. Entities & State

### 1.1 Items & Units

- **Items**: `water_L`, `ration:LOW|MID|HIGH|ELITE`, `spare_part_SKU`, `suit_SKU`,
  `labor_hour`, `escort_slot`, `clinic_slot`, `vault_space`, etc.
- **Quote Unit**: price in local **credits per unit** or **liters per unit**
  (for water-basis quoting).
- **Ward Context**: per ward `w`, each item has:
  - `P_ref_w[ward,item]` — reference/fair value (from credits / indices).
  - `GovLegit_w[ward]` — governance legitimacy score.
  - `ρ_env(ward)` — environmental risk.
  - `ρ_sec(ward)` — security risk.

### 1.2 Venues

Each **Venue**:

```json
{
  "venue_id": "W21_BAZ_01",
  "ward": "W21",
  "kind": "KIOSK|BAZAAR|FX_VENUE|AUCTION|ROYAL_DESK|BLACK_NODE",
  "legitimacy": "ROYAL|LORD|GUILD|CIVIC|ILLICIT",
  "inventory_profile": { "water_L": 12000, "ration:LOW": 4400 },
  "order_book": { "water_L": {}, "ration:LOW": {} },
  "fees": { "maker": 0.003, "taker": 0.007 },
  "telemetry_stream": "venue_W21_BAZ_01"
}
```

Human read:

- **KIOSK** – simple posted prices, small book; often civic kitchens / bunkhouses.
- **BAZAAR** – multi-stall order book; heterogenous quality, haggling.
- **FX_VENUE** – specialized venue for credit↔credit / credit↔water.
- **AUCTION** – batch clearance for bulk lots (barrels, maintenance POs).
- **ROYAL_DESK** – king/duke controlled; used for policy ops and backstops.
- **BLACK_NODE** – illicit; narrower books, high risk, better spreads on contraband.

### 1.3 Participants

- **Retail Agents** (citizens, small shops).
- **Guilds / Workshops** (production & maintenance).
- **Kitchens & Clinics** (civic service operators).
- **Lords / Treasury Desk** (policy ops, crisis trades).
- **Black-Market Brokers** (illicit venues, arbitrage).

---

## 2. Order Types & Flow

Supported order types:

- **LimitOrder**  
  `{side: BUY|SELL, item, qty, limit_price, ttl_min}`
- **MarketOrder**  
  `{side, item, qty, urgency}` (executes across book at best available).
- **RFQ** (Request For Quote) — for OTC / escort / maintenance jobs:
  - Agents ask a venue or guild for a one-shot quote; accepted or declined.
- **BatchAuctionLot** — for bulk barrels, rations, or reclaimed scrap.

### 2.1 Event Surface

Common events:

- `QuotePosted {ward,item,venue,bid,ask,mid,spread}`
- `OrderAccepted {order_id, venue}`
- `TradeExecuted {trade_id, buyer,seller,item,qty,price,venue,fees}`
- `OrderCancelled {order_id, reason}`
- `SpreadAdjusted {ward,item,venue,spread,drivers}`
- `CircuitBreakTriggered {ward,item,venue,reason}`

These feed:

- Agent decisions (perceived prices and spreads).
- Ledgers (double-entry journal updates).
- Telemetry & Audit (variance detection and surveillance).
- Rumor systems (sudden price shocks, outages).

---

## 3. Mid-Price & Spread Model

### 3.1 Mid-Price

Per `(ward, item)` and venue `v`:

```text
mid = α_ref * P_ref_w[ward,item] + (1 - α_ref) * last_trade[ward,item]
```

- `P_ref_w` comes from credits / FX indices.  
- `last_trade` is venue- or ward-wide most recent executed price.  
- `α_ref` controls anchoring vs. fresh trades.

### 3.2 Spread Drivers

Spread decomposes into stacked risk terms:

```text
spread = base_spread
       + κ_inv  * inv_skew(ward,item)
       + κ_risk * (ρ_env(ward) + ρ_sec(ward))
       + κ_leg  * (1 - GovLegit_w[ward])
       + κ_liq  * (1 / max(ε, liquidity(ward,item)))
       + κ_tax  * tax_drag(ward,item)
```

- **Inventory skew**: how off-balance inventories are.
- **Risk**: dangerous routes, likely ambush, facility fragility.
- **Legitimacy**: lower trust → wider spreads.
- **Liquidity**: thin books & small float → wider spreads.
- **Tax drag**: official skim, excise, and bribe expectations.

### 3.3 Policy Knobs (Example)

```yaml
market:
  α_ref: 0.7          # weight of reference vs last trade
  base_spread: 0.04   # baseline % spread

  κ_inv: 0.08         # inventory skew → spread sensitivity
  κ_risk: 0.10        # env + security risk
  κ_leg: 0.06         # illegitimacy penalty
  κ_liq: 0.12         # thin liquidity penalty
  κ_tax: 0.05         # tax/skim drag on spreads

  β_demand: 0.20      # demand shock → mid up
  β_supply: -0.18     # supply shock → mid down
  β_legit: -0.10      # legitimacy ↑ → mid down
  β_risk: 0.12        # risk ↑ → mid up
  β_tax: 0.05         # tax ↑ → mid up

  γ_rel: 0.50         # reliability weight in venue trust
  γ_leg: 0.35         # legitimacy weight
  γ_risk: 0.40        # risk weight

  η_route: 0.50       # route surcharge multiplier
  η_seal: 0.20        # suit quality / escort protection discount

  fee_maker: 0.003    # maker fee
  fee_taker: 0.007    # taker fee

  φ_risk: 0.6         # how much micro-risk feeds rumor
  φ_illicit: 0.4      # black-market rumor amplification
  φ_deadline: 0.3     # deadline pressure → price volatility
  ψ_liq: 0.2          # liquidity → rumor
  ψ_reliab: 0.3       # reliability → rumor
```

---

## 4. Venue Matching Logic

### 4.1 Order Book (Continuous Double Auction)

Per `(venue, item)` maintain:

```json
{
  "bids": [ { "price": 9.4, "qty": 200, "agent": "A1", "ts": 12001 } ],
  "asks": [ { "price": 9.8, "qty": 150, "agent": "A7", "ts": 12003 } ]
}
```

Matching:

1. Insert new order at its price level.
2. Cross against opposite side:
   - Price priority (best first) then time priority.
3. Execute at resting order price (or midpoint, policy-tunable).
4. Emit `TradeExecuted` + ledger entries.

Partial fills allowed; remainders remain in book or expire at `ttl_min`.

### 4.2 Simplified Venues

- **KIOSK** – No full book; just posted `bid/ask` with bounded size.
- **BAZAAR** – Reduced order book; more noise in `liquidity()` estimates.
- **BLACK_NODE** – May appear to ignore some conservation constraints in fiction,
  but the underlying simulation still conserves stock.

---

## 5. Route Surcharges & Frictions

Trades involving **transport** (barrels, ration trucks, exo-suit convoys) incorporate route friction:

```text
delivered_price = venue_price
                + route_cost(ward_src, ward_dst)
                + risk_premium(route)
                + stealth_premium(if_illicit)
```

- **Route cost** uses:
  - Distance & elevation.
  - Escort wages (from labor market docs).
  - Fuel and maintenance (maintenance loop).
- **Risk premium**:
  - Higher `ρ_sec` → higher route risk premium.
  - Insurance contracts can offset shocks but add base cost.
- **Stealth premium**:
  - Illicit routes pay extra for silence and plausible deniability.

---

## 6. Legitimacy, Regulation & Enforcement

Markets are not neutral:

- **Legitimized venues**:
  - Must report trades to Financial Ledgers & Taxation.
  - Subject to telemetry-based audits.
  - Can be fined, sanctioned, or shut down.
- **Illicit venues (BLACK_NODE)**:
  - Better prices on some goods; poorer recourse.
  - Higher chance of raids; spreads include bust risk.

Enforcement hooks:

- `VarianceAlert` from telemetry/audit (missing liters, suspicious flows).
- `MarketAbuseFlag` for spoofing / wash trades / cornering.
- `VenueSanctioned` or `VenueClosed` events that collapse liquidity and push demand into neighboring wards or black-nodes.

---

## 7. Integration with Credits, FX, Ledgers, and Tasks

### 7.1 Credits & FX

- Market mid-prices consume FX / reference prices as `P_ref_w`.
- FX venues use similar microstructure but specialized pairs:
  - `Credit_I ↔ Credit_J`
  - `Credit_I ↔ water_L`

### 7.2 Ledgers & Taxes

Each `TradeExecuted` generates:

- Water-basis and credit-basis double-entry.
- Tax lines:
  - Skim on cascade flows (official barrel transfers).
  - Excise for regulated goods (suits, weapons, narcotics).
  - Income / profit classification for accounting.

### 7.3 Work & Labor / Maintenance / Clinics / Kitchens

- **Labor**: wages (credits + water) discovered partly through labor-market microstructure,
  anchored to local prices of rations, suits, clinic access.
- **Maintenance**: facility component prices, maintenance task bounties.
- **Kitchens / Clinics**: ration and clinic price indices feed agent decisions on risk vs. care.

---

## 8. Agents, Drives & Rumor Hooks

Agents perceive:

- `P_obs(ward,item)` – observed mid & spread.
- `VenueProfile` – reliability, legitimacy, risk, rumor polarity.

They use these to decide:

- Where to buy/sell (venue choice).
- When to hoard vs. consume.
- Which contracts to accept (escort, maintenance, smuggling).

Rumor & Perception:

- Big jumps in `mid` or `spread` emit `RumorEmitted` events:
  - “Water spreads blew out in W21”; “Black-node has cheap suit filters.”
- Repeated `VarianceAlert` / `ReserveBreach` signals push agents toward:
  - Flight to quality (king credits, inner ward venues).
  - Opportunistic arbitrage (outer ring black-nodes).

---

## 9. Sanity & Anti-Gaming Constraints

To keep the simulation stable:

- **Conservation**  
  Sum of executed trades must reconcile with stocks and ledgers.
- **No Negative Spreads**  
  Enforce `ask ≥ bid` on all venues.
- **Circuit Breakers**  
  If minute price change `> x%`, freeze new orders briefly; emit `CircuitBreakTriggered`.
- **Spoofing Guard**  
  Minimum display time or penalties for cancel spam; repeated patterns → risk score bump.
- **Wash Trade Detection**  
  Self-trades or closed loops at same venue flagged; spreads widen; rumor/legitimacy penalties.

---

## 10. Pseudocode — Minute Quote Update

```python
def minute_quote_update(ward, item, venue):
    mid_ref = P_ref_w[ward, item]          # from credits / FX / indices
    last = last_trade_price[ward, item]    # ward-level or venue-level
    mid = α_ref * mid_ref + (1 - α_ref) * last

    inv_term  = κ_inv  * inv_skew(ward, item)
    risk_term = κ_risk * (ρ_env(ward) + ρ_sec(ward))
    leg_term  = κ_leg  * (1 - GovLegit_w[ward])
    liq_term  = κ_liq  * (1 / max(ε, liquidity(ward, item)))
    tax_term  = κ_tax  * tax_drag(ward, item)

    spread = base_spread + inv_term + risk_term + leg_term + liq_term + tax_term
    spread = max(spread_min, spread)

    bid, ask = mid - spread / 2.0, mid + spread / 2.0

    emit("QuotePosted", {
        "ward": ward,
        "item": item,
        "venue": venue.id,
        "mid": mid,
        "bid": bid,
        "ask": ask,
        "spread": spread,
        "drivers": {
            "inv": inv_term, "risk": risk_term,
            "leg": leg_term, "liq": liq_term,
            "tax": tax_term
        }
    })
    return bid, ask
```

---

## 11. Dashboards & Explainability

Per ward & venue, maintain:

- **Price Board**  
  Mid, bid/ask, spread, volume, volatility.
- **Venue Health**  
  Liquidity, order depth, cancellation rate, spoof flags.
- **Legitimacy & Risk**  
  Governance legitimacy, venue reliability, venue risk score.
- **Tax & Skim View**  
  Water taxed vs. traded, route surcharges, skim flows.
- **Equity View**  
  Average meal/suit prices vs. caste/ward; identify wards in pre-crisis spread regimes.

This is where players and tools “see” the economy’s pulse.

---

## 12. Test Checklist

1. **Spread Monotonicity**
   - Higher `ρ_env` or `ρ_sec` → higher spreads, all else equal.
   - Lower `GovLegit` → higher spreads and worse rumor polarity.
2. **Liquidity Effects**
   - Remove major venue: spreads widen; volume shifts to neighbors / black-nodes.
3. **Cascade & FX Shocks**
   - Supply/FX shocks propagate to mid-prices; wages adjust via labor markets.
4. **Audit & Enforcement**
   - Artificial wash trading / spoofing raises flags and adjusts risk/legitimacy as expected.
5. **Conservation**
   - Total water and credits remain conserved modulo explicitly modeled leaks, theft, and reclamation.
