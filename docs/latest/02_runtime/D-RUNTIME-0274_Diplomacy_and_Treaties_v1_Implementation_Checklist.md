---
title: Diplomacy_and_Treaties_v1_Implementation_Checklist
doc_id: D-RUNTIME-0274
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
  - D-RUNTIME-0259   # Expansion Planner v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
---

# Diplomacy & Treaties v1 — Implementation Checklist

Branch name: `feature/diplomacy-treaties-v1`

Goal: add a lightweight **contract layer** for corridor stability and resource sharing:
- enables nonviolent stabilization (a counter to D3 harshness),
- creates credible levers for institutions and factions beyond “fight or die,”
- produces emergent geopolitics over 200-year runs.

v1 is **system-level diplomacy**, not agent dialogue.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same treaty proposals and outcomes.
2. **Bounded.** Evaluate only TopK counterparties and TopK corridors/materials.
3. **Enforceable.** Treaties create concrete obligations, breaches, and consequences.
4. **Composable.** Feeds into logistics, corridor risk, factions, culture, and ledger.
5. **Persisted.** Treaties are part of “empire identity” and must be seed-vaulted.
6. **Tested.** Proposal selection, execution, breach detection, persistence.

---

## 1) Concept model

A treaty is a **contract between two parties** (ward institutions and/or factions) that specifies:
- obligations (deliver X per day/week, escort coverage, corridor maintenance),
- consideration (payments, resource swaps, safe passage),
- monitoring (how to detect breach),
- penalties (sanctions, enforcement posture shift, risk multipliers),
- duration and renewal logic.

We avoid bargaining UIs; instead:
- system proposes treaties when pressure is high,
- accepts/rejects based on deterministic utility and cultural alignment.

---

## 2) Parties

Define party IDs:
- `party:ward:<ward_id>`
- `party:fac:<faction_id>`

In v1, focus on **ward ↔ ward** treaties.
Optionally allow ward ↔ guild/state faction where useful.

---

## 3) Treaty types (v1 set)

1) **SAFE_PASSAGE**
- obligation: allow couriers of counterparty through specified corridors
- effect: reduces corridor risk multiplier for shipments (bounded)
- consideration: payment per shipment or per day

2) **ESCORT_PACT**
- obligation: provide escort capacity on corridor segment(s)
- effect: reduces predation outcomes (A2 counter)
- consideration: payment + priority supplies

3) **RESOURCE_SWAP**
- obligation: deliver material A weekly
- consideration: deliver material B weekly
- effect: reduces market urgency spikes

4) **MAINTENANCE_COMPACT**
- obligation: jointly fund/perform corridor upgrades/repairs (0267, 0253)
- effect: corridor condition improves faster; shared costs via ledger

---

## 4) Data structures

Create `src/dosadi/runtime/treaties.py`

### 4.1 Config
- `@dataclass(slots=True) class TreatyConfig:`
  - `enabled: bool = False`
  - `max_active_treaties: int = 200`
  - `max_new_treaties_per_day: int = 3`
  - `counterparty_topk: int = 12`
  - `corridor_topk: int = 24`
  - `deterministic_salt: str = "treaties-v1"`
  - `default_duration_days: int = 60`
  - `renewal_window_days: int = 10`

### 4.2 Treaty spec/state
- `@dataclass(slots=True) class TreatyObligation:`
  - `kind: str`                    # "deliver", "escort", "allow_passage", "maintain"
  - `material: str | None = None`
  - `amount: int | float | None = None`
  - `cadence_days: int = 1`
  - `corridor_ids: list[str] = field(default_factory=list)`
  - `meta: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class TreatyTerms:`
  - `treaty_type: str`
  - `party_a: str`
  - `party_b: str`
  - `obligations_a: list[TreatyObligation]`
  - `obligations_b: list[TreatyObligation]`
  - `consideration: dict[str, object] = field(default_factory=dict)`
  - `penalties: dict[str, object] = field(default_factory=dict)`
  - `duration_days: int = 60`

- `@dataclass(slots=True) class TreatyState:`
  - `treaty_id: str`
  - `terms: TreatyTerms`
  - `start_day: int`
  - `end_day: int`
  - `status: str = "active"`       # active | breached | expired | cancelled
  - `breach_score: float = 0.0`
  - `last_checked_day: int = -1`
  - `history: list[dict[str, object]] = field(default_factory=list)`  # bounded

World stores:
- `world.treaty_cfg`
- `world.treaties: dict[str, TreatyState]`

Snapshot + seed vault include treaties (core identity).

---

## 5) Treaty proposal generation (bounded)

Implement:
- `propose_treaties_for_day(world, day) -> list[TreatyTerms]`

Signals:
- corridor risk spikes (0261)
- market urgencies (0263)
- institutions needing stability (0269)
- culture alignments (0270)
- ledger capacity to pay (0273)

Counterparty selection:
- for each active ward, pick TopK neighbor wards by:
  - corridor traffic volume,
  - adjacency via corridors,
  - cultural alignment compatibility,
  - mutual benefit (one has surplus, other shortage).

Treaty type selection:
- if corridor risk high: propose ESCORT_PACT or SAFE_PASSAGE
- if shortage mismatch: propose RESOURCE_SWAP
- if corridor condition poor: propose MAINTENANCE_COMPACT

Rank all candidate treaties by utility and pick up to max_new_treaties_per_day.

---

## 6) Acceptance logic (deterministic utility)

Implement:
- `should_accept_treaty(world, terms) -> bool`

Utility inputs per party:
- expected reduction in shortage/risk,
- cost in payments/resources,
- cultural norms (anti_state, smuggling_tolerance, pro_cooperation),
- institutional posture and legitimacy,
- faction pressure (raiders benefit from no treaties).

Accept if:
- utility > threshold, with hysteresis and phase adjustments.

Phase-aware:
- P0 easier acceptance, P2 harder unless desperate.

---

## 7) Execution of obligations (deliveries / payments)

Implement:
- `run_treaties_for_day(world, day)`

For each active treaty:
1) if expired: mark expired.
2) execute obligations due on cadence:
   - deliveries: enqueue logistics orders (0261/0263/0257)
   - payments: ledger transfers (0273)
   - escorts: increase escort coverage on specified corridors (0261/0265)
   - maintenance: enqueue corridor improvement projects (0267/0258)
3) record execution results into treaty history (bounded).

---

## 8) Monitoring and breach detection

Each day (or weekly), compute breach_score updates from:
- missed deliveries,
- non-payment,
- escorts not provided,
- repeated interdictions when pact promised safety.

Breach score increases with each failure, decays slowly on success.

When breach_score > threshold:
- status becomes `breached`
- apply penalties.

---

## 9) Penalties and consequences

Penalties should be bounded and mostly systemic:
- sanctions: increase levy_rate or reduce safe-passage effects for breaching party
- trust hit: culture norms shift (anti_state/anti_counterparty)
- enforcement posture shift (increase audits/escorts) for counterparties
- corridor risk multiplier increases temporarily for that party’s shipments

Emit events:
- `TREATY_SIGNED`
- `TREATY_EXECUTED`
- `TREATY_BREACHED`
- `TREATY_EXPIRED`

---

## 10) Telemetry + cockpit

Metrics:
- `metrics["treaties"]["active"]`
- `metrics["treaties"]["signed"]`
- `metrics["treaties"]["breached"]`
- `metrics["treaties"]["avg_breach_score"]`

TopK:
- treaties by breach risk
- wards with most treaty traffic

Cockpit:
- treaty list with status, parties, type, end_day
- per treaty: obligations, last executions, breach reasons
- per ward: current treaty commitments and net benefit

---

## 11) Persistence / seed vault

Export stable:
- `seeds/<name>/treaties.json` sorted by treaty_id, with terms and status.

Treaties matter for 200-year seeds; keep history bounded so exports stay small.

---

## 12) Tests (must-have)

Create `tests/test_diplomacy_treaties_v1.py`.

### T1. Determinism
- same conditions → same proposed and signed treaties.

### T2. Execution scheduling
- deliveries/payments occur at cadence; treaty history records them.

### T3. Breach detection
- missed obligations increase breach score; sustained misses → breached status.

### T4. Penalties applied
- breached treaty increases corridor risk for breaching party shipments (bounded).

### T5. Persistence
- snapshot roundtrip
- seed export stable ordering

---

## 13) Codex Instructions (verbatim)

### Task 1 — Add treaties module + state
- Create `src/dosadi/runtime/treaties.py` with config + TreatyState/Terms/Obligations
- Add world.treaties to snapshots + seed vault persisted layer
- Add stable export `treaties.json`

### Task 2 — Proposal + acceptance logic (bounded)
- Select active wards and TopK counterparties deterministically
- Propose treaty candidates by corridor risk and market urgency
- Accept/reject using deterministic utility and phase adjustments
- Cap new treaties per day and total active treaties

### Task 3 — Execute obligations and detect breach
- Hook treaty obligations into logistics orders and ledger transfers
- Update breach_score from missed obligations and interdictions
- Apply penalties and emit events

### Task 4 — Telemetry + tests
- Cockpit views and metrics/topK
- Add `tests/test_diplomacy_treaties_v1.py` (T1–T5)

---

## 14) Definition of Done

- `pytest` passes.
- With enabled=True:
  - treaties form deterministically under pressure,
  - obligations generate real logistics + payments,
  - breaches are detected and penalized,
  - treaties persist into seeds,
  - cockpit can explain the diplomatic landscape.

---

## 15) Next slice after this

**Border Control & Customs v1** — tariffs, inspections, contraband flow
to connect treaties, smuggling tolerance, and enforcement into a crisp corridor politics loop.
