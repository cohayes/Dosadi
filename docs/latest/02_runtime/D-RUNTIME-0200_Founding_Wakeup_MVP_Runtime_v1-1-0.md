---
title: Founding_Wakeup_MVP_Runtime
doc_id: D-RUNTIME-0200
version: 1.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-SCEN-0002     # Founding_Wakeup_MVP_Scenario
  - D-WORLD-0100    # Founding_Wakeup_Topology
  - D-AGENT-0020    # Agent_Model_Foundation
  - D-AGENT-0021    # Agent_Goals_and_Episodic_Memory
  - D-AGENT-0022    # Agent_MVP_Python_Skeleton
  - D-AGENT-0023    # Groups_and_Councils_MVP
  - D-LAW-0010      # Risk_and_Protocol_Cycle
  - D-LAW-0013      # Movement_Protocols_MVP
---

# 1. Purpose and Scope

This document defines the **runtime orchestration** for the **Founding Wakeup MVP**
scenario. It describes:

- The **WorldState** shape needed to run the scenario.
- The **per-tick loop** and the order of operations.
- How to invoke:
  - agent decisions,
  - pod meetings and proto-council logic,
  - movement + hazard resolution,
  - protocol authoring and effects.

Version 1.1.0 extends the original D-RUNTIME-0200 to incorporate **Step 6** of the
MVP plan:

- Integration of `D-AGENT-0022` (AgentState, goals, episodes).
- Integration of `D-AGENT-0023` (pod groups, proto-council, group goals).
- Integration of `D-LAW-0013` (movement protocols and hazard multipliers).
- A concrete **tick loop** for `founding_wakeup_mvp` suitable for Codex to
  implement in Python.


# 2. Timebase and Simulation Horizon

See `D-RUNTIME-0001_Simulation_Timebase` for global definitions.

For Founding Wakeup MVP we assume:

- **Ticks per minute**: 100 (1 tick = 0.6 seconds of in-world time).
- **Short-run tests**: 10,000–50,000 ticks (100–500 in-world minutes).
- **Mid-run arcs**: 100,000–300,000 ticks (~1–3 in-world days).

The MVP goal is not yet multi-year; it is to observe:

- Emergence of pod representatives.
- Formation of a proto-council.
- Authoring and activation of at least one movement/safety protocol.
- Observable changes in hazard incident rates on targeted corridors.


# 3. WorldState (MVP Shape)

This section defines the **minimal fields** the runtime needs to coordinate the
Founding Wakeup MVP. Existing `WorldState` implementations should be extended
(not replaced) to match this surface.


## 3.1 Core WorldState fields

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random

from dosadi.agents.core import AgentState
from dosadi.agents.groups import Group, GroupType
from dosadi.systems.protocols import ProtocolRegistry
# Topology types should be defined in D-WORLD-0100; this is an indicative sketch:
# from dosadi.world.topology import Node, Edge


@dataclass
class WorldState:
    """MVP world state for the Founding Wakeup scenario."""

    # Clock and RNG
    tick: int = 0
    rng: random.Random = field(default_factory=random.Random)

    # Agents and groups
    agents: Dict[str, AgentState] = field(default_factory=dict)
    groups: List[Group] = field(default_factory=list)

    # Topology (pods, corridors, well core, etc.)
    nodes: Dict[str, "Node"] = field(default_factory=dict)
    edges: Dict[str, "Edge"] = field(default_factory=dict)

    # Protocols (movement / safety)
    protocols: ProtocolRegistry = field(default_factory=ProtocolRegistry)

    # Scenario / runtime config knobs (see §3.2)
    config: "RuntimeConfig" = field(default_factory=lambda: RuntimeConfig())

    # Simple metrics (incidents, traversals, etc.)
    metrics: Dict[str, float] = field(default_factory=dict)
```


## 3.2 RuntimeConfig

The `RuntimeConfig` encapsulates timing and threshold parameters for this scenario.

```python
@dataclass
class RuntimeConfig:
    """Tunable configuration for the Founding Wakeup MVP runtime."""

    # Pod meeting cadence (ticks between meetings per pod)
    pod_meeting_interval_ticks: int = 2400  # ~24 minutes

    # Council meeting cooldown
    council_meeting_cooldown_ticks: int = 600  # ~6 minutes

    # Minimum council members present to hold a meeting
    min_council_members_for_meeting: int = 2

    # Group selection thresholds
    rep_vote_fraction_threshold: float = 0.4
    min_leadership_threshold: float = 0.6
    max_pod_representatives: int = 2
    max_council_size: int = 10

    # Protocol trigger parameters
    min_incidents_for_protocol: int = 3
    risk_threshold_for_protocol: float = 0.3  # incidents / traversals

    # Max ticks for the scenario
    max_ticks: int = 100_000
```


# 4. High-Level Runtime Loop

The Founding Wakeup runtime is structured as a **per-tick loop** with a stable,
predictable sequence of phases. This ensures:

- Deterministic behavior (given a seed).
- Clean points for group/council updates, agent decisions, and hazard resolution.


## 4.1 Tick phases (overview)

At each tick `t`, the runtime performs:

1. **Phase A: Scheduled group/council updates**
   - Pod meetings (maybe).
   - Proto-council formation (maybe).
   - Proto-council meetings (maybe).

2. **Phase B: Agent decision phase**
   - For each agent, call `decide_next_action(agent, world)`.

3. **Phase C: Action application & hazard resolution**
   - For each agent, apply chosen action:
     - MOVEMENT → path resolution + hazard checks.
     - REST_IN_POD → update fatigue, etc.
     - POD_MEETING or COUNCIL_MEETING → episodes are recorded.

4. **Phase D: Post-processing & metrics**
   - Update beliefs (`PlaceBelief`) from episodes.
   - Update aggregate metrics (traversals, incidents per corridor).

5. **Phase E: Advance clock & termination checks**
   - Increment `world.tick`.
   - If `world.tick >= config.max_ticks`, stop.


## 4.2 Entry point: run_founding_wakeup_mvp

```python
from typing import Optional

from dosadi.scenarios.founding_wakeup import generate_founding_wakeup_mvp
from dosadi.runtime.reporting import ScenarioReport  # whatever type is used


def run_founding_wakeup_mvp(
    num_agents: int,
    max_ticks: int,
    seed: int,
) -> "ScenarioReport":
    """Run the Founding Wakeup MVP scenario from scratch.

    - Initializes world via generate_founding_wakeup_mvp.
    - Steps the world until max_ticks or a natural stopping condition.
    - Returns a report structure consumable by dashboards.
    """
    world = generate_founding_wakeup_mvp(num_agents=num_agents, seed=seed)
    world.config.max_ticks = max_ticks
    world.rng.seed(seed)

    while world.tick < world.config.max_ticks:
        step_world_once(world)

    # Construct and return a ScenarioReport (implementation-specific)
    report = build_founding_wakeup_report(world)
    return report
```


## 4.3 Core step function: step_world_once

```python
from dosadi.agents.core import AgentState
from dosadi.agents.decision import decide_next_action, apply_action
from dosadi.agents.groups import (
    Group,
    GroupType,
    maybe_run_pod_meeting,
    maybe_form_proto_council,
    maybe_run_council_meeting,
)


def step_world_once(world: WorldState) -> None:
    """Advance the world by a single tick for the Founding Wakeup MVP."""
    tick = world.tick
    rng = world.rng
    cfg = world.config

    # Phase A: Group / council maintenance
    _phase_A_groups_and_council(world, tick, rng, cfg)

    # Phase B: Agent decision phase
    actions_by_agent = _phase_B_agent_decisions(world, tick)

    # Phase C: Apply actions and resolve hazards
    _phase_C_apply_actions_and_hazards(world, tick, actions_by_agent)

    # Phase D: Post-processing & metrics
    _phase_D_postprocess_and_metrics(world, tick)

    # Phase E: Advance clock
    world.tick += 1
```


# 5. Phase A: Groups and Proto-Council

Phase A wires in `D-AGENT-0023` pod and council logic.


```python
def _phase_A_groups_and_council(world: WorldState, tick: int, rng, cfg: RuntimeConfig) -> None:
    # 1. Pod meetings (representative selection)
    for g in world.groups:
        if g.group_type == GroupType.POD:
            from dosadi.agents.groups import maybe_run_pod_meeting
            maybe_run_pod_meeting(
                pod_group=g,
                agents_by_id=world.agents,
                tick=tick,
                rng=rng,
                meeting_interval_ticks=cfg.pod_meeting_interval_ticks,
                rep_vote_fraction_threshold=cfg.rep_vote_fraction_threshold,
                min_leadership_threshold=cfg.min_leadership_threshold,
                max_representatives=cfg.max_pod_representatives,
            )

    # 2. Proto-council formation / extension
    from dosadi.agents.groups import maybe_form_proto_council
    council = maybe_form_proto_council(
        groups=world.groups,
        agents_by_id=world.agents,
        tick=tick,
        hub_location_id="loc:well-core",
        max_council_size=cfg.max_council_size,
    )

    # 3. Council meetings (if council exists)
    if council is not None:
        from dosadi.agents.groups import maybe_run_council_meeting
        maybe_run_council_meeting(
            council_group=council,
            agents_by_id=world.agents,
            tick=tick,
            rng=rng,
            cooldown_ticks=cfg.council_meeting_cooldown_ticks,
            hub_location_id="loc:well-core",
        )
```

Notes:

- The **aggregation of hazard episodes** and creation of `GATHER_INFORMATION` /
  `AUTHOR_PROTOCOL` group goals are internal to `maybe_run_council_meeting` and its
  helpers (see `D-AGENT-0023` and `D-LAW-0013`).
- The actual **creation** of `Protocol` records occurs when a scribe completes an
  `AUTHOR_PROTOCOL` goal and calls into the protocol system (see §7).


# 6. Phase B: Agent Decisions

Phase B uses the decision loop described in `D-AGENT-0020` / `D-AGENT-0022`. The
concrete functions live in something like `dosadi.agents.decision` (name flexible as
long as the interface matches).


```python
from typing import Dict
from dosadi.actions import Action  # placeholder for concrete Action type


def _phase_B_agent_decisions(world: WorldState, tick: int) -> Dict[str, "Action"]:
    actions_by_agent: Dict[str, Action] = {}

    for agent_id, agent in world.agents.items():
        action = decide_next_action(agent, world)
        actions_by_agent[agent_id] = action
        agent.last_decision_tick = tick

    return actions_by_agent
```

Requirements for `decide_next_action(agent, world)` (see future `D-RUNTIME-0201`):

- Use `agent.choose_focus_goal()` as a starting point.
- Consider a small action set for MVP:
  - `REST_IN_POD`
  - `MOVE(destination_location_id)`
  - `ATTEND_POD_MEETING` (if at pod and meeting is flagged)
  - `TRAVEL_TO_WELL_CORE` (if acting as representative or council member)
  - `SCOUT_CORRIDOR` (if holding a `GATHER_INFORMATION` goal)
  - `DRAFT_PROTOCOL` (if holding an `AUTHOR_PROTOCOL` goal)
- Use:
  - `PlaceBelief.danger_score`,
  - personality traits (bravery, communal, ambition, curiosity),
  - physical state (fatigue, health),
  - goal priority/urgency

  to rank options.


# 7. Phase C: Actions and Hazards

Phase C applies the chosen actions, including movement and hazard resolution.

```python
def _phase_C_apply_actions_and_hazards(
    world: WorldState,
    tick: int,
    actions_by_agent: Dict[str, "Action"],
) -> None:
    for agent_id, action in actions_by_agent.items():
        agent = world.agents[agent_id]
        episodes = apply_action(agent, action, world, tick)
        # apply_action returns a sequence of Episode objects (see D-AGENT-0022)
        for ep in episodes:
            agent.record_episode(ep)
```

The **movement + hazard** part of `apply_action` must:

1. Determine the **edge** and **destination location**:

   ```python
   edge = world.edges[action.edge_id]
   dest_location_id = edge.to_node_id  # or similar
   ```

2. Determine the **base hazard probability** from topology:

   ```python
   base_hazard_prob = edge.base_hazard_prob
   ```

3. Determine the **group size** for this traversal:

   - MVP: group size can be `1` unless there is an explicit “travel together”
     mechanic implemented.
   - Future: group size is the size of a `movement cohort` (agents moving on same
     edge in same tick).

4. Call the protocol-aware hazard helper from `D-LAW-0013`:

   ```python
   from dosadi.systems.protocols import compute_effective_hazard_prob

   group_size = 1  # MVP placeholder; extend later for joint movement
   hazard_prob = compute_effective_hazard_prob(
       agent=agent,
       location_id=dest_location_id,
       base_hazard_prob=base_hazard_prob,
       group_size=group_size,
       registry=world.protocols,
   )
   ```

5. Roll for hazard and emit episodes:

   ```python
   roll = world.rng.random()
   if roll < hazard_prob:
       # Hazard incident
       # - Update agent.physical (health, stress)
       # - Increment metrics (see §8)
       # - Emit a HAZARD_INCIDENT Episode
   else:
       # Safe traversal
       # - Increment traversals metric
       # - Optionally emit a MOVEMENT Episode
   ```


# 8. Phase D: Post-Processing and Metrics

After all actions are applied:

- Agents update beliefs from new episodes.
- World-level metrics are updated for use by the council and post-run reports.


```python
def _phase_D_postprocess_and_metrics(world: WorldState, tick: int) -> None:
    # 1. Beliefs
    for agent in world.agents.values():
        # For MVP, we just update place beliefs from each latest episode.
        for ep in agent.episodes:
            # In a real implementation, you might only process episodes from this tick.
            if ep.tick_end == tick and ep.location_id is not None:
                agent.update_beliefs_from_episode(ep)

    # 2. Metrics can be maintained incrementally inside apply_action; this function
    # can be used for any per-tick aggregations or snapshots.
```

### 8.1 Corridor metrics (for protocol triggers)

The council needs simple metrics per corridor:

- `traversals[corridor_id]`
- `incidents[corridor_id]`

Suggestion:

- Store them in `world.metrics` under keys like:
  - `f"traversals:{corridor_id}"`
  - `f"incidents:{corridor_id}"`
- Update them in the movement part of `apply_action`.

When `maybe_run_council_meeting` aggregates risk, it can read these metrics and
decide whether to create `AUTHOR_PROTOCOL` goals per corridor, following
`D-LAW-0013`.


# 9. Protocol Authoring Hook (Step 6 Integration)

When a **scribe** agent completes an `AUTHOR_PROTOCOL` goal, the decision/logic
layer should call into the protocol system to actually create and activate a
movement protocol.

This is **not** a new runtime phase; it’s a hook that occurs within:

- `apply_action` when handling a `DRAFT_PROTOCOL` or `AUTHOR_PROTOCOL` action, or
- A small helper called from the agent decision loop when a scribe “finishes”.


## 9.1 Protocol authoring helper pattern

```python
from dosadi.systems.protocols import (
    create_movement_protocol_from_goal,
    activate_protocol,
)


def handle_protocol_authoring(
    world: WorldState,
    scribe: AgentState,
    authoring_goal: Goal,
    corridors: List[str],
) -> Protocol:
    """Create and activate a movement protocol from a scribe's authoring goal."""
    # Find the council group id owning this goal; this may be encoded in goal.target
    council_group_id = authoring_goal.target.get("council_group_id", "group:council:alpha")

    protocol = create_movement_protocol_from_goal(
        council_group_id=council_group_id,
        scribe_agent_id=scribe.agent_id,
        group_goal=authoring_goal,
        corridors=corridors,
        tick=world.tick,
        registry=world.protocols,
    )

    activate_protocol(protocol, tick=world.tick)
    return protocol
```

After activation:

- The protocol will be considered in `compute_effective_hazard_prob`.
- The runtime or a higher-level system can schedule **READ_PROTOCOL** events for
  agents (e.g. all council members, then all pod reps, etc.).


# 10. Summary

D-RUNTIME-0200 (v1.1.0) defines the **runtime glue** for the Founding Wakeup MVP:

- A concrete **WorldState** shape with agents, groups, topology, and protocols.
- A stable **tick loop** with explicit phases A–E.
- Integration of:
  - Pod groups and proto-council (D-AGENT-0023),
  - Agent goals, episodes, and beliefs (D-AGENT-0021, D-AGENT-0022),
  - Movement/safety protocols and hazard multipliers (D-LAW-0013).

This is the document Codex should follow when wiring together:

- `generate_founding_wakeup_mvp` (scenario/worldgen),
- Agent decision and action logic,
- Group and council mechanics,
- Protocol authoring and hazard effects,
- And the `run_founding_wakeup_mvp` scenario runner.
