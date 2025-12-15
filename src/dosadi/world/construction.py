"""Construction project scaffolding for building new facilities.

This module implements a minimal deterministic pipeline:
PROPOSED → APPROVED → STAGED → BUILDING → COMPLETE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from hashlib import sha256
from typing import Dict, MutableMapping, Optional


class ProjectStatus(Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    STAGED = "STAGED"
    BUILDING = "BUILDING"
    COMPLETE = "COMPLETE"
    CANCELED = "CANCELED"


@dataclass(slots=True)
class ProjectCost:
    materials: Dict[str, float]
    labor_hours: float


@dataclass(slots=True)
class ConstructionProject:
    project_id: str
    site_node_id: str
    kind: str
    status: ProjectStatus
    created_tick: int
    last_tick: int
    cost: ProjectCost
    materials_delivered: Dict[str, float]
    labor_applied_hours: float
    assigned_agents: list[str]
    deadline_tick: Optional[int] = None
    notes: Dict[str, str] = field(default_factory=dict)

    def ensure_building(self) -> None:
        if self.status == ProjectStatus.STAGED and self.assigned_agents:
            self.status = ProjectStatus.BUILDING

    def is_complete(self) -> bool:
        if self.status == ProjectStatus.COMPLETE:
            return True
        if self.status != ProjectStatus.BUILDING:
            return False
        materials_ready = all(
            self.materials_delivered.get(mat, 0.0) >= required
            for mat, required in self.cost.materials.items()
        )
        return materials_ready and self.labor_applied_hours >= self.cost.labor_hours


@dataclass(slots=True)
class ProjectLedger:
    projects: MutableMapping[str, ConstructionProject] = field(default_factory=dict)

    def add_project(self, p: ConstructionProject) -> None:
        self.projects[p.project_id] = p

    def get(self, project_id: str) -> ConstructionProject:
        return self.projects[project_id]

    def signature(self) -> str:
        canonical = {
            project_id: {
                "status": project.status.value,
                "site": project.site_node_id,
                "kind": project.kind,
                "materials": dict(sorted(project.materials_delivered.items())),
                "labor": round(project.labor_applied_hours, 6),
                "assigned": sorted(project.assigned_agents),
            }
            for project_id, project in sorted(self.projects.items())
        }
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()


def _hours_per_tick(world) -> float:
    seconds = getattr(getattr(world, "config", None), "tick_seconds", 0.6)
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        seconds = 0.6
    return max(0.0, seconds) / 3600.0


def _agent_skill_factor(world, agent_id: str) -> float:
    agent = getattr(world, "agents", {}).get(agent_id)
    if agent is None:
        return 0.0
    attrs = getattr(agent, "attributes", None)
    if attrs is None:
        return 1.0
    return max(0.1, (getattr(attrs, "INT", 10) + getattr(attrs, "END", 10)) / 20.0)


def _can_reserve_materials(stock: MutableMapping[str, float], required: Dict[str, float]) -> bool:
    for material, qty in required.items():
        if stock.get(material, 0.0) < qty:
            return False
    return True


def stage_project_if_ready(world, project: ConstructionProject, tick: int) -> bool:
    if project.status != ProjectStatus.APPROVED:
        return False

    stockpiles: MutableMapping[str, float] = getattr(world, "stockpiles", {})
    if not _can_reserve_materials(stockpiles, project.cost.materials):
        return False

    for material, qty in project.cost.materials.items():
        stockpiles[material] = stockpiles.get(material, 0.0) - qty
        project.materials_delivered[material] = project.materials_delivered.get(material, 0.0) + qty

    project.status = ProjectStatus.STAGED
    project.last_tick = tick
    return True


def _apply_labor(world, project: ConstructionProject, elapsed_hours: float, tick: int) -> None:
    if elapsed_hours <= 0.0 or project.status != ProjectStatus.BUILDING:
        return

    labor_delta = 0.0
    for agent_id in project.assigned_agents:
        labor_delta += elapsed_hours * _agent_skill_factor(world, agent_id)

    project.labor_applied_hours += labor_delta
    project.last_tick = tick


def _create_facility_stub(world, project: ConstructionProject) -> str:
    facility_id = f"fac:{project.project_id}"
    facilities: MutableMapping[str, object] = getattr(world, "facilities", {})
    if facility_id not in facilities:
        stub = {
            "id": facility_id,
            "kind": project.kind,
            "site_node_id": project.site_node_id,
            "project_id": project.project_id,
        }
        facilities[facility_id] = stub
        nodes: MutableMapping[str, object] = getattr(world, "nodes", {})
        nodes.setdefault(
            facility_id,
            {
                "id": facility_id,
                "kind": "facility",
                "site_node_id": project.site_node_id,
                "name": project.kind,
            },
        )
    return facility_id


def _maybe_complete(world, project: ConstructionProject, tick: int) -> None:
    if project.status == ProjectStatus.CANCELED:
        return

    if project.is_complete():
        _create_facility_stub(world, project)
        project.status = ProjectStatus.COMPLETE
        project.last_tick = tick


def process_projects(world, *, tick: Optional[int] = None) -> None:
    current_tick = tick if tick is not None else getattr(world, "tick", 0)
    hours = _hours_per_tick(world)
    ledger: ProjectLedger = getattr(world, "projects", ProjectLedger())

    for project in ledger.projects.values():
        if project.status == ProjectStatus.CANCELED:
            continue

        if project.status == ProjectStatus.APPROVED:
            stage_project_if_ready(world, project, current_tick)

        project.ensure_building()

        if project.status == ProjectStatus.BUILDING:
            _apply_labor(world, project, hours, current_tick)

        _maybe_complete(world, project, current_tick)


def apply_project_work(world, *, elapsed_hours: float, tick: Optional[int] = None) -> None:
    current_tick = tick if tick is not None else getattr(world, "tick", 0)
    ledger: ProjectLedger = getattr(world, "projects", ProjectLedger())

    for project in ledger.projects.values():
        if project.status in {ProjectStatus.CANCELED, ProjectStatus.COMPLETE}:
            continue

        if project.status == ProjectStatus.APPROVED:
            stage_project_if_ready(world, project, current_tick)

        project.ensure_building()

        if project.status == ProjectStatus.BUILDING:
            _apply_labor(world, project, elapsed_hours, current_tick)

        _maybe_complete(world, project, current_tick)

