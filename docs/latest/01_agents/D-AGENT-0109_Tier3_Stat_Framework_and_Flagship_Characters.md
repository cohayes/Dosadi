---
title: Tier3_Stat_Framework_and_Flagship_Characters
doc_id: D-AGENT-0109
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-24
depends_on:
  - D-AGENT-0001       # Dosadi_Agent_Core
  - D-AGENT-0108       # Tier3_Office_Sheets
  - D-RUNTIME-0101     # Simulation_Timebase (if numbered differently, adjust)
  - D-RUNTIME-0105     # AI_Policy_Profiles
  - D-RUNTIME-0106     # Office_Precedent_and_Institutional_Memory
---

# 01_agents · Tier-3 Stat Framework & Flagship Characters (D-AGENT-0109)

## 1. Core Attribute System (10-based, ±10% steps)

Tier-3 agents (and eventually all agents) use a six-attribute system:

- **Strength (STR)** – physical power, lifting, melee.
- **Agility (AGI)** – coordination, reflexes, fine motor control.
- **Constitution (CON)** – health, stamina, resistance to disease and fatigue.
- **Intellect (INT)** – reasoning, pattern recognition, learning ability.
- **Willpower (WIL)** – discipline, grit, ability to endure stress and temptation.
- **Charisma (CHA)** – social presence, magnetism, ability to sway others.

### 1.1 Scale

- Human baseline = **10** → multiplier **1.00**.
- Each step up = ×1.10 (~+10%).
- Each step down = ÷1.10 (~−10%).
- Initial implementations SHOULD use **integers only**; fractional advancement
  (10.4, 11.2) MAY be introduced later as a result of long-term training.

Formal rule:

```text
attribute_multiplier = 1.1 ** (score - 10)
```

Reference table (rounded to 3 decimals):

| Score | Multiplier | Description                         |
|-------|------------|-------------------------------------|
| 5     | 0.621      | crippling / severely impaired       |
| 6     | 0.683      | very weak / fragile                 |
| 7     | 0.751      | significantly below average         |
| 8     | 0.826      | below average                       |
| 9     | 0.909      | slightly below average              |
| 10    | 1.000      | human average                       |
| 11    | 1.100      | slightly above average              |
| 12    | 1.210      | clearly above average               |
| 13    | 1.331      | strong talent                       |
| 14    | 1.464      | elite                               |
| 15    | 1.611      | rare exceptional                    |

These multipliers are used when translating attributes into effective
percentages for skill checks and derived stats.

---

## 2. Skills & Percentile Checks

Skills are **universal** (Tier-1 to Tier-3), but some are mainly relevant at
leadership scale. This document focuses on Tier-3-relevant skills; other skill
families (craft, combat, survival) are defined elsewhere.

### 2.1 Governance, Security & Social Skill List (Tier-3 relevant)

**Governance & Logistics**

- **Administration** – running bureaucracies, delegating, paperwork discipline.
- **Logistics** – moving water, food, equipment and people efficiently.
- **Finance & Ledgers** – taxation, accounts, skimming without obvious theft.

**Military & Security**

- **Strategy** – campaign-level planning, big-picture war / security posture.
- **Tactics & Command** – unit-level command, issuing orders under stress.
- **Security Craft** – checkpoints, patrol patterns, hardening / subversion basics.

**Political & Social**

- **Diplomacy** – negotiation, alliances, formal politics.
- **Oratory** – speeches, crowd control, public persuasion.
- **Intrigue** – plotting, blackmail, secret deals, reading factional currents.
- **Streetwise** – local gossip, underworld contacts, safe routes and taverns.

**Knowledge & Information**

- **Scholarship** – reading, archives, history, theory (requires literacy).
- **Law & Doctrine** – statutes, charters, civic/religious doctrine.
- **Intel Analysis** – parsing reports, spotting patterns and deception.
- **Interrogation** – extracting information by psychological or physical means.

### 2.2 Skill rating → base effectiveness

Each skill has a rating `0–5` which maps to a **base effectiveness percentage**:

| Rating | Base effectiveness |
|--------|--------------------|
| 0      | 0%                 |
| 1      | 25%                |
| 2      | 50%                |
| 3      | 75%                |
| 4      | 100%               |
| 5      | 125%               |

This base value is then modified by:

- relevant attribute multipliers (usually one or two attributes),
- task difficulty,
- situational modifiers (resources, timing, crowd state, etc.).

### 2.3 Task difficulty & situational modifiers

Standard difficulty bands for v1:

- **Trivial**: +50%
- **Easy**: +25%
- **Standard**: +0%
- **Hard**: −50%
- **Extreme**: −75%

Situational modifiers stack on top, such as:

- Favorable conditions: +10% to +50%
  - strong resources, good timing, friendly audience, rehearsed speech, etc.
- Adverse conditions: −10% to −50%
  - missing tools, hostile audience, prior failures, bad rumors, etc.

### 2.4 Effective chance of success (single check)

For v1, an effective success chance for a skillful action can be approximated as:

```text
effective_skill_pct =
    (skill_base_pct) * attribute_multiplier
    + difficulty_modifier
    + situational_modifiers
```

- Values SHOULD be clamped to a sensible band, e.g. `[0%, 150%]`.
- A percentile roll under `effective_skill_pct` indicates success.
- Failure need not mean immediate catastrophe; scenario logic can interpret
  partial / repeated failures into escalation.

**Example – Oratory on a hostile mob:**

- Oratory rating 3 → base 75%.
- CHA 11 → attribute multiplier ≈ 1.10.
- Task difficulty: Hard (−50%).
- Offering concessions: +25%.

```text
base_with_attr = 75% * 1.10 ≈ 82.5%
effective_skill_pct = 82.5% + (−50% + 25%) ≈ 57.5%
```

**Example – Oratory at a scripted ward leadership meeting:**

- Same Oratory 3 → 75%.
- CHA 11 → ×1.10 → 82.5%.
- Difficulty: Easy (+25%).
- Breaking mildly bad news: −20%.

```text
effective_skill_pct = 82.5% + (25% − 20%) ≈ 87.5%
```

Opposed checks (Oratory vs Skepticism, Intrigue vs Security Craft) MAY be
implemented later by rolling each side against their own effective pct and
comparing degrees of success. v1 does not require opposed mechanics.

---

## 3. Derived Stats (Tier-3 focus)

Derived stats tie attributes and skills into runtime metrics and learning
systems defined in D-RUNTIME-0105 and D-RUNTIME-0106.

### 3.1 Learning & information

- **archive_literacy_score**  
  - Derived from `INT` multiplier, **Scholarship** skill, and Literacy trait.
  - Drives throughput and quality of `StudyArchives` learning actions.

- **rumor_attunement_score**  
  - Derived from `CHA` multiplier, **Streetwise** and **Intrigue** skills.
  - Drives throughput and quality of `WorkRumorCircles` learning actions.

- **memory_capacity_base**  
  - Derived from `INT` and `WIL` multipliers, scaled by office importance.
  - Sets initial maximum size of `PersonalPrecedentLibrary`.

### 3.2 Survival & stress

- **Stress Tolerance**  
  - Derived from `CON` + `WIL` multipliers.
  - Influences personal reaction to crises, burnout risk, and how quickly
    seat_risk escalates under pressure.

- **Command Presence**  
  - Derived from `CHA` + `WIL` multipliers and **Tactics & Command** skill.
  - Affects garrison morale, obedience, and propensity to follow harsh orders.

- **Personal Security** (conceptual helper)  
  - Derived from `CON` + `WIL` multipliers, **Security Craft** and **Intrigue**.
  - Affects assassination risk and vulnerability to coups.

### 3.3 Mapping into AI_PolicyProfile

Attributes and derived stats inform `AiPolicyProfile` parameters, e.g.:

- Higher **INT + Scholarship** → higher baseline `learning_drive` and
  `source_trust_archive`.
- Higher **Streetwise + Intrigue** → higher `source_trust_rumor` and more
  opportunistic bias.
- Higher **WIL** → higher `patience` and resistance to panic/crisis decisions.
- Higher **CHA + Diplomacy/Oratory** → stronger valuation of legitimacy in
  policy trade-offs.
- Higher **Strategy + Tactics & Command** → more structured `risk_tolerance`
  (willingness to risk when odds are favorable).

Precise mapping functions are left to implementation; this document sets the
directional intent.

---

## 4. Personality Schema (Facets)

Personality facets shape how Tier-3 agents weigh risks, interpret signals, use
power, and interact with the precedence/learning system.

Each facet is represented as a float in `[0.0, 1.0]`:

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

### 4.1 Effects on AI and learning

- **Ambition**  
  - Increases weighting of **prestige**, **dynasty**, and power accumulation.

- **Honesty**  
  - High: preference for overt, institutional methods.
  - Low: preference for intrigue, blackmail, and covert manipulation.

- **Communal**  
  - High: places more value on ward/population well-being and allies.
  - Low: places more value on personal survival and narrow faction interests.

- **Bravery**  
  - Drives `risk_tolerance` (willingness to choose risky policies, coups,
    aggressive crackdowns, daring reforms).

- **Paranoia**  
  - Elevates suspicion of others, encourages CI-heavy responses, raises
    baseline `bias_strength` for interpreting threats.

- **Dogmatism**  
  - High: favors doctrinal consistency over empirical evidence; pushes
    `bias_strength` upward and resists debiasing from learning.
  - Low: more flexible belief updates from diverse precedent.

- **Cruelty**  
  - Raises comfort with purges, harsh sentencing, and collective punishment.
  - Drives preference for higher law_intensity and repression.

- **Patience**  
  - High: favors long-term strategies, slower escalations.
  - Low: favors immediate action, quick “solutions”, more impulsive crackdowns.

- **Curiosity**  
  - Direct driver for `learning_drive` and willingness to engage in
    `StudyArchives` / `WorkRumorCircles` actions.
  - Increases exposure to diverse precedent (subject to access constraints).

### 4.2 Cunning as emergent, not atomic

There is no single “cunning” stat. Instead, cunning **emerges** from a mix of:

- High **INT** and **Intel Analysis** / **Intrigue** skills,
- Moderate **paranoia** (not naïve, not completely frozen),
- Lower **honesty** (comfort with manipulation),
- Some **Streetwise** (context for how power actually works on the ground),
- Moderate **dogmatism** (rigid ideologues are less adaptive),
- Non-zero **curiosity** (actually seeks information).

If an explicit `cunning` helper is desired later, it SHOULD be a derived value
from these components rather than a standalone trait.

---

## 5. Flagship Tier-3 Characters (v1)

This section defines four **flagship Tier-3 characters** as exemplars. They are
intended both as lore seeds and as concrete targets for Codex-backed
implementation.

### 5.1 Crown: Regent Tashir of the Well

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

learning_fields (derived intent):
  learning_drive: ~0.7        # from curiosity & office expectations
  source_trust_archive: ~0.8  # educated, archive-leaning
  source_trust_rumor: ~0.4
  bias_strength: ~0.5         # moderate dogmatism/paranoia

notes: >
  Tashir is a learned, conservative regent who prefers stability to glory. He
  trusts archives and legal precedent, listens to espionage warnings, and will
  accept harsh measures but prefers to maintain legitimacy. His patience makes
  him slow to crack down, but once committed he follows through.
```

### 5.2 Ducal: Duke Keshar of River Ring

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

learning_fields (derived intent):
  learning_drive: ~0.4
  source_trust_archive: ~0.6
  source_trust_rumor: ~0.5
  bias_strength: ~0.7

notes: >
  Keshar is a hardline, ambitious duke in charge of a critical ring of wards.
  He is competent at command and intrigue, wary of everyone, and comfortable
  with violent solutions. He studies enough to avoid obvious mistakes but
  often filters history through a paranoid, punitive lens.
```

### 5.3 Espionage: Chief Auditor Serel of the Cartography Office

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

learning_fields (derived intent):
  learning_drive: ~0.8
  source_trust_archive: ~0.8
  source_trust_rumor: ~0.6
  bias_strength: ~0.4

notes: >
  Serel is a methodical intelligence chief who sees the world as patterns in
  maps and ledgers. High curiosity and scholarship make her a natural archive
  diver, and she uses precedent extensively. Her risk aversion and paranoia
  skew her toward cautious, surveillance-heavy CI stances, with purges as last
  resorts.
```

### 5.4 Cartel: “Uncle” Varek of the Lower Corridors

```yaml
name: ""Uncle" Varek"
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

learning_fields (derived intent):
  learning_drive: ~0.5
  source_trust_archive: ~0.2
  source_trust_rumor: ~0.9
  bias_strength: ~0.6

notes: >
  Varek is a charismatic cartel boss whose classroom was the alleys and
  corridors. He lives by rumor, favors clever workarounds over direct conflict,
  and invests heavily in relationships and informants. He rarely uses archives
  but builds a deep personal and social precedent library from stories and
  deals.
```

---

## 6. Implementation Notes

- These flagship characters SHOULD be wired into early scenarios (e.g. Quiet
  Season and its successors) as canonical holders of their offices.
- Scenario configs MAY override exact numeric values but SHOULD preserve the
  core personality and role alignment described here.
- Future revisions MAY:
  - add more Tier-3 exemplars (bishop, MIL high command),
  - normalize doc_id references once the full agent pillar index is stable,
  - and extract the attribute/skill framework into a dedicated
    D-AGENT-0002-style document, with this file focusing purely on Tier-3
    character examples.
