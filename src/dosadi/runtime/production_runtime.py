from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.world.construction import ConstructionProject
from dosadi.world.facilities import FacilityKind, ensure_facility_ledger
from dosadi.world.materials import Material, InventoryRegistry, ensure_inventory_registry, material_from_key
from dosadi.world.recipes import Recipe, RecipeRegistry, ensure_recipe_registry


@dataclass(slots=True)
class ProductionConfig:
    enabled: bool = False
    max_jobs_per_day_global: int = 200
    max_jobs_per_facility_per_day: int = 3
    prefer_recipes: list[str] = field(default_factory=lambda: ["FASTENERS", "SEALANT", "FILTER_MEDIA"])
    deterministic_salt: str = "prod-v2"


@dataclass(slots=True)
class ProductionState:
    last_run_day: int = -1
    jobs_started_today: int = 0
    jobs_started_by_facility: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class FacilityProductionState:
    facility_id: str
    active_job: str | None = None
    job_started_day: int = -1
    job_complete_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


def _production_metrics(world) -> Dict[str, object]:
    telemetry = ensure_metrics(world)
    prod_metrics = telemetry.gauges.get("production")
    if not isinstance(prod_metrics, dict):
        prod_metrics = {}
        telemetry.gauges["production"] = prod_metrics
    return prod_metrics  # type: ignore[return-value]


def _material_need_scores(world, prefer: list[str]) -> dict[Material, float]:
    scores: dict[Material, float] = {}
    registry = ensure_inventory_registry(world)
    ledger = getattr(world, "stock_policies", None)
    profiles = getattr(ledger, "profiles", {}) if ledger is not None else {}
    for depot_id, profile in sorted(profiles.items()):
        thresholds = getattr(profile, "thresholds", {})
        inv = registry.inv(f"facility:{depot_id}")
        for mat_key, threshold in sorted(thresholds.items()):
            material = material_from_key(mat_key)
            if material is None:
                continue
            deficit = max(0, getattr(threshold, "target_level", 0) - inv.get(material))
            if deficit > 0:
                scores[material] = scores.get(material, 0.0) + float(deficit)

    projects = getattr(world, "projects", None)
    if projects is not None:
        for project_id, project in sorted(getattr(projects, "projects", {}).items()):
            if not isinstance(project, ConstructionProject):
                continue
            bom = getattr(project, "bom", None) or getattr(getattr(project, "cost", None), "materials", {})
            normalized = {material_from_key(k): v for k, v in (bom or {}).items()}
            inv = registry.inv(getattr(project, "staging_owner_id", f"project:{project_id}"))
            for mat, qty in normalized.items():
                if not isinstance(mat, Material):
                    continue
                missing = max(0, int(qty) - inv.get(mat))
                if missing > 0:
                    scores[mat] = scores.get(mat, 0.0) + float(missing)

    preference = {name: float(len(prefer) - idx) for idx, name in enumerate(prefer)}
    for mat_name, weight in preference.items():
        material = material_from_key(mat_name)
        if material is None:
            continue
        scores[material] = max(scores.get(material, 0.0), weight)
    return scores


def choose_recipe_for_facility(
    world, facility_id: str, facility_kind: FacilityKind | str, day: int, *, cfg: ProductionConfig | None = None
) -> Recipe | None:
    cfg = cfg or ProductionConfig()
    registry: RecipeRegistry = ensure_recipe_registry(world)
    recipes = registry.get(facility_kind)
    if not recipes:
        return None

    needs = _material_need_scores(world, cfg.prefer_recipes)
    best: Recipe | None = None
    best_score = -1.0
    for recipe in recipes:
        if not getattr(recipe, "enabled", True):
            continue
        score = 0.0
        for material, qty in getattr(recipe, "outputs", {}).items():
            need_score = needs.get(material, 0.0)
            score += need_score * float(qty)
        if score > best_score or (score == best_score and best is not None and recipe.recipe_id < best.recipe_id):
            best = recipe
            best_score = score

    if best_score > 0:
        return best

    fallback = next((r for r in recipes if "base" in getattr(r, "tags", set())), None)
    if fallback is not None:
        return fallback
    return recipes[0]


def _owner_id_for_facility(facility_id: str) -> str:
    return f"facility:{facility_id}"


def _emit_event(world: Any, payload: Mapping[str, object]) -> None:
    record_event(world, payload)
    events = getattr(world, "runtime_events", None)
    if not isinstance(events, list):
        events = []
    event = dict(payload)
    event.setdefault("day", getattr(world, "day", 0))
    events.append(event)
    world.runtime_events = events


def _recipe_by_id(registry: RecipeRegistry) -> dict[str, Recipe]:
    lookup: dict[str, Recipe] = {}
    for recipes in registry.recipes_by_facility.values():
        for recipe in recipes:
            lookup[recipe.recipe_id] = recipe
    return lookup


def _complete_job(
    *,
    world,
    facility_state: FacilityProductionState,
    recipe_lookup: Mapping[str, Recipe],
    inventory: InventoryRegistry,
    metrics: Dict[str, object],
) -> None:
    recipe = recipe_lookup.get(facility_state.active_job or "")
    if recipe is None:
        facility_state.active_job = None
        facility_state.job_started_day = -1
        facility_state.job_complete_day = -1
        return

    inv = inventory.inv(_owner_id_for_facility(facility_state.facility_id))
    for material, qty in getattr(recipe, "outputs", {}).items():
        inv.add(material, int(qty))
        material_gauges = metrics.setdefault("outputs", {})
        if isinstance(material_gauges, dict):
            material_gauges[material.name] = material_gauges.get(material.name, 0.0) + float(qty)
    metrics["jobs_done"] = metrics.get("jobs_done", 0.0) + 1.0
    _emit_event(
        world,
        {
            "type": "PROD_JOB_DONE",
            "facility_id": facility_state.facility_id,
            "recipe_id": recipe.recipe_id,
            "outputs": {mat.name: qty for mat, qty in getattr(recipe, "outputs", {}).items()},
        },
    )
    facility_state.active_job = None
    facility_state.job_started_day = -1
    facility_state.job_complete_day = -1


def run_production_for_day(world, *, day: int) -> None:
    cfg_obj = getattr(world, "prod_cfg", None)
    cfg: ProductionConfig = cfg_obj if isinstance(cfg_obj, ProductionConfig) else ProductionConfig()
    state_obj = getattr(world, "prod_state", None)
    state: ProductionState = state_obj if isinstance(state_obj, ProductionState) else ProductionState()
    fac_prod_obj = getattr(world, "fac_prod", None)
    fac_prod: dict[str, FacilityProductionState] = (
        fac_prod_obj if isinstance(fac_prod_obj, dict) else {}
    )

    world.prod_cfg = cfg
    world.prod_state = state
    world.fac_prod = fac_prod

    if not getattr(cfg, "enabled", False):
        return
    if state.last_run_day != day:
        state.last_run_day = day
        state.jobs_started_today = 0
        state.jobs_started_by_facility = {}

    facilities = ensure_facility_ledger(world)
    registry = ensure_recipe_registry(world)
    recipe_lookup = _recipe_by_id(registry)
    inventory = ensure_inventory_registry(world)
    metrics = _production_metrics(world)

    producer_kinds = {FacilityKind.RECYCLER, FacilityKind.CHEM_WORKS, FacilityKind.WORKSHOP}
    for facility_id in sorted(facilities.keys()):
        facility = facilities[facility_id]
        if facility.kind not in producer_kinds:
            continue
        prod_state = fac_prod.setdefault(facility_id, FacilityProductionState(facility_id=facility_id))

        if prod_state.active_job and day >= prod_state.job_complete_day:
            _complete_job(
                world=world,
                facility_state=prod_state,
                recipe_lookup=recipe_lookup,
                inventory=inventory,
                metrics=metrics,
            )

        if state.jobs_started_today >= max(0, int(cfg.max_jobs_per_day_global)):
            continue
        started_here = state.jobs_started_by_facility.get(facility_id, 0)
        if started_here >= max(0, int(cfg.max_jobs_per_facility_per_day)):
            continue
        if prod_state.active_job is not None:
            continue

        recipe = choose_recipe_for_facility(world, facility_id, facility.kind, day, cfg=cfg)
        if recipe is None:
            continue
        inv = inventory.inv(_owner_id_for_facility(facility_id))
        if getattr(recipe, "inputs", {}) and not inv.can_afford(recipe.inputs):
            prod_state.notes["blocked_inputs"] = {
                mat.name: qty for mat, qty in sorted(recipe.inputs.items(), key=lambda itm: itm[0].name)
            }
            metrics["blocked_inputs"] = metrics.get("blocked_inputs", 0.0) + 1.0
            _emit_event(
                world,
                {
                    "type": "PROD_JOB_BLOCKED_INPUTS",
                    "facility_id": facility_id,
                    "recipe_id": recipe.recipe_id,
                },
            )
            continue

        inv.apply_bom(recipe.inputs)
        prod_state.active_job = recipe.recipe_id
        prod_state.job_started_day = day
        prod_state.job_complete_day = day + max(1, int(getattr(recipe, "duration_days", 1)))
        prod_state.notes.pop("blocked_inputs", None)
        state.jobs_started_today += 1
        state.jobs_started_by_facility[facility_id] = started_here + 1
        metrics["jobs_started"] = metrics.get("jobs_started", 0.0) + 1.0
        _emit_event(
            world,
            {
                "type": "PROD_JOB_STARTED",
                "facility_id": facility_id,
                "recipe_id": recipe.recipe_id,
                "complete_day": prod_state.job_complete_day,
            },
        )

