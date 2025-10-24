# src/simulation/facility_profile.py
"""
FacilityProfile
---------------
Defines the industrial identity and behavior template for facilities within a district.

Each FacilityProfile declares:
- industry type (service, manufacturing, governance, informal)
- resource inputs and outputs
- morale and corruption modifiers
- event hooks (optional)
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FacilityProfile:
    name: str
    industry: str                 # e.g. "service", "manufacturing", "governance", "informal"
    input_resources: Dict[str, float]   # resources consumed per tick
    output_resources: Dict[str, float]  # resources produced per tick
    morale_weight: float = 1.0          # how much agent morale affects output
    corruption_sensitivity: float = 1.0 # how much corruption influences efficiency
    event_hooks: List[str] = field(default_factory=list)

    def describe(self) -> str:
        return f"{self.name} ({self.industry}) | Inputs: {list(self.input_resources.keys())} → Outputs: {list(self.output_resources.keys())}"


# ----------------------------------------------------------------------
# Example facility templates
# ----------------------------------------------------------------------

FACILITY_TEMPLATES: Dict[str, FacilityProfile] = {
    "soup_kitchen": FacilityProfile(
        name="Soup Kitchen",
        industry="service",
        input_resources={"food_stock": 5.0, "water_stock": 2.0},
        output_resources={"meals_served": 10.0},
        morale_weight=1.2,
        corruption_sensitivity=0.8,
        event_hooks=["ration_riot", "supply_shortage"]
    ),
    "recycler_plant": FacilityProfile(
        name="Recycler Plant",
        industry="manufacturing",
        input_resources={"scrap_metal": 3.0},
        output_resources={"refined_metal": 2.0},
        morale_weight=0.9,
        corruption_sensitivity=1.1,
        event_hooks=["machine_breakdown", "union_strike"]
    ),
    "security_office": FacilityProfile(
        name="Security Office",
        industry="governance",
        input_resources={"credits": 2.0},
        output_resources={"patrol_hours": 8.0},
        morale_weight=1.0,
        corruption_sensitivity=1.0,
        event_hooks=["bribery_probe", "guard_dispute"]
    ),
    "blackmarket_den": FacilityProfile(
        name="Black Market Den",
        industry="informal",
        input_resources={"contraband": 1.0},
        output_resources={"credits": 4.0, "corruption": 0.5},
        morale_weight=1.3,
        corruption_sensitivity=0.5,
        event_hooks=["sting_operation", "betrayal"]
    ),
}
