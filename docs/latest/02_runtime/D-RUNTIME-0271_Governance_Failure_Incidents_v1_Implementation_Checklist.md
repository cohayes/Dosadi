---
title: Governance_Failure_Incidents_v1_Implementation_Checklist
doc_id: D-RUNTIME-0271
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
---

# Governance Failure Incidents v1 — Implementation Checklist

Branch name: `feature/governance-failure-incidents-v1`

Goal: add the A3 escalation layer: **societal rupture events** that can:
- collapse throughput,
- change territory control,
- disable enforcement temporarily,
- force policy reactions,
and eventually lead to coups, ward secessions, and regime change.

v1 focuses on a small, testable set of incident types that are:
- deterministic,
- phase-aware,
- bounded,
- explainable,
and driven by institutions + culture + scarcity pressure.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same state/seed → same governance failures.
2. **Bounded.** Evaluate only active wards and TopK triggers.
3. **Phase-aware escalation.** P0 rare/low severity; P2 common and severe.
4. **Counterplay.** Enforcement + legitimacy + supply stabilization reduce likelihood/severity.
5. **Composable.** Incidents affect factions, territory, enforcement, and beliefs.
6. **Tested.** Triggering, effects, determinism, persistence.

---

## 1) Incident types (v1 set)

Add the following new incident kinds to the Incident Engine:

1) `STRIKE`
- reduces production throughput in ward for duration
- increases shortages elsewhere
- may be resolved by concessions (policy shift) or enforcement

2) `RIOT`
- increases local damage, interrupts deliveries
- reduces legitimacy, increases unrest
- may result in casualties (abstract), increased fear/anger beliefs

3) `SECESSION_ATTEMPT`
- territory control weakens for state; raiders/guilds may gain
- enforcement budget effectiveness reduced until resolved

4) `COUP_PLOT`
- a “slow burn” incident that can complete into a `COUP`
- driven by corruption + faction pressure + low legitimacy

v1 can implement 1–2 first (STRIKE, RIOT) and leave the latter as optional,
but the checklist includes all for completeness.

---

## 2) Data structures

If 0242 has a general incident payload, extend it with:

- `incident.kind` new enums above
- payload fields:
  - `ward_id`
  - `severity: float` (0..1)
  - `duration_days: int`
  - `cooldown_days: int`
  - `faction_id: str | None` (optional instigator/beneficiary)
  - `effects: dict[str, object]` (computed at spawn)
  - `status: "active"|"resolved"|"failed"` (if not already present)

Add a governance incident config:
- `@dataclass(slots=True) class GovernanceFailureConfig:`
  - `enabled: bool = False`
  - `max_new_incidents_per_day: int = 2`
  - `active_wards_cap: int = 24`
  - `deterministic_salt: str = "govfail-v1"`
  - `base_rates_by_phase: dict[str, dict[str, float]]`  # kind->rate
  - `cooldown_days_by_kind: dict[str, int]`
  - `severity_caps_by_kind: dict[str, float]`

World stores:
- `world.govfail_cfg`
- optional `world.govfail_state` (last_run_day etc.)

Snapshot + seed vault: config + state.

---

## 3) Trigger signals (bounded)

For each active ward, compute trigger scores from existing state:

From Institutions (0269):
- legitimacy, corruption, unrest, discipline, audit
From Culture (0270):
- norms (anti_state, vigilante_justice, smuggling_tolerance, queue_order)
From Economy (0263):
- chronic shortages / urgency
From Predation (0261/0266):
- local predation pressure / contested territory

Compute a bounded trigger vector:
- `t_shortage`, `t_unrest`, `t_corruption`, `t_anti_state`, `t_predation`, `t_discipline_low`

---

## 4) Daily incident generation (deterministic, phase-aware, capped)

Implement:
- `run_governance_failure_for_day(world, day)`

Steps:
1) Select active wards (same as institutions/culture).
2) For each ward, compute per-kind propensity score:
   - `strike_score = f(shortage, unrest, guild_alignment)`
   - `riot_score = f(unrest, anti_state_norm, predation, discipline_low)`
   - `secession_score = f(anti_state_norm, legitimacy_low, faction_pressure)`
   - `coup_plot_score = f(corruption, audit_low, faction_pressure)`
3) Convert score to a deterministic “spawn decision”:
   - either via `pseudo_rand01(salt|day|ward|kind) < rate(score, phase)`
   - or by ranking top candidates and spawning up to max_new_incidents_per_day.
**Recommended for boundedness and determinism:** rank and take top N above threshold.

4) Enforce cooldowns:
- store last incident day by kind per ward (can be in incident history index)
- skip if within cooldown.

5) Spawn incidents with computed severity and duration:
- duration increases with phase and severity
- severity capped per kind

Emit `GOVFAIL_INCIDENT_SPAWNED`.

---

## 5) Effects application (what incidents do)

### 5.1 STRIKE effects
- production multiplier in ward: e.g., `prod *= (1 - 0.6*severity)`
- construction progress multiplier: reduced
- increases market urgency (by reducing output)
- belief crumbs: anger, grievance, solidarity (optional)

Resolution:
- ends after duration OR earlier if:
  - ration strictness adjusted / concessions (policy dial)
  - enforcement pressure high + legitimacy not too low

### 5.2 RIOT effects
- delivery disruption probability increases for edges touching the ward
- infrastructure wear/damage (optional v1: add “damage points” to facilities)
- enforcement effectiveness reduced temporarily (riots occupy patrols)
- legitimacy decreases; fear/anger beliefs increase

Resolution:
- after duration, or earlier if enforcement succeeds and legitimacy above floor.

### 5.3 SECESSION_ATTEMPT effects (optional v1)
- reduce state claim strength and/or increase non-state claim strength in ward
- disable/nerf taxation and audits
- increases corridor risk in/out

Resolution:
- success/failure based on legitimacy + enforcement + faction presence

### 5.4 COUP_PLOT effects (optional v1)
- increases corruption quickly if not contained
- may complete into `COUP` that flips control (territory change)

---

## 6) Counterplay hooks

Governance failures must be mitigable by:
- increasing enforcement budgets (0265)
- reducing shortages (0263 + logistics)
- improving legitimacy (0269) via stable supply and low corruption
- cultural norms (0270): queue_order reduces riot propensity; anti_state increases it

Implement a simple mitigation score:
- `mitigation = 0.4*legitimacy + 0.3*discipline + 0.2*enforcement_cover - 0.3*corruption`

Use it to:
- reduce spawn scores,
- shorten duration,
- reduce severity.

---

## 7) Telemetry + cockpit

Metrics:
- `metrics["govfail"]["spawned"]` by kind
- `metrics["govfail"]["active"]` by kind
- `metrics["govfail"]["avg_severity"]`
TopK:
- worst wards by riot/strike risk (propensity)
Cockpit:
- Active governance incidents list
- For a ward: trigger breakdown (shortage/unrest/anti_state/etc.)
- Effects currently applied (prod multiplier, disruption chance, legitimacy delta)

Events:
- `GOVFAIL_INCIDENT_SPAWNED`
- `GOVFAIL_INCIDENT_RESOLVED`
- `GOVFAIL_ESCALATED` (for plots → coups, optional)

---

## 8) Persistence

Incidents are already persisted via incident engine snapshots.
Ensure any additional cooldown tracking is persisted (either via incident history index or govfail_state).

Seed vault stance:
- it’s OK if active incidents are not in the “persisted seed identity” layer,
but *institution/culture/faction territories* are, and thus governance failures will re-emerge.

---

## 9) Tests (must-have)

Create `tests/test_governance_failure_incidents_v1.py`.

### T1. Determinism
- same triggers → same spawned incidents.

### T2. Caps
- never exceed max_new_incidents_per_day.

### T3. Cooldowns
- cannot spawn the same incident kind in a ward within cooldown.

### T4. Effects apply and revert
- STRIKE reduces production during active duration, restores after resolved.
- RIOT increases disruption during duration, restores after resolved.

### T5. Counterplay
- raising legitimacy/enforcement or reducing shortage reduces propensity/severity deterministically.

### T6. Snapshot roundtrip
- mid-incident save/load continues with same remaining duration and effects.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add governance failure module + config
- Create `src/dosadi/runtime/governance_failures.py` (or extend incident engine) with GovernanceFailureConfig and daily runner
- Add world.govfail_cfg and any state to snapshots

### Task 2 — Add new incident kinds and effect application
- Extend incident enums and payload schema for STRIKE/RIOT/(optional SECESSION_ATTEMPT/COUP_PLOT)
- Apply effects to production/delivery/enforcement via existing hooks and reversible modifiers
- Emit events on spawn/resolution

### Task 3 — Implement deterministic spawn logic (bounded)
- Select active wards and compute trigger vectors
- Rank candidates by propensity and spawn up to cap, respecting cooldowns
- Phase-aware base rates and severity/duration mapping

### Task 4 — Telemetry + cockpit
- Metrics/topK and ward trigger breakdown

### Task 5 — Tests
- Add `tests/test_governance_failure_incidents_v1.py` (T1–T6)

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=True:
  - strikes/riots spawn deterministically and phase-aware under caps,
  - they meaningfully disrupt throughput and legitimacy,
  - mitigation (supply + enforcement + legitimacy) reduces them,
  - effects are reversible and persist through save/load,
  - cockpit explains triggers and impacts.

---

## 12) Next slice after this

**Advanced Facilities v1** (labs, fabs, water-adjacent infrastructure equivalents)
to give the empire more levers to fight A1/A2/A3 across centuries.
