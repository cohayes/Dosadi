# Founding Wakeup MVP: Why runs may not meet intent

## Slow or missing governance formation
- Pod meetings only happen every 2,400 ticks by default, so short test runs may finish before any representatives are elected, blocking council formation. `RuntimeConfig.pod_meeting_interval_ticks` also throttles repeated meetings even when pods are ready.【F:src/dosadi/runtime/founding_wakeup.py†L29-L42】
- The proto-council only forms when at least two pod representatives are simultaneously at the well core; if agents never travel there, the council never materializes.【F:src/dosadi/agents/groups.py†L243-L283】

## Council actions gated by hazard evidence
- Council meetings are further limited by a 600-tick cooldown and a requirement that two members be present at the hub, delaying any downstream goals.【F:src/dosadi/agents/groups.py†L285-L310】
- Protocol authoring waits for corridors with ≥3 incidents and risk above the runtime threshold; with low hazard rates and few traversals, those thresholds may never trigger, so no protocols get written.【F:src/dosadi/agents/groups.py†L312-L356】【F:src/dosadi/agents/groups.py†L514-L551】

## Enabling protocol authoring and propagation
- Ensure the metrics map is populated with `traversals:*` and `incidents:*` keys so `_find_dangerous_corridors_from_metrics` can flag risky corridors during council meetings; otherwise no `AUTHOR_PROTOCOL` goals get created.【F:src/dosadi/agents/groups.py†L312-L356】【F:src/dosadi/agents/groups.py†L514-L551】
- When a scribe chooses the `AUTHOR_PROTOCOL` action, the runtime’s handler will create and activate a movement protocol immediately; verify `world.protocols` is a `ProtocolRegistry` so activation succeeds.【F:src/dosadi/agents/core.py†L790-L816】【F:src/dosadi/runtime/founding_wakeup.py†L157-L170】
- After activation, schedule `READ_PROTOCOL` actions (or inject episodes) for council members and pod reps so adoption data feeds back into hazard probabilities and incident tracking.【F:src/dosadi/agents/core.py†L772-L789】【F:src/dosadi/runtime/founding_wakeup.py†L157-L170】

## Agent behaviors may not drive toward the success path
- Movement toward the well core only happens when agents are pursuing specific goal types (e.g., gathering information or organizing); if initial goal sets omit those, colonists remain in pods and never convene a council. Newly elected pod reps now get a very high priority `FORM_GROUP` goal to mitigate this, but attendance still depends on movement neighbors and hazards.【F:src/dosadi/agents/core.py†L525-L621】【F:src/dosadi/agents/groups.py†L165-L207】

## Scenario loop lacks success-based stopping
- The runtime runs until `max_ticks` and never checks the scenario success conditions (e.g., protocol adoption or hazard reduction), so runs can finish with none of the intended milestones achieved.【F:src/dosadi/runtime/founding_wakeup.py†L135-L145】【F:docs/latest/11_scenarios/D-SCEN-0002_Founding_Wakeup_MVP_Scenario.md†L190-L223】

## Runtime performance considerations
- The agent decision phase previously rebuilt topology neighbors and RNGs once per agent per tick; caching those structures once per tick reduces object churn when hundreds of agents run at high tick counts.【F:src/dosadi/runtime/founding_wakeup.py†L110-L126】【F:src/dosadi/agents/core.py†L490-L544】
- Belief updates were being replayed over every historical episode each tick even though `record_episode` already updates beliefs; removing that pass avoids quadratic growth in work as episode logs increase.【F:src/dosadi/runtime/founding_wakeup.py†L52-L66】【F:src/dosadi/agents/core.py†L257-L278】
- A goal-priority randomizer triggered after long rests added extra RNG calls and non-determinism; it has been removed now that shelter and scouting goals are more directed.【F:src/dosadi/agents/core.py†L525-L621】【F:src/dosadi/agents/core.py†L817-L826】
