---
title: ADR_0002 — Consolidate Rumor docs into a single Rumor_Systems spec
status: accepted
date: 2025-11-11
deciders: [cohayes]
supersedes: []
superseded_by: []
---

## Context
We had three closely related docs:
- `Rumors_and_Information (v1)`
- `Rumor_Credibility_Propagation (v1.1)`
- `Rumor_Stress_Scenarios (v1)`

They overlapped in scope (entities, lifecycle, equations) and were referenced together in tests and gameplay notes. This created duplication, split versioning, and review churn.

## Decision
Merge the three documents into **`docs/latest/08_info_security/Rumor_Systems.md`**. The unified spec contains:
- Lifecycle & data model
- Credibility mechanics (equations, parameters)
- Venue & faction modifiers
- Stress scenarios and a test checklist
- Runtime integration (phases, events, metrics)

File carries **SemVer in front‑matter**; filenames are versionless in `latest/`. Old files are archived as milestone snapshots.

## Consequences
**Positive**
- Single point of truth; easier test coverage & tuning
- Reduced duplication and broken cross‑links
- Independent versioning from other pillars

**Negative**
- Larger spec size (mitigated with a clear TOC)
- One PR can touch many sections

## Alternatives considered
- Keep three docs with strict cross‑links → still duplicate equations
- Move stress scenarios to a separate “playbook” → weaker coupling to the spec

## Migration plan
1. Archive legacy docs to `docs/archive/08_info_security/` with `-vX.Y.Z.md` suffix.
2. Add redirect stubs for one release cycle (optional).
3. Update tests to tag with `@pytest.mark.doc("D-INFOSEC-0001")`.
4. Update any README/indices to point to `Rumor_Systems.md`.

## Related
- `D-INFOSEC-0001` Rumor_Systems (new)
- `D-RUNTIME-0001` Simulation Runtime (timebase)
- `D-AGENT-0001` Agents Core
