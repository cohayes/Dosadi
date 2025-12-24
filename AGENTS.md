# AGENTS.md — Codex Working Agreement (Dosadi)

This file is the **first stop** for Codex changes in this repository.

Purpose:
- Reduce repeated prompt/token overhead (Codex can rely on this file).
- Prevent recurring integration mistakes (determinism, save/load, performance).
- Provide a consistent “definition of done” for changes.

If any instruction in a task conflicts with this file, **the task wins**, but keep these rules unless explicitly told to break them.

---

## 1) Repo map (where things live)

Primary code:
- `src/dosadi/`
  - `runtime/` — macro-step, day pipeline, phase/incidents/router/beliefs/focus
  - `world/` — world state, logistics, survey map, routing, events/incidents/ledgers
  - `agent/` — agent model + memory (crumbs/episodes/stm/beliefs)
  - `scenarios/` — scenario definitions + verification (if present)
- `tests/` — pytest suite

Docs/specs:
- `docs/latest/` — design specs (e.g. `D-RUNTIME-xxxx`, `D-AGENT-xxxx`)
  - Specs guide implementation but are **not** executable code.

If unsure where a change belongs:
- **runtime** = “when it runs / orchestration”
- **world** = “what the state is / ledgers”
- **agent** = “per-agent state and memory”

---

## 2) Non-negotiable invariants

### 2.1 Determinism
- Same seed + same world state must produce identical results.
- Never use uncontrolled randomness. If randomness is required, derive RNG from stable inputs:
  - `(world_seed, day, tick, stable_ids...)`.
- Tie-breaks must be stable (lexicographic IDs, stable sorts).

### 2.2 Performance / scaling
- Avoid global scans in hot paths (per tick/day).
- Prefer bounded candidate sets, queues/heaps, and incremental updates.
- Use O(log K) structures for top-K retention (STM/beliefs).

### 2.3 Save/Load compatibility
- Any new state must be snapshot-serializable.
- New dataclass fields must have safe defaults so old snapshots load.
- Do not serialize caches (LRU/memoization) unless explicitly required.

### 2.4 Backwards compatibility
- If a change can alter behavior, add a **feature flag** defaulting to OFF.
- With the flag OFF, existing tests and baseline behavior must remain unchanged.

---

## 3) Canonical ordering (daily pipeline)

When adding a new daily system, wire it into the day pipeline in this order:

1) projects/logistics/facilities updates (bounded)
2) phase engine
3) incident engine
4) world events → memory router
5) belief formation
6) decision hooks (planner/logistics/staffing posture)

Focus Mode (if enabled) can interleave awake ticks with ambient substeps, but must:
- run the daily pipeline **exactly once per day** when day transitions occur,
- avoid accidental global scans.

---

## 4) Common patterns (use these)

### 4.1 Due-queue pattern (heaps)
- Use a heap for “next completion tick” items (deliveries, edge segments, etc.).
- Process due items up to a tick; do not tick-scan all items.

### 4.2 Memory model (cheap → rich)
- **Crumbs**: cheap counters/tags, decayable, O(1) update.
- **Episodes**: rarer, structured payloads, bounded.
- **STM**: “boring winner” bounded top-K (min-heap/buckets), no linear eviction scans.
- **Router**: routes events to bounded stakeholder sets (never broadcast to all agents in v1).
- Use `agents_with_new_signals` (or equivalent) to avoid daily scans for belief formation.

### 4.3 Pathfinding / routing
- Pathfinding happens at assignment time and on rare reroutes.
- Never do unbounded pathfinding per tick for the full world.
- Use deterministic tie-breaks for multiple equal-cost paths.

### 4.4 IDs and string keys
- Use stable IDs for world objects (`ward:12`, `node:7`, `delivery:xyz`).
- Use stable crumb/belief keys (e.g., `route-risk:{edge_key}`, `facility-down:{facility_id}`).
  - Curly-brace placeholders above are literal examples, not Python f-strings.

---

## 5) Testing requirements (Definition of Done)

For any behavioral change:
- Add/extend pytest tests in `tests/`.
- Include at least one **determinism** test (run twice, compare signatures).
- Include a **snapshot roundtrip** test if state/serialization changed.
- Ensure `pytest` passes locally.

If the change adds a new bounded structure (heap, top-K store, ring buffer):
- add a test proving **bounds** are respected (no growth without limit).

---

## 6) Safe defaults & signatures

- Prefer `.signature()` helpers for new ledgers/stores.
  - Use stable hashes of sorted IDs + key fields.
- Never rely on dict iteration order for behavior.
- When adding config fields:
  - give them defaults,
  - keep them on a config dataclass on `world` when possible,
  - avoid hardcoding constants in multiple places.

---

## 7) Codex task approach (checklist)

1) Locate relevant module(s) using the Repo map.
2) Implement minimal v1 behavior behind a feature flag if risky.
3) Wire into canonical runtime ordering.
4) Add serialization hooks if stateful.
5) Add tests: determinism + bounds + snapshot roundtrip (when applicable).
6) Run pytest; keep diffs focused and readable.
7) Prefer small, composable helpers over large monolith functions.

---

## 8) Don’ts (common failure modes)

- Do not add per-tick full-world loops.
- Do not broadcast events to all agents.
- Do not introduce nondeterministic iteration or RNG calls.
- Do not break old snapshots without a migration plan.
- Do not “just add a list” without bounding it and testing bounds.

---

Last updated: 2025-12-24
