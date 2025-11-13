---
title: Hydraulic_Interfaces
doc_id: D-INTERFACE-0001
version: 1.2.0
status: draft
owners: [cohayes]
last_updated: 2025-11-11
depends_on:
  - D-RUNTIME-0001   # scheduler/timebase
  - D-ECON-0001      # economy (royalties, pricing, penalties)
  - D-WORLD-0001     # environment dynamics (loss, leakage)
previous:
  - D-INTERFACE-0001       # Compact API Checklist (rolled in here)
---

# Overview
Consolidates **Barrel_Cascade (v1.1)**, **Barrel_Cascade_Planner (v1)**, and **Compact_API_Checklist (v1)** into a single interface spec defining how water is issued, routed, delivered, and accounted across the world model.

## Scope
- Issuance cadence and routing.
- Delivery, leakage, and incidents.
- Planner heuristics and optimization hooks.
- APIs/events for integration with runtime and economy.

---

## Interfaces (Inputs/Outputs)
### Inputs
- **Supply**: well output, storage levels, policy caps.
- **Demand**: ward requests, priority queues, emergency flags.
- **Constraints**: route capacity, loss coefficients, security risk.
- **Timebase**: cadence from runtime (no magic numbers).

### Outputs
- **Events**:
  - `BarrelCascadeIssued {batch_id, qty, routes, eta}`
  - `BarrelDelivered {batch_id, ward, qty, slippage}`
  - `RoyaltyCollected {ward, qty, credits}`
  - `SecurityIncidentCreated {route, type, severity}`
- **Metrics**: fill rates, losses, delays, reliability index.

**Contracts**
- Units: barrels (B), credits (C); specify decimals and conversion if used.
- All batches carry `ttl`; expired batches are reclaimed or lost.

---

## Data & Schemas
### Batch
| field | type | notes |
|---|---|---|
| batch_id | UUID | |
| qty | float | barrels |
| route | path | sequence of edges |
| eta | ticks | expected arrival |
| ttl | ticks | shelf life |
| policy_tag | enum | rationing, relief, market |

### Route edge
| field | type | notes |
|---|---|---|
| edge_id | UUID | |
| capacity | float | barrels per tick |
| loss | float | [0,1] |
| risk | enum | NONE, THEFT, SABOTAGE |

---

## Planner (Algorithms)
### Heuristic baseline
1. Rank wards by priority = `need_index * legitimacy_weight * reliability`.
2. Satisfy base quotas; allocate surplus by marginal utility per barrel.
3. Route with minimum expected loss; if tie, prefer lower risk.

### Optimization hook (optional)
- Provide interface `optimize(routes, supply, demand, constraints) -> plan`.
- Must return a plan compatible with the batch schema.

### Incident handling
- On loss spike or risk event, emit `SecurityIncidentCreated` and re-route remaining qty if capacity allows.

---

## Runtime Integration
- **Phases**: Issuance (DAILY), Transit (per tick), Accounting (DAILY).
- **Timebase**: All cadences derived from runtime constants—no hard-coded literals.
- **Economy hooks**: royalties and penalties posted to ledgers/FX indices.
- **World hooks**: leakage updates environment balance (humidity, etc.).

---

## Examples & Test Notes
- **Shortage day**: cap issuance; verify fair allocation by priority formula.
- **Route failure**: force high loss on edge → incident + re-route.
- **A/B planner**: swap heuristic with optimizer; events/metrics remain consistent.

### Test checklist
- ✓ No batch without `ttl`.
- ✓ Sum delivered + lost ≤ issued (conservation).
- ✓ Royalty equals policy rate × delivered qty.

---

## Open Questions
- Should emergency deliveries preempt royalty collection?
- How do we persist in-flight batches across save/load?

## Changelog
- 1.2.0 — Merge of Barrel_Cascade (v1.1), Planner (v1), and Compact API Checklist (v1).

