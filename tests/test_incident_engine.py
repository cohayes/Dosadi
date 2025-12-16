from dosadi.runtime.incident_engine import IncidentConfig, IncidentState, run_incident_engine_for_day
from dosadi.state import WorldState
from dosadi.world.facilities import Facility, FacilityLedger
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, LogisticsLedger
from dosadi.world.phases import WorldPhase, PhaseState


def _make_world(seed: int = 1) -> WorldState:
    world = WorldState(seed=seed)
    world.phase_state = PhaseState(phase=WorldPhase.PHASE2)
    world.incident_cfg = IncidentConfig()
    world.incident_state = IncidentState()
    return world


def test_delivery_delay_reschedules_due_queue() -> None:
    world = _make_world(seed=42)
    cfg = world.incident_cfg
    cfg.p_delivery_delay_p2 = 1.0
    cfg.p_delivery_loss_p2 = 0.0
    cfg.max_incidents_per_day = 1
    cfg.delay_days_min = 1
    cfg.delay_days_max = 3

    logistics = LogisticsLedger()
    delivery = DeliveryRequest(
        delivery_id="d1",
        project_id="p1",
        origin_node_id="o",
        dest_node_id="d",
        items={"water": 10.0},
        status=DeliveryStatus.IN_TRANSIT,
        created_tick=0,
        due_tick=None,
        deliver_tick=50,
    )
    logistics.add(delivery)
    world.logistics = logistics
    world.delivery_due_queue = [(delivery.deliver_tick, delivery.delivery_id)]

    run_incident_engine_for_day(world, day=0)

    updated_delivery = world.logistics.deliveries["d1"]
    assert updated_delivery.deliver_tick is not None
    assert updated_delivery.deliver_tick > 50
    assert world.delivery_due_queue == [(updated_delivery.deliver_tick, "d1")]

    assert world.incidents.history
    assert world.events and world.events[-1]["incident_kind"] == "DELIVERY_DELAY"


def test_facility_downtime_and_reactivation() -> None:
    world = _make_world(seed=7)
    cfg = world.incident_cfg
    cfg.p_facility_downtime_p2 = 1.0
    cfg.max_incidents_per_day = 1
    cfg.downtime_days_min = 2
    cfg.downtime_days_max = 2

    facilities = FacilityLedger()
    facility = Facility(
        facility_id="f1", kind="outpost", site_node_id="n1", created_tick=0
    )
    facilities.add(facility)
    world.facilities = facilities

    run_incident_engine_for_day(world, day=5)

    assert facility.status == "INACTIVE"
    assert facility.state.get("reactivate_day") == 7

    world.incident_cfg.p_facility_downtime_p2 = 0.0
    run_incident_engine_for_day(world, day=7)

    assert facility.status == "ACTIVE"
    assert "reactivate_day" not in facility.state
