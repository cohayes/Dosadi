from __future__ import annotations

import copy

from dosadi.runtime.faction_interference import (
    InterferenceConfig,
    InterferenceState,
    run_faction_interference_for_day,
)
from dosadi.runtime.market_signals import MarketSignalsState, MaterialMarketSignal
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WorldState
from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, LogisticsLedger
from dosadi.world.materials import Material
from dosadi.world.phases import PhaseState, WorldPhase
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key
from dosadi.world.incidents import IncidentKind
from dosadi.runtime.corridor_risk import CorridorRiskConfig, CorridorRiskLedger, risk_for_edge


def _base_world() -> WorldState:
    world = WorldState(seed=7)
    world.day = 0
    world.phase_state = PhaseState(phase=WorldPhase.PHASE1)
    world.intf_cfg = InterferenceConfig(enabled=True, base_events_per_day=1.0, max_events_per_day=2)
    world.intf_state = InterferenceState()
    world.logistics = LogisticsLedger()
    world.market_state = MarketSignalsState(
        global_signals={"SCRAP_METAL": MaterialMarketSignal(material="SCRAP_METAL", urgency=0.9)}
    )
    world.survey_map = SurveyMap()
    world.survey_map.nodes["A"] = SurveyNode(node_id="A", kind="node", ward_id="ward:1")
    world.survey_map.nodes["B"] = SurveyNode(node_id="B", kind="node", ward_id="ward:1")
    edge = SurveyEdge(a="A", b="B", distance_m=1.0, travel_cost=1.0, hazard=0.0)
    world.survey_map.edges[edge.key] = edge
    world.risk_cfg = CorridorRiskConfig(enabled=True)
    world.risk_ledger = CorridorRiskLedger()
    return world


def _add_delivery(world: WorldState, delivery_id: str, escorts: int = 0) -> DeliveryRequest:
    delivery = DeliveryRequest(
        delivery_id=delivery_id,
        project_id="proj:1",
        origin_node_id="A",
        dest_node_id="B",
        items={"SCRAP_METAL": 40.0},
        status=DeliveryStatus.IN_TRANSIT,
        created_tick=0,
        route_nodes=["A", "B"],
        route_edge_keys=[edge_key("A", "B")],
        escort_agent_ids=[f"esc:{i}" for i in range(escorts)],
    )
    world.logistics.add(delivery)
    return delivery


def _add_project(world: WorldState, project_id: str) -> None:
    ledger = ProjectLedger()
    project = ConstructionProject(
        project_id=project_id,
        site_node_id="site:1",
        kind="workshop",
        status=ProjectStatus.STAGED,
        created_tick=0,
        last_tick=0,
        cost=ProjectCost(materials={}, labor_hours=10.0),
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
    )
    ledger.add_project(project)
    world.projects = ledger


def test_deterministic_spawn_and_losses() -> None:
    world_a = _base_world()
    world_b = copy.deepcopy(world_a)
    _add_delivery(world_a, "del:1")
    _add_delivery(world_b, "del:1")

    run_faction_interference_for_day(world_a, day=0)
    run_faction_interference_for_day(world_b, day=0)

    assert world_a.incidents.signature() == world_b.incidents.signature()
    assert world_a.logistics.signature() == world_b.logistics.signature()


def test_caps_and_cooldown() -> None:
    world = _base_world()
    world.intf_cfg.base_events_per_day = 5.0
    world.intf_cfg.max_events_per_day = 1
    _add_delivery(world, "del:1")

    run_faction_interference_for_day(world, day=0)
    first_history = list(world.incidents.history)
    assert world.intf_state.events_spawned_today <= world.intf_cfg.max_events_per_day

    run_faction_interference_for_day(world, day=1)
    assert world.incidents.history == first_history


def test_escort_mitigation_reduces_loss() -> None:
    baseline = _base_world()
    escorted = _base_world()
    _add_delivery(baseline, "del:1", escorts=0)
    _add_delivery(escorted, "del:1", escorts=2)

    run_faction_interference_for_day(baseline, day=0)
    run_faction_interference_for_day(escorted, day=0)

    base_incident = baseline.incidents.incidents[next(iter(baseline.incidents.incidents))]
    escorted_incident = escorted.incidents.incidents[next(iter(escorted.incidents.incidents))]
    assert base_incident.payload["stolen_qty"] > escorted_incident.payload["stolen_qty"]


def test_inventory_conservation_and_depot_theft() -> None:
    world = _base_world()
    world.intf_cfg.base_events_per_day = 1.0
    world.intf_cfg.max_events_per_day = 1
    profile = world.stock_policies.profile("depot:1")
    profile.thresholds[Material.SCRAP_METAL.name] = profile.thresholds[Material.SCRAP_METAL.name]
    registry = world.inventories
    registry.inv("depot:1").add(Material.SCRAP_METAL, 20)

    run_faction_interference_for_day(world, day=0)

    remaining = registry.inv("depot:1").get(Material.SCRAP_METAL)
    assert remaining >= 0
    incident = world.incidents.incidents[next(iter(world.incidents.incidents))]
    assert incident.kind is IncidentKind.THEFT_DEPOT
    assert incident.payload["stolen_qty"] <= 20


def test_risk_integration_updates_edge() -> None:
    world = _base_world()
    _add_delivery(world, "del:1")

    run_faction_interference_for_day(world, day=0)

    edge = edge_key("A", "B")
    assert risk_for_edge(world, edge) > 0.0


def test_snapshot_roundtrip_preserves_state() -> None:
    world = _base_world()
    _add_delivery(world, "del:1")
    _add_project(world, "proj:1")

    run_faction_interference_for_day(world, day=0)
    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)

    run_faction_interference_for_day(restored, day=1)
    assert restored.intf_state.last_run_day == 1
    assert restored.incidents.history

