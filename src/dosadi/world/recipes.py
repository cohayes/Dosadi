from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from dosadi.world.facilities import FacilityKind
from dosadi.world.materials import Material


@dataclass(frozen=True, slots=True)
class Recipe:
    id: str
    kind: str
    inputs: Mapping[Material, int]
    outputs: Mapping[Material, int]
    min_staff: int = 0
    enabled: bool = True
    notes: str = ""


FACILITY_RECIPES: Dict[FacilityKind, list[Recipe]] = {
    FacilityKind.WORKSHOP: [
        Recipe(
            id="workshop_fasteners",
            kind="daily",
            inputs={Material.SCRAP_METAL: 6},
            outputs={Material.FASTENERS: 6},
            min_staff=1,
            notes="SCRAP_METAL -> FASTENERS",
        ),
        Recipe(
            id="workshop_sealant",
            kind="daily",
            inputs={Material.PLASTICS: 4},
            outputs={Material.SEALANT: 2},
            min_staff=1,
            notes="PLASTICS -> SEALANT",
        ),
    ],
    FacilityKind.RECYCLER: [
        Recipe(
            id="recycler_bootstrap",
            kind="daily",
            inputs={},
            outputs={Material.SCRAP_METAL: 5, Material.PLASTICS: 2},
            min_staff=1,
            notes="Bootstrap recycling without explicit scrap input",
        )
    ],
    FacilityKind.DEPOT: [],
    FacilityKind.REFINERY: [],
    FacilityKind.WATER_WORKS: [],
}


__all__ = ["Recipe", "FACILITY_RECIPES"]
