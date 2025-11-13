---
title: Simulation_Runtime_Update_Proposals
doc_id: D-RUNTIME-0005
version: 0.1.0
status: draft
owners: [cohayes, codex]
last_updated: 2025-02-16
depends_on:
  - D-RUNTIME-0001   # Simulation_Timebase
  - D-RUNTIME-0002   # Simulation_Runtime
  - D-RUNTIME-0003   # Event & Message Taxonomy (placeholder)
---

# Simulation Runtime – Forward Improvements

> **Intent.** Capture high-value runtime upgrades that improve determinism, throughput, and developer ergonomics without rewriting the whole orchestrator. Each proposal below is scoped for incremental delivery and assumes the existing tick+phase contract defined in `D-RUNTIME-0001`.

---

## 1) Adaptive Cadence Buckets

**Problem.** Handlers currently run strictly on fixed cadences, forcing slow systems (e.g., ledger reconciliation) to block the entire tick while fast systems idle. This leads to CPU underutilization and makes it hard to add bursty systems such as large-scale rumor propagation.

**Proposal.** Introduce *cadence buckets*—groups of handlers that share cadence divisors but can execute concurrently as long as their dependencies are disjoint. The scheduler would:

1. Pre-compute dependency graphs per phase using handler-declared read/write sets (leveraging `Simulation_Timebase` identifiers).
2. Partition handlers into buckets that can run in parallel threads or async tasks when no data hazards are declared.
3. Fall back to sequential execution if the dependency metadata is missing to preserve determinism.

**Outcome.** Unlocks safe parallelism inside a tick, reduces contention on hot phases (DECISION, ACCOUNTING), and provides a stepping stone toward multi-node execution.

---

## 2) Event Bus Telemetry Channel

**Problem.** Operators lack a unified way to understand event pressure, TTL expirations, or queue starvation. Debug logging is noisy, and the observability story is inconsistent across systems.

**Proposal.** Extend the event bus with an optional telemetry channel that emits structured metrics at the end of each tick:

- Queue depth per event type and phase
- Count of dropped/expired events with causes
- Average handler latency per phase (piggyback on cadence buckets instrumentation)

Export the channel via existing interface adapters (CLI, REST, and Replay harness). Telemetry emission must be deterministic when recorded in replays (e.g., capture into the save state rather than relying on wall-clock timestamps).

**Outcome.** Gives runtime SREs real-time visibility, enables automated alerting on pathological cadences, and supplies ground truth for balancing agent behaviors.

---

## 3) Deterministic Snapshot Delta Files

**Problem.** Save/Load currently serializes the entire world state each checkpoint, causing large files and long pauses. Incremental saves are risky because we lack a canonical definition of what changed during a tick.

**Proposal.**

1. Introduce an *immutable tick journal* that records the ordered list of committed state transitions (entity mutation events, registry updates, economic transactions) produced during a tick.
2. Generate delta snapshots by replaying the journal atop the last full snapshot, storing only compressed journals between full checkpoints.
3. Verify determinism by replaying the delta journals in CI against nightly builds (hooks in the Replay harness).

**Outcome.** Shrinks save files, cuts pause time, and provides a deterministic audit log suitable for compliance tooling.

---

## 4) Scenario Fuzz Harness

**Problem.** Runtime regressions surface late because integration tests cover only a handful of scripted scenarios.

**Proposal.** Build a lightweight fuzz harness that:

- Seeds the world with randomized but schema-valid agents/commodities/contracts derived from `D-AGENTS` and `D-ECONOMY` docs.
- Applies stochastic event injections (market shocks, rumor storms, health crises) following probabilities defined in `Simulation_Timebase`.
- Runs for N ticks inside CI/nightly and asserts invariants (no NaN balances, conserved resources, bounded queue sizes).

**Outcome.** Detects scheduler deadlocks, data races introduced by cadence buckets, and stress-tests serialization.

---

## 5) Interface Contract Tests

**Problem.** Runtime changes frequently break interface adapters (CLI, REST, streaming UI) because mocks drift from the actual event schemas.

**Proposal.** Add contract tests that boot the runtime in a headless mode, attach each interface adapter, and validate that emitted payloads conform to the canonical schemas in `Dosadi_Global_Schemas.md`. Provide fixtures for archived schema versions to guarantee backward compatibility promises.

**Outcome.** Catches breaking changes before deployment, ensures archived documentation remains truthful, and encourages versioned schema evolution.

---

## Next Steps

1. Circulate this document for feedback with owners of Economy, Health, and Interfaces systems.
2. Prioritize at least one runtime-focused Epic for the next planning increment (recommend starting with Telemetry Channel + Contract Tests).
3. Track acceptance criteria via ADR updates and link implementation tasks back to `D-RUNTIME-0005`.

