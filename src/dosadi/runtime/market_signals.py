from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.world.construction import ConstructionProject
from dosadi.world.materials import InventoryRegistry, Material, ensure_inventory_registry, material_from_key
from dosadi.world.construction import ProjectLedger
if TYPE_CHECKING:
    from dosadi.runtime.stockpile_policy import DepotPolicyLedger, MaterialThreshold


@dataclass(slots=True)
class MarketSignalsConfig:
    enabled: bool = False
    materials: list[str] = field(
        default_factory=lambda: [
            "SCRAP_METAL",
            "PLASTICS",
            "FASTENERS",
            "SEALANT",
            "FABRIC",
            "FILTER_MEDIA",
            "GASKETS",
        ]
    )
    ema_alpha: float = 0.2
    urgency_floor: float = 0.05
    urgency_ceiling: float = 0.95
    max_materials_tracked: int = 64
    ward_signals_enabled: bool = False
    max_wards_tracked: int = 12
    deterministic_salt: str = "market-v1"


@dataclass(slots=True)
class MaterialMarketSignal:
    material: str
    urgency: float = 0.0
    demand_score: float = 0.0
    supply_score: float = 0.0
    last_updated_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class MarketSignalsState:
    last_run_day: int = -1
    global_signals: dict[str, MaterialMarketSignal] = field(default_factory=dict)
    ward_signals: dict[str, dict[str, MaterialMarketSignal]] = field(default_factory=dict)


def _ensure_market_config(world: Any) -> MarketSignalsConfig:
    cfg = getattr(world, "market_cfg", None)
    if isinstance(cfg, MarketSignalsConfig):
        return cfg
    cfg = MarketSignalsConfig()
    world.market_cfg = cfg
    return cfg


def _ensure_market_state(world: Any) -> MarketSignalsState:
    state = getattr(world, "market_state", None)
    if isinstance(state, MarketSignalsState):
        return state
    state = MarketSignalsState()
    world.market_state = state
    return state


def _normalized_materials(cfg: MarketSignalsConfig) -> list[str]:
    materials = [str(mat) for mat in cfg.materials][: max(1, int(cfg.max_materials_tracked))]
    return sorted(set(materials))


def _construction_demand(world: Any, registry: InventoryRegistry) -> dict[str, float]:
    ledger: ProjectLedger | None = getattr(world, "projects", None)
    if not isinstance(ledger, ProjectLedger):
        return {}
    demand: dict[str, float] = {}
    for project_id, project in list(sorted(ledger.projects.items()))[:25]:
        if not isinstance(project, ConstructionProject):
            continue
        bom = getattr(project, "bom", None) or getattr(getattr(project, "cost", None), "materials", {})
        owner_id = getattr(project, "staging_owner_id", f"project:{project_id}")
        inv = registry.inv(owner_id)
        for mat_key, qty in bom.items():
            material = material_from_key(mat_key) if isinstance(mat_key, str) else mat_key
            if not isinstance(material, Material):
                continue
            missing = max(0, int(qty) - inv.get(material))
            if missing > 0:
                demand[material.name] = demand.get(material.name, 0.0) + float(missing)
    return demand


def _stockpile_demand(world: Any, registry: InventoryRegistry) -> dict[str, float]:
    from dosadi.runtime import stockpile_policy as sp

    ledger = getattr(world, "stock_policies", None)
    depot_cls = getattr(sp, "DepotPolicyLedger", None)
    if depot_cls is None or not isinstance(ledger, depot_cls):
        return {}
    profile_ledger: Mapping[str, Any] = getattr(ledger, "profiles", {})
    thresholds_func = getattr(sp, "default_thresholds", lambda: {})

    demand: dict[str, float] = {}
    for depot_id, profile in list(sorted(profile_ledger.items()))[:25]:
        thresholds: Mapping[str, Any] = getattr(profile, "thresholds", {})
        for mat_name, threshold in thresholds.items():
            material = material_from_key(mat_name)
            if material is None:
                continue
            inv = registry.inv(f"facility:{depot_id}")
            deficit = max(0, getattr(threshold, "target_level", 0) - inv.get(material))
            if deficit > 0:
                demand[material.name] = demand.get(material.name, 0.0) + float(deficit)

        for mat_name, threshold in thresholds_func().items():
            if mat_name in thresholds:
                continue
            material = material_from_key(mat_name)
            if material is None:
                continue
            inv = registry.inv(f"facility:{depot_id}")
            deficit = max(0, getattr(threshold, "target_level", 0) - inv.get(material))
            if deficit > 0:
                demand[material.name] = demand.get(material.name, 0.0) + float(deficit)
    return demand


def _production_supply(world: Any) -> dict[str, float]:
    telemetry = ensure_metrics(world)
    prod_metrics = telemetry.gauges.get("production", {})
    if not isinstance(prod_metrics, Mapping):
        return {}
    outputs = prod_metrics.get("outputs") if isinstance(prod_metrics, Mapping) else None
    if not isinstance(outputs, Mapping):
        return {}
    return {str(mat): float(qty) for mat, qty in outputs.items()}


def _squash(raw: float) -> float:
    if raw <= 0:
        return 0.0
    return raw / (raw + 1.0)


def _update_signal(signal: MaterialMarketSignal, *, demand: float, supply: float, day: int, cfg: MarketSignalsConfig) -> None:
    raw = demand / (supply + 1e-6)
    u_raw = _squash(raw)
    urgency = cfg.ema_alpha * u_raw + (1.0 - cfg.ema_alpha) * signal.urgency
    urgency = max(cfg.urgency_floor, min(cfg.urgency_ceiling, urgency))
    signal.urgency = urgency
    signal.demand_score = demand
    signal.supply_score = supply
    signal.last_updated_day = day


def current_signal_urgency(world: Any, material: str) -> float:
    state = getattr(world, "market_state", None)
    if not isinstance(state, MarketSignalsState):
        return 0.0
    signal = state.global_signals.get(material)
    if not isinstance(signal, MaterialMarketSignal):
        return 0.0
    return float(signal.urgency)


def run_market_signals_for_day(world, *, day: int) -> None:
    cfg = _ensure_market_config(world)
    if not cfg.enabled:
        return

    state = _ensure_market_state(world)
    registry = ensure_inventory_registry(world)
    demand_scores: dict[str, float] = {}
    supply_scores: dict[str, float] = {}

    for mat, score in _construction_demand(world, registry).items():
        demand_scores[mat] = demand_scores.get(mat, 0.0) + score
    for mat, score in _stockpile_demand(world, registry).items():
        demand_scores[mat] = demand_scores.get(mat, 0.0) + score
    for mat, score in _production_supply(world).items():
        supply_scores[mat] = supply_scores.get(mat, 0.0) + score

    tracked_materials = set(_normalized_materials(cfg))
    tracked_materials.update(demand_scores.keys())
    tracked_materials.update(supply_scores.keys())
    tracked_list = sorted(list(tracked_materials))[: max(1, int(cfg.max_materials_tracked))]

    metrics = ensure_metrics(world)
    metrics.inc("market.updates", 1.0)

    for material in tracked_list:
        signal = state.global_signals.get(material)
        if signal is None:
            signal = MaterialMarketSignal(material=material)
            state.global_signals[material] = signal
        demand = demand_scores.get(material, 0.0)
        supply = supply_scores.get(material, 0.0)
        _update_signal(signal, demand=demand, supply=supply, day=day, cfg=cfg)
        metrics.topk_add(
            "market.urgent",
            material,
            signal.urgency,
            payload={"demand": demand, "supply": supply},
        )
        record_event(
            world,
            {
                "type": "MARKET_SIGNAL_UPDATED",
                "material": material,
                "urgency": signal.urgency,
                "demand": demand,
                "supply": supply,
                "day": day,
            },
        )

    state.last_run_day = day
    world.market_state = state

