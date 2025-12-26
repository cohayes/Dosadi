from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import random
from typing import Any, Iterable, Mapping

from dosadi.runtime.institutions import ensure_policy
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.runtime.tech_ladder import has_unlock
from dosadi.world.construction import (
    ConstructionProject,
    ProjectCost,
    ProjectLedger,
    ProjectStatus,
)


@dataclass(slots=True)
class UrbanConfig:
    enabled: bool = False
    update_cadence_days: int = 7
    need_topk: int = 8
    project_topk: int = 8
    deterministic_salt: str = "urban-v1"


@dataclass(slots=True)
class WardUrbanState:
    ward_id: str
    housing_cap: int = 0
    utility_cap: dict[str, int] = field(default_factory=dict)
    civic_cap: dict[str, int] = field(default_factory=dict)
    industry_cap: dict[str, int] = field(default_factory=dict)
    security_cap: dict[str, int] = field(default_factory=dict)
    zoning_bias: dict[str, float] = field(default_factory=dict)
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class WardNeed:
    kind: str
    severity: float
    driver: str = ""


NEED_TO_FACILITIES: Mapping[str, tuple[str, ...]] = {
    "HOUSING": ("HOUSING_BLOCK_L1", "HOUSING_BLOCK_L2"),
    "WATER_UTIL": ("WATER_PLANT_L1", "WATER_PLANT_L2"),
    "AIR_UTIL": ("DEHUMIDIFIER_BANK_L1", "FILTER_PLANT_L2"),
    "WASTE_UTIL": ("WASTE_RECLAIMER_L1",),
    "CLINIC": ("CLINIC_L1",),
    "ADMIN": ("ADMIN_HALL_L1",),
    "REFINERY": ("REFINERY_L1", "REFINERY_L2"),
    "WORKSHOP": ("WORKSHOP_L1", "FAB_SHOP_L2"),
    "GARRISON": ("GARRISON_L2",),
}


FACILITY_CAPACITY_EFFECT: Mapping[str, Mapping[str, int]] = {
    "HOUSING_BLOCK_L1": {"housing": 180},
    "HOUSING_BLOCK_L2": {"housing": 320},
    "WATER_PLANT_L1": {"utility:water": 120},
    "WATER_PLANT_L2": {"utility:water": 220},
    "DEHUMIDIFIER_BANK_L1": {"utility:air": 80},
    "FILTER_PLANT_L2": {"utility:air": 160},
    "WASTE_RECLAIMER_L1": {"utility:waste": 140},
    "CLINIC_L1": {"civic:clinic": 60},
    "ADMIN_HALL_L1": {"civic:admin": 40},
    "REFINERY_L1": {"industry:refinery": 50},
    "REFINERY_L2": {"industry:refinery": 110},
    "WORKSHOP_L1": {"industry:workshop": 45},
    "FAB_SHOP_L2": {"industry:workshop": 100},
    "GARRISON_L2": {"security:garrison": 90},
}


FACILITY_UNLOCKS: Mapping[str, str] = {
    "REFINERY_L2": "unlock:refinery-l2",
    "HOUSING_BLOCK_L2": "unlock:housing-l2",
    "WATER_PLANT_L2": "unlock:water-plant-l2",
    "FILTER_PLANT_L2": "unlock:filter-plant-l2",
    "FAB_SHOP_L2": "unlock:fab-shop-l2",
    "GARRISON_L2": "unlock:garrison-l2",
}


def _stable_rng(world: Any, day: int, salt: str) -> random.Random:
    seed = getattr(world, "seed", 0)
    digest = sha256(f"{seed}:{day}:{salt}".encode("utf-8")).hexdigest()
    return random.Random(int(digest, 16) % (2**32))


def _ensure_urban(world: Any) -> tuple[UrbanConfig, dict[str, WardUrbanState]]:
    cfg = getattr(world, "urban_cfg", None)
    if not isinstance(cfg, UrbanConfig):
        cfg = UrbanConfig()
        world.urban_cfg = cfg

    states = getattr(world, "urban_by_ward", None)
    if states is None or not isinstance(states, dict):
        states = {}
        world.urban_by_ward = states

    return cfg, states


def _metric_bucket(world: Any) -> dict[str, Any]:
    metrics = ensure_metrics(world)
    bucket = metrics.gauges.get("urban")
    if not isinstance(bucket, dict):
        bucket = {}
        metrics.gauges["urban"] = bucket
    return bucket


def _apply_capacity_effect(state: WardUrbanState, facility_kind: str) -> None:
    effect = FACILITY_CAPACITY_EFFECT.get(facility_kind)
    if not effect:
        return
    for key, delta in effect.items():
        if key == "housing":
            state.housing_cap = max(0, int(state.housing_cap + delta))
            continue
        if key.startswith("utility:"):
            util = key.split(":", 1)[1]
            state.utility_cap[util] = int(state.utility_cap.get(util, 0) + delta)
            continue
        if key.startswith("civic:"):
            civic = key.split(":", 1)[1]
            state.civic_cap[civic] = int(state.civic_cap.get(civic, 0) + delta)
            continue
        if key.startswith("industry:"):
            cat = key.split(":", 1)[1]
            state.industry_cap[cat] = int(state.industry_cap.get(cat, 0) + delta)
            continue
        if key.startswith("security:"):
            cat = key.split(":", 1)[1]
            state.security_cap[cat] = int(state.security_cap.get(cat, 0) + delta)


def _sync_completed_projects(world: Any, state: WardUrbanState) -> None:
    ledger: ProjectLedger | None = getattr(world, "projects", None)
    if not isinstance(ledger, ProjectLedger):
        return
    recorded = set()
    if isinstance(state.notes.get("completed_projects"), list):
        recorded.update(str(pid) for pid in state.notes.get("completed_projects", []))
    for project_id, project in ledger.projects.items():
        if project.status != ProjectStatus.COMPLETE or project_id in recorded:
            continue
        _apply_capacity_effect(state, project.kind)
        recorded.add(project_id)
    if recorded:
        state.notes["completed_projects"] = sorted(recorded)


def _need_from_migration(world: Any, ward_id: str) -> Iterable[WardNeed]:
    migration = getattr(world, "migration_by_ward", {}) or {}
    ward_mig = migration.get(ward_id)
    if ward_mig is None:
        return []
    camp = max(0, int(getattr(ward_mig, "camp", 0)))
    displaced = max(0, int(getattr(ward_mig, "displaced", 0)))
    total_pressure = camp + displaced
    if total_pressure <= 0:
        return []
    severity = min(1.0, total_pressure / 1200.0)
    needs: list[WardNeed] = [WardNeed(kind="HOUSING", severity=severity, driver="migration")]
    if camp > 0:
        util_sev = min(1.0, camp / 1500.0)
        needs.append(WardNeed(kind="WATER_UTIL", severity=util_sev, driver="migration"))
        needs.append(WardNeed(kind="AIR_UTIL", severity=0.6 * util_sev, driver="migration"))
    return needs


def _need_from_market(world: Any, ward_id: str) -> Iterable[WardNeed]:
    state = getattr(world, "market_state", None)
    if state is None:
        return []
    signals = getattr(state, "global_signals", {}) or {}
    needs: list[WardNeed] = []
    for material_key, signal in signals.items():
        urgency = float(getattr(signal, "urgency", 0.0) or 0.0)
        if urgency <= 0.1:
            continue
        severity = min(1.0, urgency)
        if material_key in {"SCRAP_METAL", "SEALANT", "FASTENERS", "PLASTICS"}:
            needs.append(WardNeed(kind="REFINERY", severity=severity, driver=material_key))
        if material_key in {"FABRIC", "FILTER_MEDIA", "GASKETS"}:
            needs.append(WardNeed(kind="WORKSHOP", severity=severity * 0.8, driver=material_key))
    return needs


def _need_from_governance(world: Any, ward_id: str) -> Iterable[WardNeed]:
    states = getattr(world, "inst_state_by_ward", {}) or {}
    ward_state = states.get(ward_id)
    if ward_state is None:
        return []
    unrest = float(getattr(ward_state, "unrest", 0.0) or 0.0)
    legitimacy = float(getattr(ward_state, "legitimacy", 0.0) or 0.0)
    civic_pressure = max(unrest - legitimacy * 0.5, 0.0)
    if civic_pressure <= 0:
        return []
    civic_severity = min(1.0, civic_pressure)
    return [
        WardNeed(kind="CLINIC", severity=0.5 * civic_severity, driver="unrest"),
        WardNeed(kind="ADMIN", severity=civic_severity, driver="unrest"),
        WardNeed(kind="GARRISON", severity=0.4 * civic_severity, driver="unrest"),
    ]


def _need_from_risk(world: Any, ward_id: str) -> Iterable[WardNeed]:
    wards = getattr(world, "wards", {}) or {}
    ward = wards.get(ward_id)
    if ward is None:
        return []
    risk_index = max(0.0, float(getattr(ward, "risk_index", 0.0) or 0.0))
    if risk_index <= 0.05:
        return []
    severity = min(1.0, risk_index)
    return [WardNeed(kind="GARRISON", severity=severity, driver="risk")]


def _topk_needs(needs: Iterable[WardNeed], *, k: int) -> list[WardNeed]:
    ordered = sorted(needs, key=lambda n: (-n.severity, n.kind, n.driver))
    return ordered[: max(1, int(k))]


def _bias_for_need(policy: Any, need_kind: str) -> float:
    if policy is None:
        return 0.0
    if need_kind == "HOUSING":
        return float(getattr(policy, "zoning_residential_bias", 0.0) or 0.0)
    if need_kind in {"WATER_UTIL", "AIR_UTIL", "WASTE_UTIL"}:
        return float(getattr(policy, "zoning_residential_bias", 0.0) or 0.0) * 0.5
    if need_kind in {"REFINERY", "WORKSHOP"}:
        return float(getattr(policy, "zoning_industrial_bias", 0.0) or 0.0)
    if need_kind in {"CLINIC", "ADMIN"}:
        return float(getattr(policy, "zoning_civic_bias", 0.0) or 0.0)
    if need_kind == "GARRISON":
        return float(getattr(policy, "zoning_security_bias", 0.0) or 0.0)
    return 0.0


def _passes_gate(world: Any, facility_kind: str) -> bool:
    unlock = FACILITY_UNLOCKS.get(facility_kind)
    if unlock is None:
        return True
    return has_unlock(world, unlock)


def _score_candidate(
    *,
    need: WardNeed,
    facility_kind: str,
    bias: float,
    rng: random.Random,
    heritage: float,
) -> float:
    maintenance_penalty = 0.05 * len(facility_kind)
    heritage_penalty = heritage * 0.1
    noise = rng.random() * 0.0001
    return need.severity + bias - maintenance_penalty - heritage_penalty + noise


def _projects_to_start(
    *,
    world: Any,
    ward_id: str,
    needs: Iterable[WardNeed],
    cfg: UrbanConfig,
    rng: random.Random,
) -> list[ConstructionProject]:
    policy = ensure_policy(world, ward_id)
    heritage = float(getattr(policy, "heritage_preservation", 0.0) or 0.0)
    aggressiveness = float(getattr(policy, "growth_aggressiveness", 0.0) or 0.0)
    ledger: ProjectLedger = getattr(world, "projects", None) or ProjectLedger()
    world.projects = ledger

    candidates: list[tuple[float, str]] = []
    for need in needs:
        for facility in NEED_TO_FACILITIES.get(need.kind, ()):  # type: ignore[arg-type]
            if not _passes_gate(world, facility):
                continue
            bias = _bias_for_need(policy, need.kind)
            score = _score_candidate(
                need=need,
                facility_kind=facility,
                bias=bias,
                rng=rng,
                heritage=heritage,
            )
            candidates.append((score, facility))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    candidates = candidates[: max(1, int(cfg.project_topk))]

    max_projects = 1 + (1 if aggressiveness >= 0.65 else 0)
    projects: list[ConstructionProject] = []
    for _, facility_kind in candidates[:max_projects]:
        project_id = f"urban:{ward_id}:{facility_kind}:{cfg.deterministic_salt}"
        digest = sha256(project_id.encode("utf-8")).hexdigest()[:12]
        project_id = f"proj:{digest}"
        if project_id in ledger.projects:
            continue
        cost = ProjectCost(materials={}, labor_hours=24.0)
        project = ConstructionProject(
            project_id=project_id,
            site_node_id=ward_id,
            kind=facility_kind,
            status=ProjectStatus.APPROVED,
            created_tick=getattr(world, "tick", 0),
            last_tick=getattr(world, "tick", 0),
            cost=cost,
            materials_delivered={},
            labor_applied_hours=0.0,
            assigned_agents=[],
        )
        project.notes["urban_need"] = need.kind
        project.notes["ward_id"] = ward_id
        ledger.add_project(project)
        projects.append(project)
    return projects


def _update_metrics(world: Any, *, projects_started: int) -> None:
    bucket = _metric_bucket(world)
    bucket["projects_started"] = float(bucket.get("projects_started", 0.0) + projects_started)
    cfg, states = _ensure_urban(world)
    migration = getattr(world, "migration_by_ward", {}) or {}
    bucket["housing_cap_total"] = sum(state.housing_cap for state in states.values())
    bucket["camp_total"] = sum(
        max(0, int(getattr(migration.get(wid, None), "camp", 0) or 0)) for wid in states
    )
    bucket["utility_shortfalls"] = float(
        len([state for state in states.values() if any(v <= 0 for v in state.utility_cap.values())])
    )
    if cfg.enabled:
        bucket["cfg_update_cadence_days"] = cfg.update_cadence_days


def run_urban_for_day(world: Any, *, day: int | None = None) -> None:
    cfg, states = _ensure_urban(world)
    if not getattr(cfg, "enabled", False):
        return

    current_day = day if day is not None else getattr(world, "day", 0)
    rng = _stable_rng(world, current_day, cfg.deterministic_salt)
    projects_started = 0

    for ward_id in sorted(getattr(world, "wards", {})):
        state = states.get(ward_id)
        if not isinstance(state, WardUrbanState):
            state = WardUrbanState(ward_id=ward_id)
            states[ward_id] = state

        _sync_completed_projects(world, state)
        if current_day <= state.last_update_day:
            continue
        if current_day % max(1, int(cfg.update_cadence_days)) != 0:
            continue

        needs = list(
            _topk_needs(
                [
                    *_need_from_migration(world, ward_id),
                    *_need_from_market(world, ward_id),
                    *_need_from_governance(world, ward_id),
                    *_need_from_risk(world, ward_id),
                ],
                k=cfg.need_topk,
            )
        )
        if not needs:
            state.last_update_day = current_day
            continue

        projects = _projects_to_start(world=world, ward_id=ward_id, needs=needs, cfg=cfg, rng=rng)
        projects_started += len(projects)
        state.last_update_day = current_day

    _update_metrics(world, projects_started=projects_started)


__all__ = [
    "UrbanConfig",
    "WardUrbanState",
    "WardNeed",
    "run_urban_for_day",
]
