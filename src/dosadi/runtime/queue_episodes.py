from __future__ import annotations

from typing import Iterable, Optional

from dosadi.agents.core import AgentState
from dosadi.memory.episode_factory import EpisodeFactory
from dosadi.memory.episodes import EpisodeChannel, EpisodeTargetType


class QueueEpisodeEmitter:
    """
    Helper for emitting queue-related episodes using EpisodeFactory.

    This is intended to be called by queue/ration systems when queue outcomes
    are resolved. It does not implement queue logic itself.
    """

    def __init__(self, factory: Optional[EpisodeFactory] = None) -> None:
        self.factory = factory or EpisodeFactory()

    def queue_served(
        self,
        *,
        tick: int,
        queue_location_id: str,
        served_agents: Iterable[AgentState],
        wait_ticks: Optional[dict[str, int]] = None,
        observers: Iterable[AgentState] = (),
        event_id: Optional[str] = None,
    ) -> None:
        for agent in served_agents:
            wait = 0
            if wait_ticks:
                wait = wait_ticks.get(agent.agent_id, 0)
            episode = self.factory.build_episode(
                owner=agent,
                tick=tick,
                summary_tag="queue_served",
                channel=EpisodeChannel.DIRECT,
                location_id=queue_location_id,
                target_type=EpisodeTargetType.PLACE,
                target_id=queue_location_id,
                event_id=event_id,
            )
            episode.tags.add("queue_served")
            episode.details["wait_ticks"] = wait
            agent.record_episode(episode)

        for agent in observers:
            episode = self.factory.build_episode(
                owner=agent,
                tick=tick,
                summary_tag="queue_served",
                channel=EpisodeChannel.OBSERVED,
                location_id=queue_location_id,
                target_type=EpisodeTargetType.PLACE,
                target_id=queue_location_id,
                event_id=event_id,
            )
            episode.tags.add("queue_served")
            agent.record_episode(episode)

    def queue_denied(
        self,
        *,
        tick: int,
        queue_location_id: str,
        denied_agents: Iterable[AgentState],
        observers: Iterable[AgentState] = (),
        event_id: Optional[str] = None,
    ) -> None:
        for agent in denied_agents:
            episode = self.factory.build_episode(
                owner=agent,
                tick=tick,
                summary_tag="queue_denied",
                channel=EpisodeChannel.DIRECT,
                location_id=queue_location_id,
                target_type=EpisodeTargetType.PLACE,
                target_id=queue_location_id,
                event_id=event_id,
            )
            episode.tags.add("queue_denied")
            agent.record_episode(episode)

        for agent in observers:
            episode = self.factory.build_episode(
                owner=agent,
                tick=tick,
                summary_tag="queue_denied",
                channel=EpisodeChannel.OBSERVED,
                location_id=queue_location_id,
                target_type=EpisodeTargetType.PLACE,
                target_id=queue_location_id,
                event_id=event_id,
            )
            episode.tags.add("queue_denied")
            agent.record_episode(episode)

    def queue_canceled(
        self,
        *,
        tick: int,
        queue_location_id: str,
        affected_agents: Iterable[AgentState],
        observers: Iterable[AgentState] = (),
        event_id: Optional[str] = None,
    ) -> None:
        for agent in affected_agents:
            episode = self.factory.build_episode(
                owner=agent,
                tick=tick,
                summary_tag="queue_canceled",
                channel=EpisodeChannel.DIRECT,
                location_id=queue_location_id,
                target_type=EpisodeTargetType.PLACE,
                target_id=queue_location_id,
                event_id=event_id,
            )
            episode.tags.add("queue_canceled")
            agent.record_episode(episode)

        for agent in observers:
            episode = self.factory.build_episode(
                owner=agent,
                tick=tick,
                summary_tag="queue_canceled",
                channel=EpisodeChannel.OBSERVED,
                location_id=queue_location_id,
                target_type=EpisodeTargetType.PLACE,
                target_id=queue_location_id,
                event_id=event_id,
            )
            episode.tags.add("queue_canceled")
            agent.record_episode(episode)

    def queue_fight(
        self,
        *,
        tick: int,
        queue_location_id: str,
        involved_agents: Iterable[AgentState],
        observers: Iterable[AgentState] = (),
        event_id: Optional[str] = None,
    ) -> None:
        """
        Called when a fight or severe altercation breaks out in/near a queue.
        """
        for agent in involved_agents:
            episode = self.factory.build_episode(
                owner=agent,
                tick=tick,
                summary_tag="queue_fight",
                channel=EpisodeChannel.DIRECT,
                location_id=queue_location_id,
                target_type=EpisodeTargetType.PLACE,
                target_id=queue_location_id,
                event_id=event_id,
            )
            episode.tags.add("queue_fight")
            agent.record_episode(episode)

        for agent in observers:
            episode = self.factory.build_episode(
                owner=agent,
                tick=tick,
                summary_tag="queue_fight",
                channel=EpisodeChannel.OBSERVED,
                location_id=queue_location_id,
                target_type=EpisodeTargetType.PLACE,
                target_id=queue_location_id,
                event_id=event_id,
            )
            episode.tags.add("queue_fight")
            agent.record_episode(episode)
