from dosadi.agents.core import AgentState
from dosadi.memory.episode_factory import EpisodeFactory
from dosadi.memory.episodes import EpisodeChannel


def test_build_episode_from_known_tag():
    agent = AgentState(agent_id="agent-1", name="Tester")
    factory = EpisodeFactory()

    episode = factory.build_episode(
        owner=agent,
        tick=10,
        summary_tag="queue_fight",
        channel=EpisodeChannel.DIRECT,
        location_id="loc:test",
    )

    assert episode.owner_agent_id == agent.agent_id
    assert episode.tick == 10
    assert episode.summary_tag == "queue_fight"
    assert episode.verb == "QUEUE_FIGHT"
    assert 0.0 <= episode.importance <= 1.0
    assert 0.0 <= episode.reliability <= 1.0
    assert 0.0 <= episode.emotion.threat <= 1.0


def test_build_episode_with_unknown_tag_defaults():
    agent = AgentState(agent_id="agent-2", name="Fallback")
    factory = EpisodeFactory()

    episode = factory.build_episode(
        owner=agent,
        tick=5,
        summary_tag="unknown_event",
        channel=EpisodeChannel.RUMOR,
    )

    assert episode.owner_agent_id == agent.agent_id
    assert episode.tick == 5
    assert episode.summary_tag == "unknown_event"
    assert episode.verb == "UNKNOWN_EVENT"
    assert 0.0 <= episode.importance <= 1.0
    assert 0.0 <= episode.reliability <= 1.0
    assert 0.0 <= episode.emotion.threat <= 1.0
