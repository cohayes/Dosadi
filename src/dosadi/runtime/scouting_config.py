from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ScoutConfig:
    max_active_missions: int = 2
    party_size: int = 2
    max_days_per_mission: int = 5

    new_node_chance: float = 0.35
    new_edge_chance: float = 0.60
    confidence_gain_on_revisit: float = 0.05
    confidence_new_node: float = 0.55
    confidence_cap: float = 0.95

    base_fail_chance: float = 0.02
    hazard_fail_multiplier: float = 2.0

    allow_reuse_agent_days: int = 2


__all__ = ["ScoutConfig"]
