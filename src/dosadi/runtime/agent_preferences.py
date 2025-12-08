from __future__ import annotations

from typing import Optional

from dosadi.agents.core import AgentState
from dosadi.runtime.config import (
    NEGATIVE_PREFERENCE_THRESHOLD,
    POSITIVE_PREFERENCE_THRESHOLD,
    PREFERENCE_REVIEW_INTERVAL_TICKS,
)
from dosadi.runtime.work_details import WorkDetailType
from dosadi.state import WorldState


def maybe_update_desired_work_type(world: WorldState, agent: AgentState) -> None:
    """
    Once per review interval, let an agent consider whether to stay in their
    current work or desire a transfer to some other work type.
    """

    # Only workers and low-level supervisors make these choices for now
    if agent.tier not in (1, 2):
        return

    # Approximate cadence via total_ticks_employed
    if agent.total_ticks_employed <= 0:
        return
    if int(agent.total_ticks_employed) % PREFERENCE_REVIEW_INTERVAL_TICKS != 0:
        return

    # Identify current primary work type
    current_work_type: Optional[WorkDetailType] = None

    if agent.supervisor_work_type is not None:
        current_work_type = agent.supervisor_work_type
    else:
        # Fallback: most-worked type
        best_ticks = 0.0
        for wt, hist in agent.work_history.per_type.items():
            if hist.ticks > best_ticks:
                best_ticks = hist.ticks
                current_work_type = wt

    if current_work_type is None:
        return

    current_pref = agent.work_preferences.get_or_create(current_work_type).preference

    # If preference is not strongly negative, keep (or reinforce) current
    if current_pref > NEGATIVE_PREFERENCE_THRESHOLD:
        if current_pref > POSITIVE_PREFERENCE_THRESHOLD:
            agent.desired_work_type = current_work_type
        return

    # They dislike current work; see if there's a better alternative
    best_alt: Optional[WorkDetailType] = None
    best_score = current_pref  # must beat current

    for wt, wp in agent.work_preferences.per_type.items():
        if wt == current_work_type:
            continue
        if wp.preference > best_score:
            best_score = wp.preference
            best_alt = wt

    if best_alt is None or best_score <= current_pref:
        agent.desired_work_type = None
    else:
        agent.desired_work_type = best_alt


__all__ = ["maybe_update_desired_work_type"]
