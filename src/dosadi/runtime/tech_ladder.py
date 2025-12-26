from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Iterable, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.runtime.ledger import ensure_ledger_config, ensure_ledger_state, post_tx
from dosadi.world.materials import Material, InventoryRegistry, ensure_inventory_registry


@dataclass(frozen=True, slots=True)
class TechProjectSpec:
    tech_id: str
    name: str
    prereqs: tuple[str, ...]
    cost_materials: dict[Material, int]
    cost_labor_days: int
    duration_days: int
    unlocks: tuple[str, ...]
    tags: tuple[str, ...] = ()


@dataclass(slots=True)
class TechConfig:
    enabled: bool = False
    max_projects_active: int = 3
    max_projects_started_per_day: int = 1
    deterministic_salt: str = "tech-v1"


@dataclass(slots=True)
class ActiveTechProject:
    tech_id: str
    started_day: int
    complete_day: int
    sponsor_faction_id: str | None = None
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class TechState:
    unlocked: set[str] = field(default_factory=set)
    completed: set[str] = field(default_factory=set)
    active: dict[str, ActiveTechProject] = field(default_factory=dict)
    last_run_day: int = -1


def _spec(
    *,
    tech_id: str,
    name: str,
    prereqs: Iterable[str] | None = None,
    cost_materials: Mapping[Material, int] | None = None,
    cost_labor_days: int = 0,
    duration_days: int = 7,
    unlocks: Iterable[str],
    tags: Iterable[str] | None = None,
) -> TechProjectSpec:
    return TechProjectSpec(
        tech_id=tech_id,
        name=name,
        prereqs=tuple(prereqs or ()),
        cost_materials=dict(cost_materials or {}),
        cost_labor_days=int(cost_labor_days),
        duration_days=int(duration_days),
        unlocks=tuple(unlocks),
        tags=tuple(tags or ()),
    )


def tech_registry() -> dict[str, TechProjectSpec]:
    projects = [
        _spec(
            tech_id="tech:recycler:t1",
            name="Recycler Basics",
            cost_materials={Material.SCRAP_INPUT: 8},
            cost_labor_days=2,
            duration_days=4,
            unlocks=("UNLOCK_RECYCLER_RECIPES_T1",),
        ),
        _spec(
            tech_id="tech:workshop:parts:t2",
            name="Workshop Fasteners",
            prereqs=("tech:recycler:t1",),
            cost_materials={Material.SCRAP_METAL: 6, Material.FASTENERS: 1},
            cost_labor_days=3,
            duration_days=5,
            unlocks=("UNLOCK_WORKSHOP_PARTS_T2",),
            tags=("industry",),
        ),
        _spec(
            tech_id="tech:chem:sealants:t2",
            name="Sealants",
            prereqs=("tech:recycler:t1",),
            cost_materials={Material.CHEM_SALTS: 4, Material.FIBER: 2},
            cost_labor_days=3,
            duration_days=5,
            unlocks=("UNLOCK_CHEM_SEALANTS_T2",),
            tags=("industry",),
        ),
        _spec(
            tech_id="tech:suits:repairkit:t1",
            name="Suit Repair Kits",
            cost_materials={Material.FABRIC: 4, Material.SEALANT: 2},
            cost_labor_days=2,
            duration_days=4,
            unlocks=("UNLOCK_SUIT_REPAIR_KIT_T1",),
            tags=("suits",),
        ),
        _spec(
            tech_id="tech:suits:seals:t2",
            name="Suit Seals",
            prereqs=("tech:suits:repairkit:t1", "tech:chem:sealants:t2"),
            cost_materials={Material.SEALANT: 3, Material.GASKETS: 2},
            cost_labor_days=2,
            duration_days=6,
            unlocks=("UNLOCK_SUIT_SEALS_T2",),
            tags=("suits",),
        ),
        _spec(
            tech_id="tech:corridor:l2",
            name="Corridor Upgrade",
            prereqs=("tech:workshop:parts:t2",),
            cost_materials={Material.FASTENERS: 4, Material.SEALANT: 2, Material.FILTER_MEDIA: 2},
            cost_labor_days=4,
            duration_days=7,
            unlocks=("UNLOCK_CORRIDOR_L2",),
            tags=("corridor",),
        ),
        _spec(
            tech_id="tech:fab:simple:t3",
            name="Basic Fabrication",
            prereqs=("tech:workshop:parts:t2", "tech:chem:sealants:t2"),
            cost_materials={
                Material.METAL_PLATE: 2,
                Material.SEALANT: 2,
                Material.FITTINGS: 2,
            },
            cost_labor_days=4,
            duration_days=8,
            unlocks=("UNLOCK_FABRICATION_SIMPLE_T3",),
            tags=("fabrication",),
        ),
    ]
    return {spec.tech_id: spec for spec in projects}


def _stable_hash(values: Iterable[str], *, salt: str) -> float:
    digest = sha256((salt + "|".join(sorted(values))).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / float(0xFFFFFFFF)


def _pressure_scores(world) -> dict[str, float]:
    registry: InventoryRegistry = ensure_inventory_registry(world)
    priorities: dict[str, float] = {}
    thresholds = getattr(getattr(world, "stock_policies", None), "profiles", {}) or {}
    for depot_id, profile in sorted(thresholds.items()):
        inv = registry.inv(f"facility:{depot_id}")
        for mat_key, threshold in sorted(getattr(profile, "thresholds", {}).items()):
            material = getattr(mat_key, "material", None) or getattr(mat_key, "key", mat_key)
            if hasattr(material, "value"):
                material = material.value
            if isinstance(material, Material):
                mat = material
            else:
                mat = Material[material] if isinstance(material, str) and material in Material.__members__ else None
            if mat is None:
                continue
            deficit = max(0, getattr(threshold, "target_level", 0) - inv.get(mat))
            if deficit <= 0:
                continue
            priorities[mat.name] = max(priorities.get(mat.name, 0.0), float(deficit))
    return priorities


def _score_project(spec: TechProjectSpec, priorities: Mapping[str, float]) -> float:
    score = sum(priorities.get(tag, 0.0) for tag in spec.unlocks)
    if spec.prereqs:
        score += 0.01 * len(spec.prereqs)
    score += 0.001 * len(spec.tags)
    return score


def _owner_for_research(world) -> str:
    return getattr(world, "research_owner_id", "owner:state:research")


def _emit_metric(world, key: str, value: object) -> None:
    metrics = ensure_metrics(world)
    bucket = metrics.gauges.setdefault("tech", {})
    if isinstance(bucket, dict):
        bucket[key] = value


def run_tech_for_day(world, *, day: int) -> None:
    cfg_obj = getattr(world, "tech_cfg", None)
    cfg: TechConfig = cfg_obj if isinstance(cfg_obj, TechConfig) else TechConfig()
    state_obj = getattr(world, "tech_state", None)
    state: TechState = state_obj if isinstance(state_obj, TechState) else TechState()

    world.tech_cfg = cfg
    world.tech_state = state

    if not cfg.enabled:
        return

    ledger_cfg = ensure_ledger_config(world)
    ledger_state = ensure_ledger_state(world) if ledger_cfg.enabled else None

    registry = tech_registry()
    priorities = _pressure_scores(world)
    inventory = ensure_inventory_registry(world)

    sponsor_policies = getattr(world, "inst_policy_by_ward", {}) or {}
    sponsor_candidates = [
        (float(getattr(policy, "research_budget_points", 0.0)), ward_id)
        for ward_id, policy in sorted(sponsor_policies.items())
    ]
    sponsor_candidates.sort(key=lambda item: (-round(item[0], 6), item[1]))

    # Complete finished projects
    for tech_id, active in sorted(list(state.active.items())):
        if active.complete_day > day:
            continue
        state.completed.add(tech_id)
        spec = registry.get(tech_id)
        if spec:
            state.unlocked.update(spec.unlocks)
        state.active.pop(tech_id, None)
        record_event(world, {"type": "TECH_COMPLETED", "tech_id": tech_id, "day": day})

    started_today = 0
    if state.last_run_day == day:
        return

    available_slots = max(0, cfg.max_projects_active - len(state.active))
    candidates: list[TechProjectSpec] = []
    for tech_id, spec in sorted(registry.items()):
        if tech_id in state.completed or tech_id in state.active:
            continue
        if any(prereq not in state.completed for prereq in spec.prereqs):
            continue
        candidates.append(spec)

    candidates.sort(key=lambda spec: (-_score_project(spec, priorities), spec.tech_id))

    for spec in candidates:
        if available_slots <= 0 or started_today >= cfg.max_projects_started_per_day:
            break
        if spec.tech_id in state.completed or spec.tech_id in state.active:
            continue
        if not inventory.inv(_owner_for_research(world)).can_afford(spec.cost_materials):
            continue
        if ledger_cfg.enabled:
            sponsor_budget, sponsor_ward = (sponsor_candidates[0] if sponsor_candidates else (0.0, None))
            if sponsor_budget <= 0.0 or sponsor_ward is None:
                continue
            prev_len = len(ledger_state.txs) if ledger_state is not None else 0
            posted = post_tx(
                world,
                day=day,
                from_acct=f"acct:ward:{sponsor_ward}",
                to_acct="acct:state:treasury",
                amount=sponsor_budget,
                reason="PAY_RESEARCH",
                meta={"tech_id": spec.tech_id},
            )
            if not posted or (ledger_state is not None and len(ledger_state.txs) <= prev_len):
                continue
        inventory.inv(_owner_for_research(world)).apply_bom(spec.cost_materials)
        complete_day = day + max(1, int(spec.duration_days))
        state.active[spec.tech_id] = ActiveTechProject(
            tech_id=spec.tech_id,
            started_day=day,
            complete_day=complete_day,
        )
        started_today += 1
        record_event(
            world,
            {
                "type": "TECH_STARTED",
                "tech_id": spec.tech_id,
                "complete_day": complete_day,
                "cost_materials": {mat.name: qty for mat, qty in spec.cost_materials.items()},
            },
        )

    state.last_run_day = day
    _emit_metric(world, "completed", len(state.completed))
    _emit_metric(world, "active", len(state.active))
    _emit_metric(world, "started", started_today)


def tech_seed_payload(state: TechState) -> dict[str, list[str]]:
    return {
        "completed": sorted(state.completed),
        "unlocked": sorted(state.unlocked),
        "active": sorted(state.active),
    }


def has_unlock(world, tag: str) -> bool:
    cfg = getattr(world, "tech_cfg", None)
    state = getattr(world, "tech_state", None)
    if not isinstance(cfg, TechConfig) or not cfg.enabled:
        return True
    unlocked = state.unlocked if isinstance(state, TechState) else set()
    return tag in unlocked


__all__ = [
    "ActiveTechProject",
    "TechConfig",
    "TechProjectSpec",
    "TechState",
    "has_unlock",
    "run_tech_for_day",
    "tech_registry",
    "tech_seed_payload",
]
