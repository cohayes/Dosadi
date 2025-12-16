from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from dosadi.agent.memory_crumbs import CrumbStore
from dosadi.agent.memory_episodes import EpisodeBuffer
from dosadi.agent.memory_stm import STMBoringWinner
from dosadi.runtime.event_to_memory_router import RouterConfig, RouterState, run_router_for_day
from dosadi.world.events import EventKind, WorldEvent, WorldEventLog
from dosadi.world.workforce import Assignment, AssignmentKind, WorkforceLedger


def _make_agent(agent_id: str, stm_k: int = 24):
    agent = SimpleNamespace()
    agent.id = agent_id
    agent.crumbs = CrumbStore()
    agent.episodes_daily = EpisodeBuffer()
    agent.stm = STMBoringWinner(k=stm_k)
    return agent


def _make_world(*, seed: int = 1, stm_k: int = 24, max_len: int = 100) -> SimpleNamespace:
    world = SimpleNamespace()
    world.seed = seed
    world.day = 0
    world.workforce = WorkforceLedger()
    world.agents = {f"agent:{i}": _make_agent(f"agent:{i}", stm_k=stm_k) for i in range(10)}
    world.event_log = WorldEventLog(max_len=max_len)
    world.router_state = RouterState()
    world.router_config = RouterConfig(stm_k=stm_k)
    return world


def _append_event(world, *, day: int, kind: EventKind, subject_kind: str, subject_id: str, severity: float = 0.0, payload=None):
    event = WorldEvent(
        event_id="",
        day=day,
        kind=kind,
        subject_kind=subject_kind,
        subject_id=subject_id,
        severity=severity,
        payload=payload or {},
    )
    world.event_log.append(event)


def _crumb_signatures(world) -> dict:
    return {aid: agent.crumbs.signature() for aid, agent in sorted(world.agents.items())}


def _stm_signatures(world) -> dict:
    return {aid: agent.stm.signature() for aid, agent in sorted(world.agents.items())}


def test_deterministic_routing():
    def setup_world():
        world = _make_world(seed=42, stm_k=5)
        _append_event(
            world,
            day=1,
            kind=EventKind.DELIVERY_FAILED,
            subject_kind="delivery",
            subject_id="del-1",
            severity=0.9,
        )
        world.workforce.assignments["agent:1"] = Assignment(
            agent_id="agent:1", kind=AssignmentKind.LOGISTICS_COURIER, target_id="del-1", start_day=0
        )
        return world

    world_a = setup_world()
    world_b = setup_world()

    run_router_for_day(world_a, day=1)
    run_router_for_day(world_b, day=1)

    assert _crumb_signatures(world_a) == _crumb_signatures(world_b)
    assert _stm_signatures(world_a) == _stm_signatures(world_b)


def test_bounded_fan_out():
    world = _make_world(seed=7, stm_k=4)
    world.router_config.max_stakeholders_per_event = 5
    project_id = "proj-xyz"
    for idx, agent_id in enumerate(world.agents.keys()):
        world.workforce.assignments[agent_id] = Assignment(
            agent_id=agent_id, kind=AssignmentKind.PROJECT_WORK, target_id=project_id, start_day=0
        )
    _append_event(
        world,
        day=1,
        kind=EventKind.PROJECT_APPROVED,
        subject_kind="project",
        subject_id=project_id,
    )

    run_router_for_day(world, day=1)

    engaged = [aid for aid, agent in world.agents.items() if agent.crumbs.tags]
    assert len(engaged) <= world.router_config.max_stakeholders_per_event


def test_stm_boring_winner_keeps_top_k():
    world = _make_world(seed=5, stm_k=3)
    world.router_config.episode_salience_threshold = 0.0
    world.workforce.assignments["agent:0"] = Assignment(
        agent_id="agent:0", kind=AssignmentKind.LOGISTICS_COURIER, target_id="del-x", start_day=0
    )
    for severity in [0.1, 0.5, 0.9, 0.7, 0.3]:
        _append_event(
            world,
            day=1,
            kind=EventKind.INCIDENT,
            subject_kind="delivery",
            subject_id="del-x",
            severity=severity,
            payload={"incident_kind": "TEST", "target_kind": "delivery", "target_id": "del-x", "severity": severity},
        )

    run_router_for_day(world, day=1)

    agent = world.agents["agent:0"]
    assert len(agent.stm.items) <= 3

    episode_scores = sorted((ep.salience for ep in agent.episodes_daily.daily), reverse=True)
    stm_scores = sorted((itm.score for itm in agent.stm.items), reverse=True)
    assert stm_scores == episode_scores[: len(stm_scores)]


def test_cursor_prevents_double_application():
    world = _make_world(seed=11)
    world.workforce.assignments["agent:0"] = Assignment(
        agent_id="agent:0", kind=AssignmentKind.FACILITY_STAFF, target_id="fac-1", start_day=0
    )
    _append_event(
        world,
        day=1,
        kind=EventKind.FACILITY_DOWNTIME,
        subject_kind="facility",
        subject_id="fac-1",
    )

    run_router_for_day(world, day=1)
    first_count = world.agents["agent:0"].crumbs.tags.copy()
    run_router_for_day(world, day=1)
    assert world.agents["agent:0"].crumbs.tags == first_count


def test_snapshot_stability():
    world = _make_world(seed=21)
    world.workforce.assignments["agent:0"] = Assignment(
        agent_id="agent:0", kind=AssignmentKind.LOGISTICS_COURIER, target_id="del-a", start_day=0
    )
    _append_event(
        world,
        day=1,
        kind=EventKind.DELIVERY_FAILED,
        subject_kind="delivery",
        subject_id="del-a",
    )
    run_router_for_day(world, day=1)

    saved = deepcopy(world)

    for w in (world, saved):
        _append_event(
            w,
            day=2,
            kind=EventKind.PHASE_TRANSITION,
            subject_kind="phase",
            subject_id="0->1",
            payload={"from": 0, "to": 1},
        )
        run_router_for_day(w, day=2)

    assert _crumb_signatures(world) == _crumb_signatures(saved)
    assert _stm_signatures(world) == _stm_signatures(saved)


def test_ring_buffer_trim_updates_cursor():
    world = _make_world(seed=99, max_len=2)
    world.router_config.episode_salience_threshold = 0.0
    for idx in range(3):
        agent_id = f"agent:{idx}"
        world.workforce.assignments[agent_id] = Assignment(
            agent_id=agent_id, kind=AssignmentKind.PROJECT_WORK, target_id=f"p{idx+1}", start_day=0
        )
    _append_event(world, day=1, kind=EventKind.PROJECT_COMPLETE, subject_kind="project", subject_id="p1")
    _append_event(world, day=2, kind=EventKind.PROJECT_COMPLETE, subject_kind="project", subject_id="p2")
    _append_event(world, day=3, kind=EventKind.PROJECT_COMPLETE, subject_kind="project", subject_id="p3")

    world.router_state.cursor_seq = 0
    run_router_for_day(world, day=3)

    assert world.router_state.cursor_seq == world.event_log.base_seq + len(world.event_log.events)
    assert world.router_state.cursor_seq >= world.event_log.base_seq
