from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Iterable, Mapping, MutableMapping, Sequence

from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus
from dosadi.world.extraction import ExtractionLedger, SiteKind, ensure_extraction
from dosadi.world.facilities import FacilityKind, coerce_facility_kind, ensure_facility_ledger
from dosadi.world.materials import InventoryRegistry, Material, ensure_inventory_registry, normalize_bom
from dosadi.world.survey_map import SurveyMap


@dataclass(slots=True)
class ExpansionPlannerV2Config:
    enabled: bool = False
    top_k_nodes: int = 25
    top_k_actions: int = 8
    max_actions_per_day: int = 2
    min_days_between_actions: int = 3
    shortage_lookback_days: int = 5
    downtime_lookback_days: int = 14
    suit_attrition_lookback_days: int = 7
    prefer_same_ward: bool = True
    deterministic_salt: str = "planner-v2"
    w_shortage: float = 1.0
    w_blocked_projects: float = 0.9
    w_extraction: float = 1.1
    w_flow_distance: float = 0.6
    w_risk: float = 0.7
    w_downtime: float = 0.5
    w_suit_cost: float = 0.4
    w_information: float = 0.8


@dataclass(slots=True)
class ExpansionPlannerV2State:
    last_action_day: int = -10
    actions_taken_today: int = 0
    last_plan_signature: str = ""


@dataclass(slots=True)
class ScoreBreakdown:
    total: float
    terms: dict[str, float] = field(default_factory=dict)
    details: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class PlannedAction:
    kind: str
    target_node_id: str | None
    facility_kind: str | None
    payload: dict[str, object]
    score: ScoreBreakdown


_ACTION_ORDER: tuple[str, ...] = (
    "BUILD_DEPOT",
    "BUILD_WORKSHOP",
    "BUILD_RECYCLER",
    "BUILD_CORRIDOR_EDGE",
    "SCHEDULE_SCOUT_MISSION",
    "INCREASE_ESCORT_LEVEL",
    "ALLOCATE_MAINTENANCE_CREW",
)


def _stable_metrics(world) -> MutableMapping[str, MutableMapping[str, int]]:
    metrics = getattr(world, "metrics", None)
    if not isinstance(metrics, MutableMapping):
        metrics = {}
        world.metrics = metrics
    bucket = metrics.setdefault("planner_v2", {})
    return bucket


def _stable_events(world) -> list[dict[str, object]]:
    events = getattr(world, "runtime_events", None)
    if not isinstance(events, list):
        events = []
        world.runtime_events = events
    return events


def _shortage_targets() -> Mapping[Material, int]:
    return {
        Material.FASTENERS: 20,
        Material.SEALANT: 20,
        Material.FABRIC: 10,
        Material.SCRAP_METAL: 30,
        Material.PLASTICS: 20,
    }


def _shortage_signal(world, *, top_k: int) -> list[tuple[Material, float, str | None]]:
    registry: InventoryRegistry = ensure_inventory_registry(world)
    targets = _shortage_targets()
    shortages: list[tuple[Material, float, str | None]] = []

    for owner_id, inventory in sorted(registry.by_owner.items(), key=lambda item: item[0]):
        for material, target in targets.items():
            qty = inventory.get(material)
            deficit = max(0, target - qty)
            if deficit <= 0:
                continue
            severity = min(1.0, deficit / max(1.0, float(target)))
            shortages.append((material, severity, owner_id))

    ledger: ProjectLedger = getattr(world, "projects", None) or ProjectLedger()
    for project in ledger.projects.values():
        bom = normalize_bom(project.bom) or normalize_bom(project.cost.materials)
        if not bom:
            continue
        delivered = normalize_bom(project.materials_delivered)
        for material, qty in bom.items():
            missing = max(0, qty - delivered.get(material, 0))
            if missing <= 0:
                continue
            severity = min(1.0, missing / max(1.0, float(targets.get(material, qty))))
            shortages.append((material, severity, project.site_node_id))

    shortages.sort(key=lambda tup: (-tup[1], tup[0].name, tup[2] or ""))
    return shortages[:top_k]


def _blocked_projects(world, *, top_k: int) -> dict[str, float]:
    ledger: ProjectLedger = getattr(world, "projects", None) or ProjectLedger()
    blocked: dict[str, float] = {}
    for project in ledger.projects.values():
        if project.stage_state.value == "WAITING_MATERIALS":
            blocked[project.site_node_id] = blocked.get(project.site_node_id, 0.0) + 1.0
        elif project.stage_state.value == "WAITING_STAFF":
            blocked[project.site_node_id] = blocked.get(project.site_node_id, 0.0) + 0.5
        elif project.block_reason:
            blocked[project.site_node_id] = blocked.get(project.site_node_id, 0.0) + 0.25

    ordered = sorted(blocked.items(), key=lambda item: (-item[1], item[0]))
    return dict(ordered[:top_k])


def _extraction_yields(world, *, top_k: int) -> dict[str, float]:
    ledger: ExtractionLedger = ensure_extraction(world)
    yields: dict[str, float] = {}
    for node_id, site_ids in sorted(ledger.sites_by_node.items()):
        total = 0.0
        for site_id in sorted(site_ids):
            site = ledger.sites.get(site_id)
            if site is None:
                continue
            total += max(0.0, float(site.richness))
            if site.kind == SiteKind.SCRAP_FIELD:
                total += 0.25
        if total > 0:
            yields[node_id] = total
    ordered = sorted(yields.items(), key=lambda item: (-item[1], item[0]))
    return dict(ordered[:top_k])


def _downtime(world, *, top_k: int) -> dict[str, float]:
    facilities = ensure_facility_ledger(world)
    day = getattr(world, "day", 0)
    downtime: dict[str, float] = {}
    for facility in facilities.values():
        if facility.down_until_day > day:
            downtime[facility.site_node_id] = max(downtime.get(facility.site_node_id, 0.0), 1.0)
    ordered = sorted(downtime.items(), key=lambda item: (-item[1], item[0]))
    return dict(ordered[:top_k])


def _suit_stress(world) -> float:
    ledger = getattr(world, "suit_service_ledger", None)
    if not ledger:
        return 0.0
    pending = len(getattr(ledger, "repairs_pending", []) or [])
    active_agents = max(1, len(getattr(world, "agents", {}) or {}))
    return min(1.0, pending / float(active_agents))


def _information_signal(world, shortages: Sequence[tuple[Material, float, str | None]]):
    survey: SurveyMap = getattr(world, "survey_map", SurveyMap())
    frontier = [node_id for node_id, node in sorted(survey.nodes.items()) if node.confidence < 0.5]
    need_information = bool(frontier and shortages)
    return need_information, frontier[:5]


def _node_for_owner(owner_id: str | None, survey: SurveyMap) -> str | None:
    if owner_id is None:
        return None
    if owner_id in survey.nodes:
        return owner_id
    if ":" in owner_id:
        parts = owner_id.split(":")
        for idx in range(len(parts) - 1, -1, -1):
            candidate = ":".join(parts[: idx + 1])
            if candidate in survey.nodes:
                return candidate
    return None


def _candidate_nodes(
    survey: SurveyMap,
    *,
    extraction: Mapping[str, float],
    blocked: Mapping[str, float],
    shortages: Sequence[tuple[Material, float, str | None]],
    frontier: Sequence[str],
    top_k: int,
) -> list[str]:
    candidates: set[str] = set()
    candidates.update(extraction.keys())
    candidates.update(blocked.keys())
    candidates.update(frontier)

    for owner_id in (owner for *_, owner in shortages if owner):
        node_id = _node_for_owner(owner_id, survey)
        if node_id:
            candidates.add(node_id)

    scored: list[tuple[float, str]] = []
    for node_id in candidates:
        proxy = extraction.get(node_id, 0.0) + blocked.get(node_id, 0.0)
        scored.append((proxy, node_id))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [node_id for _, node_id in scored[:top_k]]


def _risk_for_node(survey: SurveyMap, node_id: str) -> float:
    node = survey.nodes.get(node_id)
    if not node:
        return 0.0
    return max(0.0, float(getattr(node, "hazard", 0.0)))


def _ward_for_node(survey: SurveyMap, node_id: str) -> str | None:
    node = survey.nodes.get(node_id)
    if not node:
        return None
    return getattr(node, "ward_id", None)


def _shortage_score_for_node(node_id: str, shortages: Sequence[tuple[Material, float, str | None]], survey: SurveyMap) -> float:
    score = 0.0
    for material, severity, owner in shortages:
        owner_node = _node_for_owner(owner, survey)
        if owner_node and owner_node == node_id:
            score += severity
    return score


def _global_shortage(materials: set[Material], shortages: Sequence[tuple[Material, float, str | None]]) -> float:
    return sum(severity for material, severity, _ in shortages if material in materials)


def _score_depot(node_id: str, *, cfg: ExpansionPlannerV2Config, signals: dict[str, object]) -> ScoreBreakdown:
    survey: SurveyMap = signals["survey"]
    shortages = signals["shortages"]
    extraction = signals["extraction"]
    blocked = signals["blocked"]
    downtime = signals["downtime"]
    ward = _ward_for_node(survey, node_id)
    base_shortage = _shortage_score_for_node(node_id, shortages, survey)
    extraction_term = extraction.get(node_id, 0.0) * cfg.w_extraction
    shortage_term = base_shortage * cfg.w_shortage
    blocked_term = blocked.get(node_id, 0.0) * cfg.w_blocked_projects
    risk_term = -_risk_for_node(survey, node_id) * cfg.w_risk
    downtime_term = -downtime.get(node_id, 0.0) * cfg.w_downtime

    if cfg.prefer_same_ward:
        origin_ward = getattr(signals.get("origin_node", None), "ward_id", None)
        if origin_ward and ward and ward != origin_ward:
            downtime_term -= cfg.w_flow_distance * 0.5

    total = extraction_term + shortage_term + blocked_term + risk_term + downtime_term
    return ScoreBreakdown(
        total=total,
        terms={
            "extraction": extraction_term,
            "shortage": shortage_term,
            "blocked": blocked_term,
            "risk": risk_term,
            "downtime": downtime_term,
        },
        details={"ward": ward},
    )


def _score_workshop(node_id: str, *, cfg: ExpansionPlannerV2Config, signals: dict[str, object]) -> ScoreBreakdown:
    survey: SurveyMap = signals["survey"]
    shortages = signals["shortages"]
    blocked = signals["blocked"]
    downtime = signals["downtime"]
    risk_term = -_risk_for_node(survey, node_id) * cfg.w_risk
    downtime_term = -downtime.get(node_id, 0.0) * cfg.w_downtime
    shortage_term = _global_shortage(
        {Material.FASTENERS, Material.SEALANT, Material.FABRIC}, shortages
    ) * cfg.w_shortage
    blocked_term = blocked.get(node_id, 0.0) * cfg.w_blocked_projects
    total = shortage_term + blocked_term + risk_term + downtime_term
    return ScoreBreakdown(
        total=total,
        terms={
            "shortage": shortage_term,
            "blocked": blocked_term,
            "risk": risk_term,
            "downtime": downtime_term,
        },
        details={},
    )


def _score_recycler(node_id: str, *, cfg: ExpansionPlannerV2Config, signals: dict[str, object]) -> ScoreBreakdown:
    survey: SurveyMap = signals["survey"]
    shortages = signals["shortages"]
    extraction = signals["extraction"]
    downtime = signals["downtime"]
    risk_term = -_risk_for_node(survey, node_id) * cfg.w_risk
    downtime_term = -downtime.get(node_id, 0.0) * cfg.w_downtime
    shortage_term = _global_shortage(
        {Material.SCRAP_METAL, Material.PLASTICS}, shortages
    ) * cfg.w_shortage
    extraction_term = extraction.get(node_id, 0.0) * cfg.w_extraction
    total = shortage_term + extraction_term + risk_term + downtime_term
    return ScoreBreakdown(
        total=total,
        terms={
            "shortage": shortage_term,
            "extraction": extraction_term,
            "risk": risk_term,
            "downtime": downtime_term,
        },
        details={},
    )


def _score_scout(node_id: str | None, *, cfg: ExpansionPlannerV2Config, signals: dict[str, object]) -> ScoreBreakdown:
    risk = 0.0
    if node_id:
        risk = _risk_for_node(signals["survey"], node_id)
    need_information: bool = signals["need_information"]
    suit_stress: float = signals["suit_stress"]
    info_term = (cfg.w_information if need_information else 0.0)
    suit_term = -suit_stress * cfg.w_suit_cost
    risk_term = -risk * cfg.w_risk
    total = info_term + suit_term + risk_term
    return ScoreBreakdown(
        total=total,
        terms={"information": info_term, "suit": suit_term, "risk": risk_term},
        details={},
    )


def _hash_plan(actions: Sequence[PlannedAction], *, salt: str) -> str:
    payload = [
        {
            "kind": action.kind,
            "node": action.target_node_id,
            "facility": action.facility_kind,
            "score": round(action.score.total, 6),
        }
        for action in actions
    ]
    digest = sha256((salt + str(payload)).encode("utf-8")).hexdigest()
    return digest[:16]


def _maybe_emit_action(world, action: PlannedAction) -> None:
    events = _stable_events(world)
    events.append(
        {
            "type": "PLANNER_V2_ACTION_CHOSEN",
            "kind": action.kind,
            "node_id": action.target_node_id,
            "score_terms": action.score.terms,
            "payload": action.payload,
            "day": getattr(world, "day", 0),
        }
    )


def _ensure_ledger(world) -> ProjectLedger:
    ledger: ProjectLedger = getattr(world, "projects", None) or ProjectLedger()
    world.projects = ledger
    return ledger


def _execute_build(world, action: PlannedAction) -> str:
    ledger = _ensure_ledger(world)
    project_id = f"proj:{sha256((action.kind + (action.target_node_id or 'none')).encode('utf-8')).hexdigest()[:10]}"
    if project_id in ledger.projects:
        return project_id
    cost = ProjectCost(materials={}, labor_hours=12.0)
    project = ConstructionProject(
        project_id=project_id,
        site_node_id=action.target_node_id or "unknown",
        kind=action.facility_kind or "DEPOT",
        status=ProjectStatus.APPROVED,
        created_tick=getattr(world, "tick", 0),
        last_tick=getattr(world, "tick", 0),
        cost=cost,
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
    )
    ledger.add_project(project)
    return project_id


def _apply_actions(world, actions: Sequence[PlannedAction]) -> list[str]:
    created: list[str] = []
    for action in actions:
        _maybe_emit_action(world, action)
        if action.kind in {"BUILD_DEPOT", "BUILD_WORKSHOP", "BUILD_RECYCLER"}:
            created.append(_execute_build(world, action))
        elif action.kind == "SCHEDULE_SCOUT_MISSION":
            missions = getattr(world, "scout_missions", None)
            if not isinstance(missions, list):
                missions = []
                world.scout_missions = missions
            missions.append(action.payload)
            created.append(f"scout:{action.target_node_id or 'frontier'}")
    return created


def maybe_plan_expansion_v2(
    world,
    *,
    cfg: ExpansionPlannerV2Config | None = None,
    state: ExpansionPlannerV2State | None = None,
) -> list[str]:
    cfg = cfg or getattr(world, "plan2_cfg", ExpansionPlannerV2Config())
    state = state or getattr(world, "plan2_state", ExpansionPlannerV2State())
    world.plan2_cfg = cfg
    world.plan2_state = state

    if not cfg.enabled:
        return []

    day = getattr(world, "day", 0)
    if day - state.last_action_day < cfg.min_days_between_actions and state.actions_taken_today >= cfg.max_actions_per_day:
        _stable_events(world).append({"type": "PLANNER_V2_SKIPPED_COOLDOWN", "day": day})
        return []

    survey: SurveyMap = getattr(world, "survey_map", SurveyMap())
    shortages = _shortage_signal(world, top_k=cfg.top_k_nodes)
    blocked = _blocked_projects(world, top_k=cfg.top_k_nodes)
    extraction = _extraction_yields(world, top_k=cfg.top_k_nodes)
    downtime = _downtime(world, top_k=cfg.top_k_nodes)
    suit_stress = _suit_stress(world)
    need_information, frontier = _information_signal(world, shortages)

    candidate_nodes = _candidate_nodes(
        survey,
        extraction=extraction,
        blocked=blocked,
        shortages=shortages,
        frontier=frontier,
        top_k=cfg.top_k_nodes,
    )

    signals = {
        "survey": survey,
        "shortages": shortages,
        "extraction": extraction,
        "blocked": blocked,
        "downtime": downtime,
        "suit_stress": suit_stress,
        "need_information": need_information,
        "origin_node": None,
    }

    actions: list[PlannedAction] = []
    for node_id in candidate_nodes:
        depot_score = _score_depot(node_id, cfg=cfg, signals=signals)
        actions.append(
            PlannedAction(
                kind="BUILD_DEPOT",
                target_node_id=node_id,
                facility_kind=FacilityKind.DEPOT.value,
                payload={},
                score=depot_score,
            )
        )

        workshop_score = _score_workshop(node_id, cfg=cfg, signals=signals)
        actions.append(
            PlannedAction(
                kind="BUILD_WORKSHOP",
                target_node_id=node_id,
                facility_kind=FacilityKind.WORKSHOP.value,
                payload={},
                score=workshop_score,
            )
        )

        recycler_score = _score_recycler(node_id, cfg=cfg, signals=signals)
        actions.append(
            PlannedAction(
                kind="BUILD_RECYCLER",
                target_node_id=node_id,
                facility_kind=FacilityKind.RECYCLER.value,
                payload={},
                score=recycler_score,
            )
        )

    if need_information:
        for node_id in frontier:
            scout_score = _score_scout(node_id, cfg=cfg, signals=signals)
            actions.append(
                PlannedAction(
                    kind="SCHEDULE_SCOUT_MISSION",
                    target_node_id=node_id,
                    facility_kind=None,
                    payload={"node_id": node_id},
                    score=scout_score,
                )
            )

    actions.sort(
        key=lambda action: (
            -action.score.total,
            _ACTION_ORDER.index(action.kind) if action.kind in _ACTION_ORDER else len(_ACTION_ORDER),
            action.target_node_id or "",
        )
    )
    actions = [action for action in actions if action.score.total > 0][: cfg.top_k_actions]

    max_actions = max(1, cfg.max_actions_per_day)
    selected = actions[:max_actions]

    created = _apply_actions(world, selected)

    metrics = _stable_metrics(world)
    metrics["actions_considered"] = metrics.get("actions_considered", 0) + len(actions)
    metrics["actions_taken"] = metrics.get("actions_taken", 0) + len(selected)
    for action in selected:
        key = action.kind.lower()
        metrics[key] = metrics.get(key, 0) + 1

    state.actions_taken_today = len(selected)
    if selected:
        state.last_action_day = day
        state.last_plan_signature = _hash_plan(selected, salt=cfg.deterministic_salt)

    return created


__all__ = [
    "ExpansionPlannerV2Config",
    "ExpansionPlannerV2State",
    "ScoreBreakdown",
    "PlannedAction",
    "maybe_plan_expansion_v2",
]
