from __future__ import annotations

from dosadi.runtime.extraction_runtime import ExtractionConfig, run_extraction_for_day
from dosadi.runtime.materials_economy import MaterialsEconomyConfig
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.state import WorldState
from dosadi.world.extraction import ExtractionSite, SiteKind, create_sites_for_node, ensure_extraction
from dosadi.world.facilities import Facility, FacilityKind, ensure_facility_ledger
from dosadi.world.logistics import (
    DeliveryStatus,
    assign_pending_deliveries,
    ensure_logistics,
    process_due_deliveries,
)
from dosadi.world.materials import Material, ensure_inventory_registry
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode


def _base_world(seed: int = 1) -> WorldState:
    world = WorldState(seed=seed)
    world.mat_cfg = MaterialsEconomyConfig(enabled=True)
    ensure_inventory_registry(world)
    ensure_logistics(world)
    ensure_facility_ledger(world)
    return world


def _add_site(world: WorldState, *, node_id: str = "loc:site", richness: float = 1.0) -> ExtractionSite:
    ledger = ensure_extraction(world)
    site_id = f"site:{node_id}:{SiteKind.SCRAP_FIELD.value}"
    site = ExtractionSite(
        site_id=site_id,
        kind=SiteKind.SCRAP_FIELD,
        node_id=node_id,
        created_day=0,
        richness=richness,
    )
    ledger.add(site)
    return site


def _link_nodes(world: WorldState, a: str, b: str) -> None:
    survey: SurveyMap = getattr(world, "survey_map", SurveyMap())
    survey.upsert_node(SurveyNode(node_id=a, kind="site", ward_id="ward:0", confidence=1.0, last_seen_tick=0))
    survey.upsert_node(SurveyNode(node_id=b, kind="site", ward_id="ward:0", confidence=1.0, last_seen_tick=0))
    survey.upsert_edge(
        SurveyEdge(a=a, b=b, distance_m=1.0, travel_cost=1.0, hazard=0.0, confidence=1.0, last_seen_tick=0)
    )


def test_flag_off_produces_no_yield() -> None:
    world = _base_world()
    _add_site(world)
    world.extract_cfg = ExtractionConfig(enabled=False)
    registry = ensure_inventory_registry(world)
    before = registry.signature()

    run_extraction_for_day(world, day=0)

    assert registry.signature() == before


def test_deterministic_yields() -> None:
    cfg = ExtractionConfig(enabled=True, yield_jitter=0.1)
    world_a = _base_world(seed=2)
    world_b = _base_world(seed=2)
    _add_site(world_a)
    _add_site(world_b)
    world_a.extract_cfg = cfg
    world_b.extract_cfg = cfg

    run_extraction_for_day(world_a, day=1)
    run_extraction_for_day(world_b, day=1)

    sig_a = ensure_inventory_registry(world_a).signature()
    sig_b = ensure_inventory_registry(world_b).signature()
    assert sig_a == sig_b


def test_caps_enforced_deterministically() -> None:
    cfg = ExtractionConfig(
        enabled=True,
        max_units_per_site_per_day=5,
        max_units_per_day_global=5,
        yield_jitter=0.0,
    )
    world = _base_world(seed=3)
    site = _add_site(world, richness=1.0)
    world.extract_cfg = cfg

    run_extraction_for_day(world, day=0)

    inv = ensure_inventory_registry(world).inv(f"site:{site.site_id}")
    assert inv.get(Material.SCRAP_METAL) == 5
    metrics = getattr(world, "metrics", {}).get("extraction", {})
    assert metrics.get("units_capped_site", 0) > 0


def test_site_created_from_resource_tag() -> None:
    world = _base_world(seed=4)
    node = SurveyNode(
        node_id="loc:rich", kind="outpost_site", ward_id="ward:0", confidence=0.8, last_seen_tick=0, resource_tags=("scrap_field",)
    )
    created = create_sites_for_node(world, node, day=1)

    assert created == ["site:loc:rich:SCRAP_FIELD"]
    ledger = ensure_extraction(world)
    site = ledger.sites[created[0]]
    assert site.kind is SiteKind.SCRAP_FIELD
    assert site.richness == node.resource_richness


def test_pickup_request_created_once() -> None:
    cfg = ExtractionConfig(enabled=True, pickup_min_batch=1, yield_jitter=0.0, max_units_per_site_per_day=10)
    world = _base_world(seed=5)
    depot = Facility(facility_id="fac:depot", kind=FacilityKind.DEPOT, site_node_id="loc:depot")
    facilities = ensure_facility_ledger(world)
    facilities.add(depot)
    _link_nodes(world, "loc:site", "loc:depot")
    _add_site(world, richness=0.5)
    world.extract_cfg = cfg

    run_extraction_for_day(world, day=2)
    logistics = ensure_logistics(world)
    assert len(logistics.deliveries) == 1
    pending = next(iter(logistics.deliveries.values()))
    assert pending.status is DeliveryStatus.REQUESTED

    run_extraction_for_day(world, day=2)
    assert len(logistics.deliveries) == 1


def test_delivery_completion_transfers_materials() -> None:
    cfg = ExtractionConfig(enabled=True, pickup_min_batch=1, yield_jitter=0.0, max_units_per_site_per_day=8)
    world = _base_world(seed=6)
    depot = Facility(facility_id="fac:depot", kind=FacilityKind.DEPOT, site_node_id="loc:depot")
    ensure_facility_ledger(world).add(depot)
    _link_nodes(world, "loc:site", "loc:depot")
    site = _add_site(world, richness=0.4)
    world.extract_cfg = cfg

    run_extraction_for_day(world, day=3)
    assign_pending_deliveries(world, tick=0)
    process_due_deliveries(world, tick=10)

    registry = ensure_inventory_registry(world)
    site_inv = registry.inv(f"site:{site.site_id}")
    depot_inv = registry.inv(getattr(world.mat_cfg, "default_depot_owner_id", "ward:0"))
    assert site_inv.get(Material.SCRAP_METAL) == 0
    assert depot_inv.get(Material.SCRAP_METAL) > 0


def test_snapshot_roundtrip_preserves_extraction_flow() -> None:
    cfg = ExtractionConfig(enabled=True, pickup_min_batch=1, yield_jitter=0.0, max_units_per_site_per_day=6)
    world = _base_world(seed=7)
    depot = Facility(facility_id="fac:depot", kind=FacilityKind.DEPOT, site_node_id="loc:depot")
    ensure_facility_ledger(world).add(depot)
    _link_nodes(world, "loc:site", "loc:depot")
    _add_site(world, richness=0.7)
    world.extract_cfg = cfg

    run_extraction_for_day(world, day=0)
    snap = snapshot_world(world, scenario_id="extraction-test")
    restored = restore_world(snap)

    run_extraction_for_day(world, day=1)
    run_extraction_for_day(restored, day=1)

    assert world_signature(world) == world_signature(restored)
