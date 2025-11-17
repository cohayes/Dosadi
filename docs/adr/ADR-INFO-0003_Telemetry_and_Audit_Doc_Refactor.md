---
title: ADR_Telemetry_and_Audit_Doc_Refactor
doc_id: ADR-INFO-0003
version: 1.0.0
status: accepted
owners: [cohayes]
last_updated: 2025-11-17
---

# ADR: Telemetry & Audit Doc Refactor (D-INFOSEC-0009 → D-INFO-0001)

## 1. Context

An earlier document, `D-INFOSEC-0009_Telemetry_and_Audit_Infrastructure`, was drafted under an **INFOSEC** namespace.

Since then, the project has:

- Clarified a set of **information-focused docs** under the `D-INFO-XXXX` namespace:
  - `D-INFO-0002_Espionage_Branch`
  - `D-INFO-0003_Information_Flows_and_Report_Credibility`
  - `D-INFO-0004_Scholars_and_Clerks_Branch`
- Established Telemetry & Audit as:
  - A **cross-branch, world-level measurement system**, rather than a “security hardening” concern.
  - A primary data source for **Scholars & Clerks** and the **credibility system**, not just a defensive mechanism.

The original `INFOSEC` naming is now misleading:
- It suggests a focus on cyber/technical security rather than **measurement, logging, and auditing** of socio-economic flows.
- It does not match the new “information pillar” (`D-INFO`) taxonomy.

## 2. Decision

We will:

1. **Archive** `D-INFOSEC-0009_Telemetry_and_Audit_Infrastructure` as superseded.
2. **Introduce** a new canonical document:
   - `D-INFO-0001_Telemetry_and_Audit_Infrastructure`
3. Treat `D-INFO-0001` as:
   - The **primary reference** for:
     - Meters, instruments, and logs (water, moisture, rations, access, patrols, etc.).
     - Audit processes (routine and triggered).
     - Integration with Scholars & Clerks and the credibility system.
4. **Not** create a redirect stub file for `D-INFOSEC-0009` on disk:
   - Consistent with the current project decision to **avoid redirect stubs** while there is only one human editor.
5. **Update references opportunistically**:
   - When touching existing docs that refer to `D-INFOSEC-0009`, update them to `D-INFO-0001`.
   - No mass refactor required immediately.

## 3. Alternatives Considered

1. **Keep the INFOSEC ID and add a cross-reference**
   - Pros:
     - No reference drift.
   - Cons:
     - Confusing taxonomy: INFOSEC suggests a different domain than the doc actually covers.
     - Inconsistent with the emerging `D-INFO` cluster.

2. **Create a new Telemetry doc but keep INFOSEC for “security telemetry”**
   - Pros:
     - Could distinguish operational telemetry vs infosec logs.
   - Cons:
     - Over-segmentation at this stage.
     - Premature optimization without a clear need.

We chose the **single, clear Telemetry & Audit doc** in `D-INFO`.

## 4. Consequences

### Positive

- Clearer taxonomy:
  - All information-flows-and-integrity docs live under `D-INFO-XXXX`.
- Telemetry is explicitly aligned with:
  - `D-INFO-0003_Information_Flows_and_Report_Credibility`
  - `D-INFO-0004_Scholars_and_Clerks_Branch`
- Future contributors will:
  - Naturally look for audit and measurement systems under `D-INFO-0001`.

### Negative / Tradeoffs

- Some older references (e.g., in notes, out-of-repo materials) may still mention `D-INFOSEC-0009` until touched.
- No automated redirect:
  - Requires mental mapping that “old `D-INFOSEC-0009` == new `D-INFO-0001`” for legacy material.

## 5. Implementation Notes

- Create and maintain `D-INFO-0001_Telemetry_and_Audit_Infrastructure` as the **active** design doc.
- When editing or reviewing older documents:
  - Replace any mention of `D-INFOSEC-0009` with `D-INFO-0001`.
- Treat the old doc as:
  - Conceptually merged into and superseded by `D-INFO-0001`.
