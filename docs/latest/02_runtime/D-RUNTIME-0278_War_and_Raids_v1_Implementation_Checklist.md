---
title: War_and_Raids_v1_Implementation_Checklist
doc_id: D-RUNTIME-0278
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0231   # Save/Load Seed Vault
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0259   # Expansion Planner v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0264   # Faction Interference v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0267   # Corridor Improvements v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0277   # Crackdown Strategy v1
---

# War & Raids v1 — Implementation Checklist

Branch name: `feature/war-raids-v1`

Goal: formalize A2 predation escalation into structured operations:
- raids as planned, resource-consuming actions (not just random incidents),
- territory pressure and capture mechanics,
- corridor collapse dynamics under D3 harshness,
- credible responses: escorts, crackdowns, treaties, fortification, and retaliation.

v1 is **macro war**, not tactical combat.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same raid decisions and outcomes.
2. **Bounded.** Operate on TopK corridors/wards; avoid per-agent combat loops.
3. **Explainable.** Every raid has a reason, target, plan, and outcome summary.
4. **Composable.** Raids affect logistics, customs, smuggling, treaties, and legitimacy.
5. **Escalation ladder.** From harassment → raids → corridor collapse → territory capture.
6. **Tested.** Outcome determinism, corridor collapse, territory updates, persistence.

---

## 1) Core concept

A raid is an **operation** launched by an aggressor faction against a target:
- a corridor segment (interdiction / toll / collapse),
- a shipment class (water/food/material),
- a ward node (hit-and-run theft, intimidation, sabotage),
- a facility (sabotage/steal parts).

Raids have:
- a planner (aggressor),
- a defender posture (ward + enforcement),
- a time window,
- costs and rewards,
- and consequences.

---

## 2) Data structures

Create `src/dosadi/runtime/war.py`

### 2.1 Config
- `@dataclass(slots=True) class WarConfig:`
  - `enabled: bool = False`
  - `max_ops_per_day: int = 3`
  - `candidate_topk: int = 24`
  - `raid_duration_days: int = 3`
  - `deterministic_salt: str = "war-v1"`
  - `collapse_threshold: float = 1.0`      # corridor stress level at which it collapses
  - `stress_decay_per_day: float = 0.05`
  - `raid_stress_per_success: float = 0.12`
  - `territory_pressure_per_week: float = 0.05`

### 2.2 Operation model
- `@dataclass(slots=True) class RaidPlan:`
  - `op_id: str`
  - `aggressor_faction: str`
  - `target_kind: str`              # "corridor"|"ward"|"shipment"|"facility"
  - `target_id: str`
  - `start_day: int`
  - `end_day: int`
  - `intensity: float`              # 0..1
  - `objective: str`                # "loot"|"disrupt"|"capture_pressure"
  - `expected_loot: dict[str, float] = field(default_factory=dict)`
  - `expected_cost: dict[str, float] = field(default_factory=dict)`
  - `reason: str = ""
  - `score_breakdown: dict[str, float] = field(default_factory=dict)`

- `@dataclass(slots=True) class RaidOutcome:`
  - `op_id: str`
  - `day: int`
  - `status: str`                   # "active"|"succeeded"|"failed"|"aborted"|"expired"
  - `loot: dict[str, float] = field(default_factory=dict)`
  - `losses: dict[str, float] = field(default_factory=dict)`
  - `corridor_stress_delta: float = 0.0`
  - `territory_delta: dict[str, object] = field(default_factory=dict)`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.war_cfg`
- `world.raid_active: dict[str, RaidPlan]`
- `world.raid_history: list[RaidOutcome]` (bounded)
- `world.corridor_stress: dict[str, float]`  # corridor_id -> stress (0..inf)
- `world.territory_map` already exists (0266); extend with pressure fields (see below)

Persist active ops + corridor_stress + (optional bounded history) into snapshots and seeds.

---

## 3) Territory pressure and control (minimal v1)

Extend territory representation with:
- `pressure: dict[faction_id, float]` per ward (or per corridor node)
- `controller: faction_id | "ward:<ward_id>" | "state"` (existing)
- `last_changed_day`

Pressure evolves:
- raids increase aggressor pressure in targeted ward/corridor region
- defense actions and legitimacy reduce hostile pressure over time
- when pressure crosses threshold, control can flip (optional v1; can start with “influence only”)

v1 recommendation:
- implement **influence/pressure** fully,
- implement **control flip** only for corridor segments (not whole wards), to keep scope bounded.

---

## 4) Candidate selection (TopK)

For each aggressor faction eligible to raid (e.g., raiders/predators):
- build candidate targets from:
  - high-value corridors (water/food throughput, 0261/0263)
  - weak escort coverage (0261)
  - low legitimacy / high corruption wards (0269/0271)
  - treaty edges (0274) that, if broken, cause outsized disruption
  - border customs hotspots (0275) where extortion is possible

Select TopK by value/opportunity, deterministic tie-break by id.

---

## 5) Raid planning (utility + constraints)

Implement:
- `propose_raid_ops_for_day(world, day) -> list[RaidPlan]`

Constraints:
- aggressor needs capacity (budget, manpower proxy, morale proxy)
- do not exceed max_ops_per_day total across world
- cooldown per target kind/id (optional v1: 7 days)

Utility score components:
- value of loot (expected shipment/facility value)
- disruption value (harms defender economy)
- defensive strength penalty (escort + enforcement + crackdown presence)
- political risk penalty (if defender legitimacy high)
- retaliation risk (defender has strong enforcement)

Pick best plans and activate them.

---

## 6) Resolution mechanics (bounded, no combat sim)

Each active op resolves daily:
- compute success probability deterministically from:
  - op intensity
  - aggressor capacity
  - target defense strength:
    - escort coverage + crackdown modifiers + treaties + corridor improvements
  - environment difficulty (A1 harshness)
- resolve with deterministic pseudo-rand keyed on (salt, day, op_id)

Outcomes:
- If succeeds:
  - loot transfers to aggressor (ledger or resources)
  - corridor stress increases (if corridor op)
  - shipments delayed/interdicted (if shipment op)
  - facility wear increases or downtime event (if facility op)
  - pressure increases in region
- If fails:
  - aggressor losses (budget, capacity)
  - defender legitimacy may increase (propaganda success)
  - crackdown may intensify next day (0277 synergy)

---

## 7) Corridor collapse (D3 harshness)

Corridor stress model:
- each corridor has stress; decays slowly daily
- successful raids add stress
- lack of maintenance + harsh environment can add baseline stress (optional)
- when stress >= collapse_threshold:
  - corridor becomes “collapsed” for N days or until repaired
  - logistics must reroute (0261)
  - economic urgency spikes (0263)
  - institutions panic (0271 incidents)
Repair path:
- corridor improvements (0267) can reduce stress or rebuild collapsed corridors.

This is the “ecosystem depletion” mechanic you wanted.

---

## 8) Integration points

### 8.1 Logistics (0261) + Courier (0246)
- interdiction adds delay, seizure chance, reroute pressure
- collapsed corridors are unavailable

### 8.2 Crackdown (0277)
- crackdowns reduce raid success probability on targeted borders/corridors
- raid failures can boost crackdown candidate scores

### 8.3 Treaties (0274)
- raids can violate safe passage; treaty breach mechanics trigger
- treaties can reduce incentive to raid (utility penalty)

### 8.4 Ledger (0273)
- raids and extortion move budget points:
  - loot can be modeled as transfer from ward/faction accounts to aggressor
  - fines/tribute can be posted as forced tx reason `RAID_TRIBUTE`
- keep v1 bounded; do not simulate individual theft inventories.

### 8.5 Governance failures (0271) + Culture (0270)
- repeated raids increase unrest, factionalism, anti_state norms
- strong defense and fair enforcement reduce radicalization

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["war"]["ops_active"]`
- `metrics["war"]["ops_started"]`
- `metrics["war"]["ops_success"]`
- `metrics["war"]["corridor_collapses"]`
- `metrics["war"]["loot_total"]`

TopK:
- most stressed corridors
- most targeted wards
- factions by raid success rate

Cockpit:
- active raid ops list with reason and expected outcome
- corridor stress table and “collapse risk” view
- per ward: pressure/influence overlays

Events:
- `RAID_STARTED`
- `RAID_RESOLVED`
- `CORRIDOR_COLLAPSED`
- `CORRIDOR_REOPENED`
- `TERRITORY_PRESSURE_CHANGED`

---

## 10) Tests (must-have)

Create `tests/test_war_and_raids_v1.py`.

### T1. Determinism
- same state → same raid plan selection and outcomes.

### T2. Corridor stress and collapse
- repeated successful raids push stress over threshold and collapse corridor deterministically.

### T3. Reroute behavior
- when corridor collapsed, logistics avoids it (integration assertion or smoke test).

### T4. Crackdown interaction
- active crackdown reduces raid success probability and lowers successful outcomes (bounded).

### T5. Treaty breach effect
- raids on treaty corridors trigger treaty breach penalties.

### T6. Ledger loot transfers
- raid tribute/loot changes balances deterministically and never creates negative balances unless allowed.

### T7. Snapshot roundtrip
- active ops + corridor stress persist and continue deterministically after load.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add war module + state
- Create `src/dosadi/runtime/war.py` with WarConfig, RaidPlan, RaidOutcome
- Add world.raid_active, world.corridor_stress, and bounded raid_history to snapshots + seeds

### Task 2 — Implement raid planning (TopK)
- Build candidate targets from corridor throughput, weak escorts, and legitimacy/corruption signals
- Score and select plans deterministically; cap ops per day

### Task 3 — Implement daily raid resolution
- Deterministic success resolution and outcome application
- Apply loot/losses, delays/interdictions, and pressure updates
- Emit RAID_* events

### Task 4 — Corridor collapse mechanics
- Maintain corridor stress with decay and raid stress deltas
- Collapse corridor at threshold; reopen via repair/improvement actions
- Wire logistics/routing to treat collapsed corridors as blocked

### Task 5 — Telemetry + tests
- Cockpit views for raid ops and corridor stress
- Add `tests/test_war_and_raids_v1.py` (T1–T7)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - raider factions plan and execute raids deterministically,
  - corridor stress/collapse creates existential corridor failures under D3,
  - defenses (escorts, crackdowns, treaties, upgrades) measurably reduce harm,
  - outcomes persist into 200-year seeds,
  - cockpit can explain the war landscape and corridor fragility.

---

## 13) Next slice after this

**Fortifications & Militia v1** — buildable defensive infrastructure and local defense capacity:
- militia training as a tech/institution product,
- forts/waystations as deterrence,
- and long-run stability levers for the empire.
