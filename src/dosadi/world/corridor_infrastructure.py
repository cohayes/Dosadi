"""Corridor infrastructure improvements (D-RUNTIME-0267).

This module stores per-edge improvement state and provides helper
functions for routing, wear, and interdiction effects. A lightweight
planner proposes deterministic upgrade projects that flow through the
existing construction pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Mapping, MutableMapping, TYPE_CHECKING

from dosadi.runtime.corridor_risk import CorridorRiskLedger, hot_edges
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.world.materials import Material

if TYPE_CHECKING:  # pragma: no cover - typing only
    from dosadi.world.construction import ConstructionProject, ProjectLedger


@dataclass(slots=True)
class CorridorInfraConfig:
    enabled: bool = False
    max_candidates_per_day: int = 25
    max_projects_spawned_per_day: int = 2
    upgrade_cooldown_days: int = 14
    deterministic_salt: str = "corridor-infra-v1"


@dataclass(slots=True)
class CorridorInfraEdge:
    edge_key: str
    level: int = 0
    last_upgrade_day: int = -1
    tags: set[str] = field(default_factory=set)
    notes: dict[str, object] = field(default_factory=dict)


def ensure_infra_config(world) -> CorridorInfraConfig:
    cfg: CorridorInfraConfig | None = getattr(world, "infra_cfg", None)
    if not isinstance(cfg, CorridorInfraConfig):
        cfg = CorridorInfraConfig()
        world.infra_cfg = cfg
    return cfg


def ensure_infra_edges(world) -> MutableMapping[str, CorridorInfraEdge]:
    edges: MutableMapping[str, CorridorInfraEdge] = getattr(world, "infra_edges", None) or {}
    world.infra_edges = edges
    return edges


def _infra_metrics(world) -> MutableMapping[str, object]:
    metrics = ensure_metrics(world)
    bucket = metrics.gauges.get("infra")
    if not isinstance(bucket, dict):
        bucket = {}
        metrics.gauges["infra"] = bucket
    return bucket  # type: ignore[return-value]


def _clamp_level(level: int) -> int:
    return max(0, min(2, int(level)))


def edge_record(world, edge_key: str) -> CorridorInfraEdge:
    edges = ensure_infra_edges(world)
    rec = edges.get(edge_key)
    if rec is None:
        rec = CorridorInfraEdge(edge_key=edge_key)
        edges[edge_key] = rec
    rec.level = _clamp_level(rec.level)
    return rec


def level_for_edge(world, edge_key: str) -> int:
    rec = edge_record(world, edge_key)
    return _clamp_level(getattr(rec, "level", 0))


def travel_time_multiplier(level: int) -> float:
    mapping = {0: 1.0, 1: 0.9, 2: 0.75}
    return mapping.get(_clamp_level(level), 1.0)


def suit_wear_multiplier(level: int) -> float:
    mapping = {0: 1.0, 1: 0.9, 2: 0.8}
    return mapping.get(_clamp_level(level), 1.0)


def predation_multiplier(level: int) -> float:
    mapping = {0: 1.0, 1: 0.85, 2: 0.65}
    return mapping.get(_clamp_level(level), 1.0)


def corridor_upgrade_recipe(from_level: int, to_level: int) -> dict[Material, int]:
    if (from_level, to_level) == (0, 1):
        return {
            Material.SCRAP_METAL: 4,
            Material.FASTENERS: 4,
            Material.FABRIC: 2,
        }
    if (from_level, to_level) == (1, 2):
        return {
            Material.SCRAP_METAL: 6,
            Material.SEALANT: 4,
            Material.FILTER_MEDIA: 3,
            Material.GASKETS: 2,
        }
    return {}


def _is_project_active(project) -> bool:
    from dosadi.world.construction import ProjectStatus

    return project.status not in {ProjectStatus.COMPLETE, ProjectStatus.CANCELED}


def _has_active_upgrade(world, edge_key: str, to_level: int) -> bool:
    from dosadi.world.construction import ConstructionProject, ProjectLedger

    ledger: "ProjectLedger" | None = getattr(world, "projects", None)
    if ledger is None:
        return False
    for project in ledger.projects.values():
        if not isinstance(project, ConstructionProject) or project.kind != "CORRIDOR_UPGRADE":
            continue
        payload = getattr(project, "notes", {}) or {}
        if payload.get("edge_key") == edge_key and payload.get("to_level") == to_level:
            if _is_project_active(project):
                return True
    return False


def _score_edge(ledger: CorridorRiskLedger | None, edge_key: str, level: int) -> float:
    if ledger is None:
        return float(-level)
    rec = ledger.edges.get(edge_key)
    if rec is None:
        return float(-level)
    risk = getattr(rec, "risk", 0.0)
    wear = getattr(rec, "suit_damage_ema", 0.0)
    hazard = getattr(rec, "hazard_prior", 0.0)
    return 1.2 * risk + 0.6 * wear + 0.4 * hazard - 0.25 * level


def _candidate_edges(world, cfg: CorridorInfraConfig, *, ledger: CorridorRiskLedger | None) -> list[str]:
    candidates: list[str] = []
    if ledger is not None:
        candidates.extend(hot_edges(ledger))
        ranked = sorted(ledger.edges.values(), key=lambda rec: (-rec.risk, rec.edge_key))
        candidates.extend(rec.edge_key for rec in ranked)
    seen = set()
    ordered: list[str] = []
    for edge_key in candidates:
        if edge_key in seen:
            continue
        seen.add(edge_key)
        ordered.append(edge_key)
        if len(ordered) >= cfg.max_candidates_per_day:
            break
    return ordered


def run_corridor_improvement_planner(world, *, day: int) -> list[str]:
    from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus

    cfg = ensure_infra_config(world)
    if not getattr(cfg, "enabled", False):
        return []

    ledger: CorridorRiskLedger | None = getattr(world, "risk_ledger", None)
    candidates = _candidate_edges(world, cfg, ledger=ledger)
    edges = ensure_infra_edges(world)

    scored: list[tuple[float, str, int]] = []
    for edge_key in candidates:
        level = _clamp_level(edges.get(edge_key, CorridorInfraEdge(edge_key=edge_key)).level)
        if level >= 2:
            continue
        scored.append((_score_edge(ledger, edge_key, level), edge_key, level))

    scored.sort(key=lambda item: (-round(item[0], 6), item[1]))
    created: list[str] = []
    metrics = _infra_metrics(world)
    tick = getattr(world, "tick", 0)
    ledger_obj: ProjectLedger = getattr(world, "projects", None) or ProjectLedger()
    world.projects = ledger_obj

    for score, edge_key, level in scored:
        if len(created) >= cfg.max_projects_spawned_per_day:
            break
        rec = edge_record(world, edge_key)
        if rec.last_upgrade_day >= 0 and day - rec.last_upgrade_day < cfg.upgrade_cooldown_days:
            continue
        to_level = level + 1
        if _has_active_upgrade(world, edge_key, to_level):
            continue

        bom = corridor_upgrade_recipe(level, to_level)
        project_id = sha256(f"{cfg.deterministic_salt}|{edge_key}|{to_level}".encode("utf-8")).hexdigest()[:16]
        project_id = f"corridor:{project_id}"
        if project_id in ledger_obj.projects and _is_project_active(ledger_obj.projects[project_id]):
            continue
        project = ConstructionProject(
            project_id=project_id,
            site_node_id=edge_key.split("|")[0] if "|" in edge_key else edge_key,
            kind="CORRIDOR_UPGRADE",
            status=ProjectStatus.APPROVED,
            created_tick=tick,
            last_tick=tick,
            cost=ProjectCost(materials=bom, labor_hours=12.0),
            materials_delivered={},
            labor_applied_hours=0.0,
            assigned_agents=[],
            notes={
                "edge_key": edge_key,
                "from_level": level,
                "to_level": to_level,
                "score": round(score, 4),
            },
        )
        ledger_obj.add_project(project)
        created.append(project.project_id)
        metrics["projects_started"] = metrics.get("projects_started", 0.0) + 1.0

    return created


def apply_corridor_upgrade(world, project, *, day: int) -> None:
    if project.kind != "CORRIDOR_UPGRADE":
        return
    edge_key = project.notes.get("edge_key") if isinstance(project.notes, Mapping) else None
    to_level = project.notes.get("to_level") if isinstance(project.notes, Mapping) else None
    if not isinstance(edge_key, str) or not isinstance(to_level, int):
        return
    rec = edge_record(world, edge_key)
    rec.level = _clamp_level(max(rec.level, to_level))
    rec.last_upgrade_day = day
    metrics = _infra_metrics(world)
    metrics["edges_upgraded_total"] = metrics.get("edges_upgraded_total", 0.0) + 1.0
    metrics["projects_done"] = metrics.get("projects_done", 0.0) + 1.0

    events = getattr(world, "runtime_events", None)
    if not isinstance(events, list):
        events = []
    events.append(
        {
            "type": "CORRIDOR_UPGRADE_DONE",
            "edge_key": edge_key,
            "to_level": rec.level,
            "day": day,
        }
    )
    world.runtime_events = events


def travel_time_multiplier_for_edge(world, edge_key: str) -> float:
    cfg = ensure_infra_config(world)
    if not getattr(cfg, "enabled", False):
        return 1.0
    return travel_time_multiplier(level_for_edge(world, edge_key))


def suit_wear_multiplier_for_edge(world, edge_key: str) -> float:
    cfg = ensure_infra_config(world)
    if not getattr(cfg, "enabled", False):
        return 1.0
    return suit_wear_multiplier(level_for_edge(world, edge_key))


def predation_multiplier_for_edge(world, edge_key: str) -> float:
    cfg = ensure_infra_config(world)
    if not getattr(cfg, "enabled", False):
        return 1.0
    return predation_multiplier(level_for_edge(world, edge_key))


__all__ = [
    "CorridorInfraConfig",
    "CorridorInfraEdge",
    "apply_corridor_upgrade",
    "corridor_upgrade_recipe",
    "ensure_infra_config",
    "ensure_infra_edges",
    "level_for_edge",
    "predation_multiplier_for_edge",
    "run_corridor_improvement_planner",
    "suit_wear_multiplier_for_edge",
    "travel_time_multiplier_for_edge",
]
