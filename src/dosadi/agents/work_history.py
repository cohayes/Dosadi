from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import math

from dosadi.runtime.work_details import WorkDetailType


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
