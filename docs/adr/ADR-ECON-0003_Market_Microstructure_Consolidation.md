---
title: ADR_Market_Microstructure_Consolidation
doc_id: ADR-ECON-0003
version: 1.0.0
status: accepted
owners: [cohayes]
last_updated: 2025-11-17
---

# ADR: Consolidating Dosadi Market Microstructure v1 into v1.1

## 1. Context

An earlier version of `D-ECON-0002_Dosadi_Market_Microstructure` was drafted as a
first-pass sketch of how prices and venues work on Dosadi. Since then:

- `D-ECON-0001_Ward_Resource_and_Water_Economy` has become the canonical spec
  for ward-level water and resource budgets.
- New or planned docs clarify related domains:
  - Credits & FX
  - Work & Labor Markets
  - Food & Rations Flow
  - Maintenance & Production
  - Financial Ledgers & Taxation
  - Telemetry, Espionage, Scholars & Clerks.

The original Market Microstructure content:

- Mixed older nomenclature (e.g. references to the previous `Dosadi_Economic_Systems`).
- Did not explicitly tie into the new water-first econ stack and information docs.
- Was still structurally aligned enough to be **revised in place** rather than archived.

## 2. Decision

We will:

1. **Keep `D-ECON-0002` as the canonical Market Microstructure doc**, preserving
   its ID and file location.

2. **Update its content to v1.1**, with:
   - An explicit dependency on `D-ECON-0001_Ward_Resource_and_Water_Economy`.
   - Clear integration points with:
     - Credits/FX, Ledgers & Taxation, Telemetry & Audit,
       and the information/espionage pillar.
   - A tightened scope:
     - Focus on venues, order types, mid-price & spread formation,
       matching logic, enforcement, and simulation hooks.

3. **Avoid creating a legacy/archived copy**:
   - Changes are **incremental and clarifying**, not a wholesale conceptual replacement.
   - Git history / version control already preserves the v1 text if needed.

## 3. Alternatives Considered

### Option A – Archive v1 as a legacy doc

We could have:

- Moved the older v1 content into a new `D-ECON-0200_Market_Microstructure_Legacy`
  in `docs/archive/04_economy/`.
- Created a fresh `D-ECON-0002` from scratch.

This was rejected because:

- The conceptual core of v1 (venues, spreads, and microstructure) remains valid.
- Most changes are about **wiring** it cleanly into the new water-first,
  information-heavy architecture.

### Option B – Fold Market Microstructure into a larger “Economic Systems” doc

We could have:

- Absorbed all microstructure details into a single, broader economic design.

This was rejected because:

- It conflicts with the emerging pattern of narrow, simulation-facing docs.
- A monolithic econ doc would be harder to use as a direct spec for code.

## 4. Consequences

### Positive

- `D-ECON-0002` remains stable as the ID for Market Microstructure.
- The doc now:
  - Explicitly depends on `D-ECON-0001_Ward_Resource_and_Water_Economy`.
  - Exposes clear hooks to credits, labor, ledgers, and telemetry.
- Simulation implementations get:
  - A cleaner, self-contained microstructure spec for venues, quotes, and flows.

### Negative / Tradeoffs

- Readers familiar with the older v1 text will need to adjust to:
  - The new dependencies and slightly different parameterization.
- Some informal notes or out-of-repo references to “v1” phrasing may linger
  until they are manually updated.

## 5. Implementation Notes

- Update `D-ECON-0002_Dosadi_Market_Microstructure.md` in-place to the v1.1 text.
- Ensure its front-matter:
  - `version: 1.1.0`, `status: draft`.
- When related econ / info docs are edited:
  - Consider adding cross-links back to `D-ECON-0002` wherever local prices,
    spreads, or venues are discussed.

This ADR documents the consolidation so future readers understand why the Market
Microstructure doc's semantics evolved without an accompanying ID change.
