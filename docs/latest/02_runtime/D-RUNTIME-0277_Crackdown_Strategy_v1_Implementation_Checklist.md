---
title: Crackdown_Strategy_v1_Implementation_Checklist
doc_id: D-RUNTIME-0277
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0275   # Border Control & Customs v1
  - D-RUNTIME-0276   # Smuggling Networks v1
---

# Crackdown Strategy v1 — Implementation Checklist

Branch name: `feature/crackdown-strategy-v1`

Goal: create the **cat-and-mouse** loop:
- smugglers adapt to enforcement pressure,
- institutions allocate limited enforcement/audit capacity strategically,
- corridor harm (D3 harshness) can be prevented or caused by mismanagement,
- crackdown actions have political cost (legitimacy/unrest) and economic impact.

v1 is a system-level planner, not agent micromanagement.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same state/seed → same crackdown choices.
2. **Bounded.** Choose from TopK borders/corridors; no global per-edge scans.
3. **Multi-objective.** Balance interdiction, throughput, legitimacy, and corruption.
4. **Counterplay.** Smugglers adapt (0276), so naive “always hottest border” fails.
5. **Phase-aware.** P0 soft touch; P2 brutal, corruption-prone.
6. **Tested.** Target selection, action effects, adaptation dynamics, persistence.

---

## 1) Concept model

Crackdown strategy is a daily note produced by institutions:
- which borders to inspect heavily,
- which corridors to patrol/escort,
- which wards to audit,
- where to run sting operations (optional v1),
and what intensity to use.

This produces **modifiers** used by:
- customs checks (0275),
- corridor risk (0261),
- faction interference (0264),
- governance failures (0271) via legitimacy/unrest impacts.

---

## 2) Data structures

Create `src/dosadi/runtime/crackdown.py`

### 2.1 Config
- `@dataclass(slots=True) class CrackdownConfig:`
  - `enabled: bool = False`
  - `border_topk: int = 24`
  - `ward_topk: int = 16`
  - `max_targets_per_day: int = 6`
  - `deterministic_salt: str = "crackdown-v1"`
  - `intensity_levels: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0)`
  - `cooldown_days: int = 7`

### 2.2 Plan outputs
- `@dataclass(slots=True) class CrackdownTarget:`
  - `kind: str`                # "border"|"corridor"|"ward_audit"
  - `target_id: str`           # border_id/corridor_id/ward_id
  - `intensity: float`         # 0..1
  - `start_day: int`
  - `end_day: int`
  - `reason: str`              # explainable summary
  - `score_breakdown: dict[str, float] = field(default_factory=dict)`

- `@dataclass(slots=True) class CrackdownPlan:`
  - `day: int`
  - `targets: list[CrackdownTarget]`
  - `budget_used: float`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.crackdown_cfg`
- `world.crackdown_plans: dict[int, CrackdownPlan]` (bounded by recent days)
- `world.crackdown_active: dict[str, CrackdownTarget]` (active targets indexed)

Persist active targets + recent plan history (bounded). Seeds may omit history.

---

## 3) Enforcement capacity model (inputs)

We need a simple “available capacity” per day:
- from ledger-paid enforcement budgets (0273 + 0265)
- optionally split into:
  - border inspection capacity,
  - patrol capacity,
  - audit capacity.

Define:
- `capacity = f(paid_enforcement_points, paid_audit_points, phase_multiplier)`

Bounded: treat it as a scalar budget and spend it on targets.

---

## 4) Candidate generation (TopK)

Candidates should come from:
- customs metrics (0275): seizures, bribes, inspections, suspected contraband
- smuggling telemetry (0276): smuggling traffic estimates (if visible) OR proxy via customs anomalies
- corridor risk (0261): interdictions, attrition, escort incidents
- institutions (0269): corruption signals and legitimacy fragility

Generate candidate sets:
- `candidate_borders`: TopK by (bribes + seizures + traffic)
- `candidate_corridors`: TopK by (interdictions + risk + throughput importance)
- `candidate_wards`: TopK by (corruption + smuggling_tolerance + unrest)

All TopK and deterministic tie-breaking by id.

---

## 5) Scoring and selection (multi-objective, deterministic)

For each candidate, compute a score:
- harm_score (damage if ignored)
- opportunity_score (expected efficacy)
- political_cost (unrest + legitimacy risk)
- corruption_risk (bribes may capture enforcement)

Example:
- border_score = +0.5*bribes +0.7*seizures +0.3*traffic
              -0.4*political_cost -0.3*corruption_risk

Corridor score considers:
- corridor importance (critical route for water/food)
- current risk level
- ability to reduce risk with patrol intensity

Ward audit score considers:
- corruption level
- governance failure risk (0271 synergy)
- audit effectiveness (paid audit points)

Select up to max_targets_per_day by descending net score, subject to:
- capacity budget
- cooldown_days per target
- minimum intensity threshold.

---

## 6) Action effects (how plans modify the world)

### 6.1 Border crackdown effect (customs)
While active:
- inspection probability multiplier increases (bounded)
- contraband detection probability increases (bounded)
- bribe success probability decreases (bounded)
- political cost: legitimacy hit and unrest increase if intensity high

### 6.2 Corridor patrol effect (risk)
While active:
- corridor interdiction risk decreases (bounded)
- escort coverage increases (bounded)

### 6.3 Ward audit effect (institutions)
While active:
- reduces corruption drift rate in the ward
- increases detection of corruption leaks (ledger)
- but can increase anti_state culture if overused (P2)

All effects should be implemented as reversible modifiers with clear source tags.

---

## 7) Feedback loops with smugglers (expected dynamics)

Smuggling (0276) updates edge_stats based on seizures and bribe failures, so:
- after crackdown on a border, smuggling should shift routes away deterministically.

Add a simple “exploration” component:
- reserve 1 target slot occasionally for the next-best border to avoid predictable cycles.
Deterministic schedule: every 7th day choose one exploratory target.

---

## 8) Governance and legitimacy impacts (A3 link)

Crackdowns impose political cost:
- higher intensity increases unrest and reduces legitimacy short-term.
In P2, corruption may turn crackdowns into extortion, increasing unrest further.

Tie into governance failures:
- if repeated crackdowns occur in same ward, increase strike/riot propensity (0271) unless legitimacy high.

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["crackdown"]["targets_active"]`
- `metrics["crackdown"]["capacity_used"]`
- `metrics["crackdown"]["seizures_delta"]` (optional before/after)
- `metrics["crackdown"]["bribes_delta"]`

Cockpit:
- plan for day: list of targets and score breakdown
- border/corridor pages show active crackdown modifiers
- “effectiveness report”: rolling 14-day changes in seizures/bribes/interdictions (bounded)

Events:
- `CRACKDOWN_PLAN_CREATED`
- `CRACKDOWN_TARGET_ACTIVATED`
- `CRACKDOWN_TARGET_EXPIRED`

---

## 10) Tests (must-have)

Create `tests/test_crackdown_strategy_v1.py`.

### T1. Determinism
- same inputs → same plan targets and intensities.

### T2. Boundedness
- never exceeds max_targets_per_day; candidate TopK respected.

### T3. Cooldowns
- target not reselected within cooldown_days unless emergency override (optional).

### T4. Effects wiring
- active border crackdown increases inspections and reduces bribe success deterministically.

### T5. Smuggler adaptation
- after repeated seizures due to crackdown, smuggling routes shift away within N days.

### T6. Political cost
- high-intensity crackdown increases unrest/lowers legitimacy in ward (bounded).

### T7. Snapshot roundtrip
- active crackdown targets persist and remain effective after load.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add crackdown module + plan state
- Create `src/dosadi/runtime/crackdown.py` with CrackdownConfig and CrackdownPlan/Target
- Add world.crackdown_active (+ bounded history) to snapshots

### Task 2 — Candidate generation + deterministic selection
- Pull candidates from customs metrics, corridor risk, and institution corruption/unrest
- Score candidates with multi-objective function (harm/opportunity/political/corruption)
- Select up to max_targets_per_day under capacity and cooldown constraints
- Emit CRACKDOWN_PLAN_CREATED

### Task 3 — Apply reversible modifiers
- Borders: modify customs inspection/detection/bribe success
- Corridors: modify interdiction risk / escort coverage
- Wards: modify corruption drift and audit strength
- Ensure modifiers expire and are reversible

### Task 4 — Telemetry + tests
- Add cockpit views of plans and active targets with score breakdown
- Add `tests/test_crackdown_strategy_v1.py` (T1–T7)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - a daily crackdown plan is created deterministically,
  - customs/corridor/institution systems consume modifiers,
  - smugglers adapt and plans rotate targets,
  - political costs can trigger governance consequences,
  - cockpit explains why targets were chosen and what changed.

---

## 13) Next slice after this

**War & Raids v1** — formalize A2 predation escalation:
- raids as structured operations,
- territory capture mechanics,
- and corridor collapse dynamics under D3 harshness.
