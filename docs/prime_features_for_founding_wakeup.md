# Wakeup Prime Features to Reuse in Founding Wakeup

The Wakeup Prime scenario includes several mechanics that can strengthen the founding_wakeup_mvp goals (pod formation, proto-council emergence, hazard-driven protocols, and memory-driven behavior). These features can be lifted or adapted directly:

## Queueing discipline for scarce resources
- **Suit/assignment queues**: Prime registers explicit queues for suit issue and assignment halls with FIFO rules and throughput limits, exercising agent patience, prioritization, and congestion effects. Bringing these queues into the MVP would make resource constraints legible and give pod reps/council a reason to debate scheduling fairness.
- **Queue lifecycle hooks**: The queue emitter plus `process_all_queues` let us measure wait times and frustrations that could trigger policy proposals or hazard workarounds.

Reference: `wakeup_prime._register_wakeup_queues`, `run_wakeup_prime` runtime loop, and `QueueEpisodeEmitter`.

## Governance cadence and council tuning
- **Pod meeting cadence and voting thresholds**: Prime’s runtime uses tick-gated pod meetings with vote fraction and leadership thresholds. Aligning MVP governance ticks with similar thresholds offers ready-made knobs for how quickly pods elevate reps and when they churn.
- **Proto-council tuning once per in-world day**: The periodic tuning in `_maybe_run_proto_council` enforces rotation and eligibility rules so the council composition keeps reflecting pod politics. This complements the founding wakeup requirement for a proto-council to emerge and stabilize.
- **Council meeting cooldown**: Cooldowns avoid back-to-back meetings and force prioritization of agenda items, which can reveal unmet hazards.

Reference: `wakeup_prime._step_governance` and `_maybe_run_proto_council`.

## Hazard-aware protocol triggers
- **Edge risk seeding**: Prime seeds traversal/incident metrics from base hazard probabilities, giving the runtime an initial gradient so protocol authorship can activate quickly. Adding this to the MVP ensures early signals for the Risk→Protocol loop rather than waiting for long-run incident accumulation.
- **Dangerous-edge detection**: `_find_dangerous_corridors_from_metrics` already scans metrics against incident/risk thresholds; plugging that into the MVP keeps protocol authorship grounded in observed hazards.
- **Movement protocol authoring**: The runtime’s `maybe_author_movement_protocols` hook automatically drafts movement protocols once thresholds are hit; adopting it accelerates the “at least one protocol” success condition.

Reference: `wakeup_prime._step_governance`, `_seed_risk_metrics`, and `runtime.protocol_authoring`.

## Agent rhythm and employment pressure
- **Sleep/wake staggering**: `_initialize_agent_sleep_schedule` spreads sleep offsets across a day, keeping agents active in overlapping shifts. This reduces synchronized idle periods and yields steadier queue usage and corridor traversal data for hazard detection.
- **Employment ticks**: Incrementing `total_ticks_employed` when awake (in `step_wakeup_prime_once`) gives a coarse productivity signal that could inform council debates about work allocation or suit shortages.

Reference: `wakeup_prime._initialize_agent_sleep_schedule` and `step_wakeup_prime_once`.

## Facility-level protocol tuning
- **FacilityProtocolTuning defaults**: Prime initializes protocol tuning per facility, making it easy to attach facility-specific guidance (e.g., throughput rules, hazard signage). Carrying this into the MVP gives councils concrete levers for non-movement protocols.

Reference: `wakeup_prime.generate_wakeup_scenario_prime` facility registration.

## Scenario metadata and objectives
- **Explicit objective metadata**: Prime tags the scenario with objectives like `queue_discipline`, `proto_council_readiness`, and `risk_protocol_feedback`. Mirroring this in the MVP helps downstream validation/reporting emphasize council dynamics and hazard-protocol responsiveness.

Reference: `wakeup_prime.generate_wakeup_scenario_prime` metadata.
