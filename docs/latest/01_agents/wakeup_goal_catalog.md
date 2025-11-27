# Founding wakeup goal catalogue

This reference lists the goal types currently available to agents in the founding wakeup MVP, the conditions that add them to an agent or group, and the actions they drive when the goal is in focus.

| Goal | How it is acquired | Resulting behavior when focused |
| --- | --- | --- |
| `MAINTAIN_SURVIVAL` | Seeded for every agent during creation. | No special action mapping; acts as the parent for survival-related subgoals. |
| `ACQUIRE_RESOURCE` | Seeded for every agent during creation. | Moves toward the well core (or the least-dangerous neighbor) when away from the core. |
| `SECURE_SHELTER` | Seeded for every agent during creation. | Moves toward the agent’s `home` pod assignment when away from it. |
| `REDUCE_POD_RISK` | Seeded at creation only for agents whose `communal` and `leadership_weight` traits are both > 0.6. | Attempts a pod meeting at the current location to coordinate mitigation. |
| `MAINTAIN_RELATIONSHIPS` | Not currently auto-assigned. | Attempts a pod meeting wherever the agent is located. |
| `FORM_GROUP` | Granted (or reprioritized to very high) when an agent is elected `POD_REPRESENTATIVE` during a pod meeting. | Moves toward the well core; if already at the core, initiates a council meeting. |
| `STABILIZE_POD` | Not currently auto-assigned. | Moves toward the well core (or safest neighbor) when away from the core. |
| `GATHER_INFORMATION` | Created as a council group goal when `ensure_council_gather_information_goal` is invoked, and projected to selected scouts by `project_gather_information_to_scouts` at very high priority/urgency. | Wanders to adjacent nodes/edges while counting hazard incidents; after 5 hazards it reverts to `PENDING` with very low priority/urgency so other goals can take over. |
| `AUTHOR_PROTOCOL` | Added to a council scribe when dangerous corridors are detected or projected from a group `GATHER_INFORMATION` goal via `project_author_protocol_to_scribe`, both at very high priority/urgency. | Drafts and activates a movement/safety protocol targeting the corridors in the goal payload. |
| `ORGANIZE_GROUP` | Not currently auto-assigned. | Attempts a pod meeting wherever the agent is located. |

## Notes on focus and action selection
- Only ACTIVE or PENDING goals can be selected for focus; picking a PENDING goal promotes it to ACTIVE so it can drive behavior. The highest combined `priority` + `urgency` wins the focus slot.
- Goals without explicit verb mappings fall back to `REST_IN_POD` after reaching the well core, so additional logic may be needed before they produce visible effects.

## Triggers still missing for non-seeded goals
- `MAINTAIN_RELATIONSHIPS`, `STABILIZE_POD`, and `ORGANIZE_GROUP` still have no creation hooks in the runtime or council helpers, so they only appear if manually injected into an agent’s goal list.
- To promote them automatically, add creation conditions (e.g., pod-coordination gaps, morale decay, or council quorum checks) in either the worldgen seeding phase or the `maybe_run_pod_meeting` / `maybe_run_council_meeting` flows.
