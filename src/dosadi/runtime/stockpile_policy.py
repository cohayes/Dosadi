from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping

from dosadi.world.events import EventKind, WorldEvent, WorldEventLog
from dosadi.world.extraction import ExtractionLedger, ensure_extraction
from dosadi.world.facilities import Facility, FacilityKind, FacilityLedger, ensure_facility_ledger
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, ensure_logistics
from dosadi.world.materials import InventoryRegistry, Material, ensure_inventory_registry, material_from_key
from dosadi.world.routing import compute_route
from dosadi.world.survey_map import SurveyMap


@dataclass(slots=True)
class StockpilePolicyConfig:
    enabled: bool = False
    materials: list[str] = field(
        default_factory=lambda: ["SCRAP_METAL", "PLASTICS", "FASTENERS", "SEALANT", "FABRIC"]
    )
    max_deliveries_per_day: int = 30
    max_deliveries_per_depot_per_day: int = 5
    min_batch_units: int = 10
    max_batch_units: int = 200
    source_candidate_cap: int = 50
    depot_candidate_cap: int = 25
    prefer_same_ward: bool = True
    deterministic_salt: str = "stockpile-v1"


@dataclass(slots=True)
class StockpilePolicyState:
    last_run_day: int = -1
    deliveries_requested_today: int = 0
    deliveries_by_depot: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class MaterialThreshold:
    min_level: int
    target_level: int
    max_level: int


@dataclass(slots=True)
class DepotPolicyProfile:
    depot_facility_id: str
    thresholds: dict[str, MaterialThreshold]
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class DepotPolicyLedger:
    profiles: dict[str, DepotPolicyProfile] = field(default_factory=dict)

    def profile(self, depot_id: str) -> DepotPolicyProfile:
        if depot_id not in self.profiles:
            self.profiles[depot_id] = DepotPolicyProfile(
                depot_facility_id=depot_id,
                thresholds=default_thresholds(),
                notes={},
            )
        profile = self.profiles[depot_id]
        for mat_name, threshold in default_thresholds().items():
            if mat_name not in profile.thresholds:
                profile.thresholds[mat_name] = threshold
        return profile

    def signature(self) -> str:
        canonical: Mapping[str, object] = {
            depot_id: {
                "thresholds": {
                    mat: {
                        "min": th.min_level,
                        "target": th.target_level,
                        "max": th.max_level,
                    }
                    for mat, th in sorted(profile.thresholds.items())
                },
                "notes": {k: v for k, v in sorted(profile.notes.items())},
            }
            for depot_id, profile in sorted(self.profiles.items())
        }
        return str(canonical)


def default_thresholds() -> dict[str, MaterialThreshold]:
    return {
        "SCRAP_METAL": MaterialThreshold(min_level=50, target_level=150, max_level=400),
        "PLASTICS": MaterialThreshold(min_level=30, target_level=100, max_level=250),
        "FASTENERS": MaterialThreshold(min_level=20, target_level=60, max_level=150),
        "SEALANT": MaterialThreshold(min_level=10, target_level=40, max_level=120),
        "FABRIC": MaterialThreshold(min_level=10, target_level=30, max_level=80),
    }


def _stockpile_metrics(world) -> Dict[str, float]:
    metrics = getattr(world, "metrics", None)
    if metrics is None:
        metrics = {}
        world.metrics = metrics
    stock_metrics = metrics.get("stockpile")
    if not isinstance(stock_metrics, dict):
        stock_metrics = {}
        metrics["stockpile"] = stock_metrics
    return stock_metrics  # type: ignore[return-value]


def _ensure_event_log(world: Any) -> WorldEventLog:
    log: WorldEventLog | None = getattr(world, "event_log", None)
    if not isinstance(log, WorldEventLog):
        log = WorldEventLog(max_len=5000)
        world.event_log = log
    return log


def _reset_daily_sources(profile: DepotPolicyProfile, *, day: int) -> None:
    notes = profile.notes
    marker = notes.get("sources_day")
    if marker != day:
        notes["sources_day"] = day
        notes["sources_today"] = {}


def _sources_today(profile: DepotPolicyProfile, material: str, day: int) -> set[str]:
    _reset_daily_sources(profile, day=day)
    sources = profile.notes.get("sources_today")
    if not isinstance(sources, dict):
        sources = {}
        profile.notes["sources_today"] = sources
    current = sources.get(material)
    if not isinstance(current, set):
        current = set()
        sources[material] = current
    return current


def _pending_inbound(profile: DepotPolicyProfile) -> MutableMapping[str, str]:
    pending = profile.notes.get("pending_inbound")
    if not isinstance(pending, dict):
        pending = {}
        profile.notes["pending_inbound"] = pending
    return pending


def _owner_node(world: Any, owner_id: str, facilities: FacilityLedger, extraction: ExtractionLedger) -> str | None:
    if owner_id.startswith("facility:"):
        facility = facilities.get(owner_id.split(":", 1)[1])
        if isinstance(facility, Facility):
            return facility.site_node_id
    if owner_id.startswith("site:"):
        site = extraction.sites.get(owner_id.split(":", 1)[1])
        if site is not None:
            return site.node_id
    return None


def _ward_for_node(world: Any, node_id: str | None) -> str | None:
    if node_id is None:
        return None
    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    node = survey_map.nodes.get(node_id)
    return getattr(node, "ward_id", None)


def _route_cost(world: Any, source_node: str | None, dest_node: str | None) -> float:
    if not source_node or not dest_node:
        return float("inf")
    route = compute_route(world, from_node=source_node, to_node=dest_node, perspective_agent_id=None)
    if route is None:
        return float("inf")
    return float(route.total_cost)


def _candidate_sources(
    world: Any,
    *,
    depot: Facility,
    material: Material,
    cfg: StockpilePolicyConfig,
    registry: InventoryRegistry,
    facilities: FacilityLedger,
    extraction: ExtractionLedger,
) -> list[tuple[str, float, str | None]]:
    dest_node = depot.site_node_id
    dest_ward = _ward_for_node(world, dest_node)
    candidates: list[tuple[str, float, str | None]] = []

    for site_id in sorted(extraction.sites):
        site = extraction.sites[site_id]
        owner_id = f"site:{site_id}"
        available = registry.inv(owner_id).get(material)
        if available > 0:
            candidates.append((owner_id, float(available), site.node_id))

    for fac in sorted(facilities.facilities.values(), key=lambda f: f.facility_id):
        if fac.kind not in {FacilityKind.WORKSHOP, FacilityKind.RECYCLER}:
            continue
        owner_id = f"facility:{fac.facility_id}"
        available = registry.inv(owner_id).get(material)
        if available > 0:
            candidates.append((owner_id, float(available), fac.site_node_id))

    for fac in sorted(facilities.list_by_kind(FacilityKind.DEPOT), key=lambda f: f.facility_id):
        if fac.facility_id == depot.facility_id:
            continue
        owner_id = f"facility:{fac.facility_id}"
        available = registry.inv(owner_id).get(material)
        profile = getattr(world, "stock_policies", DepotPolicyLedger()).profile(fac.facility_id)
        target = profile.thresholds.get(material.name, MaterialThreshold(0, 0, 0)).target_level
        surplus = available - target
        if surplus > 0:
            candidates.append((owner_id, float(surplus), fac.site_node_id))

    fallback_owner = "ward:0"
    available = registry.inv(fallback_owner).get(material)
    if available > 0:
        candidates.append((fallback_owner, float(available), None))

    limited = candidates[: max(0, int(cfg.source_candidate_cap))]
    sorted_candidates = sorted(
        limited,
        key=lambda c: (
            0
            if cfg.prefer_same_ward and dest_ward is not None and _ward_for_node(world, c[2]) == dest_ward
            else 1,
            _route_cost(world, c[2], dest_node),
            c[0],
        ),
    )
    return sorted_candidates


def choose_source_for_material(
    world: Any, depot: Facility, material: Material, request_qty: int, day: int
) -> tuple[str, int] | None:
    cfg: StockpilePolicyConfig = getattr(world, "stock_cfg", StockpilePolicyConfig())
    registry = ensure_inventory_registry(world)
    facilities = ensure_facility_ledger(world)
    extraction = ensure_extraction(world)
    profile = getattr(world, "stock_policies", DepotPolicyLedger()).profile(depot.facility_id)
    sources_today = _sources_today(profile, material.name, day)

    for owner_id, available, _ in _candidate_sources(
        world,
        depot=depot,
        material=material,
        cfg=cfg,
        registry=registry,
        facilities=facilities,
        extraction=extraction,
    ):
        if owner_id in sources_today:
            continue
        amount = min(request_qty, int(available))
        if amount <= 0:
            continue
        sources_today.add(owner_id)
        return owner_id, amount
    return None


def _delivery_id(depot_id: str, material: Material, day: int, seq: int) -> str:
    return f"delivery:stockpile:{depot_id}:{material.name}:{day}:{seq}"


def _request_stockpile_delivery(
    world: Any,
    *,
    depot: Facility,
    material: Material,
    qty: int,
    source_owner_id: str,
    day: int,
    state: StockpilePolicyState,
) -> None:
    logistics = ensure_logistics(world)
    registry = ensure_inventory_registry(world)
    facilities = ensure_facility_ledger(world)
    extraction = ensure_extraction(world)

    delivery_id = _delivery_id(depot.facility_id, material, day, state.deliveries_requested_today + 1)
    if delivery_id in logistics.deliveries:
        return

    dest_owner_id = f"facility:{depot.facility_id}"
    dest_node_id = depot.site_node_id
    source_node = _owner_node(world, source_owner_id, facilities, extraction)
    delivery = DeliveryRequest(
        delivery_id=delivery_id,
        project_id=f"stockpile:{depot.facility_id}",
        origin_node_id=source_node or dest_node_id,
        dest_node_id=dest_node_id,
        items={material.name: qty},
        status=DeliveryStatus.REQUESTED,
        created_tick=getattr(world, "tick", 0),
        origin_owner_id=source_owner_id,
        dest_owner_id=dest_owner_id,
        notes={"kind": "stockpile_pull", "material": material.name, "policy_day": day, "depot_id": depot.facility_id},
    )
    logistics.add(delivery)
    registry.inv(source_owner_id)
    registry.inv(dest_owner_id)

    profile = getattr(world, "stock_policies", DepotPolicyLedger()).profile(depot.facility_id)
    pending = _pending_inbound(profile)
    pending[material.name] = delivery_id

    metrics = _stockpile_metrics(world)
    metrics["deliveries_requested"] = metrics.get("deliveries_requested", 0.0) + 1.0
    state.deliveries_requested_today += 1
    state.deliveries_by_depot[depot.facility_id] = state.deliveries_by_depot.get(depot.facility_id, 0) + 1

    log = _ensure_event_log(world)
    log.append(
        WorldEvent(
            event_id="",
            day=day,
            kind=EventKind.STOCKPILE_PULL_REQUESTED,
            subject_kind="depot",
            subject_id=depot.facility_id,
            payload={"material": material.name, "qty": qty, "source_owner": source_owner_id},
        )
    )


def _emit_shortage(world: Any, *, depot: Facility, material: Material, deficit: int, day: int) -> None:
    metrics = _stockpile_metrics(world)
    metrics["shortages"] = metrics.get("shortages", 0.0) + 1.0
    log = _ensure_event_log(world)
    log.append(
        WorldEvent(
            event_id="",
            day=day,
            kind=EventKind.STOCKPILE_SHORTAGE,
            subject_kind="depot",
            subject_id=depot.facility_id,
            payload={"material": material.name, "deficit": deficit},
        )
    )


def run_stockpile_policy_for_day(world, *, day: int) -> None:
    cfg_obj = getattr(world, "stock_cfg", None)
    cfg: StockpilePolicyConfig = cfg_obj if isinstance(cfg_obj, StockpilePolicyConfig) else StockpilePolicyConfig()
    state_obj = getattr(world, "stock_state", None)
    state: StockpilePolicyState = state_obj if isinstance(state_obj, StockpilePolicyState) else StockpilePolicyState()
    ledger_obj = getattr(world, "stock_policies", None)
    ledger: DepotPolicyLedger = ledger_obj if isinstance(ledger_obj, DepotPolicyLedger) else DepotPolicyLedger()

    world.stock_cfg = cfg
    world.stock_state = state
    world.stock_policies = ledger

    if not getattr(cfg, "enabled", False):
        return
    if state.last_run_day != day:
        state.last_run_day = day
        state.deliveries_requested_today = 0
        state.deliveries_by_depot = {}

    facilities = ensure_facility_ledger(world)
    registry = ensure_inventory_registry(world)
    metrics = _stockpile_metrics(world)
    metrics["depots_covered"] = float(len(facilities.list_by_kind(FacilityKind.DEPOT)))

    global_cap = max(0, int(cfg.max_deliveries_per_day))
    per_depot_cap = max(0, int(cfg.max_deliveries_per_depot_per_day))

    for depot in sorted(facilities.list_by_kind(FacilityKind.DEPOT), key=lambda f: f.facility_id)[: cfg.depot_candidate_cap]:
        if state.deliveries_requested_today >= global_cap:
            break
        profile = ledger.profile(depot.facility_id)
        depot_budget = per_depot_cap - state.deliveries_by_depot.get(depot.facility_id, 0)
        if depot_budget <= 0:
            continue
        inv = registry.inv(f"facility:{depot.facility_id}")
        for mat_key in cfg.materials:
            if state.deliveries_requested_today >= global_cap or depot_budget <= 0:
                break
            material = material_from_key(mat_key)
            if material is None:
                continue
            threshold = profile.thresholds.get(material.name)
            if threshold is None:
                continue
            qty = inv.get(material)
            if qty >= threshold.min_level:
                continue
            deficit = threshold.target_level - qty
            request_qty = max(cfg.min_batch_units, min(cfg.max_batch_units, deficit))
            if request_qty <= 0:
                continue
            pending = _pending_inbound(profile)
            if material.name in pending:
                continue
            source = choose_source_for_material(world, depot, material, request_qty, day)
            if source is None:
                _emit_shortage(world, depot=depot, material=material, deficit=deficit, day=day)
                continue
            source_owner_id, amount = source
            amount = max(cfg.min_batch_units, min(request_qty, amount))
            if amount <= 0:
                continue
            _request_stockpile_delivery(
                world,
                depot=depot,
                material=material,
                qty=amount,
                source_owner_id=source_owner_id,
                day=day,
                state=state,
            )
            depot_budget -= 1


def handle_stockpile_delivery_result(world: Any, delivery: DeliveryRequest, *, success: bool) -> None:
    if not isinstance(delivery.notes, Mapping):
        return
    if delivery.notes.get("kind") != "stockpile_pull":
        return
    depot_id = str(delivery.notes.get("depot_id", ""))
    material = str(delivery.notes.get("material", ""))
    if not depot_id or not material:
        return
    ledger_obj = getattr(world, "stock_policies", None)
    ledger: DepotPolicyLedger = ledger_obj if isinstance(ledger_obj, DepotPolicyLedger) else DepotPolicyLedger()
    profile = ledger.profile(depot_id)
    pending = _pending_inbound(profile)
    pending.pop(material, None)
    world.stock_policies = ledger

    metrics = _stockpile_metrics(world)
    if success:
        metrics["deliveries_completed"] = metrics.get("deliveries_completed", 0.0) + 1.0
    log = _ensure_event_log(world)
    payload = {"material": material, "qty": sum(delivery.items.values())}
    if success and getattr(delivery, "origin_owner_id", None):
        payload["source_owner"] = delivery.origin_owner_id
    log.append(
        WorldEvent(
            event_id="",
            day=getattr(world, "day", 0),
            kind=EventKind.STOCKPILE_PULL_COMPLETED if success else EventKind.STOCKPILE_SHORTAGE,
            subject_kind="depot",
            subject_id=depot_id,
            payload=payload,
        )
    )
