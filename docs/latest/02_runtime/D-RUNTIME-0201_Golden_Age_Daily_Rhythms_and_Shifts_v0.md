---
title: Golden_Age_Daily_Rhythms_and_Shifts
doc_id: D-RUNTIME-0201
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-SCEN-0002     # Founding_Wakeup_Scenario
  - D-AGENT-0001    # Agent_Core_Schema_v0
  - D-AGENT-0020    # Unified_Agent_Model_v0
  - D-MEMORY-0004   # Belief_System_and_Tiered_Memory_v0
---

# 02_runtime · Golden Age Daily Rhythms and Shifts v0 (D-RUNTIME-0201)

## 1. Purpose & Scope

This document defines **daily rhythm templates** for key roles in the Golden Age
baseline of the Dosadi simulation. It links:

- the global timebase (ticks → minutes → hours),
- wake / sleep cycles,
- work / meeting / queue blocks,

to the **memory system** (short-term episodes, daily buffers, long-term beliefs)
and the **emergence of early institutions** (council, stewards, scribes,
task forces).

The goal is not to hard-code rigid schedules, but to define **role templates**
that the runtime can use as defaults when assigning wake/sleep blocks and
activity windows. Later phases (Realization of Limits, Scarcity & Corruption)
will distort these rhythms; Golden Age is the baseline.

This document focuses on:

- Tier-1 pod workers (day shift),
- Tier-1/2 night maintenance / guard roles,
- Tier-2 stewards / shift supervisors,
- Tier-2/3 scribes / archivists,
- Tier-3 councilors / pattern-readers.

Numerical tick ranges are indicative; implementations may adjust exact values
while preserving the structure.

---

## 2. Timebase Reminder

Per D-RUNTIME-0001, the simulation timebase is:

- 1 tick ≈ 0.6 seconds
- 100 ticks ≈ 1 minute
- 6 000 ticks ≈ 1 hour
- 144 000 ticks ≈ 24 hours

This document uses **clock-time language** (hours) for clarity while implicitly
mapping to ticks.

Sleep and consolidation windows are defined per role; there is **no global
synchronization** of sleep. This is important for:

- night-shift vs day-shift divergence,
- staggered memory consolidation,
- and asynchronous rumor and report flows.

---

## 3. Tier-1 Pod Worker – Standard Day Shift Colonist

**Role:** basic labor, minimal authority. Most early colonists fall into some
variant of this pattern.

### 3.1 Daily Rhythm (24h)

**Hour 0–1: Wake & body check**

- Wake up in pod bunk.
- Light hygiene, suit check, first food/water intake.
- Brief social contact with bunkmates (conversation, complaints, minor gossip).
- Memory effects:
  - short-term buffer starts filling with body-signal episodes:
    - “a bit stiff”, “hungry”, “cold/warm”;
  - only particularly salient or goal-relevant signals enter daily buffer.

**Hour 1–3: Commute & early work**

- Move through familiar corridors to assigned work area (cleaning, hauling,
  simple fabrication, maintenance support, etc.).
- Work is repetitive and spatially localized.
- Memory effects:
  - PlaceBeliefs reinforced for pods, corridors, depots along commute:
    - perceived_safety, perceived_access, crowding.
  - Most episodes are discarded from short-term buffer unless something
    unusual/unsafe occurs.

**Hour 3–7: Main work block**

- 3–4 hours of continuous task work under supervision.
- One or two short breaks for food/water.
- Memory effects:
  - normal days:
    - only a few episodes promoted to daily buffer (minor conflicts, praise,
      visible accidents, frightening moments, strong rumors);
  - heavy days (fights, serious accidents, alarms):
    - daily buffer can approach capacity,
    - low-salience episodes are dropped (overflow),
    - long-term beliefs skew toward the most painful or frightening experiences.

**Hour 7–9: Post-work queues**

- End of shift.
- Join queues for rations, hygiene, suit maintenance.
- Primary site of **rumor exchange** for Tier-1:
  - talk about guards, stewards, council, and protocols.
- Memory effects:
  - a subset of social and rumor episodes enter daily buffer,
  - these shape coarse FactionBeliefs:
    - “garrison is dangerous”, “council tries to be fair / doesn’t care”.

**Hour 9–11: Free / pod time**

- Low-intensity activities:
  - conversation, simple games, petty trades, informal help.
- Memory effects:
  - some episodes consolidate into PersonBeliefs for a **small number** of
    individuals (bunkmates, romantic partners, particularly salient neighbors),
  - for most Tier-1 agents, this block is where their tiny person-belief catalog
    is formed and reinforced.

**Hour 11–16: Sleep / downtime**

- 5 hours of mostly uninterrupted sleep (Golden Age ideal).
- Memory consolidation:
  - daily buffer episodes are processed:
    - PlaceBeliefs (safety, resource quality) updated for routine locations,
    - FactionBeliefs about council/pod/garrison adjusted,
    - a handful of PersonBeliefs (supervisor, bunkmates, notable guards) updated;
  - daily buffer is then cleared.
- Remaining ~3 hours of the 24h cycle are flexible:
  - shift offset, extra sleep, or overtime (later phases).

### 3.2 Key Properties for Tier-1 Template

- Wake time: ~16 hours; Sleep: ~5–7 hours; remaining time is slack for phase
  variation.
- Beliefs most used:
  - PlaceBeliefs (safety, comfort, crowding),
  - coarse FactionBeliefs (who hits, who feeds),
  - 3–8 PersonBeliefs (kin, immediate supervisor, particularly salient figures).
- Overload behavior:
  - chaotic days → daily buffer overflow → loss of many mundane details;
  - long-term beliefs become dominated by the day’s most emotionally intense
    episodes (fear, humiliation, relief).

---

## 4. Tier-1/2 Night Maintenance / Guard – The Night Backbone

**Role:** suit/pipe maintenance, exo-bay assistance, patrols in low-traffic
hours. A mix of Tier-1 bodies with elevated Tier-2 leads.

### 4.1 Daily Rhythm (Night-Shift Template)

**Hour 0–6: Sleep / recovery**

- Night workers sleep while day-shift workers are active.
- Memory consolidation:
  - episodes from the previous night’s work (hazards, confrontations,
    suspicious behavior) are processed now,
  - strong reinforcement of night-specific PlaceBeliefs:
    - “this corridor is dangerous at night,”
    - “this bay is safe if X is on duty”.

**Hour 6–8: Wake / transition**

- Wake, eat, suit check.
- Briefing with day stewards or scribes:
  - recap of day incidents,
  - new protocols or operational changes that affect night work.

**Hour 8–12: Prep & shadow period**

- Overlaps with late day shift:
  - take over corridors and bays as they empty,
  - inspect infrastructure,
  - coordinate handover with day staff.
- Memory effects:
  - episodes about **handover quality** matter (“day crew left a mess”, “lied
    about conditions”),
  - PersonBeliefs for selected day stewards and technical staff.

**Hour 12–18: Core night shift**

- True night window:
  - corridor patrols,
  - exo-bay supervision,
  - emergency response,
  - suit/pipe/vent maintenance.
- Fewer witnesses, more cover for misbehavior.
- Memory effects:
  - high-salience episodes (shadows, noises, minor attacks, undisclosed
    hazards) are common,
  - night workers carry sharper PlaceBeliefs for certain routes and bays than
    day workers.

**Hour 18–20: Wind-down & reporting**

- End-of-shift debriefing to stewards or scribes:
  - hazard anomalies,
  - rule violations,
  - incidents that may require new protocols.
- Tier-2 night leads function as **memory compression nodes**:
  - they transform fuzzy Tier-1 night reports into structured logs.

**Hour 20–24: Free / drift**

- Food, minimal social time, private tasks.
- Gradual drift into sleep window.

### 4.2 Key Properties for Night Template

- Wake time: 16–18 hours, with peak activity during global quiet hours.
- Belief specialization:
  - stronger PlaceBeliefs for night conditions,
  - precise PersonBeliefs for repeat offenders/allies and stewards.
- Systemic bias:
  - because their **sleep time** often overlaps with council meetings,
    night incidents risk being underweighted unless scribes and stewards act as
    explicit bridges.

---

## 5. Tier-2 Steward / Shift Supervisor – Local Brain & Buffer

**Role:** manage a pod section, bay, or corridor cluster; buffer between council
and workers. Major local pattern-recognition role.

### 5.1 Daily Rhythm

**Hour 0–1: Quiet review**

- Wake slightly earlier than subordinates.
- Skim:
  - prior-cycle logs for their domain,
  - new notices or protocol changes.
- Memory effects:
  - ExpectationBeliefs updated (“tension rising?”, “injuries trending?”),
  - alignment of personal goals with new constraints (keep section stable,
    protect status).

**Hour 1–3: Start-of-shift setup**

- Brief incoming workers.
- Assign roles and tasks.
- Walk the area:
  - quick visual checks of corridors, equipment, queue conditions.
- Socially intense block: many short interactions.
- Memory effects:
  - social episodes dominate daily buffer,
  - PersonBeliefs for subordinates, habitual troublemakers, and key peers.

**Hour 3–7: Active management**

- Rotate between:
  - handling conflicts,
  - fielding requests,
  - adjusting assignments,
  - sending short reports upward if anomalies occur.
- Memory effects:
  - daily buffer fills with PersonEpisodes and PlaceEpisodes,
  - high risk of overload on chaotic days.

**Hour 7–8: Mid-shift overview**

- Short “steering” window:
  - review incidents,
  - consider deploying extra guards, maintenance crews, or escort rules.
- Seeds ExpectationBeliefs:
  - “if we don’t add another guard, the queue will blow up,”
  - “this corridor is a near miss away from a serious accident.”

**Hour 8–11: Late shift & handover**

- Close out shift:
  - check tasks are complete,
  - log unresolved issues,
  - handover to next shift or night crew.
- Write **local reports** (often the only written trace that survives).
- Memory effects:
  - acts as an internal filter:
    - some episodes are recorded,
    - others are only preserved in personal beliefs.

**Hour 11–13: Council / steward meetings (not daily)**

- On some days, attend:
  - ward-level summaries,
  - protocol discussions,
  - hazard reviews.
- Memory effects:
  - FactionBeliefs and ProtocolBeliefs updated,
  - PersonBeliefs sharpened for councilors, scribes, other stewards.

**Hour 13–18: Free + sleep**

- Some personal time, then 5–7 hours of sleep.
- Consolidation:
  - heavy updates to PersonBeliefs (subordinates, peers, superiors),
  - PlaceBeliefs for their domain (safety, throughput),
  - ProtocolBeliefs about “real rules”, “flexible rules”, “theater rules”.

### 5.2 Key Properties

- Wake time: 16–18 hours; chronically overloaded in later phases.
- Memory role: significant **belief formation nodes**; their logs and omissions
  shape institutional memory.
- Fragility: chronic overload and sleep loss shrink usable daily buffers,
  leading to belief systems dominated by a few pain/pressure themes.

---

## 6. Tier-2/3 Scribe / Archivist – Institutional Memory

**Role:** attached to council, pods, exo-bays, or the Well core; convert episodic
chaos into written records and compact “views of history.” Early memory
professionals.

### 6.1 Daily Rhythm

**Hour 0–2: Quiet archival block**

- Preferentially scheduled while others sleep or are in transit.
- Copy and summarize prior day’s reports:
  - movement incidents,
  - injuries,
  - protocol breaches,
  - production counts.
- Memory effects:
  - strong reinforcement of ProtocolBeliefs and FactionBeliefs,
  - beliefs skew toward archived reality vs personal experience.

**Hour 2–4: Meeting prep**

- Prepare briefing packets for stewards or council:
  - aggregated dashboards,
  - anomaly flags.
- ExpectationBeliefs form from aggregate views rather than single episodes.

**Hour 4–8: Field presence**

- Spend time in operational spaces:
  - queues, bays, corridors, or pods.
- Goals:
  - ground-truth records,
  - listen for rumor,
  - detect mismatches between protocol on paper vs protocol in practice.
- Memory effects:
  - rich social episodes (many scribes are high-INT, high-CHA),
  - PersonBeliefs about who misreports, who tells the truth.

**Hour 8–11: Meetings**

- Attend:
  - council sessions,
  - dispute hearings,
  - protocol-authoring discussions.
- Take minutes, annotate **reasons for decisions** when possible.

**Hour 11–14: Follow-up logging**

- Turn meeting output into:
  - protocol records,
  - amendments,
  - explanatory notes (recorded “why”).
- Fate of “why we made this rule” depends on this block’s quality and load.

**Hour 14–20: Sleep / personal**

- 6 hours of sleep; some flexible personal time.
- Consolidation:
  - belief catalogs heavy on ProtocolBeliefs, FactionBeliefs, and PersonBeliefs
    for high-tier actors,
  - scribes become carriers of an “institutional worldview.”

### 6.2 Key Properties

- First role with **memory as a primary job**.
- Rhythm sits between field and council → main conduit that lets Tier-3 see
  beyond immediate circles.
- Vulnerable to:
  - political capture,
  - selective recording,
  - chronic overload which narrows what actually gets archived.

---

## 7. Tier-3 Councilor / Pattern-Reader – Macro Horizon

**Role:** early on, the most competent and trusted agents from each pod; later,
formal councilors, dukes, guild heads. Responsible for stability and long-horizon
risk management.

### 7.1 Daily Rhythm

**Hour 0–2: Private review**

- Wake, read summaries prepared by scribes:
  - key incidents,
  - trend summaries,
  - resource status,
  - protocol breaches and enforcement patterns.
- Memory effects:
  - ExpectationBeliefs updated (“are things getting safer or tenser?”),
  - adjustment of long-horizon goals (stability, legitimacy, control).

**Hour 2–4: Small consultations**

- Brief one-on-one or small-group meetings with:
  - stewards,
  - scribes,
  - technical experts.
- Memory effects:
  - PersonBeliefs sharpened for other elites and crucial stewards,
  - FactionBeliefs about proto-guilds and clusters.

**Hour 4–7: Council session / decisions**

- Main council block:
  - hearing reports,
  - authoring or revising protocols,
  - forming or disbanding task forces,
  - allocating resources.
- High cognitive load; expectation-setting center.

**Hour 7–10: Public presence / inspections**

- Appear in pods, queues, bays, or corridors:
  - demonstrate presence,
  - gather informal signals,
  - test whether protocols are followed or gamed.
- Memory effects:
  - episodic impressions are sparse but heavily weighted
    (e.g. “this corridor felt explosive”, “that steward defied me in public”).

**Hour 10–13: Strategic planning**

- Debrief with scribes and trusted stewards:
  - refine protocols,
  - consider structural changes (more formal roles, ward boundaries),
  - in later Golden Age, early thinking about scarcity.
- ExpectationBeliefs and ProtocolBeliefs are updated or created here,
  often with long time horizons.

**Hour 13–18: Sleep + protected downtime**

- In Golden Age, councilors are usually shielded from constant overtime.
- 6+ hours of sleep and some secluded leisure.
- Consolidation:
  - ExpectationBeliefs and ProtocolBeliefs become relatively stable,
  - personal belief systems are less chaotic than those of stewards or workers,
    but can still be wrong or biased by selective information.

### 7.2 Key Properties

- Daily rhythm maximizes **pattern-reading** and relatively clean belief
  consolidation.
- Heavy reliance on curated inputs from scribes and stewards → structural bias
  toward institutional narratives.
- Errors at this level propagate widely through protocols and task-force
  deployments.

---

## 8. Usage Notes for Runtime

This document is descriptive, not strictly prescriptive. Implementations MAY:

- Instantiate role templates as **default schedules** for agents by role/tier:
  - e.g. `RoleSchedule` objects that specify wake blocks, work blocks,
    meeting windows, and sleep windows in ticks.
- Use wake/sleep windows to:
  - determine when short-term and daily buffers are active,
  - trigger nightly belief integration during sleep,
  - schedule when agents are eligible for certain actions
    (meetings, patrols, queues, etc.).
- Stagger schedules within a role to avoid global synchronization and to simulate
  natural variation.

Later documents (D-RUNTIME-02xx, D-MEMORY-02xx) SHOULD:

- define exact tick ranges for these blocks,
- specify how sleep/wake rhythms are modified under stress, scarcity,
  and protocol changes,
- and integrate schedules with **episode generation** and **belief updates** in
  the runtime decision loop.
