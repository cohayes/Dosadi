"""Deterministic expansion planner for spawning construction projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Iterable, Mapping, MutableMapping

from .construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus, stage_project_if_ready
from .site_scoring import SiteScoreConfig, score_site
from .survey_map import SurveyMap, SurveyNode


@dataclass(slots=True)
class ExpansionPlannerConfig:
    planning_interval_days: int = 30
    max_candidates: int = 50
    max_new_projects_per_cycle: int = 1
    max_active_projects: int = 3
    min_site_confidence: float = 0.5
    project_kinds: tuple[str, ...] = ("outpost",)
    materials_budget: dict[str, float] = field(default_factory=dict)
    labor_pool_size: int = 8
    min_idle_agents: int = 10


@dataclass(slots=True)
class ExpansionPlannerState:
    next_plan_day: int
    last_plan_day: int = -1
    recent_choices: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProjectProposal:
    site_node_id: str
    kind: str
    score: float
    estimated_cost: ProjectCost


_DEFAULT_COSTS: Mapping[str, ProjectCost] = {
    "outpost": ProjectCost(materials={"polymer": 10.0, "metal": 5.0}, labor_hours=80.0),
    "pump_station": ProjectCost(materials={"metal": 8.0, "ceramic": 6.0}, labor_hours=64.0),
}


def estimate_cost(kind: str) -> ProjectCost:
    return _DEFAULT_COSTS.get(kind, ProjectCost(materials={}, labor_hours=0.0))


def _materials_available(stock: MutableMapping[str, float], cost: ProjectCost, budget: Mapping[str, float]) -> bool:
    for material, qty in cost.materials.items():
        if stock.get(material, 0.0) < qty:
            return False
        if budget:
            cap = budget.get(material)
            if cap is not None and qty > cap:
                return False
    return True


def _deterministic_agents(world, *, labor_pool_size: int, min_idle: int) -> list[str]:
    assigned = set()
    ledger: ProjectLedger = getattr(world, "projects", ProjectLedger())
    for project in ledger.projects.values():
        if project.status in {ProjectStatus.COMPLETE, ProjectStatus.CANCELED}:
            continue
        assigned.update(project.assigned_agents)

    agent_ids = sorted(getattr(world, "agents", {}).keys())
    idle_candidates = [aid for aid in agent_ids if aid not in assigned]
    available = max(0, len(idle_candidates) - min_idle)
    if available < labor_pool_size:
        return []
    return idle_candidates[:labor_pool_size]


def _origin_node_id(world, survey: SurveyMap) -> str | None:
    if "loc:well-core" in survey.nodes:
        return "loc:well-core"
    if "loc:well-core" in getattr(world, "nodes", {}):
        return "loc:well-core"
    return None


def _active_project_count(ledger: ProjectLedger) -> int:
    active_status = {ProjectStatus.PROPOSED, ProjectStatus.APPROVED, ProjectStatus.STAGED, ProjectStatus.BUILDING}
    return sum(1 for project in ledger.projects.values() if project.status in active_status)


def _project_id(day: int, site_node_id: str, kind: str) -> str:
    digest = sha256(f"{day}:{site_node_id}:{kind}".encode("utf-8")).hexdigest()
    return f"proj:{digest[:12]}"


def maybe_plan(
    world,
    *,
    cfg: ExpansionPlannerConfig,
    state: ExpansionPlannerState,
) -> list[str]:
    day = getattr(world, "day", 0)
    if day < state.next_plan_day or day == state.last_plan_day:
        return []

    survey: SurveyMap = getattr(world, "survey_map", SurveyMap())
    ledger: ProjectLedger = getattr(world, "projects", None) or ProjectLedger()
    world.projects = ledger

    candidates: list[SurveyNode] = []
    facility_sites = set(getattr(world, "facilities", {}).keys())
    for node_id, node in sorted(survey.nodes.items()):
        if node.confidence < cfg.min_site_confidence:
            continue
        if node_id in facility_sites:
            continue
        if node_id in state.recent_choices:
            continue
        candidates.append(node)
        if len(candidates) >= cfg.max_candidates:
            break

    origin = _origin_node_id(world, survey)
    score_cfg = SiteScoreConfig()
    proposals: list[ProjectProposal] = []
    for node in candidates:
        for kind in cfg.project_kinds:
            score = score_site(node, origin_node_id=origin, survey=survey, cfg=score_cfg)
            proposals.append(
                ProjectProposal(
                    site_node_id=node.node_id,
                    kind=kind,
                    score=score,
                    estimated_cost=estimate_cost(kind),
                )
            )

    proposals.sort(key=lambda p: (-p.score, p.site_node_id, p.kind))

    stockpiles: MutableMapping[str, float] = getattr(world, "stockpiles", {})
    created: list[str] = []
    new_projects = 0
    active = _active_project_count(ledger)

    for proposal in proposals:
        if active >= cfg.max_active_projects or new_projects >= cfg.max_new_projects_per_cycle:
            break

        if not _materials_available(stockpiles, proposal.estimated_cost, cfg.materials_budget):
            continue

        agents = _deterministic_agents(
            world, labor_pool_size=cfg.labor_pool_size, min_idle=cfg.min_idle_agents
        )
        if not agents:
            continue

        project_id = _project_id(day, proposal.site_node_id, proposal.kind)
        project = ConstructionProject(
            project_id=project_id,
            site_node_id=proposal.site_node_id,
            kind=proposal.kind,
            status=ProjectStatus.APPROVED,
            created_tick=getattr(world, "tick", 0),
            last_tick=getattr(world, "tick", 0),
            cost=proposal.estimated_cost,
            materials_delivered={},
            labor_applied_hours=0.0,
            assigned_agents=list(agents),
        )

        ledger.add_project(project)
        stage_project_if_ready(world, project, getattr(world, "tick", 0))
        created.append(project_id)
        state.recent_choices.append(proposal.site_node_id)
        if len(state.recent_choices) > 10:
            state.recent_choices = state.recent_choices[-10:]

        new_projects += 1
        active += 1

    state.last_plan_day = day
    state.next_plan_day = day + max(1, cfg.planning_interval_days)

    return created


__all__ = [
    "ExpansionPlannerConfig",
    "ExpansionPlannerState",
    "ProjectProposal",
    "estimate_cost",
    "maybe_plan",
]
