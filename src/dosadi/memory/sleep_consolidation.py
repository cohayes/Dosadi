"""Sleep-time memory consolidation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dosadi.agents.core import AgentState
from dosadi.memory.config import MemoryConfig
from dosadi.runtime.memory_runtime import promote_daily_memory, run_sleep_consolidation

if TYPE_CHECKING:  # pragma: no cover
    from dosadi.state import WorldState


def consolidate_sleep_for_agent(world: "WorldState", agent: AgentState) -> None:
    """Run the memory consolidation sequence for an agent at sleep completion."""

    config = getattr(world, "memory_config", None) or MemoryConfig()
    world.memory_config = config

    tick = getattr(world, "tick", getattr(world, "current_tick", 0))

    promote_daily_memory(agent, tick, config, force=True)
    run_sleep_consolidation(agent, tick, config)
