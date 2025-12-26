---
title: Law_and_Enforcement_v1_Implementation_Checklist
doc_id: D-RUNTIME-0265
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0231   # Save/Load Seed Vault
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0249   # Local Interactions v1
  - D-RUNTIME-0250   # Escort Protocols v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0264   # Faction Interference v1
---

# Law & Enforcement v1 — Implementation Checklist

Branch name: `feature/law-enforcement-v1`

Goal: add a bounded, deterministic **ward security** loop that can *counterplay existential predation*.
This is intentionally “institution-hybrid”:
- **system-driven budgets/policies** per ward (cheap, scalable),
- optional hooks to “personify later” (marshal/captain agents) without needing that now.

This slice should make corridors survivable by:
- raising interdiction probability,
- increasing escort effectiveness,
- enabling checkpoints/patrol coverage,
- creating penalties that deter repeated predation (later: factions respond).

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same enforcement actions/effects.
2. **Bounded compute.** Update only wards with traffic/incidents; avoid scanning all edges daily.
3. **Counterplay is real.** With sufficient security investment, corridors can be stabilized.
4. **Configurable.** Phase-based default budgets; D3 harshness assumes low budgets collapse corridors.
5. **Save/Load safe.** Ward security state persists; old snapshots load.
6. **Tested.** Mitigation works, caps respected, snapshot roundtrip.

---

## 1) Concept model

We define a ward-level “security posture” that influences:
- interference event probability/severity (0264),
- corridor risk decay vs escalation (0261),
- escort availability and success (0250 / 0261),
- agent-level interactions locally (0249) (optional v1: arrests/confiscation as incidents).

Key idea: predation is “an ecosystem pressure.” If enforcement is too weak, risk rises faster than it decays,
and throughput collapses. If enforcement is sufficient, risk can be pushed back down.

---

## 2) Data structures

Create `src/dosadi/runtime/law_enforcement.py`

### 2.1 Config
- `@dataclass(slots=True) class EnforcementConfig:`
  - `enabled: bool = False`
  - `phase_budget_multiplier: dict[str,float] = {"P0":0.4,"P1":1.0,"P2":1.4}`
  - `max_patrols_per_ward: int = 12`
  - `max_checkpoints_per_ward: int = 6`
  - `traffic_lookback_days: int = 7`
  - `incident_lookback_days: int = 14`
  - `base_interdiction_prob: float = 0.05`
  - `patrol_interdiction_bonus: float = 0.03`      # per patrol on edge (cap)
  - `checkpoint_interdiction_bonus: float = 0.06`  # per checkpoint on edge (cap)
  - `escort_synergy_bonus: float = 0.10`           # multiplier on escort mitigation
  - `max_interdiction_prob: float = 0.85`
  - `risk_suppression_per_day: float = 0.03`       # security pushes risk down on protected edges
  - `deterministic_salt: str = "enforcement-v1"`

### 2.2 Ward policy/state (system-driven core)
- `@dataclass(slots=True) class WardSecurityPolicy:`
  - `ward_id: str`
  - `budget_points: float = 10.0`          # abstract budget, not money
  - `posture: str = "balanced"`            # "balanced"|"patrol-heavy"|"checkpoint-heavy"
  - `priority_edges: list[str] = field(default_factory=list)`  # edge_keys, bounded
  - `notes: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class WardSecurityState:`
  - `ward_id: str`
  - `patrol_edges: dict[str,int] = field(default_factory=dict)`       # edge_key -> patrol count
  - `checkpoints: dict[str,int] = field(default_factory=dict)`        # edge_key -> checkpoint count
  - `last_updated_day: int = -1`
  - `events_today: int = 0`

World stores:
- `world.enf_cfg`
- `world.enf_policy_by_ward: dict[str, WardSecurityPolicy]`
- `world.enf_state_by_ward: dict[str, WardSecurityState]`

Snapshot them.

**Bounded rule:** never store more than:
- `max_patrols_per_ward` total patrols (sum counts)
- `max_checkpoints_per_ward` total checkpoints

---

## 3) Deterministic selection (no RNG)

Use stable hash-based pseudo-random like 0264:
- `pseudo_rand01(f"{salt}|day:{day}|ward:{ward_id}|edge:{edge_key}|slot:{k}")`

But prefer deterministic ranking rather than random:
- patrol/ checkpoint placement based on traffic + risk + value.

---

## 4) Inputs (signals) to security planning (bounded)

Per ward, assemble a bounded view:
- Top risky edges intersecting this ward (from 0261 TopK)
- Top traffic edges (from logistics telemetry; if missing, infer from deliveries completed)
- Recent interference hits in ward (0264 recent events)
- Market urgency for materials flowing through (0263), optional v1

Keep it capped:
- at most 20 edges considered per ward per day.

---

## 5) Security planning loop (daily)

Implement:
- `def run_enforcement_for_day(world, *, day: int) -> None`

For each “active ward” (wards with traffic/incidents recently):
1) Compute edge scores (deterministic):
   - `score = w_risk*risk(edge) + w_traffic*traffic(edge) + w_hits*recent_hits(edge)`
2) Choose `priority_edges = top K` (K = min(10, edges_seen))
3) Allocate posture:
   - balanced: split patrol/checkpoint by budget
   - patrol-heavy: more patrols
   - checkpoint-heavy: more checkpoints
4) Place patrols/checkpoints on those edges within caps.

**Allocation rule (simple v1):**
- each patrol costs 1 point
- each checkpoint costs 2 points
- budget_points sets max units per ward

Persist:
- patrol_edges + checkpoints counts by edge_key.

---

## 6) Enforcement effects (how it changes the world)

### 6.1 Interference mitigation hook (0264)
Expose:
- `def interdiction_prob_for_edge(world, edge_key, ward_id) -> float`
  - base + patrol_bonus*patrols + checkpoint_bonus*checkpoints, clamped

Use it in interference:
- before applying THEFT/SABOTAGE effect, roll a deterministic “interdiction check”:
  - if interdicted: reduce severity heavily or prevent the incident
  - optionally convert into `ARREST_MADE` event

Also apply synergy with escorts:
- effective escort mitigation = escort_mitigation_per_guard * (1 + escort_synergy_bonus * interdiction_prob_edge)

### 6.2 Corridor risk suppression (0261)
For edges with patrol/checkpoint coverage:
- apply extra decay/suppression daily:
  - `risk = clamp(risk - risk_suppression_per_day * coverage_factor, 0, 1)`
Where coverage_factor can be:
- `min(1.0, 0.25*patrols + 0.5*checkpoints)`

This is crucial for “existential predation”: without suppression, risk rises; with suppression, it can be pushed back down.

### 6.3 Local interactions (optional v1)
If interdiction triggers:
- emit `LOCAL_ARREST` or `CONFISCATION` as local interaction incidents.
v1 can keep this as telemetry only (no agent incarceration yet).

---

## 7) Persistence stance (seed vault policy)

Given the current preference (persist map + factions + culture):
- enforcement state can be treated as **derived** from ward budgets and posture,
or persisted depending on taste.

v1 recommendation:
- persist `WardSecurityPolicy` (budget + posture),
- treat `WardSecurityState` as rebuildable (but snapshot it anyway for mid-run save/load consistency).

---

## 8) Telemetry + cockpit additions

Metrics:
- `metrics["enforcement"]["patrols_total"]`
- `metrics["enforcement"]["checkpoints_total"]`
- `metrics["enforcement"]["interdictions"]`
- `metrics["enforcement"]["incidents_prevented"]`
- TopK:
  - `enforcement.covered_edges` by coverage_factor
  - `enforcement.hot_wards` by incidents_prevented

DebugCockpit:
- Top protected edges (edge, patrols, checkpoints, risk)
- Interdictions today
- Incidents prevented vs incidents successful

Events:
- `ENF_PLAN_UPDATED`
- `ENF_INTERDICTION_SUCCESS`
- `ENF_INTERDICTION_FAIL` (optional)

---

## 9) Tests (must-have)

Create `tests/test_law_enforcement_v1.py`.

### T1. Determinism
- clone world; same traffic/incidents; enforcement placements identical.

### T2. Caps respected
- patrol/checkpoint totals never exceed caps.

### T3. Interference mitigation works
- with enforcement coverage, same interference attempt yields reduced severity or prevented event.

### T4. Risk suppression works
- edge risk decreases faster with enforcement coverage than without.

### T5. Snapshot roundtrip
- save mid-run; load; same placement + mitigation outcomes.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add enforcement module + state
- Create `src/dosadi/runtime/law_enforcement.py` with EnforcementConfig, WardSecurityPolicy, WardSecurityState
- Add world.enf_cfg/world.enf_policy_by_ward/world.enf_state_by_ward to snapshots

### Task 2 — Implement daily enforcement planning (bounded)
- Determine active wards and candidate edges (bounded)
- Rank edges deterministically from risk/traffic/hits and allocate patrols/checkpoints within budget and caps

### Task 3 — Wire effects into interference + corridor risk
- Add interdiction probability hooks used by faction interference
- Apply risk suppression to covered edges daily
- Add escort synergy multiplier

### Task 4 — Telemetry + cockpit
- Add counters/topK and render protected edges + interdictions

### Task 5 — Tests
- Add `tests/test_law_enforcement_v1.py` implementing T1–T5

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=True:
  - wards allocate patrols/checkpoints deterministically,
  - interference is meaningfully countered (prevented/reduced),
  - corridor risk can be suppressed on protected edges,
  - cockpit shows coverage and interdictions,
  - save/load works.

---

## 12) Next slice after this trunk step

**Real Factions v1** (named groups with territory + budgets + predation policy),
so interference becomes *actor-driven* rather than an abstract shadow pressure.
