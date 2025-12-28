---
title: Milestone_KPIs_and_Scorecards_v1_Implementation_Checklist
doc_id: D-RUNTIME-0311
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0233   # Evolve Seeds Harness v1
  - D-RUNTIME-0310   # Scenario Success Contracts v1
---

# Milestone KPIs & Scorecards v1 — Implementation Checklist

Branch name: `feature/kpis-scorecards-v1`

Goal: standardize and harden the KPI layer so that:
- success contracts consume a stable schema (not ad-hoc metric keys),
- evolve harness compares seeds and ranks outcomes consistently,
- dashboards show comparable progress across different runs and versions,
- missing telemetry becomes a *test failure* instead of silent drift.

This slice turns “we have metrics” into “we have a measurement contract.”

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Stable schema.** KPI names and semantics are versioned and consistent.
2. **Deterministic.** KPI derivation must be deterministic.
3. **Cheap.** KPI updates are incremental; avoid scanning world state.
4. **Bounded.** TopK lists bounded; evidence payloads bounded.
5. **Tested.** Schema presence tests + invariants.
6. **Backward-compatible.** Provide adapters from legacy metric keys.

---

## 1) Core concept

A KPI is:
- a named scalar value (int/float/bool encoded),
- with a clear definition and source,
- and (optionally) an attached bounded “evidence” list.

A Scorecard is:
- a named set of KPI values,
- plus derived grades/badges (“depot built”, “first delivery”, “corridor stable”),
- used by the evolve harness to rank seeds.

---

## 2) KPI schema (v1)

Create a canonical schema under `src/dosadi/runtime/kpis.py`.

### 2.1 KPI namespaces

Use a small number of namespaces:

- `progress.*` — milestones and progress counters
- `logistics.*` — deliveries, depots, corridors
- `safety.*` — incidents, injuries, deaths
- `governance.*` — councils, protocols, legitimacy proxies
- `economy.*` — scarcity, prices, stockpiles (coarse)
- `performance.*` — step time, microstep counts, timewarp usage

### 2.2 Minimum KPI set for Founding Wakeup (v1)

Progress:
- `progress.tick`
- `progress.day`
- `progress.phase_id`
- `progress.milestones_achieved` (count)
- `progress.no_progress_ticks` (deadlock input)

Logistics:
- `logistics.depots_built`
- `logistics.routes_active`
- `logistics.corridors_established`
- `logistics.deliveries_completed`
- `logistics.delivery_success_rate` (0..1)
- `logistics.avg_delivery_time_days`

Governance:
- `governance.council_formed` (0/1)
- `governance.protocols_authored`
- `governance.enforcement_actions` (count)
- `governance.legitimacy_proc` (0..1 proxy if available)

Safety:
- `safety.incidents_total`
- `safety.injuries_total`
- `safety.deaths_total`
- `safety.population_alive_ratio`

Economy:
- `economy.water_shortage_severe_days`
- `economy.avg_ration_level` (0..1 proxy)

Performance:
- `performance.ticks_simulated`
- `performance.microsteps`
- `performance.timewarp_steps`
- `performance.step_ms_p50` (optional)
- `performance.step_ms_p95` (optional)

Keep v1 tight; expand later.

---

## 3) Data structures

### 3.1 KPI key and record
- `@dataclass(frozen=True, slots=True) class KPIKey:`
  - `name: str`
  - `dtype: str`          # "int"|"float"|"bool"
  - `description: str`
  - `unit: str | None = None`

- `@dataclass(slots=True) class KPIValue:`
  - `value: float`        # encode ints and bools as floats too
  - `updated_tick: int`
  - `evidence: list[dict] = field(default_factory=list)`  # bounded

### 3.2 KPI store
- `@dataclass(slots=True) class KPIStore:`
  - `schema_version: str = "1.0"`
  - `values: dict[str, KPIValue] = field(default_factory=dict)

World/report:
- `world.kpis: KPIStore`
- `report.kpis: dict[str, float]` (flattened for external tools)
- `report.scorecard: dict[str, object]` (optional)

Persist KPIs in snapshots? Optional for v1; recommended to include in reports and seed vault outputs.

---

## 4) Update mechanism

Implement a single update entrypoint:
- `update_kpis(world, tick, *, mode="micro"|"day"|"run_end")`

Rules:
- **micro:** update only cheap counters (tick/day, deliveries completed increments, incidents increments).
- **day:** compute daily aggregates and derived ratios (delivery success rate, avg ration, etc).
- **run_end:** finalize performance aggregates and scorecard grades.

Avoid scanning agents. Use:
- event hooks to increment counters,
- and cached aggregates already maintained by logistics/governance modules.

---

## 5) Event-hooking pattern

Add “KPI taps” to the runtime event bus you already have (or add minimal hooks):
- On depot built → `logistics.depots_built += 1`
- On corridor established → `logistics.corridors_established += 1`
- On delivery completed → `logistics.deliveries_completed += 1` and record duration
- On protocol authored → `governance.protocols_authored += 1`
- On incident → `safety.incidents_total += 1`

If you don’t have a centralized event bus:
- add tiny calls at the end of each module’s “commit” step to notify KPIs.

---

## 6) KPI adapters for legacy metrics

Implement:
- `kpi_from_legacy_metrics(world.metrics) -> dict[str, float]`

Mapping table:
- `metrics["depots_built"]` → `logistics.depots_built`
- `metrics["deliveries_completed"]` → `logistics.deliveries_completed`
- etc.

This lets you adopt KPIs without rewriting every module immediately.

---

## 7) Scorecards

Create `src/dosadi/runtime/scorecards.py`

### 7.1 Founding Wakeup scorecard (v1)
Compute grades:
- `grade.progress`: number of achieved milestones / required
- `grade.logistics`: routes active + deliveries completed + success rate
- `grade.safety`: alive ratio and incident burden
- `grade.governance`: council formed + protocols authored
- `grade.economy`: shortage days (lower is better)

Compute a scalar `score_total` with weights:
- progress 0.35
- logistics 0.25
- governance 0.15
- safety 0.15
- economy 0.10

Expose:
- `scorecard = {"score_total":..., "grades":..., "badges":[...], "kpis":{...}}`

Badges examples:
- `FIRST_DEPOT_BUILT`
- `FIRST_DELIVERY`
- `COUNCIL_FORMED`
- `NO_SHORTAGE_CRISIS`

---

## 8) Evolve harness integration

Modify evolve harness (0233):
- after each run, read `report.scorecard["score_total"]`
- rank seeds by score_total
- save top seeds to vault with `scorecard.json`

Also support:
- “regression guard”: if score_total drops > X% vs baseline seed, fail CI (optional later).

---

## 9) CLI integration

Add to dashboards:
- KPI panel showing key KPIs (progress/logistics/safety/governance)
- scorecard summary at end of run
- tiny “badges” line

Keep it readable.

---

## 10) Tests (must-have)

Create `tests/test_kpis_and_scorecards_v1.py`.

### T1. Schema presence
- all required KPI names exist after a run (even if zeros).

### T2. Determinism
- same seed/run → identical KPI values and score_total.

### T3. Increment hooks
- simulate depot build and delivery completion → KPIs increment correctly.

### T4. Derived ratios
- with deliveries and failures, delivery_success_rate computed correctly.

### T5. Scorecard monotonicity sanity
- more milestones/deliveries should not lower score_total (within reason).

### T6. Legacy adapter mapping
- a fake legacy metrics dict maps into correct KPI keys.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add KPI schema and store
- Create `src/dosadi/runtime/kpis.py` with KPIKey, KPIValue, KPIStore and required schema list
- Add `world.kpis` and include flattened `report.kpis`

### Task 2 — Add update_kpis() and hook points
- Implement `update_kpis(world, tick, mode=...)`
- Add minimal hook calls in depot, delivery, corridor, protocol, and incident completion points

### Task 3 — Add legacy adapter
- Implement `kpi_from_legacy_metrics()` and integrate it so KPIs populate even before all hooks exist

### Task 4 — Add scorecards
- Create `src/dosadi/runtime/scorecards.py` and compute a Founding Wakeup scorecard from KPIs

### Task 5 — Integrate into evolve harness and dashboards
- Rank seeds by score_total; save scorecard; display KPI panel

### Task 6 — Tests
- Add `tests/test_kpis_and_scorecards_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- Success contract reads KPIs instead of ad-hoc metric keys where possible.
- Evolve harness ranks and saves seeds with `score_total`.
- Dashboards show consistent KPI/score views.
- Missing KPIs are caught by schema tests.

---

## 13) Next slice after this

**D-RUNTIME-0312 Evidence Pipelines for Governance v1** — standardize the “evidence keys”
that councils/institutions need so the world doesn’t stall when telemetry gaps exist.
