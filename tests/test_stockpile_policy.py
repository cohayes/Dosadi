from copy import deepcopy

import pytest

from dosadi.runtime.materials_economy import MaterialsEconomyConfig
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.stockpile_policy import StockpilePolicyConfig, run_stockpile_policy_for_day
from dosadi.state import WorldState
from dosadi.world.extraction import ExtractionSite, SiteKind, ensure_extraction
from dosadi.world.facilities import Facility, FacilityKind, ensure_facility_ledger
from dosadi.world.logistics import DeliveryStatus, ensure_logistics, process_logistics_until
from dosadi.world.materials import Material, ensure_inventory_registry
from dosadi.world.survey_map import SurveyEdge, SurveyNode


def _add_depot(world: WorldState, depot_id: str, node_id: str, ward: str) -> None:
    facilities = ensure_facility_ledger(world)
    facilities.add(
        Facility(
            facility_id=depot_id,
            kind=FacilityKind.DEPOT,
            site_node_id=node_id,
        )
    )
    world.survey_map.upsert_node(SurveyNode(node_id=node_id, kind="facility", ward_id=ward))


def _add_site_source(world: WorldState, site_id: str, node_id: str, ward: str, material: Material, qty: int) -> None:
    extraction = ensure_extraction(world)
    extraction.add(ExtractionSite(site_id=site_id, kind=SiteKind.SCRAP_FIELD, node_id=node_id, created_day=0))
    world.survey_map.upsert_node(SurveyNode(node_id=node_id, kind="site", ward_id=ward))
    registry = ensure_inventory_registry(world)
    registry.inv(f"site:{site_id}").add(material, qty)

    world.survey_map.upsert_edge(SurveyEdge(a=node_id, b="node:depot-1", distance_m=1.0, travel_cost=1.0))


def _connect_nodes(world: WorldState, a: str, b: str) -> None:
    world.survey_map.upsert_edge(SurveyEdge(a=a, b=b, distance_m=1.0, travel_cost=1.0))


def _basic_world() -> WorldState:
    world = WorldState(seed=7)
    world.mat_cfg = MaterialsEconomyConfig(enabled=True)
    ensure_logistics(world)
    _add_depot(world, "depot-1", "node:depot-1", "ward:1")
    _add_site_source(world, "site-a", "node:site-a", "ward:1", Material.SCRAP_METAL, 500)
    _connect_nodes(world, "node:site-a", "node:depot-1")
    return world


def _first_delivery(world: WorldState):
    logistics = ensure_logistics(world)
    assert logistics.deliveries
    delivery_id = sorted(logistics.deliveries)[0]
    return logistics.deliveries[delivery_id]


def test_policy_disabled_no_deliveries() -> None:
    world = _basic_world()
    world.stock_cfg = StockpilePolicyConfig(enabled=False)

    run_stockpile_policy_for_day(world, day=0)

    assert not world.logistics.deliveries


def test_deterministic_requests() -> None:
    world_a = _basic_world()
    world_a.stock_cfg = StockpilePolicyConfig(enabled=True)
    world_b = deepcopy(world_a)

    run_stockpile_policy_for_day(world_a, day=0)
    run_stockpile_policy_for_day(world_b, day=0)

    assert world_a.logistics.signature() == world_b.logistics.signature()
    assert world_a.stock_policies.signature() == world_b.stock_policies.signature()


def test_pending_blocks_duplicates() -> None:
    world = _basic_world()
    world.stock_cfg = StockpilePolicyConfig(enabled=True)

    run_stockpile_policy_for_day(world, day=0)
    run_stockpile_policy_for_day(world, day=0)

    assert len(world.logistics.deliveries) == 1
    assert world.stock_state.deliveries_requested_today == 1


def test_global_cap_enforced() -> None:
    world = _basic_world()
    world.stock_cfg = StockpilePolicyConfig(enabled=True, max_deliveries_per_day=1)
    _add_depot(world, "depot-2", "node:depot-2", "ward:2")
    _connect_nodes(world, "node:depot-2", "node:site-a")

    run_stockpile_policy_for_day(world, day=0)

    assert world.stock_state.deliveries_requested_today == 1
    assert len(world.logistics.deliveries) == 1


def test_source_prefers_same_ward() -> None:
    world = _basic_world()
    world.stock_cfg = StockpilePolicyConfig(enabled=True)
    _add_site_source(world, "site-b", "node:site-b", "ward:2", Material.SCRAP_METAL, 500)
    _connect_nodes(world, "node:site-b", "node:depot-1")

    run_stockpile_policy_for_day(world, day=0)
    delivery = _first_delivery(world)

    assert delivery.origin_owner_id == "site:site-a"


def test_delivery_completion_transfers_materials() -> None:
    world = _basic_world()
    world.stock_cfg = StockpilePolicyConfig(enabled=True)

    run_stockpile_policy_for_day(world, day=0)
    delivery = _first_delivery(world)
    process_logistics_until(world, target_tick=10, current_tick=0)

    registry = ensure_inventory_registry(world)
    source_inv = registry.inv(delivery.origin_owner_id or "")
    dest_inv = registry.inv(delivery.dest_owner_id or "")

    assert delivery.status is DeliveryStatus.DELIVERED
    assert dest_inv.get(Material.SCRAP_METAL) >= 150
    assert source_inv.get(Material.SCRAP_METAL) <= 350
    profile = world.stock_policies.profile("depot-1")
    assert "SCRAP_METAL" not in profile.notes.get("pending_inbound", {})


def test_snapshot_roundtrip_mid_pending() -> None:
    world = _basic_world()
    world.stock_cfg = StockpilePolicyConfig(enabled=True)

    run_stockpile_policy_for_day(world, day=0)
    snapshot = snapshot_world(world, scenario_id="stockpile-test")
    restored = restore_world(snapshot)

    process_logistics_until(world, target_tick=10, current_tick=0)
    process_logistics_until(restored, target_tick=10, current_tick=0)

    assert sorted(world.logistics.deliveries) == sorted(restored.logistics.deliveries)
    assert world.inventories.signature() == restored.inventories.signature()
    delivery = _first_delivery(restored)
    assert delivery.status is DeliveryStatus.DELIVERED
