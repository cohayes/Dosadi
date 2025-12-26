from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Iterable, Mapping

from dosadi.world.facilities import FacilityKind
from dosadi.world.materials import Material, normalize_bom


@dataclass(frozen=True, slots=True)
class Recipe:
    recipe_id: str
    facility_kind: str
    inputs: Mapping[Material, int]
    outputs: Mapping[Material, int]
    duration_days: int = 1
    labor_days: int = 0
    waste: Mapping[Material, int] = field(default_factory=dict)
    tags: frozenset[str] = frozenset()
    requires_unlocks: frozenset[str] = frozenset()
    min_staff: int = 0
    enabled: bool = True
    notes: str = ""

    @property
    def id(self) -> str:  # Compatibility with v1 callers
        return self.recipe_id

    @property
    def kind(self) -> str:
        return self.facility_kind


class RecipeRegistry:
    def __init__(self, recipes: Iterable[Recipe] | None = None):
        self.recipes_by_facility: dict[str, list[Recipe]] = {}
        if recipes:
            for recipe in recipes:
                self.add(recipe)

    def add(self, recipe: Recipe) -> None:
        key = recipe.facility_kind
        bucket = self.recipes_by_facility.setdefault(key, [])
        bucket.append(recipe)
        bucket.sort(key=lambda r: r.recipe_id)

    def get(self, facility_kind: FacilityKind | str) -> list[Recipe]:
        key = facility_kind.value if isinstance(facility_kind, FacilityKind) else str(facility_kind)
        recipes = self.recipes_by_facility.get(key, [])
        return list(recipes)

    def signature(self) -> str:
        canonical = {
            kind: [r.recipe_id for r in recipes]
            for kind, recipes in sorted(self.recipes_by_facility.items(), key=lambda item: item[0])
        }
        digest = sha256(str(canonical).encode("utf-8")).hexdigest()
        return digest


def _recipe(
    *,
    recipe_id: str,
    facility_kind: FacilityKind,
    inputs: Mapping[object, object],
    outputs: Mapping[object, object],
    duration_days: int = 1,
    labor_days: int = 0,
    waste: Mapping[object, object] | None = None,
    tags: Iterable[str] | None = None,
    requires_unlocks: Iterable[str] | None = None,
    min_staff: int = 0,
    enabled: bool = True,
    notes: str = "",
) -> Recipe:
    return Recipe(
        recipe_id=recipe_id,
        facility_kind=facility_kind.value,
        inputs=normalize_bom(inputs),
        outputs=normalize_bom(outputs),
        duration_days=duration_days,
        labor_days=labor_days,
        waste=normalize_bom(waste or {}),
        tags=frozenset(tags or set()),
        requires_unlocks=frozenset(requires_unlocks or set()),
        min_staff=min_staff,
        enabled=enabled,
        notes=notes,
    )


DEFAULT_RECIPES: list[Recipe] = [
    _recipe(
        recipe_id="recycler_scrap_basic",
        facility_kind=FacilityKind.RECYCLER,
        inputs={Material.SCRAP_INPUT: 6},
        outputs={Material.SCRAP_METAL: 4, Material.PLASTICS: 2, Material.FIBER: 1},
        tags={"base", "refine"},
        notes="SCRAP_INPUT -> SCRAP_METAL/PLASTICS/FIBER",
        requires_unlocks={"UNLOCK_RECYCLER_RECIPES_T1"},
    ),
    _recipe(
        recipe_id="recycler_salvage_mix",
        facility_kind=FacilityKind.RECYCLER,
        inputs={Material.SALVAGE_MIX: 4},
        outputs={Material.SCRAP_METAL: 3, Material.PLASTICS: 1, Material.FIBER: 1},
        tags={"refine"},
        notes="SALVAGE_MIX -> mixed basics",
        requires_unlocks={"UNLOCK_RECYCLER_RECIPES_T1"},
    ),
    _recipe(
        recipe_id="chemworks_sealant_gaskets",
        facility_kind=FacilityKind.CHEM_WORKS,
        inputs={Material.CHEM_SALTS: 2, Material.FIBER: 1},
        outputs={Material.SEALANT: 2, Material.GASKETS: 1},
        tags={"parts"},
        notes="CHEM_SALTS/FIBER -> SEALANT/GASKETS",
        requires_unlocks={"UNLOCK_CHEM_SEALANTS_T2"},
    ),
    _recipe(
        recipe_id="workshop_fasteners",
        facility_kind=FacilityKind.WORKSHOP,
        inputs={Material.SCRAP_METAL: 5},
        outputs={Material.FASTENERS: 5},
        min_staff=1,
        tags={"parts"},
        notes="SCRAP_METAL -> FASTENERS",
        requires_unlocks={"UNLOCK_WORKSHOP_PARTS_T2"},
    ),
    _recipe(
        recipe_id="workshop_filter_media",
        facility_kind=FacilityKind.WORKSHOP,
        inputs={Material.FIBER: 4},
        outputs={Material.FILTER_MEDIA: 2},
        min_staff=1,
        tags={"parts"},
        notes="FIBER -> FILTER_MEDIA",
        requires_unlocks={"UNLOCK_WORKSHOP_PARTS_T2"},
    ),
    _recipe(
        recipe_id="workshop_circuit_simple",
        facility_kind=FacilityKind.WORKSHOP,
        inputs={Material.PLASTICS: 2, Material.SCRAP_METAL: 2},
        outputs={Material.CIRCUIT_SIMPLE: 2},
        tags={"parts"},
        notes="PLASTICS/SCRAP_METAL -> CIRCUIT_SIMPLE",
    ),
]


DEFAULT_RECIPE_REGISTRY = RecipeRegistry(DEFAULT_RECIPES)


def ensure_recipe_registry(world) -> RecipeRegistry:
    registry = getattr(world, "recipe_registry", None)
    if isinstance(registry, RecipeRegistry):
        return registry
    registry = RecipeRegistry(DEFAULT_RECIPES)
    world.recipe_registry = registry
    return registry


def _legacy_facility_recipes() -> dict[FacilityKind, list[Recipe]]:
    mapping: dict[FacilityKind, list[Recipe]] = {}
    for kind in FacilityKind:
        mapping[kind] = [recipe for recipe in DEFAULT_RECIPE_REGISTRY.get(kind)]
    return mapping


FACILITY_RECIPES = _legacy_facility_recipes()


__all__ = [
    "DEFAULT_RECIPES",
    "DEFAULT_RECIPE_REGISTRY",
    "FACILITY_RECIPES",
    "Recipe",
    "RecipeRegistry",
    "ensure_recipe_registry",
]
