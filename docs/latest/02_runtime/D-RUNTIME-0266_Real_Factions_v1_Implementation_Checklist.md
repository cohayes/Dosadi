---
title: Real_Factions_v1_Implementation_Checklist
doc_id: D-RUNTIME-0266
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0231   # Save/Load Seed Vault
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0264   # Faction Interference v1
  - D-RUNTIME-0265   # Law & Enforcement v1
---

# Real Factions v1 — Implementation Checklist

Branch name: `feature/real-factions-v1`

Goal: replace “shadow interference” with actor-driven predation and governance pressure by introducing:
- named factions,
- territories (ward/node/edge claims),
- budgets/capacity,
- simple deterministic strategies (raid, protect, trade, recruit),
- persistence (faction territories are one of your seed vault must-haves).

This remains hybrid-institutional:
- faction policies are system-level,
- later we can “personify” faction leaders and captains as agents without changing the core.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same state/seed → same faction choices and events.
2. **Bounded.** Factions consider only TopK opportunities; no global scans.
3. **Persisted.** Faction definitions + territories are part of long-run continuity and seed vault.
4. **Composable.** Factions can drive interference, enforcement pressure, and economic behavior.
5. **Tested.** Determinism, caps, and persistence.

---

## 1) Minimal v1 faction model

We need just enough to create meaningful variation after 200 years.

### 1.1 Faction kinds
- `STATE` (legitimate enforcement / ward councils)
- `GUILD` (industrial / logistics)
- `RAIDERS` (predation specialists)
- `CULT` (belief-driven, lower material emphasis) (optional v1)
- `MERCENARY` (sells protection) (optional)

v1 can start with 3: STATE, GUILD, RAIDERS.

### 1.2 Assets / capacities
- `influence` (0..100)
- `security_capacity` (patrol points or “guards available”)
- `raiding_capacity` (raiders available)
- `logistics_capacity` (couriers / wagons)
- `budget_points` (abstract; rises/falls)

### 1.3 Territory
Territory is a *claim layer*:
- wards claimed (soft control)
- corridor edges controlled/raided
- depots controlled (optional later)

Territory affects:
- where they can act cheaply,
- belief seeds (“this ward is under X”),
- enforcement/interference probability.

---

## 2) Data structures

Create `src/dosadi/world/factions.py` (or `runtime/factions.py` if you prefer)

### 2.1 Core
- `@dataclass(slots=True) class Faction:`
  - `faction_id: str`         # "fac:state", "fac:raiders:01"
  - `name: str`
  - `kind: str`               # enum-like string
  - `color: str = ""`         # optional UI
  - `influence: float = 10.0`
  - `budget_points: float = 10.0`
  - `security_capacity: int = 0`
  - `raiding_capacity: int = 0`
  - `logistics_capacity: int = 0`
  - `policy: dict[str, object] = field(default_factory=dict)`
  - `last_updated_day: int = -1`

- `@dataclass(slots=True) class FactionTerritory:`
  - `wards: dict[str,float] = field(default_factory=dict)`      # ward_id -> strength 0..1
  - `edges: dict[str,float] = field(default_factory=dict)`      # edge_key -> strength 0..1
  - `nodes: dict[str,float] = field(default_factory=dict)`      # node_id -> strength 0..1
  - `last_claim_day: dict[str,int] = field(default_factory=dict)`  # key->day (cooldown)

- `@dataclass(slots=True) class FactionSystemConfig:`
  - `enabled: bool = False`
  - `max_factions: int = 32`
  - `max_claims_per_faction: int = 200`
  - `claim_decay_per_day: float = 0.002`
  - `claim_gain_on_success: float = 0.05`
  - `claim_loss_on_failure: float = 0.04`
  - `min_days_between_claim_updates: int = 3`
  - `topk_opportunities: int = 25`
  - `max_actions_per_faction_per_day: int = 2`
  - `deterministic_salt: str = "factions-v1"`

- `@dataclass(slots=True) class FactionSystemState:`
  - `last_run_day: int = -1`

World stores:
- `world.faction_cfg`, `world.faction_state`
- `world.factions: dict[str, Faction]`
- `world.faction_territory: dict[str, FactionTerritory]`

Snapshot them.

---

## 3) Seed vault persistence stance (must-have)

Update Seed Vault (0231) to ensure:
- faction_cfg/state
- factions + faction_territory

are included in the “persisted seed state” layer.

Also: provide an export that is stable/diffable:
- `seeds/<name>/factions.json` (sorted keys)

---

## 4) Faction opportunity model (bounded)

Each day, build a global bounded opportunity set from telemetry:
- top urgent materials (value)
- top risky edges (risk)
- top blocked projects (strategic pressure)
- wards with low enforcement but high value throughput
- depots with chronic shortages

Then each faction picks from this set rather than scanning.

Opportunity object:
- `opp_id`, `kind`, `target_id`, `value`, `risk`, `ward_id`, `material` (optional)

---

## 5) Faction actions (v1)

Define action kinds:
- `RAID_EDGE` (theft/interdiction attempt on an edge)
- `EXTORT_DEPOT` (theft from depot, or “tax”)
- `INVEST_SECURITY` (increase ward budget_points for enforcement)
- `RECRUIT` (increase capacity by spending budget_points)
- `CLAIM_TERRITORY` (soft claim a ward/edge)

v1 minimal: RAID_EDGE, INVEST_SECURITY, CLAIM_TERRITORY.

### 5.1 STATE strategy (defensive)
- prioritizes INVEST_SECURITY in wards with high value + high risk
- claims wards it protects
- reduces interference rate in its claimed wards (synergy with 0265)

### 5.2 RAIDERS strategy (predatory)
- targets edges with high value and weak enforcement
- increases corridor risk via incidents
- claims edges where it raids successfully

### 5.3 GUILD strategy (economic)
- invests in security for key routes
- optionally reduces market urgency by funding production later (v2)

All choices deterministic:
- score each opportunity with faction-specific weights and pick top K.

---

## 6) Wiring factions into interference (0264)

Modify interference system to support “actor attribution”:
- incidents include `faction_id` in payload (when spawned via faction action)
- “shadow interference” can remain as fallback if no factions enabled.

Implement `run_faction_actions_for_day(world, day)`:
- for each faction, choose up to max_actions_per_faction_per_day
- translate actions into:
  - incident spawns (RAID_EDGE/EXTORT_DEPOT)
  - enforcement policy changes (INVEST_SECURITY → increase ward security budget or posture)
  - territory claim updates

Important: enforce global caps too (e.g., total faction incidents per day).

---

## 7) Territory claim update rules

On successful action:
- increase claim strength on target ward/edge: `strength += claim_gain_on_success` (clamp 0..1)

On failure/interdiction:
- decrease: `strength -= claim_loss_on_failure` (clamp)

Decay:
- daily: `strength *= (1 - claim_decay_per_day)`

Cap number of claims per faction:
- if over: evict lowest-strength claims deterministically (strength asc, key asc).

---

## 8) Beliefs + culture hooks

When a faction gains/loses territory:
- emit belief seeds / crumbs:
  - `faction_control:{ward}:{faction_id}`
  - `faction_threat:{edge}:{faction_id}`

Belief formation can convert these to cultural beliefs later.

---

## 9) Telemetry + cockpit additions

Metrics:
- `metrics["factions"]["count"]`
- `metrics["factions"]["actions_taken"]`
- TopK:
  - `factions.top_raids` (by value)
  - `factions.top_claims` (by strength)
  - `factions.hot_edges` (edge contested)

Cockpit:
- list factions with influence/budget/capacity
- top claimed wards and edges per faction (bounded)
- recent faction-attributed incidents

---

## 10) Tests (must-have)

Create `tests/test_real_factions_v1.py`.

### T1. Determinism
- clone world; run N days; same actions and same territory changes.

### T2. Caps
- max_actions_per_faction_per_day enforced; claim caps enforced.

### T3. Territory update on success/failure
- success increases strength; interdiction decreases strength.

### T4. Persistence
- snapshot roundtrip preserves territories and yields stable continuation.

### T5. Seed vault export stable
- factions.json stable ordering.

### T6. Integration with enforcement
- higher state security reduces raider success (deterministic).

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add faction data model + world state
- Create `src/dosadi/world/factions.py` (or runtime equivalent) with Faction, FactionTerritory, configs, state
- Add world.factions/world.faction_territory/world.faction_cfg/world.faction_state to snapshots

### Task 2 — Seed vault persistence/export
- Ensure faction territories are persisted in seed vault
- Add stable `factions.json` export with sorted keys

### Task 3 — Opportunity set + deterministic action selection
- Build bounded opportunity basket from telemetry (urgent materials, risky edges, weak enforcement wards)
- Implement deterministic scoring per faction kind
- Execute up to max actions per faction/day

### Task 4 — Wire to incidents + enforcement + territory
- Raiders spawn faction-attributed interference incidents
- State invests in enforcement budgets/policy
- Update territory claims on success/failure with decay and caps

### Task 5 — Telemetry + cockpit + beliefs
- Add metrics/topK, render factions panel
- Emit belief crumbs on claim changes

### Task 6 — Tests
- Add `tests/test_real_factions_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - factions act deterministically using bounded opportunities,
  - raiders conduct actor-attributed predation,
  - state invests in enforcement and stabilizes routes,
  - territory claims evolve and persist,
  - cockpit shows faction status and territory,
  - seed vault saves/loads faction territories.

---

## 13) Next slice after this trunk step

**Corridor Improvements v1** — the planner can propose infrastructure projects
to reduce risk, travel time, and suit wear (closing A1 + A2 loops).
