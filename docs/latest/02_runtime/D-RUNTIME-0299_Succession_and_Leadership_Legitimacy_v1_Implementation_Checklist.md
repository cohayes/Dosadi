---
title: Succession_and_Leadership_Legitimacy_v1_Implementation_Checklist
doc_id: D-RUNTIME-0299
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
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0274   # Diplomacy & Treaties v1
  - D-RUNTIME-0286   # Media & Information Channels v1
  - D-RUNTIME-0287   # Counterintelligence & Espionage v1
  - D-RUNTIME-0291   # Wages, Rations & Class Stratification v1
  - D-RUNTIME-0296   # Policing Doctrine v2
  - D-RUNTIME-0297   # Insurgency & Counterinsurgency v1
  - D-RUNTIME-0298   # Civil War & Fragmentation v1
---

# Succession & Leadership Legitimacy v1 — Implementation Checklist

Branch name: `feature/succession-leadership-legitimacy-v1`

Goal: make regime change real so that:
- rulers/councils can be replaced via succession, coups, or purges,
- legitimacy shocks propagate into labor, insurgency, and fragmentation,
- factions compete to install leaders aligned with their ideology and interests,
- leadership continuity (or instability) becomes a long-run seed differentiator.

v1 is macro leadership state for each polity (empire and splinters), not character-level dynasties.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same succession outcomes.
2. **Bounded.** Polity-level leadership only; limited contender sets.
3. **Legibility.** Explain why leadership changed (events + scores).
4. **Phase-aware.** P2 increases coups/purges; P0 more orderly.
5. **Composable.** Hooks into policing doctrine, media, diplomacy, insurgency, and sovereignty.
6. **Tested.** Trigger rules, transitions, persistence.

---

## 1) Leadership model (v1)

Each polity has:
- a leadership form and office type:
  - `SOVEREIGN` (king/duke figure)
  - `COUNCIL` (proto-council / senate)
  - `THEOCRAT` (high priest)
  - `WARLORD` (military commander)

- a legitimacy score (0..1) that decomposes into:
  - performance legitimacy (stability/food/water)
  - procedural legitimacy (rule-of-law, orderly succession)
  - ideological legitimacy (alignment with dominant culture/religion)
  - fear legitimacy (terror policing; short-run)

Leadership changes can be:
- orderly succession
- council reshuffle
- coup
- purge
- assassination shock (from insurgency)

---

## 2) Data structures

Create `src/dosadi/runtime/leadership.py`

### 2.1 Config
- `@dataclass(slots=True) class LeadershipConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 30`          # monthly is fine
  - `deterministic_salt: str = "leadership-v1"`
  - `base_succession_rate: float = 0.003`    # mortality/term expiry proxy
  - `coup_rate_p2: float = 0.010`
  - `purge_rate_p2: float = 0.006`
  - `legitimacy_shock_scale: float = 0.20`
  - `max_contenders: int = 6`

### 2.2 Polity leadership state
- `@dataclass(slots=True) class PolityLeadership:`
  - `polity_id: str`
  - `office_type: str`               # SOVEREIGN|COUNCIL|THEOCRAT|WARLORD
  - `leader_id: str`                 # symbolic id, e.g. "leader:empire:7"
  - `tenure_months: int = 0`
  - `legitimacy: float = 0.5`        # 0..1
  - `perf_legit: float = 0.5`
  - `proc_legit: float = 0.5`
  - `ideo_legit: float = 0.5`
  - `fear_legit: float = 0.0`
  - `alignment: dict[str, float] = field(default_factory=dict)`  # ideology axes
  - `sponsor_faction: str | None = None`
  - `status: str = "STABLE"`         # STABLE|CONTESTED|EMERGENCY
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)

### 2.3 Succession event record (bounded)
- `@dataclass(slots=True) class SuccessionEvent:`
  - `day: int`
  - `polity_id: str`
  - `kind: str`                      # ORDERLY|RESHUFFLE|COUP|PURGE|ASSASSINATION
  - `from_leader_id: str`
  - `to_leader_id: str`
  - `winner_faction: str | None`
  - `legitimacy_delta: float`
  - `reason_codes: list[str]`

World stores:
- `world.leadership_cfg`
- `world.leadership_by_polity: dict[str, PolityLeadership]`
- `world.succession_events: list[SuccessionEvent]` (bounded)

Persist leadership states and bounded history in snapshots and seeds.

---

## 3) Legitimacy computation (monthly)

Compute components:

### 3.1 Performance legitimacy
Inputs:
- hardship/inequality averages in polity territory (0291)
- war/civil conflict intensity (0278/0298)
- trade stability (0263/0295)
- epidemic burden (0283)
Lower hardship and stable borders increase perf_legit.

### 3.2 Procedural legitimacy
Inputs:
- policing doctrine procedural share (0296)
- corruption proxy from policing/finance (0292/0296)
- adherence to treaties (0274) and rule-of-law signals
Higher procedural share increases proc_legit.

### 3.3 Ideological legitimacy
Inputs:
- dominant ideology/religion (0285/0288)
- culture war intensity (0270)
- leader alignment vs dominant culture
Mismatch reduces ideo_legit.

### 3.4 Fear legitimacy
Inputs:
- terror policing share (0296) and repression incidents (0277)
Increases fear_legit but reduces others over time (backlash).

Combine:
- `legitimacy = w_perf*perf + w_proc*proc + w_ideo*ideo + w_fear*fear`
Weights can be tuned; deterministic.

---

## 4) Triggers for leadership change

Monthly check:

1) **Orderly succession (term/mortality proxy)**
- pseudo_rand < base_succession_rate adjusted by office type and stability.

2) **Council reshuffle**
- if office_type == COUNCIL and legitimacy low or faction pressure high.

3) **Coup**
- higher probability when:
  - legitimacy low,
  - war pressure high,
  - powerful factions dissatisfied (0266),
  - insurgency threat high (0297),
  - policing militarized but not effective.
Use `coup_rate_p2` in P2 with multipliers.

4) **Purge**
- if leader is authoritarian and terror share high, plus counterintel high.
Purges reduce faction power but increase backlash and insurgency.

5) **Assassination shock**
- from insurgency ops outcomes (0297). If an assassination attempt succeeds:
  - force immediate contested succession.

Deterministic ordering: apply highest-severity event first.

---

## 5) Contender selection and winner resolution

For a polity, generate contender list (bounded max_contenders):
- top factions by influence in polity territory (0266/0298)
- religious institution if relevant (0288)
- military leadership if war pressure high

Each contender provides a candidate alignment profile.

Winner scoring:
- faction power + support base + control of enforcement + media advantage
- minus legitimacy cost if coup/purge
- incorporate counterintel advantage

Choose winner deterministically using score tie breaks.

Update:
- leader_id increments
- sponsor_faction set
- legitimacy changes based on kind and whether succession is orderly.

---

## 6) Effects wiring

After leadership change:
- Policing doctrine (0296) may shift toward sponsor preference
- Sanctions/diplomacy posture (0274/0295) may change
- Labor bargaining bias (0289) may change
- Sovereignty fractures (0298) risk increases if legitimacy drops
- Insurgency recruitment (0297) increases if coup/purge/terror spike
- Markets react: volatility bump (0263)

Keep v1 minimal: apply a handful of scalar deltas and emit events.

---

## 7) Telemetry + cockpit

Metrics:
- `metrics["leadership"]["avg_legitimacy"]`
- `metrics["leadership"]["succession_events"]`
- `metrics["leadership"]["coups"]`
- `metrics["leadership"]["purges"]`

TopK:
- polities by legitimacy decline rate
- polities in contested status
- factions winning coups

Cockpit:
- polity leadership page: office type, legitimacy components, sponsor faction, tenure
- succession timeline: events and reason codes
- “legitimacy breakdown” chart (text/CLI fine)

Events:
- `LEADERSHIP_ORDERLY_SUCCESSION`
- `LEADERSHIP_COUNCIL_RESHUFFLE`
- `LEADERSHIP_COUP`
- `LEADERSHIP_PURGE`
- `LEADERSHIP_ASSASSINATION`

---

## 8) Persistence / seed vault

Export:
- `seeds/<name>/leadership.json` with leadership per polity and succession history (bounded).

---

## 9) Tests (must-have)

Create `tests/test_succession_leadership_legitimacy_v1.py`.

### T1. Determinism
- same inputs → same legitimacy and succession outcomes.

### T2. Hardship reduces legitimacy
- increasing hardship lowers perf_legit and total legitimacy.

### T3. Terror increases fear legitimacy but harms total over time
- rising terror share increases fear_legit and reduces proc/ideo via backlash.

### T4. Coup probability rises in P2 with low legitimacy
- under P2 and low legitimacy, coups occur more often deterministically.

### T5. Leadership change affects sovereignty pressure
- post-coup legitimacy shock increases fracture pressure (hook smoke test).

### T6. Snapshot roundtrip
- leadership states persist across snapshot/load and seeds.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add leadership module + polity leadership state
- Create `src/dosadi/runtime/leadership.py` with LeadershipConfig, PolityLeadership, SuccessionEvent
- Add world.leadership_by_polity and succession_events to snapshots + seeds

### Task 2 — Implement monthly legitimacy computation
- Compute perf/proc/ideo/fear components from hardship, policing doctrine, culture alignment, war pressure, and corruption proxies

### Task 3 — Implement succession/coup/purge triggers and contender resolution
- Deterministically select event type and winner among bounded contenders
- Apply legitimacy shocks and update sponsor faction

### Task 4 — Wire effects into policy and sovereignty/insurgency inputs
- Leadership changes adjust policing and bargaining biases and raise/lower fracture and recruitment inputs

### Task 5 — Cockpit + tests
- Add polity leadership pages and succession timeline
- Add `tests/test_succession_leadership_legitimacy_v1.py` (T1–T6)

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=True:
  - leadership legitimacy is computed and visible per polity,
  - orderly successions, coups, and purges can occur deterministically under stress,
  - leadership shifts change policy posture and destabilize or stabilize polities,
  - legitimacy shocks propagate into insurgency and fragmentation loops,
  - cockpit explains “who rules now, and why.”

---

## 12) Next slice after this

**Religious Schisms & Holy Conflict v1** — sect splits as political geometry:
- schisms, councils, crusades, martyrdom feedback,
- and theocratic polities emerging from cultural pressure.
