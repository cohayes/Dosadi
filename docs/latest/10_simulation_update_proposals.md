---
title: Simulation_Update_Proposals
status: draft
doc_id: D-ROADMAP-0001
version: 0.1.0
owners: [cohayes]
depends_on:
  - D-AGENT-0001
  - D-RUNTIME-0002
  - D-ECON-0001
  - D-HEALTH-0001
last_updated: 2025-11-11
---

# Simulation Update Proposals

## 1. Purpose
Summarize cross-cutting improvements that leverage the latest documentation refresh and target near-term upgrades for the Dosadi simulation runtime, agent stack, and systemic loops.

## 2. Recommended Initiatives

### 2.1 Agent Stress Reactivity Loop
- **Motivation.** Current agent docs describe cognitive load, burnout, and suit comfort but we lack a concrete feedback loop that binds _Perception → Decision → Health_ when chronic stressors accumulate.
- **Proposal.** Introduce a multi-factor _StressReactance_ score derived from `MentalProcessingBudget` overuse, thermal penalties, and rumor exposure intensity. Feed this score into the utility calculus (D-AGENT-0005) as a negative weight multiplier and into health decay (D-AGENT-0001 §2.1).
- **Runtime impact.** Emit a weekly `AgentStressAudit` cadence in the SOCIAL phase to consolidate asynchronous stress events and publish mitigation tasks to the decision planner.
- **Benefits.** Produces more realistic spiral dynamics (fatigue → paranoia), unlocks emergent behaviors like proactive rest or factional therapy services.

### 2.2 Suit Maintenance → Economy Bridge
- **Motivation.** Suit degradation is modeled, and maintenance loops exist in the economy docs, yet agents currently treat suit upkeep as background noise.
- **Proposal.** Add a shared `SuitServiceLedger` registry entry updated by ACCOUNTING-phase handlers. Market microstructure (D-ECON-0003) should expose parts scarcity, while Maintenance Fault Loop (D-ECON-0005) ingests suit telemetry to price repairs dynamically.
- **Runtime impact.** Introduce a `SuitTelemetryIngest` handler in the PERCEPTION phase, coupled with an ACCOUNTING phase settlement that debits guild budgets. Emit `MaintenanceDeferralRisk` events when agents skip service.
- **Benefits.** Aligns physical risk with economic pressure, creating richer incentives for agent cooperation or black-market procurement.

### 2.3 Information Security Incident Escalation
- **Motivation.** The info-security dossier outlines breach surfaces but lacks a structured escalation pipeline that interfaces with law and reputation systems.
- **Proposal.** Define an `InfosecIncident` event family with tiered severities (Recon, Intrusion, Exfiltration). Each tier publishes to the LAW systems (D-LAW-0001) and updates reputation weights (D-AGENT-0001 §2.4) via SOCIAL-phase handlers.
- **Runtime impact.** Extend the event taxonomy to include TTL-based containment steps; add deterministic replay checkpoints after escalation to aid forensic re-simulations.
- **Benefits.** Ties breaches to legal responses, enabling narratives where courts, enforcers, and rumor networks react cohesively.

### 2.4 Adaptive Cadence Tuning
- **Motivation.** `Simulation_Timebase` currently relies on static cadences. Highly dynamic subsystems (e.g., rumor propagation, credit liquidity) oscillate between over- and under-sampling.
- **Proposal.** Implement a feedback controller that inspects queue backlog and handler durations, then adjusts cadence divisors within bounded ranges. Persist adjustments in the shared variable registry for reproducibility.
- **Runtime impact.** Requires scheduler support for mutable cadences with audit logging. Provide a `CadenceAdjust` event so downstream systems can respond (e.g., smoothing interest rate updates).
- **Benefits.** Reduces wasted ticks during calm periods while preserving fidelity during crises; improves deterministic testing by recording cadence shifts in save states.

## 3. Next Steps
1. Socialize these initiatives in the design review loop.
2. Select one agent-centric and one infrastructure-centric initiative for sprint backlog.
3. Prototype runtime changes behind feature flags to avoid destabilizing the deterministic baseline.
4. Update relevant docs (agents, runtime, economy, law) once pilots validate assumptions.

