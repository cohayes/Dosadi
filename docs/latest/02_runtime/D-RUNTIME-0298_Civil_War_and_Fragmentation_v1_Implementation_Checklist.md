---
title: Civil_War_and_Fragmentation_v1_Implementation_Checklist
doc_id: D-RUNTIME-0298
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0264   # Faction Interference v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0274   # Diplomacy & Treaties v1
  - D-RUNTIME-0278   # War & Raids v1
  - D-RUNTIME-0281   # Migration & Refugees v1
  - D-RUNTIME-0282   # Urban Growth & Zoning v1
  - D-RUNTIME-0291   # Wages, Rations & Class Stratification v1
  - D-RUNTIME-0296   # Policing Doctrine v2
  - D-RUNTIME-0297   # Terror, Insurgency & Counterinsurgency v1
---

# Civil War & Fragmentation v1 — Implementation Checklist

Branch name: `feature/civil-war-fragmentation-v1`

Goal: allow the empire to splinter into competing polities when control fails so that:
- sovereignty over wards and corridors becomes contested,
- treaties can break and new treaties form,
- civil conflict changes trade, migration, and enforcement,
- the simulation can produce divergent 200-year “seed outcomes” (unified empire, fractured warlords, theocracy, etc.).

v1 is macro sovereignty + frontlines + splinter states, not tactical battles.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same fragmentation outcomes.
2. **Bounded.** Limited number of polities, bounded contested corridors.
3. **Legible.** Clear “who controls what” map and why it changed.
4. **Phase-sensitive.** P2 more likely; P0 should almost never fragment.
5. **Composable.** Hooks into war/raids, diplomacy, customs, migration, markets.
6. **Tested.** Split/merge mechanics, contested sovereignty, persistence.

---

## 1) Concept model

We represent political control as:
- **polities** (empire or splinter regimes),
- each controlling:
  - a set of wards (territory),
  - a set of corridors (sovereignty claims),
  - institutions (governance styles) and enforcement postures,
  - legitimacy and capacity.

Fragmentation occurs when:
- governance failures accumulate (0271),
- insurgency support/capability high (0297),
- policing terror/backlash high (0296),
- economic hardship/inequality high (0291),
- and central legitimacy collapses.

The result is:
- a new polity “breaks away” and claims wards,
- corridors become contested borders,
- the old empire may attempt reconquest (macro war),
- or negotiate autonomy (treaties).

---

## 2) Data structures

Create `src/dosadi/runtime/sovereignty.py`

### 2.1 Config
- `@dataclass(slots=True) class SovereigntyConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 7`
  - `deterministic_salt: str = "sovereignty-v1"`
  - `max_polities: int = 6`
  - `max_contested_corridors: int = 30`
  - `split_threshold: float = 0.75`
  - `merge_threshold: float = 0.25`
  - `border_friction: float = 0.20`
  - `reconquest_bias: float = 0.55`          # default central posture
  - `negotiation_bias: float = 0.45`

### 2.2 Polity state
- `@dataclass(slots=True) class PolityState:`
  - `polity_id: str`                  # "polity:empire" or "polity:wardlord:<n>"
  - `name: str`
  - `capital_ward_id: str`
  - `style: str`                      # THEOCRACY|MILITARY|GUILD_CARTEL|COUNCIL|Warlord
  - `legitimacy: float = 0.5`         # 0..1
  - `capacity: float = 0.5`           # 0..1 (enforcement/admin)
  - `cohesion: float = 0.5`           # 0..1
  - `treasury: float = 0.0`           # optional: or reference to ledger
  - `notes: dict[str, object] = field(default_factory=dict)

### 2.3 Territory and borders
- `@dataclass(slots=True) class TerritoryState:`
  - `ward_control: dict[str, str] = field(default_factory=dict)`          # ward_id -> polity_id
  - `corridor_control: dict[str, str] = field(default_factory=dict)`      # corridor_id -> polity_id
  - `corridor_contested: dict[str, list[str]] = field(default_factory=dict)` # corridor_id -> [polity_ids]
  - `last_update_day: int = -1`

### 2.4 Conflict fronts (macro)
- `@dataclass(slots=True) class ConflictFront:`
  - `front_id: str`
  - `corridor_id: str`
  - `polity_a: str`
  - `polity_b: str`
  - `intensity: float`               # 0..1
  - `status: str`                    # COLD|SKIRMISH|OPEN_WAR
  - `last_update_day: int = -1`

World stores:
- `world.sov_cfg`
- `world.polities: dict[str, PolityState]`
- `world.territory: TerritoryState`
- `world.fronts: dict[str, ConflictFront]`
- `world.sov_events: list[dict]` (bounded)

Persist in snapshots and seeds.

---

## 3) Initialization

On new world:
- create `polity:empire` with all wards controlled.
- corridor_control defaults to empire.
- contested empty.

---

## 4) Fragmentation trigger (weekly)

Compute a “fracture pressure” per ward:
- governance failure score (0271)
- insurgency support/capability (0297)
- hardship/inequality (0291)
- policing terror/backlash (0296)
- comms blindness (0294) (optional input)
- faction interference (0264) (rival claims)

Aggregate to a regional cluster (simple v1):
- if TopK wards exceed split_threshold and are adjacent (via corridors),
  propose split.

Split selection:
- choose seed ward as capital (highest fracture pressure)
- define cluster = BFS up to N wards (bounded) where pressure high and connected
- create new polity if max_polities allows.

New polity style:
- if religion dominance high → THEOCRACY
- if warlords/guards dominate → MILITARY/Warlord
- if guild capture high → GUILD_CARTEL
- else COUNCIL

Assign ward_control for cluster to new polity.

Corridors connecting cluster to empire become contested borders.

---

## 5) Contested corridors and border friction

For contested corridors:
- increase corridor risk (0261) via border_friction and war intensity
- increase customs enforcement and tariffs (0275/0295)
- increase smuggling opportunities (0276)

Control resolution:
- each week, contested corridor can flip control based on:
  - polity capacity/legitimacy and local support
  - war intensity and raid outcomes
  - insurgency presence
Deterministic tie breaks.

---

## 6) Civil war escalation and resolution

Fronts evolve:
- intensity rises when reconquest_bias dominates and diplomacy fails
- intensity falls when negotiation_bias dominates and treaties form (0274)

Resolution types:
- `AUTONOMY_TREATY` (splinter remains but trade reopens)
- `RECONQUEST` (wards rejoin empire)
- `PERMANENT_SPLIT` (stabilized borders)
- `BALKANIZATION` (splinter splits again if cohesion low)

Keep v1 simple: only reconquest vs autonomy treaty.

---

## 7) Integration with war/raids and diplomacy/customs

- War engine (0278):
  - allow raids across contested corridors
  - war intensity modifies raid frequency and damage
- Diplomacy (0274):
  - enable treaties between polities
- Customs (0275):
  - border corridors become customs checkpoints with tariffs/embargo potential
- Market signals (0263):
  - contested borders reduce trade and raise prices
- Migration (0281):
  - people flee war zones; camp share rises

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["sovereignty"]["polities_count"]`
- `metrics["sovereignty"]["contested_corridors"]`
- `metrics["sovereignty"]["fronts_open_war"]`
- `metrics["sovereignty"]["ward_switches"]` (control changes)

TopK:
- wards with highest fracture pressure
- hottest fronts by intensity
- polities by legitimacy/capacity

Cockpit:
- sovereignty map: ward_control and corridor_control
- contested borders view: which corridors are disputed and why
- polity page: style, capital, legitimacy/capacity, economy proxies
- timeline: splits, treaties, reconquests

Events:
- `POLITY_SPLIT_CREATED`
- `CORRIDOR_CONTESTED`
- `FRONT_ESCALATED`
- `TREATY_AUTONOMY_SIGNED`
- `WARD_RECONQUERED`
- `POLITY_COLLAPSED`

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/sovereignty.json` with polities, territory, and fronts.

---

## 10) Tests (must-have)

Create `tests/test_civil_war_fragmentation_v1.py`.

### T1. Determinism
- same pressures → same split/cluster and border set.

### T2. High fracture pressure creates split
- when threshold crossed, new polity appears.

### T3. Contested corridors increase risk
- contested corridors raise risk multipliers deterministically.

### T4. Reconquest vs autonomy
- changes in biases and capacity alter resolution outcomes.

### T5. Market and migration impacts
- border contest increases prices and increases camp share proxy.

### T6. Snapshot roundtrip
- polities and territory persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add sovereignty module + state
- Create `src/dosadi/runtime/sovereignty.py` with SovereigntyConfig, PolityState, TerritoryState, ConflictFront
- Initialize `polity:empire` and territory control; persist in snapshots + seeds

### Task 2 — Implement fracture pressure and split creation
- Compute ward fracture pressure from governance failures, insurgency, hardship, policing backlash
- Create bounded connected cluster splits; assign new polities and contested corridors

### Task 3 — Implement contested corridor and front evolution
- Add border friction risk modifiers and control resolution
- Create/maintain conflict fronts and escalate/de-escalate based on biases and diplomacy

### Task 4 — Integrate with war/raids, customs, markets, and migration
- Border contest affects raid patterns, trade costs, and displacement

### Task 5 — Cockpit + tests
- Add sovereignty map and polity pages
- Add `tests/test_civil_war_fragmentation_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - polities can split deterministically from fracture pressure,
  - borders become contested and reshape corridors, trade, and migration,
  - civil conflict can escalate or settle into autonomy treaties,
  - long-run seeds produce distinct political geographies,
  - cockpit explains “who controls what and why.”

---

## 13) Next slice after this

**Succession & Leadership Legitimacy v1** — regime change rules:
- coups, dynastic succession, council replacements,
- and legitimacy shocks that precipitate splits or reforms.
