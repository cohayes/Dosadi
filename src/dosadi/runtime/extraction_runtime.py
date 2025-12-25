from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from dosadi.runtime.local_interactions import hashed_unit_float
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.world.extraction import ExtractionSite, SiteKind, ensure_extraction
from dosadi.world.facilities import FacilityKind, coerce_facility_kind, ensure_facility_ledger
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, ensure_logistics
from dosadi.world.materials import InventoryRegistry, Material, ensure_inventory_registry
from dosadi.world.phases import WorldPhase
from dosadi.world.survey_map import SurveyMap, edge_key


@dataclass(slots=True)
class ExtractionConfig:
    enabled: bool = False
    max_units_per_day_global: int = 10000
    max_units_per_site_per_day: int = 200
    yield_jitter: float = 0.15
    phase2_yield_mult: float = 0.90
    auto_pickup_requests: bool = True
    pickup_min_batch: int = 20
    deterministic_salt: str = "extract-v1"


@dataclass(slots=True)
class ExtractionState:
    last_run_day: int = -1


def _extraction_metrics(world) -> Dict[str, float]:
    telemetry = ensure_metrics(world)
    extraction_metrics = telemetry.gauges.get("extraction")
    if not isinstance(extraction_metrics, dict):
        extraction_metrics = {}
        telemetry.gauges["extraction"] = extraction_metrics
    return extraction_metrics  # type: ignore[return-value]


def _phase_multiplier(world, cfg: ExtractionConfig) -> float:
    phase_state = getattr(world, "phase_state", None)
    phase = getattr(phase_state, "phase", WorldPhase.PHASE0)
    if phase >= WorldPhase.PHASE2:
        return float(cfg.phase2_yield_mult)
    return 1.0


def _base_yields(site: ExtractionSite) -> Dict[Material, float]:
    richness = max(0.0, float(getattr(site, "richness", 0.0)))
    base: Dict[Material, float] = {}
    if site.kind is SiteKind.SCRAP_FIELD:
        base[Material.SCRAP_METAL] = 30.0 * richness
    elif site.kind is SiteKind.SALVAGE_CACHE:
        base[Material.FASTENERS] = 4.0 * richness
        base[Material.SEALANT] = 2.0 * richness
        base[Material.SCRAP_METAL] = 6.0 * richness
    elif site.kind is SiteKind.BRINE_POCKET:
        base[Material.SEALANT] = 1.0 * richness
    return base


def _jittered_yield(
    *,
    base: float,
    site_id: str,
    material: Material,
    day: int,
    cfg: ExtractionConfig,
    depletion: float,
    phase_mult: float,
) -> int:
    jitter = max(0.0, min(0.5, float(cfg.yield_jitter)))
    draw = hashed_unit_float("yield", cfg.deterministic_salt, site_id, str(day), material.name)
    mult = 1.0 - jitter + (2.0 * jitter * draw)
    qty = base * mult * max(0.0, 1.0 - depletion) * max(0.0, phase_mult)
    return int(round(max(0.0, qty)))


def _emit_event(world, event: Mapping[str, object]) -> None:
    events = getattr(world, "runtime_events", None)
    if not isinstance(events, list):
        events = []
    payload = dict(event)
    payload.setdefault("day", getattr(world, "day", 0))
    events.append(payload)
    world.runtime_events = events


def _choose_depot(world, *, node_id: str):
    facilities = ensure_facility_ledger(world)
    survey: SurveyMap = getattr(world, "survey_map", SurveyMap())
    depots = [fac for fac in facilities.values() if coerce_facility_kind(fac.kind) is FacilityKind.DEPOT]
    if not depots:
        return None

    best = None
    depot = None
    for facility in sorted(depots, key=lambda f: f.facility_id):
        cost = float("inf")
        if facility.site_node_id:
            key = edge_key(node_id, facility.site_node_id)
            edge = survey.edges.get(key)
            if edge is not None:
                cost = max(getattr(edge, "distance_m", 0.0), getattr(edge, "travel_cost", 0.0))
        candidate = (cost, facility.facility_id)
        if best is None or candidate < best:
            best = candidate
            depot = facility
    return depot if best else None


def _pickup_items(inventory: InventoryRegistry, owner_id: str, *, min_batch: int) -> Dict[str, int]:
    inv = inventory.inv(owner_id)
    total = sum(inv.items.values())
    if total < max(0, int(min_batch)):
        return {}
    return {material.name: int(qty) for material, qty in sorted(inv.items.items(), key=lambda item: item[0].name) if qty > 0}


def _clear_completed_pickups(world, ledger, metrics) -> None:
    logistics = ensure_logistics(world)
    for site in ledger.sites.values():
        pending_id = site.notes.get("pending_pickup_delivery_id") if isinstance(site.notes, dict) else None
        if not pending_id:
            continue
        delivery = logistics.deliveries.get(pending_id)
        if delivery is None or delivery.status in {DeliveryStatus.DELIVERED, DeliveryStatus.CANCELED, DeliveryStatus.FAILED}:
            if delivery and delivery.status is DeliveryStatus.DELIVERED:
                metrics["pickups_completed"] = metrics.get("pickups_completed", 0.0) + 1.0
            site.notes.pop("pending_pickup_delivery_id", None)


def _maybe_request_pickup(world, *, site: ExtractionSite, cfg: ExtractionConfig, day: int, metrics, registry: InventoryRegistry) -> None:
    if not getattr(cfg, "auto_pickup_requests", False):
        return

    pending = site.notes.get("pending_pickup_delivery_id") if isinstance(site.notes, dict) else None
    if pending:
        return

    items = _pickup_items(registry, f"site:{site.site_id}", min_batch=cfg.pickup_min_batch)
    if not items:
        return

    depot = _choose_depot(world, node_id=site.node_id)
    if depot is None:
        return

    logistics = ensure_logistics(world)
    delivery_id = f"delivery:pickup:{site.site_id}:{day}"
    if delivery_id in logistics.deliveries:
        site.notes["pending_pickup_delivery_id"] = delivery_id
        return

    mat_cfg = getattr(world, "mat_cfg", None)
    origin_owner = f"site:{site.site_id}"
    dest_owner = getattr(mat_cfg, "default_depot_owner_id", "ward:0")
    delivery = DeliveryRequest(
        delivery_id=delivery_id,
        project_id=f"pickup:{site.site_id}",
        origin_node_id=site.node_id,
        dest_node_id=depot.site_node_id,
        items=items,
        status=DeliveryStatus.REQUESTED,
        created_tick=getattr(world, "tick", 0),
        notes={"priority": "extraction"},
        origin_owner_id=origin_owner,
        dest_owner_id=dest_owner,
    )
    logistics.add(delivery)
    site.notes["pending_pickup_delivery_id"] = delivery_id
    metrics["pickups_requested"] = metrics.get("pickups_requested", 0.0) + 1.0


def run_extraction_for_day(world, *, day: int) -> None:
    cfg_obj = getattr(world, "extract_cfg", None)
    cfg: ExtractionConfig = cfg_obj if isinstance(cfg_obj, ExtractionConfig) else ExtractionConfig()
    state_obj = getattr(world, "extract_state", None)
    state: ExtractionState = state_obj if isinstance(state_obj, ExtractionState) else ExtractionState()
    world.extract_cfg = cfg
    world.extract_state = state

    telemetry = ensure_metrics(world)
    ledger = ensure_extraction(world)
    registry = ensure_inventory_registry(world)
    metrics = _extraction_metrics(world)
    metrics["sites"] = float(len(ledger.sites))
    telemetry.set_gauge("extraction.sites", metrics["sites"])

    if not getattr(cfg, "enabled", False):
        return
    if state.last_run_day == day:
        return

    _clear_completed_pickups(world, ledger, metrics)

    global_cap = max(0, int(cfg.max_units_per_day_global))
    per_site_cap = max(0, int(cfg.max_units_per_site_per_day))
    phase_mult = _phase_multiplier(world, cfg)
    produced_total = 0

    for site_id in sorted(ledger.sites):
        if produced_total >= global_cap:
            break
        site = ledger.sites[site_id]
        if getattr(site, "down_until_day", -1) >= day:
            _emit_event(
                world,
                {
                    "type": "EXTRACTION_SITE_DOWN",
                    "site_id": site.site_id,
                    "node_id": site.node_id,
                    "day": day,
                },
            )
            continue

        base_table = _base_yields(site)
        if not base_table:
            continue

        outputs: Dict[Material, int] = {}
        for material, base in base_table.items():
            if produced_total >= global_cap:
                break
            qty = _jittered_yield(
                base=base,
                site_id=site.site_id,
                material=material,
                day=day,
                cfg=cfg,
                depletion=getattr(site, "depletion", 0.0),
                phase_mult=phase_mult,
            )
            if per_site_cap > 0 and qty > per_site_cap:
                metrics["units_capped_site"] = metrics.get("units_capped_site", 0.0) + float(qty - per_site_cap)
                qty = per_site_cap
            remaining_global = max(0, global_cap - produced_total)
            if qty > remaining_global:
                metrics["units_capped_global"] = metrics.get("units_capped_global", 0.0) + float(qty - remaining_global)
                qty = remaining_global
            if qty <= 0:
                continue
            produced_total += qty
            outputs[material] = qty
            registry.inv(f"site:{site.site_id}").add(material, qty)

        if outputs:
            metrics["units_produced"] = metrics.get("units_produced", 0.0) + float(sum(outputs.values()))
            telemetry.topk_add(
                "extraction.top_sites",
                site.site_id,
                float(sum(outputs.values())),
                payload={
                    "node": site.node_id,
                    "kind": site.kind.value,
                    "pending_pickup": bool(site.notes.get("pending_pickup_delivery_id")) if isinstance(site.notes, dict) else False,
                },
            )
            _emit_event(
                world,
                {
                    "type": "EXTRACTION_YIELD",
                    "site_id": site.site_id,
                    "node_id": site.node_id,
                    "kind": site.kind.value,
                    "outputs": {mat.name: qty for mat, qty in sorted(outputs.items(), key=lambda item: item[0].name)},
                    "day": day,
                },
            )
            _maybe_request_pickup(world, site=site, cfg=cfg, day=day, metrics=metrics, registry=registry)

    state.last_run_day = day
    telemetry.set_gauge("extraction.units_today", metrics.get("units_produced", 0.0))


__all__ = ["ExtractionConfig", "ExtractionState", "run_extraction_for_day"]
