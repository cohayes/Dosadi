---
title: Empire_Balance_Sheet_v1_Implementation_Checklist
doc_id: D-RUNTIME-0273
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0231   # Save/Load Seed Vault
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0268   # Tech Ladder v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0272   # Advanced Facilities v1
---

# Empire Balance Sheet v1 — Implementation Checklist

Branch name: `feature/empire-balance-sheet-v1`

Goal: introduce a lightweight **accounting / budget ledger** that:
- ties together institutions, factions, enforcement, tech, and facilities,
- provides a controllable “money-like” abstraction (budget points) without full currency simulation,
- creates a clean place for corruption and taxation to flow and be tested.

This is a key support pillar for multi-century runs.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. Deterministic. Same state/seed → same balances.
2. Bounded. No scanning every agent; use aggregated telemetry and throughput counters.
3. Auditable. Every budget delta has a reason code.
4. Persistent. Ledger is part of seed identity (empire continuity).
5. Composable. Enforcement, tech, and institutions pull from the same budget system.
6. Tested. Conservation-ish properties, caps, persistence.

---

## 1) Core concept

We maintain accounts for:
- each ward institution: `acct:ward:<ward_id>`
- each faction: `acct:fac:<faction_id>`
- central state treasury: `acct:state:treasury`
- optional black market sink: `acct:blackmarket`

We record transactions with:
- amount (float),
- day,
- reason code,
- from_acct / to_acct.

We avoid negative hard errors; if a payer is insolvent:
- v1: cap spending to available balance (preferred)
- v2 option: allow debt with interest

---

## 2) Data structures

Create `src/dosadi/runtime/ledger.py`

### 2.1 Account / transaction model
- `@dataclass(slots=True) class LedgerConfig:`
  - `enabled: bool = False`
  - `max_tx_per_day: int = 2000`      # safety
  - `max_tx_retained: int = 20000`    # bounded history
  - `deterministic_salt: str = "ledger-v1"`

- `@dataclass(slots=True) class LedgerAccount:`
  - `acct_id: str`
  - `balance: float = 0.0`
  - `tags: set[str] = field(default_factory=set)`
  - `notes: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class LedgerTx:`
  - `day: int`
  - `tx_id: str`                 # deterministic (day + counter)
  - `from_acct: str`
  - `to_acct: str`
  - `amount: float`
  - `reason: str`                # e.g. "LEVY_THROUGHPUT", "PAY_ENFORCEMENT"
  - `meta: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class LedgerState:`
  - `accounts: dict[str, LedgerAccount] = field(default_factory=dict)`
  - `txs: list[LedgerTx] = field(default_factory=list)`
  - `last_run_day: int = -1`
  - `tx_counter_day: int = -1`
  - `tx_counter: int = 0`

World stores:
- `world.ledger_cfg`
- `world.ledger_state`

Snapshot + seed vault include ledger_state.

---

## 3) Account creation rules

On world init (or on first ledger run), ensure accounts exist:
- `acct:state:treasury`
- for each ward: `acct:ward:<ward_id>`
- for each faction: `acct:fac:<faction_id>`
- optional: `acct:blackmarket`

Provide helper:
- `get_or_create_account(world, acct_id, tags=...)`

---

## 4) Transaction API (central)

Implement:
- `def post_tx(world, *, day, from_acct, to_acct, amount, reason, meta=None) -> bool`

Rules:
- if disabled: no-op true
- enforce max_tx_per_day
- if from_acct has insufficient funds:
  - v1: cap amount to available balance; if <=0 return false
- update balances
- append tx with deterministic tx_id (e.g., f"{day}:{counter:06d}")
- keep bounded history: if len(txs) > max_tx_retained, evict oldest deterministically

Also implement:
- `def transfer(world, day, from_acct, to_acct, amount, reason, meta=None)`

---

## 5) Where budget comes from (revenue)

v1 revenues should be simple, deterministic, and tied to real activity:

### 5.1 Throughput levy (recommended)
Once per day, for each active ward:
- compute throughput_proxy from telemetry (deliveries, production outputs, construction progress)
- levy = policy.levy_rate * throughput_proxy
- post_tx from `acct:ward:<ward_id>` to `acct:state:treasury` reason `LEVY_THROUGHPUT`

### 5.2 Resource rents (optional)
If a ward controls a high-value node (mine/extractor), it gets budget points:
- post_tx from `acct:state:treasury` to ward account reason `RENT_DISTRIBUTION`

### 5.3 Corruption skims (corruption)
High-corruption wards leak a fraction of ward revenue to black market:
- post_tx from ward to `acct:blackmarket` reason `CORRUPTION_LEAK`
Optional: move from blackmarket to raider factions based on alignment/territory.

Keep bounded and capped.

---

## 6) Where budget goes (spending)

### 6.1 Enforcement (0265)
Institutions decide enforcement_budget_points.
Translate into a daily payment:
- payer: `acct:ward:<ward_id>`
- payee: `acct:state:treasury` (or `acct:fac:state`, pick one)
- reason: `PAY_ENFORCEMENT`
Then 0265 reads “paid enforcement” as the effective budget.
If unpaid, enforcement is scaled down.

### 6.2 Audit (0269)
- reason: `PAY_AUDIT`
Higher audit payments increase audit capacity.

### 6.3 Tech sponsorship (0268)
When starting tech projects:
- pay from sponsor ward/faction account into a research sink (or keep internal)
- reason: `PAY_RESEARCH`
If insufficient, project can’t start.

### 6.4 Facility maintenance (0253)
Maintenance costs can be denominated in materials and/or budget points:
- ward pays `PAY_MAINTENANCE`
If short, facility performance degrades.

v1: budget affects service quality, not hard stops everywhere.

---

## 7) Ledger update loop (daily)

Implement:
- `run_ledger_for_day(world, day)`

Order:
1) Ensure accounts exist.
2) Apply revenues (levies) based on throughput proxies.
3) Apply corruption leaks based on institution corruption.
4) Apply planned spending (enforcement/audit budgets), capping by balances.
5) Emit telemetry.

This loop should run before enforcement/tech decisions (or provide last-day values).

---

## 8) Integration points (minimal wiring plan)

1) Institutions (0269):
- levy_rate is already in policy; ledger uses it
- corruption controls leak rate

2) Enforcement (0265):
- enforcement uses paid budget from ledger

3) Tech ladder (0268):
- research sponsorship requires payment

4) Factions (0266):
- faction accounts allow raiders to grow capacity by spending budget
- raiders can gain budget via blackmarket transfers or raid proceeds (optional v1)

5) Telemetry (0260):
- ledger panel, top accounts, top tx reasons

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["ledger"]["balances"]["state_treasury"]`
- `metrics["ledger"]["balances"]["avg_ward"]`
- `metrics["ledger"]["balances"]["avg_faction"]`
- `metrics["ledger"]["tx_count"]`

TopK:
- richest wards
- lowest-balance wards
- biggest corruption leaks
- biggest enforcement spends

Cockpit:
- account list (TopK by balance)
- recent transactions (N)
- ward finance page: revenue, spend, leak, net

---

## 10) Persistence / seed vault

Ledger is part of long-run identity:
- include ledger_state in seed vault persisted layer
- export stable:
  - `seeds/<name>/ledger_accounts.json` sorted by acct_id with balances
Transaction history export optional; v1 can omit to keep seeds small.

---

## 11) Tests (must-have)

Create `tests/test_empire_balance_sheet_v1.py`.

### T1. Determinism
- same telemetry inputs → same balances and tx list.

### T2. Caps on spending
- if ward has low balance, enforcement payments cap (no negatives).

### T3. Corruption leak effect
- higher corruption increases leak amount deterministically.

### T4. Conservation-ish sanity
- sum of balances changes only via explicit mint/burn reasons
(define which reasons can mint/burn, e.g. RENT_DISTRIBUTION uses state treasury seeding)

### T5. Bounded tx history
- tx list never exceeds max_tx_retained; eviction deterministic.

### T6. Snapshot roundtrip
- balances and tx counters persist; tx_id continues deterministically after load.

---

## 12) Codex Instructions (verbatim)

### Task 1 — Add ledger module + state
- Create `src/dosadi/runtime/ledger.py` with LedgerConfig/Account/Tx/State
- Add world.ledger_cfg/world.ledger_state to snapshots + seed vault persisted layer
- Provide `post_tx()` API with caps and bounded tx retention

### Task 2 — Implement daily ledger loop
- Ensure accounts exist for state/wards/factions
- Apply throughput levies using telemetry throughput proxies
- Apply corruption leak transfers based on institution corruption
- Apply payments for enforcement/audit budgets (capped)
- Emit metrics/topK

### Task 3 — Wire enforcement + tech to ledger
- Enforcement uses paid budget from ledger
- Tech sponsorship requires ledger payment to start projects

### Task 4 — Cockpit + tests
- Add ledger panels (balances + recent txs)
- Add `tests/test_empire_balance_sheet_v1.py` (T1–T6)

---

## 13) Definition of Done

- `pytest` passes.
- With enabled=True:
  - wards earn/spend budget points deterministically from real activity,
  - corruption leaks budget to black market/factions,
  - enforcement and research are constrained by ability to pay,
  - ledger state persists into 200-year seeds,
  - cockpit can explain the empire’s finances.

---

## 14) Next slice after this

Diplomacy & Treaties v1 — nonviolent corridor stabilization and resource-sharing contracts
between wards/factions (a softer counter to D3 ecosystem harshness).
