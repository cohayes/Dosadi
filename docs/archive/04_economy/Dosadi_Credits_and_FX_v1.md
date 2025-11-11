ARCHIVED -- Superseded by Version 1.1 in /docs/latest
# **Credits & FX v1 (Ward Money, Redemption, and Exchange)**

**Purpose:** Define how ward-issued credits are minted, redeemed for water, exchanged across issuers, taxed, manipulated, and audited—so markets, contracts, labor, and the barrel cascade all have a solid monetary backbone.

Integrates with **Market v1**, **Barrel Cascade v1**, **Labor v1**, **Law & Contract Systems v1**, **Rumor & Perception v1**, **Security Loop v1**, **Maintenance v1**, and the **Tick Loop**.

> Cadence: FX references and redemption windows update **per Day**; quotes and trades update **per Minute**.

---

## 0) Entities & Instruments

- **Issuer:** `king` or any **lord/duke** with a reservoir. Each issuer has:

  - `reserve_water_L` (audited), `issuance_cap`, `policy{tax, mint, redeem, peg}`.

- **Credit:** `credit:<issuer>` — bearer claim on issuer’s reservoir at posted **redemption rate**:

  - `RedeemRate_i` (L per credit), set by issuer’s treasurer; can move daily.

  - Form: electronic token (default), or physical chit (rare; used for black‑market obfuscation).

- **Water:** base commodity unit (`L`) used for redemption and some payments.

- **FX Pair:** `credit:<A> / credit:<B>` quoted as mid, with bid/ask, in both venues (CIVIC/GUILD/MERC) and BLACK‑NODES.

---

## 1) Issuance & Redemption

### 1.1 Minting

- Issuer mints `ΔC` credits when:

  - Paying staff/contracts, subsidizing civic programs, funding security.

  - **Constraint:** `Minted_i ≤ issuance_cap_i` and **Reserve Coverage** ≥ `θ_cover`:

    - `Coverage_i = reserve_water_L / (OutstandingCredits_i * RedeemRate_i)`

- Event: `CreditsMinted{issuer, amount, purpose}`

### 1.2 Redemption

- Bearer exchanges `C` credits for `C * RedeemRate_i * (1 − fee_i)` liters.

- Redemption throttles by **window** (daily liters) and **queue** (first‑come).

- Failure modes:

  - **Delay:** queue grows → FX discount widens.

  - **Haircut:** temporary reduction in `RedeemRate_i` triggers legitimacy hit.

- Event: `CreditsRedeemed{issuer, credits, liters, wait_min}`

### 1.3 Royal Tax & Seigniorage

- On **official** water transfers (barrel cascade, civic wholesale): issuer pays `RoyalTax` in **king‑credits** (5–15% equivalent of water value).

- King can **recycle** these into ward operations (informants, audits, discrete buys).

- Event: `RoyalTaxAssessed{from_issuer, liters_equiv}`

---

## 2) Price Formation & FX

### 2.1 Reference & Parity

- Daily **Ref Price** for water in ward `w`: `P_ref_w` (credits of local issuer per liter).

- **Theoretical Parity** for FX (`A/B`) from redemption:

  - `PX_theory = (RedeemRate_B / RedeemRate_A) * (Adj_reserve_risk)`

- Deviations drive **arbitrage**; spreads widen with:

  - Lower legitimacy, audit gaps, transport risk, hoarding pressure.

### 2.2 Venues

- **CIVIC/GUILD/MERC:** posted quotes; narrower spreads; KYC’d.

- **BLACK‑NODE:** token‑escrow, anonymity, wider spreads, higher fees.

### 2.3 Microstructure Signals

- **Order Imbalance** → transient moves.

- **Rumor Shocks** (facility outage, scandal, epidemic) → risk premia bump.

- **Policy Change** (RedeemRate, haircuts) → discrete jumps; Arbiter advisories mitigate chaos.

Events: `CreditRateUpdated{issuer, FX_vs_king}`, `PricePosted{pair, venue, bid, ask, spread}`

---

## 3) Hoarding, Inflation, and Controls

### 3.1 Hoarding (Trust Collapse via Scarcity Psychology)

- Trigger conditions:

  - Rising queue times for redemption, rising **route risk**, visible shortages.

- Effects:

  - Labor participation ↓, posted wages ↑, spot liquidity in credits ↓, **water premium** ↑.

- Countermeasures:

  - **Targeted Liquidity** (king spot‑redeems king‑credits in the ward).

  - **Emergency Rations/Water Windows** for critical industries.

  - **Transparency Burst** (audits & proof‑of‑reserves events).

Event: `HoardingAlert{ward, intensity}`

### 3.2 Inflation (Token Over‑Issuance)

- Trigger conditions:

  - Coverage ratio drops toward threshold, issuer mints to fund shortfalls/loyalty.

- Effects:

  - Local prices in `credit:<issuer>` ↑, FX discount vs king widens, wage demands ↑.

- Countermeasures:

  - **Mint Freeze**, **RedeemRate Glidepath** (predictable adjustments), **Royal Swap Line** (king lends water against strict terms), enforced austerity.

Event: `InflationAlert{issuer, CPI_like, coverage}`

---

## 4) Audits, Proof‑of‑Reserves, and Penalties

- **Clerks/Auditors Guild** runs periodic and surprise audits:

  - Publish `ReserveAttested{issuer, reserve_water_L, coverage, confidence}`.

  - Failure → **Sanctions** (FX cap, forced reductions in mint window).

- **Reclaimers** double as a water‑bank backstop (escrowed reserves, taxed by king and local lord).

- **Penalty Ladder**:

  1) Warning & transparency mandate.

  2) Mint freeze; stricter redeem windows.

  3) Technocratic oversight (royal comptroller installs).

  4) **Receivership** (replace issuer’s treasurer / lord).

Events: `AuditStarted/Completed`, `IssuerSanctioned`, `ReceivershipInvoked`

---

## 5) Arbitrage & Routing

- **Triangular FX** (A↔B↔king) allowed with transport & audit risk.

- **Water‑Credit Arbitrage**:

  1) Redeem `credit:A` → water @ `W_A`.

  2) Ship to `W_B` (pay risk/route surcharge).

  3) Sell water for `credit:B` above parity if spreads justify.

- **Credit‑for‑Goods** swaps: some guilds quote in multiple issuers to reduce FX cost.

Event: `ArbTradeExecuted{path, pnl_est, risk}`

---

## 6) Policy Knobs

```yaml
money:
  coverage_min: 0.85        # issuers below → sanctions
  redeem_fee: 0.01          # default redemption fee
  redeem_window_L_per_day:  # issuer-specific throttles
    king: 200000
    default_lord: 20000
  royal_tax_pct: 0.10
  fx_spread_base: 0.04
  fx_spread_legit_coeff: 0.10
  hoarding_trigger:
    wait_min: 90
    spread_widen: 0.05
  inflation_trigger:
    coverage_drop: 0.05
    cpi_jump_pct: 0.08
  audit_freq_days:
    inner: 7
    middle: 10
    outer: 14
  receivership_threshold: 0.65
```

---

## 7) Event & Function Surface (for Codex)

**Functions**

- `mint_credits(issuer, amount, purpose)` → `CreditsMinted`

- `redeem_credits(holder, issuer, credits)` → `CreditsRedeemed`

- `post_fx_quote(pair, venue)` → `PricePosted`

- `execute_fx_trade(pair, side, qty, venue)` → `TradeExecuted`

- `update_fx_reference(day)` → `CreditRateUpdated*` (vs king)

- `run_audit(issuer)` → `AuditCompleted` + `ReserveAttested`

- `apply_sanction(issuer, level)` → `IssuerSanctioned`

- `invoke_receivership(issuer)` → `ReceivershipInvoked`

- `detect_hoarding(ward)` / `detect_inflation(issuer)` → corresponding alerts

- `royal_swapline(issuer, liters, terms)` → credit line open; logs strict conditions

**Events**

- `CreditsMinted`, `CreditsRedeemed`, `CreditRateUpdated`, `PricePosted`, `TradeExecuted`,  

  `AuditStarted/Completed`, `ReserveAttested`, `IssuerSanctioned`, `ReceivershipInvoked`,  

  `HoardingAlert`, `InflationAlert`, `RoyalTaxAssessed`, `ArbTradeExecuted`.

---

## 8) Typical Flows (Narrative → Deterministic Hooks)

### 8.1 Healthy Inner Ward (W2)

1) Daily `ReserveAttested(coverage≈1.0)`.

2) Narrow spreads (fx_spread ≈ base + small risk).

3) Labor paid half in credits, half in water (small bonus).

4) `CreditRateUpdated` stable; rumor bus calm.

### 8.2 Stressed Outer Ward (W21)

1) Reclaimer outage → rumor of short water window.

2) `HoardingAlert` trips (`wait_min` rising, spreads widen).

3) King opens **swapline**, mandates audit; issuer posts **RedeemRate** glidepath (predictable), clerks broadcast.

4) Hoarding de‑escalates; FX discount narrows; legitimacy +ε.

### 8.3 Bad Actor Issuer

1) Over‑mints to pay mercs; coverage dips below threshold.

2) `InflationAlert` + widening FX discount; Arbiter orders mint freeze.

3) Continues games → **ReceivershipInvoked**; temporary technocrat and royal guard secure vaults/reservoir.

4) Spreads normalize over a week if production recovers.

---

## 9) Explainability & Rumor Hooks

- Every FX and redemption line attaches **evidence**:

  - `LEDGER` (issuance logs), `SENSOR` (reservoir meters), `WITNESS` (queue times), `VIDEO` (public counters).

- Public dashboard per ward:

  - `coverage`, `redeem_wait_min`, `fx_discount`, `royal_tax_paid`, `audit_recency`.

- Rumors get **evidence scores**; civic centers pin official summaries to suppress panic.

---

## 10) Minimal Pseudocode (conceptual)

```python
def update_fx_reference(issuer):
    cov = coverage(issuer)
    base = 1.0
    risk = max(0, 0.5 - cov)  # lower coverage = higher risk
    fx_vs_king = base * (1 + risk)
    emit("CreditRateUpdated", {"issuer": issuer, "fx": fx_vs_king})
    return fx_vs_king

def detect_hoarding(ward):
    wait = median_redeem_wait(ward)
    spread = current_spread("credit:ward", "credit:king", ward)
    if wait > θ_wait or spread-increase > θ_spread:
        emit("HoardingAlert", {"ward": ward, "wait": wait, "spread": spread})
```

---

### End of Credits & FX v1
