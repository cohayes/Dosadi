from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, MutableMapping

from dosadi.runtime.telemetry import ensure_metrics
from dosadi.world.facilities import FacilityKind, ensure_facility_ledger
from dosadi.world.incidents import IncidentLedger

KPI_SCHEMA_VERSION = "1.0"
MAX_EVIDENCE_ITEMS = 8


@dataclass(frozen=True, slots=True)
class KPIKey:
    name: str
    dtype: str
    description: str
    unit: str | None = None


@dataclass(slots=True)
class KPIValue:
    value: float = 0.0
    updated_tick: int = -1
    evidence: list[dict] = field(default_factory=list)

    def update(self, value: float, tick: int, *, evidence: Iterable[Mapping[str, object]] | None = None) -> None:
        self.value = float(value)
        self.updated_tick = int(tick)
        if evidence:
            for item in evidence:
                self.evidence.append(dict(item))
            if len(self.evidence) > MAX_EVIDENCE_ITEMS:
                self.evidence = self.evidence[-MAX_EVIDENCE_ITEMS:]


@dataclass(slots=True)
class KPIStore:
    schema_version: str = KPI_SCHEMA_VERSION
    values: dict[str, KPIValue] = field(default_factory=dict)

    def ensure_key(self, key: KPIKey, *, tick: int) -> KPIValue:
        if key.name not in self.values:
            self.values[key.name] = KPIValue(updated_tick=int(tick))
        return self.values[key.name]


def _schema() -> dict[str, KPIKey]:
    keys: list[KPIKey] = [
        KPIKey("progress.tick", "int", "Current tick"),
        KPIKey("progress.day", "int", "Current day"),
        KPIKey("progress.phase_id", "int", "Current phase identifier"),
        KPIKey("progress.milestones_achieved", "int", "Number of milestones achieved"),
        KPIKey("progress.no_progress_ticks", "int", "Ticks since last progress change"),
        KPIKey("logistics.depots_built", "int", "Depots constructed"),
        KPIKey("logistics.routes_active", "int", "Active logistics routes"),
        KPIKey("logistics.corridors_established", "int", "Corridors established"),
        KPIKey("logistics.deliveries_completed", "int", "Successful deliveries"),
        KPIKey("logistics.delivery_success_rate", "float", "Success ratio for deliveries"),
        KPIKey("logistics.avg_delivery_time_days", "float", "Average delivery duration (days)", unit="days"),
        KPIKey("governance.council_formed", "bool", "Council has been formed"),
        KPIKey("governance.protocols_authored", "int", "Protocols authored"),
        KPIKey("governance.enforcement_actions", "int", "Enforcement actions taken"),
        KPIKey("governance.legitimacy_proc", "float", "Legitimacy proxy"),
        KPIKey("safety.incidents_total", "int", "Total incidents"),
        KPIKey("safety.injuries_total", "int", "Total injuries"),
        KPIKey("safety.deaths_total", "int", "Total deaths"),
        KPIKey("safety.population_alive_ratio", "float", "Alive population ratio"),
        KPIKey("economy.water_shortage_severe_days", "int", "Severe shortage days"),
        KPIKey("economy.avg_ration_level", "float", "Average ration level", unit="ratio"),
        KPIKey("performance.ticks_simulated", "int", "Ticks simulated"),
        KPIKey("performance.microsteps", "int", "Microsteps executed"),
        KPIKey("performance.timewarp_steps", "int", "Timewarp steps executed"),
        KPIKey("performance.step_ms_p50", "float", "Step p50 runtime", unit="ms"),
        KPIKey("performance.step_ms_p95", "float", "Step p95 runtime", unit="ms"),
    ]
    return {key.name: key for key in keys}


SCHEMA = _schema()


def ensure_kpi_store(world: Any) -> KPIStore:
    store = getattr(world, "kpis", None)
    if isinstance(store, KPIStore):
        return store
    store = KPIStore()
    world.kpis = store
    return store


def _ticks_per_day(world: Any) -> int:
    ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(world, "ticks_per_day", 144_000)
    try:
        return max(1, int(ticks_per_day))
    except Exception:
        return 144_000


def _set(store: KPIStore, name: str, value: float, tick: int) -> None:
    key = SCHEMA.get(name)
    if key is None:
        return
    store.ensure_key(key, tick=tick).update(value, tick)


def _count_agents(world: Any) -> tuple[int, int]:
    agents = getattr(world, "agents", {}) or {}
    if isinstance(agents, Mapping):
        agent_iter = agents.values()
    else:
        agent_iter = agents
    total = 0
    alive = 0
    for agent in agent_iter:
        total += 1
        physical = getattr(agent, "physical", agent)
        is_alive = getattr(physical, "is_alive", getattr(agent, "is_alive", True))
        alive += 1 if is_alive else 0
    return total, alive


def _from_metrics(metrics: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    if hasattr(metrics, "counters"):
        counters = getattr(metrics, "counters", {}) or {}
        if key in counters:
            return float(counters.get(key, default))
    if hasattr(metrics, "gauges"):
        gauges = getattr(metrics, "gauges", {}) or {}
        if key in gauges:
            try:
                return float(gauges.get(key, default))
            except Exception:
                return default
    if hasattr(metrics, "legacy"):
        legacy = getattr(metrics, "legacy", {}) or {}
        if key in legacy:
            try:
                return float(legacy.get(key, default))
            except Exception:
                return default
    try:
        value = metrics.get(key, default)  # type: ignore[arg-type]
        return float(value)
    except Exception:
        return default


def kpi_from_legacy_metrics(metrics: Mapping[str, Any]) -> dict[str, float]:
    mapping = {
        "depots_built": "logistics.depots_built",
        "deliveries_completed": "logistics.deliveries_completed",
        "routes_active": "logistics.routes_active",
        "corridors_established": "logistics.corridors_established",
        "incidents_total": "safety.incidents_total",
        "injuries_total": "safety.injuries_total",
        "deaths_total": "safety.deaths_total",
        "water_shortage_severe_days": "economy.water_shortage_severe_days",
    }
    translated: dict[str, float] = {}
    for legacy_key, kpi_key in mapping.items():
        translated[kpi_key] = _from_metrics(metrics, legacy_key, 0.0)
    return translated


def _update_progress_kpis(world: Any, store: KPIStore, tick: int) -> None:
    ticks_per_day = _ticks_per_day(world)
    day = getattr(world, "day", int(tick) // ticks_per_day)
    _set(store, "progress.tick", tick, tick)
    _set(store, "progress.day", day, tick)
    phase_id = getattr(getattr(world, "phase_state", None), "current_phase", None)
    phase_value = int(getattr(phase_id, "value", phase_id or 0)) if phase_id is not None else 0
    _set(store, "progress.phase_id", phase_value, tick)
    milestones = getattr(getattr(world, "active_contract", None), "milestones", []) or []
    achieved = 0
    for milestone in milestones:
        status = getattr(milestone, "status", None)
        status_value = getattr(status, "value", None)
        status_str = str(status)
        if status_value == "ACHIEVED" or status_str.endswith("ACHIEVED"):
            achieved += 1
    _set(store, "progress.milestones_achieved", achieved, tick)
    _set(store, "progress.no_progress_ticks", getattr(world, "no_progress_ticks", 0), tick)


def _update_logistics_kpis(world: Any, store: KPIStore, tick: int) -> None:
    facilities = ensure_facility_ledger(world)
    depots = len(facilities.list_by_kind(FacilityKind.DEPOT)) if facilities else 0
    _set(store, "logistics.depots_built", depots, tick)
    routes = getattr(world, "routes", {}) or {}
    route_count = len(routes) if hasattr(routes, "__len__") else 0
    _set(store, "logistics.routes_active", route_count, tick)
    corridors = getattr(world, "infra_edges", {}) or {}
    corridor_count = len(corridors) if hasattr(corridors, "__len__") else route_count
    _set(store, "logistics.corridors_established", corridor_count, tick)

    metrics = ensure_metrics(world)
    deliveries_completed = _from_metrics(metrics, "stockpile.deliveries_completed", 0.0)
    deliveries_failed = _from_metrics(metrics, "stockpile.deliveries_failed", 0.0)
    deliveries_requested = _from_metrics(metrics, "stockpile.deliveries_requested", deliveries_completed + deliveries_failed)
    _set(store, "logistics.deliveries_completed", deliveries_completed, tick)
    denom = deliveries_requested if deliveries_requested > 0 else deliveries_completed + deliveries_failed
    success_rate = 0.0 if denom <= 0 else deliveries_completed / max(1.0, denom)
    _set(store, "logistics.delivery_success_rate", success_rate, tick)
    avg_duration = _from_metrics(metrics, "stockpile.avg_delivery_time_days", 0.0)
    _set(store, "logistics.avg_delivery_time_days", avg_duration, tick)


def _update_governance_kpis(world: Any, store: KPIStore, tick: int) -> None:
    groups = getattr(world, "groups", []) or []
    council_present = any(str(getattr(g, "group_type", getattr(g, "type", ""))) in {"COUNCIL", "GroupType.COUNCIL"} for g in groups)
    _set(store, "governance.council_formed", 1.0 if council_present else 0.0, tick)
    registry = getattr(world, "protocols", None)
    protocol_values: Iterable = getattr(registry, "protocols_by_id", {}) or {}
    if isinstance(protocol_values, Mapping):
        protocol_count = len(protocol_values)
    else:
        try:
            protocol_count = len(list(protocol_values))
        except Exception:
            protocol_count = 0
    _set(store, "governance.protocols_authored", protocol_count, tick)
    metrics = ensure_metrics(world)
    enforcement = _from_metrics(metrics, "governance.enforcement_actions", 0.0)
    _set(store, "governance.enforcement_actions", enforcement, tick)
    legitimacy = _from_metrics(metrics, "governance.legitimacy", 0.0)
    _set(store, "governance.legitimacy_proc", legitimacy, tick)


def _update_safety_kpis(world: Any, store: KPIStore, tick: int) -> None:
    ledger: IncidentLedger | None = getattr(world, "incidents", None)
    history_count = len(getattr(ledger, "history", []) or []) if isinstance(ledger, IncidentLedger) else 0
    metrics = ensure_metrics(world)
    incidents_total = max(history_count, _from_metrics(metrics, "incidents_total", 0.0))
    _set(store, "safety.incidents_total", incidents_total, tick)
    injuries_total = _from_metrics(metrics, "injuries_total", 0.0)
    deaths_total = _from_metrics(metrics, "deaths_total", 0.0)
    _set(store, "safety.injuries_total", injuries_total, tick)
    _set(store, "safety.deaths_total", deaths_total, tick)
    total, alive = _count_agents(world)
    ratio = 1.0 if total == 0 else alive / max(1, total)
    _set(store, "safety.population_alive_ratio", ratio, tick)


def _update_economy_kpis(world: Any, store: KPIStore, tick: int) -> None:
    metrics = ensure_metrics(world)
    shortage_days = _from_metrics(metrics, "stockpile.shortages", 0.0)
    _set(store, "economy.water_shortage_severe_days", shortage_days, tick)
    avg_ration = _from_metrics(metrics, "economy.avg_ration_level", 0.0)
    _set(store, "economy.avg_ration_level", avg_ration, tick)


def _update_performance_kpis(world: Any, store: KPIStore, tick: int) -> None:
    _set(store, "performance.ticks_simulated", tick, tick)
    metrics = ensure_metrics(world)
    _set(store, "performance.microsteps", _from_metrics(metrics, "runtime.microsteps", 0.0), tick)
    _set(store, "performance.timewarp_steps", _from_metrics(metrics, "runtime.timewarp_steps", 0.0), tick)
    _set(store, "performance.step_ms_p50", _from_metrics(metrics, "runtime.step_ms_p50", 0.0), tick)
    _set(store, "performance.step_ms_p95", _from_metrics(metrics, "runtime.step_ms_p95", 0.0), tick)


def update_kpis(world: Any, tick: int, *, mode: str = "micro") -> KPIStore:
    store = ensure_kpi_store(world)
    for key in SCHEMA.values():
        store.ensure_key(key, tick=tick)

    _update_progress_kpis(world, store, tick)
    _update_logistics_kpis(world, store, tick)
    _update_governance_kpis(world, store, tick)
    _update_safety_kpis(world, store, tick)
    _update_economy_kpis(world, store, tick)
    _update_performance_kpis(world, store, tick)

    metrics = ensure_metrics(world)
    for name, value in kpi_from_legacy_metrics(metrics).items():
        _set(store, name, max(value, store.values.get(name, KPIValue()).value), tick)

    return store


def flatten_kpis_for_report(store: KPIStore | None) -> dict[str, float]:
    if store is None:
        return {}
    report = {name: float(value.value) for name, value in sorted(store.values.items())}
    report["schema_version"] = store.schema_version
    return report


__all__ = [
    "KPIKey",
    "KPIStore",
    "KPIValue",
    "SCHEMA",
    "ensure_kpi_store",
    "flatten_kpis_for_report",
    "kpi_from_legacy_metrics",
    "update_kpis",
]
