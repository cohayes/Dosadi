from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from dosadi.world.construction import ProjectStatus
from dosadi.world.facilities import Facility, get_facility_behavior
from dosadi.world.scout_missions import MissionStatus
from dosadi.world.workforce import Assignment, AssignmentKind, WorkforceLedger, ensure_workforce


@dataclass(slots=True)
class StaffingConfig:
    min_idle_agents: int = 10
    policy_interval_days: int = 1
    max_changes_per_cycle: int = 10
    project_workers_default: int = 6
    facility_staff_default: int = 2
    prefer_keep_assignments: bool = True


@dataclass(slots=True)
class StaffingState:
    last_run_day: int = -1


def _role_priority(role: str | None) -> int:
    if role is None:
        return 50
    priority = {
        "scout": 0,
        "engineer": 1,
        "builder": 2,
        "worker": 3,
    }
    return priority.get(role, 25)


def _score(agent, kind: AssignmentKind) -> float:
    def _attr(key: str) -> float:
        attrs = getattr(agent, "attributes", None)
        if attrs is not None and hasattr(attrs, key):
            return float(getattr(attrs, key, 0.0) or 0.0)

        skills = getattr(agent, "skills", None)
        if isinstance(skills, dict) and key in skills:
            val = skills.get(key)
            return float(getattr(val, "score", val) or 0.0)

        affinities = getattr(agent, "affinities", None)
        if isinstance(affinities, dict):
            return float(affinities.get(key, 0.0) or 0.0)

        return 0.0

    if kind is AssignmentKind.PROJECT_WORK:
        return _attr("construction_skill") + _attr("END") + _attr("WIL")
    if kind is AssignmentKind.FACILITY_STAFF:
        return _attr("craft") + _attr("INT")
    if kind is AssignmentKind.SCOUT_MISSION:
        return _attr("perception") + _attr("END")
    return _attr("INT") + _attr("WIL")


def _candidate_sort_key(agent, kind: AssignmentKind) -> Tuple[int, float, str]:
    role = getattr(agent, "role", None)
    return (_role_priority(role), -_score(agent, kind), getattr(agent, "id", ""))


def _active_assignments_for_target(
    ledger: WorkforceLedger, *, kind: AssignmentKind, target_id: str | None
) -> List[str]:
    return [
        agent_id
        for agent_id, assignment in ledger.assignments.items()
        if assignment.kind is kind and assignment.target_id == target_id
    ]


def _prune_inactive_assignments(
    ledger: WorkforceLedger,
    *,
    active_targets: dict[AssignmentKind, set[str | None]],
    changes_left: int,
) -> int:
    for agent_id, assignment in list(ledger.assignments.items()):
        targets = active_targets.get(assignment.kind)
        if targets is None or assignment.kind is AssignmentKind.IDLE:
            continue
        if assignment.target_id in targets:
            continue
        if changes_left <= 0:
            break
        ledger.unassign(agent_id)
        changes_left -= 1
    return changes_left


def _assign_agents(
    world,
    ledger: WorkforceLedger,
    *,
    requests: List[tuple[AssignmentKind, str | None, int]],
    cfg: StaffingConfig,
    day: int,
    changes_left: int,
) -> int:
    idle_agents = [
        agent
        for agent in world.agents.values()
        if ledger.is_idle(agent.id)
    ]

    total_agents = len(world.agents)
    available = max(0, total_agents - cfg.min_idle_agents)
    for kind, target_id, needed_count in requests:
        if changes_left <= 0 or available <= 0:
            break

        current = _active_assignments_for_target(ledger, kind=kind, target_id=target_id)
        already = len(current)
        if already >= needed_count:
            continue

        candidates = sorted(idle_agents, key=lambda agent: _candidate_sort_key(agent, kind))
        for agent in list(candidates):
            if available <= 0 or changes_left <= 0:
                break
            if not ledger.is_idle(agent.id):
                continue
            ledger.assign(
                Assignment(
                    agent_id=agent.id,
                    kind=kind,
                    target_id=target_id,
                    start_day=day,
                )
            )
            idle_agents.remove(agent)
            available -= 1
            changes_left -= 1
            already += 1
            if already >= needed_count:
                break

    return changes_left


def _requested_staffing(world, cfg: StaffingConfig) -> List[tuple[AssignmentKind, str | None, int]]:
    requests: List[tuple[AssignmentKind, str | None, int]] = []

    missions = getattr(world, "scout_missions", None)
    if missions is not None and hasattr(missions, "active_ids"):
        for mission_id in missions.active_ids:
            mission = missions.missions.get(mission_id)
            if mission is None or mission.status in {MissionStatus.COMPLETE, MissionStatus.FAILED}:
                continue
            requests.append(
                (AssignmentKind.SCOUT_MISSION, mission.mission_id, len(mission.party_agent_ids))
            )

    projects = getattr(getattr(world, "projects", None), "projects", None)
    if projects:
        for project in projects.values():
            if project.status not in {ProjectStatus.STAGED, ProjectStatus.BUILDING}:
                continue
            requests.append(
                (AssignmentKind.PROJECT_WORK, project.project_id, cfg.project_workers_default)
            )

    facilities = getattr(getattr(world, "facilities", None), "values", None)
    if facilities is not None:
        for facility in facilities():
            if not isinstance(facility, Facility):
                continue
            try:
                behavior = get_facility_behavior(facility.kind)
            except Exception:
                continue
            if not getattr(behavior, "requires_labor", False):
                continue
            requests.append(
                (
                    AssignmentKind.FACILITY_STAFF,
                    facility.facility_id,
                    cfg.facility_staff_default,
                )
            )

    return requests


def run_staffing_policy(world, *, day: int, cfg: StaffingConfig, state: StaffingState) -> None:
    if day - state.last_run_day < cfg.policy_interval_days:
        return

    ledger = ensure_workforce(world)

    requests = _requested_staffing(world, cfg)
    active_targets = {
        kind: {target_id for req_kind, target_id, _ in requests if req_kind is kind}
        for kind in {req[0] for req in requests}
    }

    changes_left = _prune_inactive_assignments(
        ledger, active_targets=active_targets, changes_left=cfg.max_changes_per_cycle
    )

    _assign_agents(
        world,
        ledger,
        requests=requests,
        cfg=cfg,
        day=day,
        changes_left=changes_left,
    )

    state.last_run_day = day


__all__ = [
    "StaffingConfig",
    "StaffingState",
    "run_staffing_policy",
]
