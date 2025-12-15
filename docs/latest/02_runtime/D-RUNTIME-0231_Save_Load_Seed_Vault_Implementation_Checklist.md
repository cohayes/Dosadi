---
title: Save_Load_Seed_Vault_Implementation_Checklist
doc_id: D-RUNTIME-0231
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-15
depends_on:
  - D-RUNTIME-0230   # Cadence_Contract
  - D-RUNTIME-0001   # Simulation_Timebase
  - D-AGENT-0020     # Agent model
---

# Save/Load + Seed Vault + Deterministic Replay — Implementation Checklist

Branch name: `feature/save-load-seed-vault`

Goal: enable **WorldSnapshot v1** (save/load), **Seed Vault** (catalog evolved worlds), and a **deterministic replay harness** (tests) so long-running evolution (e.g., “200-year empires”) becomes feasible and refactors become safe.

This document is designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **RNG state is persisted.** Save both `seed` and *the RNG internal state* (e.g., `random.Random.getstate()`).
2. **Stable ordering rules exist.** Avoid “dict iteration order by accident” for any step that impacts randomness or outcomes.
3. **Snapshot roundtrip tests exist.** `(N ticks + save + load + M ticks) == (N+M ticks)` for deterministic hashes + key KPIs.
4. **JSON first, optimize later.** Start with canonical JSON (+ optional gzip). Only switch formats after replay tests exist.

---

## 1) Slice A — WorldSnapshot v1 (roundtrip save/load)

### A1. Create module: `src/dosadi/runtime/snapshot.py`
**Deliverables**
- `SNAPSHOT_SCHEMA_VERSION = "world_snapshot_v1"`
- `@dataclass(slots=True) class WorldSnapshotV1: ...`
- `def snapshot_world(world, *, scenario_id: str) -> WorldSnapshotV1`
- `def restore_world(snapshot: WorldSnapshotV1) -> WorldState`
- `def save_snapshot(snapshot: WorldSnapshotV1, path: Path, *, gzip: bool = True) -> str  # returns sha256`
- `def load_snapshot(path: Path) -> WorldSnapshotV1`

**Required fields (v1)**
- `schema_version: str`
- `scenario_id: str`
- `seed: int`
- `tick: int`
- `rng_state: object` (serialize `world.rng.getstate()` to JSON-safe form)
- `world: dict` (serialized world state; see “A2”)

**Optional (v1, but plan for v2)**
- `event_queue: dict | None` (only if you already have a bus/queue worth persisting)

### A2. Define the v1 serialization boundary (keep it minimal)
Start by supporting only what your “Founding Wakeup / Wakeup Prime” paths require.

**World state buckets to serialize (typical)**
- `world.meta` / `world.config` minimal: `ticks_per_minute/hour/day` if present, else derived
- `wards/topology` (if present in world)
- `agents` (agent state)
- `groups` / factions (if present)
- `protocols/queues/facilities` (only those instantiated in scenarios)
- `metrics` needed for `verify_scenario(...)`

**Strategy**
- Implement per-type helpers:
  - `to_snapshot_dict(obj) -> dict`
  - `from_snapshot_dict(d: dict) -> obj`
- Keep these in the same module initially to reduce churn; refactor into `dosadi/state/serde/*.py` later.

### A3. Canonical JSON rules (for deterministic hashing)
Implement a canonical encoder:
- Sort dict keys on dump
- Use stable list ordering:
  - For lists of entities that have ids, sort by `.id` (or by `id` field)
- Avoid serializing derived/transient caches.

### A4. RNG state serialization
Python `random.Random.getstate()` returns a tuple. JSON can’t represent tuples cleanly without conversion.
Implement:
- `def rng_state_to_jsonable(state) -> list|dict`
- `def rng_state_from_jsonable(x) -> state_tuple`

Store:
- `seed` (int)
- `rng_state_json` (converted)

On restore:
- `world.rng = random.Random()` then `world.rng.setstate(...)`

### A5. Determinism guardrails (minimal)
In any update loop where order could matter (and likely does), iterate stably:
- `for agent_id in sorted(world.agents): agent = world.agents[agent_id]`

Only apply this where it could influence outcomes (agent step ordering, event ordering, facility service ordering).

---

## 2) Slice B — Seed Vault (catalog evolved worlds)

### B1. Create package: `src/dosadi/vault/seed_vault.py`
**Folder layout**
- `seeds/`
  - `manifest.json`
  - `snapshots/`
    - `{seed_id}.json.gz`

**API**
- `def list_seeds(vault_dir: Path) -> list[dict]`
- `def load_manifest(vault_dir: Path) -> dict`
- `def write_manifest(vault_dir: Path, manifest: dict) -> None`
- `def save_seed(vault_dir: Path, world, *, seed_id: str, scenario_id: str, meta: dict | None = None) -> dict`
- `def load_seed(vault_dir: Path, *, seed_id: str) -> WorldState`

**Manifest entry shape**
- `seed_id: str`
- `scenario_id: str`
- `parent_seed_id: str | None`
- `created_tick: int`
- `elapsed_ticks: int`
- `snapshot_path: str`
- `snapshot_sha256: str`
- `kpis: dict` (lightweight summary, stable fields)

**KPIs (suggested minimal)**
- `agents_total`
- `groups_total`
- `protocols_total`
- `facilities_total`
- `water_total` (if applicable)
- `ward_count`
- `day` (tick // ticks_per_day)

> KPI fields should be safe to compute without scanning deeply; keep it cheap.

### B2. Add scenario helpers (optional but useful)
- `run_scenario(..., overrides=..., save_seed_at_tick=..., seed_id=...)` (optional)
- OR keep vault usage external (CLI/test only) for v1 to minimize changes.

---

## 3) Slice C — Deterministic replay harness (tests)

Create tests under `tests/test_snapshot_replay.py` (or similar).

### C1. Snapshot equivalence test
**Test name**
- `test_snapshot_roundtrip_replay_equivalence()`

**Procedure**
1. Run scenario with fixed seed:
   - `world0 = run_scenario(..., overrides={"seed": 7})` (or equivalent)
2. Step `N` ticks.
3. Snapshot at tick `T=N`.
4. Restore into `worldA`.
5. Step `M` ticks.
6. Separately: start fresh, run `N+M` ticks → `worldB`.
7. Compare:
   - `hashA == hashB`
   - plus a handful of KPIs equality (counts, protocol adoption stats, etc.)

### C2. Seed vault roundtrip test
**Test name**
- `test_seed_vault_save_load_roundtrip()`

**Procedure**
1. Save seed after N ticks.
2. Load seed into a new world.
3. Confirm snapshot hash matches.
4. Step a few ticks and confirm deterministic hash matches a “continued” run.

### C3. Hash function (deterministic state signature)
Implement `def world_signature(world) -> str` in `snapshot.py` or `dosadi/testing/signatures.py`:
- Create a canonical dict of selected stable fields:
  - tick
  - agents: (id, location, top goal id, key needs, key beliefs summary counts)
  - queue lengths
  - protocol adoption levels
- Serialize with canonical JSON and hash via `sha256`.

> Keep the signature small and stable. Do not include timestamps, memory addresses, or nondeterministic ordering.

---

## 4) Optional (nice-to-have) — CLI hooks

If you already have a CLI entrypoint pattern, add minimal commands:

- `dosadi snapshot save --scenario founding_wakeup --seed 7 --tick 6000 --out seeds/snapshots/foo.json.gz`
- `dosadi snapshot load --in seeds/snapshots/foo.json.gz --run-ticks 6000`
- `dosadi vault list`
- `dosadi vault save --seed-id empire_0007`
- `dosadi vault load --seed-id empire_0007`

This can come after tests are green.

---

## 5) Implementation order (recommended)

1. Implement **WorldSnapshotV1** + JSON save/load + RNG state.
2. Add **world_signature** helper.
3. Add **snapshot equivalence test** (must pass).
4. Add **Seed Vault** manifest + save/load.
5. Add **seed vault test** (must pass).
6. Add minimal determinism guardrails in agent step ordering if tests reveal drift.

---

## 6) “Codex Instructions” (verbatim)

### Task 1 — Add snapshot module
- Create `src/dosadi/runtime/snapshot.py`
- Implement `WorldSnapshotV1` + `snapshot_world`, `restore_world`, `save_snapshot`, `load_snapshot`
- Persist seed + RNG state; restore RNG deterministically
- Canonical JSON dump (sorted keys), stable ordering for entity lists

### Task 2 — Add seed vault module
- Create `src/dosadi/vault/seed_vault.py`
- Create `seeds/manifest.json` if missing (initialize to `{"schema":"seed_vault_v1","seeds":[]}`)
- Implement `save_seed`, `load_seed`, `list_seeds`
- Save snapshots under `seeds/snapshots/{seed_id}.json.gz`
- Store sha256 + KPIs in manifest

### Task 3 — Add deterministic tests
- Create `tests/test_snapshot_replay.py`
- Implement:
  - `test_snapshot_roundtrip_replay_equivalence`
  - `test_seed_vault_save_load_roundtrip`
- Add helper `world_signature(world)` that hashes a canonical subset of state
- If tests fail due to ordering nondeterminism:
  - enforce stable iteration ordering in the critical step loops (agents, facilities, queues)
  - ensure any random draws occur in the same order

### Task 4 — Keep the change-set minimal
- Prefer adding new modules + light glue over refactoring unrelated systems
- Expand serialization coverage incrementally:
  - Start with minimal fields required by Founding Wakeup / Wakeup Prime
  - Add missing pieces only when tests fail

---

## 7) Definition of Done

- `pytest` passes locally.
- Can:
  - run a scenario → step N ticks → save snapshot
  - load snapshot → step M ticks
  - compare signature with straight-through run of N+M ticks (equal)
- Can save/load seed entries via seed vault.

---

## 8) Next steps unlocked by this branch

Once this lands, you can safely implement:
- fast-forward “day/week step” modes
- scouting/survey maps
- construction projects
- economy loops

…because you’ll have replay regression to keep long-horizon evolution stable and debuggable.
