import math
import pickle

from dosadi.agent.beliefs import Belief, BeliefStore
from dosadi.agent.memory_crumbs import CrumbCounter, CrumbStore
from dosadi.agents.core import AgentState
from dosadi.runtime.belief_formation import run_belief_formation_for_day
from dosadi.runtime.event_to_memory_router import run_router_for_day
from dosadi.state import WorldState
from dosadi.world.events import EventKind, WorldEvent, WorldEventLog


def _make_agent(agent_id: str) -> AgentState:
    return AgentState(agent_id=agent_id, name=agent_id)


def _make_world_with_event() -> WorldState:
    world = WorldState(seed=0)
    agent = _make_agent("agent-1")
    world.register_agent(agent)
    world.event_log = WorldEventLog(max_len=100)
    event = WorldEvent(
        event_id="",
        day=0,
        kind=EventKind.DELIVERY_FAILED,
        subject_kind="delivery",
        subject_id="del-1",
        severity=0.7,
        payload={"edge_key": "a-b"},
    )
    world.event_log.append(event)
    return world


def test_deterministic_belief_signature():
    world_a = _make_world_with_event()
    run_router_for_day(world_a, day=0)
    run_belief_formation_for_day(world_a, day=0)
    sig_a = world_a.agents["agent-1"].beliefs.signature()

    world_b = _make_world_with_event()
    run_router_for_day(world_b, day=0)
    run_belief_formation_for_day(world_b, day=0)
    sig_b = world_b.agents["agent-1"].beliefs.signature()

    assert sig_a == sig_b


def test_belief_store_retains_top_weights():
    store = BeliefStore(max_items=2)
    store.upsert(Belief(key="a", value=0.2, weight=0.2, last_day=0))
    store.upsert(Belief(key="b", value=0.9, weight=0.9, last_day=0))
    store.upsert(Belief(key="c", value=0.5, weight=0.5, last_day=0))

    assert set(store.items.keys()) == {"b", "c"}


def test_belief_update_math():
    world = WorldState(seed=1)
    agent = _make_agent("agent-x")
    agent.crumbs = CrumbStore(tags={"route-risk:x": CrumbCounter(count=3, last_day=0)})
    world.register_agent(agent)
    world.agents_with_new_signals.add(agent.agent_id)

    run_belief_formation_for_day(world, day=0)

    belief = agent.beliefs.get("route-risk:x")
    assert belief is not None
    expected_signal = 1.0 - math.exp(-3.0 / 3.0)
    assert math.isclose(belief.value, expected_signal, rel_tol=1e-6)

    # Second update with lower signal to exercise EMA behavior.
    agent.crumbs.tags["route-risk:x"].count = 1
    world.agents_with_new_signals.add(agent.agent_id)
    run_belief_formation_for_day(world, day=1)
    new_signal = 1.0 - math.exp(-1.0 / 3.0)
    expected_value = (1 - 0.10) * expected_signal + 0.10 * new_signal
    assert math.isclose(agent.beliefs.get("route-risk:x").value, expected_value, rel_tol=1e-6)


def test_belief_decay_applied_when_idle():
    world = WorldState(seed=2)
    agent = _make_agent("agent-decay")
    agent.beliefs = BeliefStore(
        max_items=4,
        items={"route-risk:q": Belief(key="route-risk:q", value=0.5, weight=0.8, last_day=0)},
    )
    world.register_agent(agent)
    world.agents_with_new_signals.add(agent.agent_id)

    run_belief_formation_for_day(world, day=120)

    belief = agent.beliefs.get("route-risk:q")
    assert belief is not None
    assert math.isclose(belief.weight, 0.4, rel_tol=1e-6)
    assert belief.last_day == 120


def test_only_signaled_agents_processed():
    world = WorldState(seed=3)
    for idx in range(5):
        agent = _make_agent(f"a{idx}")
        agent.crumbs = CrumbStore(tags={"route-risk:x": CrumbCounter(count=2, last_day=0)})
        world.register_agent(agent)
    world.agents_with_new_signals.update({"a0", "a1"})

    run_belief_formation_for_day(world, day=0)

    assert "route-risk:x" in world.agents["a0"].beliefs.items
    assert "route-risk:x" in world.agents["a1"].beliefs.items
    assert world.agents["a2"].beliefs.items == {}


def test_beliefs_survive_pickle_roundtrip():
    world = _make_world_with_event()
    run_router_for_day(world, day=0)
    run_belief_formation_for_day(world, day=0)

    blob = pickle.dumps(world)
    restored: WorldState = pickle.loads(blob)

    assert restored.belief_state.last_run_day == 0
    assert restored.agents["agent-1"].beliefs.signature() == world.agents["agent-1"].beliefs.signature()
