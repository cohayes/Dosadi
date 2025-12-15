---
title: Evolve_Seeds_Harness_Implementation_Checklist
doc_id: D-RUNTIME-0233
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-15
depends_on:
  - D-RUNTIME-0231   # Save/Load + Seed Vault + Deterministic Replay
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0001   # Simulation_Timebase
---

# Evolve Seeds Harness — Implementation Checklist

Branch name: `feature/evolve-seeds-harness`

Goal: turn the new capabilities (snapshot/replay + seed vault + timewarp) into an operational pipeline that can generate, catalog, and reload “developed empire” seeds (e.g., 200 years) with repeatable milestones and KPI reporting.

This document is designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic milestones.** Given (scenario_id, seed, config), the harness produces the same milestone snapshot hashes.
2. **Bounded runtime.** The harness advances mostly via macro-step and only uses tick-mode microsim as configured.
3. **Milestones are saved and indexed.** Every milestone saves a snapshot + KPI row + signature.
4. **Progress is auditable.** Harness output is a timeline file you can diff.
5. **Minimal surface area.** Add new modules and small glue; avoid refactors.

---

## 1) Concept: “MacroStep cruise + Microsim dip + Save”

A canonical evolution loop:

1. Initialize from scenario seed (`founding_wakeup` / `wakeup_prime`).
2. Repeat until target years reached:
   - **Cruise:** macro-step forward by `cruise_days` (e.g., 30 days)
   - **Dip:** run tick-mode microsim for `microsim_days` (e.g., 1 day) every `microsim_every_days` (e.g., 90 days)
   - **Milestone:** at defined boundaries (year, phase transition, KPI triggers), save snapshot to vault and log KPIs.

This is how you evolve fast while periodically letting acute systems create texture (queues, incidents, disputes, memory events).

---

## 2) Implementation Slice A — Harness module

### A1. Create module: `src/dosadi/runtime/evolve.py`
**Deliverables**
- `@dataclass(slots=True) class EvolveConfig: ...`
  - `target_years: int = 200`
  - `cruise_days: int = 30`
  - `microsim_days: int = 1`
  - `microsim_every_days: int = 90`
  - `save_every_days: int = 365`  # annual milestone
  - `max_steps: int | None = None`  # safety
  - `timewarp_cfg: TimewarpConfig = TimewarpConfig(...)`
  - `vault_dir: Path = Path("seeds")`
  - `seed_prefix: str = "empire"`
  - `kpi_enabled: bool = True`
  - `signature_enabled: bool = True`
  - `save_initial_snapshot: bool = True`

- `def evolve_seed(*, scenario_id: str, seed: int, cfg: EvolveConfig) -> dict`
  - Returns run summary: final seed_id, list of milestones, paths to outputs.

- `def evolve_from_snapshot(*, snapshot_path: Path, cfg: EvolveConfig) -> dict` (optional)

### A2. Milestone definition
Implement a simple milestone policy:

**Required milestones**
- Initial (tick 0 or after initialization)
- Every `save_every_days` (annual)
- Final

**Optional “eventful milestones”** (stubbed for later)
- phase transition boundaries
- KPI triggers (population collapse, water crisis, rebellion index, etc.)

---

## 3) Implementation Slice B — Outputs (timeline + reports)

### B1. Add directory layout for a run
For each harness run create:
- `runs/{run_id}/`
  - `timeline.jsonl` (one JSON object per milestone)
  - `timeline.csv` (optional convenience)
  - `config.json`
  - `notes.md` (optional; run summary)

`run_id` suggestion: `{scenario_id}__seed-{seed}__{YYYYMMDD-HHMMSS}`

### B2. Timeline row schema (stable + diffable)
Each milestone writes one row containing:

- `run_id`
- `scenario_id`
- `seed`
- `day`
- `year` (computed)
- `tick`
- `milestone_type` (initial/annual/final/trigger)
- `snapshot_path`
- `snapshot_sha256`
- `world_signature` (if enabled)
- `kpis` (small dict; see below)

---

## 4) Implementation Slice C — KPI + signature collection

### C1. Create module: `src/dosadi/testing/kpis.py` (or `dosadi/runtime/kpis.py`)
**Deliverables**
- `def collect_kpis(world) -> dict`

**Keep KPIs cheap and stable**, e.g.:
- `agents_total`, `agents_alive`
- `groups_total`
- `facilities_total`
- `protocols_total`
- `avg_hunger`, `avg_thirst`, `avg_fatigue` (or your canonical needs)
- `stocks_total` (if you have a canonical stock ledger)
- `day`, `year`
- `incidents_today` (optional if tracked)

### C2. Signature
Reuse the deterministic `world_signature(world)` from the snapshot/replay work (0231). If it lives elsewhere, import it.

---

## 5) Implementation Slice D — The evolution loop (how to drive the sim)

### D1. Acquire timebase constants
Use the runtime timebase (ticks/day = 144,000) from the world/timebase module (do not hardcode).
The repo already treats `ticks_per_day` as first-class. Ensure the harness does too.

### D2. Cruise vs Dip schedule
Pseudo-logic:

- `total_days_target = cfg.target_years * 365`
- Track `day_cursor`
- While `day_cursor < total_days_target`:
  - `step_day(world, days=cfg.cruise_days, cfg=cfg.timewarp_cfg)`  # cruise
  - `day_cursor += cfg.cruise_days`
  - If `day_cursor % cfg.microsim_every_days == 0`:
    - run tick-mode microsim for `cfg.microsim_days` worth of ticks:
      - `run_ticks(world, ticks=cfg.microsim_days * ticks_per_day)`
  - If `day_cursor % cfg.save_every_days == 0` (or on final):
    - snapshot + vault save + timeline row

**Important**
- Avoid global modulo checks on tick; this is a harness loop, so it’s fine to branch on day_cursor.
- Keep deterministic ordering for any random draws in macrosim.

---

## 6) Implementation Slice E — Tests for harness

Create `tests/test_evolve_harness.py`.

### E1. “Smoke evolve” test
- Run with tiny parameters:
  - `target_years=1`, `cruise_days=30`, `microsim_days=1`, `microsim_every_days=90`, `save_every_days=365`
- Assert:
  - output files exist
  - at least 2 milestones (initial + final, possibly annual)
  - snapshots load successfully
  - deterministic hashes exist

### E2. Determinism test
Run the harness twice with same config, compare:
- milestone snapshot hashes (or signatures) match for corresponding milestones.

Use small target_years to keep tests fast (1 year or less).

---

## 7) Optional: CLI entrypoint (nice-to-have)

If you have a CLI pattern, add:

- `dosadi evolve --scenario founding_wakeup --seed 7 --years 200 --out runs/`
- options for cruise/microsim cadences
- `--save-every-days` and `--microsim-every-days`

This can be added after tests are green.

---

## 8) “Codex Instructions” (verbatim)

### Task 1 — Add evolve harness module
- Create `src/dosadi/runtime/evolve.py`
- Implement `EvolveConfig`, `evolve_seed`, and milestone logic
- Use `step_day` from timewarp for cruise
- Use existing tick-mode stepping function for microsim dip
- Save snapshots via seed vault (0231)
- Write run outputs under `runs/{run_id}/` including `timeline.jsonl` and `config.json`

### Task 2 — Add KPI collection
- Create `src/dosadi/testing/kpis.py` (or runtime equivalent)
- Implement `collect_kpis(world)` with stable, cheap KPIs
- Reuse `world_signature(world)` from snapshot/replay work (0231)

### Task 3 — Add tests
- Create `tests/test_evolve_harness.py`
- Add smoke test (1-year)
- Add determinism test (repeat run, compare milestone hashes/signatures)

### Task 4 — Keep scope tight
- No new economy mechanics in this branch
- No new exploration mechanics in this branch
- This branch is about orchestrating existing systems into a repeatable pipeline

---

## 9) Definition of Done

- `pytest` passes.
- You can run `evolve_seed(scenario_id="founding_wakeup", seed=7, target_years=10)` and get:
  - snapshots stored in seed vault
  - a timeline file you can diff
- Running the same evolve config twice produces identical milestone hashes/signatures.
- Snapshots can be loaded and continued deterministically.

---

## 10) Next steps unlocked by this branch

Once the harness exists, you can:
- run “seed tournaments” (many seeds, pick most interesting KPI trajectories)
- add exploration/survey maps and construction projects, and observe their long-horizon effects
- validate phase transitions (Golden Age → Limits → Scarcity/Corruption) as emergent outcomes
