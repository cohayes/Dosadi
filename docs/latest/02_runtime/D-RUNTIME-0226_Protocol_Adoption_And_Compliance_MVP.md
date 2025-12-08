---
title: Protocol_Adoption_And_Compliance_MVP
doc_id: D-RUNTIME-0226
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
---

# 02_runtime · Protocol Adoption & Compliance (MVP) — D-RUNTIME-0226

## 1. Purpose & scope

The Founding Wakeup MVP already supports:

- pod meetings and proto-council formation,
- council metrics over corridor hazards,
- protocol authoring for dangerous corridors (e.g. “group travel protocol”),
- scenario success checks for:
  - `proto_council_formed`,
  - `protocol_authored`,
  - `gather_information_goals`,
  - `protocol_adoption`,
  - `hazard_reduction`.

In current runs we see **`protocol_authored: OK`** but **`protocol_adoption: MISSING`**.  
Protocols exist and are marked `ACTIVE`, but nothing in runtime measures whether colonists **actually follow** them.

This document defines the minimal loop needed for protocol adoption to be meaningful in the Founding Wakeup MVP:

> protocol authored → expectations communicated → behaviour on covered edges measured → adoption metrics → scenario success check

Scope (MVP):

- Define **protocol-level adoption metrics** and simple per-tick updates.
- Define how **agent movement** on protocol-covered edges is classified as
  conforming or non-conforming.
- Define a **scenario-level success check** for `protocol_adoption`.
- Keep behaviour as simple as possible (no complex persuasion / defiance model).

Out of scope (future docs):

- Agent personality & faction-driven **willingness to comply**.
- Conflicting protocols and explicit protocol revocation.
- Player-facing UX around protocols and compliance graphs.

---

## 2. Entities & references

This document assumes the following already exist in the codebase/docs:

- `Protocol` dataclass (or equivalent) with:
  - `protocol_id: str`,
  - `protocol_type` / `field` (e.g. `ProtocolType.TRAFFIC_AND_SAFETY`),
  - `status` (e.g. `ProtocolStatus.ACTIVE`, `ProtocolStatus.REVOKED`),
  - `coverage` (edges/locations the protocol applies to),
  - `authored_at_tick: int`,
  - `authored_by_group_id: str`,
  - `content: str` / human-readable text.
- `ProtocolStatus` enum with at least `ACTIVE` (and possibly others).
- A world-level collection of protocols, e.g. `world.protocols: Dict[str, Protocol]`.
- Movement and location model where we can observe:
  - which agents are on which **edges/rooms** each tick,
  - which edges correspond to the protocol’s coverage.
- Founding Wakeup success criteria including a `protocol_adoption` flag.

We do **not** change how protocols are authored. We only add:

- a minimal **adoption metrics struct** attached to each protocol, and
- scenario logic to interpret those metrics.

---

## 3. Protocol adoption metrics

### 3.1 AdoptionMetrics struct

We introduce an internal helper struct to attach to each protocol:

```python
@dataclass
class ProtocolAdoptionMetrics:
    first_observed_tick: int | None = None
    last_observed_tick: int | None = None

    total_traversals: int = 0
    conforming_traversals: int = 0
    nonconforming_traversals: int = 0

    @property
    def adoption_ratio(self) -> float:
        if self.total_traversals == 0:
            return 0.0
        return self.conforming_traversals / float(self.total_traversals)
```

Each `Protocol` gains an optional `adoption: ProtocolAdoptionMetrics | None`
field, lazily initialised when the protocol first sees a traversal on its
coverage.

### 3.2 What counts as “traversal”?

In this MVP we define a **traversal** as:

> any tick where at least one colonist occupies a **covered edge** for a protocol.

Implementation detail:

- In the per-tick movement update, after agents move, we can derive:
  - `agents_by_edge: Dict[EdgeId, List[AgentId]]` for the current tick.
- For each ACTIVE protocol:
  - For each `edge_id` in `protocol.coverage.edges`:
    - look up `agents_by_edge.get(edge_id, [])`,
    - if non-empty, then each **agent on that edge** is counted as one traversal.

This gives us counts like “agent A traversed corridor 7A while the protocol was active”.

### 3.3 Conforming vs non-conforming (MVP)

For the Founding Wakeup “group travel protocol”, we assume the content describes
a simple rule like:

> “Travel in groups of at least 2 on these edges to reduce hazard risk.”

We define **conformance** in a purely mechanical way:

- When evaluating a particular edge and tick, we compute:
  - `group_size = len(agents_on_edge)`.
- Let `required_group_size` be a small integer, defaulting to 2 unless specified
  in the protocol metadata.
- For each agent on that edge at that tick:
  - If `group_size >= required_group_size` → **conforming traversal**.
  - Else → **non-conforming traversal**.

This yields per-protocol:

- `total_traversals` = conforming + nonconforming,
- `adoption_ratio` = conforming / total.

We do **not** require that agents know the protocol; we only measure **de facto behaviour**.
Knowledge and beliefs about protocols can be layered on later when we care about
why they comply or defect.

---

## 4. Runtime update hook

### 4.1 Per-tick adoption update

We add a small helper that runs once per tick after agent movement:

```python
def update_protocol_adoption_metrics(world: WorldState, current_tick: int) -> None:
    # Build mapping of edge -> agents present this tick
    agents_by_edge: Dict[str, List[AgentId]] = _index_agents_by_edge(world)

    for protocol in world.protocols.values():
        if protocol.status is not ProtocolStatus.ACTIVE:
            continue

        metrics = protocol.adoption or ProtocolAdoptionMetrics()
        protocol.adoption = metrics  # ensure attached

        for edge_id in protocol.coverage.edge_ids:
            agents_here = agents_by_edge.get(edge_id, [])
            if not agents_here:
                continue

            # First time we see traffic
            if metrics.first_observed_tick is None:
                metrics.first_observed_tick = current_tick

            metrics.last_observed_tick = current_tick

            group_size = len(agents_here)
            required_group_size = getattr(protocol, "required_group_size", 2)

            for _ in agents_here:
                metrics.total_traversals += 1
                if group_size >= required_group_size:
                    metrics.conforming_traversals += 1
                else:
                    metrics.nonconforming_traversals += 1
```

Where `_index_agents_by_edge(world)` is a small helper that consults agent
location state and returns the grouping.

### 4.2 Integration point

This function should be called from the main runtime loop **after** agent
movement and before the tick is committed, e.g. near:

- “apply movement results”
- “update council metrics and staffing”

Ordering isn’t critical as long as it runs consistently every tick once
protocols can become ACTIVE.

---

## 5. Scenario success: protocol_adoption

### 5.1 Intuition

For Founding Wakeup, we want `protocol_adoption` to become **OK** when:

- At least one `TRAFFIC_AND_SAFETY` protocol was authored for dangerous
  corridors (already captured by `protocol_authored: OK`), and
- After a small grace period, **most traversals** on those corridors are in
  compliance with the protocol (i.e., colonists are actually travelling in groups).

We don’t require perfect compliance; we just need evidence that the protocol has
**meaningfully changed behaviour**.

### 5.2 Helper: _protocol_adoption_ok(world, cfg)

We define a helper in the Founding Wakeup report builder:

```python
def _protocol_adoption_ok(world: WorldState, cfg: FoundingWakeupRuntimeConfig) -> bool:
    # 1. Collect candidate protocols (e.g. traffic & safety on dangerous corridors)
    protocols = [
        p
        for p in world.protocols.values()
        if p.status is ProtocolStatus.ACTIVE
        and getattr(p, "field", None) == ProtocolType.TRAFFIC_AND_SAFETY
    ]

    if not protocols:
        return False

    # 2. Filter to protocols that actually saw some traffic
    candidates: List[Protocol] = []
    for p in protocols:
        m = getattr(p, "adoption", None)
        if m is None or m.total_traversals < cfg.min_traversals_for_adoption_check:
            continue
        # Optional: ensure some time passed since authored
        if m.last_observed_tick is not None and (
            m.last_observed_tick - p.authored_at_tick
            < cfg.min_ticks_since_authored_for_adoption_check
        ):
            continue
        candidates.append(p)

    if not candidates:
        return False

    # 3. Compute aggregate adoption
    total_traversals = sum(p.adoption.total_traversals for p in candidates)
    conforming_traversals = sum(p.adoption.conforming_traversals for p in candidates)

    if total_traversals == 0:
        return False

    ratio = conforming_traversals / float(total_traversals)
    return ratio >= cfg.min_protocol_adoption_ratio
```

Suggested config additions on `FoundingWakeupRuntimeConfig`:

```python
class FoundingWakeupRuntimeConfig:
    ...
    min_traversals_for_adoption_check: int = 20
    min_ticks_since_authored_for_adoption_check: int = 200
    min_protocol_adoption_ratio: float = 0.6
```

Interpretation:

- Ignore protocols that never saw traffic or were authored too recently.
- Once enough traversals have occurred, require that at least 60% of them
  follow the rule (travel in groups of 2+).

### 5.3 Wiring into the scenario report

The scenario report builder (for `run_founding_wakeup_mvp`) should:

- call `_protocol_adoption_ok(world, cfg)`,
- set the `protocol_adoption` flag to `"OK"` if it returns true, `"MISSING"` otherwise.

For debugging and dashboards, it is useful but optional to dump:

- per-protocol `total_traversals`, `conforming_traversals`, `adoption_ratio`,
- which edges each protocol covers.

---

## 6. Minimal agent-facing expectations (optional for MVP)

The above logic uses only **observed behaviour**; agents can be following the
rule by accident. For the MVP, that’s acceptable.

If desired, a small additional piece of glue can be added:

- when a protocol is authored by the council, emit a short-lived “announcement”
  episode in each pod / ward, tagged with the protocol id;
- when agents are choosing work or routes, they can check for “local protocols”
  and bias toward group movement (e.g., prefer stepping onto a corridor when
  another agent is present or nearby).

These would live in separate docs (e.g. Protocol Communication & Local Norms)
and are not required for `protocol_adoption` to flip to OK in the current spec.

---

## 7. Test checklist

After implementing this document, a typical Founding Wakeup run should show:

1. A `TRAFFIC_AND_SAFETY` protocol is authored for dangerous corridors
   (as already happens; `protocol_authored: OK` remains OK).
2. Agents move through those corridors over many ticks, often in small groups.
3. `ProtocolAdoptionMetrics` on that protocol show non-zero
   `total_traversals`, with a majority conforming.
4. The `_protocol_adoption_ok` helper returns true once thresholds are met.
5. The scenario report printed by `run_founding_wakeup_mvp.py` shows:
   - `protocol_authored: OK`
   - `protocol_adoption: OK`

This closes the second missing success criterion for the Founding Wakeup MVP.
