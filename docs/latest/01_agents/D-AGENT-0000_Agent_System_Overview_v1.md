---
title: Agent_System_Overview_v1
doc_id: D-AGENT-0000
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-RUNTIME-0001   # Simulation_Timebase
  - D-AGENT-0001     # Agent_Core_Schema_v0
  - D-AGENT-0002     # Agent_Decision_Rule_v0
  - D-AGENT-0003     # Agent_Drives_v0
  - D-AGENT-0004     # Agent_Action_API_v0
  - D-AGENT-0005     # Perception_and_Memory_v0
  - D-AGENT-0006     # Skills_and_Learning_v0
  - D-AGENT-0007     # Rumor_and_Gossip_Dynamics_v0
---

# 1. Purpose

This document is the **index and conceptual overview** for the Dosadi **Agent v1** system.

It:

- Describes the **layered architecture** of agents (data → drives → decisions → actions → learning).
- Summarizes what each D-AGENT-000x document is responsible for.
- Clarifies relationships to **legacy agent documents** (now `D-AGENT-0101`–`D-AGENT-0107`).
- Provides an **implementation checklist** to guide Codex and future-you when wiring code.

This is the “you are here” map for the agent pillar.

---

# 2. High-Level Architecture

Agents are modeled as **pressure-driven decision-makers** embedded in a hostile world:

1. **Core schema** defines what an agent *is* (state, attributes, drives, social ties).
2. **Drives** convert world + internal state into **pressures** (hunger, fear, ambition, loyalty, etc.).
3. **Decision rule** maps pressures + beliefs into a **chosen action** each tick.
4. **Action API** defines what agents can *do* (move, work, talk, observe, report…).
5. **Perception & memory** define what an agent *knows* and *remembers* about the world.
6. **Skills & learning** define how agents get **better** (or stagnate) through practice.
7. **Rumor & gossip** define how **information flows** through the social graph.

Each simulation tick (per D-RUNTIME-0001):

1. World produces a **perception snapshot** for each agent.
2. Agent **updates memory** and **drives**.
3. Decision rule selects an **action** using drives, memory, skills, and rumors.
4. World applies action → **state changes** (positions, resources, statuses).
5. Agent receives **outcomes**, updating:
   - Memory (beliefs about agents/facilities, rumor credibility),
   - Skills (XP & rank),
   - Social ties (affinity, suspicion, threat).

---

# 3. Document Map (0000–0007)

## 3.1 Core v1 set

- **D-AGENT-0001 — Agent_Core_Schema_v0**  
  Defines the **Agent data model**:
  - Identity & static tags (role, faction, caste).
  - Physical state (health, fatigue, hunger, thirst).
  - Psychological & social state (fear, ambition, loyalty, discipline).
  - Inventory/suits (lightweight hooks to the suits/health pillars).
  - Embedded sub-objects:
    - `drives`
    - `memory`
    - `skills`
    - `rumor_policy` (light, for 0007)

- **D-AGENT-0002 — Agent_Decision_Rule_v0**  
  Specifies the **decision-making pipeline**:
  - How drives are read and normalized.
  - How candidate actions are enumerated (from Action API & context).
  - How expected value (EV) is computed per action, including:
    - Survival needs (food, water, safety),
    - Social risks & opportunities,
    - Long-term goals (status, safety, loyalty payoffs).
  - How a single action is sampled/selected each tick.

- **D-AGENT-0003 — Agent_Drives_v0**  
  Defines the **drives system**:
  - Minimal drive set (e.g. hunger, thirst, fatigue, fear, ambition, loyalty, curiosity).
  - How drives are updated from:
    - Physical state (health, nutrition, rest),
    - Environmental conditions (ward danger, enforcement presence),
    - Social state (threats, betrayals, favors).
  - How drives influence:
    - Action priorities (e.g. eat vs work vs flee vs gossip),
    - Thresholds and risk tolerance.

- **D-AGENT-0004 — Agent_Action_API_v0**  
  Defines the **canonical action vocabulary**:
  - Core verbs:
    - `MOVE_TO_FACILITY`
    - `PERFORM_JOB`
    - `OBSERVE_AREA`
    - `TALK_TO_AGENT`
    - `REQUEST_SERVICE`
    - `REPORT_TO_AUTHORITY`
    - (plus future: stealth moves, medical actions, exo-suit ops)
  - Input/output shapes for each:
    - Required context (target ids, location, mode),
    - Expected side effects (resource deltas, social changes, flags).

- **D-AGENT-0005 — Perception_and_Memory_v0**  
  Defines how agents **see & remember**:
  - **PerceptionSnapshot**, **VisibleAgent**, **VisibleFacility** structures.
  - `Memory` container:
    - `known_agents: Dict[str, AgentBelief]`
    - `known_facilities: Dict[str, FacilityBelief]`
    - `rumors: Dict[str, Rumor]`
  - Methods:
    - `update_from_observation(snapshot)`
    - `update_from_conversation(event)`
    - `adjust_suspicion/affinity/threat`
    - `decay(current_tick, params)`
    - Read-side helpers (e.g. `get_safe_facilities`, `get_high_credibility_rumors`).
  - Skeleton implementation: **D-AGENT-0005-SKEL** (`memory.py` proto).

- **D-AGENT-0006 — Skills_and_Learning_v0**  
  Defines **skills, checks, and XP**:
  - Static `SkillDefinition` registry (`perception`, `streetwise`, `conversation`,
    `intimidation`, `labor_kitchen`, `labor_industrial`, `bureaucracy`,
    `stealth`, `medicine_basic`, `weapon_handling`).
  - Per-agent `SkillState` and `SkillSet`.
  - `SkillCheckContext` and `perform_skill_check(ctx, rng)`:
    - Combines skill rank + attributes + difficulty into `p_success`.
  - XP & progression:
    - Rank-up cost tables by difficulty tier,
    - `apply_skill_xp` and `compute_xp_gain_from_check`.
  - Skeleton implementation: **D-AGENT-0006-SKEL** (`skills.py` proto).

- **D-AGENT-0007 — Rumor_and_Gossip_Dynamics_v0**  
  Turns **talk into a strategic system**:
  - Structured `Rumor.payload` (category, subtype, targets, payoff).
  - `SpaceProfile` for rumor-safe vs unsafe spaces.
  - Per-agent `RumorPolicy` thresholds (when to act/forward).
  - Rumor loops:
    - Speaker chooses whether/what to share,
    - Listener updates beliefs and rumor credibility,
    - Later, agents act or forward based on drives & policy.
  - Strong links to:
    - `Memory.rumors` in 0005,
    - `Skills` (`conversation`, `streetwise`, `perception`) in 0006.
  - Skeleton implementation: **D-AGENT-0007-SKEL** (`rumors.py` proto).

---

# 4. Tick-Level Flow (Conceptual)

For a **single agent** on a single tick:

1. **Perception**
   - World produces `PerceptionSnapshot` based on location, visibility, etc.
   - Agent calls `memory.update_from_observation(snapshot)`.

2. **Drive update**
   - Agent reads:
     - Internal state (health, hunger, thirst, fatigue),
     - Memory (recent threats, safe facilities, opportunities),
   - Drives update (0003):
     - `hunger`, `thirst`, `fatigue` from body/health.
     - `fear` from threat signals, enforcement, recent harm.
     - `ambition` from opportunities, boredom, social position.
     - `loyalty` from faction ties, favors, moral inheritance.

3. **Candidate actions**
   - Decision rule (0002) constructs a small set of candidates from 0004:
     - e.g. `PERFORM_JOB` at a nearby facility,
     - `MOVE_TO_FACILITY` (safer bunkhouse),
     - `TALK_TO_AGENT` (rumor/ask for info),
     - `OBSERVE_AREA` (check enforcement before moving).

4. **Value estimation**
   - For each candidate:
     - Estimate **short-term survival payoff** (food, water, safety).
     - Estimate **long-term payoff** (status, loyalty, skill growth).
     - Use skills (0006) to estimate `p_success` of relevant checks.
     - Incorporate rumors (0007) if they suggest threat/opportunity.

5. **Action selection**
   - Decision rule picks the action with highest EV (plus optional noise, tie-breaking).
   - Action is sent through the **Action API** (0004) to the world.

6. **Outcome**
   - World applies the action, updating:
     - Resources, positions, health, flags (e.g. detained, wounded).
     - Possibly generating events for other agents (new jobs, crackdowns, etc.).

7. **Post-outcome updates**
   - Agent:
     - Updates skills via `apply_skill_xp` (0006).
     - Updates memory for:
       - Facility outcomes (`note_facility_visit`),
       - Rumor confirmation/contradiction (0005 + 0007).
     - Adjusts social beliefs (suspicion/affinity) based on behavior observed.

Repeat next tick.

---

# 5. Implementation Checklist (Code-Level)

A recommended minimal code layout corresponding to these docs:

- `runtime/timebase.py`  
  - Implements D-RUNTIME-0001 (ticks per second, scheduling).

- `agents/core.py`  
  - Implements D-AGENT-0001 core schema:
    - `Agent` dataclass with:
      - `drives`, `memory`, `skills`, `rumor_policy`, `attributes`, etc.

- `agents/drives.py`  
  - Implements D-AGENT-0003:
    - Drive container, update functions,
    - Hooks to health/suits/environment.

- `agents/decision.py`  
  - Implements D-AGENT-0002:
    - `evaluate_candidate_actions(agent, world, tick)`,
    - `choose_action(agent, world, tick)`.

- `agents/actions.py`  
  - Implements D-AGENT-0004:
    - Action structs/enums + handlers,
    - Integration with world state.

- `agents/memory.py`  
  - From D-AGENT-0005-SKEL:
    - `PerceptionSnapshot`, `Memory`, `AgentBelief`, `FacilityBelief`, `Rumor`.

- `agents/skills.py`  
  - From D-AGENT-0006-SKEL:
    - `SkillDefinition`, `SkillSet`, `SkillState`, `perform_skill_check`, XP logic.

- `agents/rumors.py`  
  - From D-AGENT-0007-SKEL:
    - `SpaceProfile`, `RumorPolicy`,
    - `evaluate_rumor_share`, `speaker_choose_rumor`, `listener_update_from_rumor`.

This overview (0000) should be the **first doc Codex reads** when reasoning about the agent pillar, then follow the dependency chain into each more detailed doc.

---

# 6. Relationship to Legacy Agent Docs (0101–0107)

Earlier agent documents have been **renumbered** to avoid conflicts:

- **Legacy / exploratory designs** are now:
  - `D-AGENT-0101` … `D-AGENT-0107`

These may contain:

- Deeper **tier-2 agent concepts**,
- Alternative schemas or experimental mechanics,
- Ideas that might later shape v2+ agents.

For now:

- **D-AGENT-0000–0007 are canonical for Agent v1.**
- Legacy documents 0101–0107 should be treated as:
  - **Idea reserves** and references,
  - Not authoritative for the implementation Codex should build today.
- When a conflict arises:
  - **000x wins over 010x**, unless explicitly overridden in a future ADR.

A future ADR (e.g. `D-AGENT-0090` “Agent v1 vs Legacy Tier-2”) may formally record how 0101–0107 are to be folded into v2 designs.

---

# 7. Next Steps

Short-term recommended next moves:

1. **Sanity pass on document headers**
   - Ensure all existing agent docs in `docs/latest/01_agents` use:
     - Updated doc_ids (0000–0007, 0101–0107),
     - Correct `depends_on` pointing into `D-RUNTIME-0001` and siblings.

2. **Minimal working slice**
   - Implement a very simple:
     - `Agent`,
     - `Memory`,
     - `Skills`,
     - `Decision rule` that can:
       - Observe,
       - Decide between `PERFORM_JOB` vs `OBSERVE_AREA` vs `MOVE_TO_FACILITY`,
       - Update skills and beliefs.

3. **Early rumor testbed**
   - Add 1–2 rumor patterns:
     - “Crackdown soon at Facility X”
     - “Job opportunity at Facility Y”
   - Watch agents:
     - Change routes,
     - Change work targets,
     - Adjust trust in speakers as rumors resolve TRUE/FALSE.

This document should remain small and stable; changes here should reflect real architectural shifts, not fine-tuning of sub-doc details.
