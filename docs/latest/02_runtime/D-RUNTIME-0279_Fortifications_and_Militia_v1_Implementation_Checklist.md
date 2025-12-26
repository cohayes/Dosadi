---
title: Fortifications_and_Militia_v1_Implementation_Checklist
doc_id: D-RUNTIME-0279
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0262   # Resource Refining Recipes v2
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0267   # Corridor Improvements v1
  - D-RUNTIME-0268   # Tech Ladder v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0277   # Crackdown Strategy v1
  - D-RUNTIME-0278   # War & Raids v1
---

# Fortifications & Militia v1 — Implementation Checklist

Branch name: `feature/fortifications-militia-v1`

Goal: add buildable and maintainable **defensive capacity** that:
- deters raids and reduces corridor collapse risk (A2 + D3),
- gives institutions a non-random way to invest in safety,
- creates a “defense economy” (materials + budgets + tech),
- supports long-run empire stability.

v1 is macro defense, not tactical battles.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same defense outcomes.
2. **Bounded.** Defenses apply as modifiers; no per-agent combat simulation.
3. **Buildable.** Uses construction pipeline + recipes (0258, 0262).
4. **Maintainable.** Wear and upkeep matter; neglect causes decay (0253/0272 synergy).
5. **Tech-gated.** Better fortifications and militia training require unlocks (0268).
6. **Tested.** Build costs, modifiers, decay, persistence, raid interactions.

---

## 1) Concept model

Defense capacity comes from two sources:
1) **Fortifications**: corridor-node facilities that reduce raid success and increase detection.
2) **Militia capacity**: a ward-level pool that increases escort effectiveness and raid defense.

Both are fed by:
- budgets (0273),
- materials (0262),
- and institutional policy (0269).

---

## 2) Fortification facility types (v1)

Add 3 corridor-edge “defense facilities”:
1) **OUTPOST_L1**
- cheap watchpost, increases detection and reduces raid success slightly

2) **FORT_L2**
- stronger, requires better materials, significant defense modifier

3) **GARRISON_L2**
- provides escort staging and militia support; boosts escort policy effectiveness

Placement:
- best on corridor nodes/edges (like WAYSTATION_L2 idea from 0272).
If corridor-edge placement is not yet supported:
- represent as facilities in the adjacent ward and link them to specific corridor ids.

---

## 3) Militia model (v1)

Per ward, maintain:
- `militia_strength: float` (0..1 or 0..100)
- `militia_ready: float` (0..1) (fatigue/availability proxy)
- `militia_training_level: int` (tech gated)
- `militia_upkeep_per_day` (budget + supplies)

Militia increases:
- escort coverage effectiveness (0261),
- raid defense (0278),
- crackdown execution quality (0277) (optional v1).

Militia decays if:
- unpaid upkeep,
- repeated raids,
- high unrest/culture anti_state.

---

## 4) Data structures

Create `src/dosadi/runtime/defense.py`

### 4.1 Config
- `@dataclass(slots=True) class DefenseConfig:`
  - `enabled: bool = False`
  - `militia_train_rate_per_day: float = 0.02`
  - `militia_decay_per_day: float = 0.01`
  - `max_militia_strength: float = 1.0`
  - `deterministic_salt: str = "defense-v1"`

### 4.2 Ward defense state
- `@dataclass(slots=True) class WardDefenseState:`
  - `ward_id: str`
  - `militia_strength: float = 0.0`
  - `militia_ready: float = 1.0`
  - `training_level: int = 0`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.defense_cfg`
- `world.ward_defense: dict[str, WardDefenseState]`

Persist in snapshots and seeds.

---

## 5) Training and upkeep (daily loop)

Implement:
- `run_defense_for_day(world, day)`

For each ward:
1) Determine desired militia policy from institutions:
- policy dials:
  - `militia_target_strength` (0..1)
  - `militia_training_budget` (budget points/day)
2) Pay upkeep + training using ledger (0273):
- `PAY_MILITIA_UPKEEP`
- `PAY_MILITIA_TRAINING`
Cap by available balance.
3) Apply training gains if paid:
- militia_strength moves toward target
- training_level upgrades if tech unlocked and budget sustained (simple thresholds)
4) Apply decay if unpaid or high unrest.

Bounded: per ward daily update is fine (36 wards).

---

## 6) Fortification build + upkeep

Add facility definitions (0252/0272 style):
- OUTPOST_L1 requires:
  - basic materials (SCRAP_METAL, FASTENERS, FILTER_MEDIA)
  - tech gate: `UNLOCK_OUTPOST_L1`
- FORT_L2 requires:
  - ADV_COMPONENTS, SEALANT, FILTER_MEDIA
  - tech gate: `UNLOCK_FORT_L2`
- GARRISON_L2 requires:
  - similar + “training supplies”
  - tech gate: `UNLOCK_GARRISON_L2`

Integrate with construction (0258):
- planner proposes fortification projects for high-risk corridors.

Upkeep:
- fortifications require maintenance supplies and/or budget points:
  - `PAY_FORT_MAINTENANCE`
If unpaid, fortification effectiveness decays.

---

## 7) Effects wiring (what defenses change)

### 7.1 Raids (0278)
When resolving a raid:
- if target corridor/ward has fortifications:
  - reduce raid success probability
  - increase raid failure penalty for aggressor
- militia adds defense multiplier in ward/corridor region.

### 7.2 Corridor risk / escort policy (0261)
- militia_ready boosts escort coverage quality
- GARRISON_L2 boosts escort staging and reduces escort fatigue (abstract)

### 7.3 Crackdowns (0277)
- militia can reduce political cost of crackdowns (stable presence),
  OR increase it if militia is seen as oppressive under certain cultures (optional later).

### 7.4 Culture and legitimacy (0270/0269)
- visible fortifications can reduce fear, increasing legitimacy
- heavy militarization can increase resentment in P2

Keep v1 minimal:
- defense reduces risk but adds upkeep burden.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["defense"]["militia_avg"]`
- `metrics["defense"]["militia_by_ward"]`
- `metrics["defense"]["forts_by_type"]`
- `metrics["defense"]["upkeep_paid"]`
- `metrics["defense"]["upkeep_shortfall"]`

TopK:
- highest-risk corridors without defenses
- wards with low militia vs high raid risk

Cockpit:
- ward defense page: militia strength/ready, training level, upkeep status
- corridor defense overlay: fortifications present and their effective modifier
- “defense ROI”: raids prevented vs upkeep (rough)

Events:
- `MILITIA_TRAINED`
- `FORT_BUILT`
- `FORT_DEGRADED`
- `DEFENSE_UPKEEP_FAILED`

---

## 9) Tests (must-have)

Create `tests/test_fortifications_militia_v1.py`.

### T1. Determinism
- same budgets/policies → same militia evolution.

### T2. Upkeep cap
- if ward cannot pay upkeep, militia decays and telemetry records shortfall.

### T3. Fortification build gating
- cannot build without tech unlock; can build with unlock.

### T4. Raid interaction
- with fortifications/militia, raid success probability decreases deterministically.

### T5. Persistence
- ward defense and fort status persist across snapshot/load and seed.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add defense module + ward defense state
- Create `src/dosadi/runtime/defense.py` with DefenseConfig and WardDefenseState
- Add world.ward_defense to snapshots + seeds

### Task 2 — Add militia policy dials + daily updater
- Extend institutions policy with militia targets and training/upkeep budgets
- Implement `run_defense_for_day()` that pays via ledger and updates militia

### Task 3 — Add fortification facility types
- Add OUTPOST_L1, FORT_L2, GARRISON_L2 facility definitions with tech gates and costs
- Integrate into construction pipeline and maintenance/upkeep

### Task 4 — Wire effects into raids and escort policy
- Apply fort/militia modifiers to raid resolution (0278)
- Apply militia effects to escort coverage quality (0261)

### Task 5 — Telemetry + tests
- Add cockpit pages and metrics/topK
- Add `tests/test_fortifications_militia_v1.py` (T1–T5)

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=True:
  - wards can train and sustain militia with budgets,
  - fortifications can be built and maintained,
  - raids/corridor collapses are measurably reduced by defenses,
  - defense state persists into long-run seeds,
  - cockpit can explain defense posture by ward and corridor.

---

## 12) Next slice after this

**Diplomatic Deterrence v1** — make defense interact with treaties:
- mutual defense pacts,
- threat postures,
- and stability regimes that can prevent war escalation.
