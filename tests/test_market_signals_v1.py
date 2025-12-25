from dataclasses import replace

from dosadi.runtime.market_signals import (
    MarketSignalsConfig,
    MarketSignalsState,
    MaterialMarketSignal,
    current_signal_urgency,
    run_market_signals_for_day,
)
from dosadi.runtime.production_runtime import ProductionConfig, ProductionState, choose_recipe_for_facility
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.runtime.stockpile_policy import DepotPolicyLedger
from dosadi.state import WorldState
from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus
from dosadi.world.facilities import Facility, FacilityKind, FacilityLedger
from dosadi.world.materials import InventoryRegistry, Material
from dosadi.world.recipes import ensure_recipe_registry


def _market_world() -> WorldState:
    world = WorldState(seed=7)
    world.market_cfg = MarketSignalsConfig(enabled=True)
    world.market_state = MarketSignalsState()
    world.inventories = InventoryRegistry()
    world.stock_policies = DepotPolicyLedger()
    world.projects = ProjectLedger()
    world.facilities = FacilityLedger()
    ensure_recipe_registry(world)
    return world


def test_deterministic_update() -> None:
    base_a = _market_world()
    base_b = _market_world()

    profile = base_a.stock_policies.profile("depot-1")
    base_a.inventories.inv("facility:depot-1")
    base_b.stock_policies.profiles["depot-1"] = replace(profile)
    base_b.inventories.inv("facility:depot-1")

    run_market_signals_for_day(base_a, day=0)
    run_market_signals_for_day(base_b, day=0)

    assert world_signature(base_a) == world_signature(base_b)


def test_demand_raises_urgency() -> None:
    world = _market_world()
    world.stock_policies.profile("depot-1")
    run_market_signals_for_day(world, day=0)

    fasteners = world.market_state.global_signals.get("FASTENERS")
    assert fasteners is not None
    assert fasteners.urgency > world.market_cfg.urgency_floor


def test_supply_lowers_urgency() -> None:
    world = _market_world()
    world.stock_policies.profile("depot-1")
    run_market_signals_for_day(world, day=0)
    baseline = current_signal_urgency(world, "FASTENERS")

    world.metrics.gauges.setdefault("production", {})["outputs"] = {"FASTENERS": 500}
    run_market_signals_for_day(world, day=1)

    updated = current_signal_urgency(world, "FASTENERS")
    assert updated < baseline


def test_smoothing_prevents_whipsaw() -> None:
    world = _market_world()
    world.stock_policies.profile("depot-1")
    run_market_signals_for_day(world, day=0)
    first = current_signal_urgency(world, "FASTENERS")

    world.stock_policies = DepotPolicyLedger()
    run_market_signals_for_day(world, day=1)
    second = current_signal_urgency(world, "FASTENERS")

    assert second < first
    assert second > first * (1.0 - world.market_cfg.ema_alpha) - 1e-6


def test_consumer_prefers_urgent_outputs() -> None:
    world = _market_world()
    world.prod_cfg = ProductionConfig(enabled=True)
    world.prod_state = ProductionState()
    world.facilities.add(
        Facility(facility_id="work-1", kind=FacilityKind.WORKSHOP, site_node_id="node:a", created_tick=0)
    )
    world.stock_policies.profile("depot-1")
    inv = world.inventories.inv("facility:work-1")
    inv.add(Material.SCRAP_METAL, 20)

    world.market_state.global_signals["FASTENERS"] = MaterialMarketSignal(material="FASTENERS", urgency=0.9)

    recipe = choose_recipe_for_facility(world, "work-1", FacilityKind.WORKSHOP, 0, cfg=world.prod_cfg)
    assert recipe is not None
    assert recipe.recipe_id == "workshop_fasteners"


def test_snapshot_roundtrip() -> None:
    world = _market_world()
    world.stock_policies.profile("depot-1")
    world.projects.add_project(
        ConstructionProject(
            project_id="p1",
            site_node_id="node:a",
            kind="housing",
            status=ProjectStatus.APPROVED,
            created_tick=0,
            last_tick=0,
            cost=ProjectCost(materials={Material.FASTENERS.name: 20}, labor_hours=10),
            materials_delivered={},
            labor_applied_hours=0.0,
            bom={Material.FASTENERS: 20},
            assigned_agents=set(),
        )
    )

    run_market_signals_for_day(world, day=0)
    snap = snapshot_world(world, scenario_id="market")
    restored = restore_world(snap)
    restored.market_cfg = replace(world.market_cfg)

    run_market_signals_for_day(restored, day=1)
    run_market_signals_for_day(world, day=1)

    assert world_signature(world) == world_signature(restored)

