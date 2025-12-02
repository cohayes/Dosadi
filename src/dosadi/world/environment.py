from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class PlaceEnvironmentState:
    place_id: str

    # 0.0 = hostile/uncomfortable, 1.0 = ideal interior comfort
    comfort: float = 0.5

    # Optional coarse attributes (can be refined later)
    temperature: float = 0.0  # deviation from ideal, -1 .. +1
    humidity: float = 0.0  # deviation from ideal, -1 .. +1


def get_or_create_place_env(
    world: "WorldState", place_id: str
) -> PlaceEnvironmentState:
    env_map: Dict[str, PlaceEnvironmentState] = getattr(world, "place_environment", {})
    env = env_map.get(place_id)
    if env is None:
        env = PlaceEnvironmentState(place_id=place_id)
        env_map[place_id] = env
        world.place_environment = env_map
    return env


__all__ = ["PlaceEnvironmentState", "get_or_create_place_env"]
