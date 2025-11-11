---
title: ADR_0004 — Unify Barrel Cascade, Planner, and API Checklist
status: accepted
date: 2025-11-11
deciders: [cohayes]
supersedes: []
superseded_by: []
---

## Context
Water routing behavior and interfaces were split across:
- `Barrel_Cascade (v1.1)`
- `Barrel_Cascade_Planner (v1)`
- `Compact_API_Checklist (v1)`

The split introduced mismatched cadences, duplicated batch schemas, and unclear event ownership.

## Decision
Consolidate into **`docs/latest/09_interfaces/Hydraulic_Interfaces.md`** containing:
- Issuance cadence & routing
- Batch/Route schemas
- Planner heuristics and optimization hook
- Events & metrics (issued, delivered, royalty, incident)
- Runtime/Economy/World integrations

SemVer in front‑matter; versionless filename in `latest/`; legacy files archived as milestones.

## Consequences
**Positive**
- One contract for all hydraulic flows
- Stable events and cadences; easier conservation checks
- A/B planner swapping via a single interface

**Negative**
- Larger spec; requires clear anchors and examples

## Alternatives considered
- Keep Planner separate as a module → API drift risk
- Put Checklist in README only → tests lack a normative source

## Migration plan
1. Archive legacy docs to `docs/archive/09_interfaces/` with `-vX.Y.Z.md`.
2. Replace magic numbers with runtime constants.
3. Tag tests with `@pytest.mark.doc("D-INT-0003")`.

## Related
- `D-INT-0003` Hydraulic_Interfaces (new)
- `D-RUNTIME-0001` Simulation Runtime
- `D-ECON-0001` Economy
- `D-WORLD-0001` Environment
