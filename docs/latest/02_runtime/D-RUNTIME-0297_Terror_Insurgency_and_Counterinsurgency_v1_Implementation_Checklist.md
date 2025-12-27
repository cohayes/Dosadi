---
title: Terror_Insurgency_and_Counterinsurgency_v1_Implementation_Checklist
doc_id: D-RUNTIME-0297
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0264   # Faction Interference v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0277   # Crackdown Strategy v1
  - D-RUNTIME-0278   # War & Raids v1
  - D-RUNTIME-0281   # Migration & Refugees v1
  - D-RUNTIME-0286   # Media & Information Channels v1
  - D-RUNTIME-0287   # Counterintelligence & Espionage v1
  - D-RUNTIME-0291   # Wages, Rations & Class Stratification v1
  - D-RUNTIME-0294   # Comms Failure & Jamming v1
  - D-RUNTIME-0296   # Policing Doctrine v2
---

# Terror, Insurgency & Counterinsurgency v1 — Implementation Checklist

Branch name: `feature/insurgency-counterinsurgency-v1`

Goal: add clandestine cell networks so that:
- hardship, camps, and terror policing create recruitment pools,
- insurgent cells run sabotage, assassinations, and propaganda,
- counterinsurgency trades effectiveness vs legitimacy,
- prolonged instability can tip into civil fragmentation.

v1 is macro cell networks with TopK cells per ward (no per-agent stealth sim).

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same cell emergence and ops outcomes.
2. **Bounded.** TopK cells per ward; bounded active ops; no agent-level stealth.
3. **Two-sided game.** Insurgents adapt; state responds with doctrine choices.
4. **Phase-aware.** P1 begins; P2 intensifies and splinters.
5. **Composable.** Integrates with policing, comms, media, raids, and governance failures.
6. **Tested.** Emergence, detection, suppression, and persistence.

---

## 1) Concept model

Insurgency is modeled via:
- **cells** operating in wards/corridors,
- **support base** (population sympathy) driven by hardship and ideology,
- **capability** (weapons, training, money) driven by smuggling, war, and patronage,
- **operations** executed periodically.

Counterinsurgency is modeled via:
- policing doctrine (0296),
- counterintel (0287),
- comms resilience (0294),
- targeted crackdowns (0277) and raids (0278).

---

## 2) Cell archetypes (v1)

Define 4 cell archetypes:
- `REVOLUTIONARY` (ideology-driven; targets institutions)
- `SEPARATIST` (territory-driven; targets borders/corridors)
- `CRIMINAL_INSURGENT` (profit-driven; merges with smuggling)
- `MARTYR_CULT` (religion-driven; high willingness to die)

Each archetype defines:
- preferred operation types,
- recruitment drivers (hardship, policing terror, sect adherence),
- and resilience to repression.

---

## 3) Data structures

Create `src/dosadi/runtime/insurgency.py`

### 3.1 Config
- `@dataclass(slots=True) class InsurgencyConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 7`
  - `deterministic_salt: str = "insurgency-v1"`
  - `max_cells_per_ward: int = 3`
  - `max_ops_active: int = 24`
  - `base_emergence_rate: float = 0.002`
  - `base_op_rate: float = 0.08`
  - `suppression_effect: float = 0.6`
  - `backlash_effect: float = 0.35`
  - `cell_decay_rate: float = 0.05`

### 3.2 Cell state
- `@dataclass(slots=True) class CellState:`
  - `cell_id: str`
  - `ward_id: str`
  - `archetype: str`
  - `support: float = 0.0`           # 0..1
  - `capability: float = 0.0`        # 0..1
  - `secrecy: float = 0.5`           # 0..1 (higher is harder to detect)
  - `heat: float = 0.0`              # 0..1 (how “hot”/exposed)
  - `morale: float = 0.5`            # 0..1
  - `status: str = "DORMANT"`        # DORMANT|ACTIVE|BROKEN
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

### 3.3 Ops plan + outcome
- `@dataclass(slots=True) class CellOpPlan:`
  - `op_id: str`
  - `cell_id: str`
  - `ward_id: str`
  - `op_type: str`
  - `day_started: int`
  - `day_end: int`
  - `target_kind: str`               # FACILITY|RELAY|CORRIDOR|LEADER|CUSTOMS
  - `target_id: str`
  - `intensity: float`
  - `reason: str`
  - `score_breakdown: dict[str, float] = field(default_factory=dict)`

- `@dataclass(slots=True) class CellOpOutcome:`
  - `op_id: str`
  - `day: int`
  - `status: str`                    # ACTIVE|SUCCEEDED|FAILED|DETECTED|ROLLED_UP|EXPIRED
  - `effects: dict[str, object] = field(default_factory=dict)`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.insurgency_cfg`
- `world.cells_by_ward: dict[str, list[CellState]]`
- `world.cell_ops_active: dict[str, CellOpPlan]`
- `world.cell_ops_history: list[CellOpOutcome]` (bounded)

Persist cells and active ops in snapshots and seeds.

---

## 4) Emergence model (weekly)

Implement:
- `run_insurgency_week(world, day)`

Emergence drivers:
- hardship + inequality (0291)
- camps share and displacement (0281)
- terror policing / backlash proxy (0296)
- ideology polarization (0285/0270)
- comms outages (0294) (state blindness)
- smuggling strength (0276) provides capability

Compute `p_emerge` per ward:
- base_emergence_rate * f(drivers) with phase multiplier
If triggered and slots available (max_cells_per_ward):
- spawn cell with archetype chosen by dominant drivers.

Initialize:
- support ~ hardship-driven
- capability ~ smuggling/war-driven
- secrecy depends on counterintel posture.

Deterministic.

---

## 5) Cell growth/decay updates

Each week:
- support drifts up if hardship/backlash high and propaganda success high
- support drifts down if services improve, legitimacy rises, community policing grows
- capability drifts up with smuggling/foreign help/war loot
- capability drifts down with seizures, arrests, and broken supply

Heat increases when ops run; decreases with time if not detected.

Cells can become BROKEN if capability low and heat high under heavy counterintel.

---

## 6) Operation planning (bounded)

Cell operations (v1):
- `SABOTAGE_RELAY` (comms outage or degrade) (ties to 0294)
- `SABOTAGE_DEPOT` (stockpile loss or delay) (0257)
- `ATTACK_CONVOY` (increase corridor losses) (0261/0293)
- `ASSASSINATION_ATTEMPT` (leadership shock; legitimacy hit) (0269/0271)
- `BOMB_CUSTOMS` (reduce enforcement; increase leak) (0295)
- `PROPAGANDA_BROADCAST` (increase polarization; reduce legitimacy) (0286/0285)

Plan TopK ops:
- target high-value nodes, chokepoints, and weak wards.
Cap active ops: max_ops_active.

---

## 7) Detection and roll-up (counterinsurgency)

Detection probability depends on:
- policing capacity and doctrine (0296)
- counterintel coverage (0287)
- comms reliability (0294)
- inspections and informant reliance (0296)

If detected:
- state can choose response (policy dial):
  - targeted arrests (procedural)
  - sweep raids (militarized)
  - collective punishment (terror)
Each response:
- reduces cell capability/support short-run
- but may increase backlash and recruitment long-run (especially terror)

Roll-up mechanic:
- if cell detected and counterintel strong:
  - can reduce secrecy and “discover” linked cells (bounded to same ward)

Keep v1 simple: only within ward.

---

## 8) Effects wiring

- Comms (0294): relay sabotage increases outages and jamming-like modifiers
- Sanctions/customs (0295): customs bomb reduces enforcement effectiveness
- Insurance (0293): convoy attacks increase losses, premiums rise
- Governance failures (0271): assassination attempt increases instability
- War/raids (0278): insurgency can trigger raids or be exploited by rival factions
- Media/ideology (0286/0285): propaganda ops change polarization inputs

---

## 9) Incidents

Use Incident Engine (0242):
- `TERROR_ATTACK`
- `ASSASSINATION_SHOCK`
- `INFRASTRUCTURE_SABOTAGE`
- `COUNTERINSURGENCY_SWEEP`
- `MARTYRDOM_EVENT`
- `RIOT_AFTER_REPRISALS`

---

## 10) Telemetry + cockpit

Metrics:
- `metrics["insurgency"]["cells_active"]`
- `metrics["insurgency"]["support_avg"]`
- `metrics["insurgency"]["ops_active"]`
- `metrics["insurgency"]["ops_detected"]`
- `metrics["insurgency"]["sabotage_events"]`
- `metrics["insurgency"]["backlash_proxy"]`

TopK:
- wards by support/capability
- cells by heat
- targets most attacked

Cockpit:
- insurgency map: cell count and support per ward
- cell detail: archetype, support/capability/secrecy/heat, recent ops
- counterinsurgency panel: doctrine, counterintel, detection rates, outcomes
- timeline: ops → response → backlash → recruitment

Events:
- `CELL_EMERGED`
- `CELL_OP_STARTED`
- `CELL_OP_SUCCEEDED`
- `CELL_OP_DETECTED`
- `CELL_ROLLED_UP`
- `BACKLASH_SPIKE`

---

## 11) Persistence / seed vault

Export:
- `seeds/<name>/insurgency.json` with cells and active ops.

---

## 12) Tests (must-have)

Create `tests/test_insurgency_counterinsurgency_v1.py`.

### T1. Determinism
- same drivers → same emergence and ops outcomes.

### T2. Hardship/backlash increases emergence
- higher hardship/terror policing yields more cells.

### T3. Counterintel improves detection
- higher counterintel and procedural policing increases detection rate.

### T4. Terror response increases backlash
- terror response reduces capability but increases support via backlash.

### T5. Sabotage affects comms
- sabotage relay op increases comms outage modifiers.

### T6. Snapshot roundtrip
- cells and active ops persist across snapshot/load and seeds.

---

## 13) Codex Instructions (verbatim)

### Task 1 — Add insurgency module + cell state
- Create `src/dosadi/runtime/insurgency.py` with InsurgencyConfig, CellState, CellOpPlan, CellOpOutcome
- Add world.cells_by_ward and active ops to snapshots + seeds

### Task 2 — Implement weekly emergence and growth/decay
- Compute p_emerge from hardship, camps, policing backlash, ideology polarization, comms, smuggling
- Update support/capability/secrecy/heat

### Task 3 — Implement bounded op planning and resolution
- Plan TopK ops, resolve success vs detection deterministically
- Apply effects to comms, customs, convoys, legitimacy, and media

### Task 4 — Implement counterinsurgency responses
- Use policing doctrine and counterintel to detect and roll up cells
- Apply response effects and backlash tradeoffs

### Task 5 — Cockpit + tests
- Add insurgency dashboards and timelines
- Add `tests/test_insurgency_counterinsurgency_v1.py` (T1–T6)

---

## 14) Definition of Done

- `pytest` passes.
- With enabled=True:
  - cells emerge from hardship/backlash and grow with support/capability,
  - insurgents execute sabotage/attack/propaganda operations,
  - state detects and responds with doctrine-dependent outcomes,
  - terror policing can radicalize and amplify recruitment loops,
  - insurgency can blind the empire and collapse corridor safety (D3),
  - cockpit explains “where the insurgency is growing and why.”

---

## 15) Next slice after this

**Civil War & Fragmentation v1** — splinter regimes and contested sovereignty:
- territory splits,
- corridor sovereignty contests,
- and the empire breaking into competing polities.
