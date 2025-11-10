"""Procedural world generation following the design briefs."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable, List

from .state import AgentState, FactionState, WardState, WorldState


@dataclass
class WorldgenConfig:
    seed: int = 0
    ward_count: int = 12
    faction_count: int = 6
    agents_per_faction: int = 8


def generate_world(config: WorldgenConfig) -> WorldState:
    rng = Random(config.seed)
    world = WorldState()
    for i in range(1, config.ward_count + 1):
        ward = WardState(
            id=f"ward:{i}",
            name=f"Ward {i}",
            ring=1 + (i - 1) // 6,
            sealed_mode="INNER" if i <= 6 else ("MIDDLE" if i <= 20 else "OUTER"),
        )
        ward.stocks.water_liters = rng.uniform(100.0, 500.0)
        ward.stocks.biomass_kg = rng.uniform(20.0, 60.0)
        world.register_ward(ward)

    for i in range(config.faction_count):
        home = f"ward:{(i % config.ward_count) + 1}"
        faction = FactionState(
            id=f"faction:{i}",
            name=f"Faction {i}",
            archetype=rng.choice(
                ["FEUDAL", "GUILD", "MILITARY", "CIVIC", "CULT", "CLERK", "RECLAIMER", "SMUGGLER"]
            ),
            home_ward=home,
        )
        faction.assets.water_liters = rng.uniform(50.0, 150.0)
        faction.assets.biomass_kg = rng.uniform(5.0, 30.0)
        world.register_faction(faction)
        if home in world.wards:
            world.wards[home].governor_faction = faction.id

        for j in range(config.agents_per_faction):
            agent = AgentState(
                id=f"agent:{i}:{j}",
                name=f"Agent {i}-{j}",
                faction=faction.id,
                ward=home,
            )
            agent.inventory["owned"].append(f"ration:{j}")
            faction.members.append(agent.id)
            world.register_agent(agent)

    return world


__all__ = ["WorldgenConfig", "generate_world"]

