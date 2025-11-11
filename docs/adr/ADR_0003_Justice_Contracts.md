---
title: ADR_0003 — Merge Law/Contracts/Case Evidence into Justice_Contracts
status: accepted
date: 2025-11-11
deciders: [cohayes]
supersedes: []
superseded_by: []
---

## Context
Legal machinery spanned three docs:
- `Law_and_Contract_Systems (v1)`
- `Contract_and_Case_State_Machines (v1)`
- `Case_Evidence_Scoring (v1)`

Readers had to bounce between files for a single case. Version drift emerged across state diagrams, evidence thresholds, and remedies.

## Decision
Create **`docs/latest/07_law/Justice_Contracts.md`** as the single operational spec covering:
- Contract schema & lifecycle
- Case workflow/state machines
- Evidence scoring & thresholds
- Events and economy/security hooks

The doc uses **SemVer** in front‑matter and lives versionless in `latest/`; prior variants are archived as milestones.

## Consequences
**Positive**
- End‑to‑end traceability from breach to judgment
- Cleaner interface to economy/security
- Fewer duplicate tables/thresholds

**Negative**
- Bigger doc; reviewers must use section anchors
- Tighter coupling between subtopics (mitigated by headings)

## Alternatives considered
- Keep three docs with a “hub” README → links still drift and tables duplicate
- Split evidence into a standalone appendix → increased indirection

## Migration plan
1. Archive legacy docs to `docs/archive/07_law/` with `-vX.Y.Z.md`.
2. Update cross‑refs to `Justice_Contracts.md`.
3. Tag tests with `@pytest.mark.doc("D-LAW-0002")`.

## Related
- `D-LAW-0002` Justice_Contracts (new)
- `D-RUNTIME-0001` Simulation Runtime
- `D-ECON-0001` Economy
