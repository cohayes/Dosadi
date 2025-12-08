---
title: Hazard_Reduction_Metrics_And_Success_Check_MVP
doc_id: D-RUNTIME-0227
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-08
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0213   # Work_Detail_Behaviors_MVP_Scout_And_Inventory
  - D-RUNTIME-0214   # Council_Metrics_And_Staffing_Response_MVP
  - D-RUNTIME-0218   # Hydration_And_Water_Access_MVP
  - D-RUNTIME-0225   # Gather_Information_Goals_And_Scouting_MVP
  - D-RUNTIME-0226   # Protocol_Adoption_And_Compliance_MVP
  - D-SCEN-0002      # Founding_Wakeup_Spec
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
  - D-AGENT-0023     # Agent_Goal_System_v0
  - D-AGENT-0024     # Agent_Decision_Loop_v0
  - D-AGENT-0025     # Groups_And_Councils_MVP
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
---

# 02_runtime · Hazard Reduction Metrics & Success Check (MVP) — D-RUNTIME-0227

## 1. Purpose & scope

In the Founding Wakeup MVP we now have:

- **Information loop**: dangerous corridors → gather-information goals → scouting.
- **Norms loop**: dangerous corridors → traffic & safety protocol → protocol adoption metrics.

The remaining scenario flag, `hazard_reduction`, is still **MISSING**.

This document defines a minimal, mechanical notion of “hazard reduction”:

> measure hazardous incident rates on targeted corridors **before** council action,  
> measure them again **after** information + protocol adoption,  
> consider the scenario successful if hazard rates **drop enough** on those corridors.

Scope (MVP):

- Define simple **edge-level hazard rate metrics** derived from existing council statistics.
- Define a small amount of state to capture **“before” and “after”** hazard snapshots.
- Define the **scenario-level `hazard_reduction` success check**.
- Keep the implementation local to the runtime/reporting layer.

Out of scope (future docs):

- Complex causal attribution (which protocol / crew / repair caused the reduction).
- Spatial spillover (hazard shifting to neighbouring edges).
- Agent beliefs or fear/stress feedback loops.

---

## 2. Entities & references

We build directly on:

- Council metrics (D-RUNTIME-0214):
  - `world.council_metrics.hazard_incidents_by_edge[edge_id]: int`
  - `world.council_metrics.traversals_by_edge[edge_id]: int`
  - Optional: `world.council_metrics.dangerous_edges: set[str]`
- Protocol model & adoption (D-RUNTIME-0226):
  - `Protocol` objects with fields like:
    - `protocol_id`, `field` (e.g. `ProtocolType.TRAFFIC_AND_SAFETY`),
    - `status` (`ProtocolStatus.ACTIVE`),
    - `coverage.edge_ids: list[str]`,
    - `authored_at_tick: int`,
    - `adoption: ProtocolAdoptionMetrics`.
- Scenario config (D-SCEN-0002 + runtime config):
  - `success_criteria.require_hazard_reduction: bool`.

We assume that council metrics are already updated **once per tick** before
the end-of-tick reporting snapshot.

---

## 3. Edge-level hazard rate

### 3.1 Definition

For any edge `e`, define its **cumulative hazard rate** at tick `t` as:

```text
hazard_rate(e, t) = hazard_incidents_by_edge[e] / max(1, traversals_by_edge[e])
```

Intuition: “What fraction of traversals of this edge have resulted in
hazard incidents so far?”

- This is deliberately **simple and cumulative** for the MVP.
- Later we can add rolling windows or weighted recency.

### 3.2 Dangerous edges of interest

We are only interested in edges that:

- were deemed **dangerous** by council metrics at some point in the run, and
- are covered by at least one **traffic & safety protocol**.

Concretely, we define the set:

```text
TargetEdges = union over all ACTIVE traffic & safety protocols of their coverage.edge_ids
```

Optionally intersect this with `world.council_metrics.dangerous_edges` if that
field exists; otherwise assume all protocol-covered edges were problematic.

---

## 4. Hazard snapshots: before vs after

We need a way to compare “before” and “after” hazard rates for `TargetEdges`.

### 4.1 Snapshot struct

We introduce a lightweight struct used only by the Founding Wakeup runtime:

```python
@dataclass
class HazardSnapshot:
    tick: int
    hazard_rate_by_edge: dict[str, float]
```

These snapshots do **not** need to be on `WorldState`; they can live in the
scenario runner that builds the report, or be stored in a small
`world.runtime_bookkeeping` field if convenient.

### 4.2 When to take snapshots (MVP)

For MVP we use **two** snapshots per run:

1. **Baseline hazard snapshot** (`baseline`):

   - Taken at or near the time the first **traffic & safety protocol** is authored.
   - Implementation: when the first matching protocol is observed, we compute:

     ```python
     baseline = HazardSnapshot(
         tick=current_tick,
         hazard_rate_by_edge=_compute_hazard_rates_for_target_edges(world)
     )
     ```

   - This freeze-frames “how bad it was when we first decided we needed rules”.

2. **Final hazard snapshot** (`final`):

   - Taken at the **end of the run**, just before we build the `ScenarioReport`.
   - Implementation: reuse the same helper:

     ```python
     final = HazardSnapshot(
         tick=current_tick,
         hazard_rate_by_edge=_compute_hazard_rates_for_target_edges(world)
     )
     ```

We don’t need intermediate snapshots for MVP; we only ask “did it get better by the end?”

### 4.3 Helper: compute hazard rates for target edges

We define a small helper (in the scenario runtime module):

```python
def _compute_hazard_rates_for_target_edges(world: WorldState) -> dict[str, float]:
    from collections import defaultdict

    # Identify target edges from active traffic & safety protocols
    target_edges: set[str] = set()
    for p in world.protocols.values():
        if p.status is not ProtocolStatus.ACTIVE:
            continue
        if getattr(p, "field", None) != ProtocolType.TRAFFIC_AND_SAFETY:
            continue
        for eid in p.coverage.edge_ids:
            target_edges.add(eid)

    rates: dict[str, float] = {}
    for edge_id in target_edges:
        incidents = world.council_metrics.hazard_incidents_by_edge.get(edge_id, 0)
        traversals = world.council_metrics.traversals_by_edge.get(edge_id, 0)
        if traversals <= 0:
            # No traffic = undefined rate. For MVP, treat as 0.0 so we don't blow up.
            rate = 0.0
        else:
            rate = incidents / float(traversals)
        rates[edge_id] = rate

    return rates
```

This helper is used for both baseline and final snapshots.

---

## 5. Scenario success: hazard_reduction

### 5.1 Intuition

We want `hazard_reduction: OK` when **on average**, the hazard rate on protocol-covered edges is **significantly lower** at the end of the run than at baseline.

We do not require complete elimination of hazard; we only need clear evidence
that the combination of:

- scouting,
- council action, and
- protocol adoption

has reduced harm on the corridors we care about.

### 5.2 Config knobs

Add to `FoundingWakeupRuntimeConfig`:

```python
class FoundingWakeupRuntimeConfig:
    ...
    min_edges_for_hazard_check: int = 1
    min_baseline_hazard_rate: float = 0.05   # below this, we don't demand reduction
    min_hazard_reduction_fraction: float = 0.30  # require at least 30% drop
```

Interpretation:

- If baseline hazard is extremely low already (< 5%), we don’t demand a reduction.
- Otherwise we require the final average hazard to be at most:
  - `(1 - min_hazard_reduction_fraction) * baseline_avg`.

### 5.3 Helper: _hazard_reduction_ok(baseline, final, cfg)

In the scenario report builder, after you have computed `baseline` and `final`,
add a helper:

```python
def _hazard_reduction_ok(
    baseline: HazardSnapshot | None,
    final: HazardSnapshot | None,
    cfg: FoundingWakeupRuntimeConfig,
) -> bool:
    # Require both snapshots
    if baseline is None or final is None:
        return False

    # Edge set: union of edges in both snapshots
    edges = set(baseline.hazard_rate_by_edge.keys()) | set(final.hazard_rate_by_edge.keys())
    if len(edges) < cfg.min_edges_for_hazard_check:
        return False

    # Compute baseline and final averages
    baseline_vals = [baseline.hazard_rate_by_edge.get(e, 0.0) for e in edges]
    final_vals = [final.hazard_rate_by_edge.get(e, 0.0) for e in edges]

    if not baseline_vals:
        return False

    baseline_avg = sum(baseline_vals) / float(len(baseline_vals))
    final_avg = sum(final_vals) / float(len(final_vals))

    # If baseline hazard was trivial, don't demand a reduction
    if baseline_avg < cfg.min_baseline_hazard_rate:
        # Edge case: if final_avg is catastrophic, you might still choose to fail;
        # MVP: treat this as OK because there was no real problem to solve.
        return True

    # Require at least configured fractional reduction
    required_max_final = baseline_avg * (1.0 - cfg.min_hazard_reduction_fraction)
    return final_avg <= required_max_final
```

### 5.4 Wiring into the scenario run

You need somewhere to capture and pass `baseline` and `final` snapshots. A simple approach inside `run_founding_wakeup_mvp`:

- Initialise `baseline_snapshot: HazardSnapshot | None = None`.
- Each tick, when you detect the **first** `TRAFFIC_AND_SAFETY` protocol being authored (or first time an ACTIVE one appears), if `baseline_snapshot is None`:

  ```python
  baseline_snapshot = HazardSnapshot(
      tick=current_tick,
      hazard_rate_by_edge=_compute_hazard_rates_for_target_edges(world),
  )
  ```

- At the end of simulation (just before building `ScenarioReport`):

  ```python
  final_snapshot = HazardSnapshot(
      tick=current_tick,
      hazard_rate_by_edge=_compute_hazard_rates_for_target_edges(world),
  )
  ```

- The report builder then calls:

  ```python
  hazard_ok = _hazard_reduction_ok(baseline_snapshot, final_snapshot, cfg)
  success_flags.hazard_reduction = "OK" if hazard_ok else "MISSING"
  ```

For debugging, the report can optionally print the baseline vs final averages.

---

## 6. Interaction with other success flags

The scenario already has success checks for:

- `protocol_authored` (at least one relevant protocol exists),
- `protocol_adoption` (behaviour aligns with protocol on covered edges),
- `gather_information_goals` (scouting loop fired at least once).

For Founding Wakeup we recommend:

- Only mark `hazard_reduction: OK` when those other three also succeed.
- Or, more loosely, allow `hazard_reduction` to be evaluated independently but
  interpret all four flags together when deciding “scenario success”.

This document does **not** prescribe a hard policy for “overall victory”;
it only defines the `hazard_reduction` flag itself.

---

## 7. Test checklist

After implementing this document, a typical successful Founding Wakeup run should show:

1. Dangerous corridors are detected and cause council action.
2. Gather-information goals are created and scouts visit the relevant edges.
3. A traffic & safety protocol covers those corridors and adoption metrics show agents often travelling in groups.
4. A baseline hazard snapshot is taken near the time the first such protocol is authored.
5. A final hazard snapshot is taken at the end of the run.
6. The final average hazard rate on protocol-covered edges is significantly lower than the baseline average.
7. The scenario report prints:

   ```text
   Scenario success checks:
   - pod_leadership: OK
   - proto_council_formed: OK
   - gather_information_goals: OK
   - protocol_authored: OK
   - protocol_adoption: OK
   - hazard_reduction: OK
   ```

This completes the third missing piece for the Founding Wakeup MVP’s
“danger discovered → information → norms → safer corridors” loop.
