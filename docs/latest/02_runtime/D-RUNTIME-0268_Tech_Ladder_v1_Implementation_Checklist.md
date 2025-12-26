---
title: Tech_Ladder_v1_Implementation_Checklist
doc_id: D-RUNTIME-0268
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0231   # Save/Load Seed Vault
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0254   # Suit Wear & Repair v1
  - D-RUNTIME-0258   # Construction Project Pipeline v2
  - D-RUNTIME-0259   # Expansion Planner v2
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0262   # Resource Refining Recipes v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0267   # Corridor Improvements v1
---

# Tech Ladder v1 — Implementation Checklist

Branch name: `feature/tech-ladder-v1`

Goal: add a **century-scale progression system** that unlocks new:
- recipes (materials → parts → advanced parts),
- facilities (recycler → workshop → fab),
- suit tiers / maintenance efficiency,
- corridor infrastructure levels (future),
without building a heavy “research tree UI” yet.

This is a *simulation control layer*:
- deterministic,
- bounded,
- persistent (seed vault),
- explainable (telemetry).

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic unlocks.** Same state/seed → same unlock schedule given same actions.
2. **Bounded compute.** Research evaluation uses TopK signals, not global scans.
3. **No magic leaps.** Unlocks must be paid for with concrete inputs (time/labor/materials).
4. **Persistent.** Tech state is long-run identity; must save/load and belong in seed vault.
5. **Composable.** Recipes, facilities, and planner all consult the tech state.
6. **Tested.** Unlock gating works; persistence works; determinism holds.

---

## 1) Concept model

Tech Ladder v1 is a set of **Research Projects**.
Each project has:
- prerequisites (other projects),
- costs (materials + labor-days + time),
- outputs (unlock tags / tiers).

We avoid a “per-agent research” model in v1.
Instead, research is a **ward/faction/institution** activity executed by the system:
- STATE and/or GUILD can fund research via budgets (0266),
- the planner can spawn research projects when pressure is high (0263, 0262, 0254).

Later we can personify (scientist agents, labs) without changing the core contract.

---

## 2) Tech primitives (what gets unlocked)

Define simple “tags” as gates:

### 2.1 Unlock tags
- `UNLOCK_RECYCLER_RECIPES_T1`
- `UNLOCK_WORKSHOP_PARTS_T2`
- `UNLOCK_CHEM_SEALANTS_T2`
- `UNLOCK_SUIT_REPAIR_KIT_T1`
- `UNLOCK_SUIT_SEALS_T2`
- `UNLOCK_FABRICATION_SIMPLE_T3` (optional later)
- `UNLOCK_CORRIDOR_L2` (enables L1→L2, or L2→L3 future)

### 2.2 Tech tiers (optional convenience)
- tier 0..3 where tier is derived from unlocked tags.
Keep v1 primarily tag-based.

---

## 3) Data structures

Create `src/dosadi/runtime/tech_ladder.py`

### 3.1 Project spec
- `@dataclass(frozen=True, slots=True) class TechProjectSpec:`
  - `tech_id: str`                      # "tech:recycler:t1"
  - `name: str`
  - `prereqs: tuple[str, ...]`
  - `cost_materials: dict[str,int]`
  - `cost_labor_days: int`
  - `duration_days: int`
  - `unlocks: tuple[str, ...]`          # tags
  - `tags: tuple[str, ...] = ()`        # e.g. ("suits","industry")

Provide a registry:
- `def tech_registry() -> dict[str, TechProjectSpec]` (deterministic ordering)

### 3.2 World state
- `@dataclass(slots=True) class TechConfig:`
  - `enabled: bool = False`
  - `max_projects_active: int = 3`
  - `max_projects_started_per_day: int = 1`
  - `deterministic_salt: str = "tech-v1"`

- `@dataclass(slots=True) class TechState:`
  - `unlocked: set[str] = field(default_factory=set)`      # unlock tags
  - `completed: set[str] = field(default_factory=set)`     # tech_id
  - `active: dict[str, "ActiveTechProject"] = field(default_factory=dict)`  # tech_id -> state
  - `last_run_day: int = -1`

- `@dataclass(slots=True) class ActiveTechProject:`
  - `tech_id: str`
  - `started_day: int`
  - `complete_day: int`
  - `sponsor_faction_id: str | None = None`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.tech_cfg`, `world.tech_state`

Snapshot + seed vault include these.

---

## 4) Research projects (v1 set)

Define a tight first ladder that unlocks your current systems:

1) `tech:recycler:t1`
- prereqs: none
- costs: SCRAP_INPUT + labor
- unlocks: `UNLOCK_RECYCLER_RECIPES_T1`

2) `tech:workshop:parts:t2`
- prereqs: tech:recycler:t1
- costs: SCRAP_METAL, FASTENERS, labor
- unlocks: `UNLOCK_WORKSHOP_PARTS_T2`

3) `tech:chem:sealants:t2`
- prereqs: tech:recycler:t1
- costs: CHEM_SALTS (or placeholder), labor
- unlocks: `UNLOCK_CHEM_SEALANTS_T2`

4) `tech:suits:repairkit:t1`
- prereqs: none
- costs: FABRIC, SEALANT, labor
- unlocks: `UNLOCK_SUIT_REPAIR_KIT_T1`

5) `tech:suits:seals:t2`
- prereqs: tech:suits:repairkit:t1 + tech:chem:sealants:t2
- costs: SEALANT, GASKETS
- unlocks: `UNLOCK_SUIT_SEALS_T2`

6) `tech:corridor:l2`
- prereqs: tech:workshop:parts:t2
- costs: FASTENERS, SEALANT, FILTER_MEDIA
- unlocks: `UNLOCK_CORRIDOR_L2`

Keep costs small but nontrivial. Duration_days 3–14 depending on cadence.

---

## 5) Tech runtime loop

Implement:
- `def run_tech_for_day(world, *, day: int) -> None`

Steps:
1) If disabled: return.
2) Complete active projects whose `complete_day <= day`:
   - add to completed
   - add unlock tags
   - emit `TECH_COMPLETED`
3) If slots available and start cap not exceeded:
   - choose next project(s) to start (see section 6)
   - verify prereqs and costs
   - consume materials from sponsor inventory (see section 7)
   - create ActiveTechProject with deterministic complete_day
   - emit `TECH_STARTED`

Bounded: iterate only over:
- active projects (<= max_projects_active)
- small candidate list (TopK) for choosing new projects.

---

## 6) Choosing what tech to pursue (bounded heuristics)

We need deterministic project selection, using “pressure” signals:

### Pressures
- market urgency (0263): materials/parts scarcity
- corridor risk & collapses (0261/0264): infrastructure pressure
- suit failure rates / wear metrics (0254): A1 pressure
- blocked construction by missing parts (0258)

Compute a bounded priority map:
- `priority[tag_or_domain] -> score`

Then score tech projects:
- `score(project) = sum(priority[u] for u in project.unlocks) + small_bonus_for_prereq_chain`

Tie-break by `tech_id`.

Start the best project not completed/active and whose prereqs satisfied and costs payable.

---

## 7) Paying costs (where materials come from)

v1 choose one clean model:

### Option A (recommended): Sponsor depot / sponsor faction stockpile
- If sponsor is STATE or GUILD (0266), define their “research depot” owner:
  - `owner:fac:<id>:research`
- Stockpile policy (0257) can keep this fed with required materials.
- Tech runtime consumes from sponsor owner inventory.

Fallback if factions disabled:
- consume from central depot `depot:main` (or first depot).

This avoids scanning many depots.

---

## 8) Gating integration (where tech tags are consulted)

### 8.1 Recipes (0262)
- Add `requires_unlocks: set[str]` to recipes (or recipe group).
- Recipe registry filters by `world.tech_state.unlocked`.

Example:
- FASTENERS recipe requires `UNLOCK_WORKSHOP_PARTS_T2`

### 8.2 Facility construction (0252, 0258)
- Facility types can require unlock tags.
- Alternatively: upgrading facility kind tiers requires unlock.

### 8.3 Suit improvements (0254)
- Repair effectiveness / max durability depends on unlocked tags:
  - `UNLOCK_SUIT_REPAIR_KIT_T1` increases repair rate
  - `UNLOCK_SUIT_SEALS_T2` reduces hazard multiplier and leak incidents

### 8.4 Corridor improvements (0267)
- L1→L2 upgrade requires `UNLOCK_CORRIDOR_L2` (or allows cheaper recipe).
If not unlocked, planner can only propose L0→L1.

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["tech"]["completed"]`
- `metrics["tech"]["active"]`
- `metrics["tech"]["started"]`
- TopK:
  - `tech.priority` (project scores)
  - `tech.unlocks_recent`

Cockpit panel:
- Completed tech list
- Active projects with days remaining
- Next recommended tech (with reason: top pressure signals)

Events:
- `TECH_STARTED`
- `TECH_COMPLETED`
- `TECH_BLOCKED_COSTS` (optional)

---

## 10) Persistence / seed vault

Because you want persisted seeds (map + factions + culture), tech is also a long-run layer:
- include `tech_state` in seed vault persisted layer
- export stable JSON:
  - `seeds/<name>/tech.json` with:
    - completed tech_ids (sorted)
    - unlocked tags (sorted)

---

## 11) Tests (must-have)

Create `tests/test_tech_ladder_v1.py`.

### T1. Determinism
- clone world; same pressures + inventories → same tech start/completion schedule.

### T2. Prereqs enforced
- cannot start tech with missing prereqs.

### T3. Costs consumed
- on start, materials removed from sponsor inventory; no negatives.

### T4. Unlock gates recipes
- before unlock: recipe absent/unselectable
- after unlock: recipe available

### T5. Unlock gates corridor upgrades
- before: planner won’t propose L1→L2
- after: planner proposes L1→L2 when pressure/risk justify

### T6. Snapshot + seed vault roundtrip
- save mid-project; load; completion occurs correctly and deterministically
- seed export stable ordering

---

## 12) Codex Instructions (verbatim)

### Task 1 — Add tech ladder module + state
- Create `src/dosadi/runtime/tech_ladder.py` with TechProjectSpec registry, TechConfig, TechState, ActiveTechProject
- Add world.tech_cfg/world.tech_state to snapshots and seed vault persisted layer
- Add stable export `tech.json`

### Task 2 — Implement daily tech runtime
- Complete projects on complete_day
- Choose new projects to start using bounded pressure signals and deterministic scoring
- Consume costs from sponsor inventory and enforce prereqs/caps

### Task 3 — Add unlock gating hooks
- Recipes (0262) filter/require unlock tags
- Corridor improvements (0267) gate L1→L2 or reduce cost when unlocked
- Suit repair/wear (0254) uses unlock tags to modify durability/repair effectiveness

### Task 4 — Telemetry + cockpit
- Add tech panels: completed, active, next recommended with reasons
- Add metrics/events

### Task 5 — Tests
- Add `tests/test_tech_ladder_v1.py` (T1–T6)

---

## 13) Definition of Done

- `pytest` passes.
- With enabled=True:
  - tech projects start/complete deterministically under caps,
  - costs are paid from a sponsor inventory,
  - unlocks gate recipes/corridor upgrades/suit improvements,
  - tech persists through save/load and seed vault,
  - cockpit explains what is being researched and why.

---

## 14) Next slice after this

**Institution Evolution v1** (budgets, legitimacy, corruption) *or*
**Advanced Facilities v1** (fab, labs, irrigation-equivalents for Dosadi) *or*
**Culture Wars v1** (beliefs → norms → faction alignment).
