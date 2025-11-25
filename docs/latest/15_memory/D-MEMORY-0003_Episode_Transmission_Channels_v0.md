---
title: Episode_Transmission_Channels
doc_id: D-MEMORY-0003
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-MEMORY-0001  # Episode_Management_System_v0
  - D-MEMORY-0002  # Episode_Schema_and_Memory_Behavior_v0
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0023   # Agent_Goal_System_v0
---

# 15_memory · Episode Transmission Channels v0 (D-MEMORY-0003)

## 1. Purpose & Scope

This document defines the **channels** by which episodes move between agents
in Dosadi, and how those channels transform and distort the underlying
episode content.

Building on:

- the core Episode Management System (D-MEMORY-0001),
- the Episode Schema and Memory Behavior specification (D-MEMORY-0002),
- and the Agent Goal System (D-AGENT-0023),

we describe how agents:

- **select** episodes from their memory or archives,
- **transform** them (compress, bias, dramatize, redact),
- and **emit** them via different media:

  - direct conversation,
  - storytelling and performance (including visual media),
  - formal reports and ledgers,
  - written protocols and protocol-like propaganda.

The goal is to provide a **canonical menu** of communicative moves that can be
used by agents of all tiers, and to articulate the cost, reach, and fidelity
properties of each channel.

---

## 2. The Select → Transform → Emit Model

Any transmission of episodic information can be decomposed as:

> **Select → Transform → Emit → Receive**

### 2.1 Select

The sender chooses which episodes (or patterns derived from them) to transmit,
based on:

- current **goals** (D-AGENT-0023),
- relationship with recipients (allies, subordinates, rivals, strangers),
- perceived value and risk of sharing:
  - status gains, trust-building, leverage,
  - or exposure, punishment, loss of monopoly.

Selection is almost never objective; it is a goal-weighted filter over
memory and archive access.

### 2.2 Transform

The selected episodes are compressed and reshaped into **messages**:

- abstraction:
  - dropping many details in favor of key points,
- bias:
  - highlighting certain causes or actors, hiding others,
- framing:
  - assigning blame, credit, justification,
- dramatization:
  - exaggeration for impact (especially in storytelling).

Different channels enforce different transformation styles (e.g. dry and
structured for reports vs vivid and emotional for tavern tales).

### 2.3 Emit & Receive

The transformed message is then **emitted** via a chosen channel and **received**
by one or more agents who:

- encode it as new episodes with `source = archive / rumor / protocol_story / visual_mark`,
- attach their own reliability judgments,
- and possibly retransmit further, adding additional transformations.

Transmission is thus not a simple copy; it is a chain of goal-driven edits and
reinterpretations.

---

## 3. Channel 1: Direct Conversation

### 3.1 Definition

Direct conversation covers:

- one-to-one talks,
- small group briefings,
- whispered warnings, private negotiations, quiet confessions.

It is the basic "low-tech" channel available to almost everyone.

### 3.2 Properties

- **Cost**
  - Low material cost.
  - Time cost can be moderate.
  - Potential social or security risk depending on topic and listeners.

- **Reach**
  - Limited to immediate participants.
  - May be amplified if participants retransmit.

- **Fidelity / Noise**
  - Relatively high fidelity on initial emission; sender can clarify in real
    time.
  - Still subject to memory bias, omission, and framing.
  - On retransmission, drift increases.

- **Visibility**
  - Low formal visibility; hard for authorities to monitor systematically
    unless surveilled.

### 3.3 Typical Use Cases

- Tactical coordination between workers or squad mates.
- Quiet warnings about dangerous places or people.
- Testing reactions to controversial information before going public.
- Simple teaching or apprenticeship (passing down craft episodes verbally).

### 3.4 Goal-Driven Selection Patterns

Agents will favor direct conversation when:

- trust with the listener is reasonably high,
- content is sensitive but important,
- material is too nuanced for wall posters but too minor for formal reports.

This channel is foundational for **local rumor seeding** and relationship-level
trust-building.

---

## 4. Channel 2: Storytelling & Performance (Including Visual Media)

### 4.1 Definition

Storytelling and performance include:

- tavern tales, gossip circles, public speeches,
- formal and informal rituals of recounting incidents,
- **visual performances**:
  - graffiti, murals, banners, posters, pamphlets, sigils.

Episodes are transformed into **narratives and symbols** designed to move
audiences emotionally and socially.

### 4.2 Properties

- **Cost**
  - Low to moderate per performance (time, social risk).
  - Visual media require materials and a physical location, plus risk of
    reprisal if message is subversive.

- **Reach**
  - Medium to high:
    - repeated tellings can reach large fractions of a pod, ward, or guild,
    - visual marks can persist and reach many passersby over time.

- **Fidelity / Noise**
  - High distortion:
    - details are compressed, exaggerated, or omitted for drama,
    - message is tuned for impact rather than accuracy.
  - However, **emotional truth** (who is seen as villain/hero, which places
    feel safe/dangerous) can be very strong.

- **Visibility**
  - Medium to high:
    - performances in public spaces are visible and can be monitored,
    - visual media are obvious and can be censored or co-opted.

### 4.3 Visual Media as Episodic Anchors

Graffiti, posters, pamphlets, and symbols act as **episodic anchors**:

- They trigger recall of episodes for those who know the backstory.
- They create episodic impressions even for those who don’t, e.g.:
  - seeing many skull symbols in a corridor is enough to mark it as "bad".

Examples:

- Hazard markers:
  - skull or crack glyph near a corridor with repeated accidents.
- Territorial markers:
  - guild emblems declaring control of an area.
- Behavioral nudges:
  - posters urging:
    - "Report hoarders",
    - "Join the garrison",
    - "Keep watch on your neighbors".

These function as a hybrid between **rumor** and **protocol**: compressed,
one-way messages that shape expectations and behavior.

### 4.4 Goal-Driven Use

Agents and groups favor storytelling/visual channels when they aim to:

- build or erode reputations (of leaders, guilds, wards),
- spread cautionary tales or heroic myths,
- claim territory symbolically,
- encourage or discourage certain behaviors broadly.

This channel is central to the **cultural layer** of Dosadi, where episodes
become legends, caution signs, and propaganda.

---

## 5. Channel 3: Formal Reports & Ledgers

### 5.1 Definition

Formal reports and ledgers include:

- shift logs,
- incident reports,
- council minutes,
- inspection records,
- medical notes,
- ration and work ledgers.

These constitute the backbone of the **shared archive** (D-MEMORY-0001).

### 5.2 Properties

- **Cost**
  - Moderate to high in time and skill:
    - requires literacy and some training,
    - sometimes politically risky (incriminating records).

- **Reach**
  - Indirect but powerful:
    - typically read by Tier-2 and Tier-3 agents (foremen, auditors,
      stewards),
    - may inform protocol updates and high-level decisions that feed back
      into the world.

- **Fidelity / Noise**
  - Higher fidelity than rumor, but still biased:
    - structured forms enforce minimal fields,
    - authors can selectively omit or frame incidents,
    - pressure to falsify or under-report may exist.

- **Visibility**
  - High visibility to authorities or whoever controls archives.
  - Low visibility to ordinary Tier-1 agents, who mostly see the
    **consequences** (changed protocols, discipline, resource shifts).

### 5.3 Typical Use Cases

- Documenting accidents, near misses, and safety violations.
- Recording ration allocation and shortages.
- Logging patrol routes and security incidents.
- Capturing council deliberations and decisions.

### 5.4 Goal-Driven Selection Patterns

Agents write reports/ledgers when:

- required by protocol or job role,
- trying to protect themselves or their crew with documented evidence,
- preparing to argue for changes (more resources, new protocols).

These records are critical for **Tier-3 pattern analysis**, anomaly detection,
and protocol governance.

---

## 6. Channel 4: Protocols & Protocol-Like Propaganda

### 6.1 Definition

Protocols (D-MEMORY-0001, D-LAW-0011) are:

> distilled, instruction-like expressions of many episodes, encoded as
> "WHEN X, IF Y, THEN do Z" rules.

Protocol-like propaganda uses similar form but with broader social/political
aims:

- "Join the garrison",
- "Report suspicious neighbors",
- "Only buy from Guild X".

These are **broadcast memory**: highly compressed guidance about what to do
and how to align.

### 6.2 Properties

- **Cost**
  - High for initial design:
    - requires data, deliberation, and authority.
  - Low per-use for Tier-1 agents:
    - reading or following a posted procedure is cheap.

- **Reach**
  - High where posted, taught, and enforced.
  - Protocols can become pervasive in workplaces, wards, or entire sectors.

- **Fidelity / Noise**
  - High internal consistency once formalized.
  - Loss of nuance: they reflect a chosen interpretation of episodes, not
    the full variety of experience.

- **Visibility**
  - High:
    - visible wall posters,
    - training manuals,
    - required recitations.
  - Also a primary target for subversion, sabotage, or quiet non-compliance.

### 6.3 Protocols as Compiled Episodes

Protocols are **compiled** from episodes and patterns:

- Safety protocols from long sequences of accidents and near misses.
- Ration protocols from repeated supply crises.
- Surveillance and CI protocols from infiltration and coup episodes.

They encode:

- conclusions: "what usually works" or "what is acceptable",
- and, by omission, what the system prefers to ignore.

Tier-1 agents mostly see protocols as **given**; Tier-2 and Tier-3 see them
as **tools to adjust**.

### 6.4 Protocol-Like Propaganda

Some messages use protocol-like form without being formal SOPs:

- "If you see hoarding, report immediately to patrols."
- "When the alarm sounds, assemble at plaza X."
- "Trust guild Y. Never deal with guild Z."

These blur lines between:

- **law** (expected behavior),
- **propaganda** (desired attitudes),
- and **rumor** (stories backing the slogans).

They can be encoded as:

- special episodes where `source = visual_mark / protocol_story`,
- or as light-weight protocols keyed to broad social contexts.

---

## 7. Comparative Summary of Channels

| Channel                  | Cost       | Reach        | Fidelity / Noise        | Typical Users            |
|--------------------------|-----------:|-------------:|-------------------------|--------------------------|
| Direct conversation      | low        | low          | medium–high fidelity    | all tiers                |
| Storytelling / performance (incl. visual) | low–medium | medium–high | low fidelity, high impact | bards, agitators, leaders |
| Formal reports & ledgers | medium–high| low–medium   | medium–high (structured) | clerks, foremen, auditors |
| Protocols & propaganda   | high (design), low (use) | high | high internal consistency, low nuance | councils, guild boards, regimes |

Each channel is a different **tradeoff** between cost, reach, and accuracy.
Agents and factions choose channels based on goals, resources, and risk
tolerance.

---

## 8. Integration with Goals, Memory, and Protocol Governance

### 8.1 Goals Driving Transmission

For a given agent, transmitting episodes is rarely neutral. Common motivations:

- **Survival & safety**
  - warn kin or pod mates about hazards.
- **Status & reputation**
  - share success episodes, bury embarrassing ones.
- **Control & influence**
  - shape others' perceptions of places, people, or protocols.
- **Institutional roles**
  - fulfill duties as clerk, auditor, steward, commissar.

Goal priorities determine:

- which episodes are selected,
- through which channel they are emitted,
- and which transformations are applied.

### 8.2 Memory Behavior Feedback

Transmission channels feed back into memory behavior (D-MEMORY-0002):

- Hearing or seeing an episode repeatedly through storytelling or posters
  increases its **salience** and **replay probability**.
- Formal reports enhance the **archive** representation, especially for
  Tier-2/3 pattern formation.
- Protocols and propaganda create **shortcuts**:
  - agents may follow them instead of consulting detailed personal or
    archival episodes, until reality forces revision.

### 8.3 Political Bodies as Channel Managers

Proto-political bodies (councils, guild boards, cartel cores) manage channels
as part of their power:

- decide what **must** be reported formally,
- decide which protocols are posted, taught, or quietly ignored,
- produce or suppress visual propaganda,
- encourage or punish certain kinds of storytelling.

This ties directly into forthcoming work on:

- **Proto-Political Body Formation and Protocol Governance** (planned
  D-LAW-0012),
- **Info-Security and Censorship** (08_info_security pillar).

---

## 9. Future Work

Future documents SHOULD:

- define **mechanical interfaces** for each channel:
  - actions like `tell_story`, `file_report`, `paint_symbol`, `post_protocol`,
- specify **noise models** and reliability updates:
  - how beliefs update after hearing conflicting versions of an episode,
- integrate channels into:
  - **rumor propagation models**,
  - **coordination and miscoordination events**,
  - **campaign-level narrative arcs** (e.g. how coup rumors spread).

D-MEMORY-0003 should be treated as the canonical reference for how information
moves between agents in Dosadi, building the bridge between individual
experience, shared memory, and institutional control.
