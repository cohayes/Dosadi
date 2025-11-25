---
title: Proto_Political_Body_Formation_and_Protocol_Governance
doc_id: D-LAW-0012
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-RUNTIME-0107   # Campaign_Phases_and_Golden_Age_Baseline
  - D-RUNTIME-0108   # Founding_Sequence_and_Communal_Coherence
  - D-LAW-0011       # Founding_Council_Protocols_v0
  - D-MEMORY-0001    # Episode_Management_System_v0
  - D-MEMORY-0002    # Episode_Schema_and_Memory_Behavior_v0
  - D-MEMORY-0003    # Episode_Transmission_Channels_v0
  - D-AGENT-0001     # Agent_Core_Schema_v0
  - D-AGENT-0006     # Agent_Attributes_and_Skills_v0
  - D-AGENT-0023     # Agent_Goal_System_v0
---

# 10_law · Proto-Political Body Formation and Protocol Governance v0 (D-LAW-0012)

## 1. Purpose & Scope

This document describes how **proto-political bodies** emerge and solidify in
Dosadi, and how they come to **own and govern protocol stacks**, rooted
explicitly in the **Control, Prediction & Order** goal family
(Goal 3.13 in D-AGENT-0023).

The focus is on:

- how individual agents with strong Control/Prediction/Order goals
  cluster into councils, guild boards, and cartel cores,
- how these bodies:
  - claim domains of responsibility,
  - build and manage **communication avenues** within those domains,
  - distill episodic experience into **formal protocols**,
- and how their protocol governance feeds back into the broader
  city-scale behavior.

This is a conceptual law/structure document and does not specify concrete
code or data structures. It is intended to guide implementation in runtime,
agent, memory, info_security, and law systems.

---

## 2. Control, Prediction & Order (Goal 3.13)

### 2.1 Goal Definition (from D-AGENT-0023)

The **Control, Prediction & Order** goal family captures an agent's desire to:

- reduce uncertainty in their environment,
- make outcomes predictable,
- structure roles, rules, and flows so events become manageable,
- and maintain stable patterns they can understand and influence.

Agents with high weight on this goal:

- are uncomfortable with chaotic, ad-hoc systems,
- seek to define, enforce, and refine **procedures**,
- value accurate information channels and reliable reporting,
- tend to accumulate authority if allowed to.

This goal family is the natural seed for proto-political roles:
- organizers, coordinators, stewards, clerks, auditors, commanders, guild
  elders, cartel planners.

### 2.2 Interaction with Other Goals

Control, Prediction & Order competes or cooperates with:

- **Survival & Security**:
  - encourages building systems that improve group survival probabilities.
- **Status & Prestige**:
  - structured order often elevates its architects.
- **Exploration & Curiosity**:
  - may either suppress risky exploration or channel it into regulated
    survey missions.
- **Greed & Accumulation**:
  - may bend order toward preserving monopolies and rent-extraction.

Proto-political bodies form when agents with strong Control/Prediction/Order
goals find that **individual action is insufficient** to tame systemic chaos.

---

## 3. From Individuals to Proto-Political Bodies

### 3.1 Stage 0: Ambient Chaos & Local Coordination Attempts

Immediately after wakeup (or during any regime shock), the environment is:

- high-entropy (no established rules, weak enforcement),
- full of conflicting goals and local improvisations.

Agents with high Control/Prediction/Order goals will:

- try to **stabilize their immediate context**:
  - organize queues instead of mobs,
  - propose simple rotation systems for chores,
  - keep informal notes or tallies (proto-ledgers),
- and begin **informal mediation**:
  - resolving disputes within pods,
  - coordinating work assignments inside a bunk cluster or crew.

At this stage, these are **personal leadership attempts**, not institutions.

### 3.2 Stage 1: Recognition & Role Consolidation

When local coordination attempts repeatedly **reduce pain episodes** (fewer
fights, smoother ration lines, safer corridors), others:

- start deferring to these organizers,
- seek them out for decisions,
- copy their rules.

Social recognition stabilizes **proto-roles** such as:

- "queue organizer",
- "crew chief",
- "pod spokesperson",
- "safety-minded elder".

Agents in these roles:

- accumulate **episodic knowledge** about coordination problems and fixes,
- become focal points for **episode transmission** (D-MEMORY-0003),
- and are natural anchors for future councils and boards.

### 3.3 Stage 2: Clustered Coordinators & Emergent Councils

As population and complexity grow:

- multiple local organizers in overlapping domains (ration queues, bunk
  allocation, survey missions) start interacting,
- their Control/Prediction/Order goals extend beyond local fixes to
  **system-wide patterns**.

They begin to:

- **meet explicitly** to discuss cross-cutting issues:
  - ration vs work vs safety tradeoffs,
- create informal **decision circles**:
  - early council-like gatherings,
- agree on **shared protocols**:
  - e.g. city-wide rules for survey missions,
  - well access tiers,
  - dispute triage procedures.

This is where **proto-political bodies** first become visible:

- Founding Council (D-LAW-0011),
- early ward committees,
- ad-hoc guild councils forming around key industries.

### 3.4 Stage 3: Domain Claims & Authority

Over time, proto-political bodies **claim responsibility** for specific
domains, e.g.:

- Founding Council:
  - survival-critical rationing, initial law frame, dispute triage,
  - macro allocation of survey missions and labor.
- Ward Committees:
  - local housing allocation, maintenance priorities, street-level order.
- Guild Boards:
  - process standards, apprenticeship rules, product quality and quotas.
- Cartel Cores:
  - smuggling routes, pricing agreements, internal discipline.

Each body now:

- asserts **authority to make and revise protocols** for its domain,
- expects reports from subordinate actors (Tier-2 coordinators, Tier-1
  workers),
- and exerts control over key **communication avenues** (reports, briefings,
  posted rules, visual propaganda).

At this stage, the city landscape is filled with overlapping, sometimes
competing **structures of order**.

---

## 4. Internal Structure: Tiers & Roles inside a Political Body

Within a proto-political body, the Control/Prediction/Order drive expresses
itself through **tiered roles**:

### 4.1 Tier-3: Core Stewards / Strategists

- Hold the strongest Control/Prediction/Order goals.
- Responsibilities:
  - define domain-level goals (stability, productivity, compliance),
  - review episodes and patterns from their domain (via archives,
    formal reports, and trusted informants),
  - draft and revise **protocols**,
  - allocate authority and punishment powers.

They sit at the top of the **information funnel** and are the primary
**protocol authors** for their domain.

### 4.2 Tier-2: Executing Coordinators / Foremen / Auditors

- Moderate to high Control/Prediction/Order, more operationally focused.
- Responsibilities:
  - ensure protocols are actually followed at local sites,
  - adjust in real time for local exceptions ("bending" rules),
  - monitor compliance and surface important episodes upward,
  - maintain local ledgers and shift logs.

They are the main **transmission link** between Tier-1 experience and
Tier-3 protocol revisions.

### 4.3 Tier-1: Workers & Street-Level Enforcers

- Varying goal stacks; some may care little about order beyond immediate
  personal benefit.
- Responsibilities:
  - follow protocols when enforced or when obviously beneficial,
  - improvise when protocols are missing, unclear, or harmful,
  - occasionally submit complaints, rumors, or incident reports.

From the political body's perspective, Tier-1 agents are the **substrate**
on which order is imposed and from which raw episodes continuously rise.

---

## 5. Communication Avenues within Political Bodies

Political bodies **do not exist** without reliable communication between their
tiers. Their Control/Prediction/Order goals push them to institutionalize
certain **channels** (D-MEMORY-0003):

### 5.1 Upward Channels (Bottom → Top)

- **Formal reports & ledgers**:
  - incident reports, productivity logs, ration deviation reports,
    safety logs.
- **Delegated spokespeople**:
  - pod reps, squad leaders, shift foremen who attend briefings and bring
    up grievances.
- **Targeted whispers / private complaints**:
  - trusted intermediaries who ferry sensitive episodes upward.

These channels feed Tier-3's **pattern recognition** and anomaly detection.

### 5.2 Lateral Channels (Within Tier or Between Peers)

- Regular coordination meetings:
  - between foremen,
  - between guild masters,
  - between ward committees.
- Gossip networks:
  - persistent background information flow about how other bodies operate.

These channels help maintain **coherent expectations** within a tier and
enable multi-body **coalitions or rivalries**.

### 5.3 Downward Channels (Top → Bottom)

- **Protocols and protocol changes**:
  - posted procedures, training sessions, mandatory briefings.
- **Visual media and slogans**:
  - propaganda posters, hazard warnings, territorial markings.
- **Direct commands and decrees**:
  - orders from council, guild board, or command core.

These channels are how political bodies attempt to **impose order** on
hundreds or thousands of Tier-1 agents.

---

## 6. Protocol Governance: Lifecycle in a Political Body

### 6.1 Protocol Ownership

Each proto-political body maintains a **protocol stack** for its domain, e.g.:

- Founding Council:
  - ration distribution, pod formation, initial dispute triage.
- Guild Board:
  - process control, safety checks, training requirements.
- Ward Committee:
  - local curfews, crowd control, tenant rules.

The body:

- owns the right to **approve**, **update**, and **retire** protocols,
- may delegate small adjustments to Tier-2, but reserves strategic changes.

### 6.2 Protocol Lifecycle Stages

1. **Trigger: Pattern Recognition**
   - Tier-2 and Tier-3 agents notice recurring episodes:
     - repeated accidents,
     - chronic shortages,
     - recurring disputes.

2. **Proposal**
   - A Tier-3 steward (or coalition) proposes a new protocol or revision:
     - draws on episodic patterns, reports, and sometimes rumor.

3. **Deliberation**
   - Body debates:
     - expected impact on control, prediction, and order,
     - cost in resources and legitimacy,
     - possible loopholes or resistance.

4. **Formalization**
   - Protocol drafted in WHEN / IF / THEN / ELSE form (see D-LAW-0011 and
     D-MEMORY-0001),
   - assigned scope (which wards, which facilities, which roles),
   - set enforcement expectations and sanctions.

5. **Dissemination**
   - Downward channels:
     - training, posted procedures, visual cues, announcements.

6. **Monitoring**
   - Upward channels:
     - incident rates,
     - compliance logs,
     - informal reports of workarounds.

7. **Revision / Fork / Retirement**
   - If protocol consistently:
     - improves order → reinforced, possibly exported to other domains.
     - fails or creates new problems → revised, narrowed, or scrapped.
   - Competing factions may **fork** protocols:
     - alternative guild standards,
     - rival councils' rules.

Throughout, the Control/Prediction/Order goal pushes political bodies to
prefer **stable, legible** protocols, but reality may force adaptability.

---

## 7. Legitimacy, Resistance, and Drift

### 7.1 Legitimacy as Predictive Performance

Legitimacy for a political body emerges when:

- its protocols **actually improve predictability and safety**,
- agents see that following the rules:
  - reduces risk,
  - improves access to resources,
  - or at least minimizes arbitrary punishment.

Agents with strong Control/Prediction/Order goals will prefer bodies whose
protocols **match observed episodes**.

### 7.2 Resistance & Counter-Order

When protocols:

- are obviously misaligned with reality,
- serve narrow elite interests at everyone else's expense,
- or generate excessive friction without benefit,

agents and rival factions may:

- quietly ignore or subvert them (local workarounds),
- propagate counter-narratives via storytelling and graffiti,
- set up **rival proto-political bodies** with their own protocol stacks
  (shadow councils, breakaway guilds, cartels).

This creates **competing orders** and overlapping claims to Control/Prediction
& Order.

### 7.3 Drift & Capture

Over time, political bodies can drift:

- from genuine order-seeking into **self-preservation**,
- from wide stability goals into **narrow control over rents**.

Protocols can become:

- tools for **entrenchment**,
- instruments of **selective enforcement** and **political punishment**.

At the same time, new high-Control/Prediction/Order agents may arise:

- seeing the existing order as chaotic or unjust,
- forming reformist bodies that promise better prediction and fairer order.

---

## 8. Integration with Campaign Phases

### 8.1 Phase 0: Golden Age Baseline

In the Golden Age:

- proto-political bodies are mostly:
  - constructive, order-creating,
  - aligned with broad survival and growth goals.
- Control/Prediction/Order is primarily about:
  - making the city **work**,
  - ensuring smooth rationing, safe work, efficient infrastructure.

Protocols are:

- relatively transparent,
- less corrupted by scarcity and severe power struggles.

### 8.2 Phase 1: Realization of Limits

As the Well's limits become known:

- the same political structures are repurposed to:
  - **tighten discipline**,
  - implement rationing regimes,
  - manage rising tensions.

Control/Prediction/Order goals shift toward:

- preserving system viability under stress,
- often at the cost of flexibility and local autonomy.

Protocols become stricter, sanctions harsher, information channels more
controlled.

### 8.3 Phase 2: Age of Scarcity and Corruption

Under deep scarcity and entrenched interests:

- proto-political bodies can become:
  - vehicles for **corruption and cartelization**,
  - tools to manage unrest through **repression and narcotics**,
  - heavily focused on **prediction and control for the benefit of elites**.

Competing bodies (rebels, splinter guilds, underground councils) emerge,
each claiming to offer a **better order**.

Control/Prediction/Order remains central, but its **beneficiaries** and
**methods** become heavily contested.

---

## 9. Summary & Future Work

D-LAW-0012 defines:

- how individual Control/Prediction/Order goals at the agent level scale up
  into:
  - emergent proto-political bodies,
  - tiered structures within those bodies,
  - controlled communication avenues,
  - and domain-owned protocol stacks.
- how protocol governance follows a **recognize → propose → formalize →
  disseminate → monitor → revise** lifecycle,
- and how legitimacy, resistance, and drift arise from the tension between
  promised order and lived episodes.

Future documents SHOULD:

- define concrete **body types**:
  - founding council, ward committee, guild board, cartel core, CI directorate,
- specify **mechanical hooks**:
  - how a body is represented in code,
  - how it subscribes to episode streams from its domain,
  - how it instantiates and revises protocols over time,
- integrate with:
  - **INFO_SECURITY** (control and censorship of communication channels),
  - **ECONOMY** (resource allocation and taxation protocols),
  - **MIL** (command-and-control, discipline, and coup handling),
  - **RUNTIME** (how body behavior impacts global stress, fragmentation,
    and legitimacy metrics).

D-LAW-0012 should be treated as the conceptual foundation for any system that
creates, updates, or simulates councils, guilds, boards, or cartel cores in
Dosadi, ensuring they remain grounded in the Control/Prediction/Order goals
of the agents who animate them.
