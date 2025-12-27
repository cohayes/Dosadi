---
title: Religious_Schisms_and_Holy_Conflict_v1_Implementation_Checklist
doc_id: D-RUNTIME-0300
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0274   # Diplomacy & Treaties v1
  - D-RUNTIME-0278   # War & Raids v1
  - D-RUNTIME-0286   # Media & Information Channels v1
  - D-RUNTIME-0288   # Religion & Ritual Power v1
  - D-RUNTIME-0291   # Wages, Rations & Class Stratification v1
  - D-RUNTIME-0296   # Policing Doctrine v2
  - D-RUNTIME-0297   # Insurgency & Counterinsurgency v1
  - D-RUNTIME-0298   # Civil War & Fragmentation v1
  - D-RUNTIME-0299   # Succession & Leadership Legitimacy v1
---

# Religious Schisms & Holy Conflict v1 — Implementation Checklist

Branch name: `feature/religious-schisms-holy-conflict-v1`

Goal: let religion fracture into sects and become geopolitics so that:
- doctrinal disputes generate schisms (new sect identities),
- sect power produces theocratic polities and holy wars,
- martyrdom and ritual legitimacy feed insurgency and leadership claims,
- long-run seeds diverge into secular empires, theocracies, or sectarian balkanization.

v1 is macro sect dynamics, not individual faith simulation.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same schisms and conflict escalations.
2. **Bounded.** TopK sects per polity; bounded schism events.
3. **Legible.** Explain what split, why, and who backed it.
4. **Composable.** Hooks into ideology/media, leadership legitimacy, insurgency, and sovereignty.
5. **Phase-aware.** P1 ideological hardening; P2 sectarian conflict.
6. **Tested.** Schism triggers, sect diffusion, persistence.

---

## 1) Concept model

We build on Religion & Ritual Power (0288) by adding:
- named **sects** with doctrines, strength, and territorial distribution,
- a **schism pressure** signal driven by hardship, culture wars, leadership legitimacy, and propaganda,
- and **holy conflict** escalation when sects become political-military actors.

Sects can:
- compete inside one polity (internal strife),
- sponsor insurgent cells (martyr cult overlaps),
- or capture leadership and become a theocracy (0299/0298).

---

## 2) Sect model (v1)

Represent a bounded set of sect archetypes:
- `ORTHODOX` (central ritual authority)
- `ASCETIC_REFORM` (anti-corruption, austerity)
- `MARTYR_CULT` (suffering → salvation; volatile)
- `WELL_MYSTICS` (water control as sacred duty)
- `SYNTHETISTS` (cosmopolitan blend; often targeted)
- `APOCALYPTIC` (end-times; insurgency-prone)

Each sect has:
- doctrine axes (purity, hierarchy, violence, universalism)
- recruitment drivers (hardship/inequality, policing terror, war)
- preferred political strategy (capture, separatism, underground)

---

## 3) Data structures

Create `src/dosadi/runtime/religion_sects.py`

### 3.1 Config
- `@dataclass(slots=True) class SectsConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 14`
  - `deterministic_salt: str = "sects-v1"`
  - `max_sects_total: int = 24`
  - `max_sects_per_polity: int = 6`
  - `schism_base_rate: float = 0.001`
  - `schism_pressure_scale: float = 0.35`
  - `diffusion_rate: float = 0.05`
  - `holy_conflict_threshold: float = 0.70`

### 3.2 Sect definition
- `@dataclass(slots=True) class SectDef:`
  - `sect_id: str`                 # "sect:orthodox:1"
  - `name: str`
  - `archetype: str`
  - `doctrine: dict[str, float]`   # axes 0..1
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Polity sect state
- `@dataclass(slots=True) class PolitySectState:`
  - `polity_id: str`
  - `strength_by_sect: dict[str, float] = field(default_factory=dict)`    # 0..1 shares sum<=1
  - `schism_pressure: float = 0.0`     # 0..1
  - `conflict_intensity: float = 0.0`  # 0..1
  - `dominant_sect: str | None = None`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.4 Schism event record (bounded)
- `@dataclass(slots=True) class SchismEvent:`
  - `day: int`
  - `polity_id: str`
  - `parent_sect_id: str`
  - `new_sect_id: str`
  - `reason_codes: list[str]`
  - `backers: list[str]`            # factions, leaders

World stores:
- `world.sects_cfg`
- `world.sects: dict[str, SectDef]`
- `world.sects_by_polity: dict[str, PolitySectState]`
- `world.schism_events: list[SchismEvent]` (bounded)

Persist all in snapshots and seeds.

---

## 4) Schism pressure computation (biweekly)

Inputs:
- hardship/inequality (0291)
- culture war intensity (0270)
- leadership legitimacy mismatch (0299) (ideological legitimacy low)
- policing terror/backlash (0296)
- media propaganda distortion (0286/0294)
- war/civil fragmentation pressure (0278/0298)

Compute `schism_pressure = clamp(base + scale * f(inputs), 0..1)`.

---

## 5) Schism event generation (bounded)

If `pseudo_rand < schism_base_rate * (1 + schism_pressure_scale*schism_pressure)`:
- choose parent sect:
  - highest strength but with high internal tension (doctrine mismatch with policy)
- generate new sect:
  - derive doctrine by mutating parent axes deterministically
  - name generated from archetype and polity id (stable)
- allocate initial strength from parent (small share transfer)
- record SchismEvent with reason codes:
  - CORRUPTION_SCANDAL, AUSTERITY_SHOCK, MARTYRDOM, LEADER_HERESY, WAR_TRAUMA, etc.

Bound max sects per polity and total.

---

## 6) Sect diffusion and competition

Each update:
- sect strength shifts:
  - toward sects aligned with current hardship and policy
  - toward sects amplified by media channels
  - away from sects suffering repression or legitimacy scandals
- diffusion:
  - sects spread along corridors (macro) at diffusion_rate
- crackdown policy:
  - policing doctrine affects whether repression increases martyrdom (0296)

Bound normalization:
- keep strength shares <=1; leftover is “non-affiliated” or baseline faith.

---

## 7) Holy conflict escalation

If:
- dominant sect > threshold OR conflict_intensity > holy_conflict_threshold
AND
- leadership sponsor faction aligned strongly with sect
Then trigger holy conflict dynamics:

v1 effects:
- increase insurgency emergence for MARTYR_CULT/APOCALYPTIC (0297)
- increase sovereignty fracture pressure for sect-minority wards (0298)
- shift leadership office_type toward THEOCRAT if sect captures governance (0299)
- escalate war/raids between sect-aligned polities (0278)

Represent as:
- `conflict_intensity` increase,
- periodic incidents.

---

## 8) Incidents

Use Incident Engine (0242):
- `SCHISM_DECLARED`
- `HERESY_TRIAL`
- `ICONOCLASM_RIOT`
- `MARTYRDOM_PROCESSION`
- `HOLY_WAR_DECLARED`
- `TEMPLE_BURNING`

Each incident modifies legitimacy components (0299) and polarization (0285/0270).

---

## 9) Telemetry + cockpit

Metrics:
- `metrics["sects"]["polities_with_schism"]`
- `metrics["sects"]["schism_events"]`
- `metrics["sects"]["avg_schism_pressure"]`
- `metrics["sects"]["holy_conflicts_active"]`

TopK:
- polities by conflict_intensity
- fastest growing sects
- martyrdom events count

Cockpit:
- polity religion panel: sect shares, schism pressure, conflict intensity
- sect registry: doctrines, where strong, recent schisms
- timeline: schisms → leadership shifts → conflicts → fragmentation

Events:
- `SECT_DIFFUSION`
- `SCHISM_EVENT`
- `HOLY_CONFLICT_ESCALATED`
- `SECT_CAPTURED_GOVERNANCE`

---

## 10) Persistence / seed vault

Export:
- `seeds/<name>/sects.json` with sect definitions and polity states.

---

## 11) Tests (must-have)

Create `tests/test_religious_schisms_holy_conflict_v1.py`.

### T1. Determinism
- same inputs → same schism triggers and outcomes.

### T2. Schism pressure responds to hardship and culture wars
- increasing hardship/culture intensity raises schism_pressure.

### T3. Schism creates new sect and reallocates strength
- new sect appears; parent loses share; bounds hold.

### T4. Repression increases martyr sect growth
- terror policing increases martyr recruitment (martyrdom feedback).

### T5. Holy conflict escalates at thresholds
- strong dominant sect + conflict intensity triggers holy conflict effects.

### T6. Snapshot roundtrip
- sect defs and polity shares persist across snapshot/load and seeds.

---

## 12) Codex Instructions (verbatim)

### Task 1 — Add sects module + state
- Create `src/dosadi/runtime/religion_sects.py` with SectsConfig, SectDef, PolitySectState, SchismEvent
- Add world.sects and sects_by_polity to snapshots + seeds

### Task 2 — Implement schism pressure and schism events
- Compute schism_pressure from hardship, culture wars, leadership legitimacy mismatch, policing terror, media distortion, and war pressure
- Create bounded schism events and new sect definitions deterministically

### Task 3 — Implement diffusion and competition
- Update sect strengths with diffusion along corridors and repression/martyrdom feedback

### Task 4 — Implement holy conflict escalation hooks
- When thresholds crossed, emit incidents and adjust inputs to insurgency, sovereignty, and leadership

### Task 5 — Cockpit + tests
- Add polity religion panels and sect registry
- Add `tests/test_religious_schisms_holy_conflict_v1.py` (T1–T6)

---

## 13) Definition of Done

- `pytest` passes.
- With enabled=True:
  - sect shares evolve and schisms occur deterministically under pressure,
  - repression can backfire via martyrdom growth,
  - holy conflict can escalate and reshape leadership and sovereignty,
  - 200-year seeds diversify into sectarian outcomes,
  - cockpit explains “which faith split, why, and what it did to politics.”

---

## 14) Next slice after this

**Trade Federations & Cartels v1** — economic alliances as sovereignty:
- cartel pricing, joint embargoes,
- and guild federations that rival polities.
