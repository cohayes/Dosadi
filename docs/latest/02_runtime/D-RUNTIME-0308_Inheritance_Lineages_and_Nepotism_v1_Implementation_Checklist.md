---
title: Inheritance_Lineages_and_Nepotism_v1_Implementation_Checklist
doc_id: D-RUNTIME-0308
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0290   # Workforce Skill Assignment v2
  - D-RUNTIME-0291   # Wages, Rations & Class Stratification v1
  - D-RUNTIME-0292   # Banking, Debt & Patronage v1
  - D-RUNTIME-0302   # Shadow State & Deep Corruption v1
  - D-RUNTIME-0304   # Constitutional Settlements & Rights Regimes v1
  - D-RUNTIME-0307   # Intergenerational Social Mobility v1
---

# Inheritance, Lineages & Nepotism v1 — Implementation Checklist

Branch name: `feature/inheritance-lineages-nepotism-v1`

Goal: move one step closer to “micro society” while staying cheap so that:
- wealth and privilege persist via inheritance mechanisms,
- nepotism and lineage networks shape high-status job assignment,
- elites can reproduce through patronage and captured institutions,
- reforms and rights regimes can restrict inheritance and nepotism (or fail),
- long-run seeds diverge into dynastic oligarchies, meritocratic checks, or corrupt patronage webs.

v1 is **not** full genealogies or romance/fertility simulation. It’s “family houses” as bounded economic-social buckets.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same lineage formation and inheritance flows.
2. **Bounded.** Track houses/lineages at polity scale (TopK); no per-person family trees.
3. **Composable.** Integrates with debt/patronage, workforce assignment, mobility, corruption, and rights regimes.
4. **Legible.** Explain “why this job went to that house”.
5. **Phase-aware.** P2 intensifies nepotism; P0 allows more open competition.
6. **Tested.** Nepotism bias and persistence.

---

## 1) Concept model

Represent “Houses” (lineages) per polity:
- each House has a wealth bucket, reputation, and patron network,
- members are not simulated individually; we track headcount and influence,
- Houses compete for offices and contracts via nepotism edges,
- inheritance transfers wealth and influence from old to new heads (macro).

Houses act like a mid-layer between factions and individual agents:
- faction sponsors Houses
- Houses provide loyal staffing pools and legitimacy narratives

---

## 2) What v1 changes in the sim

- Adds a **nepotism bias** in:
  - selecting supervisors/leaders in workforce assignment,
  - awarding contracts/permits,
  - and allocating patronage/credit terms.
- Adds **wealth persistence**: mobility alone won’t erase elites; Houses carry advantage.
- Adds **anti-nepotism constraints** via constitution/rights regimes.

---

## 3) Data structures

Create `src/dosadi/runtime/lineages.py`

### 3.1 Config
- `@dataclass(slots=True) class LineageConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 90`          # quarterly
  - `deterministic_salt: str = "lineages-v1"`
  - `max_houses_per_polity: int = 32`
  - `max_edges_per_polity: int = 64`
  - `inheritance_years: int = 25`
  - `nepotism_bias_scale: float = 0.25`
  - `anti_nepotism_scale: float = 0.30`

### 3.2 House (lineage) record
- `@dataclass(slots=True) class House:`
  - `house_id: str`                  # "house:<polity>:12"
  - `polity_id: str`
  - `name: str`
  - `tier: str`                      # mapped to mobility tiers: WORKING..ELITE
  - `wealth: float = 0.0`            # proxy bucket
  - `influence: float = 0.0`         # 0..1
  - `reputation: float = 0.5`        # 0..1
  - `debt: float = 0.0`
  - `members_proxy: int = 0`
  - `head_generation: int = 0`       # increments on inheritance cycles
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Nepotism/patronage edge (bounded)
- `@dataclass(slots=True) class PatronEdge:`
  - `polity_id: str`
  - `from_house_id: str`
  - `to_domain: str`                 # WORKFORCE|COURTS|CUSTOMS|DEPOTS|COUNCIL|MEDIA
  - `strength: float`                # 0..1
  - `mode: str`                      # NEPOTISM|PATRONAGE|BRIBE
  - `exposure: float = 0.0`
  - `last_update_day: int = -1`

### 3.4 Lineage state (per polity)
- `@dataclass(slots=True) class LineageState:`
  - `polity_id: str`
  - `houses: dict[str, House] = field(default_factory=dict)
  - `edges: list[PatronEdge] = field(default_factory=list)
  - `last_inheritance_year: int = 0`
  - `nepotism_norm: float = 0.0`     # 0..1 (cultural acceptance)
  - `last_update_day: int = -1`

World stores:
- `world.lineage_cfg`
- `world.lineage_by_polity: dict[str, LineageState]`

Persist in snapshots and seeds.

---

## 4) House generation and maintenance (quarterly)

If no houses exist for a polity:
- seed initial houses from tier shares (0307):
  - create N houses per tier proportional to tier share
  - wealth/influence seeded from tier with noise but deterministic

Each quarter:
- update house wealth:
  - from wages/rations (0291) and contracts/patronage (0292)
  - elite houses accumulate faster, but subject to debt and scandal
- update influence:
  - from faction sponsorship (0266) and shadow state (0302) capture support
- update nepotism_norm:
  - increases with capture/shadow state and low rights constraints
  - decreases with reform success (0303) and constitutional anti-corruption posture (0304)

Bound houses:
- if over max, merge lowest influence houses within same tier into a “commons” house.

---

## 5) Inheritance cycle (every inheritance_years)

When year crosses inheritance boundary:
- for each house:
  - apply wealth transfer with leakage (tax, corruption, confiscation risk)
  - reputation drift: scandals and success affect it
  - increment head_generation
- optionally create house splits for very large houses (bounded, rare):
  - split influence/wealth into two houses (dynastic branches)

Emit a polity summary event.

---

## 6) Nepotism edges and effects

Edges represent “reach” into domains:
- workforce: job placement advantage
- courts/customs/depots: favorable rulings, exemptions, priority access
- council/media: narrative power

Edge strength evolves with:
- house wealth and influence
- corruption capture (0302) increases edge growth
- truth regimes and reform (0305/0303) increase exposure and reduce edge strength

### 6.1 Applying nepotism to workforce assignment (0290)
Provide helper:
- `nepotism_bias(world, polity_id, candidate_house_id, role_kind) -> bias`

Role kinds:
- `SUPERVISOR`, `FOREMAN`, `OFFICER`, `CLERK`, `TECHNICIAN`

Bias increases selection probability for candidates connected to influential houses, but can be constrained by:
- `due_process` / `audit_independence` / `term_limits` from constitution (0304)
- reform campaigns (0303)

Keep v1 “macro”: apply bias to agent selection if agents have `house_id` tag; if not, apply at pool level via tier allocation.

---

## 7) Anti-nepotism and rights regimes constraints

From constitution (0304):
- due_process and audit_independence reduce nepotism_bias_scale
- term_limits increase churn and reduce long-lived capture of roles
- speech rights increase scandal exposure via media

Represent as a scalar:
- `anti_nepotism_factor = 1 - anti_nepotism_scale * f(constraints)`

Apply in bias helper and edge evolution.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["lineages"]["houses"]`
- `metrics["lineages"]["top_house_influence"]`
- `metrics["lineages"]["nepotism_norm"]`
- `metrics["lineages"]["nepotism_bias_avg"]`
- `metrics["lineages"]["inheritance_cycles"]`

Cockpit:
- polity lineages page:
  - list Top houses by influence/wealth, tier, reputation
  - edges view: which houses control which domains
  - inheritance timeline: generation increments and wealth shifts
  - “role capture” panel: which domains show strongest nepotism

Events:
- `HOUSE_FOUNDED`
- `HOUSE_INHERITANCE`
- `NEPOTISM_EDGE_STRENGTHENED`
- `NEPOTISM_SCANDAL_EXPOSED` (optional tie to truth regimes)

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/lineages.json` with houses and edges (bounded).

---

## 10) Tests (must-have)

Create `tests/test_inheritance_lineages_nepotism_v1.py`.

### T1. Determinism
- same inputs → same house and edge evolution.

### T2. Elite houses accumulate faster
- higher tier houses increase wealth/influence more than working houses under same conditions.

### T3. Corruption increases nepotism edges
- higher capture increases edge strengths and nepotism_norm.

### T4. Rights constraints reduce nepotism bias
- stronger constitution constraints lower nepotism_bias outputs.

### T5. Inheritance cycle updates generation and wealth
- crossing inheritance boundary increments head_generation and applies transfers.

### T6. Snapshot roundtrip
- houses and edges persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add lineages module + state
- Create `src/dosadi/runtime/lineages.py` with LineageConfig, House, PatronEdge, LineageState
- Add lineage_by_polity to snapshots + seeds

### Task 2 — Implement house seeding and quarterly updates
- Seed houses from mobility tier shares (0307); update wealth/influence and nepotism_norm quarterly

### Task 3 — Implement inheritance cycle
- Apply inheritance transfer every inheritance_years; bounded splits; emit events

### Task 4 — Implement nepotism bias helper and wire into workforce assignment
- Add `nepotism_bias()` and integrate into role selection (0290), with anti-nepotism constraints from constitution/reform

### Task 5 — Cockpit + tests
- Add lineages dashboard and edges view
- Add `tests/test_inheritance_lineages_nepotism_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - houses exist and evolve with wealth/influence,
  - nepotism materially biases high-status allocation,
  - constitutions and reforms can curb nepotism (or fail),
  - inheritance cycles preserve elite structures over centuries,
  - cockpit explains “which houses run which parts of the state.”

---

## 13) Next slice after this

**Demographic Dynamics v1** — births, deaths, household formation (macro):
- fertility/mortality as cohorts,
- and how population shape shifts labor, war, and legitimacy.
