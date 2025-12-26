from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping

from dosadi.world.construction import (
    BlockReason,
    ConstructionPipelineConfig,
    ConstructionProject,
    ProjectStatus,
    StageState,
    ensure_construction_config,
    emit_project_event,
    _unlock_block,
    project_metrics,
)
from dosadi.world.facilities import (
    FacilityLedger,
    FacilityKind,
    coerce_facility_kind,
    ensure_facility_ledger,
    facility_unlocked,
)
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, ensure_logistics
from dosadi.world.materials import (
    Inventory,
    InventoryRegistry,
    Material,
    ensure_inventory_registry,
    normalize_bom,
)
from dosadi.world.recipes import FACILITY_RECIPES, Recipe
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.world.workforce import AssignmentKind, ensure_workforce
from dosadi.runtime.tech_ladder import has_unlock


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


def _materials_metrics(world) -> Dict[str, float]:
    telemetry = ensure_metrics(world)
    materials_metrics = telemetry.gauges.get("materials")
    if not isinstance(materials_metrics, dict):
        materials_metrics = {}
        telemetry.gauges["materials"] = materials_metrics
    return materials_metrics  # type: ignore[return-value]


def _facility_metrics(world) -> Dict[str, float]:
    telemetry = ensure_metrics(world)
    facility_metrics = telemetry.gauges.get("facilities")
    if not isinstance(facility_metrics, dict):
        facility_metrics = {}
        telemetry.gauges["facilities"] = facility_metrics
    facility_metrics.setdefault("count_by_type", {})
    facility_metrics.setdefault("outputs_by_material", {})
    facility_metrics.setdefault("inputs_missing", {})
    return facility_metrics  # type: ignore[return-value]


def _facility_staff_count(world, facility_id: str) -> int:
    ledger = ensure_workforce(world)
    return sum(
        1
        for assignment in ledger.assignments.values()
        if assignment.kind is AssignmentKind.FACILITY_STAFF and assignment.target_id == facility_id
    )


def _emit_facility_event(world, event: Mapping[str, object]) -> None:
    events = getattr(world, "runtime_events", None)
    if not isinstance(events, list):
        events = []
    payload = dict(event)
    payload.setdefault("day", getattr(world, "day", 0))
    events.append(payload)
    world.runtime_events = events


def _apply_production(
    inventory: InventoryRegistry,
    owner_id: str,
    outputs: Mapping[Material, int],
    *,
    remaining_cap: int,
) -> tuple[int, dict[Material, int]]:
    produced = 0
    produced_by_material: dict[Material, int] = {}
    inv = inventory.inv(owner_id)
    for material, qty in outputs.items():
        if produced >= remaining_cap:
            break
        allowed = min(remaining_cap - produced, max(0, int(qty)))
        if allowed <= 0:
            continue
        inv.add(material, allowed)
        produced += allowed
        produced_by_material[material] = produced_by_material.get(material, 0) + allowed
    return produced, produced_by_material


def _owner_id_for_facility(facility_id: str) -> str:
    return f"facility:{facility_id}"


def bom_missing(inv: Inventory, bom: dict[Material, int]) -> dict[Material, int]:
    missing: dict[Material, int] = {}
    for material, qty in bom.items():
        need = max(0, int(qty) - inv.get(material))
        if need > 0:
            missing[material] = need
    return missing


def _run_recipe(
    *,
    world,
    facility_id: str,
    recipe: Recipe,
    inventory: InventoryRegistry,
    remaining_cap: int,
    metrics: Dict[str, float],
) -> tuple[int, dict[Material, int], dict[Material, int]]:
    inv = inventory.inv(_owner_id_for_facility(facility_id))
    if recipe.inputs and not inv.can_afford(recipe.inputs):
        metrics["recipes_skipped_inputs"] = metrics.get("recipes_skipped_inputs", 0.0) + 1.0
        missing_inputs = bom_missing(inv, dict(recipe.inputs))
        _emit_facility_event(
            world,
            {
                "type": "FACILITY_RECIPE_SKIPPED",
                "facility_id": facility_id,
                "recipe_id": recipe.id,
                "reason": "inputs",
                "missing": {mat.name: qty for mat, qty in missing_inputs.items()},
            },
        )
        return 0, {}, missing_inputs

    inv.apply_bom(recipe.inputs)
    produced, produced_by_material = _apply_production(
        inventory,
        _owner_id_for_facility(facility_id),
        recipe.outputs,
        remaining_cap=remaining_cap,
    )
    metrics["recipes_ran"] = metrics.get("recipes_ran", 0.0) + 1.0
    _emit_facility_event(
        world,
        {
            "type": "FACILITY_RECIPE_RAN",
            "facility_id": facility_id,
            "recipe_id": recipe.id,
            "produced": {mat.name: qty for mat, qty in recipe.outputs.items()},
            "applied_cap": remaining_cap,
        },
    )
    return produced, produced_by_material, {}


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
    facility_metrics = _facility_metrics(world)

    for facility_id in sorted(facilities.keys()):
        facility = facilities[facility_id]
        facility.kind = coerce_facility_kind(getattr(facility, "kind", FacilityKind.DEPOT))
        facility_metrics["count_by_type"].setdefault(facility.kind.value, 0)
        facility_metrics["count_by_type"][facility.kind.value] += 1
        if facility.last_run_day == day:
            continue

        recipes = FACILITY_RECIPES.get(facility.kind, [])
        if not recipes:
            continue

        if not facility_unlocked(world, facility):
            facility_metrics["locked"] = facility_metrics.get("locked", 0.0) + 1.0
            _emit_facility_event(
                world,
                {
                    "type": "FACILITY_RECIPE_SKIPPED",
                    "facility_id": facility_id,
                    "reason": "unlock",
                },
            )
            facility.last_run_day = day
            continue

        if not facility.is_operational or facility.down_until_day >= day:
            facility_metrics["downtime_days"] = facility_metrics.get("downtime_days", 0.0) + 1.0
            _emit_facility_event(
                world,
                {
                    "type": "FACILITY_RECIPE_SKIPPED",
                    "facility_id": facility_id,
                    "reason": "downtime",
                },
            )
            facility.last_run_day = day
            continue

        staff = _facility_staff_count(world, facility_id)
        min_staff = max(0, max(facility.min_staff, *(recipe.min_staff for recipe in recipes or [0])))
        if staff < min_staff:
            facility_metrics["recipes_skipped_staff"] = facility_metrics.get("recipes_skipped_staff", 0.0) + 1.0
            _emit_facility_event(
                world,
                {
                    "type": "FACILITY_RECIPE_SKIPPED",
                    "facility_id": facility_id,
                    "reason": "staff",
                },
            )
            facility.last_run_day = day
            continue

        eligible_recipes = [
            r
            for r in recipes
            if not any(not has_unlock(world, tag) for tag in getattr(r, "requires_unlocks", frozenset()))
        ]
        for recipe in eligible_recipes:
            if not recipe.enabled:
                continue
            if staff < max(facility.min_staff, recipe.min_staff):
                facility_metrics["recipes_skipped_staff"] = facility_metrics.get("recipes_skipped_staff", 0.0) + 1.0
                _emit_facility_event(
                    world,
                    {
                        "type": "FACILITY_RECIPE_SKIPPED",
                        "facility_id": facility_id,
                        "recipe_id": recipe.id,
                        "reason": "staff",
                    },
                )
                continue

            remaining_cap = max(0, int(cfg.daily_production_cap) - produced_units)
            if remaining_cap <= 0:
                break

            produced, produced_by_material, missing_inputs = _run_recipe(
                world=world,
                facility_id=facility_id,
                recipe=recipe,
                inventory=registry,
                remaining_cap=remaining_cap,
                metrics=facility_metrics,
            )
            if missing_inputs:
                for mat, qty in missing_inputs.items():
                    facility_metrics["inputs_missing"][mat.name] = facility_metrics["inputs_missing"].get(mat.name, 0.0) + float(qty)
                _emit_facility_event(
                    world,
                    {
                        "type": "FACILITY_STALLED_INPUTS",
                        "facility_id": facility_id,
                        "recipe_id": recipe.id,
                        "missing": {mat.name: qty for mat, qty in missing_inputs.items()},
                    },
                )
                continue

            produced_units += produced
            if produced_by_material:
                for mat, qty in produced_by_material.items():
                    facility_metrics["outputs_by_material"][mat.name] = facility_metrics["outputs_by_material"].get(mat.name, 0.0) + float(qty)
                _emit_facility_event(
                    world,
                    {
                        "type": "FACILITY_PRODUCED",
                        "facility_id": facility_id,
                        "recipe_id": recipe.id,
                        "outputs": {mat.name: qty for mat, qty in produced_by_material.items()},
                    },
                )
            if produced_units >= cfg.daily_production_cap:
                break

        facility.last_run_day = day

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
    proj_metrics = project_metrics(world)
    proj_metrics["deliveries_requested"] = proj_metrics.get("deliveries_requested", 0.0) + 1.0


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

    telemetry = ensure_metrics(world)
    if not getattr(cfg, "enabled", False):
        return
    if not getattr(cfg, "project_consumption_enabled", True):
        return

    construction_cfg = ensure_construction_config(world)

    registry = ensure_inventory_registry(world)
    ledger = getattr(world, "projects", None)
    if ledger is None:
        return

    metrics = _materials_metrics(world)
    proj_metrics = project_metrics(world)
    blocked_count = 0
    for project_id, project in sorted(ledger.projects.items()):
        if project.status in {ProjectStatus.COMPLETE, ProjectStatus.CANCELED}:
            continue
        unlock_block = _unlock_block(world, project)
        if unlock_block:
            project.block_reason = unlock_block
            project.stage_state = StageState.WAITING_MATERIALS
            project.status = ProjectStatus.STAGED
            proj_metrics["blocked_unlocks"] = proj_metrics.get("blocked_unlocks", 0.0) + 1.0
            blocked_count += 1
            telemetry.topk_add(
                "projects.blocked",
                project.project_id,
                1.0,
                payload={
                    "node": project.site_node_id,
                    "stage": project.stage_state.value,
                    "reason": "UNLOCK",
                    "missing_unlocks": unlock_block.details.get("requires", []),
                    "pending_deliveries": len(project.pending_material_delivery_ids),
                },
            )
            emit_project_event(
                world,
                {
                    "type": "PROJECT_STAGE_BLOCKED",
                    "project_id": project.project_id,
                    "reason_code": "UNLOCK",
                    "details": unlock_block.details,
                },
            )
            continue
        bom = _project_bom(project)
        if not bom:
            continue

        project.bom = dict(bom)
        inv = registry.inv(project.staging_owner_id or _project_inventory_id(project_id))

        if not getattr(construction_cfg, "enabled", False):
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
            blocked_count += 1
            if getattr(cfg, "auto_delivery_requests_enabled", True):
                _ensure_delivery(world, project=project, bom=bom)
            continue

        if project.last_evaluated_day == day and getattr(construction_cfg, "evaluate_daily", True):
            continue

        project.last_evaluated_day = day
        project.block_reason = None

        missing = bom_missing(inv, bom)
        if missing:
            project.stage_state = StageState.WAITING_MATERIALS
            project.block_reason = BlockReason(
                code="MATERIALS",
                msg="Missing materials",
                details={
                    "missing": {mat.name: qty for mat, qty in sorted(missing.items(), key=lambda item: item[0].name)}
                },
            )
            project.status = ProjectStatus.STAGED
            proj_metrics["blocked_materials"] = proj_metrics.get("blocked_materials", 0.0) + 1.0
            blocked_count += 1
            telemetry.topk_add(
                "projects.blocked",
                project.project_id,
                float(sum(missing.values())),
                payload={
                    "node": project.site_node_id,
                    "stage": project.stage_state.value,
                    "reason": "MATERIALS",
                    "missing": {mat.name: qty for mat, qty in sorted(missing.items(), key=lambda item: item[0].name)},
                    "pending_deliveries": len(project.pending_material_delivery_ids),
                },
            )
            emit_project_event(
                world,
                {
                    "type": "PROJECT_STAGE_BLOCKED",
                    "project_id": project.project_id,
                    "reason_code": "MATERIALS",
                    "details": project.block_reason.details,
                },
            )
            if getattr(cfg, "auto_delivery_requests_enabled", True):
                _ensure_delivery(world, project=project, bom=missing)
            continue

        ledger_wf = ensure_workforce(world)
        assigned = [
            agent_id
            for agent_id, assignment in ledger_wf.assignments.items()
            if assignment.kind is AssignmentKind.PROJECT_WORK
            and assignment.target_id == project.project_id
        ]
        if not assigned and project.assigned_agents:
            assigned = list(project.assigned_agents)
        assigned = sorted(set(assigned))
        project.assigned_agents = assigned
        if not assigned:
            project.stage_state = StageState.WAITING_STAFF
            project.block_reason = BlockReason(
                code="STAFF",
                msg="No workers assigned",
                details={},
            )
            project.status = ProjectStatus.STAGED
            proj_metrics["blocked_staff"] = proj_metrics.get("blocked_staff", 0.0) + 1.0
            blocked_count += 1
            telemetry.topk_add(
                "projects.blocked",
                project.project_id,
                1.0,
                payload={
                    "node": project.site_node_id,
                    "stage": project.stage_state.value,
                    "reason": "STAFF",
                    "missing": {},
                    "pending_deliveries": len(project.pending_material_delivery_ids),
                },
            )
            emit_project_event(
                world,
                {
                    "type": "PROJECT_STAGE_BLOCKED",
                    "project_id": project.project_id,
                    "reason_code": "STAFF",
                    "details": project.block_reason.details,
                },
            )
            continue

        paused = getattr(project, "incident_paused", False) or bool(
            project.notes.get("incident_pause") if isinstance(project.notes, Mapping) else False
        )
        if paused:
            project.stage_state = StageState.PAUSED_INCIDENT
            project.block_reason = BlockReason(
                code="INCIDENT",
                msg="Project paused for incident",
                details={},
            )
            project.status = ProjectStatus.STAGED
            proj_metrics["blocked_incident"] = proj_metrics.get("blocked_incident", 0.0) + 1.0
            blocked_count += 1
            telemetry.topk_add(
                "projects.blocked",
                project.project_id,
                0.5,
                payload={
                    "node": project.site_node_id,
                    "stage": project.stage_state.value,
                    "reason": "INCIDENT",
                    "missing": {},
                    "pending_deliveries": len(project.pending_material_delivery_ids),
                },
            )
            emit_project_event(
                world,
                {
                    "type": "PROJECT_STAGE_BLOCKED",
                    "project_id": project.project_id,
                    "reason_code": "INCIDENT",
                    "details": project.block_reason.details,
                },
            )
            continue

        if not project.bom_consumed:
            inv.apply_bom(bom)
            _stage_unblocked(project, bom)
            project.stage_state = StageState.IN_PROGRESS
            project.block_reason = None
            project.progress_days_in_stage = 0
            proj_metrics["projects_unblocked"] = proj_metrics.get("projects_unblocked", 0.0) + 1.0
            emit_project_event(
                world,
                {
                    "type": "PROJECT_STAGE_STARTED",
                    "project_id": project.project_id,
                },
            )
        else:
            project.stage_state = StageState.IN_PROGRESS
            project.block_reason = None

        project.status = ProjectStatus.BUILDING
        project.progress_days_in_stage += 1
        emit_project_event(
            world,
            {
                "type": "PROJECT_STAGE_PROGRESS",
                "project_id": project.project_id,
                "progress_days": project.progress_days_in_stage,
            },
        )

    telemetry.set_gauge("projects.blocked_count", blocked_count)

