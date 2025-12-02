from __future__ import annotations

import random
from typing import List, Tuple

from dosadi.law.movement_protocols import FacilityProtocolTuning
from dosadi.memory.facility_aggregation import recompute_facility_belief_summaries
from dosadi.memory.facility_summary import FacilityBeliefSummary
from dosadi.state import WorldState


def run_proto_council_tuning(
    world: WorldState,
    rng: random.Random,
    current_day: int,
    max_facilities: int = 3,
    max_changes: int = 2,
) -> None:
    """
    MVP proto-council tuning pass.

    - Recomputes facility belief summaries.
    - Scores facilities by "problem_score".
    - Applies up to `max_changes` small, local protocol knob tweaks.
    """

    recompute_facility_belief_summaries(world)

    if not world.facility_belief_summaries:
        return

    scored: List[Tuple[str, FacilityBeliefSummary, float]] = []

    w_safety = 0.6
    w_fairness = 0.4
    w_queue = 0.5
    w_incident = 0.7

    for fac_id, summary in world.facility_belief_summaries.items():
        safety = summary.safety_score
        fairness = summary.fairness_score
        queue_p = summary.queue_pressure
        inc_rate = summary.incident_rate

        problem_score = (
            w_safety * (1.0 - safety)
            + w_fairness * (1.0 - fairness)
            + w_queue * queue_p
            + w_incident * inc_rate
        )

        scored.append((fac_id, summary, problem_score))

    if not scored:
        return

    scored.sort(key=lambda t: t[2], reverse=True)
    candidates = scored[:max_facilities]

    changes_applied = 0

    for fac_id, summary, _problem_score in candidates:
        if changes_applied >= max_changes:
            break

        tuning = world.facility_protocol_tuning.get(fac_id)
        if tuning is None:
            tuning = FacilityProtocolTuning(facility_id=fac_id)
            world.facility_protocol_tuning[fac_id] = tuning

        if current_day < tuning.cooldown_until_day:
            continue

        changed = _apply_single_tweak_for_facility(
            world=world,
            fac_id=fac_id,
            summary=summary,
            tuning=tuning,
            current_day=current_day,
        )
        if changed:
            changes_applied += 1


def _apply_single_tweak_for_facility(
    *,
    world: WorldState,
    fac_id: str,
    summary: FacilityBeliefSummary,
    tuning: FacilityProtocolTuning,
    current_day: int,
) -> bool:
    """
    Decide and apply exactly one small tuning knob change for this facility, if any.

    Returns True if a change was applied.
    """

    changed = False
    old_tuning = FacilityProtocolTuning(**tuning.__dict__)

    if summary.safety_score < 0.5 and tuning.min_guard_presence < 3:
        tuning.min_guard_presence += 1
        changed = True
    elif summary.queue_pressure > 0.7 and tuning.max_queue_length < 20:
        tuning.max_queue_length += 2
        changed = True
    elif summary.fairness_score < 0.5 and not tuning.post_protocol_summary:
        tuning.post_protocol_summary = True
        changed = True

    if not changed:
        return False

    tuning.cooldown_until_day = current_day + 2

    try:
        _log_protocol_tweak(world, fac_id, old_tuning, tuning, current_day)
    except Exception:
        pass

    return True


def _log_protocol_tweak(
    world: WorldState,
    fac_id: str,
    old: FacilityProtocolTuning,
    new: FacilityProtocolTuning,
    current_day: int,
) -> None:
    """Log a proto-council protocol tweak to the admin event log."""

    admin_log = getattr(world, "admin_event_log", None)
    if admin_log is None:
        return

    council_ids = getattr(world, "council_agent_ids", [])
    agent_ids = tuple(council_ids[:1]) if council_ids else ()

    payload = {
        "facility_id": fac_id,
        "old_max_queue_length": old.max_queue_length,
        "new_max_queue_length": new.max_queue_length,
        "old_min_guard_presence": old.min_guard_presence,
        "new_min_guard_presence": new.min_guard_presence,
        "old_post_protocol_summary": old.post_protocol_summary,
        "new_post_protocol_summary": new.post_protocol_summary,
        "old_queue_status_board": old.queue_status_board,
        "new_queue_status_board": new.queue_status_board,
        "day": current_day,
    }

    admin_log.record(
        tick=getattr(world, "tick", 0),
        event_type="PROTO_TWEAK_APPLIED",
        payload=payload,
        facility_id=fac_id,
        agent_ids=agent_ids,
        tags=("proto_council",),
    )
