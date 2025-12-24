from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping

from dosadi.world.construction import ConstructionProject, ProjectStatus
from dosadi.world.facilities import FacilityLedger, ensure_facility_ledger
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, ensure_logistics
from dosadi.world.materials import (
    InventoryRegistry,
    Material,
    ensure_inventory_registry,
    normalize_bom,
)
from dosadi.world.workforce import AssignmentKind, ensure_workforce


@dataclass(slots=True)
class MaterialsEconomyConfig:
    enabled: bool = False
    daily_production_cap: int = 5000
    facility_production_enabled: bool = True
    project_consumption_enabled: bool = True
    auto_delivery_requests_enabled: bool = True
    default_depot_owner_id: str = "ward:0"
    deterministic_seed_salt: str = "mat-econ-v1"


@dataclass(slots=True)
class MaterialsEconomyState:
    last_run_day: int = -1


PRODUCTION_RECIPES: Mapping[str, Mapping[Material, int]] = {
    "facility_kind:workshop": {Material.FASTENERS: 8, Material.SEALANT: 3},
    "facility_kind:recycler": {Material.SCRAP_METAL: 12, Material.PLASTICS: 6},
}


def _materials_metrics(world) -> Dict[str, float]:
    metrics = getattr(world, "metrics", None)
    if metrics is None:
        metrics = {}
        world.metrics = metrics

    materials_metrics = metrics.get("materials")
    if not isinstance(materials_metrics, dict):
        materials_metrics = {}
        metrics["materials"] = materials_metrics
    return materials_metrics  # type: ignore[return-value]


def _facility_staff_count(world, facility_id: str) -> int:
    ledger = ensure_workforce(world)
    return sum(
        1
        for assignment in ledger.assignments.values()
        if assignment.kind is AssignmentKind.FACILITY_STAFF and assignment.target_id == facility_id
    )


def _apply_production(
    inventory: InventoryRegistry,
    owner_id: str,
    outputs: Mapping[Material, int],
    *,
    remaining_cap: int,
) -> int:
    produced = 0
    inv = inventory.inv(owner_id)
    for material, qty in outputs.items():
        if produced >= remaining_cap:
            break
        allowed = min(remaining_cap - produced, max(0, int(qty)))
        if allowed <= 0:
            continue
        inv.add(material, allowed)
        produced += allowed
    return produced


def run_materials_production_for_day(world, *, day: int) -> None:
    cfg_obj = getattr(world, "mat_cfg", None)
    cfg: MaterialsEconomyConfig = cfg_obj if isinstance(cfg_obj, MaterialsEconomyConfig) else MaterialsEconomyConfig()
    state_obj = getattr(world, "mat_state", None)
    state: MaterialsEconomyState = (
        state_obj if isinstance(state_obj, MaterialsEconomyState) else MaterialsEconomyState()
    )
    world.mat_cfg = cfg
    world.mat_state = state

    if not getattr(cfg, "enabled", False):
        return
    if not getattr(cfg, "facility_production_enabled", True):
        return
    if state.last_run_day == day:
        return

    registry = ensure_inventory_registry(world)
    facilities: FacilityLedger = ensure_facility_ledger(world)
    produced_units = 0
    metrics = _materials_metrics(world)

    for facility_id in sorted(facilities.keys()):
        facility = facilities[facility_id]
        recipe_key = f"facility_kind:{facility.kind}"
        outputs = PRODUCTION_RECIPES.get(recipe_key)
        if not outputs:
            continue

        staff = _facility_staff_count(world, facility_id)
        if staff <= 0:
            continue

        produced = _apply_production(
            registry,
            f"facility:{facility_id}",
            outputs,
            remaining_cap=max(0, int(cfg.daily_production_cap) - produced_units),
        )
        produced_units += produced
        if produced_units >= cfg.daily_production_cap:
            break

    metrics["produced_units"] = metrics.get("produced_units", 0.0) + float(produced_units)
    state.last_run_day = day


def _project_bom(project: ConstructionProject) -> Dict[Material, int]:
    if getattr(project, "bom", None):
        return normalize_bom(project.bom)
    return normalize_bom(getattr(project.cost, "materials", {}))


def _project_inventory_id(project_id: str) -> str:
    return f"project:{project_id}"


def _delivery_id(project_id: str, stage_id: str = "stage") -> str:
    return f"delivery:{project_id}:{stage_id}"


def _ensure_delivery(world, *, project: ConstructionProject, bom: Mapping[Material, int]) -> None:
    logistics = ensure_logistics(world)
    cfg: MaterialsEconomyConfig = getattr(world, "mat_cfg", MaterialsEconomyConfig())
    delivery_id = _delivery_id(project.project_id)
    if delivery_id in logistics.deliveries:
        existing = logistics.deliveries[delivery_id]
        if existing.dest_owner_id is None:
            existing.dest_owner_id = _project_inventory_id(project.project_id)
        if existing.origin_owner_id is None:
            existing.origin_owner_id = getattr(cfg, "default_depot_owner_id", "ward:0")
        if delivery_id not in project.pending_material_delivery_ids:
            project.pending_material_delivery_ids.append(delivery_id)
        return

    items = {material.name: int(qty) for material, qty in bom.items() if qty > 0}
    if not items:
        return

    owner_id = getattr(cfg, "default_depot_owner_id", "ward:0")
    delivery = DeliveryRequest(
        delivery_id=delivery_id,
        project_id=project.project_id,
        origin_node_id=getattr(world, "central_depot_node_id", "loc:depot"),
        dest_node_id=project.site_node_id,
        items=items,
        status=DeliveryStatus.REQUESTED,
        created_tick=getattr(world, "tick", 0),
        origin_owner_id=owner_id,
        dest_owner_id=_project_inventory_id(project.project_id),
        notes={"priority": "construction"},
    )
    logistics.add(delivery)
    if delivery_id not in project.pending_material_delivery_ids:
        project.pending_material_delivery_ids.append(delivery_id)
    metrics = _materials_metrics(world)
    metrics["deliveries_requested"] = metrics.get("deliveries_requested", 0.0) + 1.0


def _stage_unblocked(project: ConstructionProject, bom: Mapping[Material, int]) -> None:
    project.blocked_for_materials = False
    project.bom_consumed = True
    if project.status == ProjectStatus.APPROVED:
        project.status = ProjectStatus.STAGED
    for material, qty in bom.items():
        project.materials_delivered[material.name] = (
            project.materials_delivered.get(material.name, 0.0) + float(qty)
        )


def evaluate_project_materials(world, *, day: int) -> None:
    cfg_obj = getattr(world, "mat_cfg", None)
    cfg: MaterialsEconomyConfig = cfg_obj if isinstance(cfg_obj, MaterialsEconomyConfig) else MaterialsEconomyConfig()
    state_obj = getattr(world, "mat_state", None)
    state: MaterialsEconomyState = (
        state_obj if isinstance(state_obj, MaterialsEconomyState) else MaterialsEconomyState()
    )
    world.mat_cfg = cfg
    world.mat_state = state

    if not getattr(cfg, "enabled", False):
        return
    if not getattr(cfg, "project_consumption_enabled", True):
        return

    registry = ensure_inventory_registry(world)
    ledger = getattr(world, "projects", None)
    if ledger is None:
        return

    metrics = _materials_metrics(world)

    for project_id, project in sorted(ledger.projects.items()):
        if project.status in {ProjectStatus.COMPLETE, ProjectStatus.CANCELED}:
            continue
        bom = _project_bom(project)
        if not bom:
            continue
        project.bom = dict(bom)
        inv = registry.inv(_project_inventory_id(project_id))

        if inv.can_afford(bom):
            if not project.bom_consumed:
                inv.apply_bom(bom)
                _stage_unblocked(project, bom)
                metrics["consumed_units"] = metrics.get("consumed_units", 0.0) + float(
                    sum(bom.values())
                )
                metrics["projects_unblocked"] = metrics.get("projects_unblocked", 0.0) + 1.0
            continue

        project.blocked_for_materials = True
        metrics["projects_blocked"] = metrics.get("projects_blocked", 0.0) + 1.0
        if getattr(cfg, "auto_delivery_requests_enabled", True):
            _ensure_delivery(world, project=project, bom=bom)

