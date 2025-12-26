---
title: Culture_Wars_v1_Implementation_Checklist
doc_id: D-RUNTIME-0270
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0231   # Save/Load Seed Vault
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
---

# Culture Wars v1 — Implementation Checklist

Branch name: `feature/culture-wars-v1`

Goal: make **culture a strategic substrate** that can:
- stabilize or destabilize institutions (A3),
- amplify or suppress predation (A2),
- shape expansion priorities (A1),
without needing full dialogue / interpersonal simulation.

Culture Wars v1 is the “soft power” loop:
- beliefs → norms → alignment → pressure,
with deterministic, bounded updates.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same world/seed → same cultural outcomes.
2. **Bounded.** Culture updates only for active wards and TopK beliefs/norms.
3. **Legible.** Telemetry can explain “why Ward 12 is radicalizing.”
4. **Composable.** Feeds into institutions (0269), factions (0266), and incident likelihood (0242).
5. **Persisted.** Cultural beliefs are part of your persisted seed state.
6. **Tested.** Determinism, caps, persistence.

---

## 1) Concept model

We introduce **Ward Culture** as a bounded set of:
- *norms* (what behavior is tolerated/rewarded),
- *alignment* toward factions/institutions,
- *taboos* (what sparks conflict),
- *propaganda intensity* (how hard factions push narratives).

Culture is derived from belief formation outputs, but becomes a *sticky* medium.

We do not simulate individual speech here; instead, we:
- aggregate signals from belief crumbs/episodes,
- apply deterministic transforms,
- produce norms + alignments.

---

## 2) Data structures

Create `src/dosadi/runtime/culture_wars.py`

### 2.1 Config
- `@dataclass(slots=True) class CultureConfig:`
  - `enabled: bool = False`
  - `max_active_wards_per_day: int = 24`
  - `max_norms_per_ward: int = 12`
  - `max_alignments_per_ward: int = 8`
  - `norm_decay_per_day: float = 0.001`
  - `alignment_decay_per_day: float = 0.002`
  - `deterministic_salt: str = "culture-v1"`

### 2.2 Ward culture state
Norms are strings with weights:
- `norm:queue_order` (supports protocols / discipline)
- `norm:mutual_aid` (pro-social cooperation)
- `norm:smuggling_tolerance` (corruption permissive)
- `norm:vigilante_justice` (extra-legal enforcement)
- `norm:anti_state` (legitimacy erodes)
- `norm:anti_raider` (support for patrols/escorts)
- `norm:work_guild_pride` (industry-aligned)

- `@dataclass(slots=True) class WardCultureState:`
  - `ward_id: str`
  - `norms: dict[str, float] = field(default_factory=dict)`        # norm_key -> 0..1
  - `alignment: dict[str, float] = field(default_factory=dict)`    # faction_id/institution -> -1..+1
  - `taboos: dict[str, float] = field(default_factory=dict)`       # taboo_key -> 0..1
  - `last_updated_day: int = -1`
  - `recent_drivers: dict[str, float] = field(default_factory=dict)`  # bounded “why” map

World stores:
- `world.culture_cfg`
- `world.culture_by_ward: dict[str, WardCultureState]`

Snapshot + seed vault include these (seed identity layer).

---

## 3) Inputs (signals) from existing systems (bounded)

Culture Wars v1 consumes:
- belief formation outputs: top belief tags and weights per ward (0244)
- institutional state: legitimacy/corruption/unrest (0269)
- faction territory and recent actions (0266)
- incidents near the ward: raids, interdictions, shortages (0242/0264)

We should not scan all beliefs. Require a helper that yields TopK belief signals per ward per day.

---

## 4) Active ward selection (bounded)

Reuse the same selection logic as institutions:
- shortage spikes
- predation spikes
- belief swings
- territory shifts
Select up to `max_active_wards_per_day` deterministically.

---

## 5) Norm synthesis (beliefs → norms)

Implement:
- `def run_culture_for_day(world, *, day: int) -> None`

For each active ward:
1) Get TopK beliefs (e.g., fear, trust, anger, “state_helps”, “raiders_strike”, “guild_feeds_us”)
2) Map belief patterns to norm deltas using a small deterministic rule table.

Example rule table (v1):
- if `belief:queue_fairness` high → increase `norm:queue_order`
- if `belief:predation_fear` high → increase `norm:anti_raider` and maybe `norm:vigilante_justice`
- if `inst.corruption` high + `belief:anger` high → increase `norm:anti_state` and `norm:smuggling_tolerance`
- if repeated interdictions succeed → increase `norm:pro_state_enforcement`
- if shortages chronic → increase `norm:mutual_aid` OR `norm:smuggling_tolerance` depending on corruption/legitimacy

Apply deltas with caps (e.g., +/-0.05 per day), clamp 0..1.
Apply decay on all stored norms (bounded dict) each day:
- `norm *= (1 - norm_decay_per_day)`

Keep only Top `max_norms_per_ward` norms by weight (evict lowest deterministically).

Store `recent_drivers` as TopK rules that fired.

---

## 6) Alignment synthesis (culture → faction/institution tilt)

Alignment is a bounded map toward:
- `fac:state`
- each raider faction present
- `fac:guild:*` (if relevant)
- `inst:ward` (the local institution abstractly)

Compute deterministic alignment changes:
- if `norm:anti_state` high → move alignment away from state
- if `norm:queue_order` high → move toward state/inst
- if `norm:smuggling_tolerance` high → move toward raiders (or away from audits)
- if `norm:work_guild_pride` high → move toward guild

Clamp alignments to [-1, +1], decay daily by alignment_decay_per_day, keep TopK by |value|.

---

## 7) Culture effects (how it changes the sim)

Wire a few key effects (cheap and powerful):

### 7.1 Institutions (0269)
- legitimacy drift modifier:
  - high `norm:anti_state` makes legitimacy fall faster
  - high `norm:queue_order` makes discipline more effective (fewer unrest spikes)

### 7.2 Faction operations (0266)
- raider success chance / recruitment:
  - high `norm:smuggling_tolerance` increases raider capacity growth or reduces interdiction effectiveness locally
- state enforcement effectiveness:
  - high `norm:anti_raider` improves tip-offs → interdiction bonus (small)

### 7.3 Incident generation (0242)
Add culture-weighted incident priors:
- riots/strikes more likely when `norm:anti_state` and `unrest` high
- vigilantism incidents when `norm:vigilante_justice` high
v1 can just raise “incident weights” without new incident types yet.

All effects must be small and capped; culture should steer, not dominate.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["culture"]["wards_updated"]`
- `metrics["culture"]["norms_total"]`
- TopK:
  - `culture.hot_norms` (global)
  - `culture.most_anti_state_wards`
  - `culture.most_smuggling_tolerant_wards`

Cockpit:
- ward culture view: norms (Top), alignments (Top), taboos (Top), recent drivers (“why”)
- overlay with institutions: legitimacy/corruption/unrest

Events:
- `CULTURE_UPDATED`
- `NORM_SHIFT`
- `ALIGNMENT_SHIFT`

---

## 9) Persistence / seed vault

Because cultural beliefs are a seed identity:
- include ward culture in seed vault persisted layer
- export stable:
  - `seeds/<name>/culture.json` sorted by ward_id, with norms/alignment sorted.

---

## 10) Tests (must-have)

Create `tests/test_culture_wars_v1.py`.

### T1. Determinism
- same beliefs/incidents → same norm/alignment shifts.

### T2. Caps and eviction
- norms per ward never exceed max_norms_per_ward; evictions deterministic.

### T3. Effects on institutions
- with anti_state norm high, legitimacy declines faster (bounded).

### T4. Effects on factions
- smuggling tolerance increases raider success/recruitment (bounded).

### T5. Persistence
- snapshot roundtrip stable continuation
- seed export stable ordering

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add culture module + state
- Create `src/dosadi/runtime/culture_wars.py` with CultureConfig and WardCultureState
- Add world.culture_cfg/world.culture_by_ward to snapshots + seed vault persisted layer
- Add stable export `culture.json`

### Task 2 — Implement daily culture update (bounded)
- Select active wards deterministically
- Pull TopK belief signals per ward and map to norm deltas via a small rule table
- Maintain bounded norms/alignments with decay and eviction
- Record recent drivers for explainability

### Task 3 — Wire culture effects
- Institutions: legitimacy/discipline modifiers from norms
- Factions: bounded modifiers to raider success and state interdiction
- Incidents: culture-weighted priors (no new incident types required)

### Task 4 — Telemetry + tests
- Cockpit panels and metrics/topK
- Add `tests/test_culture_wars_v1.py` (T1–T5)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - wards develop bounded norms and alignments deterministically,
  - culture influences legitimacy/corruption dynamics and predation outcomes modestly,
  - culture state persists into 200-year seeds,
  - cockpit can explain “why this ward radicalized.”

---

## 13) Next slice after this

**Governance Failure Incidents v1** (strikes, riots, secessions, coups) — the A3 escalation layer,
now that institutions + culture can “load” the powder keg.
