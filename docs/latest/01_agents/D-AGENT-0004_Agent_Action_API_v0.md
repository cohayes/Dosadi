---
title: Agent_Action_API_v0
doc_id: D-AGENT-0004
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0002   # Agent_Decision_Rule_v0
  - D-AGENT-0003   # Drive_Facility_Impact_Matrix_v0
  - D-RUNTIME-0001 # Simulation_Timebase
---

# 1. Purpose

This document defines a **minimal, stable Agent Action API** for the Dosadi simulation.

It specifies:

- The **set of actions** an agent may attempt during a simulation tick.
- The **data structures** used to represent actions.
- The **preconditions** for each action.
- The **effects** each action has on:
  - The agent’s internal state (`body`, `drives`, `status`, `memory`),
  - The environment (`facilities`, `queues`, `job_slots`, etc.).

This API is intended as the main boundary between:

- The **decision rule** (D-AGENT-0002), which *selects* an action.
- The **runtime/environment** (D-RUNTIME-0001+), which *applies* that action and updates the world.

Codex should implement this document as `actions.py` (or equivalent) and use it to wire agents into the simulation loop.

---

# 2. Design Constraints

1. **Small, composable action set**  
   - Prefer a small number of general, composable actions (e.g. `MOVE_TO_FACILITY`) over many hyper-specific ones.
   - New actions should extend this API, not replace it.

2. **Clear contracts**  
   - Each action has:
     - **Parameters** (inputs),
     - **Preconditions** (when it is legal),
     - **Effects** (what changes),
     - **Drive hooks** (typical drives affected, linking to D-AGENT-0003).

3. **Deterministic given RNG**  
   - Apply functions accept an `rng` object; stochastic behavior must be explicitly seeded via the runtime.

4. **Graceful failure**  
   - Illegal actions **must not corrupt world state**.
   - The environment either:
     - Rejects the action and logs it, or
     - Downgrades to a safe fallback (e.g. `IDLE`) and optionally adjusts drives (e.g. stress).

5. **Agent schema alignment**  
   - Preconditions and effects must only reference fields defined in:
     - `D-AGENT-0001_Agent_Core_Schema_v0`
     - `D-AGENT-0003_Drive_Facility_Impact_Matrix_v0`

---

# 3. Data Structures

These are the canonical data structures Codex should implement.

## 3.1 ActionType enum

```python
import enum

class ActionType(enum.Enum):
    IDLE = "IDLE"
    MOVE_TO_FACILITY = "MOVE_TO_FACILITY"
    MOVE_WITHIN_FACILITY = "MOVE_WITHIN_FACILITY"
    JOIN_QUEUE = "JOIN_QUEUE"
    LEAVE_QUEUE = "LEAVE_QUEUE"
    REQUEST_SERVICE = "REQUEST_SERVICE"
    EAT_AT_FACILITY = "EAT_AT_FACILITY"
    SLEEP_AT_FACILITY = "SLEEP_AT_FACILITY"
    TALK_TO_AGENT = "TALK_TO_AGENT"
    OBSERVE_AREA = "OBSERVE_AREA"
    PERFORM_JOB = "PERFORM_JOB"
    REPORT_TO_AUTHORITY = "REPORT_TO_AUTHORITY"
```

> **Note:** This is a minimal v0 set, biased toward soup-kitchen / bunkhouse / work-floor environments.

## 3.2 Action dataclass

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class Action:
    type: ActionType
    target_id: Optional[str] = None
    facility_id: Optional[str] = None
    zone_id: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
```

### Semantics

- `target_id`  
  - Generic identifier for another agent, job slot, or authority figure.
- `facility_id`  
  - Identifier for a facility (soup kitchen, bunkhouse, clinic, garrison office, factory, etc.).
- `zone_id`  
  - Optional sub-area inside a facility (queue area, mess line, sleeping bay, waiting room).
- `params`  
  - Free-form dict for action-specific parameters:
    - `topic_token` for social actions,
    - `service_type` for requests,
    - `job_slot_id`, `report_token`, etc.

---

# 4. Action Lifecycle in the Simulation Loop

## 4.1 Agent decision step

The decision rule defined in D-AGENT-0002 must conform to:

```python
def choose_action(agent, world, rng) -> Action:
    """
    Selects one Action for this agent for the current tick.

    - Reads agent.body, agent.drives, agent.status, agent.memory.
    - Reads local world state (nearby facilities, queues, agents).
    - Produces a single Action instance.
    """
```

## 4.2 Environment application step

The runtime / environment must provide:

```python
def apply_action(agent, world, action: Action, rng) -> None:
    """
    Applies the given Action to (agent, world).

    - Checks preconditions for the given action.type.
    - If preconditions fail, handles error (no-op or fallback).
    - If preconditions pass, mutates agent and world per EFFECT spec.
    """
```

## 4.3 Per-tick sequence (per agent)

At each simulation tick:

1. `action = choose_action(agent, world, rng)`
2. `apply_action(agent, world, action, rng)`
3. Runtime updates global counters, logs, and any post-step hooks (e.g. decay, global events).

---

# 5. Core Action Catalog (v0)

For each action type:

- **Code**: `ActionType` enum value.
- **Description**: Narrative summary.
- **Parameters**: Fields used on the `Action` object.
- **Preconditions**: Required state for legality.
- **Effects**: Deterministic updates to agent/world.
- **Drive Hooks**: Drives typically satisfied or worsened.

Preconditions/effects are expressed in a simple pattern-esque pseudocode, referencing the agent/world schema.

## 5.1 IDLE

**Code:** `ActionType.IDLE`  

**Description:**  
Agent performs no deliberate external action this tick (loiter, wait, think). Used as a safe fallback when no valid action exists.

**Parameters:**  
- None.

**Preconditions:**  
- Always allowed.

**Effects (example):**
```text
EFFECT:
  # No spatial change
  agent.status.current_action := "IDLE"

  # Minor passive changes may be applied by runtime, not this API:
  #   - hunger, thirst, fatigue increase per tick
  #   - possible very small stress decay if in safe environment
```

**Drive Hooks:**
- Slight worsening of survival drives (hunger, thirst, fatigue) via global tick decay.
- May marginally reduce stress if in a safe, non-threatening facility (runtime-level rule).

---

## 5.2 MOVE_TO_FACILITY

**Code:** `ActionType.MOVE_TO_FACILITY`  

**Description:**  
Agent travels from current location to a target facility (another building or major node).

**Parameters:**  
- `facility_id` (required)

**Preconditions:**
```text
PRE:
  world.facility_exists(facility_id)
  AND world.path_exists(agent.status.location_id, facility_id)
  AND NOT agent.status.incapacitated
  AND NOT agent.status.arrested
```

**Effects (example):**
```text
EFFECT:
  agent.status.location_id := facility_id
  agent.status.zone_id := world.facilities[facility_id].default_zone_id
  agent.status.current_action := "ARRIVED"
  agent.memory.last_facility_visit[facility_id] := world.tick
```

**Drive Hooks:**
- Often chosen to reduce drives via access to services (food, sleep, clinic, work).
- May temporarily increase fatigue and/or thirst depending on travel distance (runtime).

---

## 5.3 MOVE_WITHIN_FACILITY

**Code:** `ActionType.MOVE_WITHIN_FACILITY`  

**Description:**  
Agent moves between zones inside the current facility (e.g. lobby → queue area → dining area).

**Parameters:**  
- `facility_id` (optional; defaults to `agent.status.location_id`)
- `zone_id` (required)

**Preconditions:**
```text
PRE:
  world.facility_exists(current_facility_id := facility_id or agent.status.location_id)
  AND agent.status.location_id == current_facility_id
  AND world.zone_exists(current_facility_id, zone_id)
  AND NOT agent.status.incapacitated
```

**Effects:**
```text
EFFECT:
  agent.status.zone_id := zone_id
  agent.status.current_action := "MOVING_WITHIN"
```

**Drive Hooks:**
- Neutral directly; used to position agent to perform subsequent actions (join queue, eat, sleep).
- May incur minor fatigue over time if movement is repeated.

---

## 5.4 JOIN_QUEUE

**Code:** `ActionType.JOIN_QUEUE`  

**Description:**  
Agent joins a service queue at the current facility (e.g. meal line, bed assignment line).

**Parameters:**  
- `facility_id` (optional; defaults to `agent.status.location_id`)
- `params["queue_type"]` (optional; e.g. `"MEAL"`, `"BED"`, `"CLINIC"`)

**Preconditions:**
```text
PRE:
  world.facility_exists(current_facility_id)
  AND agent.status.location_id == current_facility_id
  AND world.facility_has_queue(current_facility_id, queue_type)
  AND NOT agent.status.in_queue
  AND NOT agent.status.incapacitated
```

**Effects:**
```text
EFFECT:
  world.queues[current_facility_id, queue_type].append(agent.id)
  agent.status.in_queue := True
  agent.status.queue_facility_id := current_facility_id
  agent.status.queue_type := queue_type
  agent.status.current_action := "IN_QUEUE"
```

**Drive Hooks:**
- Supports future satisfaction of hunger, shelter, health, or other needs.
- Over time in queue, stress can increase or decrease depending on environment and social factors.

---

## 5.5 LEAVE_QUEUE

**Code:** `ActionType.LEAVE_QUEUE`  

**Description:**  
Agent voluntarily leaves their current queue (abandoning position).

**Parameters:**  
- None (uses `agent.status.queue_*` fields).

**Preconditions:**
```text
PRE:
  agent.status.in_queue == True
```

**Effects:**
```text
EFFECT:
  world.queues[agent.status.queue_facility_id, agent.status.queue_type].remove(agent.id)
  agent.status.in_queue := False
  agent.status.queue_facility_id := None
  agent.status.queue_type := None
  agent.status.current_action := "IDLE"
```

**Drive Hooks:**
- May worsen hunger/thirst/shelter drives if leaving necessary service.
- May slightly reduce stress if queue was dangerous or threatening.

---

## 5.6 REQUEST_SERVICE

**Code:** `ActionType.REQUEST_SERVICE`  

**Description:**  
Agent attempts to obtain a service at a facility, typically after reaching the head of a queue or when allowed walk-up service.

**Parameters:**  
- `facility_id` (optional; defaults to `agent.status.location_id`)
- `params["service_type"]` (required; e.g. `"MEAL"`, `"BED"`, `"MEDICAL"`, `"JOB_ASSIGNMENT"`)

**Preconditions (generic):**
```text
PRE:
  world.facility_exists(current_facility_id)
  AND agent.status.location_id == current_facility_id
  AND world.facility_offers_service(current_facility_id, service_type)
  AND NOT agent.status.incapacitated
  # Additional facility-specific rules may apply (payment, reputation, permits).
```

**Effects (generic):**
```text
EFFECT:
  # Delegated to facility-specific handler:
  world.facilities[current_facility_id].process_service_request(agent, service_type, rng)

  # Typical outcomes:
  #   - allocate meal (EAT_AT_FACILITY),
  #   - allocate bed (SLEEP_AT_FACILITY),
  #   - schedule clinic treatment,
  #   - assign job slot, etc.
```

**Drive Hooks:**
- Indirect: this is usually a wrapper that leads to concrete survival-improving actions (eat, sleep, heal, earn).
- Success typically reduces one or more drives; denial may increase frustration/stress.

---

## 5.7 EAT_AT_FACILITY

**Code:** `ActionType.EAT_AT_FACILITY`  

**Description:**  
Agent consumes a meal provided by the facility, restoring hunger/energy, possibly at the cost of currency, favors, or obligations.

**Parameters:**  
- `facility_id` (optional; defaults to `agent.status.location_id`)
- `params["meal_quality"]` (optional; defaults by facility; affects magnitude of effect and risk)

**Preconditions:**
```text
PRE:
  world.facility_exists(current_facility_id)
  AND agent.status.location_id == current_facility_id
  AND world.facility_can_serve_meal(current_facility_id, agent)
  AND NOT agent.status.incapacitated
```

**Effects (example):**
```text
EFFECT:
  # Nutrition
  agent.body.hunger := max(agent.body.hunger - meal_hunger_reduction, 0)
  agent.body.energy := min(agent.body.energy + meal_energy_gain, agent.body.energy_max)

  # Resources
  agent.inventory.credits := agent.inventory.credits - meal_cost  # if applicable

  # Risks (runtime-level decisions)
  #   - possible food poisoning risk, loyalty adjustments, etc.

  agent.status.current_action := "EATING"
```

**Drive Hooks:**
- Directly reduces hunger and (often) fatigue.
- May impact loyalty or trust toward the facility operator if consistently fed or abused.

---

## 5.8 SLEEP_AT_FACILITY

**Code:** `ActionType.SLEEP_AT_FACILITY`  

**Description:**  
Agent uses a sleeping slot (bed, pad, corner) at a facility (bunkhouse, shelter, cell).

**Parameters:**  
- `facility_id` (optional; defaults to `agent.status.location_id`)
- `params["duration_ticks"]` (optional; default from runtime, e.g. “night” phase)

**Preconditions:**
```text
PRE:
  world.facility_exists(current_facility_id)
  AND agent.status.location_id == current_facility_id
  AND world.facility_can_allocate_sleep_slot(current_facility_id, agent)
  AND NOT agent.status.incapacitated
  AND NOT agent.status.on_duty  # if relevant
```

**Effects (example, applied over multiple ticks):**
```text
EFFECT:
  # On allocation:
  agent.status.current_action := "SLEEPING"
  agent.status.sleep_facility_id := current_facility_id

  # Over ticks (runtime responsibility):
  #   - decrease fatigue
  #   - modestly improve stress
  #   - small adjustments to drives based on safety, crowding, etc.
```

**Drive Hooks:**
- Direct improvement of fatigue/energy.
- Stress changes depending on environment (safe bunkhouse vs dangerous flop-house).

---

## 5.9 TALK_TO_AGENT

**Code:** `ActionType.TALK_TO_AGENT`  

**Description:**  
Agent engages in direct conversation with another agent, exchanging information, threats, offers, or gossip.

**Parameters:**  
- `target_id` (required)
- `params["topic_token"]` (optional; describes content theme: `"RUMOR"`, `"TRADE"`, `"THREAT"`, `"LOYALTY_TEST"`, etc.)

**Preconditions:**
```text
PRE:
  world.agent_exists(target_id)
  AND world.agents[target_id].status.location_id == agent.status.location_id
  AND world.agents[target_id].status.zone_id == agent.status.zone_id
  AND NOT agent.status.incapacitated
```

**Effects (generic):**
```text
EFFECT:
  world.process_conversation(
      speaker=agent,
      listener=world.agents[target_id],
      topic_token=params.get("topic_token"),
      rng=rng
  )

  agent.status.current_action := "TALKING"
```

**Drive Hooks:**
- Social drives: affiliation, belonging, fear, ambition, loyalty recalibration.
- May alter memory (D-AGENT-0005) with new information tokens or trust updates.

---

## 5.10 OBSERVE_AREA

**Code:** `ActionType.OBSERVE_AREA`  

**Description:**  
Agent deliberately scans its surroundings to update perception and memory (who is present, which facilities/zones are active, visible enforcement, etc.).

**Parameters:**  
- `params["radius"]` (optional; default perception radius)
- `params["mode"]` (optional; e.g. `"CASUAL"`, `"SUSPICIOUS"`, `"TARGET_SEARCH"`)

**Preconditions:**
```text
PRE:
  NOT agent.status.incapacitated
```

**Effects (generic):**
```text
EFFECT:
  visible_state = world.get_visible_state(agent, radius, mode)
  agent.memory.update_from_observation(visible_state, world.tick)
  agent.status.current_action := "OBSERVING"
```

**Drive Hooks:**
- May lower anxiety if threats not present.
- May raise stress if threats or high-risk individuals detected.
- Strong link to perception & suspicion mechanics (future D-AGENT-0005).

---

## 5.11 PERFORM_JOB

**Code:** `ActionType.PERFORM_JOB`  

**Description:**  
Agent performs labor or duty at a specific job slot (kitchen, factory, patrol, accounting, etc.), usually to earn resources, status, or fulfill obligations.

**Parameters:**  
- `params["job_slot_id"]` (required)

**Preconditions:**
```text
PRE:
  world.job_slot_exists(job_slot_id)
  AND world.job_slot_open_to_agent(job_slot_id, agent)
  AND NOT agent.status.incapacitated
  AND agent.status.location_id == world.job_slots[job_slot_id].facility_id
```

**Effects (example):**
```text
EFFECT:
  world.process_job_tick(agent, job_slot_id, rng)

  # Typical results:
  #   - credits or rations gained
  #   - fatigue increased
  #   - skills incremented (future D-AGENT-0006)
  #   - loyalty to employer adjusted
  agent.status.current_action := "WORKING"
```

**Drive Hooks:**
- Improves economic/security drives (credits, rations, long-term survival).
- Increases fatigue; can affect stress depending on job conditions.

---

## 5.12 REPORT_TO_AUTHORITY

**Code:** `ActionType.REPORT_TO_AUTHORITY`  

**Description:**  
Agent shares information with an authority-aligned actor (militia, clerk, overseer) to gain favor, protection, or other benefits, at potential social cost.

**Parameters:**  
- `target_id` (required; authority figure or office)
- `params["report_token"]` (optional; reference to information being reported)
- `params["urgency"]` (optional; e.g. `"LOW"`, `"HIGH"`)

**Preconditions:**
```text
PRE:
  world.agent_exists(target_id) OR world.authority_office_exists(target_id)
  AND agent.status.location_id == world.get_location_of_authority(target_id)
  AND NOT agent.status.incapacitated
```

**Effects (generic):**
```text
EFFECT:
  world.process_authority_report(
      reporter=agent,
      authority_target=target_id,
      report_token=params.get("report_token"),
      rng=rng
  )

  agent.status.current_action := "REPORTING"
```

**Drive Hooks:**
- Potential long-term gains in protection, status, and resources.
- Possible negative impacts on:
  - Social standing with other factions,
  - Internal stress/loyalty conflicts (as defined in future social logic).

---

# 6. Error Handling & Illegal Actions

When `apply_action` is called with an illegal or partially illegal action (failed preconditions), the environment must:

1. **Log the failure** (for debugging/analytics), including:
   - `agent.id`, `action.type`, and failing preconditions.
2. **Fallback behavior**:
   - Default: convert to `IDLE` for this tick.
   - Optional: apply a small **stress bump** to represent frustration or confusion.

Suggested pattern:

```python
def apply_action(agent, world, action: Action, rng) -> None:
    if not preconditions_hold(agent, world, action):
        world.log_invalid_action(agent, action)
        # Fallback
        agent.status.current_action = "IDLE"
        agent.drives.stress = min(
            agent.drives.stress + world.constants.STRESS_INVALID_ACTION,
            agent.drives.stress_max
        )
        return

    # ... proceed with EFFECT logic ...
```

---

# 7. Roadmap & Extensions

Future documents will extend this API without breaking it:

- **D-AGENT-0005_Perception_and_Memory_v0**  
  - Formalizes `agent.memory` structure and how `OBSERVE_AREA` and `TALK_TO_AGENT` write into it.
  - Introduces suspicion/probability tracking for other agents/factions.

- **D-AGENT-0006_Skills_and_Learning_v0**  
  - Attaches skill checks and learning curves to actions like `PERFORM_JOB`, `REPORT_TO_AUTHORITY`, and complex social actions.

- **D-RUNTIME-0002_Agent_Step_Loop_v0**  
  - Codifies the per-tick order of:
    - decay,
    - decision,
    - action application,
    - logging,
    - and cross-agent interactions.

The v0 Action API defined here should remain stable enough that Codex-generated `actions.py` can be extended, not replaced, as the Dosadi simulation matures.
