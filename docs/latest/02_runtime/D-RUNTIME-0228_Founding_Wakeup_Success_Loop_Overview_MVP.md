---
title: Founding_Wakeup_Success_Loop_Overview_MVP
doc_id: D-RUNTIME-0228
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-08
depends_on:
  - D-SCEN-0002      # Founding_Wakeup_Spec
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0214   # Council_Metrics_And_Staffing_Response_MVP
  - D-RUNTIME-0225   # Gather_Information_Goals_And_Scouting_MVP
  - D-RUNTIME-0226   # Protocol_Adoption_And_Compliance_MVP
  - D-RUNTIME-0227   # Hazard_Reduction_Metrics_And_Success_Check_MVP
---

# 02_runtime · Founding Wakeup Success Loop Overview (MVP) — D-RUNTIME-0228

## 1. Purpose

The **Founding Wakeup** scenario is meant to showcase one complete, closed loop:

> **danger discovered → information gathering → norms & protocols → safer corridors**

Several runtime docs specify pieces of this loop:

- **D-RUNTIME-0214** — council hazard metrics & staffing.
- **D-RUNTIME-0225** — gather-information goals & scouting.
- **D-RUNTIME-0226** — protocol adoption & compliance.
- **D-RUNTIME-0227** — hazard reduction metrics & success check.

This document ties them together and defines a single, scenario-level view of
“success” for the Founding Wakeup MVP.

It is intentionally **narrative + contracts**, not new code.

---

## 2. Success flags at a glance

The Founding Wakeup report exposes the following boolean flags:

- `pod_leadership`
- `proto_council_formed`
- `gather_information_goals`
- `protocol_authored`
- `protocol_adoption`
- `hazard_reduction`

The first two flags are about **institutional bootstrapping**:

- `pod_leadership`: each pod has at least one awake colonist in a leadership role.
- `proto_council_formed`: a proto-council exists at the well core with a handful of
  members plus at least one scribe.

The remaining four flags are about **corridor safety**:

1. `gather_information_goals` — did the council create a gather-information goal and
   actually send scouts?
2. `protocol_authored` — did the council author at least one traffic & safety protocol
   to address dangerous corridors?
3. `protocol_adoption` — did colonists’ behaviour on protocol-covered edges actually
   shift toward compliance (e.g. group travel)?
4. `hazard_reduction` — did the hazard rate on those edges go down by a meaningful
   fraction between baseline and end of run?

This document asserts that the **Founding Wakeup MVP is “narratively successful”**
precisely when **all** of these are true in the same run.

---

## 3. The corridor safety loop

### 3.1 Discovery

Input:

- Agents move around pods and corridors.
- Hazard episodes (falls, conflicts, accidents) are emitted and counted as
  `hazard_incidents_by_edge`.
- Traversals of edges are counted as `traversals_by_edge`.

Council metrics (D-RUNTIME-0214):

- Compute hazard rates per edge.
- Flag edges with incident rates above a threshold as **dangerous**.
- Provide read-only metrics back to the council process.

There is no success flag here; these metrics are just **fuel** for the loop.

### 3.2 Information gathering (`gather_information_goals`)

In D-RUNTIME-0225, when dangerous corridors appear, the council can:

1. Create a **group-level `GATHER_INFORMATION` goal** that names the target edges.
2. Project that goal onto a handful of **scout agents** as agent-level goals.
3. Use `SCOUT_INTERIOR` behaviour to bias those scouts to traverse the dangerous
   edges on purpose and emit **hazard-inspection episodes**.

The `gather_information_goals` flag is `OK` when at least one such group-level goal
has at least one child agent goal with recorded scouting visits.

Narrative interpretation:

- “The council noticed danger and deliberately sent people to learn more, rather
  than guessing from a distance.”

### 3.3 Norms & protocols (`protocol_authored`, `protocol_adoption`)

In D-RUNTIME-0214 and D-RUNTIME-0226, the council uses that information to decide
on a protocol, typically in the `TRAFFIC_AND_SAFETY` field. For Founding Wakeup,
the flagship example is a **group travel protocol** covering specific corridors.

Two flags measure this phase:

- `protocol_authored` (existing):
  - At least one relevant protocol exists and is `ACTIVE`.
- `protocol_adoption` (D-RUNTIME-0226):
  - Runtime tracks how often colonists traverse the protocol’s edges and whether
    they do so in **groups of size ≥ N** (MVP default 2).
  - Once enough traversals have occurred, if at least `min_protocol_adoption_ratio`
    (default 60%) of them are conforming, the flag becomes `OK`.

Narrative interpretation:

- “The council didn’t just talk; it created norms. Colonists followed them often
  enough that behaviour on dangerous corridors is measurably different.”

### 3.4 Outcomes (`hazard_reduction`)

Finally, D-RUNTIME-0227 compares hazard rates **before** and **after** council action.

- When the first relevant protocol is authored, we take a **baseline snapshot** of
  hazard rates on protocol-covered edges.
- At the end of the run, we take a **final snapshot**.
- If the baseline hazard was non-trivial and the final average hazard rate across
  those edges is at least `min_hazard_reduction_fraction` (e.g. 30%) lower, the
  `hazard_reduction` flag is `OK`.

Narrative interpretation:

- “The corridors under protocol are genuinely safer by the end of the scenario.”

---

## 4. Scenario-level “success” definition (MVP)

For the Founding Wakeup MVP, this document recommends the following **overall
success** predicate for the scenario:

```text
ScenarioSuccess =
    pod_leadership
    and proto_council_formed
    and gather_information_goals
    and protocol_authored
    and protocol_adoption
    and hazard_reduction
```

That is, the run is considered successful if:

1. **Local organisation exists**: pods have leadership and a proto-council exists.
2. **Information is gathered deliberately** about dangerous corridors.
3. **Norms and protocols** are created in response.
4. **Behaviour changes** in line with those protocols.
5. **Hazards actually decrease** on the relevant corridors.

This predicate is deliberately strict for the MVP; later scenarios can loosen it
(e.g. partial success, trade-offs, or branching outcomes).

The core requirement is that a single Founding Wakeup run can, in principle,
demonstrate the entire chain from “everyone wakes up” to “corridors under council
care are measurably safer”.

---

## 5. Implementation notes

This document does not introduce new data structures; it only fixes expectations
about how existing docs interact. Concretely:

- `pod_leadership` and `proto_council_formed` are computed exactly as in
  D-RUNTIME-0200 and related docs.
- `gather_information_goals` is computed via the helper specified in
  D-RUNTIME-0225, based on group- and agent-level `GATHER_INFORMATION` goals.
- `protocol_authored` is computed as in the existing Founding Wakeup spec
  (D-SCEN-0002 / D-RUNTIME-0200).
- `protocol_adoption` is computed via per-protocol adoption metrics, as in
  D-RUNTIME-0226.
- `hazard_reduction` is computed via baseline/final hazard snapshots as in
  D-RUNTIME-0227.

The only additional step required by this document is:

- The scenario runner (or report builder) should expose an **overall success**
  view, either as:
  - a top-level boolean `scenario_success`, or
  - a derived field in the CLI/printout that reports whether **all** of the above
    flags are `OK`.

Example CLI snippet:

```text
Scenario success checks:
- pod_leadership: OK
- proto_council_formed: OK
- gather_information_goals: OK
- protocol_authored: OK
- protocol_adoption: OK
- hazard_reduction: OK

Overall scenario success: OK
```

---

## 6. Test & demo expectations

Once all referenced docs are implemented, a “golden path” Founding Wakeup run
used for demos or regression tests SHOULD satisfy:

- All six success flags are `OK`.
- Council logs / episodes clearly show:
  - detection of dangerous corridors,
  - creation of at least one gather-information goal,
  - assignment of scouts,
  - authoring of a traffic & safety protocol,
  - significant adoption of that protocol,
  - lower hazard rates on protocol-covered corridors at the end.

This provides a concrete, minimal demonstration that the Dosadi runtime can:
detect danger, organise collective response, change behaviour, and measure
outcomes — all without external deus ex machina interventions after tick 0.
