---
title: ADR_Ward_Water_Economy_Doc_Refactor
doc_id: ADR-ECON-0002
version: 1.0.0
status: accepted
owners: [cohayes]
last_updated: 2025-11-17
---

# ADR: Repurposing D-ECON-0001 for Ward Resource & Water Economy

## 1. Context

The existing economic document **`D-ECON-0001_Economic_Systems`** in `docs/04_economy`
was written as an early, broad sketch of Dosadi's economy. Since then:

- The project has converged on **water as the master constraint**, with:
  - Highly engineered, hyper-dry atmosphere.
  - Moisture capture (bunkhouses, condensers) as core to survival.
- We have begun drafting more **focused economic and para-economic docs**:
  - `D-SOC-0002_Food_Waste_and_Metabolism` (placeholder)
  - `D-SOC-0003_Logistics_Corridors_and_Safehouses` (placeholder)
  - `D-FIN-XXXX_Financial_Ledgers_and_Taxation` (planned/ongoing)
  - Black market & espionage docs that treat water as a prime traded good.

The original `Economic_Systems` doc mixes several concerns:

- High-level narrative of credits, markets, and class structure.
- Early, partially superseded assumptions about how scarcity is expressed.
- Little explicit structure for **ward-level water budgets**, which now clearly
  need their own canonical home.

We want:

- `D-ECON-0001` to become the **canonical, simulation-facing specification**
  of ward-level **water and tightly coupled resources**, which sit at the root
  of all other economic behavior.
- The older `Economic_Systems` content to be preserved as **historical / concept
  material**, but **not** treated as the primary spec.

## 2. Decision

We will:

1. **Create a new primary economic spec**:

   - `D-ECON-0001_Ward_Resource_and_Water_Economy`
   - Lives in `docs/04_economy/` (or equivalent econ folder).
   - Defines:
     - Planet → ward → branch → facility water allocations.
     - Moisture capture, recycling, and black-market diversion.
     - Ward-level water budgets as a core simulation driver.

2. **Move and archive the legacy Economic Systems doc**:

   - The existing `D-ECON-0001_Economic_Systems` will be:
     - Renamed to **`D-ECON-0100_Economic_Systems_Legacy`** (or similar archive ID)
       to avoid doc_id collision.
     - Its `status` changed to `archived`.
     - A short banner added to clarify that it is **historical / exploratory** and
       not authoritative.
   - The file should be moved into an archive folder such as:
     - `docs/archive/04_economy/` (following current archive conventions).

3. **Avoid redirect stubs**:

   - We will **not** create a stub file under the old name.
   - Instead, we rely on:
     - The new `D-ECON-0001` as canonical.
     - The ADR and front-matter annotations in the legacy doc.

4. **Update references opportunistically**:

   - Any references in other docs to the old `D-ECON-0001_Economic_Systems`:
     - Should be updated to either:
       - `D-ECON-0001_Ward_Resource_and_Water_Economy` (if the intent was about scarcity/water), or
       - `D-ECON-0100_Economic_Systems_Legacy` (if specifically discussing earlier conceptual framing).
   - No large-scale, immediate refactor is required; updates can be done
     when those docs are next touched.

## 3. Alternatives Considered

### Option A – Keep Economic Systems as D-ECON-0001, assign water a different ID

- Pros:
  - No renaming/archiving required.
- Cons:
  - `D-ECON-0001` would remain a broad, slightly messy sketch.
  - Water, the real macro constraint, would be relegated to a secondary ID,
    making the doc graph less intuitive for future readers.

### Option B – Extend Economic Systems to absorb the water model

- Pros:
  - Single, all-in-one economic doc.
- Cons:
  - High risk of **bloat** and conceptual muddiness.
  - Harder to use as a direct spec for simulation code.
  - Conflicts with the emerging pattern of **narrow, simulation-aligned docs**.

We chose to **promote water to the primary econ slot** and treat the old doc as
legacy material.

## 4. Consequences

### Positive

- `D-ECON-0001` now clearly anchors the **core survival economy**:
  - Ward-level water budgets and flow.
  - Directly feeds civic microdynamics, telemetry, and agent biology.
- The doc graph becomes more legible:
  - Water → Food → Labor → Credits, etc., can be layered in a structured way.
- The legacy `Economic_Systems` text:
  - Is preserved for mining ideas (tone, social framing, credit systems),
  - But won’t silently constrain newer, more rigorous specs.

### Negative / Tradeoffs

- References to old `D-ECON-0001` in notebooks or older notes:
  - May temporarilypoint to an archived doc until updated.
- Requires a one-time manual step:
  - Renaming/moving the legacy file and adjusting its header.

## 5. Implementation Notes

Concrete steps to perform in the repo:

1. **Introduce the new doc**

   - Add `docs/04_economy/D-ECON-0001_Ward_Resource_and_Water_Economy.md`
   - Use the current draft content (version `0.1.0`, `status: draft`).

2. **Archive the legacy doc**

   - Move the old econ file to an archive folder, e.g.:
     - From: `docs/04_economy/D-ECON-0001_Economic_Systems.md`
     - To:   `docs/archive/04_economy/D-ECON-0100_Economic_Systems_Legacy.md`
   - Update its front-matter:
     - `doc_id: D-ECON-0100`
     - `status: archived`
     - `superseded_by: D-ECON-0001`
     - `adr: ADR-ECON-0002`
   - Add a short banner at the top of the body, such as:

     > **Status:** Archived / superseded  
     > This document is an early, exploratory sketch of Dosadi's economy.  
     > It has been superseded in part by `D-ECON-0001_Ward_Resource_and_Water_Economy`  
     > and upcoming, more focused economic design docs.

3. **Adjust references when convenient**

   - When a doc is next edited:
     - Replace references to the old `D-ECON-0001` with:
       - `D-ECON-0001_Ward_Resource_and_Water_Economy` where discussing water/scarcity, or
       - `D-ECON-0100_Economic_Systems_Legacy` where discussing the original conceptual sketch.

This keeps your econ pillar **clean and water-first**, while still honoring and
preserving the initial exploratory work.
