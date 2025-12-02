from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FacilityBeliefSummary:
    facility_id: str

    # 0–1, higher is better
    safety_score: float = 0.5
    comfort_score: float = 0.5
    fairness_score: float = 0.5
    queue_pressure: float = 0.0

    # normalized incidents per time window (0+)
    incident_rate: float = 0.0

    # how many agents contributed (for debugging / weighting)
    contributors: int = 0
