---
title: Financial_Ledgers_and_Taxation
doc_id: D-ECON-0009
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
depends_on:
  - D-ECON-0001   # Ward_Resource_and_Water_Economy
  - D-ECON-0002   # Dosadi_Market_Microstructure
  - D-ECON-0003   # Credits_and_FX
  - D-WORLD-0003  # Ward_Branch_Hierarchies
  - D-INFO-0001   # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002   # Espionage_Branch
  - D-INFO-0003   # Information_Flows_and_Report_Credibility
  - D-INFO-0004   # Scholars_and_Clerks_Branch
---

# Financial Ledgers & Taxation

> This document defines **how value is recorded on Dosadi**:
> - Account structures for lords, branches, facilities, guilds, and agents.
> - The basic **double-entry** patterns for water, credits, and goods.
> - Where and how **taxes, skims, and fines** are applied.
> - How ledgers interface with **telemetry, audits, and espionage**.

It gives the numeric backbone for:

- D-ECON-0001 ward water budgets (what is *booked* vs actually flowing).
- D-ECON-0002 market trades and D-ECON-0003 FX conversions.
- INFO pillar docs that ask, “Did they lie, or did we just lose it?”

---

## 1. Purpose & Scope

This doc answers:

- **Who has a ledger?**
  - Crown, dukes, ward lords, branches, facilities, major guilds, and some agents.
- **What gets recorded?**
  - Water allocations, stock changes, trades, wages, taxes, fines, bribes (sometimes).
- **At what granularity?**
  - Ward-level and facility-level by default; per-agent bookkeeping only when needed.
- **Where do numbers and physical flows diverge?**
  - Leaks, theft, black markets, cooked books.

Out of scope (for now):

- Full accounting standards (accrual vs cash, depreciation).
- Detailed bank instruments (loans, interest curves).
- Procedural generation of “beautiful” financial reports.

We only need enough structure to support:

- Plausible **audits & investigations**.
- Tracking **who benefits** from scarcity.
- Simulation hooks for **trust, credit, and risk**.

---

## 2. Accounting Entities

We define several **ledger-bearing entities**:

1. **Sovereign Accounts**
2. **Ward & Branch Accounts**
3. **Facility Accounts**
4. **Guild / Corporate Accounts**
5. **Agent Pockets (Lightweight)**

### 2.1 Sovereign Accounts

At the top:

- `AC_CROWN_TREASURY`
- `AC_DUKE_[id]_TREASURY`

Track:

- KCR balances.
- Strategic water rights (quota slices at macro level).
- High-level transfers to wards and major guilds.

### 2.2 Ward & Branch Accounts

Each ward `W` maintains:

- `AC_WARD_W_TREASURY`  
- `AC_WARD_W_CIVIC`  
- `AC_WARD_W_INDUSTRIAL`  
- `AC_WARD_W_MILITARY`  
- `AC_WARD_W_CLERICAL` (if they have their own budget)  
- Optional:
  - `AC_WARD_W_ESPIONAGE` (often hidden or obfuscated).

These accounts:

- Hold **WCR_W**, **KCR**, water rights, and sometimes physical stocks.
- Are the main interface between:
  - Ward lord, branches, and sovereign accounts.
- Provide:
  - A clean place to look when asking, “Where did the money go?”

### 2.3 Facility Accounts

Each major facility has at least one account:

- `AC_FAC_W21_KITCHEN_01`
- `AC_FAC_W21_BUNK_03`
- `AC_FAC_W21_PLANT_RECLAIM_02`
- `AC_FAC_W21_BAZAAR_01`

They track:

- Incoming water & food stocks.
- Outgoing rations, bunk-nights, services.
- WCR, chits, and sometimes KCR flows.

### 2.4 Guild / Corporate Accounts

Guilds (industrial, service, black-market) maintain:

- `AC_GUILD_[id]_[ward]`

They:

- Sit between branch/ward accounts and individual facilities.
- Are ideal places for:
  - Profit skimming, internal redistribution, and hidden reserves.

### 2.5 Agent Pockets (Lightweight)

Most individual agents **do not need full double-entry** books. Instead:

- We treat their wallet (from D-ECON-0003) as a **thin ledger**:
  - Just balances.
- When an agent trades:
  - A full ledger entry happens at facility/guild/ward level.
  - The agent’s wallet is updated as a “counterparty side” without full account structure.

We only give full ledgers to:

- Very large operators masquerading as “agents” (crime bosses, major fixers).
- PC-like entities, if the game requires deeper financial play.

---

## 3. Account Dimensions & Structure

We don’t need full-blown GAAP, but we need **consistent dimensions**.

### 3.1 Core Dimensions

Every ledger line has:

- `time` (sim tick or cycle)
- `ward` (where the economic event is recognized)
- `entity` (account owner: ward, branch, facility, guild, etc.)
- `account_id` (e.g. `AC_WARD_W21_CIVIC`)
- `item` (what changed: `water_L`, `KCR`, `WCR_W21`, `ration:LOW`, etc.)
- `delta` (signed quantity; positive = increase)
- `side` (DEBIT|CREDIT – optional if we keep it simple)
- `counterparty` (other account involved, if known)
- `source_event` (e.g. `TradeExecuted`, `FXTradeExecuted`, `TaxAssessed`, `WagePaid`)
- `annotations` (free-form tags: “black_market?”, “audit_flag?”, “bribe?”)

### 3.2 High-Level Account Types

At a conceptual level, accounts collapse into:

- **ASSETS**:
  - Water rights, stored water, inventories, credits balances.
- **LIABILITIES**:
  - Obligations (chits issued, unpaid wages, fines owed).
- **REVENUE**:
  - Taxes, rents, markups, service fees.
- **EXPENSES**:
  - Wages, subsidies, maintenance, bribes, fines paid.

We don’t need to explicitly label every account in the doc, but we should be able
to say, e.g.:

- `AC_WARD_W21_TAX_POOL` is a REVENUE accumulator.
- `AC_FAC_W21_KITCHEN_01_INVENTORY` is an ASSET store (rations, water).
- `AC_WARD_W21_SUBSIDIES` is an EXPENSE sink.

---

## 4. Double-Entry Patterns (Canonical Moves)

We define a few core **transaction templates**.

### 4.1 Barrel Cascade (Crown → Ward)

Event: crown allocates water to ward W21.

```text
DEBIT  AC_WARD_W21_WATER_RIGHTS       +Q
CREDIT AC_CROWN_WATER_RESERVE         -Q
```

- Telemetry:
  - Flow meters at well head log physical movement.
- This forms the link between:
  - D-ECON-0001’s `W_quota[ward]` and actual ledger state.

### 4.2 Ward → Branch Budget Allocation

Event: ward treasury grants initial water + WCR to civic branch.

```text
DEBIT  AC_WARD_W21_CIVIC_WATER        +Q_water
CREDIT AC_WARD_W21_WATER_RIGHTS       -Q_water

DEBIT  AC_WARD_W21_CIVIC_WCR          +X_wcr
CREDIT AC_WARD_W21_TREASURY_WCR       -X_wcr
```

This allocation defines the **branch budgets** that drive facility quotas.

### 4.3 Trade at a Civic Kitchen (Ration Sale)

Event: agent buys 1 LOW ration meal with WCR at Kitchen_01.

Ignoring tax, simplified:

```text
DEBIT  AC_FAC_W21_KITCHEN_01_WCR      +p
CREDIT AC_WARD_W21_CIVIC_WCR          -p        # or agent wallet → kitchen account

DEBIT  AC_AGENT_[id]_NUTRITION        +1_ration # may be implicit
CREDIT AC_FAC_W21_KITCHEN_01_RATIONS  -1_ration
```

In practice:

- Agent wallet WCR decreases, but we only write full double-entry on facility side.
- Nutrition / inventory for the agent can be tracked separately in the agent model.

### 4.4 FX Trade (WCR → KCR)

Event: guild converts 100 WCR_W21 to KCR at an FX kiosk:

```text
DEBIT  AC_GUILD_X_KCR                 +k
CREDIT AC_FX_KIOSK_KCR_POOL           -k

DEBIT  AC_FX_KIOSK_WCR_POOL           +100
CREDIT AC_GUILD_X_WCR_W21             -100
```

Taxes:

```text
DEBIT  AC_GUILD_X_KCR                 -tax_kcr
CREDIT AC_WARD_W21_TAX_POOL_KCR       +tax_kcr
```

---

## 5. Taxation Architecture

We define **three main tax loci**:

1. **Cascade & Quota Taxes** (water as it flows down)
2. **Market & FX Taxes** (trade-level fees and excise)
3. **Income / Profit Taxes** (periodic assessment)

### 5.1 Cascade & Quota Taxes

- Crown charges:
  - A tax or rent on ward water quotas.
- Possible forms:
  - **Fixed quota tithe**: ward owes X% of quota value in KCR.
  - **Variable surcharge**: more punitive for disfavored wards.

Ledger example:

```text
DEBIT  AC_WARD_W21_TAX_EXPENSE_KCR    +t
CREDIT AC_CROWN_TREASURY_KCR          +t
```

This subtly **pushes wards to squeeze their population** or under-invest in
maintenance.

### 5.2 Market & FX Taxes

At market venues, we can define:

- **Trade fee**:
  - Applied to all trades; part may go to:
    - Venue operator (guild).
    - Ward tax pool.
- **Excise tax** on specific goods:
  - Weapons, exo-suits, narcotics, contraband.

Ledger sketch on a trade:

```text
# base trade
DEBIT  AC_BUYER_WCR                   -price
CREDIT AC_SELLER_WCR                  +price

# fees
DEBIT  AC_SELLER_WCR                  -fee_seller
CREDIT AC_VENUE_REVENUE_WCR           +fee_venue
CREDIT AC_WARD_TAX_POOL_WCR           +fee_tax   # if split

DEBIT  AC_BUYER_WCR                   -tax_excise
CREDIT AC_WARD_TAX_POOL_WCR           +tax_excise
```

FX trades add:

- **Conversion spread** (venue profit).
- **FX tax** (ward / crown take).

### 5.3 Income / Profit Taxes

Periodically (per cycle or longer), wards may:

- Assess taxes on:
  - Guild profit accounts.
  - Facility surplus.
- Typically via:
  - Simple rules (X% of positive change in balance).
  - Negotiated exceptions for favored allies.

This doesn’t need full accounting; we can approximate:

```text
profit = max(0, Δ_balance_over_period)

tax_due = τ * profit
```

Then:

```text
DEBIT  AC_GUILD_X_WCR                 -tax_due
CREDIT AC_WARD_W21_TAX_POOL_WCR       +tax_due
```

---

## 6. Divergence: Telemetry vs Ledger

The most interesting space is **where numbers disagree**.

For any major flow, we have:

- **Physical telemetry** (meters, tank levels, dehumidifier output).
- **Financial ledger entries** (what should have moved).
- **Operational logs** (facility usage counts, rations served).

### 6.1 Reconciliation Points

Regular checks:

- `WATER_IN_TANK` (from meters) vs summed ledger water inflows.
- `RATIONS_SERVED` (from facility counters) vs ration decrements in facility accounts.
- `FX_RESERVES_KCR` (ledger) vs cash-on-hand estimates & physical storage.

Discrepancies trigger:

- `VarianceAlert` (from D-INFO-0001).
- Updates to **credibility scores** (D-INFO-0003).
- Possible `InvestigationLaunched` events using INFO/espionage tools.

### 6.2 Common Failure / Fraud Patterns

- **Simple Skim**:
  - Some water never makes it into the books.
- **Ghost Flows**:
  - Ledger shows water moved but telemetry doesn’t.
- **Price / Quantity Misreporting**:
  - Real price differs from recorded; difference pocketed.
- **FX Manipulation**:
  - Official parities maintained on paper while actual trades happen off-ledger.

We want the ledger structure to make these patterns:

- Representable as simple deviations.
- Detectable via comparisons between a few key totals.

---

## 7. Hooks for Espionage & Audits

Espionage and investigators use ledgers as **map and weapon**.

### 7.1 Access Levels

Different roles see different slices:

- **Clerks / scholars**:
  - See most official ledgers, but not black ledgers or espionage budgets.
- **Ward auditors**:
  - Can request (and coerce) more complete views for a ward.
- **Espionage branch**:
  - Actively steals ledger fragments and compiles shadow balance sheets.

### 7.2 Ledger Manipulation as Gameplay

Interesting actions:

- Bribing a clerk to **backdate entries** or delete a line.
- Threatening an accountant to reveal **off-book accounts**.
- Investigators running **forensic comparisons**:
  - “If kitchen served N meals, why do we only see M rations debited?”

Mechanically:

- These actions flip flags in `annotations` and `audit_state`:
  - `{"redacted_by": "clerk_X", "suspicion_score": 0.8}` etc.
- Subsequent audits and espionage checks read those flags.

---

## 8. Simulation Hooks & Minimal Implementation

For a first implementation, we can:

1. Maintain **one ledger per ward**, with:
   - Rows: `time, entity, account_id, item, delta, counterparty, source_event, annotations`.
2. Enforce **simple conservation** checks:
   - Sum of water deltas over time should match:
     - Quota + reclaimed − exported − (blackmarket + losses) from D-ECON-0001.
3. Attach simple **tax rules**:
   - Fixed trade fees + excise on certain items + periodic profit skim.
4. Integrate with INFO:
   - Emit `VarianceAlert` when:
     - |telemetry_total − ledger_total| > threshold.
   - Provide **report-ready summaries** for auditors and spies.

Future docs can layer on:

- Full profit/loss statements.
- Ward-level “budget reports.”
- Procedural generation of suspicious patterns and audit trails.

---

## 9. Open Questions

To be resolved via ADRs or future revisions:

- How **thin** can agent-level accounting remain while still supporting:
  - Debt relationships?
  - Personal tax/fine systems?
- Should some wards operate with **systematically falsified books**:
  - Everyone knows the numbers are fake, but they’re still used as ritual.
- Do we want **formal banking institutions** (vaults, trust houses)?
  - Or keep “banks” implicit in ward/guild treasuries for simplicity?

Until decided, we bias toward:

- **Simplicity** at the code level.
- **Richness** in how misalignment between ledgers and reality can create story.
