---
title: Belief_System_and_Tiered_Memory
doc_id: D-MEMORY-0004
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-MEMORY-0001  # Episode_Management_System_v0
  - D-MEMORY-0002  # Episode_Schema_and_Memory_Behavior_v0
  - D-MEMORY-0003  # Episode_Transmission_Channels_v0
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0006   # Agent_Attributes_and_Skills_v0
  - D-AGENT-0023   # Agent_Goal_System_v0
---

# 15_memory · Belief System & Tiered Memory v0 (D-MEMORY-0004)

## 1. Purpose & Scope

This document defines **beliefs** as the long-term, compressed products of episodic
memory in Dosadi, and specifies how belief capacity and precision vary by:

- memory layer (short-term episodes, daily episodes, long-term beliefs),
- agent attributes (INT, WIL, CHA, END, DEX, STR),
- and agent tier (1, 2, 3).

D-MEMORY-0001–0003 establish:

- episodes as the atomic memory unit,
- how episodes are encoded, decayed, and compressed into patterns,
- and how episodes move through rumor, reports, and protocols.

D-MEMORY-0004 focuses on **what persists** inside agents over time and how that
persistence shapes behavior.

Specifically, it:

1. Defines three memory layers: **short-term episodic**, **daily episodic**, and
   **long-term beliefs**.
2. Specifies how episodes move between layers under capacity and salience constraints.
3. Introduces concrete **belief types** (places, people, factions, protocols,
   expectations) and how tiers differ in access and resolution.
4. Connects agent attributes and tiers to belief capacity and precision.

Numerical values and data structures are left for implementation docs (e.g.
D-MEMORY-01xx, D-AGENT-01xx, runtime hooks).

---

## 2. Three Memory Layers

We distinguish three conceptual layers inside each agent:

1. **Short-term episodic buffer** – high churn, seconds to minutes.
2. **Daily episodic buffer** – working set for a wake/sleep cycle.
3. **Long-term beliefs** – compressed patterns that persist over days to years.

All three layers influence action selection, but **only beliefs** survive across
many cycles without explicit external support (journals, archives, protocols).

### 2.1 Short-Term Episodic Buffer

- Holds **raw episodes** for a brief window (on the order of 5–15 minutes of
  active time).
- Contains:
  - recent sensory impressions,
  - micro-actions (“I just shifted my stance,” “someone bumped me”),
  - immediate body signals:
    - “a little hungry,” “very thirsty,” “in pain,” “too hot/cold.”
- Undergoes frequent **purges**:
  - low-salience episodes are discarded,
  - some episodes are **promoted** into the daily buffer.

**Promotion criteria (conceptual):**

- Strong linkage to active goals (goal relevance).
- Strong emotional tone (fear, anger, relief, joy).
- Novelty or violation of expectations.
- Repetition (same pattern seen multiple times in a short window).
- Profession/role flags (e.g. note-keepers, auditors, scouts are more likely to
  treat episodes as “record-worthy”).

Short-term buffer size and purge cadence are **per agent** and may depend on:

- base constants per tier,
- modifiers from attributes (see §4),
- work/rest status and chemical state (stress, drugs, trauma).

### 2.2 Daily Episodic Buffer

- Holds episodes accrued during a **waking period** (a day/night shift).
- Serves as the staging area for **belief updates**.
- Is **processed during the sleep/downtime cycle**:
  - episodes are sorted by relevance and emotional weight,
  - some are integrated into existing beliefs,
  - some trigger creation of new beliefs,
  - others are discarded.

To keep memory costly:

- The daily buffer has a **finite capacity**.
- If the buffer overflows **before** sleep integration:
  - lowest-priority episodes (low relevance/low emotion) are dropped,
  - representing overstimulation and limited retention.

This ensures that:

- chaotic or traumatic days **squeeze out** many mundane details,
- but high-salience episodes force their way into the nightly consolidation.

### 2.3 Long-Term Beliefs

Long-term beliefs are **compressed patterns** over many episodes.

A belief is “what the agent thinks is true or likely” about:

- a place,
- a person,
- a faction,
- a protocol,
- or an expectation about future outcomes.

Beliefs are stored as small, queryable records such as:

- belief target (e.g. facility_id, agent_id, faction_id, protocol_id),
- belief aspect (safety, trustworthiness, fairness, brutality, access, trend),
- current estimate/value,
- confidence,
- last_updated_tick,
- primary sources (self, close ally, rumor, protocol, archive).

Beliefs are updated primarily during **sleep/downtime**, when the daily buffer is
processed:

- consistent episodes **reinforce** existing beliefs (higher confidence),
- contradictory episodes **weaken or flip** beliefs,
- recurrent anomalies may trigger formation of new beliefs (“this corridor is
  dangerous,” “this steward plays favorites”).

Individual episodes rarely survive intact in long-term memory; their **effects**
are preserved through beliefs.

---

## 3. Belief Types

Beliefs are organized by **target** and **aspect**. This document defines the
core families for v0; implementations may extend them.

### 3.1 Place / Facility Beliefs

Target: specific locations or facilities (pods, corridors, bays, depots, wards).

Aspects (examples):

- perceived_safety (0–1)
- perceived_access (0–1)
- resource_quality (e.g. food quality, water reliability)
- enforcement_level (how likely rules are enforced here)
- crowding / stress level
- “home” / “territory” feeling

These beliefs drive:

- movement choices,
- where agents seek shelter, food, and work,
- where they choose to break rules.

### 3.2 Person Beliefs

Target: specific agents (by id) or persistent roles (“pod steward”, “bay chief”).

Aspects (examples):

- trustworthiness / reliability
- fairness vs favoritism
- bribability / corruption
- threat / danger
- alignment (ally, neutral, rival)
- competence
- influence (how much they can affect outcomes)

Not all agents maintain detailed person beliefs; see tier limits in §5.

### 3.3 Faction Beliefs

Target: groups (pods, guilds, cartels, militias, councils, cults).

Aspects (examples):

- “protects its own” vs “uses its own”
- brutality / mercy
- tendency toward retaliation
- ability to make good on promises (capacity + will)
- legitimacy (“they rule because they must / because they can / because they cheat”)

These beliefs influence:

- willingness to seek help,
- propensities to join or desert factions,
- reactions to propaganda and protocols branded by that faction.

### 3.4 Protocol / Rule Beliefs

Target: named protocols, rules, norms, or informal “ways things are done.”

Aspects (examples):

- enforcement_probability (how likely breach → sanction)
- severity_of_consequence
- fairness (perceived justice vs arbitrary cruelty)
- theater_vs_real (is it a “show rule” or actually binding?)

Agents rarely hold the **text** of the rule; they hold beliefs like:

- “You really do get punished for running in that corridor.”
- “The mask rule is enforced only if officers are watching.”

### 3.5 Expectation / Trend Beliefs

Target: dynamic patterns and “if X then Y” relationships.

Examples:

- “If rations are cut, fights in the queue spike in 2–3 days.”
- “If patrols stop visiting, cartels reclaim the corridor.”
- “Pod-4 has been getting more tense each week.”

These are the signature **Tier-3** beliefs but can appear in simplified form in
Tier-2 agents (local trends).

---

## 4. Attribute Influence on Memory & Beliefs

Attributes shape both **capacity** (how much can be stored) and **precision**
(how detailed each memory/belief can be), as well as **which episodes get
promoted**.

### 4.1 Willpower (WIL)

- Increases **daily buffer capacity** (can carry more episodes into sleep).
- Reduces “overflow loss” during overstimulating days:
  - high-WIL agents lose fewer episodes under overload.
- Slightly improves resistance to traumatic overwrite:
  - traumatic episodes still matter, but do not erase everything else.

### 4.2 Intellect (INT)

- Increases **belief catalog capacity**:
  - more distinct beliefs can be maintained before old ones are pruned.
- Improves **structural compression**:
  - higher-INT agents extract more useful structure (cause/effect, trends)
    from the same episodes.
- Enables more complex expectation/trend beliefs:
  - “if X and Y then Z,” not just “if X then Z.”

### 4.3 Charisma (CHA)

- Enhances **social episode richness**:
  - episodes involving conversations, negotiations, and performances
    carry more detail (who said what, who flinched, who hesitated).
- Increases **precision of person/faction beliefs**:
  - more nuanced sense of trust, motive, and leverage.

### 4.4 Constitution / Endurance (END)

- Improves **body-signal encoding**:
  - agents better distinguish degrees of fatigue, pain, and discomfort.
- Under stress or chemical influence (drugs, fear, heat):
  - higher END keeps episodes usable rather than blurred noise.

### 4.5 Agility (DEX) & Strength (STR)

- Mainly affect **action-linked episodes**:
  - high-DEX/STR agents encode more detail about physical maneuvers, exertion,
    and environmental feedback during action.
- Over time, this can yield more refined beliefs about:
  - dangerous maneuvers,
  - safe vs unsafe workflows,
  - physical constraints of places and tools.

---

## 5. Tiered Belief Capacity & Focus

Belief systems are **tiered** to keep simulation scale manageable and to reflect
different cognitive and institutional roles.

### 5.1 Tier-1 Agents (Grunts / Basic Colonists)

Primary focus:

- survive,
- secure immediate needs,
- avoid obvious danger.

Belief scope:

- **Places**: a small local set (pods, corridors, nearby depots).
- **Factions**: coarse views (“Council / pod / garrison / ‘they’”).
- **People**:
  - a **limited handful** of named individuals:
    - kin and close companions,
    - direct supervisors or especially salient figures (the cruel guard,
      the generous cook).
  - Everyone else is lumped into roles (“some guard”, “a clerk”).

Normative rule:

- Tier-1 agents **may** have person beliefs, but:
  - the catalog is small,
  - resolution is coarse (good/bad, safe/dangerous, fair/unfair).

Belief capacity (conceptual ranges):

- 10–40 place/facility beliefs.
- 5–20 faction beliefs.
- 3–8 person beliefs (named).
- Few or no explicit protocol/expectation beliefs beyond “will I get hit?”

### 5.2 Tier-2 Agents (Supervisors / Stewards / Squad Leads)

Primary focus:

- keep a section working,
- manage people and flows,
- protect their own status.

Belief scope:

- **Places**:
  - more extensive local map:
    - multiple bays, corridors, pods, chokepoints.
  - includes safety, throughput, and “political temperature.”
- **People**:
  - roster of subordinates and peers:
    - reliability, initiative, loyalty, trouble potential.
  - some higher-ups and key outsiders.
- **Factions**:
  - more nuanced faction map:
    - council vs ward admin vs guild-ish clusters vs garrison.
- **Protocols**:
  - practical mental list of:
    - “real rules,” “flexible rules,” “theater rules.”
- **Expectations**:
  - short-horizon trends in their domain:
    - “injuries rising on night shift,”
    - “queue tension up after recent cut.”

Belief capacity (conceptual ranges):

- 30–100 place/facility beliefs.
- 10–40 faction beliefs.
- 20–80 person beliefs.
- 10–40 protocol beliefs (coarse).
- A handful of local expectation/trend beliefs.

### 5.3 Tier-3 Agents (Councilors / Guild Heads / Dukes, Later)

Primary focus:

- stability and control of domains,
- managing risk at scale,
- long-horizon outcomes.

Belief scope:

- **Aggregated places**:
  - wards, sectors, production spines, movement networks.
- **Key people**:
  - stewards, guild faces, militia officers, clerks who can alter records.
- **Factions**:
  - city-scale power map:
    - guilds, cartels, militias, cults, civic offices.
- **Protocols**:
  - entire stacks of rules as tools and weapons.
- **Expectations & dynamics**:
  - trends over months/years,
  - counterfactuals (“if we do X, Y happens later”).

Belief capacity (conceptual ranges):

- 100+ place/ward/network beliefs (more abstract).
- 50+ faction beliefs, often aggregated (“all guilds in sector E”).
- 50–200 person beliefs (weighted toward pivotal roles).
- 50+ protocol beliefs (including relationships between protocols).
- Dozens of explicit expectation/trend beliefs (with confidence scores).

Tier-3 agents also rely heavily on **external supports**:

- archives, dashboards, summaries, briefings;
- their personal belief system sits on top of institutional memory.

---

## 6. From Episodes to Beliefs (Operational Summary)

At a high level, for each agent:

1. **Experience**:
   - episodes are generated as they pursue goals and perceive the world.
2. **Short-term buffer**:
   - episodes live for minutes, then are purged;
   - some are promoted to the daily buffer based on goal linkage/emotion/novelty.
3. **Daily buffer**:
   - collects promoted episodes during a wake cycle;
   - overflow drops low-priority episodes.
4. **Sleep/downtime integration**:
   - for each episode in the daily buffer:
     - find relevant belief targets (place/person/faction/protocol),
     - reinforce, weaken, or create beliefs,
     - adjust confidence and, optionally, urgency.
   - after processing, the daily buffer is cleared.
5. **Action selection**:
   - when deciding what to do:
     - agents consult their belief store alongside immediate episodes and goals,
     - lower tiers lean on place/faction beliefs,
     - higher tiers draw on richer person/protocol/expectation beliefs.

---

## 7. Implications & Hooks

- **Misbeliefs and stale beliefs** are normal:
  - decay, bad rumors, and limited access guarantee that agents often act on
    incorrect or outdated beliefs.
- **Tier interaction**:
  - Tier-1 agents preserve important episodes by reporting them upward to Tier-2,
    whose larger belief catalogs and logs can retain more detail.
  - Tier-3 agents act partly on **processed summaries** of those lower-tier
    experiences (reports, protocols, dashboards).
- **Trauma & overload**:
  - extreme episodes can bypass normal filters and force belief updates
    (“they really will kill you for that”),
  - but chronic overload may shrink effective buffers (especially for traumatized
    agents), leading to rigid, high-pain belief patterns dominating memory.

Future docs SHOULD:

- define concrete data structures for belief types (e.g. `AgentBelief`,
  `FacilityBelief`, `FactionBelief`, `ProtocolBelief`),
- specify quantitative rules for capacity, promotion thresholds, and decay,
- and wire belief queries into the agent decision rule used by the runtime.
