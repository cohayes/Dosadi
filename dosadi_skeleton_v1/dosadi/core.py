
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

TICK_SECONDS = 0.6
TICKS_PER_MINUTE = 100
MINUTES_PER_DAY = 1440

@dataclass
class WorldState:
    seed: int = 0
    time_min: int = 0
    wards: List[dict] = field(default_factory=list)
    routes: List[dict] = field(default_factory=list)
    policy: Dict[str, dict] = field(default_factory=dict)

def minute_tick(ws: WorldState) -> None:
    """Advance one sim minute. Subsystems should be called by `DosadiSim.on_minute`."""
    ws.time_min += 1

def day_tick(ws: WorldState) -> None:
    """Advance one sim day (aggregate updates)."""
    ws.time_min += MINUTES_PER_DAY
