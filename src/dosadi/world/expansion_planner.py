"""Deterministic expansion planner for spawning construction projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Iterable, Mapping, MutableMapping

from .construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus, stage_project_if_ready
from .facilities import FacilityKind, coerce_facility_kind
from .extraction import SiteKind, ensure_extraction
from .materials import Material, ensure_inventory_registry, normalize_bom
from .site_scoring import SiteScoreConfig, score_site
from .survey_map import SurveyMap, SurveyNode, edge_key


@dataclass(slots=True)
class ExpansionPlannerConfig:
    planning_interval_days: int = 30
    max_candidates: int = 50
    max_new_projects_per_cycle: int = 1
    max_active_projects: int = 3
    min_site_confidence: float = 0.5
    project_kinds: tuple[str, ...] = tuple(kind.value for kind in FacilityKind)
    materials_budget: dict[str, float] = field(default_factory=dict)
    labor_pool_size: int = 8
    min_idle_agents: int = 10
    belief_route_weight: float = 0.25
    belief_supply_weight: float = 0.10
    belief_facility_weight: float = 0.15


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
    components: dict[str, float] = field(default_factory=dict)


_DEFAULT_COSTS: Mapping[str, ProjectCost] = {
    FacilityKind.DEPOT.value: ProjectCost(materials={"metal": 4.0, "polymer": 3.0}, labor_hours=24.0),
    FacilityKind.WORKSHOP.value: ProjectCost(
        materials={"metal": 8.0, "polymer": 6.0}, labor_hours=72.0
    ),
    FacilityKind.RECYCLER.value: ProjectCost(
        materials={"metal": 6.0, "polymer": 4.0}, labor_hours=64.0
    ),
}


def estimate_cost(kind: str) -> ProjectCost:
    return _DEFAULT_COSTS.get(kind, ProjectCost(materials={}, labor_hours=0.0))


def _material_shortages(world, *, top_k: int = 5) -> list[tuple[Material, int]]:
    registry = ensure_inventory_registry(world)
    shortages: dict[Material, int] = {}
    cfg = getattr(world, "mat_cfg", None)
    default_owner = getattr(cfg, "default_depot_owner_id", "ward:0")

    depot_inv = registry.inv(default_owner)
    for material in Material:
        qty = depot_inv.get(material)
        if qty < 2:
            shortages[material] = shortages.get(material, 0) + (2 - qty)

    ledger: ProjectLedger = getattr(world, "projects", ProjectLedger())
    for project in ledger.projects.values():
        bom = normalize_bom(project.bom) or normalize_bom(project.cost.materials)
        if not bom:
            continue
        inv = registry.inv(f"project:{project.project_id}")
        for material, qty in bom.items():
            delivered = inv.get(material)
            if delivered < qty:
                shortages[material] = shortages.get(material, 0) + (qty - delivered)

    ordered = sorted(shortages.items(), key=lambda item: (-item[1], item[0].name))
    return ordered[:top_k]


def _kind_for_shortages(shortages: list[tuple[Material, int]]) -> FacilityKind:
    for material, _ in shortages:
        if material in {Material.FASTENERS, Material.SEALANT}:
            return FacilityKind.WORKSHOP
        if material in {Material.SCRAP_METAL, Material.PLASTICS}:
            return FacilityKind.RECYCLER
    return FacilityKind.DEPOT


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


def _planner_agent(world):
    try:
        from dosadi.runtime.belief_queries import planner_perspective_agent

        return planner_perspective_agent(world)
    except Exception:
        return None


def _route_risk(agent, edge_key: str) -> float:
    try:
        from dosadi.runtime.belief_queries import route_risk

        return route_risk(agent, edge_key)
    except Exception:
        return 0.5


def _facility_risk(agent, facility_id: str) -> float:
    try:
        from dosadi.runtime.belief_queries import facility_reliability

        return facility_reliability(agent, facility_id)
    except Exception:
        return 0.5


def _route_risk_to_site(agent, origin: str | None, node: SurveyNode, survey: SurveyMap) -> float:
    if not origin:
        return 0.5
    key = edge_key(origin, node.node_id)
    edge = survey.edges.get(key)
    if edge is None:
        return 0.5
    return _route_risk(agent, key)


def _supply_risk(origin: str | None, node: SurveyNode, survey: SurveyMap) -> float:
    if not origin:
        return 0.5
    key = edge_key(origin, node.node_id)
    edge = survey.edges.get(key)
    if edge is None:
        return 0.5
    distance = max(edge.distance_m, edge.travel_cost)
    return min(1.0, 0.5 + distance / 200.0)


def _facility_failure_risk(agent, world, node: SurveyNode) -> float:
    facilities = getattr(world, "facilities", {}) or {}
    for facility_id, facility in facilities.items():
        if getattr(facility, "node_id", None) == node.node_id:
            return _facility_risk(agent, facility_id)
    return 0.5


_RESOURCE_WEIGHTS: Mapping[SiteKind, float] = {
    SiteKind.SCRAP_FIELD: 3.0,
    SiteKind.SALVAGE_CACHE: 2.5,
    SiteKind.BRINE_POCKET: 1.0,
    SiteKind.THERMAL_VENT: 0.5,
}


def _resource_bonus(world, node_id: str) -> tuple[float, Mapping[str, float]]:
    ledger = ensure_extraction(world)
    site_ids = ledger.sites_by_node.get(node_id, [])
    bonus = 0.0
    breakdown: dict[str, float] = {}
    for site_id in sorted(site_ids):
        site = ledger.sites.get(site_id)
        if site is None:
            continue
        weight = _RESOURCE_WEIGHTS.get(site.kind, 0.0)
        contribution = weight * max(0.0, float(getattr(site, "richness", 0.0)))
        if contribution <= 0.0:
            continue
        breakdown[site.kind.value] = contribution
        bonus += contribution
    return bonus, breakdown


def _emit_site_ranking(world, *, day: int, proposals: list[ProjectProposal]) -> None:
    top = []
    seen_sites: set[str] = set()
    for proposal in proposals:
        if proposal.site_node_id in seen_sites:
            continue
        top.append(
            {
                "site": proposal.site_node_id,
                "kind": proposal.kind,
                "score": proposal.score,
                "components": dict(proposal.components),
            }
        )
        seen_sites.add(proposal.site_node_id)
        if len(top) >= 3:
            break

    event = {
        "type": "PLANNER_SITE_RANKING",
        "day": day,
        "top": top,
    }
    log = getattr(world, "runtime_events", None)
    if isinstance(log, list):
        log.append(event)
    else:
        world.runtime_events = [event]


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
    planner_agent = _planner_agent(world)
    shortages = _material_shortages(world)
    default_kinds = tuple(kind.value for kind in FacilityKind)
    if cfg.project_kinds and tuple(cfg.project_kinds) != default_kinds:
        chosen_kind = coerce_facility_kind(cfg.project_kinds[0])
    else:
        chosen_kind = _kind_for_shortages(shortages)
    proposals: list[ProjectProposal] = []
    for node in candidates:
        for kind in (chosen_kind.value,):
            base_score = score_site(node, origin_node_id=origin, survey=survey, cfg=score_cfg)
            route_risk = _route_risk_to_site(planner_agent, origin, node, survey)
            supply_risk = _supply_risk(origin, node, survey)
            facility_risk = _facility_failure_risk(planner_agent, world, node)
            resource_bonus, resource_components = _resource_bonus(world, node.node_id)
            score = (
                base_score
                - cfg.belief_route_weight * route_risk
                - cfg.belief_supply_weight * supply_risk
                - cfg.belief_facility_weight * facility_risk
                + resource_bonus
            )
            proposals.append(
                ProjectProposal(
                    site_node_id=node.node_id,
                    kind=kind,
                    score=score,
                    estimated_cost=estimate_cost(kind),
                    components={
                        "base": base_score,
                        "route_risk": route_risk,
                        "supply_risk": supply_risk,
                        "facility_risk": facility_risk,
                        "resource_bonus": resource_bonus,
                    },
                )
            )
            if resource_components:
                proposals[-1].components["resource_components"] = dict(sorted(resource_components.items()))

    proposals.sort(
        key=lambda p: (
            -p.score,
            p.site_node_id,
            0,
        )
    )

    _emit_site_ranking(world, day=day, proposals=proposals)

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
