---
title: Rumor_Networks_and_Informal_Channels
doc_id: D-INFO-0006
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-22
depends_on:
  - D-INFO-0001          # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002          # Espionage_Branch
  - D-INFO-0003          # Information_Flows_and_Report_Credibility
  - D-INFO-0004          # Scholars_and_Clerks_Branch
  - D-INFO-0005          # Record_Types_and_Information_Surfaces
  - D-ECON-0004          # Black_Market_Networks
  - D-AGENT-0101         # Occupations_and_Industrial_Roles
  - D-WORLD-0002         # Ward_Attribute_Schema
---

# 08_info_security · Rumor Networks and Informal Channels (D-INFO-0006)

## 1. Purpose

This document defines how **rumors and informal information** move through
Dosadi. It complements:

- Formal report flows (D-INFO-0003),
- Telemetry and audit streams (D-INFO-0001),
- Espionage actions (D-INFO-0002),
- Black market circuits (D-ECON-0004),
- And the occupational landscape (D-AGENT-0101).

Goals:

- Provide a **graph-level model** for rumor and gossip networks.
- Specify **ward- and location-level parameters** that shape rumor behavior.
- Ground propagation in the existing **8-point rumor logic**:
  - Loyalty as long-term self-interest.
  - Rumor as a calculated move, not random noise.
  - Safe/unsafe spaces for speaking.
  - Social alignment and memory.
- Define hooks for:
  - Scenario authors (“Where does news leak first?”),
  - Simulation code (who learns what, when, with what distortion),
  - Gameplay (“Who do I talk to if I want to know X?”).

This document focuses on **informal channels**: spoken, implied, or quietly
signaled information, rather than written records or official reports.

---

## 2. Relationship to Other Information Flows

### 2.1 Formal vs informal

- **Formal information** (D-INFO-0003, D-INFO-0005):
  - Lives in reports, ledgers, orders, audit logs.
  - Moves via official hierarchies: clerks, scholars, auditors, officers.
  - Is evaluated for **credibility** and tracked as an object in the system.

- **Informal information** (this doc):
  - Lives in conversations, gestures, gossip, and unlogged favors.
  - Moves via **social proximity** and habitual spaces (canteens, bunkhouses,
    markets, corridors, clinics).
  - Is evaluated for **usefulness and risk** by agents, not centrally scored.

Both systems coexist. Often:

- Formal channels are **slower** but have institutional weight.
- Informal channels are **faster**, more distorted, and more targeted
  (agents choose what to pass on, and to whom, based on self-interest).

### 2.2 Hooks into espionage and black markets

- Espionage branch (D-INFO-0002) uses rumor networks as:
  - Raw sensor input (“What are people whispering?”),
  - Delivery mechanisms for disinformation.

- Black market networks (D-ECON-0004) provide:
  - High-capacity **informational circuits** among cartel-linked hubs,
  - Strong incentives to trade rumors for favors, credit, or protection.

Rumor networks are thus the **substrate** for both intelligence and shadow
economy play.

---

## 3. Rumor Graph Model

We model informal information flow as a **dynamic, multiplex graph** over:

- Agents,
- Facilities/locations,
- Circuits/routes.

### 3.1 Node types

At minimum, the rumor graph should recognize:

```yaml
RumorNode:
  id: string
  type: "agent" | "location" | "circuit_hub"
  ward_id: string
  tags:
    - string   # e.g. "canteen", "bunkhouse", "clinic", "checkpoint", "market"
```

- **Agent nodes**:
  - Individual agents with occupations and drives (D-AGENT-0101).
  - Have social ties, faction ties, and habits (which locations they frequent).

- **Location nodes**:
  - Canteens, bunkhouses, markets, clinics, exo-bays, checkpoints, barracks,
    worship spaces, etc.
  - These are **condensers** of rumor—places where many agents cross paths.

- **Circuit hubs**:
  - Nodes representing key junctions in black market circuits
    (D-ECON-0004) or high-traffic logistics corridors (D-ECON-0001).

### 3.2 Edge types

We distinguish several edge categories:

```yaml
RumorEdge:
  from: node_id
  to: node_id
  type: "social" | "co_presence" | "circuit" | "hierarchical"
  weight: float        # 0–1, strength/frequency of contact
  trust_bias: float    # -1 to +1, tendency to trust/disbelieve info from this edge
```

- **Social edges**: friendships, family ties, co-workers, crew membership.
- **Co-presence edges**: repeated shared time in specific locations (same bunk,
  same canteen line, same clinic waiting area).
- **Circuit edges**: information channels along cartel routes or long-corridor
  gossip (“news from Ward 12”).
- **Hierarchical edges**: superiors/subordinates inside guilds, branches,
  or cartels, where information may move “up” or “down”.

In practice, the simulation can store a compressed representation, but the
conceptual model treats rumor propagation as **walks over this heterogeneous graph**.

---

## 4. Ward-Level Rumor Attributes

Each ward `w` should have high-level parameters governing rumor behavior:

```yaml
rumor_density: float        # 0–1, how much informal talk circulates
rumor_volatility: float     # 0–1, how fast rumors mutate
rumor_fear_index: float     # 0–1, how dangerous it feels to speak openly
rumor_memory_depth: float   # 0–1, how long wards "remember" old stories
gossip_hub_intensity: float # 0–1, strength of a few dominant rumor hubs
```

Interpretation:

- **rumor_density** – average volume of gossip per unit time.
  - Higher in dense habitation, markets, canteens, bunkhouses.

- **rumor_volatility** – how much a rumor is likely to distort per hop.
  - High volatility: fast-changing narratives, wild exaggeration.
  - Low volatility: more stable stories, easier to track.

- **rumor_fear_index** – captures *perceived* risk of speaking:
  - High where audits, informants, and reprisals are common.
  - Pushes rumor into **safer niches** (trusted edges, cartel cells).

- **rumor_memory_depth** – how long old events remain salient in talk:
  - High: old betrayals and famines still shape choices.
  - Low: wards “move on” quickly, letting new narratives dominate.

- **gossip_hub_intensity** – whether rumor is diffuse, or concentrated:
  - High: a few locations/people act as powerful amplifiers.
  - Low: more evenly distributed, slower but harder to shut down.

These can be calculated from other ward features (habitation density, black
market intensity, audit intensity, etc.) or set explicitly in scenarios.

---

## 5. Channel Archetypes

Informal information moves along characteristic **channel types**. These are
useful for scenario thinking and for differentiating edges in the graph.

### 5.1 Civic channels

- **Canteens & markets**:
  - Queues and shared tables generate dense cross-faction mixing.
  - Canteen workers and vendors are natural **gossip collectors**.

- **Bunkhouses & shared habitation**:
  - Bed allocation, snoring, late returns, and absences all produce talk.
  - Stewards see who comes and goes and can seed or damp rumors.

- **Clinics & street medics**:
  - Wounds, sickness, and missing persons produce worried whispers.
  - Orderlies and medics connect violence to specific factions and events.

### 5.2 Guild channels

- Workshop floors, tech bays, maintenance crews.
- Foremen, exo-techs, vat techs, and suit stitchers share:
  - “What really failed where,”
  - Who is skimming parts,
  - Which wards are under-supplied.

Guild rumor tends to be **technically grounded but politically slanted**.

### 5.3 Cartel channels

- Night markets, safehouses, back rooms of taverns.
- Cadence smugglers, clandestine modders, fixers, and brokers.
- Rumors here are often:
  - More **intentional** (weaponized information),
  - Tied to **credit and leverage** (“we know what you did last shipment”).

### 5.4 Military and audit channels

- Barracks gossip, checkpoint chatter, off-duty drinking spots.
- Audit scribes and ration clerks comparing discrepancies.
- Rumors here focus on:
  - Promotions/demotions,
  - Witch-hunts and upcoming raids,
  - “Which ward is being scapegoated next.”

### 5.5 Noble / high-tier channels

- Restricted salons, sealed ward social events.
- Trusted retainers, private physicians, elite suit artisans.
- These channels are **thin but high-impact**: a small rumor here can trigger
  large-scale policy shifts if it convinces a duke or key advisor.

---

## 6. Propagation Logic (Rumor as Calculated Move)

Rumor propagation should reflect the earlier **8-point logic** where:

- Loyalty is long-term self-interest,
- Rumor is a move in a game, not noise,
- Spaces have alignment and memory,
- There are safer and riskier rumor zones.

### 6.1 Local decision rule (conceptual)

When an agent `A` hears a rumor `R`, they decide whether to share it with
neighbor `B` over edge `E` based on:

```text
share_probability(A, B, R, E) ≈
    motive_gain(A, R)
  * edge_safety(A, B, E)
  * alignment_factor(A, B, R)
  * suppression_factor(A, R)   # < 1 if A wants rumor to die
```

Where:

- **motive_gain(A, R)** – how much A expects to gain (or avoid loss) by
  spreading or withholding `R`:
  - Gain for undercutting rivals, protecting allies,
  - Expected rewards from factions (militia, cartel, guild, bishop_guild).

- **edge_safety(A, B, E)** – risk that speaking will trigger audit, violence,
  or betrayal:
  - Lower on edges crossing high `rumor_fear_index` wards,
  - Higher in “safe” spaces where alignment and memory favor A.

- **alignment_factor(A, B, R)** – whether sharing strengthens useful ties:
  - Positive when A and B share faction alignment or common enemies.
  - Negative when B is aligned with targets of the rumor.

- **suppression_factor(A, R)** – used when A chooses to **sit on** a rumor,
  trying to keep it scarce as private leverage.

### 6.2 Safe vs unsafe zones

Certain locations should be tagged as **unsafe rumor zones**:

- Checkpoints under intense audit,
- Offices of feared officials,
- Spaces with high informant density.

Others as **safe-ish rumor zones**:

- Noise-heavy canteens,
- Crowded bunkhouses,
- Shared washrooms,
- Certain neutral taverns or shrines.

Implementation:

- Locations and edges can have a `rumor_safety` tag:
  - `"safe" | "neutral" | "unsafe"`
- `edge_safety` includes this factor plus ward-level `rumor_fear_index`.

### 6.3 Rumor “weight” and spread

Each rumor instance can track:

```yaml
Rumor:
  id: string
  payload_type: "event" | "threat" | "opportunity" | "character" | "policy"
  origin_ward: string
  current_confidence: float   # 0–1, how believable receivers find it
  sharpness: float            # 0–1, how specific vs vague
  spread_score: float         # used to decide if simulation keeps tracking it
```

Rules of thumb:

- Threats and opportunities spread fastest.
- High sharpness spreads well in tight, high-trust networks; in looser ones,
  it may degrade into lower-sharpness variants (“something bad happened”).

---

## 7. Reliability, Distortion, and Echo

Rumors are not just on/off; they **evolve**.

### 7.1 Distortion per hop

On each hop, rumor properties update as:

```text
R.sharpness  -= k1 * rumor_volatility(w)
R.confidence += k2 * local_confirmation - k3 * contradiction
```

Where:

- `rumor_volatility(w)` from the ward,
- `local_confirmation` is high if:
  - The listener observes matching events,
  - Multiple independent channels report similar content.

High volatility wards produce **myths** quickly; low volatility wards maintain
sharper, more actionable detail.

### 7.2 Echo and reinforcement

In gossip hubs (high `gossip_hub_intensity`):

- Rumors that repeatedly pass through the same nodes:
  - Gain *social momentum* (more people have “heard it”),
  - May become **background truth**, even if wrong.

The sim can treat this as an increase in `spread_score` and/or `confidence`
once a rumor crosses a threshold of unique listeners in a hub.

### 7.3 Rumor death

Rumors decay when:

- No one with incentive to share remains,
- Strong contradictory events or formal announcements override them,
- High `rumor_fear_index` plus punitive incidents make talk too dangerous.

The implementation can retire rumors when `spread_score` and `confidence`
fall below thresholds.

---

## 8. Hooks into Gameplay and Scenarios

This document is mainly for internal logic, but it should support clear uses.

### 8.1 Where does the player learn things?

Scenario authors can specify **rumor access points**:

- Certain NPCs (agents with many edges and low fear),
- Certain locations (canteens, markets, bunkhouses, shrines),
- Certain cartel/guild contacts.

The sim can answer queries like:

- “Give me three rumors available in Ward 12’s main canteen tonight.”
- “What do guild foremen in FABRICATION think happened in Ward 03?”

### 8.2 Misinformation and planted stories

Espionage branch and cartels can **inject synthetic rumors**:

- Create a Rumor object with desired payload,
- Seed it at selected nodes/locations,
- Let normal propagation rules operate.

Success depends on:

- Alignment and incentives of the seed audience,
- Rumor’s plausibility relative to local conditions,
- Counter-moves (formal announcements, counter-rumors).

### 8.3 Silencing and chilling effects

Branches or factions can attempt to **suppress** rumors by:

- Targeted violence against talkative nodes (vendors, stewards, medics),
- Surprise audits or raids in gossip hubs,
- Public punishments for “spreading lies”.

Mechanically:

- Raise `rumor_fear_index`,
- Reduce `rumor_density`,
- Break key edges in the rumor graph.

This reshapes the **texture** of play: information becomes scarcer, but
those remaining with good channels are more valuable.

---

## 9. Implementation Sketch (Non-Normative)

A minimal implementation loop for rumor networks could be:

1. Build/maintain a **rumor graph**:
   - Nodes: agents + key locations.
   - Edges: social, co-presence, circuit, hierarchy.
2. Maintain ward-level rumor parameters
   (`density`, `volatility`, `fear_index`, `memory_depth`, `gossip_hub_intensity`).

3. For each tick / time slice:
   - For each active rumor `R`:
     - For each holder `A`:
       - Consider neighbors `B` within a limited edge radius.
       - Compute `share_probability(A, B, R, E)` and propagate stochastically.
       - Update `R.sharpness`, `R.confidence`, `R.spread_score`.
   - Apply:
     - Decay to low-activity rumors,
     - Boosts in high-traffic hubs.

4. Allow higher-level systems to:
   - Seed new rumors (espionage, cartel, regime).
   - Query the rumor state (what do people believe here?).

5. Use rumor outputs to:
   - Modify agent decisions (fear, outrage, opportunity seeking),
   - Inform MIL responses (pre-emptive crackdowns where rumors of revolt spike),
   - Drive narrative prompts and branching.

The aim is **expressive, not prescriptive**: designers can simplify this
down to tags and tables, or implement a full rumor graph, using the same
conceptual backbone.

---

## 10. Future Extensions

Likely follow-ups and refinements:

- `D-INFO-0101_Rumor_Templates_and_Motifs`  
  - Common rumor archetypes (missing water, cursed suit lines,
    betrayal stories, martyrdoms) and how they bias agent responses.

- Deeper integration with D-AGENT-0007 (Rumor and Gossip Dynamics v0)  
  - More detailed drive-level rules for when agents weaponize rumor vs
    stay silent.

- Scenario-specific rumor atlases  
  - Pre-baked rumor webs for important days (e.g. Sting Wave scenarios),
    specifying which wards and hubs are already “hot” with certain stories.
