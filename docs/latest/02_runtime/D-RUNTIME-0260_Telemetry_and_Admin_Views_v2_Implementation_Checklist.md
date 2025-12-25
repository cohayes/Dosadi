---
title: Telemetry_and_Admin_Views_v2_Implementation_Checklist
doc_id: D-RUNTIME-0260
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0231   # Save/Load Seed Vault
  - D-RUNTIME-0232   # Timewarp MacroStep
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0243   # Event → Memory Router v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0253   # Maintenance & Wear v1
  - D-RUNTIME-0254   # Suit Wear & Repair v1
  - D-RUNTIME-0255   # Exploration & Discovery v1
  - D-RUNTIME-0256   # Resource Extraction Sites v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0259   # Expansion Planner v2
---

# Telemetry & Admin Views v2 — Implementation Checklist

Branch name: `feature/telemetry-admin-v2`

Goal: make the sim *self-explaining* during runs by adding a cohesive “debug cockpit” that answers:
- Where are we stuck?
- What is scarce?
- What is producing value?
- Where is risk/attrition coming from?
- Why did the planner choose that?

This slice is intentionally UI-light: mostly CLI panels and compact summaries,
but wired to the same telemetry/event stream you’ll later power richer dashboards with.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Low overhead.** Telemetry must be cheap: counters, top-Ks, ring buffers; no big logs by default.
2. **Deterministic reporting.** Display order and aggregation must be stable.
3. **Feature flag / verbosity.** Optional “debug verbosity” levels; default minimal.
4. **Tested.** Panels render and key metrics are present; no regressions.
5. **No global scans.** Panels should read pre-aggregated structures.

---

## 1) Telemetry backbone (if not already centralized)

Create/extend `src/dosadi/runtime/telemetry.py`:

### 1.1 Metrics registry
- `class Metrics:`
  - `counters: dict[str,int]`
  - `gauges: dict[str,float|int|str]`
  - `topk: dict[str, TopK]` (small structure)
  - `def inc(path, n=1)`
  - `def set_gauge(path, value)`
  - `def topk_add(path, key, score, payload=None)`
  - `def snapshot_signature() -> str`

TopK structure:
- bounded size K (e.g., 10)
- deterministic tie-breaks (score desc, key asc)

### 1.2 Event ring buffer (debug)
- `class EventRing:`
  - stores last N events (N default 200)
  - event = {"t": day_or_tick, "type": str, "payload": dict}
  - deterministic ordering as appended

World stores:
- `world.metrics: Metrics`
- `world.event_ring: EventRing` (optional by verbosity)

Snapshots:
- metrics can be non-snapshotted (derived), BUT for debugging determinism it’s useful to snapshot gauges/counters minimally.
Recommendation v2: snapshot gauges/counters only if already doing so; otherwise keep ephemeral and test via runtime outputs.

---

## 2) New Admin CLI panels (v2)

You already have AdminDashboardCLI / ScenarioTimelineCLI. Add a **Debug Cockpit** view.

Create `src/dosadi/ui/debug_cockpit.py` (or integrate into existing CLI module).

Provide:
- `DebugCockpitCLI(width=100).render(world, *, ward_id=None)`

### Panel A — Executive Summary
- Day, phase, population awake/ambient counts (if tracked)
- Total depots, workshops, active projects, active deliveries, active scouts
- Global shortages count (from stockpile policy shortfalls)

### Panel B — “Where are we stuck?”
Top blocked projects (top 10):
- project_id, node/ward, stage, stage_state
- block_reason code + short details (top missing material)
- pending deliveries count

Source: Construction Pipeline v2 state (use TopK aggregation if many).

### Panel C — “What is scarce?”
Top shortages (top 10):
- material, deficit, affected depot/project count

Source: stockpile policy shortage telemetry + pipeline missing materials TopK.

### Panel D — “What is producing value?”
Top extraction sites by units/day (top 10):
- site_id, kind, node, last_yield_units, pending pickup status

### Panel E — “Logistics health”
- deliveries requested today / completed
- active couriers count
- average delivery latency (if tracked)
- top stalled deliveries (age, reason)

### Panel F — “Wear & attrition”
- suits: % below warn / repair / critical
- repairs started today / completed
- maintenance downtime count for facilities

### Panel G — “Planner motives”
- last chosen v2 planner action(s)
- score breakdown terms (short)
- cooldown status

### Panel H — Recent key events (optional)
- last 10 events from EventRing:
  - DISCOVERY_*, EXTRACTION_*, STOCKPILE_*, PROJECT_*, SUIT_*, PLANNER_*

All panels must render deterministically.

---

## 3) Aggregation hooks (avoid scans)

Add small aggregation points where events occur:

### Construction pipeline v2
- on stage blocked: `metrics.topk_add("projects.blocked", project_id, severity, payload={...})`
- gauge: `projects.blocked_count`

### Stockpile policy v1
- on shortage: `metrics.topk_add("stockpile.shortages", f"{material}:{depot}", severity, payload={...})`
- counters: deliveries requested/completed

### Extraction v1
- on yield: `metrics.topk_add("extraction.top_sites", site_id, units, payload={...})`
- gauge: `extraction.units_today`

### Suit wear/repair v1
- gauges: percent below thresholds
- counters: repairs needed/started/done

### Planner v2
- store last action payload into `metrics.gauges["planner_v2.last_action_json"]` (or in planner state)
- `topk_add("planner_v2.candidates", ...)` optional for debugging

---

## 4) Verbosity levels

Add a runtime config:
- `world.debug_cfg = DebugConfig(level="minimal"|"standard"|"verbose")`

Minimal:
- no event ring
- only counters/gauges
Standard:
- event ring on
Verbose:
- include topk payload details, and include per-ward breakdowns (bounded)

---

## 5) Tests (must-have)

Create `tests/test_debug_cockpit_cli.py`.

### T1. Renders without error
- create small world; run a few days; call render; ensure returns non-empty string.

### T2. Contains key headings
- verify string contains sections: "Where are we stuck", "What is scarce", "Planner motives"

### T3. Deterministic output
- clone world; run; render; outputs identical.

### T4. No global scans regression (optional)
- if you have a scan counter, ensure render does not trigger model-wide iteration beyond allowed.
If not, at least ensure render uses pre-aggregated telemetry where possible.

---

## 6) Codex Instructions (verbatim)

### Task 1 — Telemetry helpers
- Ensure a centralized Metrics registry supports counters, gauges, and deterministic TopK
- Add optional EventRing buffer gated by debug verbosity

### Task 2 — Add DebugCockpitCLI
- Implement panels A–G (and H if ring enabled)
- Keep output deterministic (stable ordering, bounded lists)

### Task 3 — Wire aggregation hooks
- Add topK/counter updates in: construction pipeline, stockpile policy, extraction runtime, suit wear/repair, planner v2

### Task 4 — Tests
- Add `tests/test_debug_cockpit_cli.py` (T1–T3 minimum)
- Ensure rendering is deterministic and stable

---

## 7) Definition of Done

- `pytest` passes.
- Running a scenario prints a useful cockpit view showing:
  - blocked projects + reasons,
  - shortages,
  - top extraction sites,
  - suit attrition,
  - last planner motive/action,
  - logistics health.
- Overhead remains low and bounded.

---

## 8) Next slice after this

**Corridor Risk & Escort Policy v2** (close the loop: risky corridors → escorts → fewer incidents),
or **Resource Refining Recipes v2** (turn raw scrap into higher-tier parts).
