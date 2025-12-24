from __future__ import annotations

from dosadi.agents.core import AgentState, Attributes
from dosadi.runtime.maintenance import ensure_maintenance_config, update_facility_wear
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.state import WorldState
from dosadi.world.facilities import Facility, FacilityKind, FacilityLedger
from dosadi.world.materials import Material, ensure_inventory_registry
from dosadi.world.workforce import ensure_workforce


def _world_with_facility(kind: FacilityKind = FacilityKind.DEPOT, wear: float = 0.0) -> WorldState:
    world = WorldState(seed=7)
    world.facilities = FacilityLedger()
    facility = Facility(facility_id="fac:test", kind=kind, site_node_id="loc:test", wear=wear)
    world.facilities.add(facility)
    ensure_maintenance_config(world).enabled = True
    return world


def test_flag_off_baseline() -> None:
    world = _world_with_facility()
    cfg = ensure_maintenance_config(world)
    cfg.enabled = False

    update_facility_wear(world, day=0)

    assert world.facilities.get("fac:test").wear == 0.0
    assert not getattr(world, "maintenance", {}).jobs


def test_deterministic_wear_increment() -> None:
    base_world = _world_with_facility()
    snapshot = snapshot_world(base_world, scenario_id="maint-test")
    world_a = restore_world(snapshot)
    world_b = restore_world(snapshot)

    update_facility_wear(world_a, day=0)
    update_facility_wear(world_b, day=0)

    assert world_a.facilities.get("fac:test").wear == world_b.facilities.get("fac:test").wear


def test_job_opens_at_threshold() -> None:
    world = _world_with_facility(wear=0.8)

    update_facility_wear(world, day=0)

    facility = world.facilities.get("fac:test")
    assert facility.maintenance_due is True
    assert getattr(world, "maintenance").open_jobs_by_facility.get("fac:test")


def test_shutdown_event_at_threshold() -> None:
    world = _world_with_facility(wear=0.96)

    update_facility_wear(world, day=0)

    facility = world.facilities.get("fac:test")
    assert facility.down_until_day == 0
    assert facility.is_operational is False
    assert any(evt.get("type") == "FACILITY_SHUTDOWN_WEAR" for evt in getattr(world, "runtime_events", []))


def test_maintenance_completes_with_parts_and_crew() -> None:
    world = _world_with_facility(kind=FacilityKind.WORKSHOP, wear=0.85)
    agent = AgentState(agent_id="agent:1", name="worker", attributes=Attributes(INT=5, END=5))
    world.agents[agent.agent_id] = agent
    ensure_workforce(world)
    inv = ensure_inventory_registry(world).inv("facility:fac:test")
    inv.add(Material.FASTENERS, 10)
    inv.add(Material.SEALANT, 5)
    inv.add(Material.SCRAP_METAL, 10)

    update_facility_wear(world, day=0)
    update_facility_wear(world, day=1)

    job = world.maintenance.jobs.get("maint:fac:test:0")
    facility = world.facilities.get("fac:test")
    assert job is not None and job.status == "DONE"
    assert facility.wear == 0.0
    assert facility.maintenance_job_id is None
    assert ensure_workforce(world).get(agent.agent_id).kind.name == "IDLE"


def test_no_duplicate_deliveries() -> None:
    world = _world_with_facility(kind=FacilityKind.RECYCLER, wear=0.85)

    update_facility_wear(world, day=0)
    update_facility_wear(world, day=1)

    job = world.maintenance.jobs.get("maint:fac:test:0")
    assert job is not None
    assert len(job.pending_delivery_ids) == 1
    assert len(world.logistics.deliveries) == 1


def test_snapshot_roundtrip_continues_jobs() -> None:
    world = _world_with_facility(kind=FacilityKind.DEPOT, wear=0.9)
    update_facility_wear(world, day=0)
    inv = ensure_inventory_registry(world).inv("facility:fac:test")
    inv.add(Material.FASTENERS, 5)
    inv.add(Material.SEALANT, 5)

    snap = snapshot_world(world, scenario_id="maint-snap")
    restored = restore_world(snap)

    update_facility_wear(world, day=1)
    update_facility_wear(world, day=2)

    inv_restored = ensure_inventory_registry(restored).inv("facility:fac:test")
    inv_restored.add(Material.FASTENERS, 5)
    inv_restored.add(Material.SEALANT, 5)
    update_facility_wear(restored, day=1)
    update_facility_wear(restored, day=2)

    assert world_signature(world) == world_signature(restored)
