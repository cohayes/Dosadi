---
title: Deterministic_RNG_Service_v1
doc_id: D-RUNTIME-0314
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-28
depends_on:
  - D-RUNTIME-0233   # Evolve Seeds Harness
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0313   # World Event Bus & Subscriptions
---

# D-RUNTIME-0314 — Deterministic RNG Service v1 (Implementation Checklist)

## Intent

Make *all randomness* in Dosadi:
- **Deterministic** given `(seed, scenario_id, time, object_id, stream_key, call_index)`.
- **Auditable** (we can answer: “what random stream caused this?”).
- **Stable under refactors** (reordering unrelated systems doesn’t silently change results).
- **Cheap enough** to use everywhere (including hot loops).

This is a foundational move for:
- “Evolve seeds for 200 years, persist winners, replay deterministically.”
- Debugging failures / regressions (“the corridor collapsed because stream X drifted”).
- Long-run CI tests (seed vault + reproducibility).

---

## Design constraints

**Hard requirements**
- No global `random.random()` calls in runtime / world logic (except inside the RNG service).
- Named streams (string keys) with *explicit domain scope*.
- Deterministic derivation must be pure and stable across Python versions (avoid `hash()`).

**Soft requirements**
- Minimal changes to existing code: provide adapters that accept `rng=` optional param.
- Optional telemetry: count draws per stream and expose top offenders.

---

## Terminology

- **Root seed**: scenario/world seed.
- **Stream key**: stable string like `"incident:delivery_loss"`, `"scout:hazard_roll"`.
- **Scope tuple**: additional stable “namespacing” pieces like `day`, `tick`, `ward_id`, `agent_id`.
- **Draw index**: incrementing counter per (stream, scope).

---

## Proposed API

### 1) RNGService

Create `src/dosadi/runtime/rng_service.py`:

- `class RNGConfig`:
  - `enabled: bool = True`
  - `salt: str = "rng-v1"`
  - `audit_enabled: bool = True`
  - `max_audit_streams: int = 256`  (top streams to retain)
  - `warn_on_global_random: bool = False` (optional; see “lint” section)

- `class RNGService` (world-owned):
  - `seed: int`
  - `config: RNGConfig`
  - `counters: dict[str, int]`  (keyed by derived stream_id; optionally capped)
  - `audit: dict[str, dict]` (optional summary; counts + last_scope signature)

Methods:
- `stream(stream_key: str, *, scope: dict[str, object] | None = None) -> random.Random`
  - Returns a **fresh** `random.Random` whose seed is derived from:
    - `root_seed`, `salt`, `stream_key`, and a *canonicalized scope*.
  - A fresh RNG avoids state bleed across call sites.
  - Use in code that needs a handful of draws.

- `rand(stream_key: str, *, scope: dict[str, object] | None = None) -> float`
- `randint(stream_key: str, a: int, b: int, *, scope: dict[str, object] | None = None) -> int`
- `choice(stream_key: str, seq: Sequence[T], *, scope: dict[str, object] | None = None) -> T`
  - Stateless convenience wrappers that internally:
    - compute derived seed
    - increment counter for that derived stream_id
    - perform the draw deterministically

- `signature() -> str`
  - Deterministic string digest of current counters (for snapshot/regression tests).

### 2) World integration

- Add `world.rng_service_cfg: RNGConfig` and `world.rng_service: RNGService`.
- Add `ensure_rng_service(world) -> RNGService` helper.

### 3) Derivation function

Implement a stable integer seed derivation:
- Canonicalize scope:
  - Only allow JSON-serializable primitives.
  - Sort keys.
  - Convert tuples -> lists.
- Build a string:
  - `f"{salt}|{root_seed}|{stream_key}|{scope_json}|{draw_index}"`
- Hash using `sha256` and convert first 8 bytes to uint64.
- Convert to Python int and seed `random.Random(int_seed)`.

**Why include draw_index?**
- To allow repeated draws within the same stream+scope without reusing identical outputs.
- But we include it by incrementing a counter per “stream_id”.

**Stream ID definition**
- `stream_id = sha256(f"{salt}|{root_seed}|{stream_key}|{scope_json}".encode()).hexdigest()[:16]`
- Use stream_id as the key for counters/audit.

---

## Usage patterns

### Pattern A: One-off deterministic roll

```py
rng = ensure_rng_service(world)
loss_roll = rng.rand("incident:delivery_loss", scope={"day": day, "delivery_id": delivery_id})
```

### Pattern B: Deterministic sampling with bounded candidates

```py
rng = ensure_rng_service(world)
picked = rng.choice("scout:candidate_pick", candidates, scope={"tick": tick, "ward_id": ward_id})
```

### Pattern C: Injected RNG for legacy functions

Keep existing signatures:
- `def foo(..., rng: random.Random | None = None):`

Call sites do:
- `rng = rng or ensure_rng_service(world).stream("foo:legacy", scope={...})`

---

## Migration plan

### Step 1 — Add RNGService + tests

Create:
- `src/dosadi/runtime/rng_service.py`
- `tests/test_rng_service_v1.py`

Test cases:
- Determinism: same (seed, stream_key, scope, call_count) ⇒ same output.
- Stability: scope key order doesn’t matter.
- Independence: different stream_key yields different sequences.
- Counter increments: calling `rand()` twice changes draw_index behavior.
- Snapshot: `signature()` stable under deep copy / snapshot/restore (if applicable).

### Step 2 — Replace obvious global randomness

Search and replace hot call sites first:
- incidents scheduling / severity rolls
- scout sampling
- construction site scoring randomness
- warfare deterministic_roll wrappers
- focus mode agent selection randomness

Codex instruction: do this in small PRs, each with tests.

### Step 3 — Optional “random lint” guardrail

Add a *development-only* hook:
- In `dosadi/runtime/config.py` or a debug module:
  - If `world.debug_cfg.level == "strict"` and `warn_on_global_random`, monkeypatch `random.random` / `randint` to raise.
- Keep off by default.

---

## Telemetry & admin views (optional but valuable)

Expose:
- Top-N streams by draw count in Admin Dashboard / Telemetry view.
- Include `stream_key` (or a stored `stream_id -> stream_key` mapping) + counts.

This makes performance hotspots obvious:
- e.g., “incident:delivery_loss” drawing 10M times per run.

---

## Success criteria

- ✅ New service exists and is used in at least **2** major systems (incidents + scouting).
- ✅ Determinism tests pass and are stable across re-runs.
- ✅ Snapshot/replay of a short scenario matches event signatures.
- ✅ No remaining `random.` calls in key runtime paths without explicit justification.

---

## Codex implementation instructions

1) Create `src/dosadi/runtime/rng_service.py` implementing `RNGConfig`, `RNGService`, `ensure_rng_service`.
2) Wire into `WorldState` (add fields, initialize lazily via `ensure_rng_service`).
3) Add tests in `tests/test_rng_service_v1.py` as described.
4) Migrate at least:
   - `src/dosadi/runtime/incidents.py` (or wherever incident RNG exists)
   - `src/dosadi/world/scouting.py` (or scout missions)
   to use `ensure_rng_service(world)` calls.
5) Add a minimal telemetry getter: `rng_service.audit_summary()` that returns a sorted list of (stream_key_or_id, count).
6) Ensure all changes are deterministic and do not introduce non-JSON payloads in scope canonicalization.
