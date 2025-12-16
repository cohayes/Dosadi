---
title: Belief_Formation_v1_Implementation_Checklist
doc_id: D-RUNTIME-0244
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-16
depends_on:
  - D-RUNTIME-0232   # Timewarp / MacroStep
  - D-RUNTIME-0243   # Event → Memory Router v1
  - D-RUNTIME-0241   # Phase Engine v1 (optional: phase-aware belief tuning)
  - D-AGENT-0020     # Agent Model (PlaceBeliefs / Beliefs / Memory)
---

# Belief Formation v1 — Implementation Checklist

Branch name: `feature/belief-formation-v1`

Goal: convert **crumbs + episodes** into durable **belief patterns** that:
- are cheap to maintain at scale,
- influence decisions (routing, staffing, risk tolerance),
- decay / update over time,
- are deterministic and testable.

This is the “sleep cycle” step:
**daily events → beliefs**.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic beliefs.** Same seed + same events → same belief vectors.
2. **Bounded per-agent cost.** Beliefs update O(#new_signal_tags) not O(all_tags).
3. **No global scans.** Belief updates run per-agent only when that agent has new signals or on sleep cadence.
4. **Beliefs are compact.** Keep top-N beliefs per agent using boring-winner-style retention.
5. **Save/Load compatible.** Belief store persists and resumes without divergence.

---

## 1) Concept model (v1)

Beliefs are *aggregated summaries* derived from:
- crumb tags and their decayed counts
- salient episodes (especially failures/downtime)
- optionally phase context (phase 2 biases suspicion)

v1 beliefs are purely **structured numeric** entries:
- `route-risk:edge:a-b` → 0.73
- `facility-reliability:fac:12` → 0.41
- `delivery-trust:org:guild-x` → 0.55 (placeholder for later)

Each belief has:
- a key
- a value in 0..1
- a confidence / weight
- a last_updated_day

Later these can become PlaceBeliefs or faction beliefs; v1 just lays the data substrate.

---

## 2) Implementation Slice A — Belief store types

### A1. Create module: `src/dosadi/agent/beliefs.py`
**Deliverables**
- `@dataclass(slots=True) class Belief:`
  - `key: str`
  - `value: float`            # 0..1 (risk, reliability, etc.)
  - `weight: float`           # 0..1 (confidence)
  - `last_day: int`

- `@dataclass(slots=True) class BeliefStore:`
  - `max_items: int`
  - `items: dict[str, Belief]`            # key -> Belief
  - `minheap: list[tuple[float, str]]`    # boring-winner retention by weight (or abs(value-0.5)*weight)
  - `def upsert(self, belief: Belief) -> None`
  - `def get(self, key: str) -> Belief | None`
  - `def signature(self) -> str`

**Retention rule**
- Keep only top `max_items` by `importance = weight`
- O(log K) updates; no scanning all beliefs to drop one.

### A2. Agent integration
Ensure each agent has:
- `agent.beliefs: BeliefStore`
- default `max_items=64` (configurable)

---

## 3) Implementation Slice B — Belief formation runtime

### B1. Create module: `src/dosadi/runtime/belief_formation.py`
**Deliverables**
- `@dataclass(slots=True) class BeliefConfig:`
  - `enabled: bool = True`
  - `sleep_interval_days: int = 1`        # daily formation
  - `max_beliefs_per_agent: int = 64`
  - `crumb_to_belief_alpha: float = 0.10` # learning rate
  - `episode_bonus_weight: float = 0.15`
  - `belief_decay_half_life_days: int = 120`
  - `min_weight: float = 0.05`
  - `max_weight: float = 0.95`
  - `phase2_suspicion_bias: float = 0.05` # optional

- `@dataclass(slots=True) class BeliefState:`
  - `last_run_day: int = -1`

- `def run_belief_formation_for_day(world, *, day: int) -> None`
  - iterate only agents that have new memory signals since last run (see Slice C)
  - update beliefs and decay old ones

### B2. Deterministic update rule (v1 simple)
For each agent, derive signal values:

1) From crumbs:
- Each crumb tag maps to a belief key using deterministic mapping rules (see section 4)
- Convert crumb count to a normalized `signal` in 0..1:
  - `signal = 1 - exp(-count / scale)` (scale constant, e.g. 3)
  - Keep it deterministic and pure math.

2) From episodes:
- If STM contains episode kinds that match belief key families, add `episode_bonus_weight`.

Then update:
- `belief.value = (1-alpha)*belief.value + alpha*signal`
- `belief.weight = clamp(belief.weight + alpha*(signal - belief.weight), min_weight, max_weight)`
- `last_day = day`

Optional phase2 bias:
- if world.phase == PHASE2 and belief is in “risk” family: `belief.value += phase2_suspicion_bias` (clamp).

### B3. Belief decay
Beliefs that are not updated should slowly decay weight toward `min_weight`:
- apply only when agent is processed (bounded)
- `weight *= decay_factor` where `decay_factor = 0.5 ** (dt / half_life_days)`

---

## 4) Belief key mapping (v1 stable, explicit)

Implement a deterministic mapping from crumb tags → belief keys:

- `delivery-fail:{delivery_id}` →
  - `delivery-risk:{delivery_id}`

- `facility-down:{facility_id}` →
  - `facility-reliability:{facility_id}` (value represents risk, or invert later)

- `route-risk:{edge_key}` →
  - `route-risk:{edge_key}`

- `incident:{incident_kind}:{target_id}` →
  - `incident-risk:{incident_kind}:{target_id}`

For now, treat “risk” as higher value = more dangerous/unreliable.

---

## 5) Integration into decisions (minimal hooks)

v1 should expose belief queries; decisions can begin to use them.

### 5.1 Planner / Logistics hook (optional)
- If choosing between multiple routes/edges, prefer lower `route-risk` belief.
- If choosing facility build site, penalize sites with high route-risk from core.

Keep these as optional knobs; do not create a dependency cycle.

---

## 6) Efficient agent selection: agents with new signals

To avoid daily scans of all agents:
- Maintain a world-level set/list `world.agents_with_new_signals` (or a bitset-like structure)
- The Event→Memory Router marks an agent when it bumps crumbs or adds an episode.
- Belief formation processes only agents in that set, then clears them (bounded).

This makes belief formation O(#agents_touched_by_events), not O(all_agents).

---

## 7) Save/Load integration

Serialize:
- agent belief stores
- belief formation state (last_run_day)
- agents_with_new_signals queue/set (optional; can be rebuilt, but store for deterministic continuity)

---

## 8) Tests (must-have)

Create `tests/test_belief_formation.py`.

### T1. Deterministic beliefs
- Same events → same belief store signature.

### T2. Bounded retention
- Force > max_items belief keys; ensure only top-K retained deterministically.

### T3. Update math sanity
- For a known crumb count sequence, ensure belief.value moves toward expected signal.

### T4. Decay
- Belief weight decreases over time when not updated.

### T5. No global scans
- Use a stub world with 1000 agents, touch 5 agents via router, run belief formation:
  - assert only those 5 were processed (via counters or mocks).

### T6. Snapshot stability
- Save mid-day, load, continue; ensure belief signatures match.

---

## 9) Codex Instructions (verbatim)

### Task 1 — Add BeliefStore to agents
- Create `src/dosadi/agent/beliefs.py` with Belief and BeliefStore (boring-winner retention)
- Ensure every agent has `agent.beliefs`

### Task 2 — Implement belief formation runtime
- Create `src/dosadi/runtime/belief_formation.py` with BeliefConfig/State and `run_belief_formation_for_day`
- Implement deterministic signal normalization from crumbs + episode bonus
- Implement bounded decay and updates

### Task 3 — Connect router to belief formation
- Add `world.agents_with_new_signals`
- Event→Memory Router marks agents when signals added
- Belief formation processes only marked agents

### Task 4 — Save/Load + tests
- Serialize belief stores and state
- Add `tests/test_belief_formation.py` implementing T1–T6

---

## 10) Definition of Done

- `pytest` passes.
- Agents accumulate compact belief stores deterministically.
- Belief formation runs in bounded time (only agents with new signals).
- Beliefs decay over time and influence (optionally) route/site choices.
- Save/load preserves belief trajectories without duplication.

---

## 11) Next slice after this

**Decision hooks v1**:
- planner and logistics read beliefs (route-risk, facility reliability),
- agents begin to avoid “bad” edges and prefer reliable supply paths.
