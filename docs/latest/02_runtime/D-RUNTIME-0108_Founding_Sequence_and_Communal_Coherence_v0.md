---
title: Founding_Sequence_and_Communal_Coherence
doc_id: D-RUNTIME-0108
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-24
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-RUNTIME-0103  # Scenario_Framing_and_Win_Loss_Conditions
  - D-RUNTIME-0105  # AI_Policy_Profiles
  - D-RUNTIME-0106  # Office_Precedent_and_Institutional_Memory
  - D-RUNTIME-0107  # Campaign_Phases_and_Golden_Age_Baseline
  - D-WORLD-0001    # World_Index / Environment_Primers
  - D-AGENT-0001    # Agent_Core_Schema_v0
  - D-AGENT-0005    # Perception_and_Memory_v0
  - D-AGENT-0006    # Agent_Attributes_and_Skills_v0
---

# 02_runtime · Founding Sequence & Communal Coherence v0 (D-RUNTIME-0108)

## 1. Purpose & Scope

This document specifies the **founding sequence** of the Dosadi settlement
from **tick 0** and defines the **Communal Coherence** drive and the
**Politic** action that agents use to create and modify social structure.

The goals are to:

- describe what is actually **given** at tick 0,
- define how agents **self-organize** from bunk clusters into pods, zones,
  and early cores,
- ensure that all early structures (councils, sectors, sealed cores) emerge
  as **natural responses** to world state and agent traits, not as arbitrary
  top-down archetypes.

This document is primarily concerned with **Phase 0 (Golden Age Baseline)** as
defined in D-RUNTIME-0107: abundance, low structural corruption, low unrest.

---

## 2. Initial Conditions at Tick 0

### 2.1 World

At founding, the simulation assumes:

- A single **Well complex** (or tightly grouped cluster) located at known
  coordinates, capable of supplying ample water for the initial population
  plus expected near-term growth.
- Surrounding **terrain** (caverns, tunnels, voids, hazard zones) defined by
  WORLD documents, but **no pre-defined wards or districts**.
- A hostile **atmospheric envelope** (hyper-dry, thermally harsh) with no
  pre-built sealed cores; any sealed spaces are small, temporary, and tied to
  landing/arrival infrastructure.

### 2.2 Population

- A population of **N colonists** (e.g. 20k / 50k / 100k), the exact number
  scenario-specific but **large enough** to require significant coordination.
- Colonists wake from **drug-induced sleep** in functional, pragmatically
  furnished bunks, with:
  - shared sleeping bays,
  - basic wash and sanitation,
  - minimal comfort.
- **Industrial goods** (prefab structures, life-support units, tools, suits,
  seed stock, etc.) are palleted or containerized and stored **near bunk
  clusters** and the Well.

Each agent at tick 0 is defined **only** by:

- physical location,
- attributes (STR, AGI, CON, INT, WIL, CHA),
- initial skill bundle (pre-mission training),
- personality facets (ambition, honesty, communal, bravery, paranoia,
  dogmatism, cruelty, patience, curiosity),
- drives (including Communal Coherence, see §3).

There are **no titles** (no dukes, bishops, or cartel bosses), no pre-existing
guilds, and no fixed wards or social classes.

### 2.3 Mission Payload & Charter

Scenarios MAY specify a **mission charter**, representing a loose plan drafted
before arrival. This can include:

- recommended industrial priorities,
- proposed governance patterns (e.g. a Settlement Council),
- lists of pre-identified experts.

However, the **actual adoption** of these patterns is always mediated by
agent behavior and the Communal Coherence / Politic dynamics defined here.
No charter is automatically binding beyond what agents choose to recognize.

---

## 3. Communal Coherence (Drive)

### 3.1 Definition

**Communal Coherence** is a drive that reflects an agent's tendency to:

- seek belonging in a functioning group,
- invest energy in **shared rules and roles**,
- and align behavior with perceived group survival and prosperity.

At low intensity, agents simply:

- prefer not to be isolated,
- follow obvious norms (queues, taking turns) when convenient.

At higher intensity, agents will:

- attend meetings,
- endorse or resist proposed rules,
- actively work to **repair group fragmentation**,
- or, in some cases, **restructure** groups they see as dysfunctional.

### 3.2 Determinants

The baseline strength of Communal Coherence SHOULD be computed from:

- attributes:
  - positive influence from CHA, WIL,
  - weaker positive influence from INT (understanding group benefits);
- personality:
  - increased by communal, patience, curiosity,
  - reduced by extreme cruelty (antisocial) or extreme paranoia (chronic mistrust);
- history:
  - increased when group membership has clearly **improved survival**,
  - decreased when groups have **betrayed or endangered** the agent.

Implementation MAY use a normalized `[0.0, 1.0]` scalar:

```yaml
communal_coherence: 0.0-1.0
```

### 3.3 Interaction with Other Drives

Communal Coherence competes and cooperates with other drives:

- with **Survive**:
  - groups offer protection and resource stability; strong Communal Coherence
    encourages joining effective groups rather than lone survivalism;
- with **Accumulate**:
  - strong Accumulate but low Communal Coherence encourages hoarding; higher
    Communal Coherence encourages cooperative investment;
- with **Curiosity**:
  - curiosity can drive exploration; Communal Coherence channels this into
    shared surveying and mapping efforts;
- with **Ambition** (personality):
  - high ambition + high Communal Coherence = drive to build,
    lead, and improve institutions;
  - high ambition + low Communal Coherence = drive to capture or subvert
    institutions for narrow gain (more relevant in later phases).

---

## 4. Politic (Action)

### 4.1 Definition

**Politic** is an action family that instantiates the Communal Coherence drive
in a high-agency form. When an agent performs Politic, they are trying to:

- create a group,
- modify group attributes (rules, roles, responsibilities),
- or broadcast and align others around a group change
  ("Did you hear about the new council rules?").

Politic is not restricted to elites; any agent with sufficient inclination,
skill, and opportunity MAY attempt it, though success varies.

### 4.2 Triggers

Politic actions are more likely to be triggered when:

- group size exceeds a comfort threshold (coordination problems emerge),
- repeated friction is observed (resource disputes, unsafe behavior),
- the environment is risky **but not immediately lethal**
  (there is time to meet and talk),
- the agent's Communal Coherence is high and they perceive
  that better rules would improve survival or comfort.

### 4.3 Core Mechanics

A Politic action comprises:

1. **Initiation**  
   - the agent calls a meeting (formally or informally),
   - identifies relevant participants (crew, bunkmates, neighboring pods),
   - frames a problem and/or proposal.

2. **Deliberation**  
   - participants weigh the proposal against:
     - personal drives (Survive, Accumulate, Affiliation),
     - personality (dogmatism, paranoia, communal),
     - perceived fairness and competency of the proposer.
   - skilled agents use Diplomacy, Oratory, Mediation, and Administration
     to refine proposals and build consensus.

3. **Resolution**  
   - outcome types:
     - **Adopted**: group attributes (rules/roles) are updated;
     - **Modified**: a negotiated variant is accepted;
     - **Rejected**: status quo is maintained;
     - **Fragmented**: group splits; a subset adopts the new rules,
       another subset refuses.

4. **Propagation**  
   - news of decisions spreads via:
     - direct broadcast by participants,
     - bunk/gossip networks,
     - later: clerical recording and official notices.
   - agents who were not present may adjust their behavior once aware
     of the new rules and the consequences of disobedience.

### 4.4 Success Factors

The success of a Politic action SHOULD depend on:

- proposer stats:
  - CHA, INT, WIL multipliers,
  - skill levels in Diplomacy, Oratory, Administration, Mediation;
- audience traits:
  - high communal & patience facilitate consensus,
  - high dogmatism resists change,
  - high paranoia requires stronger threat framing or evidence;
- context:
  - recent survival threats (accidents, shortages) make groups more
    receptive to coordination,
  - previous proposal history (agents gain or lose credibility over time).

Failed Politic actions may reduce the proposer's **local status** and
Communal Coherence, while successful ones increase status and strengthen
group cohesion.

---

## 5. Founding Sequence: From Bunk Clusters to Cores

The founding sequence describes a **typical Phase 0 evolution** from
"everyone wakes up" to the formation of early sealed cores. Timing and exact
patterns remain scenario-dependent, but the logic SHOULD be consistent.

### 5.1 Phase A: Wakeup & Bunk Clusters

- Agents wake from sleep in **bunk bays** located near the Well and stored
  goods.
- Immediate actions are dominated by **Survive**:
  - suit checks, triage, air and water checks,
  - orientation to facility layout.
- Social structure:
  - bunkmates, bay neighbors, and ad-hoc work details form **micro-clusters**
    of ~20–200 agents.
- Politic:
  - minimal, mostly implicit norms (line up here, help injured, listen to the
    loudest competent voice).

Implementation hooks:

- identify bunk clusters as initial **Group** entities,
- assign micro-cluster IDs based on physical proximity,
- set early group attributes: shared sleeping, access to local stockpiles.

### 5.2 Phase B: Survival Stabilization & Proto-Specialization

Once basic survival is stabilized in a cluster:

- agents with relevant skills and attributes **naturally gravitate** to tasks:
  - medics to care, suit techs to maintenance, surveyors to exploration,
  - admins to tracking inventory and assignments.
- Micro-clusters attach roles informally:
  - "you handle medical stuff,"
  - "you keep the barrel counts,"
  - "you organize the survey lists."

Politic actions at this stage are:

- micro-scale: naming responsibilities, agreeing on rotations,
  setting simple "house rules" for the bunk.

Implementation hooks:

- Group objects gain initial **role slots** (medic, quartermaster, foreman),
- assign role occupants by scoring agents on relevant skills + personality,
- encode early rules as simple boolean or threshold constraints
  (e.g. "medic approves dangerous work" flag).

### 5.3 Phase C: Pod-Level Politic & Local Rules

As clusters grow or merge and share workflows:

- coordination friction appears (resource queues, noise, hazards),
- agents with higher Communal Coherence and relevant skills call **meetings**
  (Politic),
- these meetings produce **local charters**, such as:
  - quiet hours,
  - work/meal schedules,
  - safety protocols,
  - dispute resolution norms.

Politics is still **local and pragmatic**; language of "councils" may not
appear yet, but these are the **ancestors of pod councils**.

Implementation hooks:

- allow Groups to promote to **Pods** once they exceed size and complexity
  thresholds,
- attach a simple charter structure (list of rules, roles, and enforcement
  patterns),
- track charter effectiveness by reductions in local incidents.

### 5.4 Phase D: Cross-Pod Councils & Task Forces

As Pods coordinate resource flows and share key infrastructure:

- problems appear that span multiple pods:
  - water routing, barrel traffic, shared corridors, shared med resources,
  - allocation of scarce specialized labor (HVAC, exo-bays).
- Politic escalates to **inter-pod councils**:
  - representatives (formal or informal) from several pods meet to negotiate
    shared practices.
- These councils identify **short- and long-term needs**:
  - immediate: safety, output targets, basic redundancy;
  - mid-term: stable food supply, corridor hardening, hazard mapping.
- Councils begin creating **task forces**:
  - "water team", "med team", "survey & mapping", "construction cell".

Agents choose task forces based on:

- perceived **self-benefit** (survival odds and comfort),
- skill match and interest,
- social ties and trust in the team leads.

Disobedience to early council mandates carries survival risk:

- exclusion from resources,
- denial of access to safer facilities,
- social isolation.

Implementation hooks:

- introduce **Council** entities linking multiple Pods,
- define **TaskForce** structures as temporary or semi-permanent Groups
  with clear objectives,
- tie access to shared resources and safer infrastructure to compliance
  with council charters.

### 5.5 Phase E: Assets → Zones/Sectors

Survey and work over time reveal **key assets**:

- Wellhead and pumping nodes,
- prime caverns for agriculture,
- safe storage for stockpiles,
- important junction corridors,
- high-value technical bays (HVAC hubs, exo-bays).

Pods and Task Forces naturally anchor around these assets. Politic at the
Council level starts to address:

- how responsibility for each asset is divided,
- who has authority to operate, maintain, or shut down parts of the system,
- how incidents and hazards near assets are managed.

This leads to the emergence of **Zones/Sectors**, defined by:

- shared dependencies on key assets,
- common councils and task forces,
- spatial proximity and corridor topology.

Zones and sectors are the **predecessors of wards**; later phase documents
MAY formalize them into a fixed district schema (e.g. 36 wards) but they
SHOULD NOT be hard-coded at founding.

Implementation hooks:

- define a **Zone** entity whenever multiple Pods depend on the same key
  asset cluster,
- tie Zone boundaries to asset influence areas and corridor graphs,
- record which Councils have jurisdiction over which Zones.

### 5.6 Phase F: Sealed Core Proposal & Construction

Repeated incidents near critical assets (e.g. near-breaches, leaks, accidents)
motivate a higher-level Politic action at the Council/Zone level:

- "We must **harden** these assets, or one failure could doom us."

Agents with strong Communal Coherence, high Survive drive, and suitable skills
propose:

- constructing a **sealed core** around key assets
  (Well, central air-plants, med center, archives),
- implementing **access controls** and more rigorous protocols,
- dedicating labor and material to building walls, locks, and HVAC loops.

If adopted, this is the **first true sealed inner core** of the city:

- physically safer, better air and resource stability,
- limited residential/working slots tied to critical roles.

Socially, this begins a **class gradient**:

- those who work in or live near the core experience higher survival odds,
- access is a powerful lever for future politics and patronage.

Implementation hooks:

- create a **Core** or **InnerZone** entity with strict access rules,
- tie occupational roles (Well operators, core med staff, central techs) to
  Core access,
- implement a small but significant survival bonus for Core residents vs
  non-Core agents.

---

## 6. Legitimacy & Frontier Trust

### 6.1 Frontier Trust

To represent early belief in emergent councils and rules, we introduce
**frontier_trust** as a per-agent scalar:

```yaml
frontier_trust: 0.0-1.0
```

- High frontier_trust means:
  - "I believe listening to these people and following these rules
    improves my survival."
- Low frontier_trust means:
  - "These leaders are incompetent, biased, or dangerous; I should rely on
    myself or my own crew."

Frontier trust is updated by experience:

- increased by:
  - successful task forces,
  - fair and effective dispute resolution,
  - visible competence under stress;
- decreased by:
  - perceived favoritism,
  - preventable accidents or disasters,
  - broken promises or arbitrary punishments.

### 6.2 Obedience, Disobedience & Consequences

When councils issue decisions (e.g. work schedules, allocation rules,
construction plans), agents weigh obedience vs disobedience using:

- frontier_trust,
- personal drives,
- risk perception,
- social ties.

Consequences of systematic disobedience in the founding sequence SHOULD be:

- **resource access penalties** (less reliable food/water),
- **social penalties** (isolation, fewer allies),
- **infrastructure penalties** (no access to safer pods or Core areas).

This ensures that, in Golden Age Phase 0, it is usually **rational** to align
with effective councils, even though no formal nobility or harsh repression
exists yet.

---

## 7. Emergent Social Layers (Phase 0 Only)

Even within Phase 0, the dynamics described here will produce early
differentiation:

- **Pod leaders** and effective council members gain local prestige and
  influence,
- specialized task force leads become recognized experts,
- agents with high Communal Coherence and successful Politic actions become
  **institution-builders**,
- Core workers and residents form a **proto-elite stratum** through improved
  survival odds and access to information.

These emergent layers form the **substrate** upon which later phases
(Realization of Limits, Age of Scarcity and Corruption) can build:

- turning lead roles into formal offices,
- turning Zones into formal wards,
- turning aligned households into dynasties,
- and turning stricter survival constraints into
  full-feudal and cartelized power structures.

D-RUNTIME-0108 SHOULD be treated as the canonical reference for how agents,
starting from equal nominal status, are given the tools to **craft their
own city** and the institutional library their descendants will inherit.
