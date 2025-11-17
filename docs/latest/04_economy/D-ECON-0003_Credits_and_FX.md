---
title: Credits_and_FX
doc_id: D-ECON-0003
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
depends_on:
  - D-ECON-0001   # Ward_Resource_and_Water_Economy
  - D-ECON-0002   # Dosadi_Market_Microstructure
  - D-WORLD-0003  # Ward_Branch_Hierarchies
  - D-INFO-0001   # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003   # Information_Flows_and_Report_Credibility
  - D-INFO-0004   # Scholars_and_Clerks_Branch
  - D-SOC-0003    # Logistics_Corridors_and_Safehouses (placeholder)
---

# Credits & FX

> This document defines **money on Dosadi**:
> - What the recognized currencies and quasi-currencies are.
> - How they relate to the underlying **water economy**.
> - How exchange rates (FX) are set, quoted, and shocked.
> - How agents and institutions hold, convert, and weaponize value.

It provides the reference layer that:

- `D-ECON-0002_Dosadi_Market_Microstructure` uses as `P_ref_w[ward,item]`.
- Future docs (labor markets, ledgers, taxation) use to denominate prices,
  wages, and balances.

---

## 1. Purpose & Scope

On Dosadi, **water is the master resource**, but:

- It is cumbersome to move and store in large quantities at the individual level.
- Political actors want a way to **delay obligation**, **pool risk**, and **express power**.

Credits & FX define:

- A hierarchy of **currencies and instruments** (king credits, ward scrip, chits, in-kind).
- How each is backed (or not) by **water allocations and quotas**.
- How exchange works:
  - Official parities vs actual market rates.
  - Who can convert what, where, and under what constraints.

This document focuses on:

- The **minimal set** of currencies needed for the simulation.
- How FX rates are **modeled and updated** at the ward level.
- How **agents’ wallets** and **branch budgets** can hold multi-currency balances.

Macro credit theory, long-term debt cycles, and detailed bookkeeping are out of
scope here and will be handled by future **Ledgers & Taxation** docs.

---

## 2. Monetary Instruments

We distinguish four main categories:

1. **Crown Currency (King Credits)**
2. **Ward Scrip & Local Credits**
3. **Service & Ration Chits**
4. **In-Kind Water & Goods**

### 2.1 Crown Currency (King Credits, `KCR`)

- Issued by:
  - The king and central treasury.
- Backing:
  - **Implicit claim on the planetary water system**, enforced via:
    - Control of well output, cascade allocations, and military capacity.
- Uses:
  - High-level trade between:
    - King ↔ Dukes ↔ major ward lords.
    - Large guild conglomerates that span wards.
  - Payment for:
    - Strategic services (espionage, assassinations, special projects).
- Properties:
  - Highest **prestige** and **legal protection**.
  - Most widely acceptable across wards, but:
    - Not all wards see KCR in daily circulation.
  - FX anchor:
    - Many other instruments are defined **relative to KCR** on paper,
      even if practice deviates.

### 2.2 Ward Scrip & Local Credits (`WCR`)

Each ward may issue its own **Ward Credits**:

- Issuer:
  - The ward lord / treasury or a tightly controlled banking guild.
- Backing:
  - Owed slices of:
    - Ward water quota (`W_quota` from D-ECON-0001),
    - Ward production capacity (food, repair, suits), in theory.
- Uses:
  - Everyday trade inside the ward:
    - Wages for common labor.
    - Payment at most local markets and facilities.
- Properties:
  - Accepted *primarily within the issuing ward* and immediate neighbors.
  - Susceptible to:
    - Devaluation via over-issuance.
    - Loss of confidence if water quotas are cut.
- FX:
  - `KCR/WCR[ward]` floating or quasi-managed at FX venues.
  - Cross-ward trades often go:
    - `WCR_A → KCR → WCR_B` for settlement.

### 2.3 Service & Ration Chits

Represent **pre-authorized claims** on specific services:

- Examples:
  - Ration chit (one meal at a specified or generic civic kitchen).
  - Bunk chit (one sleep-cycle at a bunkhouse tier).
  - Clinic chit (triage-level treatment).
  - Work token (required license to perform certain tasks).
- Issuer:
  - Typically the **Civic branch** or contracted operators.
- Backing:
  - The issuing facility’s water and food allocations plus branch guarantees.
- Properties:
  - Often non-transferable or restricted in trade.
  - Can be:
    - Bought and sold at a discount or premium, especially near expiry or in crisis.
  - Useful in simulation as:
    - Discrete, trackable promises connecting econ to facility capacity.

### 2.4 In-Kind Water & Goods

Sometimes **water itself is the currency**:

- Sealed canisters, small barrels, or water strips:
  - Used in off-ledger deals, remote wards, and black-market exchanges.
- In-kind trade:
  - `water ↔ labor`, `water ↔ suits`, `water ↔ medical services`.

In the sim:

- In-kind water functions as:
  - A **universal numeraire** with:
    - Local price distortions.
    - Storage and transport costs.
- Markets:
  - Certain venues quote **directly in liters** (`price_per_unit = liters`),
    not credits.

---

## 3. Currency Hierarchy & Convertibility

We assume a **partial hierarchy**:

```text
KCR (crown)  >  WCR[ward] (local)  >  chits / in-kind (contextual)
```

But real convertibility is messy.

### 3.1 Official Parities (On Paper)

The crown and some ward treasuries publish **official parities**:

- `P_official(KCR ↔ water)`:
  - “1 KCR is notionally worth X liters of water over a long horizon.”
- `P_official(WCR[ward] ↔ KCR)`:
  - “1 WCR in Ward-21 is worth Y KCR.”

These are:

- Used in:
  - Tax calculations, budget planning, and some internal ledgers.
- Often **fictional** in crisis:
  - Actual market rates diverge, sometimes dramatically.

### 3.2 Market Rates (FX)

Actual exchange happens at **FX venues**:

- `KCR ↔ WCR[ward]`  
- `WCR[ward_A] ↔ WCR[ward_B]` (often via KCR as an intermediate)  
- `KCR ↔ water_L`, `WCR[ward] ↔ water_L`

Market FX rate per pair `(A,B)`:

```text
FX_market[A,B] = price(B in units of A) at last meaningful trade
```

Rates are:

- Subject to:
  - Liquidity, risk, ward legitimacy, water quota changes, and rumors.
- Updated using:
  - Similar mid/spread logic as `D-ECON-0002`, but focusing on currency pairs.

### 3.3 Capital Controls & Conversion Frictions

Wards and the crown may impose **conversion rules**:

- Limits:
  - Max daily conversion from WCR to KCR for commoners.
- Tiers:
  - Different caps for nobles, guild masters, and commoners.
- Taxes:
  - Conversion taxes, especially on outflows from sanctioned or untrusted wards.

Simulation knobs:

- `convert_cap_resident[ward]`:
  - Max WCR → KCR per agent per cycle.
- `convert_cap_branch[ward,branch]`:
  - Higher caps for legitimized branches (Civil, Industrial, Military).
- `fx_tax_rate[ward]`:
  - Additional spread component on conversions.

---

## 4. FX Venues & Quoting

FX trading uses the same conceptual machinery as Market Microstructure, but with:

- **Pairs** instead of generic items.
- Stronger **policy and sanction** overlays.

### 4.1 Venue Types for FX

- **Royal Desk (GLOBAL_FX)**:
  - Primary KCR ↔ water benchmark.
  - Can be used by:
    - Dukes, major lords, certain guilds with privileges.
- **Ward FX Kiosk**:
  - KCR ↔ WCR[ward] and WCR[ward] ↔ water_L.
  - More constrained books, subject to ward policy and reserve levels.
- **Inter-Ward Bourse**:
  - WCR[ward_A] ↔ WCR[ward_B] trades for traders with cross-ward routes.
- **Black FX Node**:
  - Illicit conversions circumventing controls and taxes.

### 4.2 FX Mid & Spread Model (Sketch)

For an FX pair `(A,B)` in ward `w`:

```text
mid_FX[A,B] = α_parity * P_official[A,B] + (1 - α_parity) * last_trade_FX[A,B]
```

Spread includes:

```text
spread_FX = base_spread_FX
          + κ_liq_FX * (1 / max(ε, liquidity_FX[A,B]))
          + κ_leg_FX * (1 - GovLegit_w[ward])
          + κ_pol_FX * sanctions_risk(A,B,ward)
          + κ_res_FX * reserve_stress(A,B,ward)
```

Where:

- `sanctions_risk`:
  - Higher if either currency issuer is under punishment.
- `reserve_stress`:
  - Higher when FX reserves held by the venue/ward are low.

FX venues emit:

- `FXQuotePosted`, `FXTradeExecuted` events analogous to normal `QuotePosted`
  and `TradeExecuted`.

---

## 5. Indices, Reference Prices & Water Parity

Market Microstructure relies on `P_ref_w[ward,item]` as a **reference price**.

### 5.1 Water Parity as Global Numeraire

We define a **notional** global water parity:

```text
P_water_baseline = 1.0  # 1 "unit" of value = 1 liter of water at crown parity
```

Then for each ward:

```text
P_water_w[ward] = P_water_baseline * water_factor(ward)
```

Where:

- `water_factor(ward)` reflects:
  - Ward’s structural water position:
    - Quota size, quota stability, recycling tech, political favor.
  - Sanctions or subsidies from crown.

### 5.2 Local Reference Prices

For item `i` in ward `w`:

```text
P_ref_w[ward,i] = cost_in_water[i] * P_water_w[ward] * markup_factors(ward,i)
```

- `cost_in_water[i]`:
  - Approx liters needed to:
    - Produce, transport, and maintain item `i`.
- `markup_factors(ward,i)`:
  - Branch profit targets, scarcity modifiers, risk premiums.

These reference values:

- Provide an **anchor** for:
  - Initial market mid-prices.
  - Wages, chits pricing, and contract baselines.

---

## 6. Shocks, Sanctions & Policy Tools

Credits & FX are prime tools of **control and punishment**.

### 6.1 Types of Shocks

- **Quota Shock**:
  - Crown cuts or boosts `W_quota[ward]` (D-ECON-0001).
  - Implication:
    - Ward water scarcity changes → WCR confidence shifts → FX rates move.
- **Sanction / Blacklisting**:
  - Crown or coalition:
    - Declares a ward or faction partially non-convertible.
  - Effects:
    - Higher `sanctions_risk`, wider FX spreads, lower liquidity.
- **Devaluation**:
  - Ward treasury:
  - Officially changes WCR ↔ KCR parity.
  - Often merely acknowledges already reflected market reality.

### 6.2 Policy Levers

For simulation, we define:

- `policy_fx_floor[ward]`:
  - Minimum official KCR value of WCR; enforced via:
    - Ward interventions at FX kiosk, if reserves allow.
- `policy_fx_ceiling[ward]`:
  - Maximum KCR value of WCR (in some defensive scenarios).
- `reserve_buffer_target[ward]`:
  - Desired KCR and water reserves held by ward treasury.

Crown and ward actors can:

- Intervene by:
  - Buying/selling WCR at the royal desk or inter-ward bourses.
  - Imposing direct bans on certain pairs or maximum ticket sizes.

---

## 7. Agents, Wallets & Branch Budgets

### 7.1 Wallet Structure

Each agent may hold:

```json
{
  "wallet": {
    "KCR":  3.5,
    "WCR_W21": 120.0,
    "chits": {
      "kitchen_W21_01:LOW": 4,
      "bunk_W21_02:STD": 2
    },
    "water_L_personal": 7.0
  }
}
```

Not all agents have all instruments:

- Elites:
  - More KCR, cross-ward scrip, and high-tier chits.
- Commoners:
  - Mainly local WCR, some chits, and tiny water amounts.
- Black-market actors:
  - Significant `water_L_personal`, contraband chits, and access to BLACK_NODE FX.

### 7.2 Branch & Facility Budgets

Branches and facilities maintain:

- **Operational budgets** in:
  - WCR (for wages, local purchases).
  - KCR (for critical imports, bribes, and strategic deals).
- **Water quotas** from D-ECON-0001.

Simulation-wise:

- Budgets influence:
  - Ability to pay wages (labor availability).
  - Ability to transact at legitimate vs illicit venues.
  - Vulnerability to FX shocks (e.g., heavy WCR exposure in a collapsing ward).

---

## 8. Simulation Hooks

### 8.1 Currency & FX Data Structures

Core entities:

- `Currency`:
  - `{ code: "KCR" | "WCR_W21" | "WCR_W07" | ... , issuer, type }`
- `FXRate`:
  - `{ base: Currency, quote: Currency, ward_context, mid, spread }`
- `FXVenue`:
  - As per D-ECON-0002 but restricted to currency pairs.

### 8.2 Update Loop Sketch

Per cycle:

1. **Update Water Context**
   - From D-ECON-0001: new `W_quota`, `W_storage`, and `water_factor(ward)`.

2. **Recompute Reference Water Prices**
   - Update `P_water_w[ward]`.

3. **Update Official Parities (Optional)**
   - Crown/wards may adjust paper `P_official(A,B)`.

4. **FX Quote Step**
   - For each FX pair at each venue, compute:
     - `mid_FX[A,B]` and `spread_FX` using liquidity, legitimacy, sanctions, reserves.

5. **Execute FX Orders**
   - Agents, branches, wards place orders subject to:
     - Caps, taxes, and policy flags.

6. **Emit Events**
   - `FXQuotePosted`, `FXTradeExecuted`, `FXShockDetected` etc.

7. **Telemetry & Audits**
   - Selected FX venues feed into:
     - Telemetry streams and audit processes (D-INFO-0001).

---

## 9. Open Design Questions

For future ADRs:

- How many **distinct WCR variants** do we want in early prototypes?
  - One per ward vs clusters of similar wards.
- Should **some wards operate mostly cashless**, with chits + in-kind water?
- How aggressively should crown **weaponize FX**?
  - Ward sanctions, blacklists, targeted devaluations.
- How much **agent-level FX behavior** do we model?
  - Simple “hold whatever you’re paid in” vs active currency hoarding/arbitrage.

These can be tuned once we see how much detail the simulation and UX can support
without becoming opaque.
