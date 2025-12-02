from __future__ import annotations

from dosadi.agents.core import AgentState, PlaceBelief
from dosadi.memory.config import MemoryConfig
from dosadi.memory.episodes import EpisodeBuffers, Episode, EpisodeGoalRelation
from dosadi.memory.place_belief_updates import apply_episode_to_place_belief
from dosadi.state import WorldState


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


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
            apply_episode_to_place_belief(pb, ep)

    buffers.daily.clear()

    # After daily episodes have been integrated into beliefs,
    # apply slow belief-driven adjustments to stress and morale.
    _apply_belief_driven_stress_and_morale(agent)


def _apply_belief_driven_stress_and_morale(agent: AgentState) -> None:
    """
    Use PlaceBeliefs for key service locations to nudge agent.physical.stress_level
    and agent.physical.morale_level a little bit per sleep cycle.

    Follows D-MEMORY-0207: small, EMA-like drifts based on fairness / safety /
    congestion / reliability / efficiency.
    """

    # Define which places matter for MVP (wakeup core services).
    places_of_interest = [
        "queue:suit-issue:front",
        "queue:assignment:front",
        # If beliefs are keyed by facility ids instead of queue nodes,
        # keep these as alternates:
        "fac:suit-issue-1",
        "fac:assign-hall-1",
    ]

    sp_list: list[float] = []
    mp_list: list[float] = []

    for place_id in places_of_interest:
        pb = agent.place_beliefs.get(place_id)
        if pb is None:
            continue

        fair = pb.fairness_score
        eff = pb.efficiency_score
        safe = pb.safety_score
        cong = pb.congestion_score
        rel = pb.reliability_score

        # Stress pressure per place (SP_place), as per spec:
        # negatives are stress-relieving, positives stress-increasing.
        sp_place = (
            -0.6 * (-safe) +   # unsafe (safe<0) increases stress
             0.4 * cong +      # congestion increases stress
            -0.4 * (-rel) +    # unreliability increases stress
            -0.2 * (-fair)     # unfairness increases stress (modestly)
        )

        # Morale pressure per place (MP_place), as per spec:
        # positives increase morale, negatives reduce morale.
        mp_place = (
             0.6 * fair +      # fairness supports morale
             0.5 * rel +       # reliability supports morale
             0.3 * eff         # efficiency; chronic slowness erodes morale
        )

        sp_list.append(sp_place)
        mp_list.append(mp_place)

    if not sp_list and not mp_list:
        # No relevant beliefs; no adjustment this cycle.
        return

    SP_net = sum(sp_list) / len(sp_list) if sp_list else 0.0
    MP_net = sum(mp_list) / len(mp_list) if mp_list else 0.0

    # Base step sizes (per sleep cycle)
    stress_step_scale = 0.05
    morale_step_scale = 0.03

    # Simple tier modulation: Tier-1 more reactive, Tier-3 more buffered.
    tier = getattr(agent, "tier", 1)
    if tier == 1:
        stress_step_scale *= 1.2
        morale_step_scale *= 1.2
    elif tier == 3:
        stress_step_scale *= 0.8
        morale_step_scale *= 0.8

    physical = agent.physical

    # Apply drifts and clamp to [0, 1]
    physical.stress_level = _clamp01(
        physical.stress_level + stress_step_scale * SP_net
    )
    physical.morale_level = _clamp01(
        physical.morale_level + morale_step_scale * MP_net
    )


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
