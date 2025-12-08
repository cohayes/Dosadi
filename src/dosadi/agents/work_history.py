from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, TYPE_CHECKING

import math

from dosadi.runtime.work_details import WorkDetailType

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from dosadi.agents.core import AgentState


@dataclass
class WorkPreference:
    # Preference in [-1.0, 1.0]
    # -1.0 = strongly dislikes / avoids
    #  0.0 = neutral
    # +1.0 = strongly likes / seeks
    preference: float = 0.0

    # Smoothed recent experience ([-1, 1])
    recent_enjoyment: float = 0.0

    # Number of shifts contributing to this preference
    samples: int = 0


@dataclass
class WorkPreferences:
    per_type: Dict[WorkDetailType, WorkPreference] = field(default_factory=dict)

    def get_or_create(self, work_type: WorkDetailType) -> WorkPreference:
        if work_type not in self.per_type:
            self.per_type[work_type] = WorkPreference()
        return self.per_type[work_type]


@dataclass
class WorkDetailHistory:
    # Total "effective ticks" spent on this work type (already perf-weighted)
    ticks: float = 0.0
    # Number of completed shifts/assignments
    shifts: int = 0
    # Cached proficiency in [0.0, 1.0]
    proficiency: float = 0.0


@dataclass
class WorkHistory:
    per_type: Dict[WorkDetailType, WorkDetailHistory] = field(default_factory=dict)

    def get_or_create(self, work_type: WorkDetailType) -> WorkDetailHistory:
        if work_type not in self.per_type:
            self.per_type[work_type] = WorkDetailHistory()
        return self.per_type[work_type]


WORK_PROFICIENCY_HORIZONS = {
    WorkDetailType.SCOUT_INTERIOR: 80_000.0,
    WorkDetailType.INVENTORY_STORES: 80_000.0,
    WorkDetailType.FOOD_PROCESSING: 60_000.0,
    WorkDetailType.ENV_CONTROL: 60_000.0,
    WorkDetailType.WATER_HANDLING: 60_000.0,
}


def ticks_to_proficiency(work_type: WorkDetailType, ticks: float) -> float:
    horizon = WORK_PROFICIENCY_HORIZONS.get(work_type, 80_000.0)
    if horizon <= 0.0:
        return 0.0
    x = max(0.0, ticks) / horizon
    # Saturating curve: 1 - exp(-x)
    prof = 1.0 - math.exp(-x)
    if prof < 0.0:
        prof = 0.0
    elif prof > 1.0:
        prof = 1.0
    return prof


def update_work_preference_after_shift(
    agent: "AgentState",
    work_type: WorkDetailType,
    enjoyment_score: float,
) -> None:
    """
    Update the agent's preference for `work_type` based on a single shift
    experience, summarized as enjoyment_score in [-1.0, 1.0].
    """

    wp = agent.work_preferences.get_or_create(work_type)

    # Clamp enjoyment to [-1, 1]
    enjoyment = max(-1.0, min(1.0, enjoyment_score))

    # Exponential moving average for recent_enjoyment
    alpha = 0.2
    wp.recent_enjoyment = (1.0 - alpha) * wp.recent_enjoyment + alpha * enjoyment

    # Slowly nudge preference toward recent_enjoyment
    beta = 0.1
    wp.preference += beta * (wp.recent_enjoyment - wp.preference)

    # Clamp preference
    if wp.preference < -1.0:
        wp.preference = -1.0
    elif wp.preference > 1.0:
        wp.preference = 1.0

    wp.samples += 1
