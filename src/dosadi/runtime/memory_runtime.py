from __future__ import annotations

from dosadi.agents.core import AgentState, PlaceBelief
from dosadi.memory.config import MemoryConfig
from dosadi.memory.episodes import EpisodeBuffers, Episode, EpisodeGoalRelation
from dosadi.state import WorldState


def _retention_score(ep: Episode) -> float:
    """
    Compute a rough retention score R(ep) in [0, 1] based on
    importance, goal relation, emotion, and channel.
    MVP: simple heuristic; can be refined later.
    """

    importance = getattr(ep, "importance", 0.0)
    base = importance

    relation = getattr(ep, "goal_relation", EpisodeGoalRelation.UNKNOWN)
    if relation in (EpisodeGoalRelation.SUPPORTS, EpisodeGoalRelation.THWARTS):
        base += 0.2
    elif relation is EpisodeGoalRelation.MIXED:
        base += 0.1

    emotion = getattr(ep, "emotion", None)
    if emotion is not None:
        base += 0.2 * getattr(emotion, "arousal", 0.0)
        base += 0.2 * getattr(emotion, "threat", 0.0)

    if base < 0.0:
        base = 0.0
    elif base > 1.0:
        base = 1.0
    return base


def maintain_short_term_memory(
    agent: AgentState,
    tick: int,
    config: MemoryConfig,
) -> None:
    """
    Periodic maintenance on short-term episodes:
    - prune very low-retention episodes
    - leave others for possible promotion.
    """

    if tick - agent.last_short_term_maintenance_tick < config.short_term_maintenance_interval_ticks:
        return
    agent.last_short_term_maintenance_tick = tick

    buffers: EpisodeBuffers = agent.episodes

    threshold = 0.2
    kept: list[Episode] = []
    for ep in list(buffers.short_term):
        r = _retention_score(ep)
        if r >= threshold:
            kept.append(ep)

    buffers.short_term.clear()
    for ep in kept:
        buffers.short_term.append(ep)


def promote_daily_memory(
    agent: AgentState,
    tick: int,
    config: MemoryConfig,
    *,
    force: bool = False,
) -> None:
    """
    Periodically scan short-term episodes and promote important ones to the daily buffer.
    """

    if not force and tick - agent.last_daily_promotion_tick < config.daily_promotion_interval_ticks:
        return
    agent.last_daily_promotion_tick = tick

    buffers: EpisodeBuffers = agent.episodes

    for ep in list(buffers.short_term):
        importance = getattr(ep, "importance", 0.0)
        relation = getattr(ep, "goal_relation", EpisodeGoalRelation.UNKNOWN)
        emotion = getattr(ep, "emotion", None)
        arousal = getattr(emotion, "arousal", 0.0) if emotion is not None else 0.0
        threat = getattr(emotion, "threat", 0.0) if emotion is not None else 0.0

        promote = False

        if importance >= 0.4:
            promote = True
        elif relation in (EpisodeGoalRelation.SUPPORTS, EpisodeGoalRelation.THWARTS) and importance >= 0.2:
            promote = True
        elif (arousal + threat) >= 0.8:
            promote = True

        if promote:
            buffers.promote_to_daily(ep)


def step_agent_sleep_wake(
    world: WorldState,
    agent: AgentState,
    tick: int,
    config: MemoryConfig,
) -> None:
    """
    Toggle agent sleep/wake based on next_sleep_tick / next_wake_tick,
    and trigger consolidation when entering sleep.
    """

    if not agent.is_asleep and tick >= agent.next_sleep_tick:
        # Make sure salient short-term episodes are ready for consolidation.
        promote_daily_memory(agent, tick, config, force=True)

        agent.is_asleep = True
        agent.next_wake_tick = tick + config.sleep_duration_ticks

        run_sleep_consolidation(agent, tick, config)

    elif agent.is_asleep and tick >= agent.next_wake_tick:
        agent.is_asleep = False
        agent.next_sleep_tick = tick + config.wake_duration_ticks


def run_sleep_consolidation(
    agent: AgentState,
    tick: int,
    config: MemoryConfig,
) -> None:
    """
    Compress daily episodes into long-term beliefs.

    MVP:
    - For each episode in daily, let PlaceBelief update itself.
    - Clear daily after processing.
    """

    if tick - agent.last_consolidation_tick < config.min_consolidation_interval_ticks:
        return
    agent.last_consolidation_tick = tick

    buffers: EpisodeBuffers = agent.episodes
    daily_eps: list[Episode] = list(buffers.daily)

    if not daily_eps:
        return

    for ep in daily_eps:
        place_id = ep.location_id or ep.target_id
        if place_id:
            pb: PlaceBelief = agent.get_or_create_place_belief(place_id)
            pb.update_from_episode(ep)

    buffers.daily.clear()


def step_agent_memory_maintenance(
    world: WorldState,
    agent: AgentState,
    tick: int,
    config: MemoryConfig,
) -> None:
    """
    High-level per-agent memory step.

    - If awake: do short-term maintenance + daily promotion when due.
    - If asleep: no-op for now (consolidation happens on sleep entry).
    """

    if agent.is_asleep:
        return

    maintain_short_term_memory(agent, tick, config)
    promote_daily_memory(agent, tick, config)
