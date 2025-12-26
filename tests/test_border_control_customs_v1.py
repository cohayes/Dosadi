import copy
from types import SimpleNamespace

import pytest

from dosadi.runtime.customs import (
    CustomsConfig,
    customs_seed_payload,
    iter_border_crossings,
    load_customs_from_seed,
    process_customs_crossing,
)
from dosadi.runtime.institutions import WardInstitutionPolicy, WardInstitutionState
from dosadi.runtime.ledger import LedgerAccount, LedgerConfig, LedgerState
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key


EDGE = edge_key("A", "B")


def _make_world(cfg: CustomsConfig | None = None) -> SimpleNamespace:
    world = SimpleNamespace()
    world.day = 0
    world.phase_state = SimpleNamespace(phase=0)
    world.wards = {"wardA": {}, "wardB": {}}
    world.survey_map = SurveyMap(
        nodes={
            "A": SurveyNode(node_id="A", kind="hub", ward_id="wardA"),
            "B": SurveyNode(node_id="B", kind="hub", ward_id="wardB"),
        },
        edges={EDGE: SurveyEdge(a="A", b="B", distance_m=1, travel_cost=1)},
    )
    world.customs_cfg = cfg or CustomsConfig(enabled=True)
    world.ledger_cfg = LedgerConfig(enabled=True)
    world.ledger_state = LedgerState(
        accounts={
            "acct:ward:wardA": LedgerAccount(acct_id="acct:ward:wardA", balance=200.0),
            "acct:ward:wardB": LedgerAccount(acct_id="acct:ward:wardB", balance=50.0),
            "acct:state:treasury": LedgerAccount(acct_id="acct:state:treasury", balance=0.0),
        }
    )
    world.inst_policy_by_ward = {
        "wardA": WardInstitutionPolicy(ward_id="wardA"),
        "wardB": WardInstitutionPolicy(ward_id="wardB"),
    }
    world.inst_state_by_ward = {
        "wardA": WardInstitutionState(ward_id="wardA"),
        "wardB": WardInstitutionState(ward_id="wardB"),
    }
    return world


def _make_delivery(**overrides) -> DeliveryRequest:
    delivery = DeliveryRequest(
        delivery_id=overrides.pop("delivery_id", "delivery:1"),
        project_id="proj",
        origin_node_id="A",
        dest_node_id="B",
        items={"NARCOTICS": 10.0},
        status=DeliveryStatus.IN_TRANSIT,
        created_tick=0,
        route_nodes=["A", "B"],
        route_edge_keys=[EDGE],
    )
    delivery.flags = {"suspicious"}
    delivery.owner_party = "wardA"
    delivery.declared_value = 100.0
    for key, value in overrides.items():
        setattr(delivery, key, value)
    return delivery


def test_determinism_same_inputs_same_outcome():
    cfg = CustomsConfig(
        enabled=True,
        base_inspection_rate=1.0,
        contraband_detection_base=1.0,
        base_tariff_rate=0.1,
    )
    world_a = _make_world(cfg)
    world_b = _make_world(copy.deepcopy(cfg))
    delivery_a = _make_delivery()
    delivery_b = _make_delivery()

    crossing = iter_border_crossings(world_a, delivery_a.route_nodes, delivery_a.route_edge_keys)[0]

    evt_a = process_customs_crossing(world_a, day=0, shipment=delivery_a, crossing=crossing)
    evt_b = process_customs_crossing(world_b, day=0, shipment=delivery_b, crossing=crossing)

    assert evt_a is not None and evt_b is not None
    assert evt_a.outcome == evt_b.outcome
    assert evt_a.tariff_charged == evt_b.tariff_charged
    assert evt_a.bribe_paid == evt_b.bribe_paid


def test_treaty_exemption_zero_tariff_and_lower_risk():
    cfg = CustomsConfig(enabled=True, base_tariff_rate=0.2, base_inspection_rate=0.5)
    world = _make_world(cfg)
    delivery = _make_delivery(flags={"treaty_exempt"})
    crossing = iter_border_crossings(world, delivery.route_nodes, delivery.route_edge_keys)[0]

    evt = process_customs_crossing(world, day=1, shipment=delivery, crossing=crossing)

    assert evt is not None
    assert evt.tariff_charged == 0.0
    assert "TARIFF_ONLY" not in evt.reason_codes


def test_corruption_and_bribery_influence_outcome():
    cfg = CustomsConfig(
        enabled=True,
        base_inspection_rate=1.0,
        contraband_detection_base=2.0,
        base_tariff_rate=0.05,
    )
    world = _make_world(cfg)
    delivery = _make_delivery()
    crossing = iter_border_crossings(world, delivery.route_nodes, delivery.route_edge_keys)[0]

    # High corruption path should clear via bribe
    world.inst_policy_by_ward["wardB"].customs_bribe_tolerance = 0.9
    world.inst_state_by_ward["wardB"].corruption = 0.6

    evt_high = process_customs_crossing(world, day=2, shipment=delivery, crossing=crossing)
    assert evt_high is not None
    assert evt_high.outcome == "CLEARED"
    assert evt_high.bribe_paid > 0
    assert "BRIBE_SUCCESS" in evt_high.reason_codes

    # Low tolerance + heavy enforcement should seize
    world.inst_policy_by_ward["wardB"].customs_bribe_tolerance = 0.0
    world.inst_policy_by_ward["wardB"].enforcement_budget_points = 10.0
    world.inst_state_by_ward["wardB"].corruption = 0.0

    delivery2 = _make_delivery(delivery_id="delivery:2")
    evt_low = process_customs_crossing(world, day=3, shipment=delivery2, crossing=crossing)
    assert evt_low is not None
    assert evt_low.outcome == "SEIZED"
    assert evt_low.bribe_paid == 0.0


def test_ledger_transfers_tariffs_and_bribes():
    cfg = CustomsConfig(enabled=True, base_tariff_rate=0.1, base_inspection_rate=0.0)
    world = _make_world(cfg)
    delivery = _make_delivery()
    crossing = iter_border_crossings(world, delivery.route_nodes, delivery.route_edge_keys)[0]

    evt = process_customs_crossing(world, day=4, shipment=delivery, crossing=crossing)

    assert evt is not None
    payer = world.ledger_state.accounts["acct:ward:wardA"]
    receiver = world.ledger_state.accounts["acct:ward:wardB"]
    assert payer.balance < 200.0
    assert receiver.balance > 50.0


def test_max_checks_per_day_cap():
    cfg = CustomsConfig(enabled=True, max_checks_per_day=1, base_inspection_rate=0.0)
    world = _make_world(cfg)
    delivery = _make_delivery()
    crossing = iter_border_crossings(world, delivery.route_nodes, delivery.route_edge_keys)[0]

    first = process_customs_crossing(world, day=5, shipment=delivery, crossing=crossing)
    second = process_customs_crossing(world, day=5, shipment=delivery, crossing=crossing)

    assert first is not None
    assert second is None
    assert len(world.customs_events) == 1


def test_snapshot_roundtrip_preserves_events():
    cfg = CustomsConfig(enabled=True, base_tariff_rate=0.1)
    world = _make_world(cfg)
    delivery = _make_delivery()
    crossing = iter_border_crossings(world, delivery.route_nodes, delivery.route_edge_keys)[0]

    event = process_customs_crossing(world, day=6, shipment=delivery, crossing=crossing)
    payload = customs_seed_payload(world)
    assert payload is not None

    restored = SimpleNamespace()
    load_customs_from_seed(restored, payload)

    assert isinstance(restored.customs_cfg, CustomsConfig)
    assert len(restored.customs_events) == 1
    restored_event = restored.customs_events[0]
    assert restored_event.shipment_id == event.shipment_id
    assert restored_event.tariff_charged == event.tariff_charged
