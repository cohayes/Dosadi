---
title: ADR_0005 — Timebase as D-RUNTIME-0001; Runtime Orchestrator as D-RUNTIME-0002
status: accepted
date: 2025-11-11
deciders: [cohayes]
---

## Context
The existing Simulation Runtime doc mixes orchestration details with timing/cadence constants. We introduced a dedicated Timebase spec.

## Decision
- Assign **D-RUNTIME-0001** to **Simulation_Timebase** (source of truth for cadences).
- Move orchestration/scheduler to **Simulation_Runtime (D-RUNTIME-0002)** and make it depend on the Timebase.

## Consequences
- Clear single source for cadences (no magic numbers).
- Runtime doc becomes slimmer and easier to maintain.

## Migration
- Update headers & cross-links.
- Replace literal cadence checks in code with imports from the Timebase module.
