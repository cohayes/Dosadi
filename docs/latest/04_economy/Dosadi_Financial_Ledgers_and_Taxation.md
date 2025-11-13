---
title: Dosadi_Financial_Ledgers_and_Taxation
doc_id: D-ECON-0009
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-13
parent: D-ECON-0001
---
# **Financial Ledgers & Taxation v1 (Double‑Entry, Multi‑Issuer Credits, Water Basis, Audits)**

**Version:** v1 — 2025‑11‑13  
**Purpose.** Provide a consistent accounting spine so factions, shops, clinics, escorts, and lords record value, pay taxes, and withstand audits. Defines double‑entry ledgers across **multiple issuer credits** and **liters of water**, “water basis” fair‑value marking, tax categories (skim, excise, fines, subsidies), reserve rules for issuers, reconciliation against Telemetry checkpoints, and Arbiter audit workflows.

Integrates with **Credits & FX v1.1** (rates, liquidity), **Barrel Cascade v1.1** (official trades & skim), **Telemetry & Audit v1** (checkpoints, custody), **Law & Contract Systems v1** (decrees, cases), **Production & Fabrication v1**, **Clinics v1.1**, **Logistics v1**, **Identity/Licensing v1**, **Rumor v1.1**, and the **Tick Loop**.

> Timebase: operational postings **per event**; valuation/FX **hourly**; tax accrual **daily**; settlement **weekly** or **on‑delivery**; audits **on trigger** or **monthly**.

---
## 0) Entities & Account Model

- **Ledger** `{entity_id, chart_of_accounts, base_unit: LITERS, alt_units: [issuer_credits...], water_basis_ref}`  
- **Accounts (examples)**  
  - **Assets**: `Water_Inventory_L`, `Credits_{issuer}`, `Receivables_{issuer}`, `Materials`, `Equipment`  
  - **Liabilities**: `Payables_{issuer}`, `Taxes_Payable_{king|lord}`, `Bonds_Payable`, `Warranties_Reserve`  
  - **Equity**: `Capital`, `Retained_Earnings`  
  - **Income**: `Water_Sales`, `Services_Income`, `Subsidies_Received`  
  - **Expenses**: `Materials_Expense`, `Labor`, `Energy`, `Water_Loss_Expense`, `Fines_Penalties`  
- **Journal Entry** `{ts, lines[], memo, links{contract_id, lot_id, custody_id, checkpoint_id}, sigs}`  
  - **Line** `{account, amount, unit: L|issuer_credit, dr|cr}` — **must balance in water basis**.

---
## 1) Valuation: Water Basis & Multi‑Currency

- **Water Basis**: canonical valuation frame; every posting converts to liters via **FX mid** (`Credits & FX v1.1`).  
- **Mark‑to‑Market**: revalue `Credits_{issuer}`, `Receivables`, `Payables` hourly with **WaterBasis**; post gains/losses to `FX_PnL`.  
- **Inventory (Liters)**: barrels and sealed containers tracked as **Water_Inventory_L** with shrink/loss posted to `Water_Loss_Expense` (reconciled to Telemetry).

---
## 2) Recognition Rules (when to book)**

- **Official Cascade Transfers**: on **dual‑sign custody** at checkpoint → DR `Water_Inventory_L`, CR `Credits_{king|lord}` or `Subsidy_Income` minus skim.  
- **Fabrication Deliveries**: on `LotDelivered` acceptance → DR `Receivables_{issuer}`, CR `Services_Income`.  
- **Clinic Episodes**: at discharge or voucher redemption → DR `Receivables/Vouchers`, CR `Services_Income`.  
- **Logistics**: on `DeliveryCompleted` → DR `Cash/Credits`, CR `Transport_Income`; claim events post to `Insurance_Income` or `Loss_Expense`.  
- **Taxes**: accrue **daily**; settle **weekly** or upon delivery depending on rule.

---
## 3) Tax Categories & Formulas

- **Skim Tax (Cascade)**: % of liters on official barrel transfers.  
  - Default: `king_skim = 0.10`, `overlord_skim = 0.02` (tunable per ward).  
  - Posting: DR `Tax_Expense`, CR `Taxes_Payable_king`.  
- **Excise on Regulated Goods**: % on meds, high‑grade seals, weapons.  
- **Income Assessment**: % on `Net_Income_WaterBasis` (after expenses, before subsidies).  
- **Withholding on Contracts**: % retained by payor until warranty/inspection window closes.  
- **Fines & Penalties**: from decrees; recognized at decree time.  
- **Subsidies/Credits**: negative taxes for priority mandates; booked to `Subsidies_Received` and offset liabilities if directed.  
- **Issuer Reserve Requirement** (for offices/lords minting credits): minimum **Reserve Ratio**: `Water_Inventory_L / Credits_Outstanding >= R_min` with breach penalties.

---
## 4) Reconciliation & Variance

- **Telemetry Checkpoint Reconcile**: compare **ledger** `Water_Inventory_L` & `Cascade Receipts` vs **anchored** checkpoints (barrel handoffs, lot QA).  
- **Variance Flags**: threshold % or absolute L; repeated flags trigger `AuditOpened`.  
- **Benford & Ratio Tests**: heuristic fraud flags on postings and invoice sizes.  
- **Aging**: receivables/payables by issuer token; long tail raises **credit risk** and rumor heat.

---
## 5) Rumor & Transparency Hooks

- **Public Boards**: post summarized stats (on‑time tax settlement, reserve coverage, audit outcomes).  
- **Reputational Effects**: late taxes or reserve breaches lower **legitimacy** and raise borrowing costs (FX spread).  
- **Voluntary Disclosure**: factions can publish clean reconciliations for trust boosts.

---
## 6) Policy Knobs (defaults)

```yaml
ledgers_taxation:
  water_basis_mark_hourly: true
  tax_rates:
    skim_king: 0.10
    skim_overlord: 0.02
    excise:
      meds: 0.05
      seals_S: 0.06
      weapons_heavy: 0.08
    income: 0.04
    withholding: 0.05
  issuer_reserve_ratio_min: 0.25
  reconciliation_threshold:
    liters_abs: 50
    percent: 0.01
  audit_sampling_rate: 0.05
  benford_enabled: true
  settlement_cycle_days: 7
  penalties:
    late_tax_daily: 0.002
    reserve_breach_surcharge: 0.03
```

---
## 7) Event & Function Surface (for Codex)

**Functions**  
- `open_ledger(entity_id, chart)` → initializes accounts.  
- `post_txn(entity_id, journal_entry)` → validates balance (water basis), signatures, links to evidence.  
- `mark_to_waterbasis(entity_id)` → revalue multi‑currency balances; post FX PnL.  
- `assess_taxes(entity_id, period)` → compute skim/excise/income/withholding; create liabilities.  
- `settle_taxes(entity_id, pay_instrument)` → reduce `Taxes_Payable`; emit settlement anchor.  
- `reconcile_checkpoints(entity_id, from_ts, to_ts)` → produce variance report & flags.  
- `issue_fine(entity_id, decree)` / `issue_subsidy(entity_id, decree)` → post liabilities/credits.  
- `reserve_check(issuer_id)` → compute reserve ratio; emit `ReserveBreach` if below floor.

**Events**  
- `LedgerPosted`, `FXMarked`, `TaxAssessed`, `TaxSettled`, `VarianceAlert`, `AuditOpened`, `ReserveBreach`, `FineIssued`, `SubsidyIssued`.

---
## 8) Pseudocode (Indicative)

```python
def post_txn(ledger, je):
    total_L = 0.0
    for line in je.lines:
        amt_L = convert_to_liters(line.amount, line.unit)  # FX mid
        total_L += amt_L if line.dr else -amt_L
    assert abs(total_L) < 1e-6, "unbalanced_in_water_basis"
    verify_links(je.links)   # custody, checkpoint, lot
    ledger.apply(je)
    emit("LedgerPosted", {"entity": ledger.entity_id, "ts": je.ts})

def assess_taxes(ledger, period):
    skim = calc_skim(ledger, period)      # from cascade events
    exc = calc_excise(ledger, period)
    inc = max(0, net_income_waterbasis(ledger, period) * policy.tax_rates["income"])
    je = compose_tax_entry(skim, exc, inc)
    post_txn(ledger, je)
    emit("TaxAssessed", {"entity": ledger.entity_id, "sum_L": total_tax_L(je)})

def reconcile_checkpoints(ledger, start, end):
    anchors = fetch_checkpoints(ledger.entity_id, start, end)
    variance = compare_water_flows(ledger, anchors)
    if variance.above_threshold():
        emit("VarianceAlert", {"entity": ledger.entity_id, "variance": variance})
```

---
## 9) Dashboards & Explainability

- **Water‑Basis P&L**: income/expense by category in liters, FX PnL, subsidies, fines.  
- **Cash & Credits**: balances by issuer; reserve ratio for issuers.  
- **Taxes**: accrued vs settled; aging of payables; penalty run‑rate.  
- **Reconciliation**: variance by period; checkpoint coverage; audit trail completeness.  
- **Compliance Score**: composite of on‑time settlement, reserve health, variance, and audit outcomes.

---
## 10) Test Checklist (Day‑0+)

- Journals balance under water basis; FX marking posts PnL without creating or destroying liters.  
- Cascade transfers automatically create skim taxes and custody‑linked entries.  
- Excise applies to regulated items; income tax on net water‑basis income; withholding reverses on warranty close.  
- Reconciliation finds missing liters; repeated flags open audits; penalties accrue per policy.  
- Issuers below reserve floor trigger `ReserveBreach`; rumor/FX spread worsens until resolved or receivership.

---
### End of Financial Ledgers & Taxation v1
