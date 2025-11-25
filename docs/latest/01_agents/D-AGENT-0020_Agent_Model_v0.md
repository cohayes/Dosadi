---
title: Agent_Model
doc_id: D-AGENT-0020
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-AGENT-0006   # Agent_Attributes_and_Skills_v0
  - D-AGENT-0023   # Agent_Goal_System_v0
  - D-AGENT-0024   # Agent_Decision_Loop_v0
  - D-MEMORY-0002  # Episode_Schema_and_Memory_Behavior_v0
  - D-MEMORY-0003  # Episode_Transmission_Channels_v0
  - D-LAW-0012     # Proto_Political_Body_Formation_and_Protocol_Governance_v0
---

# 01_agents · Agent Model v0 (D-AGENT-0020)

## 1. Purpose & Scope

This document provides a **canonical skeleton** for agents in Dosadi.

It brings together, into a single model:

- core **identity and classification** (tier, roles, factions),
- **attributes** and **derived stats**,
- **personality traits**,
- **physical & psychological state variables**,
- **skills** (in brief; detailed lists live in D-AGENT-0006),
- **goals** (D-AGENT-0023),
- **episodic and pattern memory** (D-MEMORY-0002/0003),
- **social relations and faction affiliations**.

The intention is to define a stable conceptual shape for an agent object that
the runtime, scenario, and UI layers can all target.

This is a structural spec, not an exhaustive enumeration of all skills, goals,
or factions.

---

## 2. High-Level Facet Overview

Each agent is modeled as a bundle of interlocking facets:

1. **Identity & Classification**
   - who this agent is, where they sit in the city, and what roles they hold.

2. **Core Attributes**
   - six primary numeric stats centered on human-average 10.

3. **Personality Traits**
   - stable temperamental levers (ambition, bravery, communal vs self-serving,
     etc.).

4. **Physical & Psychological State**
   - dynamic variables like hunger, fatigue, injuries, stress, trauma.

5. **Skills & Derived Stats**
   - competencies and higher-level performance measures.

6. **Goals**
   - structured goal stack with primary and sub-goals.

7. **Episodic & Pattern Memory**
   - stored episodes and compressed beliefs about places, people, protocols.

8. **Social Graph & Faction Ties**
   - relationships to other agents and membership in pods, guilds, councils,
     cartels, etc.

These facets are read and updated by the **Agent Decision Loop** (D-AGENT-0024)
on each activation.

---

## 3. Identity & Classification

### 3.1 Static Identifiers

- **agent_id**
  - unique, persistent identifier.

- **name / alias**
  - label used in UI and narrative outputs.

- **tier**
  - {1, 2, 3}:
    - Tier-1: workers, commoners, frontline.
    - Tier-2: foremen, squad leaders, clerks, auditors.
    - Tier-3: stewards, council members, guild masters, cartel planners.

### 3.2 Roles & Positions

- **role_tags**
  - functional labels, possibly multiple:
    - e.g. "ration_clerk", "guild_safety_officer",
      "cartel_logistics", "militia_squad_lead".

- **office / seat_ref**
  - reference to any official seat in a political body:
    - council seat, guild board seat, ward committee position, etc.

- **ward / locality**
  - primary ward or zone association,
  - may include finer-grain location tags (bunk block, corridor cluster, pod).

### 3.3 Legal & Social Status

- **legal_status**
  - e.g. registered citizen, indentured worker, outlaw, probation, etc.

- **reputation_summary**
  - compressed view for UI and fast decisions:
    - e.g. {"honest": "medium", "violent": "low", "reliable": "high"}.

---

## 4. Core Attributes

Attributes follow the scheme defined in D-AGENT-0006:

- baseline human-average = 10,
- each step represents ~10% multiplicative change from the prior step,
- e.g. 11 ≈ 1.1×, 9 ≈ 0.9×, etc.

### 4.1 Primary Attributes (brief recap)

- **Strength (STR)**
  - physical power, load-bearing, melee force.

- **Dexterity (DEX)**
  - coordination, fine motor skill, balance.

- **Endurance (END)**
  - stamina, resistance to fatigue, illness, environmental stress.

- **Intellect (INT)**
  - analytical capacity, pattern recognition, planning.

- **Willpower (WIL)**
  - mental resilience, focus under stress, ability to endure hardship.

- **Charisma (CHA)**
  - social fluency, persuasive capacity, reading other people.

These feed into **derived stats** and influence skills, memory capacity,
learning, and decision loop behavior.

---

## 5. Personality Traits

Agents have relatively stable personality axes (see prior personality work),
for example:

- **Ambition ↔ Contentment**
  - desire for status, power, and advancement vs satisfaction with current
    position.

- **Bravery ↔ Caution**
  - tolerance for physical and social risk.

- **Honesty ↔ Deceitfulness**
  - baseline disposition towards truth-telling vs manipulation.

- **Communal ↔ Self-Serving**
  - identification with group well-being vs personal gain.

- **Curiosity ↔ Routine-Seeking**
  - drive to explore, learn, and change vs preference for familiar patterns.

- **Trusting ↔ Paranoid**
  - default stance towards new people and institutions.

Personality traits:

- modulate **goal creation and prioritization**,
- bias **episodic encoding and interpretation**,
- shape **channel preferences** (who they talk to, what they write, whether
  they journal),
- influence **protocol obedience vs quiet defection**.

---

## 6. Physical & Psychological State

Dynamic state variables capture the agent’s current condition.

### 6.1 Physical State

- **health**
  - overall integrity; includes illness and injury.

- **fatigue**
  - short-term exhaustion; affects performance, risk of error.

- **hunger / hydration**
  - proximity to critical survival thresholds.

- **heat_stress / cold_stress**
  - environmental load relative to suit and habitat protection.

- **injury_flags**
  - specific conditions:
    - broken limb, burns, chronic issues, etc.

These interact closely with survival-related goals and can override longer-term
ambitions when extreme.

### 6.2 Psychological State

- **stress**
  - acute pressure from threats, overload, or high stakes.

- **morale**
  - longer-term emotional tone (optimistic, resigned, rebellious).

- **trauma_markers**
  - flags or counters reflecting repeated extreme episodes (violence, betrayal,
    environmental terror).

- **burnout / numbness**
  - reduced responsiveness to stimuli after prolonged overload.

Psychological state affects:

- how episodes are encoded and replayed,
- risk-taking behavior,
- susceptibility to rumors and propaganda,
- capacity to engage in complex planning.

---

## 7. Skills & Derived Stats (Brief)

### 7.1 Skills

Skills are detailed in D-AGENT-0006. Here we only note:

- **skill_profile**
  - mapping of skill_name → rating (e.g. 0–5),
  - typically interpreted as baseline success chance vs normal difficulty
    (e.g. 0%–125% before modifiers).

Example categories:

- leadership & coordination (Oratory, Logistics, Mediation),
- technical & industrial (Suit_Maintenance, Reactor_Handling, Fabrication),
- social & covert (Negotiation, Interrogation, Shadowing),
- survival & combat (Nav, Firearms, Close_Quarters, First_Aid).

The agent model treats skills as:

- competencies used in **action checks** inside the decision loop,
- lenses shaping which options are even considered (agents rarely propose
  actions they feel wholly unqualified for, unless desperate).

### 7.2 Derived Stats

Derived stats combine attributes, personality, and sometimes skills into
higher-level measures, e.g.:

- **Cunning**
  - composite of INT, CHA, paranoia, and experience with deception.
- **Resilience**
  - composite of END, WIL, trauma history, and support structure.
- **Leadership Weight**
  - ability to get others to follow:
    - CHA, reputation, role legitimacy, past performance.
- **Perception of Control**
  - how in-control the agent feels:
    - crucial for how they respond to stress and risk.

Derived stats are used to:

- modulate goal weighting (e.g. high “perception of control” might tilt an
  agent towards ambitious actions),
- influence memory patterns (cunning agents better detect manipulation),
- adjust decision loop parameters (e.g. how many options they consider).

---

## 8. Goals

The goal system is defined in D-AGENT-0023. At the agent level we track:

- **goal_stack**
  - list of active goals, each with:
    - type (template),
    - parameters (who, what, where, by when),
    - priority,
    - status (active, achieved, failed, abandoned).

Examples:

- Primary: survive; protect children; maintain position.
- Sub-goals:
  - secure two decent meals per day,
  - obtain a safer bunk for the pod,
  - avoid Patrol_B for the next week,
  - advance towards a guild apprenticeship.

Goals:

- are generated and updated based on:
  - attributes and personality,
  - episodes (what has worked/failed before),
  - social context (offers, threats, obligations).
- drive **Goal Focus Selection** in the decision loop (D-AGENT-0024),
- guide which episodes are encoded and retained.

---

## 9. Episodic & Pattern Memory

Agents store and use memory as per D-MEMORY-0002.

### 9.1 Episodic Memory

- **episodes**
  - personal list of episodes the agent holds internally:
    - self-experienced,
    - heard via conversation or storytelling,
    - read in archives or seen in visual media.

Each episode tracks:

- goal linkage,
- context, actions, outcomes,
- salience and reliability,
- source.

### 9.2 Patterns & Beliefs

From episodes, agents derive compressed patterns:

- **place_beliefs**
  - e.g. corridor X is dangerous at night,
  - food hall Y is usually fair,
  - ward Z is harsh on infractions.

- **person_beliefs**
  - judgments of specific agents:
    - fair, cruel, corruptible, competent, etc.

- **protocol_beliefs**
  - whether posted rules:
    - are followed,
    - protect or endanger,
    - can be bent.

Patterns form a **subjective map** of the city and its institutions that
strongly shapes decisions.

---

## 10. Social Relations & Faction Affiliations

### 10.1 Social Graph

Each agent maintains a local social graph, e.g.:

- **kin_relations**
  - immediate family, extended kin (with strengths and responsibilities).

- **trust_relations**
  - allies, patrons, protégés, rivals, enemies:
    - each with:
      - trust level,
      - history of key episodes,
      - current obligations.

- **pod / crew / squad**
  - close working and living partners.

Social relations affect:

- who the agent shares episodes with,
- who they defer to or defy,
- whose goals they partially internalize.

### 10.2 Faction & Body Memberships

Agents can belong to one or more larger bodies:

- **pods / households**
- **guilds / industries**
- **military units**
- **councils / ward committees**
- **cartels / clandestine networks**

For each membership, track:

- role (rank, office, novice, veteran),
- loyalty strength,
- benefits (protection, resources, information access),
- risks (scrutiny, obligations, punishments).

Faction ties:

- determine access to **protocols**, archives, and communication channels,
- shape Control/Prediction/Order goals at a group level,
- are the hooks for political bodies described in D-LAW-0012.

---

## 11. Integration with the Decision Loop

The Agent Decision Loop (D-AGENT-0024) operates over this model:

- **Goal Focus Selection**
  - reads goal_stack, internal state, personality.
- **Contextual Recall**
  - reads episodes, patterns, place/person/protocol beliefs.
- **Option Generation**
  - uses role_tags, skills, attributes, and faction memberships.
- **Option Evaluation**
  - uses derived stats, beliefs, and physical/psychological state.
- **Protocol & Constraint Application**
  - uses memberships, protocols attached to roles/wards/factions.
- **Action Selection**
  - may add new episodes and alter goals and social relations.

This closes the loop:

> Agent model → Decision loop → World interaction → New episodes →
> updated agent model.

---

## 12. Future Work

Future documents SHOULD:

- flesh out:
  - a full **skill catalog** and tagging system (D-AGENT-0006+),
  - **personality templates** for different archetypes (e.g. steward, cartel
    planner, garrison hardliner),
  - **social graph dynamics** (how relationships form, strengthen, decay),
- specify:
  - minimal vs full agent representations (for Tier-1 crowds vs named
    Tier-3 figures),
  - mechanisms for **agent aging, promotion, and succession**,
- and integrate:
  - suit & inventory schemas (from the SUITS and INVENTORY pillars),
  - health & metabolism models (HEALTH pillar),
  - economic roles (ECONOMY pillar).

D-AGENT-0020 is the structural backbone for all such elaborations: a single,
coherent picture of what a Dosadi agent *is* in the simulation.
