---
title: Economy_Market_Signals_v1_Implementation_Checklist
doc_id: D-RUNTIME-0263
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0259   # Expansion Planner v2
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0262   # Resource Refining Recipes v2
---

# Economy Market Signals v1 — Implementation Checklist

Branch name: `feature/economy-market-signals-v1`

Goal: add a lightweight “market” layer without building a full economy simulator:
- compute **urgency / pseudo-price** signals per material (global + per-ward),
- let systems (production, depots, planner, agents) use those signals to prioritize actions,
- keep it deterministic, bounded, and explainable,
- feed into beliefs (“FASTENERS are scarce; sealant is precious”).

This is not money. It’s a control signal.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic signals.** Same state → same prices/urgencies.
2. **Bounded compute.** No full-world inventory sums if avoidable; use pre-aggregated stats.
3. **Stable and damped.** Signals should not whipsaw day-to-day; use EMA smoothing.
4. **Feature-flagged.** v1 signals behind config; consumers can ignore.
5. **Tested.** Simple scenarios map to correct ordering of urgency.

---

## 1) Concept model

We define a “market signal” for each material:
- `urgency` in [0, 1] (or [0, 100])
- higher urgency = “produce/transport/build this first”

Signals can exist at two scopes:
- **global**: overall scarcity
- **ward** (optional v1): local scarcity (ward-specific shortages)

In v1, global is sufficient; ward can be a bounded extension.

---

## 2) Implementation Slice A — Data structures

Create `src/dosadi/runtime/market_signals.py`

**Deliverables**
- `@dataclass(slots=True) class MarketSignalsConfig:`
  - `enabled: bool = False`
  - `materials: list[str] = ["SCRAP_METAL","PLASTICS","FASTENERS","SEALANT","FABRIC","FILTER_MEDIA","GASKETS"]`
  - `ema_alpha: float = 0.2`                 # smoothing
  - `urgency_floor: float = 0.05`
  - `urgency_ceiling: float = 0.95`
  - `max_materials_tracked: int = 64`
  - `ward_signals_enabled: bool = False`
  - `max_wards_tracked: int = 12`            # bound
  - `deterministic_salt: str = "market-v1"`

- `@dataclass(slots=True) class MaterialMarketSignal:`
  - `material: str`
  - `urgency: float = 0.0`
  - `demand_score: float = 0.0`
  - `supply_score: float = 0.0`
  - `last_updated_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class MarketSignalsState:`
  - `last_run_day: int = -1`
  - `global_signals: dict[str, MaterialMarketSignal] = field(default_factory=dict)`
  - `ward_signals: dict[str, dict[str, MaterialMarketSignal]] = field(default_factory=dict)`  # ward->material->signal

Add to world:
- `world.market_cfg`, `world.market_state`

Snapshot them.

---

## 3) Implementation Slice B — Demand and supply scoring (bounded)

We avoid full inventory sums. v1 demand/supply sources:

### Demand sources
- blocked construction stages missing materials (from pipeline v2)
  - demand += missing_qty * weight
- depot deficits (target - current) for tracked depots (from stockpile policy)
  - demand += deficit * weight
- maintenance/repair requests missing materials (if tracked)
  - demand += qty * weight

### Supply sources
- production capacity / recent outputs (from production runtime v2)
  - supply += recent_output_qty
- extraction yields for relevant raw inputs (optional)
- depot surpluses above max (optional)

Because these may already be exposed as TopK or counters, prefer those:
- `metrics.topk["stockpile.shortages"]`
- `metrics.topk["projects.blocked"]` with payload missing materials
- `metrics["production"]["outputs"][material]`

If telemetry isn’t sufficient yet, compute in bounded loops over:
- top blocked projects (top 25)
- top depots (top 25)
- producer facilities (bounded)

---

## 4) Implementation Slice C — Urgency formula + smoothing

For each material, compute a raw signal:
- `raw = demand / (supply + epsilon)`

Then map to [0,1]:
- `u_raw = raw / (raw + 1)`  (monotone squashing)

Then apply EMA:
- `u = alpha*u_raw + (1-alpha)*u_prev`

Clamp to [urgency_floor, urgency_ceiling].

Tie-break deterministically if needed.

Ward signals (optional v1):
- same logic but demand/supply only from that ward (bounded wards).

---

## 5) Implementation Slice D — Daily runner

Implement:
- `def run_market_signals_for_day(world, *, day: int) -> None`

Steps:
1. If not enabled: return.
2. Build bounded demand/supply dicts from sources.
3. For each tracked material:
   - update signal record (create if missing)
4. Emit events:
   - `MARKET_SIGNAL_UPDATED` for top changes
5. Update metrics:
   - TopK of highest urgency materials

---

## 6) Consumers (integration points)

Minimal v1 consumers:
- **Production recipe choice** (0262): weight needed materials by urgency
- **Stockpile policy** (0257): prioritize high-urgency pull requests if delivery caps hit
- **Expansion planner v2** (0259): incorporate urgency into scoring terms
- **Belief formation** (0244): generate belief seeds like “SEALANT scarce” if urgency high for N days

Consumer contract:
- If market signals disabled, behave as before (fallback to existing heuristics).

---

## 7) Telemetry + Admin display

Add to DebugCockpit:
- Top 10 urgent materials:
  - material, urgency, demand_score, supply_score

Metrics:
- `metrics.topk_add("market.urgent", material, urgency, payload={demand,supply})`
- `metrics["market"]["updates"] += 1`

---

## 8) Tests (must-have)

Create `tests/test_market_signals_v1.py`.

### T1. Deterministic update
- clone world; run; signals identical.

### T2. Demand raises urgency
- add blocked project missing FASTENERS; urgency for FASTENERS increases.

### T3. Supply lowers urgency
- add production outputs for FASTENERS; urgency decreases or rises less.

### T4. Smoothing prevents whipsaw
- alternate demand spikes; urgency changes gradually.

### T5. Consumer usage (smoke)
- with enabled=True, production recipe choice prefers high urgency output.

### T6. Snapshot roundtrip
- save after updates; load; continue; stable.

---

## 9) Codex Instructions (verbatim)

### Task 1 — Add market signals module + world state
- Create `src/dosadi/runtime/market_signals.py` with config/state and signal records
- Add world.market_cfg/world.market_state to snapshots

### Task 2 — Implement bounded demand/supply scoring
- derive demand from blocked projects + depot deficits (bounded)
- derive supply from recent production outputs (bounded)

### Task 3 — Urgency formula + daily runner
- compute raw demand/(supply+eps), squash to [0,1], apply EMA smoothing
- emit telemetry TopK for urgent materials

### Task 4 — Wire consumers
- production recipe choice uses urgency as weight
- stockpile policy uses urgency to prioritize under caps
- planner v2 adds urgency to scoring terms
- belief formation seeds “scarce material” beliefs

### Task 5 — Tests
- Add `tests/test_market_signals_v1.py` implementing T1–T6

---

## 10) Definition of Done

- `pytest` passes.
- With enabled=True:
  - urgency signals update daily deterministically,
  - top urgent materials appear in cockpit,
  - production and depot pulls respond to urgency under caps,
  - signals are smoothed and stable,
  - save/load works.

---

## 11) Next slice after this

**Faction Interference v1** (theft/sabotage targeting valuable routes and depots) —
now that we can measure “value” and “risk,” we can simulate predation.
