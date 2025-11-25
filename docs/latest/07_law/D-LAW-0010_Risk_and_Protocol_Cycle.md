---
title: Risk_and_Protocol_Cycle
doc_id: D-LAW-0010
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-AGENT-0020   # Agent_Model_Foundation
  - D-AGENT-0021   # Agent_Goals_and_Episodic_Memory
  - D-RUNTIME-0001 # Simulation_Timebase
---

# 1. Purpose and Scope

This document defines the **Risk and Protocol Cycle** as a core law of motion for Dosadi's civilizational dynamics.

It describes how, over hundreds of years of simulated time, civilization on Dosadi emerges and evolves through a stable, repeated process:

1. **Risk discovery (bottom-up).**
2. **Coordination (group goal setting and asset deployment).**
3. **Codification (protocol authoring and enforcement).**
4. **Drift and stress (new risk regimes created by world change and protocols themselves).**

This cycle must operate:

- From **Founding Wakeup** (Phase 0, all colonists Tier-1) through late-stage cartel politics (Phase 2).
- Without external "god-logic": all changes arise via agent goals, episodic memory, patterns, and protocol mechanics.

The Risk and Protocol Cycle is a **conceptual law** that:

- Applies at every scale: pods, wards, guilds, cartels, councils, dynasties.
- Unifies early safety rules, mid-game rationing, and late-game repression under one loop.
- Provides a design invariant for tuning systems (law, economy, information, health, suits) without breaking the core logic.


# 2. Law of Iterated Risk Governance

## 2.1 Statement

> **Law of Iterated Risk Governance**
>
> Civilization on Dosadi is an iterated process of:
> **experiencing risk → aggregating experience → authoring protocols → suffering the side effects of those protocols → repeating.**

In other words:

- **Agents** live, act, and suffer or benefit.
- Their experiences become **episodes**, which aggregate into **patterns**.
- Groups with authority turn patterns into **protocols**.
- Protocols shift risk, temporarily stabilizing some domains while creating new risks in others.
- The process repeats indefinitely as the world changes and agents adapt.

## 2.2 Core corollaries

1. **All power is risk control.**  
   - Actors (especially Tier-3) who can **define** what counts as risk and **author** the protocols that address it effectively control:
     - Which agents bear risk.
     - Which agents are shielded.
     - What behaviors are normalized, outlawed, or taxed.

2. **All protocols become risk sources over time.**  
   - Protocols are authored to reduce specific risks but inevitably introduce new ones:
     - Resentment, perceived injustice, and resistance.
     - Blind spots and brittle dependencies (e.g. single points of oversight).
     - Corruption opportunities (e.g. selective enforcement, bribe channels).

3. **Groups are frozen risk bargains.**  
   - Pods, guilds, cartels, councils and unions are all ways of saying:
     - *“We will share these risks internally and shove those other risks outward.”*
   - Membership, dues, obligations, and privileges are components of that risk-sharing contract.

4. **Risk perception is subjective and local.**  
   - Agents operate on **episodic memory** and **subjective patterns**, not global truth.
   - Governance structures can be stable yet deeply miscalibrated, sowing the seeds of future crises.


# 3. The Risk and Protocol Cycle

The cycle has four main stages. They are not discrete in time; multiple cycles can overlap and nest.

## 3.1 Stage 1: Risk discovery (bottom-up)

**Input:**

- Uncoordinated agents pursuing their own goals (survival, status, kin protection, etc.).
- Early environments dominated by:
  - Environmental hazards (heat, exposure, corridors, exo-suit failure).
  - Social hazards (theft, violence, predation, betrayal).

**Mechanism:**

- Agents take actions and suffer consequences, generating **episodes** with:
  - Negative valence.
  - High perceived risk.
  - Links to survival or core identity goals.

- Agents form **place**, **person**, and **protocol** beliefs:
  - *“Corridor 7A is deadly at night.”*
  - *“Guard X shakes people down.”*
  - *“This rule is enforced only on the poor.”*

- Natural leaders/spokespeople accumulate more episodes and reports than others, giving them:
  - A richer view of local hazards.
  - Higher **LeadershipWeight** in the agent model.

**Output:**

- A growing pool of **risk-laden episodes** and partially formed beliefs.
- Pressure to reduce risk at the individual and pod level:
  - Staying in groups.
  - Avoiding certain routes.
  - Informally coordinating escorts or lookouts.


## 3.2 Stage 2: Coordination (group goal setting and assets)

**Input:**

- Clusters of agents with overlapping risks and interdependent goals.
- Emerging spokespeople or organizers within pods, squads, or work crews.

**Mechanism:**

- Individuals form **groups** (pods, patrols, work gangs, proto-councils) primarily to:
  - Pool protection (body count, watching each other's backs).
  - Share information about hazards.
  - Coordinate access to assets (suits, tools, bunk space).

- Groups set **group-level goals** (see `D-AGENT-0021`), especially:
  - `GATHER_INFORMATION` about hazards and anomalies.
  - `MITIGATE_RISK` in specific locations or processes.
  - `ORGANIZE_GROUP` for patrols, escorts, and task forces.

- Group goals are assigned to individual agents:
  - Scouts, guards, stewards, scribes, technicians, auditors.

**Output:**

- Coordinated sensing and intervention:
  - Regular patrols, structured scouting, systematic surveying.
- A clearer, though still local and biased, picture of the risk landscape.


## 3.3 Stage 3: Codification (protocol authoring and enforcement)

**Input:**

- Aggregated episodes and patterns from Stage 2.
- Group-level beliefs about:
  - Where risk is concentrated.
  - Who is expendable vs protected.
  - Which interventions seem effective.

**Mechanism:**

- Tier-2 and Tier-3 actors (stewards, council reps, guild heads, cartel planners) adopt **AUTHOR_PROTOCOL** and **ENFORCE_PROTOCOL** goals.

- Using their information funnels, they:
  - Identify high-risk or high-uncertainty buckets:
    - Dangerous corridors.
    - High-accident exo-bays.
    - Unstable gangs.
    - Well output anomalies.
  - Draft **protocols**:
    - Movement and traffic rules.
    - Ration schedules and access tiers.
    - Safety procedures and maintenance cycles.
    - Surveillance requirements and punishments.

- Protocols are then:
  - Communicated (posted, recited, drilled).
  - Enforced with varying intensity and bias.
  - Transformed into **READ_PROTOCOL** and **RECEIVED_ORDER** episodes for agents.

**Output:**

- Formal rules and procedures that:
  - Reassign risk (who is allowed where, with what, and under what conditions).
  - Create explicit obligations and privileges.
  - Define “legitimate” vs “illicit” behavior.

- Agents update **ProtocolBeliefs**:
  - Is this rule real or theater?
  - Who does it actually protect?
  - Who gets punished, and who walks free?


## 3.4 Stage 4: Drift and stress (new risk regimes)

**Input:**

- An active protocol regime in a changing world:
  - Population grows or shrinks.
  - Well output margins shift.
  - Technology advances.
  - Factions rise, fall, merge, and split.
  - Corruption and capture seep into institutions.

**Mechanism:**

- Protocols create **secondary risks**:
  - Enforcement creates resentment and pushes activity underground.
  - Rationing fosters black markets and cartelization.
  - Selective enforcement corrodes legitimacy and sparks quiet defection.
  - Overly rigid procedures cause catastrophic failures when conditions change.

- Agents experience these secondary risks as **episodes**:
  - Unfair beatings, arbitrary denial of rations, rigged tribunals.
  - Profitable workarounds, smuggling, bribes that work.

- These episodes:
  - Alter beliefs about protocols and factions.
  - Shift loyalty and willingness to comply.
  - Initiate new group formations (black markets, resistance cells).

**Output:**

- A new distribution of risk, often with:
  - Redistributions of power.
  - Accumulating tensions and hidden fault lines.
- Conditions ripe for:
  - Reforms, coups, crackdowns.
  - Emergence of parallel governance (cartels, militias, clandestine councils).

The loop then returns to **Stage 1**, but now with:

- Different dominant hazards.
- Different risk perceptions.
- Different players in control.


# 4. Phase-Specific Expressions of the Cycle

## 4.1 Phase 0: Golden Age Baseline

- **Dominant risks:**
  - Environmental exposure.
  - Unmapped corridors, falls, structural hazards.
  - Social in-fighting and theft within and between pods.

- **Coordination:**
  - Proto-councils form around bunk pods and shared corridors.
  - Goals:
    - Map corridors.
    - Identify safe paths.
    - Establish pod-level peace norms.

- **Protocols:**
  - Early safety rules (movement times, required escorts).
  - Basic bunk allocation and dispute resolution guidelines.

- **Drift:**
  - As corridors are tamed, attention shifts to productivity and comfort.
  - Risk of complacency and hidden structural weaknesses.


## 4.2 Phase 1: Realization of Limits

- **Dominant emerging risk:**
  - Well output is limited; margins between supply and demand shrink.

- **Discovery:**
  - Technicians, R&D teams, or stewards accumulate episodes:
    - `WELL_OUTPUT_ANOMALY`.
    - Unrealistic recovery curves.
    - Repeated failure of optimistic projections.

- **Coordination:**
  - Councils or technical boards adopt goals:
    - `GATHER_INFORMATION` specifically about Well behavior and consumption.
    - `STABILIZE_REGION` around Well access and industrial drawdown.

- **Protocols:**
  - Rationing rules and access tiers.
  - Efficiency mandates and waste penalties.
  - Monitoring and audit regimes.

- **Drift:**
  - New risks of:
    - Resentment toward rationing.
    - Favoritism in access.
    - Emergent black markets for water and suits.
  - Legitimacy begins to rely heavily on perceived fairness and competence.


## 4.3 Phase 2: Age of Scarcity and Corruption

- **Dominant risks:**
  - Chronic scarcity.
  - Elite capture of water, suits, and enforcement.
  - Cartelization of black markets.
  - Widespread narcotics use and dependency as a control and coping mechanism.
  - Open and clandestine political conflict.

- **Coordination:**
  - Tier-3 actors deploy:
    - Secret police, informant networks.
    - Asset-stripping and targeted allocations.
    - Negotiated truces with cartels.

- **Protocols:**
  - Harsh anti-hoarding and anti-smuggling laws (often selectively enforced).
  - Narcotics distribution controls (both formal and informal).
  - Expanded surveillance and loyalty-testing procedures.

- **Drift:**
  - These very protocols:
    - Feed resentment and rebellion.
    - Strengthen cartels who learn to exploit them.
    - Create brittle, high-pressure equilibria vulnerable to shocks.

- **Result:**
  - Coups, uprisings, and "sting waves":
    - All modeled within the same Risk and Protocol Cycle.
    - No special-case revolution system required.


# 5. Roles by Tier in the Cycle

## 5.1 Tier-1 (everyday agents)

- **Primary function:** Experiencers and carriers of risk.
- Generate most **episodes**:
  - Injuries, shortages, abuses, small wins.
- Update **local beliefs**:
  - About corridors, shops, guards, medics, pod leaders.
- Form small **groups**:
  - Pods, squads, gangs, mutual aid circles.

From their perspective, the cycle feels like:

- Sudden rule changes.
- Shifting dangers.
- Gossip and rumor about who is safe, who is dangerous, and what is “allowed if you are careful.”


## 5.2 Tier-2 (stewards, overseers, mid-level)

- **Primary function:** Aggregators and intermediaries.
- Turn scattered episodes into **reports** and early **patterns**.
- Manage **enforcement**:
  - Patrols, inspections, daily operations.
- Experience tensions:
  - Between top-down directives and bottom-up realities.
- Can become:
  - Stabilizing forces (honest stewards).
  - Corrupt brokers (fee-for-safety, selective enforcement).
  - Pivot points for reform or coups.

They are crucial to:

- How accurately risks are communicated upward.
- How harshly or fairly protocols are applied downward.


## 5.3 Tier-3 (kings, dukes, guild/cartel heads, high stewards)

- **Primary function:** Pattern readers and protocol authors.
- Receive:
  - Summaries of incidents, output metrics, unrest indicators, rumor clusters.
- Author:
  - The most impactful **protocols** and structural changes.
- Decide:
  - On which risks are acceptable and who should bear them.
  - When to reform, repress, or co-opt.

They are still constrained by:

- Biased information.
- Personal goals and fears.
- Competition from rival Tier-3 actors.

They cannot break the cycle; they can only ride and reshape it.


# 6. Design and Implementation Notes

## 6.1 Single loop, multiple content types

Engineers should treat the Risk and Protocol Cycle as a **content-agnostic loop**:

- Only the **incident types**, **goal targets**, and **protocol payloads** change across phases and contexts.
- The structure remains:
  - `Episodes → Patterns → Group Goals → Protocols → New Episodes`.

This allows:

- Early environmental safety and late political purges to be simulated by the same machinery.
- Incremental extension of risk types (health, narcotics, espionage) without new fundamental systems.

## 6.2 Parameterization hooks

Key tuning knobs:

- Thresholds for:
  - Risk scores that trigger group goals.
  - Confidence required to author protocols.
- Weights for:
  - Frequency vs severity vs reliability in pattern formation.
- Bias functions:
  - How strongly Tier-3 actors favor their allies vs enemies in protocol design.
- Enforcement intensity:
  - Patrol frequency, punishment severity, consistency.

Phase transitions (0 → 1 → 2) should be expressible as **parameter regime shifts**, not structural changes.


## 6.3 Failure modes and desired pathologies

The simulation should permit, not prevent:

- Misdiagnosis of risk (incorrect patterns).
- Overreaction or underreaction via protocols.
- Periods of over-centralization followed by collapse.
- Coexistence of multiple competing risk regimes:
  - Official law vs cartel enforcement vs community codes.

These are **features**, not bugs; they are expressions of the same core cycle under different parameter settings.


# 7. Dependencies and Future Work

This document relies on:

- `D-AGENT-0020` for the canonical agent model.
- `D-AGENT-0021` for Goal and Episodic Memory representations.
- `D-RUNTIME-0001` for timebase and tick semantics.

Future elaborations:

- `D-LAW-0011+` may specify:
  - Concrete protocol data structures.
  - Enforcement mechanics and penalty models.
  - Interactions between formal law and emergent black-market governance.
- Economy, health, suits, and info_security pillars should:
  - Express their own subsystems (rationing, suit maintenance, disease, censorship) **through** this Risk and Protocol Cycle wherever possible.

