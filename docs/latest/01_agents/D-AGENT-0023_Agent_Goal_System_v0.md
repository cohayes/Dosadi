---
title: Agent_Goal_System
doc_id: D-AGENT-0023
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-24
depends_on:
  - D-AGENT-0001  # Agent_Core_Schema_v0
  - D-AGENT-0006  # Agent_Attributes_and_Skills_v0
  - D-RUNTIME-0107  # Campaign_Phases_and_Golden_Age_Baseline
  - D-RUNTIME-0108  # Founding_Sequence_and_Communal_Coherence
---

# 01_agents · Agent Goal System v0 (D-AGENT-0023)

## 1. Purpose & Scope

This document defines the **goal-based decision system** for Dosadi agents.

Instead of modeling behavior as a set of continuously-updated "drives"
competing directly for control, agents maintain a **hierarchy of goals**
and sub-goals ("what I want"), and choose actions (skill checks) in service of
those goals. Physical and psychological fields (hunger, fatigue, fear,
isolation, etc.), together with personality and context, **generate and
reprioritize** goals over time.

This document:

- introduces the distinction between **goals**, **sub-goals**, and **goal
  families**;
- categorizes common Dosadi goals (survival, comfort, affiliation, ambition,
  dynasty, curiosity, etc.);
- distinguishes **repeating**, **episodic**, and **long-arc** goals; and
- outlines the main **triggers** that create or reprioritize goals.

It does **not** assign numeric weights or algorithms; those are left for
implementation documents and later revisions.

---

## 2. Core Concepts

### 2.1 Agents and Actions (recap)

Agents are defined by:

- attributes (STR, AGI, CON, INT, WIL, CHA),
- skills (e.g. Medical_Care, Diplomacy, Suit_Maintenance),
- personality traits (ambition, communal, paranoia, dogmatism, curiosity,
  cruelty, etc.),
- physical & psychological state fields (hunger, fatigue, injury, stress,
  loneliness, etc.).

**Actions** are **skill applications in context**:

- each action ("eat a ration", "cross a wet floor", "negotiate allocation")
  is modeled as one or more **skill checks** plus attribute/derived-stat
  gating where needed;
- many actions (e.g. walking in normal conditions, eating a basic ration) are
  **trivial** and can be treated as auto-success unless a difficulty modifier
  is present (e.g. walking on oil, eating in a high-pressure social setting).

### 2.2 Goals

A **goal** is a structured statement of desired outcome, for example:

- "Maintain survival this week.",
- "Acquire two good-quality meals today.",
- "Secure a safer bunk in a quiet bay.",
- "Join the medical task force.",
- "Ensure my child receives a guild apprenticeship.",
- "Preserve my dynasty's influence in this ward."

Goals may have:

- a **hierarchy** (primary goals and sub-goals),
- a **temporal horizon** (short, medium, long),
- a **status** (active, achieved, failed, shelved),
- and a **priority** relative to other goals.

Goals are created, updated, and retired in response to:

- internal state (body + psyche),
- personality,
- assets and social ties,
- and environment/events (opportunities, threats, decrees).

### 2.3 Sub-goals and Hierarchy

High-level goals usually decompose into more concrete sub-goals. Examples:

- **Primary goal: Survival**  
  - Sub-goal: "Acquire 2 good-quality meals each day."  
  - Sub-goal: "Secure access to decent and safe sleeping arrangements."  
  - Sub-goal: "Maintain suit integrity for my work environment."

- **Primary goal: Preserve Dynasty**  
  - Sub-goal: "Have at least one child."  
  - Sub-goal: "Secure a stable apprenticeship or office for the heir."  
  - Sub-goal: "Protect the family's reputation from major scandal."

When evaluating actions, agents primarily consider **active goals** near the
top of the hierarchy. Lower-level sub-goals guide concrete choices
(e.g. "go to this food hall" vs "volunteer for that task force").

### 2.4 Goal Families

Many goals share structure and function. We group them into **goal families**:

- Survival & Physical Continuity
- Safety & Risk Management
- Resource & Comfort (Accumulation / Buffer)
- Social Affiliation & Belonging
- Status, Rank & Influence
- Competence & Skill Mastery
- Curiosity, Exploration & Information
- Bonding, Romance & Reproduction
- Legacy & Dynasty
- Moral / Ideological / Ethos
- Revenge, Justice & Repair
- Escape, Relief & Pleasure
- Control, Prediction & Order

Each family contains many specific goal instances (see §3).

### 2.5 Survival Is Not Always Supreme

For most agents, **Survival** will be the top-level, highest-priority goal
most of the time. However, in some cases agents will legitimately assign
higher priority to goals such as:

- preserving a dynasty,
- maintaining a core ethos,
- protecting a loved one,
- or accomplishing a mission of extreme personal significance.

When conflicts arise (e.g. live but betray my values versus die but preserve
them), agents may choose to **let Survival fail** in order to protect a higher
goal. This is intentional and central to Dosadi's behavioral richness.

---

## 3. Goal Families & Example Goals

This section catalogs major **goal families** and gives examples of both
generic and Dosadi-specific goals. These are not exhaustive, but serve as a
design palette.

### 3.1 Survival & Physical Continuity

"Stay basically alive and functional."

- Maintain viability
  - Avoid lethal injury today.
  - Avoid suit breach while in hostile zone.
  - Avoid catastrophic heatstroke during exo-work.
- Nutrition & hydration
  - Get two adequate meals today.
  - Secure one day of water buffer at home.
  - Stock three emergency rations in my bunk.
- Rest & recovery
  - Sleep at least N hours in the next 24.
  - Take rotational rest after heavy exo shifts.
  - Seek medical treatment for this injury.
- Health maintenance
  - Replace suit filters this week.
  - Repair damaged suit seals before next deployment.
  - Avoid exposure to toxic fumes in known hazard corridors.

These goals typically **repeat** or regenerate as long as the agent lives.

### 3.2 Safety, Security & Risk Management

"Not just alive, but safe enough."

- Reduce immediate risk
  - Move away from a corridor where violence just broke out.
  - Avoid patrol route rumored to be trigger-happy.
- Increase structural safety
  - Relocate sleeping space to a safer pod/zone.
  - Join a pod with reliable enforcement of basic norms.
  - Lobby for physical safety improvements (railings, seals, barriers).
- Contingency & redundancy
  - Cache extra water or tools in a hidden location.
  - Maintain a personal suit patch kit.
  - Diversify food sources to avoid dependence on a single hall.

Often spawned or reprioritized after **near-miss events** (accidents, fights,
scarcity shocks).

### 3.3 Resource & Comfort (Accumulation / Buffer)

"Build a buffer and improve quality of life."

- Material accumulation
  - Acquire a target amount of scrip or barter credits.
  - Build up several days of food reserve.
  - Own a personal exo-suit instead of relying on communal pool.
- Comfort
  - Upgrade from crowded barracks to a small shared room.
  - Obtain a suit with better climate control.
  - Ensure regular access to a preferred food hall.
- Access
  - Gain access to a sealed market zone.
  - Obtain a license for restricted corridors or elevators.
  - Secure a spot in a better-ventilated refuge or gathering space.

These goals can **ratchet**: once baseline comfort is met, agents may raise
what they consider "enough".

### 3.4 Social Affiliation & Belonging

"I want my people."

- Join or maintain a group
  - Belong to a reliable pod or bunk circle.
  - Stay in good standing with my crew and foreman.
  - Be accepted by a guild (suit techs, medics, clerks, etc.).
- Repair ruptures
  - Mend a critical relationship after conflict.
  - Restore trust with a ward steward after breaking a rule.
- Find a new tribe
  - Leave an unsafe or abusive pod for a better one.
  - Align with a new guild or faction whose norms or benefits fit better.

Modulated heavily by **communal**, **paranoia**, and **dogmatism**.

### 3.5 Status, Rank & Influence

"I want my standing to rise."

- Formal rank
  - Become foreman of the crew.
  - Gain a seat on a ward council.
  - Achieve master rank in a guild.
- Informal prestige
  - Be recognized as the best medic or suit tech in the pod.
  - Become the person others seek for advice.
  - Keep a reputation for fairness, toughness, or ruthlessness.
- Control over decisions
  - Gain veto influence over risky operations.
  - Control assignment rosters for a section.
  - Shape which pods receive allocations in tight times.

Central for agents high in **ambition** and **status sensitivity**.

### 3.6 Competence & Skill Mastery

"I want to actually be good at what I do."

- Learn or advance skills
  - Improve Medical_Care from 2 to 3.
  - Learn basic HVAC maintenance.
  - Advance Oratory to handle larger or more hostile crowds.
- Cross-train
  - Learn survival skills for outer wards.
  - Pick up enough administration to keep personal books.
- Maintain an edge
  - Avoid falling behind younger or rival specialists.
  - Stay ahead of peers in a critical technical domain.

These goals often interact with Status goals but can exist without them
(pure craft pride).

### 3.7 Curiosity, Exploration & Information

"I want to know how things are and why."

- Local exploration
  - Explore an unmapped cavern or corridor.
  - Investigate a sealed or restricted door.
- System-level understanding
  - Understand how Well allocations are actually decided.
  - Study recorded history of early settlement or previous crises.
  - Verify or falsify persistent rumors about elites.
- Information brokerage
  - Collect stories and consolidate them into a more accurate picture.
  - Map alliances and rivalries for later use.

Core to agents with high **curiosity** and strong precedent-learning behavior.

### 3.8 Bonding, Romance & Reproduction

"I want emotional bonds and/or a family."

- Romance and pair-bonding
  - Find a romantic partner.
  - Maintain a relationship through stress and shifting conditions.
  - Repair a faltering partnership.
- Family & children
  - Have a child.
  - Secure safe upbringing and basic opportunities for children.
  - Arrange apprenticeships or schooling for children.
- Kinship protection
  - Protect sick or weak kin from being cut off or abandoned.
  - Keep extended family co-located or in mutually supportive pods.

These goals are future-facing and feed directly into **Legacy & Dynasty**.

### 3.9 Legacy & Dynasty

"I want something of me to persist."

- Preserve a line or house
  - Ensure an heir inherits office, property, or influence.
  - Protect a family name from major scandals or disgrace.
- Institutional legacy
  - Build a guild or institution that outlives the founder.
  - Establish strong ward traditions (e.g. fairness in rationing, martial
    excellence).
- Monuments & memory
  - Attach personal or family names to buildings or programs.
  - Ensure deeds are recorded in archives and remembered.

These goals can legitimately **outrank personal survival** for some agents.

### 3.10 Moral, Ideological & Ethos Goals

"I must live (or die) by certain principles."

- Ethos adherence
  - Never betray comrades under pressure.
  - Refuse to accept or collaborate with unjust practices.
  - Uphold specific codes (e.g. rules about water usage, treatment of the
    dead, treatment of non-combatants).
- Propagation of an ethos
  - Spread a belief or code within a pod or guild.
  - Normalize certain rituals or constraints.
- Sacrifice
  - Accept punishment rather than implicate others.
  - Choose death or exile over violating a core taboo.

These are influenced by **dogmatism**, **honor**, and sometimes cultural
context (micro-cultures within wards, guilds, or families).

### 3.11 Revenge, Justice & Repair

"I must address wrongs."

- Revenge
  - Punish the person who betrayed, robbed, or humiliated me.
  - Destroy a rival pod that attacked my kin.
- Justice-seeking
  - Expose a corrupt steward or official.
  - Correct a serious unfair allocation or decision.
- Restitution
  - Compensate someone the agent wronged to repair reputation or alliances.

Depending on personality, these may compete with or override Survival and
Status goals (especially for high-dogmatism or high-honor agents).

### 3.12 Escape, Relief & Pleasure

"I need relief from pressure."

- Escape from stress
  - Acquire narcotics or other means to blunt anxiety or pain.
  - Hide from responsibilities in quiet spaces or crowds.
- Sensory or aesthetic pleasure
  - Seek better food or rare treats.
  - Attend music, storytelling, or ritual events.
- Social relief
  - Find spaces where speech feels free of audits or reprisal.
  - Vent with trusted peers after hard shifts.

These goals become particularly important in later campaign phases when
stressors mount.

### 3.13 Control, Prediction & Order

"I am uncomfortable with chaos and surprise."

- Reduce uncertainty
  - Learn schedules, policies, and standard operating procedures.
  - Keep personal logs of events and patterns.
- Shape environment
  - Rearrange workspaces for efficiency and predictability.
  - Advocate for clearer rules, signage, and communication.
- Avoid chaos
  - Oppose volatile leaders.
  - Support stable institutions even when they are imperfect.

Often overlaps with Curiosity but emphasizes **comfort in predictability**
rather than pure exploration.

---

## 4. Temporal Profiles of Goals

Goals differ in how they evolve over time. Three broad profiles are useful.

### 4.1 Repeating / Cyclical Goals

These goals **recur** or must be continuously satisfied:

- Eat adequately each day.
- Keep suit in functional condition.
- Maintain good standing in a pod or crew.
- Balance ledgers and meet routine quotas.

Often generated by **homeostatic fields** (hunger, fatigue), ongoing roles,
and continual social maintenance needs.

### 4.2 Episodic / One-Off Goals

These goals have a clear start and end:

- Join a specific task force.
- Move bunks to a quieter or safer bay.
- Acquire a particular license or permit.
- Pay back a specific debt.
- Avenge a singular insult or betrayal.

Once achieved or failed, they may disappear or morph into new goals
("maintain position", "avoid that rival", etc.).

### 4.3 Long-Arc Goals

These goals span long periods and may generate numerous sub-goals:

- Preserve a dynasty and pass influence to an heir.
- Become a major office-holder (e.g. duke-equivalent, guild head).
- Re-shape a ward's culture over decades.
- Improve overall Well policy over a career.

Long-arc goals are anchored in **personality** and life history, and will
often conflict with short-term comfort or safety.

---

## 5. Triggers for Goal Creation & Reprioritization

Goals emerge from the interaction of **internal fields**, **personality**, and
**environmental context**. Below are high-level trigger categories.

### 5.1 Physical & Physiological Fields

- Hunger / thirst / malnutrition
  - Spawn or boost nutrition/hydration goals (seek food/water, secure buffer).
- Fatigue / sleep debt
  - Spawn rest and recovery goals, lower priority on non-critical work.
- Injury / illness
  - Spawn treatment goals, avoidance of heavy or risky duties.
- Chronic pain / stress
  - Spawn escape/relief goals (narcotics, withdrawal from high-stress pods).

### 5.2 Psychological & Social State Fields

- Loneliness / isolation
  - Spawn affiliation goals (join group, repair relationships, find new pod).
- Status frustration
  - Spawn promotion, faction-switching, or undermining rivals.
- Cognitive dissonance (values vs actions)
  - Spawn justification, behavior change, or value-adjustment goals.
- Fear / perceived threat
  - Spawn flee, fortify, ally-with-stronger, or appeasement goals.
- Boredom / under-stimulation
  - Spawn novelty-seeking, skill training, or exploratory goals.

### 5.3 Personality Levers

Personality traits shape **what type of goals** are most likely and how
strongly they are pursued.

Examples:

- High **ambition**
  - Frequent Status, Rank, and Legacy goals.
- High **communal**
  - Strong Affiliation, Justice, and institutional-maintenance goals.
- High **cruelty**
  - More exploitative resource goals, revenge, and domination.
- High **paranoia**
  - Safety, control, redundancy, and pre-emptive strike goals.
- High **curiosity**
  - Exploration, investigation, and precedent-learning goals.
- High **dogmatism**
  - Strong ethos adherence, martyrdom, and rigid justice goals.

### 5.4 Environment & Event Triggers

- Opportunity
  - Recruitment campaigns (guild, task force, militia).
  - Vacant offices or newly created roles.
  - Construction of new sealed spaces or prestigious facilities.
- Threat
  - Accidents, collapses, disease outbreaks, visible injustices.
  - Rumors of upcoming ration cuts or purges.
- Social events
  - Betrayals, humiliations, public praise, new romance, birth or death.
- System-level shifts
  - Discovery that the Well is finite (campaign phase changes).
  - New decrees altering rights, obligations, or reward structures.

These external events **seed new goals** and **reshuffle priorities** across
existing ones.

---

## 6. Goal Template Patterns

Most goals can be expressed as parameterized patterns. This is useful for both
design and implementation.

Common patterns include:

- **Acquire / Maintain / Improve [RESOURCE]**
  - water, food, suit, bunk, scrip, tools, narcotics, access rights.
- **Acquire / Maintain / Improve [RELATION]**
  - friend, ally, patron, protégé, romantic partner, guild membership.
- **Acquire / Maintain / Improve [POSITION]**
  - job, rank, office, council seat, guild tier, ward stewardship.
- **Protect [ENTITY]**
  - self, child, lover, clan, pod, ward, institution, secret.
- **Avoid [OUTCOME]**
  - injury, disgrace, demotion, exile, loss of core access, being audited.
- **Change [STATE]**
  - move pods/wards, change faction, change job, change living conditions.
- **Learn [SUBJECT]**
  - skill, secret, historical pattern, corridor topology, Well policy.
- **Avenge / Punish [TARGET]**
  - individual, group, institution, informer or betrayer.

Future documents may formalize these patterns into structured goal types with
parameters. For now, they serve as **conceptual templates** for the kinds of
things Dosadi agents will repeatedly want.

---

## 7. Future Work

Subsequent documents SHOULD:

- define a **goal representation schema** (fields, priorities, and status);
- specify how **body and psyche fields** map into goal creation and priority
  updates numerically;
- define how goals interact with **action selection** (e.g. how many active
  goals are considered at once);
- and integrate goals with **learning systems** (e.g. how successful or failed
  goal pursuits update expectations and future goal formation).

D-AGENT-0023 SHOULD be treated as the conceptual reference for what Dosadi
agents can want and how broad categories of goals are shaped by personality,
state, and environment.
