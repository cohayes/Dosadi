---
title: Constitutional_Settlements_and_Rights_Regimes_v1_Implementation_Checklist
doc_id: D-RUNTIME-0304
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0274   # Diplomacy & Treaties v1
  - D-RUNTIME-0275   # Border Control & Customs v1
  - D-RUNTIME-0296   # Policing Doctrine v2
  - D-RUNTIME-0298   # Civil War & Fragmentation v1
  - D-RUNTIME-0299   # Succession & Leadership Legitimacy v1
  - D-RUNTIME-0303   # Reform Movements & Anti-Corruption Drives v1
---

# Constitutional Settlements & Rights Regimes v1 — Implementation Checklist

Branch name: `feature/constitution-rights-regimes-v1`

Goal: enable “late-phase recovery” into durable institutions so that:
- polities can codify rights and governance forms (a constitution-like settlement),
- rights regimes constrain policing doctrine and reduce corruption drift,
- constitutional crises can occur (suspension, emergency powers, rollback),
- long-run seeds can end in stable rule-of-law, hardened theocracy, or authoritarian emergency states.

v1 is macro: rights indices + settlement documents as policy objects, not legal case simulation.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same settlements, rollbacks, and effects.
2. **Bounded.** One active settlement per polity, bounded crisis events.
3. **Legible.** Explain what was adopted and what constraints it imposes.
4. **Composable.** Hooks into policing doctrine, reform, leadership legitimacy, and sovereignty.
5. **Phase-aware.** P0 can adopt early charters; P2 can roll back via emergency powers.
6. **Tested.** Adoption/rollback mechanics and persistence.

---

## 1) Concept model

A polity may adopt a “settlement” that defines:
- governance form (council monarchy, theocracy, republic, military junta),
- a set of rights/protections (due process, movement, speech, labor, property),
- institutional constraints (court independence, audit office, term limits),
- emergency power clauses (how easy it is to suspend rights).

Settlements change behavior by:
- modifying doctrine limits (e.g., cap terror policing),
- reducing capture opportunities (shadow state resistance),
- increasing procedural legitimacy (0299),
- and reducing fracture pressure (0298) if perceived fair.

---

## 2) Rights dimensions (v1)

Define 6 rights indices (0..1):
- `due_process`
- `movement`
- `speech`
- `labor_organizing`
- `property_security`
- `religious_freedom`

Plus 3 institutional constraints:
- `court_independence`
- `audit_independence`
- `term_limits`

And emergency power:
- `emergency_power_ease` (0..1; higher is easier to suspend rights)

These are *policy state* — not moral judgments.

---

## 3) Data structures

Create `src/dosadi/runtime/constitution.py`

### 3.1 Config
- `@dataclass(slots=True) class ConstitutionConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 30`
  - `deterministic_salt: str = "constitution-v1"`
  - `adoption_rate_base: float = 0.001`
  - `rollback_rate_p2: float = 0.004`
  - `rights_effect_scale: float = 0.25`
  - `crisis_threshold: float = 0.70`

### 3.2 Settlement document
- `@dataclass(slots=True) class Settlement:`
  - `settlement_id: str`
  - `polity_id: str`
  - `name: str`
  - `governance_form: str`           # MONARCHY_COUNCIL|REPUBLIC|THEOCRACY|JUNTA|OLIGARCHY
  - `rights: dict[str, float]`       # the 6 indices
  - `constraints: dict[str, float]`  # court/audit/term
  - `emergency_power_ease: float`
  - `adopted_day: int`
  - `status: str = "ACTIVE"`         # ACTIVE|SUSPENDED|REPEALED
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Constitutional state
- `@dataclass(slots=True) class ConstitutionState:`
  - `polity_id: str`
  - `active_settlement_id: str | None = None`
  - `rights_current: dict[str, float] = field(default_factory=dict)
  - `constraints_current: dict[str, float] = field(default_factory=dict)
  - `emergency_active: bool = False`
  - `emergency_until_day: int = -1`
  - `last_update_day: int = -1`

### 3.4 Crisis events (bounded)
- `@dataclass(slots=True) class ConstitutionalEvent:`
  - `day: int`
  - `polity_id: str`
  - `kind: str`                      # ADOPTED|SUSPENDED|REPEALED|AMENDED|EMERGENCY_DECLARED|EMERGENCY_LIFTED
  - `settlement_id: str | None`
  - `reason_codes: list[str]`

World stores:
- `world.constitution_cfg`
- `world.settlements: dict[str, Settlement]`
- `world.constitution_by_polity: dict[str, ConstitutionState]`
- `world.constitution_events: list[ConstitutionalEvent]` (bounded)

Persist in snapshots and seeds.

---

## 4) Adoption logic (monthly)

Adoption pressure increases when:
- reform campaigns succeed (0303)
- leadership seeks procedural legitimacy (0299)
- civil war ends with treaty/autonomy (0298)
- corruption indices high but reform capacity exists (0302/0303)
- culture wars moderate (0270) (too high prevents compromise)

If trigger:
- generate settlement:
  - choose governance_form based on current leadership office and faction balance
  - set rights and constraints based on sponsor ideology:
    - procedural reform → high due_process, court independence, audit independence
    - theocracy → high religious authority, low religious_freedom, medium due_process
    - junta → low speech, low labor, high emergency_power_ease
  - name stable and deterministic.

Apply settlement:
- update rights_current/constraints_current for the polity
- emit event ADOPTED.

---

## 5) Effects wiring

### 5.1 Policing doctrine constraints (0296)
- cap `TERROR` share: `terror_cap = 1 - due_process` (example)
- increase procedural floor: `procedural_floor = due_process * 0.5`
- emergency power can temporarily lift caps.

### 5.2 Shadow state resistance (0302)
- audit_independence reduces capture growth and increases exposure risk for edges
- property_security affects seizure and patronage dynamics (0292)

### 5.3 Labor and speech (0289/0286)
- labor_organizing influences union strength and strike probability
- speech influences media independence and propaganda distortions

### 5.4 Sovereignty stability (0298)
- fair rights reduce fracture pressure; rollback increases it.

### 5.5 Leadership legitimacy (0299)
- procedural legitimacy rises when due_process and constraints high
- fear legitimacy becomes harder to maintain.

---

## 6) Emergency powers and rollbacks (P2)

Crisis pressure increases when:
- war intensity high (0278/0298)
- insurgency high (0297)
- comms failures high (0294)
- shortages severe (0263/0291)

If crisis pressure > crisis_threshold:
- emergency may be declared based on emergency_power_ease:
  - rights suspended partially (speech/movement)
  - policing terror cap lifted
  - rollback drift increases (long-run authoritarianism)

Emergency ends after bounded duration or when pressure falls.

Rollback/repeal:
- in P2, monthly chance to amend/repeal settlement upward or downward.
Keep v1 minimal: suspend vs lift, and rare repeal.

---

## 7) Incidents

Use Incident Engine (0242):
- `CONSTITUTION_ADOPTED`
- `RIGHTS_SUSPENDED`
- `EMERGENCY_POWERS_DECLARED`
- `CONSTITUTIONAL_CRISIS`
- `RIGHTS_RESTORED`

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["constitution"]["polities_with_settlement"]`
- `metrics["constitution"]["avg_due_process"]`
- `metrics["constitution"]["emergencies_active"]`
- `metrics["constitution"]["suspensions"]`

TopK:
- polities with lowest rights vs highest stability
- polities in repeated emergency cycles

Cockpit:
- settlement viewer: governance form + rights/constraints indices
- emergency timeline
- “constraints effects” panel: policing caps and corruption resistance

Events:
- `SETTLEMENT_ADOPTED`
- `SETTLEMENT_SUSPENDED`
- `SETTLEMENT_RESTORED`
- `SETTLEMENT_REPEALED`

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/constitution.json` with settlements and constitution_by_polity.

---

## 10) Tests (must-have)

Create `tests/test_constitution_rights_regimes_v1.py`.

### T1. Determinism
- same inputs → same adoption and emergency outcomes.

### T2. Reform success increases adoption probability
- successful reform campaign drives settlement adoption.

### T3. Due process constrains terror policing
- higher due_process lowers terror cap and increases procedural floor.

### T4. Emergency suspends rights and lifts caps
- crisis pressure triggers emergency and modifies constraints.

### T5. Rights reduce fracture pressure
- higher rights reduce sovereignty fracture pressure inputs.

### T6. Snapshot roundtrip
- settlement and rights state persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add constitution module + state
- Create `src/dosadi/runtime/constitution.py` with ConstitutionConfig, Settlement, ConstitutionState, ConstitutionalEvent
- Add settlements and constitution_by_polity to snapshots + seeds

### Task 2 — Implement adoption logic
- Monthly adoption pressure based on reform, leadership legitimacy goals, and post-conflict settlement conditions
- Generate deterministic settlement objects and apply to polity state

### Task 3 — Implement effects wiring
- Apply rights/constraints to policing doctrine, shadow state resistance, labor/media dynamics, sovereignty stability, and leadership legitimacy

### Task 4 — Implement emergency powers
- Crisis pressure triggers emergency based on emergency_power_ease; suspend rights and lift policing caps; end after duration

### Task 5 — Cockpit + tests
- Add settlement viewer and emergency timeline
- Add `tests/test_constitution_rights_regimes_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - polities can adopt settlements that constrain governance meaningfully,
  - rights regimes change policing and corruption dynamics,
  - emergencies can suspend rights under stress (P2),
  - seeds can converge to stable constitutions or authoritarian rollback cycles,
  - cockpit explains “what rights exist and when they were suspended.”

---

## 13) Next slice after this

**Metrology & Truth Regimes v1** — what counts as “official reality”:
- census integrity, measurement standards, fraud,
- and how information legitimacy underpins markets and law.
