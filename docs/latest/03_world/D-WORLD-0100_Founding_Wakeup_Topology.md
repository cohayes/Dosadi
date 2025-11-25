---
title: Founding_Wakeup_Topology
doc_id: D-WORLD-0100
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-RUNTIME-0200  # Founding_Wakeup_MVP_Runtime
---

# 1. Purpose and Scope

This document defines the **world topology** for the Founding Wakeup MVP scenario:

- The physical layout of pods, corridors, junctions, and the Well core.
- The key properties of each node and edge relevant to:
  - Movement,
  - Hazard resolution,
  - Group formation (pods, proto-councils),
  - Early protocol authoring.

It is intentionally minimal and tailored to the `founding_wakeup_mvp` scenario (`D-SCEN-0002`). Later world docs can extend this into richer ward/industry maps.


# 2. Topology Overview

## 2.1 Components

The MVP topology contains three main component types:

1. **Pods (bunk clusters)**  
   - Safe, sealed environments where colonists begin.
   - Natural units for early group formation.

2. **Corridors and junctions**  
   - Hazardous transit spaces between pods and the Well core.
   - Early focus of risk perception and protocol-making.

3. **Well core hub**  
   - Shared hub node where:
     - Pods exchange people,
     - Representatives can meet and form proto-councils,
     - Early logistics will eventually pivot.

This topology is a **toy slice** of the eventual city, designed to be small but structurally rich enough to demonstrate the Risk and Protocol Cycle.


## 2.2 Node set

Canonical node ids:

- Pods:
  - `loc:pod-1`
  - `loc:pod-2`
  - `loc:pod-3`
  - `loc:pod-4`

- Corridors:
  - `loc:corridor-2A`
  - `loc:corridor-3A`
  - `loc:corridor-7A`

- Junctions:
  - `loc:junction-7A-7B` (a simple branching point; optional but recommended)

- Hub:
  - `loc:well-core`

These ids should be treated as **stable** for this scenario so they can be referenced in logs, episodes, protocols, and debug views.


# 3. Node Properties

## 3.1 Pod nodes

Example schema:

```jsonc
PodNode {
  "id": "loc:pod-1",
  "type": "pod",
  "tags": ["sealed", "safe", "residential"],
  "max_capacity": 20
}
```

Properties:

- `type = "pod"`  
- `tags`:
  - `"sealed"`: environment is safe; no hazard incidents triggered inside the pod.
  - `"safe"`: used in agent decision logic to favor pods for rest.
  - `"residential"`: future hooks for bunk allocation and domestic routines.
- `max_capacity`:
  - Suggested ~20 for MVP; not enforced strictly, but used for worldgen distributions.


## 3.2 Corridor nodes

Example:

```jsonc
CorridorNode {
  "id": "loc:corridor-7A",
  "type": "corridor",
  "tags": ["narrow", "low-light", "unstable"],
  "base_hazard_modifier": 1.0
}
```

Properties:

- `type = "corridor"`
- `tags` (optional, descriptive; may influence flavor or later mechanics):
  - `"narrow"`, `"low-light"`, `"unstable"`, etc.
- `base_hazard_modifier`:
  - Default 1.0; most hazard is encoded on edges, not nodes, for MVP.

Corridors are where most early risk episodes occur (falls, collisions, near-misses, suit scrapes, etc.).


## 3.3 Junction nodes

Example:

```jsonc
JunctionNode {
  "id": "loc:junction-7A-7B",
  "type": "junction",
  "tags": ["choke-point"],
  "base_hazard_modifier": 1.0
}
```

Junctions:

- Provide additional structural interest and potential choke points.
- May become important in later scenarios (ambush sites, toll points, etc.).

For MVP, `loc:junction-7A-7B` exists primarily to give the high-risk route an extra step.


## 3.4 Well core hub

Example:

```jsonc
HubNode {
  "id": "loc:well-core",
  "type": "hub",
  "tags": ["well", "meeting-point"],
  "is_well_core": true
}
```

Properties:

- `type = "hub"`.
- `tags`:
  - `"well"`: signals central resource; used for future Well output modeling.
  - `"meeting-point"`: used by group logic to prefer this site for council formation.
- `is_well_core = true`:
  - Marker for world systems that care about the primary Well.


# 4. Edge Properties

Edges connect nodes and carry hazard probabilities for traversal.

Example schema:

```jsonc
Edge {
  "id": "edge:pod-4_to_corridor-7A",
  "from": "loc:pod-4",
  "to": "loc:corridor-7A",
  "undirected": true,
  "base_hazard_prob": 0.20,
  "tags": ["narrow", "poorly-lit"]
}
```

Properties:

- `from`, `to`:
  - Node ids.
- `undirected`:
  - If true, traversal cost/hazard is symmetric both ways.
- `base_hazard_prob`:
  - Per-traversal probability of a hazard incident in the absence of protocols or other modifiers.
- `tags`:
  - Optional descriptors (e.g. `"steep"`, `"poorly-lit"`) that can feed into narrative flavor or later mechanics.


## 4.1 MVP edge set and hazard defaults

Suggested defaults:

- Pod-to-corridor low-risk edges:
  - `loc:pod-1  <-> loc:corridor-2A`:
    - `base_hazard_prob: 0.02`
  - `loc:pod-2  <-> loc:corridor-3A`:
    - `base_hazard_prob: 0.02`
  - `loc:pod-3  <-> loc:corridor-3A`:
    - `base_hazard_prob: 0.02`

- Corridor-to-hub low-risk edges:
  - `loc:corridor-2A <-> loc:well-core`:
    - `base_hazard_prob: 0.02`
  - `loc:corridor-3A <-> loc:well-core`:
    - `base_hazard_prob: 0.02`

- High-risk path from pod-4 to hub:
  - `loc:pod-4 <-> loc:corridor-7A`:
    - `base_hazard_prob: 0.20`
  - `loc:corridor-7A <-> loc:junction-7A-7B`:
    - `base_hazard_prob: 0.20`
  - `loc:junction-7A-7B <-> loc:well-core`:
    - `base_hazard_prob: 0.05`

These values match the scenario config in `D-SCEN-0002` and are chosen to make protocol effects legible in short runs.


# 5. Topology Diagram (Conceptual)

A simple ASCII sketch to aid reasoning:

```text
          [pod-1]
             |
        corridor-2A
             |
          well-core
            /|\
           / | \
corridor-3A  |  junction-7A-7B
    /  \    |        |
[pod-2] [pod-3]   corridor-7A
                      |
                    [pod-4]
```

- `corridor-2A` and `corridor-3A` are relatively safe routes.
- `corridor-7A` is notably dangerous and becomes the **first focus** of:
  - Hazard episodes,
  - Proto-council risk analysis,
  - Movement protocol authoring.


# 6. Worldgen Skeleton (for Codex)

Worldgen for this topology should be anchored in a function like:

```python
def generate_founding_wakeup_mvp(num_agents: int, seed: int) -> tuple[WorldState, list[AgentState], list[Group]]:
    """Construct the Founding Wakeup MVP topology and initial population.

    - Creates nodes (pods, corridors, junctions, well-core) with the ids and types defined here.
    - Creates edges with the hazard probabilities defined above.
    - Distributes `num_agents` across 4 pods (approximately evenly).
    - Initializes agents' locations to their assigned pods.
    - Returns:
        world: WorldState with nodes, edges, and any global metadata.
        agents: list of AgentState with initialized attributes, traits, goals, and state.
        groups: initial groups (implicit pods may or may not be explicit here; proto-council not yet created).
    """
    ...
```

Requirements for Codex:

- Use the node and edge ids from this document, not ad-hoc names.
- Ensure all hazard probabilities are parameterized (constants at top of the module or read from a small config) for later tuning.
- Ensure reproducibility via the `seed` parameter for any random assignments (agent attributes, pod allocations).


# 7. Integration Notes

- This topology is specific to `founding_wakeup_mvp` and should not be assumed to describe the full city.
- Future world docs (e.g. `D-WORLD-0200+`) may:
  - Embed this topology into a larger ward map.
  - Add industry nodes, water logistics edges, external service tunnels, etc.
- All higher-level systems (agents, goals, episodes, protocols) should **refer to this topology by id** rather than hardcoding new names for these initial nodes.

By locking in this small, named world slice, we make it easier to:

- Debug early behavior,
- Compare simulation runs,
- Reuse this scenario as a canonical “unit test” for emergent governance.
