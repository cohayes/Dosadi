from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Deque, Dict, List, Optional, Set


class EpisodeChannel(Enum):
    """How this episode reached the agent."""

    DIRECT = auto()
    OBSERVED = auto()
    REPORT = auto()
    RUMOR = auto()
    PROTOCOL = auto()
    BODY_SIGNAL = auto()


class EpisodeTargetType(Enum):
    """What the episode is mainly about."""

    SELF = auto()
    PERSON = auto()
    PLACE = auto()
    FACTION = auto()
    PROTOCOL = auto()
    OBJECT = auto()
    RESOURCE = auto()
    OTHER = auto()


class EpisodeOutcome(Enum):
    """Coarse outcome classification."""

    NEUTRAL = auto()
    SUCCESS = auto()
    FAILURE = auto()
    HARM = auto()
    HELP = auto()
    NEAR_MISS = auto()


class EpisodeGoalRelation(Enum):
    """How this episode relates to the agent's current goal."""

    UNKNOWN = auto()
    IRRELEVANT = auto()
    SUPPORTS = auto()
    THWARTS = auto()
    MIXED = auto()


class EpisodeVerb:
    """Canonical episode verb names used throughout the simulation."""

    # Scout & survey
    SCOUT_PLACE = "SCOUT_PLACE"
    CORRIDOR_CROWDING_OBSERVED = "CORRIDOR_CROWDING_OBSERVED"
    HAZARD_FOUND = "HAZARD_FOUND"

    # Inventory & stores
    CRATE_OPENED = "CRATE_OPENED"
    RESOURCE_STOCKED = "RESOURCE_STOCKED"
    QUEUE_SERVED = "QUEUE_SERVED"
    QUEUE_DENIED = "QUEUE_DENIED"
    DISPUTE_AT_STORES = "DISPUTE_AT_STORES"

    # Environment & suits
    ENV_NODE_TUNED = "ENV_NODE_TUNED"
    ENV_NODE_FAILURE = "ENV_NODE_FAILURE"
    SUIT_TUNED = "SUIT_TUNED"
    SUIT_FAILURE_NEAR_MISS = "SUIT_FAILURE_NEAR_MISS"
    BODY_SIGNAL = "BODY_SIGNAL"

    # Food & water
    FOOD_SERVED = "FOOD_SERVED"
    FOOD_SHORTAGE_EPISODE = "FOOD_SHORTAGE_EPISODE"
    BARREL_MOVED = "BARREL_MOVED"
    LEAK_FOUND = "LEAK_FOUND"
    WATER_LOSS_INCIDENT = "WATER_LOSS_INCIDENT"
    WELL_PUMPED = "WELL_PUMPED"
    WATER_DELIVERED = "WATER_DELIVERED"
    DRANK_WATER = "DRANK_WATER"
    WATER_DENIED = "WATER_DENIED"

    # Knowledge & coordination
    REPORT_RECEIVED = "REPORT_RECEIVED"
    MAP_UPDATED = "MAP_UPDATED"
    LEDGER_UPDATED = "LEDGER_UPDATED"

    # Career progression
    PROMOTED_TO_TIER = "PROMOTED_TO_TIER"
    ASSIGNMENT_GIVEN = "ASSIGNMENT_GIVEN"
    ASSIGNMENT_DISPUTE = "ASSIGNMENT_DISPUTE"


@dataclass
class EmotionSnapshot:
    """
    Minimal emotional state associated with an episode.

    valence: -1 (very negative) .. +1 (very positive)
    arousal: 0 (calm) .. 1 (highly activated)
    threat:  0 (safe) .. 1 (immediate danger)
    """

    valence: float = 0.0
    arousal: float = 0.0
    threat: float = 0.0


@dataclass
class Episode:
    """
    A single, owner-relative record of something the agent experienced or learned.

    Episodes live in short-term and daily buffers and are periodically compressed
    into beliefs. Most episodes will be discarded; only a minority leave lasting
    traces in belief structures or written logs.
    """

    episode_id: str

    owner_agent_id: str
    tick: int

    # Where this happened (coarse).
    location_id: Optional[str] = None  # facility_id / corridor_id / ward_id

    # Channel & source.
    channel: EpisodeChannel = EpisodeChannel.DIRECT
    source_agent_id: Optional[str] = None  # teller, reporter, oppressor, etc.

    # Optional link to a world event record, if one exists.
    event_id: Optional[str] = None

    # Focus of the episode (what it's mainly "about").
    target_type: EpisodeTargetType = EpisodeTargetType.OTHER
    target_id: Optional[str] = None  # agent_id, facility_id, faction_id, etc.

    # Action semantics from this agent's perspective.
    verb: str = ""  # e.g. "SEE_FIGHT", "QUEUE_DENIED", "READ_PROTOCOL"
    summary_tag: str = ""  # short code for clustering: "queue_fight", "guard_cruelty"

    # Goal linkage.
    goal_id: Optional[str] = None  # current goal id, if known
    goal_relation: EpisodeGoalRelation = EpisodeGoalRelation.UNKNOWN
    goal_relevance: float = 0.0  # 0–1: how important for that goal

    # Subjective evaluation.
    outcome: EpisodeOutcome = EpisodeOutcome.NEUTRAL
    emotion: EmotionSnapshot = field(default_factory=EmotionSnapshot)

    # Salience and reliability.
    importance: float = 0.0  # 0–1: promotion/retention weight
    reliability: float = 0.5  # 0–1: trust in this episode's accuracy

    # Optional tag set for later pattern mining.
    tags: Set[str] = field(default_factory=set)

    # Tiny structured payload for role-specific details.
    details: Dict[str, float | int | str] = field(default_factory=dict)


@dataclass
class EpisodeBuffers:
    """
    Container for an agent's episodic memory layers.

    - short_term: very recent, high-churn episodes (minutes).
    - daily: promoted episodes that will be considered during the next sleep
      consolidation.
    - archive_refs: optional references to externally recorded episodes/logs
      (for scribes, auditors, etc.).
    """

    short_term: Deque[Episode] = field(default_factory=deque)
    daily: List[Episode] = field(default_factory=list)

    # For agents whose job includes record-keeping, they may keep references
    # to long-lived external records instead of internal full episodes.
    archive_refs: List[str] = field(default_factory=list)  # e.g. admin_log ids

    # Capacity hints (actual values can be set per agent/tier).
    short_term_capacity: int = 50
    daily_capacity: int = 100

    def push_short_term(self, episode: Episode) -> None:
        """
        Add an episode to short-term buffer, evicting a low-importance episode
        if over capacity.
        """

        self.short_term.append(episode)
        if len(self.short_term) > self.short_term_capacity:
            # Simple eviction: drop the lowest-importance episode.
            lowest_idx = None
            lowest_importance = 1.1
            for idx, ep in enumerate(self.short_term):
                imp = getattr(ep, "importance", 0.0)
                if imp < lowest_importance:
                    lowest_importance = imp
                    lowest_idx = idx
            if lowest_idx is not None:
                # remove by index using rotate/popleft
                self.short_term.rotate(-lowest_idx)
                self.short_term.popleft()
                self.short_term.rotate(lowest_idx)

    def promote_to_daily(self, episode: Episode) -> None:
        """
        Move or copy an episode into the daily buffer, respecting capacity.
        Lower-importance daily episodes are dropped on overflow.
        """

        self.daily.append(episode)
        if len(self.daily) > self.daily_capacity:
            # drop lowest-importance daily episode
            self.daily.sort(
                key=lambda ep: getattr(ep, "importance", 0.0),
                reverse=True,
            )
            self.daily = self.daily[: self.daily_capacity]
