from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, Optional

from dosadi.agents.core import AgentState, Goal
from dosadi.memory.episodes import (
    EmotionSnapshot,
    Episode,
    EpisodeChannel,
    EpisodeGoalRelation,
    EpisodeOutcome,
    EpisodeTargetType,
)


@dataclass(frozen=True)
class TagConfig:
    base_importance: float
    default_outcome: EpisodeOutcome
    valence: float
    arousal: float
    threat: float


SUMMARY_TAG_CONFIG: Dict[str, TagConfig] = {
    # Queue outcomes
    "queue_served": TagConfig(
        base_importance=0.5,
        default_outcome=EpisodeOutcome.SUCCESS,
        valence=0.6,
        arousal=0.4,
        threat=0.2,
    ),
    "queue_denied": TagConfig(
        base_importance=0.7,
        default_outcome=EpisodeOutcome.FAILURE,
        valence=-0.7,
        arousal=0.7,
        threat=0.5,
    ),
    "queue_canceled": TagConfig(
        base_importance=0.7,
        default_outcome=EpisodeOutcome.FAILURE,
        valence=-0.6,
        arousal=0.7,
        threat=0.5,
    ),
    "queue_fight": TagConfig(
        base_importance=0.9,
        default_outcome=EpisodeOutcome.NEAR_MISS,
        valence=-0.9,
        arousal=1.0,
        threat=0.9,
    ),
    # Guard & steward behavior
    "guard_help": TagConfig(
        base_importance=0.5,
        default_outcome=EpisodeOutcome.HELP,
        valence=0.6,
        arousal=0.5,
        threat=0.2,
    ),
    "guard_fair": TagConfig(
        base_importance=0.5,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=0.5,
        arousal=0.4,
        threat=0.2,
    ),
    "guard_brutal": TagConfig(
        base_importance=0.8,
        default_outcome=EpisodeOutcome.HARM,
        valence=-0.8,
        arousal=0.9,
        threat=0.8,
    ),
    "steward_help": TagConfig(
        base_importance=0.5,
        default_outcome=EpisodeOutcome.HELP,
        valence=0.6,
        arousal=0.4,
        threat=0.2,
    ),
    "steward_unfair": TagConfig(
        base_importance=0.7,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.6,
        arousal=0.6,
        threat=0.5,
    ),
    # Accidents
    "accident_minor": TagConfig(
        base_importance=0.6,
        default_outcome=EpisodeOutcome.NEAR_MISS,
        valence=-0.4,
        arousal=0.5,
        threat=0.5,
    ),
    "accident_major": TagConfig(
        base_importance=0.8,
        default_outcome=EpisodeOutcome.HARM,
        valence=-0.8,
        arousal=0.9,
        threat=0.9,
    ),
    # Protocol reads
    "read_protocol_move_restricted": TagConfig(
        base_importance=0.5,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.3,
        arousal=0.4,
        threat=0.4,
    ),
    "read_protocol_queue_rules": TagConfig(
        base_importance=0.5,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.2,
        arousal=0.3,
        threat=0.3,
    ),
    # Body signals (intensity variants; simple mapping for now)
    "body_thirst_mild": TagConfig(
        base_importance=0.4,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.3,
        arousal=0.3,
        threat=0.3,
    ),
    "body_thirst_moderate": TagConfig(
        base_importance=0.7,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.6,
        arousal=0.5,
        threat=0.6,
    ),
    "body_thirst_severe": TagConfig(
        base_importance=0.9,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.9,
        arousal=0.8,
        threat=0.9,
    ),
    "body_hunger_mild": TagConfig(
        base_importance=0.4,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.3,
        arousal=0.3,
        threat=0.2,
    ),
    "body_hunger_moderate": TagConfig(
        base_importance=0.6,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.6,
        arousal=0.4,
        threat=0.4,
    ),
    "body_hunger_severe": TagConfig(
        base_importance=0.8,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.9,
        arousal=0.7,
        threat=0.7,
    ),
    "body_fatigue_mild": TagConfig(
        base_importance=0.3,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.2,
        arousal=0.2,
        threat=0.2,
    ),
    "body_fatigue_moderate": TagConfig(
        base_importance=0.5,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.5,
        arousal=0.3,
        threat=0.4,
    ),
    "body_fatigue_severe": TagConfig(
        base_importance=0.8,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.8,
        arousal=0.6,
        threat=0.7,
    ),
    "body_pain_mild": TagConfig(
        base_importance=0.4,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.4,
        arousal=0.4,
        threat=0.4,
    ),
    "body_pain_moderate": TagConfig(
        base_importance=0.7,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.7,
        arousal=0.6,
        threat=0.7,
    ),
    "body_pain_severe": TagConfig(
        base_importance=0.9,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.9,
        arousal=0.9,
        threat=0.9,
    ),
    "body_heat_stress_mild": TagConfig(
        base_importance=0.4,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.4,
        arousal=0.4,
        threat=0.4,
    ),
    "body_heat_stress_moderate": TagConfig(
        base_importance=0.7,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.7,
        arousal=0.7,
        threat=0.7,
    ),
    "body_heat_stress_severe": TagConfig(
        base_importance=0.9,
        default_outcome=EpisodeOutcome.NEUTRAL,
        valence=-0.9,
        arousal=0.9,
        threat=0.9,
    ),
}


def _channel_defaults(channel: EpisodeChannel) -> tuple[float, float]:
    """
    Return (reliability, importance_bonus) defaults for the given channel,
    based on D-MEMORY-0203.
    """
    if channel == EpisodeChannel.DIRECT:
        return 0.85, 0.3
    if channel == EpisodeChannel.BODY_SIGNAL:
        return 0.9, 0.4
    if channel == EpisodeChannel.OBSERVED:
        return 0.7, 0.2
    if channel == EpisodeChannel.REPORT:
        return 0.65, 0.3
    if channel == EpisodeChannel.RUMOR:
        return 0.3, 0.2
    if channel == EpisodeChannel.PROTOCOL:
        return 0.75, 0.3
    # Fallback
    return 0.5, 0.0


def _compute_goal_relevance(
    owner: AgentState,
    summary_tag: str,
    location_id: Optional[str],
    target_id: Optional[str],
) -> tuple[Optional[str], float, EpisodeGoalRelation]:
    """
    Compute (goal_id, goal_relevance, goal_relation) for the owner's current
    focus goal, using simple v0 heuristics from D-MEMORY-0203.
    """
    focus: Optional[Goal] = owner.choose_focus_goal()
    if focus is None:
        return None, 0.0, EpisodeGoalRelation.UNKNOWN

    goal_id: Optional[str] = getattr(focus, "id", None) or getattr(focus, "goal_id", None)

    relevance = 0.0

    # Location overlap
    goal_location = getattr(focus, "target_location_id", None)
    if goal_location is None and hasattr(focus, "target") and isinstance(focus.target, dict):
        goal_location = focus.target.get("location_id")
    if location_id is not None and goal_location is not None and location_id == goal_location:
        relevance += 0.6

    # Resource / domain overlap: basic needs
    goal_kind = getattr(focus, "kind", None) or getattr(focus, "tag", None)
    if goal_kind is None:
        goal_kind = getattr(focus, "goal_type", None)
    if isinstance(goal_kind, str):
        if goal_kind in ("eat", "get_food", "get_water", "drink"):
            if summary_tag.startswith("queue_") or summary_tag.startswith("body_hunger") or summary_tag.startswith("body_thirst"):
                relevance += 0.6
        if goal_kind in ("rest", "sleep"):
            if summary_tag.startswith("body_fatigue"):
                relevance += 0.6
    elif hasattr(goal_kind, "value"):
        kind_value = str(getattr(goal_kind, "value"))
        if kind_value in ("eat", "get_food", "get_water", "drink"):
            if summary_tag.startswith("queue_") or summary_tag.startswith("body_hunger") or summary_tag.startswith("body_thirst"):
                relevance += 0.6
        if kind_value in ("rest", "sleep"):
            if summary_tag.startswith("body_fatigue"):
                relevance += 0.6

    # Target overlap (for future use; placeholder)
    goal_target_id = getattr(focus, "target_agent_id", None)
    if goal_target_id is None and hasattr(focus, "target") and isinstance(focus.target, dict):
        goal_target_id = focus.target.get("agent_id")
    if target_id is not None and goal_target_id is not None and target_id == goal_target_id:
        relevance += 0.7

    # Clamp to [0, 1].
    relevance = max(0.0, min(1.0, relevance))

    # v0: we don't distinguish SUPPORTS vs THWARTS; keep UNKNOWN.
    relation = EpisodeGoalRelation.UNKNOWN

    return goal_id, relevance, relation


class EpisodeFactory:
    """
    Helper to build scored Episode instances from runtime information.

    This is scaffolding for future integration: it centralizes the logic for
    setting importance, reliability, emotion, and goal_relevance based on
    channel and summary_tag, per D-MEMORY-0203 and D-MEMORY-0204.
    """

    def build_episode(
        self,
        owner: AgentState,
        tick: int,
        *,
        summary_tag: str,
        channel: EpisodeChannel,
        location_id: Optional[str] = None,
        target_type: EpisodeTargetType = EpisodeTargetType.OTHER,
        target_id: Optional[str] = None,
        event_id: Optional[str] = None,
        source_agent_id: Optional[str] = None,
    ) -> Episode:
        # Tag defaults
        tag_cfg = SUMMARY_TAG_CONFIG.get(
            summary_tag,
            TagConfig(
                base_importance=0.3,
                default_outcome=EpisodeOutcome.NEUTRAL,
                valence=0.0,
                arousal=0.0,
                threat=0.0,
            ),
        )

        # Channel defaults
        reliability, importance_bonus = _channel_defaults(channel)

        # Emotion snapshot from tag config
        emotion = EmotionSnapshot(
            valence=tag_cfg.valence,
            arousal=tag_cfg.arousal,
            threat=tag_cfg.threat,
        )

        # Base importance from tag + channel bonus
        importance = max(0.0, min(1.0, tag_cfg.base_importance + importance_bonus))

        # Goal linkage
        goal_id, goal_relevance, goal_relation = _compute_goal_relevance(
            owner=owner,
            summary_tag=summary_tag,
            location_id=location_id,
            target_id=target_id,
        )

        # Simple episode_id: uuid4
        episode_id = f"ep:{uuid.uuid4().hex}"

        episode = Episode(
            episode_id=episode_id,
            owner_agent_id=owner.agent_id,
            tick=tick,
            location_id=location_id,
            channel=channel,
            source_agent_id=source_agent_id,
            event_id=event_id,
            target_type=target_type,
            target_id=target_id,
            verb=summary_tag.upper(),  # simple mapping for now
            summary_tag=summary_tag,
            goal_id=goal_id,
            goal_relation=goal_relation,
            goal_relevance=goal_relevance,
            outcome=tag_cfg.default_outcome,
            emotion=emotion,
            importance=importance,
            reliability=reliability,
        )

        return episode
