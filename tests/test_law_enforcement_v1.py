from copy import deepcopy

from dosadi.runtime.corridor_risk import CorridorRiskLedger, EdgeRiskRecord
from dosadi.runtime.faction_interference import run_faction_interference_for_day
from dosadi.runtime.law_enforcement import (
    EnforcementConfig,
    WardSecurityPolicy,
    ensure_policy_for_ward,
    ensure_state_for_ward,
    run_enforcement_for_day,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WorldState
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode
from dosadi.world.logistics import DeliveryRequest, LogisticsLedger, DeliveryStatus
from dosadi.runtime.market_signals import MarketSignalsState, MaterialMarketSignal


def _basic_world() -> WorldState:
    world = WorldState()
    node_a = SurveyNode(node_id="A", kind="hub", ward_id="ward:1")
    node_b = SurveyNode(node_id="B", kind="hub", ward_id="ward:1")
    edge = SurveyEdge(a="A", b="B", distance_m=1.0, travel_cost=1.0)
    world.survey_map = SurveyMap(nodes={"A": node_a, "B": node_b}, edges={edge.key: edge})
    world.risk_ledger = CorridorRiskLedger(edges={edge.key: EdgeRiskRecord(edge_key=edge.key, risk=0.5, incidents_lookback=0.2)})
    world.enf_cfg = EnforcementConfig(enabled=True)
    world.enf_policy_by_ward = {"ward:1": WardSecurityPolicy(ward_id="ward:1", budget_points=6.0, posture="balanced")}
    world.logistics = LogisticsLedger()
    delivery = DeliveryRequest(
        delivery_id="d1",
        origin_node_id="A",
        dest_node_id="B",
        items={"mat": 10},
        project_id="proj",
        status=DeliveryStatus.REQUESTED,
        created_tick=0,
        route_nodes=["A", "B"],
        route_edge_keys=[edge.key],
    )
    world.logistics.add(delivery)
    world.market_state = MarketSignalsState(global_signals={"mat": MaterialMarketSignal(material="mat", urgency=1.0)})
    # Prime interference config/state for tests
    from dosadi.runtime.faction_interference import InterferenceConfig, InterferenceState

    world.intf_cfg = InterferenceConfig(enabled=False)
    world.intf_state = InterferenceState()
    return world


def test_enforcement_determinism():
    world = _basic_world()
    run_enforcement_for_day(world, day=1)
    snapshot_state = deepcopy(world.enf_state_by_ward)

    clone = deepcopy(world)
    run_enforcement_for_day(clone, day=1)

    assert snapshot_state == clone.enf_state_by_ward


def test_caps_respected():
    world = _basic_world()
    policy = ensure_policy_for_ward(world, "ward:1")
    policy.budget_points = 50.0
    world.enf_cfg.max_patrols_per_ward = 3
    world.enf_cfg.max_checkpoints_per_ward = 2
    run_enforcement_for_day(world, day=2)
    state = ensure_state_for_ward(world, "ward:1")

    assert sum(state.patrol_edges.values()) <= world.enf_cfg.max_patrols_per_ward
    assert sum(state.checkpoints.values()) <= world.enf_cfg.max_checkpoints_per_ward


def test_interference_mitigation_prevents_incident():
    world = _basic_world()
    world.enf_cfg.base_interdiction_prob = 1.0
    world.enf_cfg.max_interdiction_prob = 1.0
    run_enforcement_for_day(world, day=3)

    world.intf_cfg.enabled = True  # type: ignore[attr-defined]
    world.intf_cfg.base_events_per_day = 1.0  # type: ignore[attr-defined]
    world.intf_cfg.max_events_per_day = 1  # type: ignore[attr-defined]
    world.intf_state.last_run_day = -1  # type: ignore[attr-defined]

    run_faction_interference_for_day(world, day=3)
    incidents = getattr(world, "incidents", None)
    assert incidents is None or len(incidents.incidents) == 0
    assert world.metrics.counters.get("enforcement.incidents_prevented", 0) >= 1


def test_risk_suppression():
    world = _basic_world()
    record = world.risk_ledger.edges[next(iter(world.risk_ledger.edges))]
    original_risk = record.risk
    run_enforcement_for_day(world, day=4)
    assert record.risk < original_risk


def test_snapshot_roundtrip():
    world = _basic_world()
    run_enforcement_for_day(world, day=5)
    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)
    assert restored.enf_state_by_ward == world.enf_state_by_ward
    assert restored.enf_policy_by_ward == world.enf_policy_by_ward
