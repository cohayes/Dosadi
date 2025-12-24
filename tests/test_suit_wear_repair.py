import copy

import pytest

from dosadi.agents.core import AgentState
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.suit_wear import (
    ensure_suit_config,
    ensure_suit_ledger,
    ensure_suit_state,
    run_suit_wear_for_day,
)
from dosadi.state import WorldState
from dosadi.world.facilities import Facility, FacilityKind, FacilityLedger
from dosadi.world.events import EventKind
from dosadi.world.logistics import DeliveryStatus, LogisticsLedger
from dosadi.world.materials import ensure_inventory_registry
from dosadi.world.workforce import AssignmentKind, WorkforceLedger


def _build_world(agent_count: int = 3) -> WorldState:
    world = WorldState(seed=99)
    world.facilities = FacilityLedger()
    world.workforce = WorkforceLedger()
    world.logistics = LogisticsLedger()
    ensure_inventory_registry(world)

    workshop = Facility(facility_id="fac:workshop-1", kind=FacilityKind.WORKSHOP, site_node_id="node:ws-1")
    world.facilities.add(workshop)

    for idx in range(agent_count):
        agent = AgentState(agent_id=f"agent:{idx}", name=f"Agent {idx}")
        world.agents[agent.agent_id] = agent
    cfg = ensure_suit_config(world)
    cfg.enabled = True
    ensure_suit_state(world)
    ensure_suit_ledger(world)
    return world


def test_flag_off_keeps_suits_static():
    world = _build_world(agent_count=2)
    cfg = ensure_suit_config(world)
    cfg.enabled = False

    before = {aid: agent.suit.integrity for aid, agent in world.agents.items()}
    run_suit_wear_for_day(world, day=0)

    after = {aid: agent.suit.integrity for aid, agent in world.agents.items()}
    assert before == after
    assert world.suit_repairs.jobs == {}


def test_deterministic_wear_applied():
    world_a = _build_world(agent_count=3)
    world_b = copy.deepcopy(world_a)

    run_suit_wear_for_day(world_a, day=1)
    run_suit_wear_for_day(world_b, day=1)

    integrities_a = {aid: agent.suit.integrity for aid, agent in world_a.agents.items()}
    integrities_b = {aid: agent.suit.integrity for aid, agent in world_b.agents.items()}
    assert integrities_a == integrities_b
    assert world_a.suit_repairs.signature() == world_b.suit_repairs.signature()


def test_threshold_events_and_flags():
    world = _build_world(agent_count=1)
    cfg = ensure_suit_config(world)
    cfg.wear_per_day_base = 0.3
    agent = next(iter(world.agents.values()))
    agent.suit.integrity = 0.65

    run_suit_wear_for_day(world, day=5)

    assert agent.suit.repair_needed is True
    kinds = {event.kind for event in world.event_log.events}
    assert EventKind.SUIT_WEAR_WARN in kinds
    assert EventKind.SUIT_REPAIR_NEEDED in kinds


def test_repair_job_creation_bounded():
    world = _build_world(agent_count=5)
    cfg = ensure_suit_config(world)
    cfg.max_repairs_per_day = 2
    for agent in world.agents.values():
        agent.suit.integrity = 0.2
        agent.suit.repair_needed = True

    run_suit_wear_for_day(world, day=2)

    assert len(world.suit_repairs.jobs) == 2
    assert list(sorted(world.suit_repairs.open_jobs_by_agent.keys())) == ["agent:0", "agent:1"]


def test_repair_completes_with_parts_and_staff():
    world = _build_world(agent_count=2)
    cfg = ensure_suit_config(world)
    cfg.repair_duration_days = 1
    subject = world.agents["agent:0"]
    subject.suit.integrity = 0.1
    subject.suit.repair_needed = True

    run_suit_wear_for_day(world, day=0)
    job_id = world.suit_repairs.open_jobs_by_agent[subject.agent_id]
    job = world.suit_repairs.jobs[job_id]

    delivery_id = job.pending_delivery_ids[0]
    delivery = world.logistics.deliveries[delivery_id]
    delivery.status = DeliveryStatus.DELIVERED

    run_suit_wear_for_day(world, day=1)

    assert subject.suit.integrity == pytest.approx(1.0)
    assert subject.suit.repair_needed is False
    assert world.suit_repairs.jobs[job_id].status == "DONE"
    workforce = world.workforce
    assert all(assignment.kind is AssignmentKind.IDLE for assignment in workforce.assignments.values())


def test_no_duplicate_deliveries():
    world = _build_world(agent_count=1)
    agent = world.agents["agent:0"]
    agent.suit.integrity = 0.1
    agent.suit.repair_needed = True

    run_suit_wear_for_day(world, day=0)
    job_id = world.suit_repairs.open_jobs_by_agent[agent.agent_id]
    job = world.suit_repairs.jobs[job_id]

    run_suit_wear_for_day(world, day=0)
    assert len(job.pending_delivery_ids) == 1
    assert len(world.logistics.deliveries) == 1


def test_snapshot_roundtrip_mid_repair():
    world = _build_world(agent_count=2)
    subject = world.agents["agent:0"]
    subject.suit.integrity = 0.2
    subject.suit.repair_needed = True

    run_suit_wear_for_day(world, day=3)
    snapshot = snapshot_world(world, scenario_id="suit")
    restored = restore_world(snapshot)

    job_id = world.suit_repairs.open_jobs_by_agent[subject.agent_id]
    delivery_id = world.suit_repairs.jobs[job_id].pending_delivery_ids[0]
    world.logistics.deliveries[delivery_id].status = DeliveryStatus.DELIVERED
    run_suit_wear_for_day(world, day=4)

    restored_job_id = restored.suit_repairs.open_jobs_by_agent[subject.agent_id]
    restored_delivery_id = restored.suit_repairs.jobs[restored_job_id].pending_delivery_ids[0]
    restored.logistics.deliveries[restored_delivery_id].status = DeliveryStatus.DELIVERED
    run_suit_wear_for_day(restored, day=4)

    assert world.suit_repairs.signature() == restored.suit_repairs.signature()
    assert restored.agents[subject.agent_id].suit.integrity == pytest.approx(world.agents[subject.agent_id].suit.integrity)
