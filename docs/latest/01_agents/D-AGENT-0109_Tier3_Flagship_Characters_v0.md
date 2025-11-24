---
title: Tier3_Flagship_Characters
doc_id: D-AGENT-0109
version: 1.0.1
status: draft
owners: [cohayes]
last_updated: 2025-11-24
depends_on:
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0004   # Agent_Action_API_v0
  - D-AGENT-0005   # Perception_and_Memory_v0
  - D-AGENT-0006   # Agent_Attributes_and_Skills_v0
  - D-AGENT-0108   # Tier3_Office_Sheets
  - D-RUNTIME-0001 # Simulation_Timebase
  - D-RUNTIME-0103 # Scenario_Framing_and_Win_Loss_Conditions
  - D-RUNTIME-0105 # AI_Policy_Profiles
  - D-RUNTIME-0106 # Office_Precedent_and_Institutional_Memory
---

# 01_agents · Tier-3 Flagship Characters v0 (D-AGENT-0109)

## 1. Purpose

This document defines a set of **flagship Tier-3 characters** intended as
canonical examples for:

- how the **Agent_Attributes_and_Skills** framework (D-AGENT-0006) is used
  for high-level actors,
- how Tier-3 characters bind to **office sheets** (D-AGENT-0108),
- and how they plug into campaign scenarios (D-RUNTIME-0103) via
  AI_Policy_Profiles and precedent/learning systems.

It does **not** redefine attributes or skills. For the authoritative rules on:

- attribute names and scales,
- skill ratings and check semantics,
- derived stats and learning hooks,

refer to **D-AGENT-0006_Agent_Attributes_and_Skills_v0**.

---

## 2. Personality Facets (Tier-3 Usage)

Tier-3 characters use a shared personality schema that influences their
AI_PolicyProfiles and precedent-learning behavior.

Each facet is a float in `[0.0, 1.0]`:

```yaml
Personality:
  ambition: 0.0-1.0       # career & power hunger
  honesty: 0.0-1.0        # high = honest; low = comfortable with deception
  communal: 0.0-1.0       # high = community-/group-oriented; low = self-serving
  bravery: 0.0-1.0        # risk appetite; willingness to act under danger
  paranoia: 0.0-1.0       # suspicion of plots and betrayal
  dogmatism: 0.0-1.0      # rigidity of beliefs vs openness
  cruelty: 0.0-1.0        # comfort with others' suffering as a tool
  patience: 0.0-1.0       # long-game vs impulsive decisions
  curiosity: 0.0-1.0      # appetite for information & learning
```

Directional intent:

- **Ambition** – raises weights on prestige, dynasty, and power accumulation.
- **Honesty** – high favors overt/institutional means; low favors intrigue.
- **Communal** – high values ward/population health and allies; low is
  narrowly self/faction-serving.
- **Bravery** – increases willingness to choose risky policies and actions.
- **Paranoia** – raises baseline suspicion and CI usage; strengthens bias.
- **Dogmatism** – resists belief updates; tends to reinforce prior views.
- **Cruelty** – increases comfort with purges, harsh sentencing, collective
  punishment.
- **Patience** – favors slow, information-heavy strategies over quick shocks.
- **Curiosity** – increases use of `StudyArchives` / `WorkRumorCircles` and
  the rate at which precedent libraries grow.

### 2.1 Cunning as emergent

There is no atomic **cunning** stat. Instead, cunning emerges from a
combination of:

- high **INT** and skills such as **Intrigue**, **Streetwise**,
  **Intel Analysis**,
- moderate **paranoia** (neither naïve nor paralytic),
- lower **honesty** (comfort with manipulation),
- moderate **dogmatism** (not fully rigid),
- non-zero **curiosity** (interest in new information).

Implementations MAY define a derived `cunning` scalar from these inputs,
but it SHOULD NOT be stored independently.

---

## 3. Data Shape for Tier-3 Characters

Tier-3 characters extend the generic `Agent` core (D-AGENT-0001) with:
- an `office_id` that binds them to an office sheet (D-AGENT-0108),
- an `ai_policy_profile_ref` into D-RUNTIME-0105,
- and the personality facets defined above.

Example structure:

```yaml
Tier3Character:
  name: string
  office_id: string                # e.g. "crown:king", "duchy:river_ring"
  role: string                     # local label (regent, duke, cartel_boss, etc.)
  ai_policy_profile_ref: string    # into AI_Policy_Profiles

  attributes:                      # see D-AGENT-0006
    STR: int
    AGI: int
    CON: int
    INT: int
    WIL: int
    CHA: int

  skills:                          # subset of global skill registry
    Administration: int
    # ...

  traits:
    literacy: bool
    education: string              # free-text tag

  personality:
    ambition: float
    honesty: float
    communal: float
    bravery: float
    paranoia: float
    dogmatism: float
    cruelty: float
    patience: float
    curiosity: float

  # optional hints for runtime initialization; these are derived in practice
  learning_fields:
    learning_drive: float
    source_trust_archive: float
    source_trust_rumor: float
    bias_strength: float

  notes: string
```

The `learning_fields` block exists as a convenience for scenario authors and
can be recomputed from personality + office defaults per D-RUNTIME-0105/0106.

---

## 4. Flagship Characters v0

This section defines four flagship Tier-3 characters as canonical examples.

### 4.1 Crown: Regent Tashir of the Well

```yaml
name: "Regent Tashir of the Well"
office_id: "crown:king"
role: "regent"
ai_policy_profile_ref: "crown_pragmatic_traditionalist"

attributes:
  STR: 9
  AGI: 9
  CON: 10
  INT: 13
  WIL: 12
  CHA: 12

skills:
  Administration: 4
  Logistics: 2
  Finance_Ledgers: 3

  Strategy: 3
  Tactics_Command: 1
  Security_Craft: 2

  Diplomacy: 4
  Oratory: 3
  Intrigue: 3
  Streetwise: 1

  Scholarship: 4
  Law_Doctrine: 4
  Intel_Analysis: 3
  Interrogation: 1

traits:
  literacy: true
  education: "palace_scholar_tutors"

personality:
  ambition: 0.7
  honesty: 0.5
  communal: 0.6
  bravery: 0.5
  paranoia: 0.6
  dogmatism: 0.6
  cruelty: 0.4
  patience: 0.8
  curiosity: 0.7

learning_fields:
  learning_drive: 0.7
  source_trust_archive: 0.8
  source_trust_rumor: 0.4
  bias_strength: 0.5

notes: >
  Tashir is a learned, conservative regent who prefers stability to glory. He
  trusts archives and legal precedent, listens to espionage warnings, and will
  accept harsh measures but prefers to maintain legitimacy. His patience makes
  him slow to crack down, but once committed he follows through.
```

### 4.2 Ducal: Duke Keshar of River Ring

```yaml
name: "Duke Keshar of River Ring"
office_id: "duchy:river_ring"
role: "ducal_lord"
ai_policy_profile_ref: "duke_paranoid_hardline"

attributes:
  STR: 10
  AGI: 10
  CON: 12
  INT: 12
  WIL: 13
  CHA: 11

skills:
  Administration: 3
  Logistics: 2
  Finance_Ledgers: 2

  Strategy: 3
  Tactics_Command: 4
  Security_Craft: 3

  Diplomacy: 2
  Oratory: 3
  Intrigue: 4
  Streetwise: 2

  Scholarship: 1
  Law_Doctrine: 3
  Intel_Analysis: 2
  Interrogation: 3

traits:
  literacy: true
  education: "ducal_tutor"

personality:
  ambition: 0.8
  honesty: 0.3
  communal: 0.4
  bravery: 0.6
  paranoia: 0.8
  dogmatism: 0.7
  cruelty: 0.7
  patience: 0.5
  curiosity: 0.4

learning_fields:
  learning_drive: 0.4
  source_trust_archive: 0.6
  source_trust_rumor: 0.5
  bias_strength: 0.7

notes: >
  Keshar is a hardline, ambitious duke in charge of a critical ring of wards.
  He is competent at command and intrigue, wary of everyone, and comfortable
  with violent solutions. He studies enough to avoid obvious mistakes but
  often filters history through a paranoid, punitive lens.
```

### 4.3 Espionage: Chief Auditor Serel

```yaml
name: "Chief Auditor Serel"
office_id: "esp:branch_chief"
role: "espionage_branch_head"
ai_policy_profile_ref: "espionage_cautious_analyst"

attributes:
  STR: 8
  AGI: 9
  CON: 10
  INT: 14
  WIL: 11
  CHA: 10

skills:
  Administration: 3
  Logistics: 1
  Finance_Ledgers: 2

  Strategy: 2
  Tactics_Command: 1
  Security_Craft: 3

  Diplomacy: 2
  Oratory: 1
  Intrigue: 4
  Streetwise: 3

  Scholarship: 4
  Law_Doctrine: 3
  Intel_Analysis: 5
  Interrogation: 3

traits:
  literacy: true
  education: "audit_clerical_academy"

personality:
  ambition: 0.6
  honesty: 0.4
  communal: 0.5
  bravery: 0.3
  paranoia: 0.7
  dogmatism: 0.4
  cruelty: 0.5
  patience: 0.8
  curiosity: 0.8

learning_fields:
  learning_drive: 0.8
  source_trust_archive: 0.8
  source_trust_rumor: 0.6
  bias_strength: 0.4

notes: >
  Serel is a methodical intelligence chief who sees the world as patterns in
  maps and ledgers. High curiosity and scholarship make her a natural archive
  diver, and she uses precedent extensively. Her risk aversion and paranoia
  skew her toward cautious, surveillance-heavy CI stances, with purges as last
  resorts.
```

### 4.4 Cartel: “Uncle” Varek of the Lower Corridors

```yaml
name: "\"Uncle\" Varek"
office_id: "cartel:boss_lower_corridors"
role: "cartel_boss"
ai_policy_profile_ref: "cartel_expansionist_shadow"

attributes:
  STR: 9
  AGI: 10
  CON: 11
  INT: 12
  WIL: 11
  CHA: 13

skills:
  Administration: 2
  Logistics: 3
  Finance_Ledgers: 3

  Strategy: 2
  Tactics_Command: 2
  Security_Craft: 3

  Diplomacy: 2
  Oratory: 3
  Intrigue: 5
  Streetwise: 5

  Scholarship: 0
  Law_Doctrine: 1
  Intel_Analysis: 2
  Interrogation: 3

traits:
  literacy: true
  education: "self_taught_street"

personality:
  ambition: 0.8
  honesty: 0.2
  communal: 0.3
  bravery: 0.7
  paranoia: 0.7
  dogmatism: 0.2
  cruelty: 0.6
  patience: 0.6
  curiosity: 0.5

learning_fields:
  learning_drive: 0.5
  source_trust_archive: 0.2
  source_trust_rumor: 0.9
  bias_strength: 0.6

notes: >
  Varek is a charismatic cartel boss whose classroom was the alleys and
  corridors. He lives by rumor, favors clever workarounds over direct conflict,
  and invests heavily in relationships and informants. He rarely uses archives
  but builds a deep personal and social precedent library from stories and
  deals.
```

---

## 5. Usage Notes

- Scenarios SHOULD reference these characters by `office_id` and explicitly
  bind them to scenario roles where appropriate (e.g. Quiet Season, later
  Sting Wave setups).
- Numerical values (attributes, skills, personality) MAY be tuned per
  scenario, but such deviations SHOULD be documented as “variant profiles”.
- Additional Tier-3 characters (military high command, bishop roles, etc.)
  MAY be added in future versions, following the same schema.
