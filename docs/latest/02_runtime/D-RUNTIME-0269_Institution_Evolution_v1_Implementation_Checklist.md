---
title: Institution_Evolution_v1_Implementation_Checklist
doc_id: D-RUNTIME-0269
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0231   # Save/Load Seed Vault
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0268   # Tech Ladder v1
---

# Institution Evolution v1 — Implementation Checklist

Branch name: `feature/institution-evolution-v1`

Goal: add a *century-scale governance pressure system* that evolves from:
- Phase 0: “baseline legitimacy”
to
- Phase 1: “tightening discipline”
to
- Phase 2: “scarcity, corruption, and fracture” (A3).

This slice is **hybrid** (B3):
- primarily system-level institutions with budgets and policy dials,
- but explicitly shaped by belief/culture signals and faction pressures,
- with hooks to personify later (councilors, marshals, auditors).

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same state/seed → same institutional evolution.
2. **Bounded.** Update only active wards/factions; TopK issues, no global scans.
3. **Phase-aware.** Defaults and dynamics change with phase engine (0241).
4. **Composable.** Feeds into enforcement, factions, tech sponsorship, and beliefs.
5. **Persisted (core identity).** Institutional baselines and corruption levels must persist in seed vault.
6. **Tested.** Determinism, caps, phase transitions, snapshot roundtrip.

---

## 1) Concept model

Institution Evolution v1 introduces **Ward Institutions** as a small state vector per ward:
- legitimacy (public buy-in),
- discipline capacity (ability to enforce protocols),
- corruption pressure (incentive to defect/extract),
- audit capacity (ability to detect graft),
- policy dials (tax/levy rates, enforcement budgets, ration strictness),
which respond to:
- supply shortages (market signals),
- predation and risk (interference, corridor risk),
- cultural beliefs (belief formation outputs),
- faction territory/control (real factions).

The core deliverable is a stable, bounded update step:
- once per day (or per macro-step day),
- per active ward.

---

## 2) Data structures

Create `src/dosadi/runtime/institutions.py`

### 2.1 Config
- `@dataclass(slots=True) class InstitutionConfig:`
  - `enabled: bool = False`
  - `max_active_wards_per_day: int = 24`
  - `issue_topk: int = 12`
  - `deterministic_salt: str = "institutions-v1"`
  - `phase_defaults: dict[str, dict[str, float]] = {"P0":{...},"P1":{...},"P2":{...}}`
  - `daily_delta_caps: dict[str, float] = {"legitimacy":0.02,"corruption":0.03,"audit":0.02,"discipline":0.02}`

### 2.2 Ward institution state
- `@dataclass(slots=True) class WardInstitutionPolicy:`
  - `ward_id: str`
  - `ration_strictness: float = 0.3`     # 0..1
  - `levy_rate: float = 0.05`            # abstract “tax” on throughput
  - `enforcement_budget_points: float = 10.0`  # feeds 0265
  - `audit_budget_points: float = 2.0`
  - `research_budget_points: float = 0.0`      # feeds 0268 (optional)
  - `posture: str = "balanced"`          # “balanced” | “hardline” | “lenient”
  - `notes: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class WardInstitutionState:`
  - `ward_id: str`
  - `legitimacy: float = 0.7`            # 0..1
  - `discipline: float = 0.5`            # 0..1
  - `corruption: float = 0.1`            # 0..1
  - `audit: float = 0.2`                 # 0..1
  - `unrest: float = 0.0`                # 0..1 (derived-ish)
  - `last_updated_day: int = -1`
  - `recent_issue_scores: dict[str, float] = field(default_factory=dict)`  # bounded

World stores:
- `world.inst_cfg`
- `world.inst_policy_by_ward: dict[str, WardInstitutionPolicy]`
- `world.inst_state_by_ward: dict[str, WardInstitutionState]`

Snapshot + seed vault include these.

**Seed vault stance (your preference):**
- persist map + faction territories + culture beliefs (baseline),
- additionally persist institutional state because it’s “empire identity” (recommended).

---

## 3) Active-ward selection (bounded)

Define “active wards” as those with recent:
- high traffic / deliveries,
- high shortages (market urgencies),
- high corridor risk or incidents,
- contested faction territory changes,
- strong belief swings (fear/anger/trust).

Select up to `max_active_wards_per_day` deterministically:
- compute activity_score per ward from TopK signals,
- sort (score desc, ward_id asc),
- take first N.

---

## 4) Issues model (TopK pressure map)

For each active ward, compute a small set of “issues” (bounded, explainable):

Example issue keys:
- `issue:shortage` (from market urgencies affecting ward)
- `issue:predation` (from interference events / risk spikes near ward)
- `issue:wear` (from suit failures / hazard exposure)
- `issue:corruption_opportunity` (high throughput + low audit)
- `issue:belief_anger` (from belief formation: grievance/fear)
- `issue:faction_pressure` (raider/guild/state control conflicts)

Compute issue scores in 0..1, then keep only TopK (issue_topk).

Store into `recent_issue_scores` (bounded).

---

## 5) Daily institution update rule (deterministic dynamics)

Implement:
- `def run_institutions_for_day(world, *, day: int) -> None`

For each active ward:
1) Pull current phase defaults (0241). If new ward state uninitialized, seed from phase defaults.
2) Compute issue scores (TopK).
3) Update state with capped deltas:

Suggested dynamics (simple v1):
- legitimacy decreases with shortages + predation + anger, increases with safety + supply stability
- discipline increases with posture hardline + enforcement success, decreases with high corruption/unrest
- corruption increases with shortage + high throughput + low audit, decreases with audit budget + successful interdictions
- audit increases with audit budget and legitimacy, decreases with corruption pressure
- unrest is derived-ish: `unrest = clamp(0.5*shortage + 0.5*anger + 0.4*predation - 0.3*legitimacy, 0, 1)`

Cap deltas per day with `daily_delta_caps`.

4) Optional policy auto-tuning (v1 can be conservative):
- if shortage high: increase ration_strictness slightly
- if predation high: increase enforcement_budget_points (within a cap)
- if corruption rising: increase audit_budget_points (within a cap)
All deterministic and capped.

Emit events:
- `INST_UPDATED`
- `INST_POLICY_ADJUSTED` (if changed)

---

## 6) Integration points (how institutions affect the rest)

### 6.1 Enforcement budgets (0265)
Wire:
- enforcement system reads `WardInstitutionPolicy.enforcement_budget_points`
and uses it as `budget_points` for ward security planning.

### 6.2 Interference success / ecosystem harshness (0264)
Optionally adjust D3 harshness through institutions:
- low legitimacy/high corruption wards have weaker interdiction follow-through
- apply a small penalty to interdiction_prob or risk suppression when corruption high

### 6.3 Faction growth (0266)
Tie budgets/capacity changes to institutional weakness:
- raiders gain influence faster when local legitimacy low and corruption high
- state claims strengthen when legitimacy high and enforcement succeeds

Keep v1 minimal: just emit telemetry hooks; full coupling can be v2.

### 6.4 Tech sponsorship (0268)
Institution policy can allocate `research_budget_points`:
- if A1 pressure high (wear), sponsor suit tech projects
- if A2 pressure high (risk), sponsor corridor tech

v1: allow tech system to pick a sponsor ward/faction budget owner.

### 6.5 Beliefs/culture (0244)
Feed back:
- emit belief crumbs:
  - `institution_legitimacy:{ward}:{bucket}`
  - `institution_corruption:{ward}:{bucket}`
So culture can encode “trust in state” vs “state is rotten”.

---

## 7) Persistence / seed vault

Add stable export:
- `seeds/<name>/institutions.json` (sorted by ward_id) containing:
  - policy dials,
  - legitimacy/discipline/corruption/audit baseline,
  - optional posture.

This becomes part of the persisted seed layer.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["institutions"]["wards_updated"]`
- `metrics["institutions"]["avg_legitimacy"]`
- `metrics["institutions"]["avg_corruption"]`
- `metrics["institutions"]["avg_unrest"]`

TopK:
- `institutions.most_corrupt_wards`
- `institutions.most_unrest_wards`
- `institutions.biggest_policy_shifts`

Cockpit panel:
- ward table: legitimacy/discipline/corruption/audit/unrest, posture, budgets
- “Why?” for a selected ward: top issues (shortage/predation/belief anger/etc.)

---

## 9) Tests (must-have)

Create `tests/test_institution_evolution_v1.py`.

### T1. Determinism
- clone world; same signals → same state and policy adjustments.

### T2. Delta caps respected
- state changes per day do not exceed caps.

### T3. Phase defaults apply
- phase transition changes baselines and response (P0 vs P2).

### T4. Enforcement budget coupling
- raising enforcement_budget_points changes 0265 outputs deterministically.

### T5. Persistence
- snapshot roundtrip stable continuation
- seed vault export stable ordering

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add institution module + state
- Create `src/dosadi/runtime/institutions.py` with config + WardInstitutionPolicy/State
- Add to snapshots and seed vault persisted layer
- Add stable export `institutions.json`

### Task 2 — Implement active-ward selection + TopK issues
- Derive activity_score from telemetry (shortages, risk, incidents, belief swings, territory changes)
- Select up to max_active_wards_per_day deterministically
- Compute issue scores and keep TopK per ward

### Task 3 — Daily institution update + conservative policy auto-tuning
- Update legitimacy/discipline/corruption/audit/unrest with capped deltas
- Adjust ration_strictness / enforcement budget / audit budget conservatively and deterministically
- Emit events

### Task 4 — Wire integrations
- Enforcement uses enforcement_budget_points from institutions
- Belief crumbs emitted for legitimacy/corruption buckets
- Optional: tech sponsorship uses research_budget_points

### Task 5 — Telemetry + tests
- Add cockpit panel and metrics/topK
- Add `tests/test_institution_evolution_v1.py` (T1–T5)

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=True:
  - institutions evolve deterministically and phase-aware,
  - corruption/unrest can rise under scarcity/predation pressure,
  - enforcement budgets respond (and visibly change corridor stability),
  - beliefs record legitimacy/corruption sentiment,
  - seed vault captures institutional state for 200-year seeds,
  - cockpit explains “why this ward is destabilizing.”

---

## 12) Next slice after this

Pick the next “empire spice”:
1) **Culture Wars v1** — beliefs → norms → faction alignment shifts (soft power)
2) **Advanced Facilities v1** — labs/fabs, higher-tier suits, deep economy tiers
3) **Governance Failure Incidents v1** — coups, strikes, ward secessions (A3 escalation)
