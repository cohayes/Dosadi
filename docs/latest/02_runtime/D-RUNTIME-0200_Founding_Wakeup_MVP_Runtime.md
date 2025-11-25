---
title: Founding_Wakeup_MVP_Runtime
doc_id: D-RUNTIME-0200
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-RUNTIME-0001 # Simulation_Timebase
  - D-AGENT-0020   # Agent_Model_Foundation
  - D-AGENT-0021   # Agent_Goals_and_Episodic_Memory
  - D-LAW-0010     # Risk_and_Protocol_Cycle
---

# 1. Purpose and Scope

This document specifies the **Minimum Viable Product (MVP)** runtime for the **Founding Wakeup** sequence in the Dosadi simulation.

The goal of this MVP is to implement a small, self-contained scenario where:

1. **N colonists wake up** in bunk pods around the Well.  
2. They form **pod-level social structures** and at least one **proto-council**.  
3. The proto-council sets **group information-gathering goals** about local hazards.  
4. Assigned scouts explore nearby corridors, generating **episodes** about risk.  
5. The proto-council authors at least one **movement/safety protocol** that:  
   - Is read by multiple agents, and  
   - Produces a **measurable reduction in hazard incidents** on affected corridors.

This MVP:

- Uses the unified agent model and goal/memory architecture from `D-AGENT-0020` and `D-AGENT-0021`.  
- Demonstrates the **Risk and Protocol Cycle** (`D-LAW-0010`) in miniature.  
- Avoids complex subsystems (espionage, economics, health detail, narcotics, etc.), focusing only on:
  - Survival, movement, group formation, information sharing, and basic protocol authoring/enforcement.


# 2. Scenario Overview

## 2.1 High-level description

Scenario id: `founding_wakeup_mvp`

- **Initial conditions:**
  - N colonists (Tier-1 agents) wake in sealed bunk pods arranged around the Well core.
  - Corridors outside pods are **hostile**:
    - Some edges have elevated hazard probabilities (falls, exposure, structural risks).
  - All colonists have:
    - Basic suits (enough to traverse corridors with non-zero risk).
    - Equal formal legal status; no pre-existing nobility, guilds, or cartels.

- **Main dynamics:**
  - Agents form **pod-level groups** for safety and coordination.
  - Each pod gradually recognizes 1–2 **spokespeople** with higher LeadershipWeight and influence.
  - When spokespeople from multiple pods meet at shared locations (e.g. Well hub), they form a **proto-council**.
  - The proto-council:
    - Aggregates hazard-related episodes (corridor incidents).
    - Sets group-level `GATHER_INFORMATION` goals targeting dangerous or unknown corridors.
    - Assigns scouts and scribes.
  - Scouts explore corridors, generating episodes about hazards and safe paths.
  - The proto-council uses these episodes to author the **first movement/safety protocol(s)**.

- **Success conditions (see §7):**
  - At least one protocol is authored and read by multiple agents.
  - After protocol adoption, hazard incidents on affected corridors decline relative to pre-protocol ticks.


## 2.2 Out-of-scope (for this MVP)

The following are **explicitly excluded** from the MVP runtime:

- Economy: no credits, rations as explicit items, or water barrel logistics.
- Espionage, counterintelligence, sting waves.
- Organized crime, narcotics, and cartels.
- Complex law (courts, prisons, formal sanctions):
  - Protocols are **soft norms** with basic enforcement behavior only.
- Multi-tier formal governance:
  - We allow proto-council behavior and proto-Tier-3 actions but do not define full crowns/dukes/guilds.


# 3. World Specification

## 3.1 Topology

The MVP world is a small graph with the following node types:

- **Pods:**
  - `loc:pod-1`, `loc:pod-2`, ..., `loc:pod-K`
  - Properties:
    - Safe (no hazard events occur inside pods).
    - Capacity (number of colonists assigned).
    - Implicit group boundary (pod membership).

- **Well hub:**
  - `loc:well-core`
  - Shared location for cross-pod interaction.
  - Candidate site for proto-council formation.

- **Corridors and junctions:**
  - `loc:corridor-2A`, `loc:corridor-3A`, `loc:corridor-7A`, etc.
  - Optionally `loc:junction-*` nodes for branching points.
  - Properties:
    - `base_hazard_prob` per edge traversal.
    - Optional tags:
      - e.g. `["narrow", "low-light"]`.

### 3.1.1 Edges

Edges are directed or undirected connections with per-step hazard probabilities:

- Example:
  - `pod-1 <-> corridor-2A <-> well-core`
  - `pod-2 <-> corridor-3A <-> well-core`
  - `well-core <-> corridor-7A <-> junction-7A-7B`

Each edge has:

```jsonc
Edge {
  "from": "loc:pod-1",
  "to":   "loc:corridor-2A",
  "base_hazard_prob": 0.02
}
```

Certain edges (e.g. those involving `corridor-7A`) have elevated `base_hazard_prob` (e.g. 0.15–0.25) to create a **meaningful risk gradient**.

## 3.2 Worldgen function

A dedicated worldgen function should be defined, e.g.:

```python
generate_founding_wakeup_mvp(num_agents: int, seed: int) -> (world, agents, groups)
```

Responsibilities:

- Construct nodes and edges as above.
- Partition N colonists into K pods (approx. equal distribution).
- Initialize all agents as located in their pod.
- Initialize group structures:
  - Implicit pod groups (by membership).
  - No proto-council yet.

Worldgen is deterministic given `num_agents` and `seed`.


# 4. Agent Initialization

## 4.1 Agent population

For MVP, we assume:

- N in the range 40–120 (e.g. default 80).
- K pods such that each pod has 8–30 agents.

Each agent uses the canonical structure from `D-AGENT-0020`, initialized with:

- **Identity:**
  - `tier = 1`
  - `roles = ["colonist"]` (some may gain `POD_REPRESENTATIVE` later)
  - `ward/locality` = this initial sealed cluster only.

- **Attributes & personality:**
  - Attributes (STR/DEX/END/INT/WIL/CHA) sampled from a small distribution around 10.
  - Personality traits sampled with mild variation:
    - Some more brave, some more cautious.
    - Some more communal, some more self-serving.
    - A few with higher ambition and LeadershipWeight.

- **State:**
  - Reasonable baseline health, low fatigue, mild hunger (to drive basic action but not dominate).
  - No serious injuries or trauma at tick 0.

## 4.2 Initial goals

Each agent starts with a minimal goal stack (see `D-AGENT-0021`):

- Universal:
  - `MAINTAIN_SURVIVAL_TODAY` (parent goal; very high priority, SHORT horizon).
  - `ACQUIRE_RESOURCE` (abstracted; enough to justify occasional movement out of pod).
  - `SECURE_SHELTER` (already satisfied initially but can influence avoidance of losing pod).

- Conditional (more likely in selected personalities):
  - `REDUCE_POD_RISK` (for agents with higher LeadershipWeight and communal traits).
  - `FORM_GROUP` / `STABILIZE_POD` (in early steps).

No explicit proto-council goals exist at tick 0; they emerge from pod-level interactions.


# 5. Runtime Loop

## 5.1 Simulation envelope

A typical MVP run:

- Tick count: 500–2000 ticks (to be tuned).
- Timebase: as defined in `D-RUNTIME-0001` (e.g. 1.67 ticks per real-time second; for design purposes we only need relative order).

The runtime engine should support:

```python
run_founding_wakeup_mvp(num_agents: int, ticks: int, seed: int) -> ScenarioReport
```

Where `ScenarioReport` contains at minimum:

- Aggregate episode statistics (e.g. hazard incidents per corridor over time).
- List of groups (pods, proto-council).
- List of protocols authored and adoption counts.
- Basic time series:
  - hazard incidents before/after first protocol per affected corridor.

## 5.2 Per-tick agent loop (MVP subset)

For this scenario, we use a constrained subset of the full Agent Decision Loop:

1. **Select focus goal**
   - Compute a score for each goal using:
     - `priority`, `urgency`, `horizon`, and simple personality/state modifiers.
   - Likely focus goals:
     - `MAINTAIN_SURVIVAL_TODAY` (when hunger/fatigue rise).
     - `REDUCE_POD_RISK` (for emerging leaders).
     - `GATHER_INFORMATION` (for scouts once assigned).
     - `FORM_GROUP` / `STABILIZE_POD` (in early steps).

2. **Recall relevant episodes**
   - For survival/movement:
     - Retrieve episodes tagged with current or adjacent locations.
   - For pod risk reduction:
     - Retrieve episodes involving podmates or corridor incidents near the pod.
   - For information gathering:
     - Retrieve previous scouting or hazard episodes related to target corridors.

3. **Generate candidate actions**
   - Hard-coded, small option set (sufficient for MVP):
     - Stay in pod (rest, socialize lightly).
     - Move along one outgoing edge (to corridor or hub).
     - Attend or initiate pod meeting (if in pod).
     - Attend or initiate multi-pod meeting (if at hub and other spokespeople present).

4. **Evaluate and choose action**
   - Use PlaceBelief.danger_score (if any) for candidate edges.
   - Personality influences:
     - Brave vs cautious weighting of danger.
     - Communal vs self-serving weighting of group vs personal risk.
   - For leaders:
     - Slight bias towards attending/initiating meetings and risk reduction actions.

5. **Execute action and log episode**
   - Movement:
     - Resolve possible hazard on traversed edge (see §5.3).
     - Create `Episode` with `event_type = MOVEMENT` and possibly `HAZARD_INCIDENT` or `HAZARD_NEAR_MISS`.
   - Meetings:
     - Create `COUNCIL_MEETING` or `POD_MEETING` episodes.
   - Protocol reading (later):
     - Create `READ_PROTOCOL` episodes.

6. **Update goals and beliefs**
   - Adjust goal progress and statuses where appropriate.
   - Update PlaceBeliefs about corridor danger scores when hazards occur.
   - For MVP, person and protocol beliefs can be minimal or omitted.


## 5.3 Hazard resolution

Whenever an agent traverses an edge E:

1. Determine `effective_hazard_prob`:
   - Start with edge `base_hazard_prob`.
   - Optionally adjust by:
     - Protocol compliance (e.g. traveling in groups may reduce hazard).
     - Time-of-cycle if modeled (e.g. night vs day tags).

2. Sample a Bernoulli trial:
   - If success (no incident): log movement without hazard.
   - If failure:
     - Create an `Episode`:
       - `event_type = HAZARD_INCIDENT`.
       - Negative valence, high arousal.
       - Linked to survival and/or risk-related goals.
     - Apply consequences:
       - Injury flag or temporary debuff.
       - For MVP, death can be rare or disabled; injury episodes are sufficient.

3. Update PlaceBelief for the corridor:
   - Increase `danger_score` for the owner agent.
   - Optionally, pod-level or council-level aggregated scores when episodes are shared.


# 6. Group and Protocol Mechanics

## 6.1 Pod-level grouping and spokespeople

### 6.1.1 Pod groups

Pods are implicit groups defined by bunk assignment:

- All agents in `loc:pod-X` share:
  - A `group:pod-X` identifier (conceptual).
  - Regular opportunities for pod meetings.

### 6.1.2 Pod meetings and leader emergence

At some cadence (e.g. every 20–40 ticks):

- A subset of pod members attend a **pod meeting**.
- During/after the meeting:
  - Each attendee internally updates a **competence score** for other podmates:
    - Based on:
      - Observed successful advice.
      - Relative LeadershipWeight attribute.
      - Past episodes where someone’s suggestion avoided hazards.
  - Each agent’s perceived best candidate is a local `spokesperson_candidate`.

If enough podmates converge on the same agent (above a threshold), that agent gains role:

```python
roles.append("POD_REPRESENTATIVE")
```

and is more likely to:

- Travel to the Well hub to coordinate.
- Focus on `REDUCE_POD_RISK` goals.


## 6.2 Proto-council formation

Whenever 2 or more `POD_REPRESENTATIVE` agents are present at `loc:well-core` in the same tick (or within a small time window):

- If no existing proto-council:
  - Instantiate:

    ```python
    group_id = "group:council:alpha"
    members = {rep_ids}
    ```

- Else:
  - Add representatives to the existing council up to a small cap.

The first council meeting produces `COUNCIL_MEETING` episodes for participants.

The proto-council immediately sets a group goal:

- `GATHER_INFORMATION` targeting:
  - Corridors with the highest aggregated hazard episodes, or
  - Corridors with the least information (few episodes tagged).

This uses the pattern aggregation logic sketched in `D-AGENT-0021` and `D-LAW-0010` in minimal form.


## 6.3 Scouting assignments

The `GATHER_INFORMATION` council goal is then:

- Projected into per-agent goals for assigned **scouts** and a **scribe**.

Selection heuristics:

- Preferred scouts:
  - Higher DEX/END and bravery, lower caution.
- Preferred scribes:
  - Higher INT/WIL and routine-seeking.

Agents with these roles:

- Bias goal selection toward scouting-related actions:
  - Leaving pods.
  - Traversing target corridors.
  - Returning to hub or pods to report findings.


## 6.4 Protocol authoring

At each council meeting after some scouting:

1. Aggregate hazard-related episodes referenced in recent `COUNCIL_MEETING` episodes.
2. Bucket them by `location_id` and `event_type = HAZARD_INCIDENT` / `HAZARD_NEAR_MISS`.
3. Compute a simple risk score per corridor:
   - Weighting frequency and severity.

If a corridor’s risk score exceeds `protocol_threshold`:

- Create a group-level `AUTHOR_PROTOCOL` goal with target:

```jsonc
{
  "protocol_type": "TRAFFIC_AND_SAFETY",
  "covered_locations": ["loc:corridor-7A"],
  "rule_payload": {
    "min_group_size": 2,
    "restricted_ticks": [0, 100],  // example
    "notes": "No solo travel at night-cycle."
  }
}
```

- On completion, register a `Protocol` object in a simple runtime registry.

## 6.5 Protocol adoption and effects

Agents “adopt” protocols when:

- They are present at a council/pod briefing, or
- They read a posted notice (simplified as an instantaneous event when in the same location).

This generates `READ_PROTOCOL` episodes and:

- Adds an entry to the agent’s internal `known_protocols` list.
- Sets an initial ProtocolBelief for that protocol:
  - For MVP, default to high enforcement and moderate burden.

When agents evaluate movement actions:

- They check for applicable protocols for the target edge/location.
- For MVP, we can use a very simple compliance rule, e.g.:

  - If agent knows protocol and:
    - It is not excessively burdensome (simple heuristics), and
    - Personality is not extremely rebellious,
  - Then the agent will comply.

Compliance adjusts `effective_hazard_prob`, e.g.:

- Traveling in group size ≥ 2 on corridor 7A halves the hazard probability.

The MVP’s success metric relies on this change in hazard probability.


# 7. Success Metrics and Reporting

## 7.1 MVP success criteria

A run of `founding_wakeup_mvp` is considered successful if:

1. **Pod-level social structure:**
   - Each pod has at least one agent with role `POD_REPRESENTATIVE`.

2. **Proto-council formation:**
   - At least one `group:council:*` exists with ≥ 2 representatives.

3. **Information-gathering goals:**
   - At least one `GATHER_INFORMATION` group goal is created and assigned.
   - At least one corridor is visited by scouts as part of this goal.

4. **Protocol authored and adopted:**
   - At least one `TRAFFIC_AND_SAFETY` protocol is authored by the proto-council.
   - At least 10% of agents receive `READ_PROTOCOL` episodes for this protocol.

5. **Risk reduction:**
   - For at least one corridor covered by a protocol:
     - Hazard incidents per 100 edge traversals **decrease** after protocol adoption versus before adoption.
   - This does not need to be statistically sophisticated; simple pre/post comparison is sufficient for MVP.

## 7.2 Scenario report structure

`ScenarioReport` for this MVP should include:

- Basic counts:
  - Number of pods.
  - Number of agents.
  - Number of spokespeople.
  - Number of councils formed.
  - Number of protocols authored.

- Hazard metrics per corridor:
  - `pre_protocol_hazard_incidents` (count and rate).
  - `post_protocol_hazard_incidents` (count and rate).
  - Number of traversals pre/post.

- Protocol adoption:
  - For each protocol:
    - Number of agents with `READ_PROTOCOL` episodes.
    - Number of agents complying vs violating, if modeled.

This report is intended both for:

- Human inspection (CLI/console).
- Future visualization/Unity front-end integration.


# 8. Non-Normative Implementation Notes

## 8.1 Engineering considerations

- Start with a **small agent count** (e.g. N = 40) for initial testing, then scale.
- Keep episode creation **sparse**:
  - Only log episodes for:
    - Movement across non-trivial edges.
    - Hazards (incident or clear near-miss).
    - Meetings.
    - Protocol read/adoption.
- Pattern updates (PlaceBeliefs) can be simple EMA or count-based; full Bayesian updates are not required for MVP.

## 8.2 Gradual refinement path

Once this MVP is stable, next steps may include:

- Adding **basic enforcement behavior**:
  - Pod reps or stewards scolding/persuading non-compliers.
- Extending risk space:
  - Suit failure probability.
  - Heat/cold stress near certain nodes.
- Introducing simple **resource abstraction**:
  - A generic “ration” metric that loosely couples to movement and survival.

All of these should reuse the same patterns:

- `Episodes → Patterns → Group Goals → Protocols → Episodes`, as defined in `D-LAW-0010`.

