import copy
import random

import pytest

from dosadi.agents.core import AgentState
from dosadi.runtime.eating import chronic_update_agent_physical_state
from dosadi.runtime.timewarp import step_day
from dosadi.state import WorldState


def _build_world(seed: int, agent_count: int) -> WorldState:
    world = WorldState(seed=seed)
    world.rng = random.Random(seed)

    for idx in range(agent_count):
        agent = AgentState(agent_id=f"agent:{idx}", name=f"Agent {idx}")
        rng = random.Random(seed + idx)
        agent.physical.hunger_level = rng.uniform(0.0, 0.3)
        agent.physical.hydration_level = rng.uniform(0.6, 1.0)
        agent.physical.stress_level = rng.uniform(0.0, 0.2)
        world.agents[agent.id] = agent

    return world


def _collect_kpis(world: WorldState) -> dict:
    agents = list(world.agents.values())
    hunger_values = [a.physical.hunger_level for a in agents]
    hydration_values = [a.physical.hydration_level for a in agents]
    sleep_pressures = [a.physical.sleep_pressure for a in agents]

    return {
        "tick": world.tick,
        "total_agents": len(agents),
        "avg_hunger": sum(hunger_values) / len(hunger_values),
        "avg_hydration": sum(hydration_values) / len(hydration_values),
        "avg_sleep_pressure": sum(sleep_pressures) / len(sleep_pressures),
    }


def test_timewarp_step_day_matches_tick_mode_kpis_small_world():
    world_tick = _build_world(seed=42, agent_count=4)
    ticks_per_day = world_tick.config.ticks_per_day

    for tick in range(ticks_per_day):
        world_tick.tick = tick
        for agent_id in sorted(world_tick.agents.keys()):
            chronic_update_agent_physical_state(world_tick, world_tick.agents[agent_id], world_tick.rng)
    world_tick.tick = ticks_per_day

    baseline_kpis = _collect_kpis(world_tick)

    world_macro = _build_world(seed=42, agent_count=4)
    step_day(world_macro, days=1)

    macro_kpis = _collect_kpis(world_macro)

    assert world_macro.tick == ticks_per_day
    assert macro_kpis["total_agents"] == baseline_kpis["total_agents"]
    assert macro_kpis["tick"] == baseline_kpis["tick"]
    assert macro_kpis["avg_hunger"] == pytest.approx(baseline_kpis["avg_hunger"], abs=0.02)
    assert macro_kpis["avg_hydration"] == pytest.approx(baseline_kpis["avg_hydration"], abs=0.02)
    assert macro_kpis["avg_sleep_pressure"] == pytest.approx(
        baseline_kpis["avg_sleep_pressure"], abs=0.05
    )


def test_timewarp_deterministic_replay_same_seed_same_result():
    world_a = _build_world(seed=99, agent_count=3)
    world_b = copy.deepcopy(world_a)

    step_day(world_a, days=2)
    step_day(world_b, days=2)

    assert world_a.tick == world_b.tick

    for agent_id in sorted(world_a.agents.keys()):
        agent_a = world_a.agents[agent_id]
        agent_b = world_b.agents[agent_id]
        assert agent_a.physical.hunger_level == pytest.approx(agent_b.physical.hunger_level)
        assert agent_a.physical.hydration_level == pytest.approx(agent_b.physical.hydration_level)
        assert agent_a.physical.sleep_pressure == pytest.approx(agent_b.physical.sleep_pressure)
        assert agent_a.physical.stress_level == pytest.approx(agent_b.physical.stress_level)
