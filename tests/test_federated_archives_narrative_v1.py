from __future__ import annotations

from dosadi.runtime.archives import ArchiveState, archives_signature, run_archives_for_day
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WorldState
from dosadi.world.incidents import Incident, IncidentKind, IncidentLedger
from dosadi.runtime.truth_regimes import IntegrityState


def _world_with_incidents(seed: int, incidents: list[Incident]) -> WorldState:
    world = WorldState(seed=seed)
    world.archives_cfg.enabled = True
    world.archives_cfg.update_cadence_days = 1
    world.incidents = IncidentLedger()
    world.archive_by_polity["polity:central"] = ArchiveState(polity_id="polity:central", archive_capacity=1.0)
    for inc in incidents:
        world.incidents.add(inc)
    return world


def test_archives_determinism():
    incidents = [
        Incident(
            incident_id="inc:1",
            kind=IncidentKind.WORKER_INJURY,
            day=5,
            target_kind="polity",
            target_id="polity:central",
            severity=0.8,
        ),
        Incident(
            incident_id="inc:2",
            kind=IncidentKind.RIOT,
            day=10,
            target_kind="polity",
            target_id="polity:central",
            severity=0.6,
        ),
    ]
    world_a = _world_with_incidents(7, incidents)
    world_b = _world_with_incidents(7, incidents)

    run_archives_for_day(world_a, day=30)
    run_archives_for_day(world_b, day=30)

    sig_a = archives_signature(world_a)
    sig_b = archives_signature(world_b)
    assert sig_a == sig_b


def test_archive_capacity_increases_retention():
    incidents = [
        Incident(
            incident_id="inc:cap-1",
            kind=IncidentKind.RIOT,
            day=2,
            target_kind="polity",
            target_id="polity:central",
            severity=0.9,
        ),
        Incident(
            incident_id="inc:cap-2",
            kind=IncidentKind.WORKER_INJURY,
            day=3,
            target_kind="polity",
            target_id="polity:central",
            severity=0.8,
        ),
    ]
    high = _world_with_incidents(1, incidents)
    low = _world_with_incidents(1, incidents)
    high.archive_by_polity["polity:central"] = ArchiveState(polity_id="polity:central", archive_capacity=1.0)
    low.archive_by_polity["polity:central"] = ArchiveState(polity_id="polity:central", archive_capacity=0.4)

    run_archives_for_day(high, day=5)
    run_archives_for_day(low, day=5)

    assert len(high.canon_events["polity:central"]) > len(low.canon_events["polity:central"]) >= 0


def test_weak_truth_regimes_enable_revisionism():
    incidents = [
        Incident(
            incident_id="inc:rev-1",
            kind=IncidentKind.RIOT,
            day=4,
            target_kind="polity",
            target_id="polity:central",
            severity=0.9,
        )
    ]
    weak = _world_with_incidents(2, incidents)
    strong = _world_with_incidents(2, incidents)
    weak.integrity_by_polity["polity:central"] = IntegrityState(scope_kind="polity", scope_id="polity:central", metrology=0.1)
    strong.integrity_by_polity["polity:central"] = IntegrityState(scope_kind="polity", scope_id="polity:central", metrology=0.95)
    weak.archive_by_polity["polity:central"] = ArchiveState(
        polity_id="polity:central",
        archive_capacity=1.0,
        censorship_pressure=0.8,
        revisionism_pressure=0.7,
        pluralism=0.1,
    )
    strong.archive_by_polity["polity:central"] = ArchiveState(
        polity_id="polity:central",
        archive_capacity=1.0,
        censorship_pressure=0.1,
        revisionism_pressure=0.1,
    )

    run_archives_for_day(weak, day=10)
    run_archives_for_day(strong, day=10)

    weak_statuses = {evt.status for evt in weak.canon_events["polity:central"]}
    strong_statuses = {evt.status for evt in strong.canon_events["polity:central"]}
    assert weak_statuses != {"CANON"}
    assert strong_statuses == {"CANON"}


def test_narrative_stances_follow_topics():
    incidents = [
        Incident(
            incident_id="inc:martyr",
            kind=IncidentKind.WORKER_INJURY,
            day=1,
            target_kind="polity",
            target_id="polity:central",
            severity=0.9,
        ),
        Incident(
            incident_id="inc:war",
            kind=IncidentKind.RIOT,
            day=2,
            target_kind="polity",
            target_id="polity:central",
            severity=0.7,
        ),
    ]
    world = _world_with_incidents(3, incidents)
    run_archives_for_day(world, day=15)

    stances = world.narrative_by_polity["polity:central"].stances
    assert stances.get("martyrdom", 0.0) > 0.0
    assert stances.get("militarism", 0.0) > 0.0


def test_counter_narratives_form_under_suppression():
    incidents = [
        Incident(
            incident_id="inc:cn-1",
            kind=IncidentKind.RIOT,
            day=6,
            target_kind="polity",
            target_id="polity:central",
            severity=0.95,
        )
    ]
    world = _world_with_incidents(4, incidents)
    world.archive_by_polity["polity:central"] = ArchiveState(
        polity_id="polity:central",
        censorship_pressure=0.9,
        revisionism_pressure=0.6,
        pluralism=0.2,
    )

    run_archives_for_day(world, day=30)

    assert len(world.counter_narratives.get("polity:central", [])) > 0


def test_archives_snapshot_roundtrip():
    incidents = [
        Incident(
            incident_id="inc:snap-1",
            kind=IncidentKind.WORKER_INJURY,
            day=2,
            target_kind="polity",
            target_id="polity:central",
            severity=0.85,
        )
    ]
    world = _world_with_incidents(5, incidents)
    run_archives_for_day(world, day=20)

    snapshot = snapshot_world(world, scenario_id="scenario")
    restored = restore_world(snapshot)

    assert len(restored.canon_events.get("polity:central", [])) == len(world.canon_events.get("polity:central", []))

