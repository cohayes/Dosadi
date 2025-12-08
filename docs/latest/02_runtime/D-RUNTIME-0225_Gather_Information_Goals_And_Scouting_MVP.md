---
title: Gather_Information_Goals_And_Scouting_MVP
doc_id: D-RUNTIME-0225
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-08
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0213   # Work_Detail_Behaviors_MVP_Scout_And_Inventory
  - D-RUNTIME-0214   # Council_Metrics_And_Staffing_Response_MVP
  - D-RUNTIME-0218   # Hydration_And_Water_Access_MVP
  - D-SCEN-0002      # Founding_Wakeup_Spec
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
  - D-AGENT-0023     # Agent_Goal_System_v0
  - D-AGENT-0024     # Agent_Decision_Loop_v0
  - D-AGENT-0025     # Groups_And_Councils_MVP
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
  - D-MEMORY-0205    # Place_Belief_Updates_From_Queue_Episodes_MVP_v0
  - D-MEMORY-0210    # Episode_Verbs_For_Initial_Work_Details_MVP
---

# 02_runtime · Gather Information Goals & Scouting (MVP) — D-RUNTIME-0225

## 1. Purpose & scope

In the Founding Wakeup MVP, we already have:

- pod meetings and proto-council formation,
- council metrics over corridor hazards,
- protocol authoring for dangerous corridors,
- success checks for:
  - `proto_council_formed`,
  - `protocol_authored`,
  - `gather_information_goals`,
  - `protocol_adoption`,
  - `hazard_reduction`.

In observed runs, `gather_information_goals`, `protocol_adoption`, and `hazard_reduction` are failing, even though:

- hazard metrics correctly detect dangerous corridors, and
- proto-councils meet and can author protocols.

This document defines the missing runtime loop:

dangerous corridors → council gather-information group goal → projected scout goals → scouting behaviour → episodes & beliefs → scenario success check.

Scope for this MVP:

- Define group-level and agent-level `GATHER_INFORMATION` goals.
- Define council triggers for creating gather-information goals, based on hazard metrics.
- Define projection of group goals onto agent-level scout goals.
- Define minimal behaviour for agents that are pursuing gather-information goals, re-using `SCOUT_INTERIOR`.
- Define how the scenario checks whether gather-information goals have been meaningfully used.

---

## 2. Entities & references

This document assumes the following exist:

- `Goal`, `GoalType`, `GoalStatus`, `GoalOrigin` as in D-AGENT-0023.
- `AgentState` and `GroupState` (D-AGENT-0020, D-AGENT-0022, D-AGENT-0025).
- Council hazard metrics and dangerous corridor detection (D-RUNTIME-0214).
- Work details and `WorkDetailType.SCOUT_INTERIOR` (D-RUNTIME-0213).
- Episode and belief machinery, including place beliefs for corridors (D-MEMORY-*).
- Founding Wakeup scenario spec with `min_information_goals` and `require_hazard_reduction` (D-SCEN-0002).

This document does not re-specify those; it only adds the glue and contracts needed for gather-information goals.

---

## 3. Goal types & metadata

### 3.1 GoalType.GATHER_INFORMATION

We introduce or confirm `GoalType.GATHER_INFORMATION`. It can be used for:

- group-level goals whose owner id is a group id, e.g. `group:council:alpha`,
- agent-level goals whose owner id is an agent id, e.g. `agent:17`.

Semantic intent:

- Group-level: represents a collective decision that more information is needed about hazards on specific corridors.
- Agent-level: represents a specific assignment to scout certain corridors, collect risk information, and feed episodes into memory.

### 3.2 Required metadata

Both group and agent goals carry metadata in `Goal.metadata`.

For group-level `GATHER_INFORMATION` goals, metadata should include at least:

- `corridor_edge_ids`: list of corridor/edge ids that are currently considered dangerous and need scouting.
- `hazard_snapshot`: optional copy of council metrics when the goal was created.
- `max_scouts`: integer, recommended number of scouts to assign (MVP default 3).
- `created_by_group_id`: id of the creating council group.

For agent-level `GATHER_INFORMATION` goals, metadata should include:

- `parent_group_goal_id`: id of the parent council goal.
- `corridor_edge_ids`: copy of the target corridors.
- `ticks_active`: counter incremented each tick while the goal is active.
- `visits_recorded`: counter of how many scouting visits produced hazard-inspection episodes.

The scenario success checks only need that these fields exist and are used consistently. The goal system remains otherwise generic.

---

## 4. Council trigger for gather-information

Council decisions about gather-information goals are built on the hazard metrics described in D-RUNTIME-0214.

### 4.1 Trigger condition

After metrics are updated and dangerous corridors are identified, the council evaluates:

- there is at least one dangerous corridor edge, and
- there is no existing group-level `GATHER_INFORMATION` goal in planning or active status, whose `corridor_edge_ids` match the current set of dangerous corridors, and
- any configured cooldown for gather-information decisions has elapsed (MVP may skip cooldown).

If these conditions are met, the council should ensure there is at least one gather-information group goal.

### 4.2 Helper: ensure_council_gather_information_goal

We define a helper at the groups layer that:

- takes the world, the council group, the hazard metrics, the corridors of interest, and the current tick,
- searches for an existing `GATHER_INFORMATION` goal owned by this council, with matching `corridor_edge_ids` and status in planning or active,
- if found, returns that goal as-is,
- otherwise, allocates a new goal id and creates a new group-level `Goal` with:
  - `owner_id` set to the council group id,
  - `goal_type = GATHER_INFORMATION`,
  - `origin = GROUP_DECISION`,
  - `status = ACTIVE`,
  - `created_at_tick = current_tick`,
  - metadata populated as defined in section 3.2,
- registers the goal in the world’s goal registry and appends its id to `council_group.goal_ids`,
- returns the group goal.

This helper is pure book-keeping; it does not select scouts or move agents.

---

## 5. Projecting gather-information goals onto agents

### 5.1 Helper: project_gather_information_to_scouts

We also define a helper that:

- takes the world, the council group, a group-level gather-information goal, the list of corridors of interest, and the current tick,
- selects a small set of candidate agents to act as scouts,
- assigns them agent-level `GATHER_INFORMATION` goals, and
- marks them with `GroupRole.SCOUT` for this council.

### 5.2 Candidate selection (MVP)

Candidate agents are filtered from the global agent set:

- awake and not critically impaired,
- not already overloaded with long-running work,
- not already holding another active `GATHER_INFORMATION` goal.

A simple scoring heuristic is used, for example:

- score is a weighted combination of dexterity, endurance, and inverse stress level.

Candidates are sorted by score and the top `max_scouts` agents (from the group goal metadata, default 3) are selected.

### 5.3 Creating agent-level goals

For each selected agent:

- ensure that their role for this group includes `GroupRole.SCOUT`,
- create an agent-level `Goal` with:
  - `owner_id` set to the agent id,
  - `goal_type = GATHER_INFORMATION`,
  - `origin = GROUP_DECISION`,
  - `status = ACTIVE`,
  - `created_at_tick` = current tick,
  - metadata populated as defined in section 3.2 (parent id, corridor ids, counters initialised to zero),
- register the goal and append it to the agent’s list of goals.

Optionally, the runtime can emit an episode representing the assignment decision.

---

## 6. Agent behaviour while gathering information

### 6.1 Mapping to SCOUT_INTERIOR work detail

To minimise new behaviour code, the MVP reuses `WorkDetailType.SCOUT_INTERIOR`:

- if an agent has at least one active `GATHER_INFORMATION` goal, the decision loop should ensure the agent has a `SCOUT_INTERIOR` work detail that targets the corridors in the goal metadata,
- the work detail’s metadata should contain the corridor ids to bias path selection.

The existing `SCOUT_INTERIOR` handler is extended so that:

- when selecting the next move, it preferentially chooses to traverse edges listed in the goal metadata, where possible,
- when the agent visits or traverses a target corridor edge, it emits a hazard-oriented scouting episode and increments the goal’s `visits_recorded` and `ticks_active` counters.

### 6.2 Completion rules (agent-level)

Agent-level `GATHER_INFORMATION` goals use the following completion conditions:

- if runtime config provides `min_ticks_for_gather_information` and `min_visits_for_gather_information`, then:
  - mark the goal completed when `ticks_active` and `visits_recorded` both meet or exceed these thresholds,
- otherwise, for MVP, a simple rule is acceptable:
  - mark the goal completed as soon as `visits_recorded` is at least 1.

The completed status is used primarily for success checks and debugging; the council may still continue to run additional scouting rounds in later ticks.

### 6.3 Group-level satisfaction

A group-level gather-information goal is considered to have been substantively acted on when:

- at least one agent-level child goal referencing it as `parent_group_goal_id` is either:
  - explicitly completed, or
  - has recorded at least one visit and has been active for a configurable minimum number of ticks.

The group-level goal can remain active if desired; the success logic only cares that some meaningful scouting has taken place.

---

## 7. Scenario success check for gather_information_goals

The Founding Wakeup spec includes `min_information_goals` as a success criterion. This document defines how the runtime should interpret that field.

A helper at the scenario or report layer should:

- collect all `GATHER_INFORMATION` goals from the world’s global goal registry,
- identify which of these are group-level (owner id is a group),
- for each such group-level goal, search for agent-level `GATHER_INFORMATION` goals whose metadata points back to it via `parent_group_goal_id`,
- if at least one of those agent-level goals is completed or has a non-zero `visits_recorded` counter, then that group-level goal counts as a satisfied information goal.

The helper then:

- counts how many group-level goals are satisfied in this way, and
- compares that count to `min_information_goals`.

If the count is at least `min_information_goals`, the `gather_information_goals` success flag is set to `OK`; otherwise it is set to `MISSING`.

---

## 8. Integration order and boundaries

Recommended order for implementation:

1. Ensure `GoalType.GATHER_INFORMATION` and `GoalOrigin.GROUP_DECISION` exist in the goal system, with `metadata` available on goals.
2. Implement `ensure_council_gather_information_goal` in the groups layer and call it from the council meeting logic whenever dangerous corridors are detected.
3. Implement `project_gather_information_to_scouts` and call it immediately after creating or retrieving the group-level goal.
4. Extend the agent decision loop to:
   - detect active `GATHER_INFORMATION` goals, and
   - ensure the agent is running a `SCOUT_INTERIOR` work detail that targets the corridors requested by the goal.
5. Extend `SCOUT_INTERIOR` behaviour to:
   - bias movement toward target corridors,
   - emit hazard-inspection episodes and update the goal counters.
6. Implement the scenario-level helper for checking gather-information success and wire it into the Founding Wakeup report builder.

Explicit MVP simplifications:

- no complex routing or retreat logic,
- naive scout selection based on a simple heuristic,
- binary success criteria based on at-least-one meaningful scouting loop,
- no explicit player-facing UI yet for information goals.

These can all be refined in future runtime or agent docs.

---

## 9. Test checklist

After implementation, a typical Founding Wakeup run should show:

- dangerous corridors being detected via council metrics,
- the council creating at least one `GATHER_INFORMATION` group goal that points at those corridors,
- several agents being assigned as scouts with agent-level `GATHER_INFORMATION` goals,
- scouts travelling along the target corridors and emitting hazard-focused episodes,
- at least one agent-level gather-information goal registering a non-zero `visits_recorded` counter,
- the scenario report showing `gather_information_goals: OK` in the success checks.

This completes the gather-information loop for the Founding Wakeup MVP.
