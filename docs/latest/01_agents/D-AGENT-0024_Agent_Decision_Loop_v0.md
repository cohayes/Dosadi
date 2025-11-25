---
title: Agent_Decision_Loop
doc_id: D-AGENT-0024
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0006   # Agent_Attributes_and_Skills_v0
  - D-AGENT-0023   # Agent_Goal_System_v0
  - D-MEMORY-0002  # Episode_Schema_and_Memory_Behavior_v0
  - D-MEMORY-0003  # Episode_Transmission_Channels_v0
  - D-LAW-0011     # Founding_Council_Protocols_v0
  - D-LAW-0012     # Proto_Political_Body_Formation_and_Protocol_Governance_v0
---

# 01_agents · Agent Decision Loop v0 (D-AGENT-0024)

## 1. Purpose & Scope

This document specifies a **conceptual decision loop** for agents in Dosadi.

It answers the question:

> At tick _t_, given my goal stack, my remembered episodes and patterns, and
> any applicable protocols, which action do I choose?

The loop is intended to:

- sit on top of the **Agent Core Schema** (D-AGENT-0001) and
  **Attributes & Skills** (D-AGENT-0006),
- use the **Goal System** (D-AGENT-0023) as the driver of priorities,
- consult **episodes and patterns** (D-MEMORY-0002),
- be modulated by **protocols and proto-political bodies**
  (D-LAW-0011, D-LAW-0012),
- and operate in a way that can be specialized for Tier-1, Tier-2, and Tier-3
  agents.

This is a behavior spec, not a code-level algorithm. Numerical thresholds and
data structures are left to implementation documents and runtime modules.

---

## 2. Inputs to the Decision Loop

At the start of each decision step (e.g. each tick, or each agent-activation),
an agent has access to:

1. **Internal State**
   - physical status (health, fatigue, hunger, heat stress, injuries),
   - psychological status (stress, morale),
   - attributes and derived stats (D-AGENT-0006),
   - currently active **goals** and their priorities (D-AGENT-0023).

2. **Perceived Environment**
   - local sensory information:
     - who is nearby,
     - immediate hazards,
     - current crowding, visible patrols, etc.
   - cached beliefs about the area:
     - patterns about places, people, and times (D-MEMORY-0002),
     - known hazards, safe spots, profitable hubs.

3. **Applicable Protocols**
   - protocols relevant to:
     - this agent’s role (worker, foreman, council clerk, etc.),
     - this location (ward, facility, corridor),
     - this situation (alarm state, ration window, curfew).
   - including both formal protocols and protocol-like propaganda
     (D-MEMORY-0003, D-LAW-0011, D-LAW-0012).

4. **Recent Episodes**
   - fresh episodes from the current or last few ticks:
     - personal experience,
     - conversations, stories, reports seen or heard.

These inputs feed the decision pipeline described below.

---

## 3. High-Level Decision Pipeline

The **Agent Decision Loop** is framed as a six-stage conceptual pipeline:

1. **Goal Focus Selection**
2. **Contextual Recall**
3. **Option Generation**
4. **Option Evaluation**
5. **Protocol & Constraint Application**
6. **Action Selection (with Exploration)**

### 3.1 Stage 1: Goal Focus Selection

The agent first determines **which goals are hot this tick**.

- Start from the agent’s current goal set (D-AGENT-0023) with priorities.
- Adjust priorities based on:
  - internal state:
    - extreme hunger or imminent heat stroke can temporarily overshadow
      long-range goals,
  - external triggers:
    - alarms, threats, sudden opportunities,
  - personality traits:
    - high ambition may elevate status goals,
    - high communal lean may elevate kin or pod protection.

Output:

- a small **focus set** of top goals for this decision (e.g. 1–3 goals).

### 3.2 Stage 2: Contextual Recall

Given the focus goals and the immediate situation, the agent:

- queries personal **patterns** and **episodes** (D-MEMORY-0002),
- optionally queries external memory (journals, wall charts) if available,
- retrieves:
  - known options that have been tried before,
  - known consequences in similar contexts,
  - known reputations of nearby people and places.

Recall is biased by:

- salience of episodes,
- source reliability (self vs rumor vs archive),
- personal credulity/cynicism.

Output:

- a contextual **belief set**:
  - “this corridor is dangerous at night”,
  - “foreman L is lenient”,
  - “queue B often runs out of rations early”.

### 3.3 Stage 3: Option Generation

The agent builds a small set of **candidate actions**, based on:

- role and skills:
  - a Tier-1 laborer might consider:
    - queue for rations,
    - skip line,
    - trade with a neighbor,
    - complain to a foreman.
  - a Tier-3 steward might consider:
    - adjust protocol,
    - order a survey,
    - reshuffle assignments,
    - ignore the issue.

- situation templates:
  - patterns in memory provide typical “moves” for similar situations:
    - hide, obey, negotiate, escalate, report, sabotage, etc.

- personality and goals:
  - brave vs cautious,
  - communal vs self-serving.

Output:

- a set of candidate actions with rough tags:
  - expected time, effort,
  - risk exposure,
  - social visibility.

### 3.4 Stage 4: Option Evaluation

The agent assigns a rough **expected value** to each option relative to the
current focus goals.

Factors include:

- expected impact on each focus goal:
  - survival, status, control, kin protection, etc.
- risk:
  - danger of injury or death,
  - risk of punishment or social sanction,
  - risk of losing future options.
- long-term vs short-term:
  - some goals are discounted over time,
  - personality and attributes affect discounting.

Evaluation uses:

- patterns:
  - “people caught skipping line are usually beaten”,
  - “cooperating with this steward often leads to better shifts later”.
- recent episodes:
  - “yesterday patrol B was in a bad mood”,
  - “the last person who complained was quietly transferred”.

Output:

- a **scored list** of options per focus goal (conceptually, not
  necessarily numeric).

### 3.5 Stage 5: Protocol & Constraint Application

Protocols act as **structural modifiers** on option evaluation:

- Hard constraints:
  - some actions may be effectively forbidden for certain roles/contexts:
    - leaving post during alarm,
    - accessing sealed areas without clearance.
- Soft constraints and nudges:
  - protocol-compliant options may be:
    - safer from punishment,
    - more likely to gain institutional favor.
- Contradictions:
  - conflicts between protocols and experienced reality
    (e.g. protocol says “queue will be fair,” episodes say otherwise)
    can:
    - lower trust in the protocol,
    - increase perceived risk of compliance,
    - encourage cautious defection or quiet workarounds.

Political bodies (D-LAW-0012) influence:

- which protocols apply,
- how strictly they are enforced,
- which exceptions are tolerated for which agents.

Output:

- updated option evaluations factoring in:
  - policy constraints,
  - enforcement expectations,
  - reputational effects of compliance/non-compliance.

### 3.6 Stage 6: Action Selection (with Exploration)

Finally, the agent chooses an action.

The selection rule balances:

- **exploitation**:
  - picking the option that appears best under current beliefs,
- **exploration**:
  - occasionally trying alternatives, especially when:
    - beliefs are weak or conflicted,
    - curiosity/exploration goals are high,
    - current protocols or patterns seem failing.

Noise sources include:

- misperception,
- emotional overload (panic, rage),
- impulsivity or fatigue-driven shortcuts.

Output:

- a single chosen **action** for this decision loop invocation,
- possible creation of **new episodes** capturing the attempt and its outcome.

---

## 4. Tier-Specific Variants

The above pipeline is generic. Different agent **tiers** (as used elsewhere in
the project) emphasize different parts.

### 4.1 Tier-1 Decision Loop (Workers, Grunts, Commoners)

Tier-1 agents:

- have limited memory capacity and fewer goals,
- rely heavily on:
  - local patterns,
  - habits,
  - immediate protocols,
  - neighborhood rumors.

Simplifications:

- **Goal Focus**:
  - dominated by survival and immediate family/pod concerns.
- **Recall**:
  - mostly local episodes and simple pattern tags (“safe/unsafe”, “fair/unfair”).
- **Option Generation**:
  - small, stereotyped set of actions per context (queue, comply, dodge, trade).
- **Evaluation**:
  - short horizon, highly risk-averse or risk-seeking depending on personality.
- **Protocol Application**:
  - strong influence where enforcement is visible,
  - weak where enforcement is inconsistent.
- **Exploration**:
  - mostly random drift unless driven by strong traits (recklessness, curiosity).

Tier-1 loops make the world feel **dense and noisy**, but can still show
emergent behavior via crowd-level patterns.

### 4.2 Tier-2 Decision Loop (Foremen, Squad Leaders, Clerks, Auditors)

Tier-2 agents:

- sit at the interface between protocols and workers,
- have explicit **role-based duties**,
- must balance:
  - personal goals,
  - group goals (crew, pod, ward),
  - directives from Tier-3.

Differences from Tier-1:

- **Goal Focus**:
  - duty and role goals matter strongly (e.g. “keep this line orderly”).
- **Recall**:
  - broader memory of incidents across shifts,
  - greater access to formal reports and patterns.
- **Option Generation**:
  - includes:
    - local protocol bending,
    - targeted discipline,
    - selective reporting.
- **Evaluation**:
  - must weigh:
    - crew loyalty vs compliance,
    - performance metrics vs human risk,
    - future promotion vs scapegoating dangers.
- **Protocol Application**:
  - often have limited authority to interpret or adapt protocols.
- **Exploration**:
  - more strategic experimentation with minor local changes.

Tier-2 loops are key to **how protocols actually manifest** in the world:
they are the human interface of the system.

### 4.3 Tier-3 Decision Loop (Stewards, Council Members, Guild Masters, Cartel Planners)

Tier-3 agents:

- have many goals (status, dynasty, control, stability, personal grudges),
- have access to **large episode sets** via archives and reports,
- operate at a scale where a single decision affects many Tier-1 and Tier-2
  agents.

Differences from Tier-1 and Tier-2:

- **Goal Focus**:
  - can explicitly weigh multiple, long-range goals:
    - city stability vs personal power vs guild growth vs favor with the
      crown.
- **Recall**:
  - pattern-heavy:
    - uses summaries, trends, anomaly reports.
- **Option Generation**:
  - large but structured:
    - change protocol,
    - shift resources,
    - promote/demote individuals,
    - create or dismantle political bodies,
    - seed rumors or propaganda campaigns.
- **Evaluation**:
  - uses projections and heuristics:
    - expected impact on stress, fragmentation, legitimacy,
    - expected reactions from other political bodies.
- **Protocol Application**:
  - they **author and revise** protocols, not just obey them.
- **Exploration**:
  - may experiment with pilot programs or controlled trials in smaller wards
    before city-wide changes.

Tier-3 loops drive **campaign-scale dynamics**: regime strategies,
large-scale shifts, and cascading episodes.

---

## 5. Integration With the Simulation Runtime

### 5.1 Activation Cadence

The decision loop can be invoked:

- once per **tick**, for all agents or a scheduled subset, or
- on a **per-event** basis:
  - when a significant stimulus arrives (threat, opportunity, command).

Tier differentiation may apply:

- Tier-3: updated less frequently but with heavier computations (strategic
  decisions).
- Tier-2: medium cadence, particularly around start/end of shifts or when
  receiving reports.
- Tier-1: high cadence but with simple, cached decisions and short-term focus.

### 5.2 Episode Generation

Every decision loop invocation has the potential to:

- create new **episodes** when the agent acts and observes outcomes,
- update existing patterns during rest cycles (D-MEMORY-0002),
- feed upward through transmission channels (D-MEMORY-0003) to political
  bodies (D-LAW-0012).

### 5.3 Hooks for AI Policy Profiles

Higher-level AI policy profiles (e.g. “cautious CI”, “reckless cartel”) can be
implemented as:

- modifiers to:
  - goal weights (e.g. boost Control/Prediction/Order vs Survival),
  - risk appetite,
  - protocol obedience,
- presets for:
  - how options are generated or pruned,
  - how exploration vs exploitation is balanced.

These profiles can be attached to key Tier-3 agents or bodies to simulate
different regimes.

---

## 6. Future Work

Future documents SHOULD:

- define concrete **action sets** per role and context:
  - D-AGENT-000x Agent_Action_API refinements,
- specify:
  - decision loop variants for different AI sophistication levels
    (e.g. scalar heuristics vs RL-based policies),
  - how learning updates adjust:
    - goal priorities,
    - pattern beliefs,
    - protocol trust,
- provide **worked examples** of:
  - Tier-1, Tier-2, Tier-3 loops in representative scenes
    (ration line, exo-bay maintenance, coup rumor, guild safety crisis),
- and integrate with:
  - **RUNTIME** metrics (stress, fragmentation, legitimacy),
  - **MEMORY** systems (episode storage and decay),
  - **LAW** and **INFO_SECURITY** (sanctions, secrecy, censorship).

D-AGENT-0024 should be treated as the conceptual backbone of agent behavior in
Dosadi: the place where goals, memory, and protocols are woven into concrete
choices, tick after tick.
