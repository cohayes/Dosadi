import types

import pytest

from dosadi.agents.core import AgentState
from dosadi.state import WorldState
from dosadi.testing.kpis import collect_kpis
from dosadi.runtime.snapshot import world_signature


def test_collect_kpis_counts_and_averages():
    world = WorldState()
    world.tick = world.config.ticks_per_day * 370

    agent_a = AgentState(agent_id="agent:a", name="Agent A")
    agent_a.physical.hunger_level = 0.1
    agent_a.physical.hydration_level = 0.8
    agent_a.physical.sleep_pressure = 0.2
    world.agents[agent_a.id] = agent_a

    agent_b = AgentState(agent_id="agent:b", name="Agent B")
    agent_b.physical.hunger_level = 0.3
    agent_b.physical.hydration_level = 0.6
    agent_b.physical.sleep_pressure = 0.4
    world.agents[agent_b.id] = agent_b

    kpis = collect_kpis(world)

    assert kpis["agents_total"] == 2
    assert kpis["day"] == 370
    assert kpis["year"] == 1
    assert kpis["avg_hunger"] == pytest.approx(0.2)
    assert kpis["avg_hydration"] == pytest.approx(0.7)
    assert kpis["avg_sleep_pressure"] == pytest.approx(0.3)
    assert "world_signature" not in kpis


def test_collect_kpis_signature_toggle():
    world = WorldState()
    world.runtime_config = types.SimpleNamespace(kpi_signatures_enabled=True)

    kpis = collect_kpis(world)

    assert kpis.get("world_signature") == world_signature(world)
