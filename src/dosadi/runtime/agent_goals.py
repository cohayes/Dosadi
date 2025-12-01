from __future__ import annotations

from dosadi.agents.core import AgentState, GoalStatus


def complete_goals_by_kind(agent: AgentState, kind: str) -> None:
    """Mark all goals of a given kind as COMPLETED if applicable."""
    if not hasattr(agent, "goals"):
        return

    for goal in agent.goals:
        if getattr(goal, "kind", None) != kind:
            continue
        if goal.status in (
            GoalStatus.COMPLETED,
            GoalStatus.FAILED,
            GoalStatus.ABANDONED,
        ):
            continue
        goal.status = GoalStatus.COMPLETED
