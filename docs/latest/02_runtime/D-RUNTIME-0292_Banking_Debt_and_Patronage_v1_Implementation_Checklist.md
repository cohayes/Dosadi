---
title: Banking_Debt_and_Patronage_v1_Implementation_Checklist
doc_id: D-RUNTIME-0292
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0289   # Labor Unions & Guild Politics v1
  - D-RUNTIME-0291   # Wages, Rations & Class Stratification v1
---

# Banking, Debt & Patronage v1 — Implementation Checklist

Branch name: `feature/banking-debt-patronage-v1`

Goal: make chains of obligation explicit so that:
- guilds/state can issue credit and create debt peonage,
- patronage buys loyalty and stabilizes elites (or rots legitimacy),
- defaults and runs create crises that spill into labor, migration, and governance,
- corruption becomes balance-sheet-visible and policy-relevant.

v1 is macro finance, not per-person accounts.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same credit allocation and defaults.
2. **Bounded.** Ward-level ledgers and TopK counterparties; no micro banking.
3. **Balance-sheet coherent.** No money from nowhere; all flows reconcile.
4. **Phase-aware.** P0 disciplined; P2 predatory lending and patronage spirals.
5. **Composable.** Feeds class hardship, labor, corruption, and faction power.
6. **Tested.** Issuance, interest, default, and persistence.

---

## 1) Concept model

We add a macro “credit layer” atop the empire balance sheet:

Actors who can issue credit:
- State treasury / ward treasuries
- Major guild banks (merchant guilds, water engineers)
- Shadow lenders (smuggling network, heretic patrons) (optional v1)

Borrowers:
- wards (public works, emergencies)
- guilds/factions (operations, facilities)
- class tiers (as aggregates) (optional v1, can model as ward “household debt” proxy)

Debt creates:
- interest obligations (budget drain),
- political obligations (patronage),
- and crisis dynamics (defaults, seizures, unrest).

---

## 2) Instruments (v1)

Represent 3 instrument types:
1) `LOAN_PUBLIC_WORKS`
- borrower: ward treasury
- used for construction/health/defense
- repaid from taxes/production

2) `LOAN_GUILD_CAPITAL`
- borrower: guild/faction
- repaid from tolls/market profits

3) `PATRONAGE_BOND`
- not a “loan” but a recurring transfer:
  - patron → client
  - client provides loyalty/behavior (labor peace, votes, enforcement alignment)

Patronage is explicitly tracked and can be scandalous.

---

## 3) Data structures

Create `src/dosadi/runtime/finance.py`

### 3.1 Config
- `@dataclass(slots=True) class FinanceConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 7`
  - `deterministic_salt: str = "finance-v1"`
  - `max_loans_total: int = 500`
  - `max_loans_per_ward: int = 30`
  - `base_interest_rate: float = 0.01`       # weekly
  - `predatory_rate_bonus: float = 0.02`     # P2 or shadow lenders
  - `default_threshold: float = 0.35`        # hardship/shortage threshold
  - `seizure_strength: float = 0.4`          # what collateral seizures do

### 3.2 Loan model
- `@dataclass(slots=True) class Loan:`
  - `loan_id: str`
  - `instrument: str`                 # LOAN_PUBLIC_WORKS|LOAN_GUILD_CAPITAL|PATRONAGE_BOND
  - `issuer_id: str`                  # treasury or guild bank
  - `borrower_id: str`                # ward or faction
  - `ward_id: str`                    # context ward
  - `principal: float`
  - `rate_weekly: float`
  - `term_weeks: int`
  - `weeks_elapsed: int = 0`
  - `outstanding: float = 0.0`
  - `payment_weekly: float = 0.0`
  - `collateral: dict[str, float] = field(default_factory=dict)`  # e.g., depot toll rights
  - `status: str = "ACTIVE"`          # ACTIVE|PAID|DEFAULTED|RESTRUCTURED|SEIZED
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Patronage contract
- `@dataclass(slots=True) class Patronage:`
  - `patron_id: str`
  - `client_id: str`
  - `ward_id: str`
  - `weekly_transfer: float`
  - `loyalty_effect: float`           # 0..1
  - `corruption_effect: float`        # 0..1
  - `status: str = "ACTIVE"`

World stores:
- `world.finance_cfg`
- `world.loans: dict[str, Loan]`
- `world.patronage: list[Patronage]`
- `world.finance_events: list[dict]` (bounded)

Persist loans and patronage in snapshots and seeds.

---

## 4) Issuance: who lends and why (weekly)

Implement:
- `run_finance_week(world, day)`

Candidate borrowers and reasons:
- wards with:
  - high hardship and low reserves (0291/0273)
  - urgent projects (construction pipeline) with high priority
  - defense emergencies (raids/war)
- guilds with:
  - expansion opportunities (market signals)
  - desire to capture depots/corridors (0289/0257)

Issuers:
- ward treasuries and central treasury (if modeled)
- major guild banks (merchant/engineer archetypes)

Issuance decision:
- score expected benefit (stability, output, control)
- minus default risk (hardship/shortages)
- minus political cost (legitimacy hit if predatory)

Cap total loans (max_loans_total) and per-ward.

---

## 5) Payment and interest

Each week:
- accrue interest: outstanding *= (1 + rate_weekly)
- attempt payment:
  - borrower pays from ledger (0273) with reason `PAY_DEBT_SERVICE`
- if insufficient funds:
  - miss payment; increment delinquency (store in notes)

When term completes:
- if outstanding <= epsilon → PAID
- else restructure or default.

---

## 6) Default and restructuring

Default conditions:
- borrower delinquent for N weeks OR
- hardship high AND reserves low AND shortages persist

On default:
- lender can:
  - restructure (extend term, reduce rate, add patronage constraints)
  - seize collateral (SEIZED)
  - demand austerity policies (rationing regime shifts toward AUSTERITY)

Collateral examples:
- depot toll rights (increase guild capture)
- corridor customs rights
- facility output share
- “seat” influence in institution evolution (soft power)

Seizure effects:
- increases inequality and guild power (0289/0291)
- may increase unrest and migration pressure.

---

## 7) Patronage network

Patronage formation:
- in P2, elites use patronage to stabilize officer tiers and suppress labor unrest.
- create Patronage contracts:
  - treasury → guild leader
  - guild → officers
  - religious institution → communities (optional tie-in 0288)

Effects:
- reduces labor militancy short-run in the ward
- increases corruption and legitimacy fragility long-run
- increases class inequality (0291)

Patronage payments are ledger transfers: `PAY_PATRONAGE`.

---

## 8) Effects wiring

- Class system (0291):
  - debt service crowds out social spending → increases hardship
  - seizure increases inequality and T0/T1 privileges

- Labor (0289):
  - austerity regimes increase strike probability
  - patronage can buy labor peace but raises corruption

- Governance failures (0271):
  - defaults and seizures increase failure incident probability

- Economy signals (0263):
  - credit expands supply temporarily but increases long-run volatility

Keep v1 minimal: hardship/inequality hooks + a few incident triggers.

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["finance"]["loans_active"]`
- `metrics["finance"]["debt_outstanding_total"]`
- `metrics["finance"]["debt_service_weekly"]`
- `metrics["finance"]["defaults"]`
- `metrics["finance"]["seizures"]`
- `metrics["finance"]["patronage_total_weekly"]`

TopK:
- wards by debt burden (debt service / revenue)
- lenders by outstanding and defaults
- wards with repeated restructures

Cockpit:
- loan register: issuer, borrower, outstanding, rate, status, collateral
- ward finance page: revenue, spending, debt service, patronage flows
- “who owns what” view: collateral seizures and captured rights

Events:
- `LOAN_ISSUED`
- `PAYMENT_MISSED`
- `LOAN_RESTRUCTURED`
- `DEFAULT_TRIGGERED`
- `COLLATERAL_SEIZED`
- `PATRONAGE_SIGNED`

---

## 10) Persistence / seed vault

Export stable:
- `seeds/<name>/finance.json` with loans and patronage contracts.

---

## 11) Tests (must-have)

Create `tests/test_banking_debt_patronage_v1.py`.

### T1. Determinism
- same budgets/inputs → same issuance and default outcomes.

### T2. Interest accrual and payment
- outstanding grows by interest; payments reduce it; reconciles with ledger.

### T3. Default path
- persistent inability to pay triggers default and either restructure or seize.

### T4. Seizure effects
- seizure increases inequality and guild capture proxy deterministically.

### T5. Patronage effects
- patronage reduces labor militancy input but increases corruption/inequality.

### T6. Snapshot roundtrip
- loans and patronage persist across snapshot/load and seeds.

---

## 12) Codex Instructions (verbatim)

### Task 1 — Add finance module + loan/patronage models
- Create `src/dosadi/runtime/finance.py` with FinanceConfig, Loan, Patronage
- Add world.loans and world.patronage to snapshots + seeds

### Task 2 — Implement weekly debt service loop
- Accrue interest, attempt payments via ledger, track delinquency

### Task 3 — Implement issuance and default/resolution
- Score borrowers and issue bounded loans
- On delinquency, restructure or default and seize collateral with effects

### Task 4 — Implement patronage network
- Create patronage contracts phase-aware
- Transfer via ledger and apply effects to labor and class indices

### Task 5 — Cockpit + tests
- Add loan register and ward finance views
- Add `tests/test_banking_debt_patronage_v1.py` (T1–T6)

---

## 13) Definition of Done

- `pytest` passes.
- With enabled=True:
  - the empire can borrow, repay, default, and seize collateral coherently,
  - debt service changes policy and class hardship,
  - patronage stabilizes short-run and corrupts long-run,
  - finance state persists into 200-year seeds,
  - cockpit can explain “why the ward is trapped in debt.”

---

## 14) Next slice after this

**Insurance & Risk Markets v1** — premiums as signals:
- corridor insurance and shipping premiums,
- protection rackets as “shadow insurance,”
- and risk pricing shaping expansion decisions.
