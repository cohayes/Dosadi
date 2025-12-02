from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WellState:
    well_id: str = "well:core"

    # Max amount pumpable per "day"
    daily_capacity: float = 10_000.0

    # Amount pumped in current day window
    pumped_today: float = 0.0

    # Optional: rolling average utilization for debugging
    utilization_rolling: float = 0.0
