---
title: Agent_Attributes_and_Skills
doc_id: D-AGENT-0006
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-24
depends_on:
  - D-AGENT-0000   # Agent_System_Overview_v1
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0002   # Agent_Decision_Rule_v0
  - D-AGENT-0003   # Drive_Facility_Impact_Matrix_v0
  - D-AGENT-0005   # Perception_and_Memory_v0
  - D-AGENT-0109   # Tier3_Stat_Framework_and_Flagship_Characters (examples)
  - D-RUNTIME-0001 # Simulation_Timebase
  - D-RUNTIME-0105 # AI_Policy_Profiles
  - D-RUNTIME-0106 # Office_Precedent_and_Institutional_Memory
---

# 01_agents · Agent Attributes and Skills v0 (D-AGENT-0006)

## 1. Purpose & Scope

This document defines the **canonical attribute and skill framework** for Dosadi
agents. It is intended to:

- provide a **single source of truth** for agent stats across all tiers
  (Tier-1 commoners, Tier-2 specialists, Tier-3 office-holders),
- specify how **attributes**, **skills**, and **derived stats** are represented,
  and how they plug into:
  - the **decision rule** (D-AGENT-0002),
  - **drives and facilities** (D-AGENT-0003),
  - **perception and memory** (D-AGENT-0005),
  - **AI policy profiles** (D-RUNTIME-0105), and
  - **precedent-based learning** (D-RUNTIME-0106),
- define a **v0 registry of skills**, grouped into families, that can be
  extended in later versions.

D-AGENT-0109 (Tier-3 Stat Framework & Flagship Characters) provides concrete
examples of this schema in use; **this** document is the normative definition.

---

## 2. Core Attribute System

### 2.1 Attribute list

All agents share the same six **primary attributes**:

- **Strength (STR)** – physical power, lifting, melee.
- **Agility (AGI)** – coordination, reflexes, fine motor control.
- **Constitution (CON)** – health, stamina, resistance to fatigue and disease.
- **Intellect (INT)** – reasoning, pattern recognition, learning ability.
- **Willpower (WIL)** – discipline, persistence, resistance to stress/temptation.
- **Charisma (CHA)** – social presence, magnetism, influence over others.

### 2.2 Scale and multipliers

Attributes are measured on a **10-based** human scale:

- Human baseline = **10** → multiplier **1.00**
- Each step up = ×1.10 (~+10%)
- Each step down = ÷1.10 (~−10%)

Formal rule:

```text
attribute_multiplier(attr_score) = 1.1 ** (attr_score - 10)
```

Implementations SHOULD clamp typical human scores to `[5, 15]` in v0. Other
species or extreme cases MAY exceed this.

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

v0 **SHOULD** use integer attribute scores only. Fractional scores MAY be
introduced in later builds as the result of long-term training or injury.

### 2.3 Attribute checks

Direct attribute checks (e.g. raw STR test, WIL test) MAY be represented as
percent chances derived from the multiplier:

```text
base_pct = 50% * attribute_multiplier
```

and then modified by difficulty and situation (Section 4). However, gameplay
and simulation SHOULD prefer **skill-based checks** where possible, with
attributes feeding into those checks as multipliers.

---

## 3. Skill System

### 3.1 Skill ratings

Skills are represented as integer ratings in `[0, 5]`:

- 0 – untrained
- 1 – basic familiarity
- 2 – competent
- 3 – proficient
- 4 – expert
- 5 – master / rare specialist

### 3.2 Skill rating → base effectiveness

Each rating maps to a **base effectiveness percentage**:

| Rating | Base effectiveness |
|--------|--------------------|
| 0      | 0%                 |
| 1      | 25%                |
| 2      | 50%                |
| 3      | 75%                |
| 4      | 100%               |
| 5      | 125%               |

This is the **starting point** for a skill check. It is then modified by:

- relevant attribute multipliers,
- task difficulty,
- situational modifiers (resources, crowd state, timing),
- and any trait/perk bonuses.

### 3.3 Task difficulty & situational modifiers

Standard v0 difficulty bands:

- **Trivial**: +50%
- **Easy**: +25%
- **Standard**: +0%
- **Hard**: −50%
- **Extreme**: −75%

Situational modifiers stack on top:

- Favorable conditions: +10% to +50% (good tools, helpful allies, ideal timing).
- Adverse conditions: −10% to −50% (missing resources, hostility, bad timing).

---

## 4. Check Resolution (Single-Actor)

### 4.1 Effective chance of success

For a typical action where a single agent uses a skill `S` and one or two
primary attributes dominate (e.g. Oratory using CHA, Administration using INT),
the v0 resolution rule is:

```text
skill_base_pct = base_effectiveness_from_rating(S)   # 0–125%
attr_mult = product_of_relevant_attribute_multipliers  # e.g. CHA, INT, etc.

effective_skill_pct =
    (skill_base_pct) * attr_mult
    + difficulty_modifier
    + situational_modifiers
```

The final value SHOULD be clamped to e.g. `[0%, 150%]`. A percentile roll
under `effective_skill_pct` indicates success.

### 4.2 Opposed checks (optional v0)

Opposed checks (e.g. Intrigue vs Security Craft, Oratory vs Skepticism) MAY be
implemented by:

- computing `effective_pct_attacker` and `effective_pct_defender` separately,
- rolling percentile for each,
- comparing **degrees of success** or margin differences.

v0 core systems DO NOT require opposed checks; they are a future extension.

### 4.3 Consequences and escalation

Failure does **not** automatically imply catastrophe. Scenario logic and
decision rules SHOULD interpret:

- single failures as delays, partial results, or local setbacks,
- **critical failures** (very large misses or repeated failures) as triggers
  for escalation (angry mobs turning violent, purges triggering unrest, etc.).

Critical thresholds are scenario-dependent and defined in runtime docs.

---

## 5. Skill Registry v0

This section enumerates the **v0 skill families** and individual skills. Future
versions MAY add skills or split existing entries; removal should be rare.

Each skill entry includes:

- a short description,
- typical associated attributes,
- indicative use cases and which tiers benefit most.

### 5.1 Physical & Mobility

- **Athletics**  
  - Attributes: STR, AGI, CON  
  - Running, climbing, jumping, lifting, general physical exertion.  
  - Tier use: important for Tier-1/2; Tier-3 only in rare direct-action scenes.

- **Stealth**  
  - Attributes: AGI, WIL  
  - Moving quietly, remaining unseen, blending into crowds.  
  - Tier use: common for scouts, infiltrators; some Tier-3 use via aides.

- **Melee Combat**  
  - Attributes: STR, AGI  
  - Close-quarters combat with handheld weapons.  

- **Ranged Combat**  
  - Attributes: AGI, INT  
  - Firearms, thrown weapons, long-distance attacks.

### 5.2 Survival & Fieldcraft

- **Scavenging**  
  - Attributes: INT, CON  
  - Finding useful materials in ruins, waste streams, and derelict spaces.

- **Wilderness/Outskirts Survival**  
  - Attributes: CON, INT  
  - Navigating hostile terrain, securing shelter, basic foraging (where
    applicable on Dosadi).

- **Urban Navigation**  
  - Attributes: INT, AGI  
  - Knowing shortcuts, escape routes, safe corridors within wards.

### 5.3 Technical & Industry

- **Mechanics**  
  - Attributes: INT, AGI  
  - Repairing and maintaining machinery, including exo-suits and heavy gear.

- **Suit Operation**  
  - Attributes: INT, AGI, CON  
  - Competent use of environmental suits, including life-support settings and
    basic troubleshooting.

- **Suit Maintenance**  
  - Attributes: INT  
  - Maintaining seals, filters, condensers, and moisture capture systems.

- **Fabrication & Craft**  
  - Attributes: INT, AGI  
  - Operating fabricators, handcrafting tools, improvising repairs.

- **HVAC & Atmospherics**  
  - Attributes: INT  
  - Understanding and maintaining air handling, pressure differentials,
    filtration systems in sealed/partially sealed wards.

- **Medicine**  
  - Attributes: INT, WIL  
  - Diagnosis, treatment, surgery, triage.

### 5.4 Governance & Logistics

- **Administration**  
  - Attributes: INT, WIL  
  - Paperwork, rosters, scheduling, delegating, bureaucratic discipline.  
  - Tier use: key for foremen, ward stewards, Tier-3 offices.

- **Logistics**  
  - Attributes: INT, CON  
  - Moving resources and people, planning routes and timetables.

- **Finance & Ledgers**  
  - Attributes: INT  
  - Accounting, taxation, detection or execution of skimming, budgeting.

### 5.5 Military & Security

- **Strategy**  
  - Attributes: INT, WIL  
  - Overall campaign-level planning, large-scale security posture.

- **Tactics & Command**  
  - Attributes: WIL, CHA  
  - Unit-level command, battlefield leadership, issuing orders under fire.

- **Security Craft**  
  - Attributes: INT, WIL  
  - Checkpoints, patrol patterns, security design, infiltration resistance.

- **Interrogation**  
  - Attributes: WIL, CHA  
  - Extracting information through psychological or physical pressure.

### 5.6 Political & Social

- **Diplomacy**  
  - Attributes: CHA, INT  
  - Negotiation, alliance-building, formal politics.

- **Oratory**  
  - Attributes: CHA  
  - Public speaking, crowd control, morale shaping.

- **Intrigue**  
  - Attributes: INT, CHA  
  - Plotting, blackmail, subtle manipulation, managing secret networks.

- **Streetwise**  
  - Attributes: CHA, CON  
  - Understanding local cultures, tavern politics, underworld practices.

- **Etiquette & Protocol**  
  - Attributes: CHA, INT  
  - High-society behavior, court etiquette, knowing “the right thing” to do
    in formal situations.

### 5.7 Knowledge & Information

- **Scholarship**  
  - Attributes: INT  
  - Reading, archives, theory, historical knowledge (requires literacy).

- **Law & Doctrine**  
  - Attributes: INT, WIL  
  - Statutes, charters, civic/religious doctrine.

- **Intel Analysis**  
  - Attributes: INT  
  - Parsing reports, identifying patterns, spotting deception in data.

- **Bureaucratic Navigation**  
  - Attributes: INT, WIL  
  - Knowing which forms, who to ask, and how to push things through
    administrative channels.

### 5.8 Trade & Commerce

- **Bargaining & Haggling**  
  - Attributes: CHA, INT  
  - Negotiating prices and deals.

- **Market Lore**  
  - Attributes: INT  
  - Understanding supply chains, scarcity signals, and price flows.

- **Smuggling & Routing**  
  - Attributes: INT, CHA  
  - Planning and protecting illicit routes, minimizing exposure.

### 5.9 Specialized / Cultural

- **Religious/Civic Ritual**  
  - Attributes: CHA, WIL  
  - Conducting or participating in rituals that matter for legitimacy or
    community cohesion.

- **Performance & Storytelling**  
  - Attributes: CHA  
  - Entertaining, shaping narratives, spreading rumors or counter-rumors.

This registry is **not exhaustive**; v0 defines the baseline. New skills MAY be
added in Tier-2 and Tier-3 design docs as long as they adhere to the same
rating and check semantics.

---

## 6. Derived Stats (v0)

Derived stats are functions of attributes, skills, and sometimes traits. They
serve as bridges to the runtime metrics defined in D-RUNTIME docs.

### 6.1 Learning & information

- **archive_literacy_score**  
  - Derived from INT multiplier, **Scholarship** skill, and Literacy trait.  
  - Higher values → more effective `StudyArchives` actions
    (D-RUNTIME-0106), more and better precedents per session.

- **rumor_attunement_score**  
  - Derived from CHA multiplier, **Streetwise** and **Intrigue** skills.  
  - Higher values → more effective `WorkRumorCircles` actions, better
    signal-to-noise in rumor-based precedent.

- **memory_capacity_base**  
  - Derived from INT and WIL multipliers; scaled by role importance.  
  - Sets initial capacity for `PersonalPrecedentLibrary` (D-RUNTIME-0106).

### 6.2 Survival, stress, and combat

- **Stress Tolerance**  
  - Derived from CON + WIL multipliers.  
  - Affects how quickly stress and seat_risk accumulate under pressure.

- **Command Presence**  
  - Derived from CHA + WIL multipliers and **Tactics & Command** skill.  
  - Drives garrison morale, obedience, and willingness to follow harsh orders.

- **Personal Security**  
  - Derived from CON + WIL multipliers, **Security Craft** and **Intrigue**.  
  - Modulates assassination risk, susceptibility to coups and ambushes.

### 6.3 Suit & environment handling

- **Suit Proficiency**  
  - Derived from INT, AGI, CON multipliers and **Suit Operation** skill.  
  - Affects survival in harsh environments, incident rates, and water recovery
    efficiency.

- **Suit Maintenance Quality**  
  - Derived from INT multiplier and **Suit Maintenance** + **Mechanics**.  
  - Influences failure rates and long-term degradation.

### 6.4 Economic & social influence

- **Economic Acumen**  
  - Derived from INT multiplier, **Finance & Ledgers**, **Market Lore**,
    and **Bargaining**.  
  - Used when agents make decisions that trade near-term extraction against
    long-term viability.

- **Social Capital**  
  - Derived from CHA multiplier, **Diplomacy**, **Oratory**, and **Streetwise**.  
  - Tracks how easily agents can secure favors, call in debts, and mobilize
    allies.

Exact formulas MAY vary by implementation; the key is that derived stats must
be **pure functions** of attributes, skills, and traits so they remain
recomputable when the agent learns or changes.

---

## 7. Learning & Progression Hooks

This section defines how attributes and skills **change over time**. Detailed
XP and training rules are out-of-scope for v0 and live in the runtime; this
document defines the **interfaces**.

### 7.1 Skill advancement

- Skills gain XP when used in meaningful checks or via dedicated training
  actions (practice, drills, tutors).  
- When XP exceeds a threshold, the skill rating increases by +1 (to a maximum
  of 5 in v0).  
- XP thresholds MAY be nonlinear (higher ratings require disproportionately
  more practice).

### 7.2 Attribute advancement

- Attributes change **slowly**, if at all.
- v0 recommendation:
  - Attribute increases require long periods of focused training, significant
    story events, or rare technologies.
  - Decreases may occur from injuries, deprivation, or aging events.

Attributes SHOULD be more stable than skills; most learning should happen at
the skill and derived-stat layers.

### 7.3 Interaction with precedent-based learning

D-RUNTIME-0106 defines:

- `learning_drive`
- `memory_training_xp`
- `memory_capacity_current`
- `bias_strength` and diversity-based updates

This document provides the **raw capacity**:

- Archive and rumor skills determine how **efficiently** learning actions
  translate into usable precedent.  
- Attributes like INT and WIL define the **ceiling** for memory capacity and
  stress handling.

Implementations SHOULD:

- use `archive_literacy_score` and `rumor_attunement_score` to scale
  `XP_ARCHIVE` and `XP_RUMOR` gains in D-RUNTIME-0106, and
- allow long-term high-learning agents to develop significantly larger and
  richer precedent libraries than low-learning ones.

---

## 8. Future Extensions (v1+)

The following are explicitly out-of-scope for v0 but good candidates for later:

- species- or caste-specific attribute baselines and caps,
- more granular skill ratings (e.g. 0–10) with smoother XP curves,
- per-office or per-faction **skill packages** for faster NPC generation,
- formal treatment of **opposed checks** and degree-of-success mechanics,
- modeling of **training infrastructure** (guild schools, military academies)
  as world entities that affect progression rates,
- explicit modeling of **cunning** as a derived scalar used in intrigue and
  high-level AI behaviors.

Until such extensions are written, **D-AGENT-0006** SHOULD be treated as the
canonical reference for attributes and skills. Other documents (e.g. Tier-3
examples, industry or law-specific skill lists) MUST be compatible with this
schema.
