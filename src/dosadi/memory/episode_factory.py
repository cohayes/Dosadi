from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Set

from dosadi.agents.core import AgentState, Goal
from dosadi.memory.episodes import (
    EmotionSnapshot,
    Episode,
    EpisodeChannel,
    EpisodeGoalRelation,
    EpisodeOutcome,
    EpisodeTargetType,
    EpisodeVerb,
)
from dosadi.state import WorldState


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


_episode_id_counter = itertools.count()


@dataclass
class EpisodeFactory:
    """
    Helper to build scored Episode instances from runtime information.

    This is scaffolding for future integration: it centralizes the logic for
    setting importance, reliability, emotion, and goal_relevance based on
    channel and summary_tag, per D-MEMORY-0203 and D-MEMORY-0204.
    """

    world: Optional[WorldState] = None

    def _next_episode_id(self) -> str:
        return f"ep:{next(_episode_id_counter)}"

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

    def create_body_signal_episode(
        self,
        *,
        owner_agent_id: str,
        tick: int,
        signal_type: str,
        intensity: float,
    ) -> Episode:
        intensity = max(0.0, min(1.0, float(intensity)))
        emotion = EmotionSnapshot(valence=0.0, arousal=intensity, threat=0.0)
        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=None,
            channel=EpisodeChannel.BODY_SIGNAL,
            target_type=EpisodeTargetType.SELF,
            target_id=owner_agent_id,
            verb=EpisodeVerb.BODY_SIGNAL,
            summary_tag="body_signal",
            goal_relation=EpisodeGoalRelation.UNKNOWN,
            goal_relevance=0.2,
            outcome=EpisodeOutcome.NEUTRAL,
            emotion=emotion,
            importance=0.2 + 0.3 * intensity,
            reliability=0.9,
            tags={"body_signal"},
            details={
                "signal_type": signal_type,
                "intensity": float(intensity),
            },
        )

    def create_scout_place_episode(
        self,
        owner_agent_id: str,
        tick: int,
        place_id: str,
        interior: bool = True,
        hazard_level: float = 0.0,
        visibility: float = 1.0,
        distance_from_pod: float = 0.0,
        note: str = "",
    ) -> Episode:
        tags: Set[str] = {"scout", "mapping"}
        tags.add("interior" if interior else "exterior")

        emotion = EmotionSnapshot(
            valence=0.0 if hazard_level == 0 else -0.2 * hazard_level,
            arousal=0.2 + 0.6 * hazard_level,
            threat=hazard_level,
        )

        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=place_id,
            channel=EpisodeChannel.DIRECT,
            target_type=EpisodeTargetType.PLACE,
            target_id=place_id,
            verb=EpisodeVerb.SCOUT_PLACE,
            summary_tag="scout_place",
            goal_relation=EpisodeGoalRelation.UNKNOWN,
            goal_relevance=0.1,
            outcome=EpisodeOutcome.NEUTRAL,
            emotion=emotion,
            importance=max(0.2, hazard_level),
            reliability=0.7,
            tags=tags,
            details={
                "hazard_level": float(hazard_level),
                "visibility": float(visibility),
                "distance_from_pod": float(distance_from_pod),
                "note": note,
            },
        )

    def create_corridor_crowding_episode(
        self,
        owner_agent_id: str,
        tick: int,
        corridor_id: str,
        estimated_density: float,
        estimated_wait_ticks: int,
    ) -> Episode:
        density = max(0.0, min(1.0, estimated_density))
        emotion = EmotionSnapshot(
            valence=-0.2 * density,
            arousal=0.3 + 0.5 * density,
            threat=0.2 * density,
        )
        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=corridor_id,
            channel=EpisodeChannel.DIRECT,
            target_type=EpisodeTargetType.PLACE,
            target_id=corridor_id,
            verb=EpisodeVerb.CORRIDOR_CROWDING_OBSERVED,
            summary_tag="corridor_crowding",
            goal_relation=EpisodeGoalRelation.UNKNOWN,
            goal_relevance=0.1,
            outcome=EpisodeOutcome.NEUTRAL,
            emotion=emotion,
            importance=0.3 + 0.4 * density,
            reliability=0.7,
            tags={"corridor", "crowding", "queue_like"},
            details={
                "estimated_density": float(density),
                "estimated_wait_ticks": int(estimated_wait_ticks),
            },
        )

    def create_crate_opened_episode(
        self,
        owner_agent_id: str,
        tick: int,
        crate_id: str,
        resource_type: str,
        quantity: float,
        location_id: Optional[str] = None,
    ) -> Episode:
        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=location_id,
            channel=EpisodeChannel.DIRECT,
            target_type=EpisodeTargetType.RESOURCE,
            target_id=crate_id,
            verb=EpisodeVerb.CRATE_OPENED,
            summary_tag="crate_opened",
            goal_relation=EpisodeGoalRelation.SUPPORTS,
            goal_relevance=0.4,
            outcome=EpisodeOutcome.SUCCESS,
            emotion=EmotionSnapshot(valence=0.2, arousal=0.3, threat=0.0),
            importance=0.4,
            reliability=0.8,
            tags={"inventory", "crate", "resource_discovery"},
            details={
                "crate_id": crate_id,
                "resource_type": resource_type,
                "quantity": float(quantity),
            },
        )

    def create_resource_stocked_episode(
        self,
        owner_agent_id: str,
        tick: int,
        place_id: str,
        resource_type: str,
        quantity: float,
    ) -> Episode:
        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=place_id,
            channel=EpisodeChannel.DIRECT,
            target_type=EpisodeTargetType.PLACE,
            target_id=place_id,
            verb=EpisodeVerb.RESOURCE_STOCKED,
            summary_tag="resource_stocked",
            goal_relation=EpisodeGoalRelation.SUPPORTS,
            goal_relevance=0.3,
            outcome=EpisodeOutcome.SUCCESS,
            emotion=EmotionSnapshot(valence=0.1, arousal=0.2, threat=0.0),
            importance=0.3,
            reliability=0.8,
            tags={"inventory", "stocking"},
            details={
                "resource_type": resource_type,
                "quantity": float(quantity),
            },
        )

    def create_food_served_episode(
        self,
        owner_agent_id: str,
        tick: int,
        hall_id: str,
        wait_ticks: int,
        calories_estimate: float,
    ) -> Episode:
        wait_ticks = max(0, wait_ticks)
        normalized_wait = min(1.0, wait_ticks / 10_000.0)
        valence = 0.5 - 0.2 * normalized_wait

        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=hall_id,
            channel=EpisodeChannel.DIRECT,
            target_type=EpisodeTargetType.PLACE,
            target_id=hall_id,
            verb=EpisodeVerb.FOOD_SERVED,
            summary_tag="food_served",
            goal_relation=EpisodeGoalRelation.SUPPORTS,
            goal_relevance=0.7,
            outcome=EpisodeOutcome.SUCCESS,
            emotion=EmotionSnapshot(valence=valence, arousal=0.3, threat=0.0),
            importance=0.5,
            reliability=0.9,
            tags={"food", "served", "meal"},
            details={
                "wait_ticks": int(wait_ticks),
                "calories_estimate": float(calories_estimate),
                "hall_id": hall_id,
            },
        )

    def create_queue_served_episode(
        self,
        owner_agent_id: str,
        tick: int,
        place_id: str,
        wait_ticks: int,
        resource_type: Optional[str] = None,
    ) -> Episode:
        wait_ticks = max(0, wait_ticks)
        normalized_wait = min(1.0, wait_ticks / 10_000.0)
        valence = 0.4 - 0.3 * normalized_wait

        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=place_id,
            channel=EpisodeChannel.DIRECT,
            target_type=EpisodeTargetType.PLACE,
            target_id=place_id,
            verb=EpisodeVerb.QUEUE_SERVED,
            summary_tag="queue_served",
            goal_relation=EpisodeGoalRelation.SUPPORTS,
            goal_relevance=0.6,
            outcome=EpisodeOutcome.SUCCESS,
            emotion=EmotionSnapshot(valence=valence, arousal=0.3, threat=0.0),
            importance=0.4,
            reliability=0.9,
            tags={"queue", "served", "queue_served"},
            details={
                "wait_ticks": int(wait_ticks),
                "resource_type": resource_type or "",
            },
        )

    def create_queue_denied_episode(
        self,
        owner_agent_id: str,
        tick: int,
        place_id: str,
        wait_ticks: int,
        reason: str,
    ) -> Episode:
        wait_ticks = max(0, wait_ticks)
        normalized_wait = min(1.0, wait_ticks / 10_000.0)
        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=place_id,
            channel=EpisodeChannel.DIRECT,
            target_type=EpisodeTargetType.PLACE,
            target_id=place_id,
            verb=EpisodeVerb.QUEUE_DENIED,
            summary_tag="queue_denied",
            goal_relation=EpisodeGoalRelation.THWARTS,
            goal_relevance=0.8,
            outcome=EpisodeOutcome.FAILURE,
            emotion=EmotionSnapshot(
                valence=-0.6 - 0.2 * normalized_wait,
                arousal=0.5 + 0.3 * normalized_wait,
                threat=0.1,
            ),
            importance=0.6,
            reliability=0.9,
            tags={"queue", "denied", "queue_denied"},
            details={
                "wait_ticks": int(wait_ticks),
                "reason": reason,
            },
        )

    def create_food_served_episode(
        self,
        owner_agent_id: str,
        tick: int,
        hall_id: str,
        wait_ticks: int,
        calories_estimate: float,
    ) -> Episode:
        normalized_wait = min(1.0, max(0, wait_ticks) / 10_000.0)
        valence = 0.5 - 0.3 * normalized_wait

        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=hall_id,
            channel=EpisodeChannel.DIRECT,
            target_type=EpisodeTargetType.PLACE,
            target_id=hall_id,
            verb=EpisodeVerb.FOOD_SERVED,
            summary_tag="food_served",
            goal_relation=EpisodeGoalRelation.SUPPORTS,
            goal_relevance=0.7,
            outcome=EpisodeOutcome.HELP,
            emotion=EmotionSnapshot(valence=valence, arousal=0.3, threat=0.0),
            importance=0.5,
            reliability=0.9,
            tags={"food", "meal", "queue"},
            details={
                "wait_ticks": int(wait_ticks),
                "calories_estimate": float(calories_estimate),
            },
        )

    def create_leak_found_episode(
        self,
        owner_agent_id: str,
        tick: int,
        place_id: str,
        severity: float,
        estimated_loss: float,
    ) -> Episode:
        severity = max(0.0, min(1.0, severity))
        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=place_id,
            channel=EpisodeChannel.DIRECT,
            target_type=EpisodeTargetType.PLACE,
            target_id=place_id,
            verb=EpisodeVerb.LEAK_FOUND,
            summary_tag="leak_found",
            goal_relation=EpisodeGoalRelation.UNKNOWN,
            goal_relevance=0.5,
            outcome=EpisodeOutcome.NEAR_MISS,
            emotion=EmotionSnapshot(
                valence=-0.4 - 0.3 * severity,
                arousal=0.5 + 0.3 * severity,
                threat=0.4 + 0.4 * severity,
            ),
            importance=0.6 + 0.3 * severity,
            reliability=0.8,
            tags={"water", "loss", "risk"},
            details={
                "severity": float(severity),
                "estimated_loss": float(estimated_loss),
            },
        )

    def create_env_node_tuned_episode(
        self,
        owner_agent_id: str,
        tick: int,
        place_id: str,
        comfort_before: float,
        comfort_after: float,
    ) -> Episode:
        return Episode(
            episode_id=self._next_episode_id(),
            owner_agent_id=owner_agent_id,
            tick=tick,
            location_id=place_id,
            channel=EpisodeChannel.DIRECT,
            target_type=EpisodeTargetType.PLACE,
            target_id=place_id,
            verb=EpisodeVerb.ENV_NODE_TUNED,
            summary_tag="env_node_tuned",
            goal_relation=EpisodeGoalRelation.SUPPORTS,
            goal_relevance=0.3,
            outcome=EpisodeOutcome.SUCCESS,
            emotion=EmotionSnapshot(valence=0.1, arousal=0.2, threat=0.0),
            importance=0.2,
            reliability=0.9,
            tags={"environment", "comfort"},
            details={
                "comfort_before": float(comfort_before),
                "comfort_after": float(comfort_after),
            },
        )
