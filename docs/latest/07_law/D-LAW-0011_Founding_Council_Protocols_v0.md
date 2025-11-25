---
title: Founding_Council_Protocols
doc_id: D-LAW-0011
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-RUNTIME-0107  # Campaign_Phases_and_Golden_Age_Baseline
  - D-RUNTIME-0108  # Founding_Sequence_and_Communal_Coherence
  - D-AGENT-0001    # Agent_Core_Schema_v0
  - D-AGENT-0023    # Agent_Goal_System_v0
  - D-MEMORY-0001   # Episode_Management_System_v0
---

# 10_law · Founding Council Protocols v0 (D-LAW-0011)

## 1. Purpose & Context

This document defines the **Founding Council Protocol Stack v0** for Dosadi's
tick-0 / early Golden Age phase.

At simulation start, a population of colonists "wakes up" around the Well
with:
- limited initial structure,
- a shared need to survive the first days and weeks,
- and no entrenched nobility or guild hierarchy yet.

The **Founding Council** is the emergent proto-political body that:
- stabilizes access to critical resources (Well, stockpiles, bunks),
- seeds basic social organization (pods, task forces),
- and begins the habit of **logging decisions and incidents as episodes**
  (D-MEMORY-0001).

This document describes the **initial protocol stack** such a council is
likely to generate in the first days. These protocols are intentionally:
- simple enough for Tier-1 actors to follow,
- flexible enough for Tier-2 emergent leaders to bend,
- and traceable enough for Tier-3 stewards to revise based on cumulative
  episodes.

---

## 2. Founding Council Role & Goals

In early ticks, the Founding Council is not yet a formal monarchy or guild
structure. It is a small cluster of agents whose abilities and goals pull
them into de facto Tier-3 roles for core domains.

### 2.1 Implicit Mandate

The council's emergent mandate is:
1. **Prevent immediate chaos and waste** around the Well and stockpiles.
2. **Ensure basic survival**: food, water, safe sleeping arrangements.
3. **Reduce violent fragmentation** into warring cliques.
4. **Lay the groundwork** for future governance that can be revised as
   circumstances change.

### 2.2 Goal Stack (Conceptual)

Canonical high-level goals include:
- **Primary**
  - Maintain survival of as many colonists as reasonably possible.
  - Preserve critical infrastructure (Well, sealed hardware, industrial kit).
- **Secondary**
  - Avoid rapid fragmentation into hostile pods/factions.
  - Establish decision habits and record-keeping that allow future revision.

The protocols below are the **first concrete expressions** of these goals.

---

## 3. Protocol Stack v0 Overview

The Founding Council Protocol Stack v0 consists of several families:
1. Ration & Well Access.
2. Bunk & Pod Formation.
3. Work Assignment & Survey.
4. Dispute Triage & Violence Containment.
5. Foundational Norm / Law Frame.
6. Founding Records & Episode Capture.

Each protocol is intended to be:
- directly usable by Tier-1 workers,
- improvable by emergent Tier-2 leaders,
- and revisable or replaceable by Tier-3 stewards as episodes accumulate.

Field names and condition structures here are conceptual and should be
aligned with the runtime state schema during implementation.

---

## 4. Ration & Well Access Protocol

### 4.1 RATION_DISTRIBUTION_V0

**Purpose:** Prevent initial riots and waste at stockpiles and the Well by
imposing a minimal, easy-to-follow ration distribution method.

**Key idea:** Rations are distributed **by pod**, through designated
representatives. No free-for-all access to stockpiles.

```text
PROTOCOL: RATION_DISTRIBUTION_V0

WHEN
  task_type == "daily_ration_issue"

THEN
  - STEP 1: Recognize provisional pods (bunk clusters of size 8–20).
  - STEP 2: One representative per pod queues at Well-side depot.
  - STEP 3: Issue standard ration_per_capita based on headcount manifest.
  - STEP 4: Record pod_id, count, time in RATION_LEDGER.
  - STEP 5: Any disputes are deferred to DISPUTE_TRIAGE_V0,
            not resolved in line.
```

Notes:
- This protocol does **not** yet encode long-term scarcity modeling; it
  simply enforces order and basic fairness at the distribution point.
- It implicitly treats pods as the basic socio-political unit.

---

## 5. Bunk & Pod Formation Protocol

### 5.1 POD_FORMATION_V0

**Purpose:** Turn a mass of individuals into manageable social units (pods)
with continuity and responsibility.

**Key idea:** Encourage self-chosen pods of moderate size, then bind ration
and task allocation to pod membership.

```text
PROTOCOL: POD_FORMATION_V0

WHEN
  new_arrivals == true
  AND housing_status == "unassigned"

THEN
  - STEP 1: Instruct individuals to form groups of 8–20: provisional pods.
  - STEP 2: Assign each pod a bunk cluster id.
  - STEP 3: Record pod membership in POD_REGISTER.
  - STEP 4: Inform pods that:
            - ration and task allocations will be pod-based,
            - internal norms are pod responsibility unless they
              violate COUNCIL_FRAME_V0.
```

Notes:
- This protocol seeds pods as **basic political and administrative units**.
- Later documents may refine pod size, stability rules, and pod-splitting /
  merging processes.

---

## 6. Work Assignment & Survey Protocols

The council must quickly begin **learning the environment** and spinning up
basic productive activity without collapsing into misallocation.

### 6.1 SKILL_INTAKE_V0

**Purpose:** Gather rough skill information to seed early task force
formation.

```text
PROTOCOL: SKILL_INTAKE_V0

WHEN
  colonist_status == "newly_assigned_pod"

THEN
  - STEP 1: Each colonist briefly declares prior skills (self-report).
  - STEP 2: Record in SKILL_REGISTER with broad tags
            (e.g. medic, tech, organizer, labor, logistics).
  - STEP 3: Use this register to assemble provisional task forces:
            - survey_teams
            - maintenance_teams
            - medical_support
            - ration/logistics support
```

Notes:
- This is explicitly **crude** and subject to later refinement (testing,
  guild formation, formal certifications).

### 6.2 SURVEY_MISSION_V0

**Purpose:** Begin mapping the environment and hazards without losing crews or
creating rogue expedition factions.

```text
PROTOCOL: SURVEY_MISSION_V0

WHEN
  task_type == "environmental_scout"

THEN
  - STEP 1: Assign at least 3-person teams (no solo missions).
  - STEP 2: Equip teams with basic suit + comms appropriate to expected risk.
  - STEP 3: Mandate ROUTE_LOG during mission and FINDINGS_LOG on return.
  - STEP 4: Forbid independent water or infrastructure decisions in the field;
            all water-related findings are sent to COUNCIL_REVIEW_V0.
```

Notes:
- This protocol seeds **structured exploration** and episode capture rather
  than uncoordinated wandering.
- Later expansions may differentiate survey types (industrial, biological,
  structural).

---

## 7. Dispute Triage & Violence Containment

### 7.1 DISPUTE_TRIAGE_V0

**Purpose:** Provide a simple default pattern for handling early disputes
without establishing full courts or detailed law codes.

```text
PROTOCOL: DISPUTE_TRIAGE_V0

WHEN
  conflict IN ('inter_pod', 'intra_pod')
  AND severity IN ('verbal', 'minor_physical')

THEN
  - STEP 1: Any pod may call for COUNCIL_MEDIATOR.
  - STEP 2: Suspend ration or task decisions about the contested resource.
  - STEP 3: Hear both sides in presence of a neutral pod representative
            if possible.
  - STEP 4: Issue temporary ruling valid for 24 hours.
  - STEP 5: Log the case in DISPUTE_LEDGER for future pattern analysis.
```

Notes:
- Serious violence (weapons, severe injury) may be treated with ad hoc
  responses until more formal LAW protocols are developed.
- The key is to establish **habits of deferral and logging**, not perfect
  justice at this stage.

---

## 8. Foundational Norm / Law Frame

### 8.1 COUNCIL_FRAME_V0

**Purpose:** Provide a minimal normative frame that other protocols and pod
norms should respect. This is a proto-constitutional seed, not a full legal
code.

**Informal principles (posted summary):**
- **P1:** The Well and critical infrastructure are common assets; no pod may
  seize them for exclusive control.
- **P2:** Basic survival (water, food, safe bunk) takes precedence over status
  or luxury disputes.
- **P3:** Violence is a last resort; disputes should pass through
  DISPUTE_TRIAGE_V0 where possible.
- **P4:** Council roles are provisional and revisitable once basic survival
  is stable.

**Formal frame behavior:**

```text
PROTOCOL: COUNCIL_FRAME_V0

WHEN
  any protocol is proposed
  OR a pod practice appears to conflict with principles P1–P4

THEN
  - STEP 1: Council convenes to review the conflict.
  - STEP 2: Temporarily suspend practices that clearly violate P1–P4.
  - STEP 3: Amend or affirm relevant protocols (e.g. ration, pod, work rules).
  - STEP 4: Post updated summary so pods understand the change.
```

Notes:
- This protocol explicitly gives the Founding Council **revision authority**
  but also acknowledges its provisional nature.
- Later LAW documents may formalize or replace this frame with charters,
  codes, and succession rules.

---

## 9. Founding Records & Episode Capture

### 9.1 FOUNDING_RECORDS_V0

**Purpose:** Ensure that the founding period leaves a usable memory trail for
later learning and institutionalization.

```text
PROTOCOL: FOUNDING_RECORDS_V0

WHEN
  any council decision, major incident, or life-critical operation occurs

THEN
  - STEP 1: Log a minimal episode with fields:
            (what, who, where, when, why, outcome)
  - STEP 2: Tag the episode with a domain:
            (ration, housing, survey, dispute, medical, security, etc.)
  - STEP 3: Store in COUNCIL_JOURNAL (the seed archive).
```

Notes:
- This protocol connects directly to the Episode Management System
  (D-MEMORY-0001).
- Early logs may be incomplete or messy; the priority is to **start the
  habit** of recording meaningful events.

---

## 10. Evolution & Replacement

The protocols in this stack are **version 0**. They are expected to be:
- stress-tested in the first weeks and months,
- criticized by pods, task forces, and later guilds,
- gradually refined, split, or replaced by more specialized LAW documents.

Patterns of failures and disputes logged via FOUNDING_RECORDS_V0 and other
ledgers will inform:
- later **LAW** documents (formal codes, courts, punishments),
- **MEMORY** expansions (structured archives, protocol DSL tooling),
- and **RUNTIME** adjustments (how founding choices shape Golden Age
  trajectories).

D-LAW-0011 should be treated as the **initial scaffolding**: the minimal,
rational set of protocols a competent Founding Council might adopt to bring
order out of the wakeup chaos, while leaving enough flexibility for the city
to grow, specialize, and eventually decay under new pressures.
