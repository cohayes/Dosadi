from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping

from dosadi.agent.beliefs import BeliefStore
from dosadi.runtime.institutions import ensure_inst_config, ensure_state as ensure_inst_state, select_active_wards
from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.world.factions import FactionTerritory
from dosadi.world.survey_map import SurveyMap


@dataclass(slots=True)
class CultureConfig:
    enabled: bool = False
    max_active_wards_per_day: int = 24
    max_norms_per_ward: int = 12
    max_alignments_per_ward: int = 8
    norm_decay_per_day: float = 0.001
    alignment_decay_per_day: float = 0.002
    deterministic_salt: str = "culture-v1"


@dataclass(slots=True)
class WardCultureState:
    ward_id: str
    norms: dict[str, float] = field(default_factory=dict)
    alignment: dict[str, float] = field(default_factory=dict)
    taboos: dict[str, float] = field(default_factory=dict)
    last_updated_day: int = -1
    recent_drivers: dict[str, float] = field(default_factory=dict)


def _clamp(lo: float, hi: float, value: float) -> float:
    return max(lo, min(hi, value))


def _clamp01(value: float) -> float:
    return _clamp(0.0, 1.0, value)


def _ward_for_location(world: Any, location_id: str | None) -> str | None:
    if not location_id:
        return None
    survey_map: SurveyMap | None = getattr(world, "survey_map", None)
    if isinstance(survey_map, SurveyMap):
        node = survey_map.nodes.get(location_id)
        if node is not None and node.ward_id:
            return str(node.ward_id)
    return None


def _ward_for_agent(world: Any, agent: Any) -> str | None:
    ward = getattr(agent, "ward", None)
    if ward:
        return str(ward)
    location = getattr(agent, "location_id", None)
    resolved = _ward_for_location(world, location)
    if resolved:
        return resolved
    home = getattr(agent, "home", None)
    if home:
        resolved = _ward_for_location(world, home)
    return resolved


def _ensure_cfg(world: Any) -> CultureConfig:
    cfg = getattr(world, "culture_cfg", None)
    if not isinstance(cfg, CultureConfig):
        cfg = CultureConfig()
        world.culture_cfg = cfg
    return cfg


def _ensure_culture_state(world: Any) -> dict[str, WardCultureState]:
    cultures: dict[str, WardCultureState] = getattr(world, "culture_by_ward", None) or {}
    world.culture_by_ward = cultures
    return cultures


def _decay_state(state: WardCultureState, *, day: int, cfg: CultureConfig) -> None:
    if state.last_updated_day < 0 or state.last_updated_day >= day:
        state.last_updated_day = day
        return
    dt = day - state.last_updated_day
    norm_decay = (1.0 - _clamp01(cfg.norm_decay_per_day)) ** dt
    align_decay = (1.0 - _clamp01(cfg.alignment_decay_per_day)) ** dt
    for key, value in list(state.norms.items()):
        decayed = value * norm_decay
        if abs(decayed) < 1e-6:
            state.norms.pop(key, None)
        else:
            state.norms[key] = _clamp01(decayed)
    for key, value in list(state.alignment.items()):
        decayed = value * align_decay
        if abs(decayed) < 1e-6:
            state.alignment.pop(key, None)
        else:
            state.alignment[key] = _clamp(-1.0, 1.0, decayed)
    state.last_updated_day = day


def _trim_topk(entries: Mapping[str, float], *, k: int, by_abs: bool = False) -> dict[str, float]:
    key_func = (lambda item: (-abs(round(item[1], 6)), item[0])) if by_abs else (lambda item: (-round(item[1], 6), item[0]))
    sorted_items = sorted(entries.items(), key=key_func)
    return {k_: v for k_, v in sorted_items[: max(1, int(k))]}


def _belief_signals_by_ward(world: Any) -> dict[str, dict[str, float]]:
    wards: dict[str, dict[str, float]] = {}
    agents = getattr(world, "agents", {}) or {}
    for agent_id in sorted(agents.keys()):
        agent = agents[agent_id]
        ward = _ward_for_agent(world, agent)
        if not ward:
            continue
        store: BeliefStore | None = getattr(agent, "beliefs", None)
        if not isinstance(store, BeliefStore) or not getattr(store, "items", None):
            continue
        bucket = wards.setdefault(str(ward), {})
        for key, belief in sorted(store.items.items()):
            bucket[key] = max(bucket.get(key, 0.0), float(getattr(belief, "weight", 0.0)))
    return wards


def _norm_deltas(
    *, signals: Mapping[str, float], issues: Mapping[str, float], inst_state: Any
) -> tuple[dict[str, float], dict[str, float]]:
    deltas: dict[str, float] = {}
    drivers: dict[str, float] = {}

    def bump(norm: str, delta: float, reason: str) -> None:
        if abs(delta) <= 0:
            return
        deltas[norm] = deltas.get(norm, 0.0) + delta
        drivers[reason] = drivers.get(reason, 0.0) + delta

    def signal(key: str) -> float:
        return float(signals.get(key, 0.0))

    bump("norm:queue_order", 0.05 * signal("belief:queue_fairness"), "queue_fairness")
    predation = signal("belief:predation_fear")
    if predation > 0:
        bump("norm:anti_raider", 0.05 * predation, "predation_fear")
        bump("norm:vigilante_justice", 0.03 * predation, "predation_fear")

    anger = signal("belief:anger")
    if anger > 0:
        bump("norm:anti_state", 0.05 * anger, "anger")
    bump("norm:work_guild_pride", 0.04 * signal("belief:guild_pride"), "guild_pride")

    shortage = float(issues.get("issue:shortage", 0.0))
    if shortage > 0:
        corruption = float(getattr(inst_state, "corruption", 0.0))
        if corruption > 0.4:
            bump("norm:smuggling_tolerance", 0.04 * shortage, "shortage_corruption")
        else:
            bump("norm:mutual_aid", 0.04 * shortage, "shortage")

    if float(getattr(inst_state, "corruption", 0.0)) > 0.5 and anger > 0:
        bump("norm:smuggling_tolerance", 0.03 * anger, "corruption_anger")
        bump("norm:anti_state", 0.04 * anger, "corruption_anger")

    discipline = float(getattr(inst_state, "discipline", 0.0))
    if discipline > 0.5 and predation > 0:
        bump("norm:anti_raider", 0.02 * discipline * predation, "discipline_predation")

    return deltas, _trim_topk(drivers, k=6, by_abs=True)


def _apply_norm_deltas(state: WardCultureState, deltas: Mapping[str, float], *, cfg: CultureConfig) -> None:
    for norm_key, delta in sorted(deltas.items()):
        bounded = _clamp(-0.05, 0.05, float(delta))
        updated = _clamp01(state.norms.get(norm_key, 0.0) + bounded)
        if updated <= 1e-6:
            state.norms.pop(norm_key, None)
        else:
            state.norms[norm_key] = updated
    state.norms = _trim_topk(state.norms, k=cfg.max_norms_per_ward)


def _alignment_from_norms(state: WardCultureState, ward_id: str, *, cfg: CultureConfig, territory: Mapping[str, FactionTerritory]) -> None:
    anti_state = state.norms.get("norm:anti_state", 0.0)
    queue_order = state.norms.get("norm:queue_order", 0.0)
    smuggling = state.norms.get("norm:smuggling_tolerance", 0.0)
    anti_raider = state.norms.get("norm:anti_raider", 0.0)
    guild_pride = state.norms.get("norm:work_guild_pride", 0.0)

    state.alignment["fac:state"] = _clamp(
        -1.0,
        1.0,
        state.alignment.get("fac:state", 0.0) + 0.12 * queue_order - 0.18 * anti_state - 0.08 * smuggling,
    )
    state.alignment[f"inst:{ward_id}"] = _clamp(
        -1.0,
        1.0,
        state.alignment.get(f"inst:{ward_id}", 0.0) + 0.10 * queue_order - 0.12 * anti_state,
    )

    raider_claim = 0.0
    for territory_entry in territory.values():
        wards = getattr(territory_entry, "wards", {}) or {}
        raider_claim = max(raider_claim, float(wards.get(ward_id, 0.0) or 0.0))
    if raider_claim > 0:
        state.alignment["fac:raiders"] = _clamp(
            -1.0,
            1.0,
            state.alignment.get("fac:raiders", 0.0) + 0.15 * smuggling - 0.10 * anti_raider,
        )

    if guild_pride > 0:
        state.alignment["fac:guild"] = _clamp(
            -1.0,
            1.0,
            state.alignment.get("fac:guild", 0.0) + 0.14 * guild_pride,
        )

    state.alignment = _trim_topk(state.alignment, k=cfg.max_alignments_per_ward, by_abs=True)


def _culture_metrics(metrics, ward_id: str, state: WardCultureState) -> None:
    for norm_key, weight in state.norms.items():
        metrics.topk_add("culture.hot_norms", norm_key, weight, payload={"ward": ward_id})
    anti_state = state.norms.get("norm:anti_state", 0.0)
    smuggling = state.norms.get("norm:smuggling_tolerance", 0.0)
    if anti_state > 0:
        metrics.topk_add("culture.most_anti_state_wards", ward_id, anti_state)
    if smuggling > 0:
        metrics.topk_add("culture.most_smuggling_tolerant_wards", ward_id, smuggling)


def run_culture_for_day(world, *, day: int) -> None:
    cfg = _ensure_cfg(world)
    if not cfg.enabled:
        return

    inst_cfg = ensure_inst_config(world)
    active = select_active_wards(world, cfg=inst_cfg)
    active = active[: max(1, int(cfg.max_active_wards_per_day))]
    signals_by_ward = _belief_signals_by_ward(world)
    cultures = _ensure_culture_state(world)
    metrics = ensure_metrics(world)

    wards_updated = 0
    total_norms = 0
    territory: Mapping[str, FactionTerritory] = getattr(world, "faction_territory", {}) or {}

    for ward_id, issues in active:
        if ward_id not in signals_by_ward and ward_id not in cultures:
            continue
        state = cultures.get(ward_id) or WardCultureState(ward_id=ward_id)
        _decay_state(state, day=day, cfg=cfg)
        inst_state = ensure_inst_state(world, ward_id, cfg=inst_cfg)
        deltas, drivers = _norm_deltas(signals=signals_by_ward.get(ward_id, {}), issues=issues, inst_state=inst_state)
        _apply_norm_deltas(state, deltas, cfg=cfg)
        state.recent_drivers = drivers
        _alignment_from_norms(state, ward_id, cfg=cfg, territory=territory)
        cultures[ward_id] = state
        _culture_metrics(metrics, ward_id, state)
        wards_updated += 1
        total_norms += len(state.norms)
        record_event(
            world,
            {
                "type": "CULTURE_UPDATED",
                "ward_id": ward_id,
                "day": day,
                "norms": dict(state.norms),
                "alignment": dict(state.alignment),
                "drivers": dict(drivers),
            },
        )

    metrics.set_gauge("culture.wards_updated", wards_updated)
    metrics.set_gauge("culture.norms_total", total_norms)
    world.culture_by_ward = cultures


def culture_seed_payload(world: Any) -> dict[str, Any] | None:
    cfg = getattr(world, "culture_cfg", None)
    if not isinstance(cfg, CultureConfig) or not cfg.enabled:
        return None
    cultures: Mapping[str, WardCultureState] = getattr(world, "culture_by_ward", {}) or {}
    wards: list[dict[str, Any]] = []
    for ward_id in sorted(cultures.keys()):
        state = cultures[ward_id]
        entry = {
            "ward_id": ward_id,
            "norms": {k: state.norms[k] for k in sorted(state.norms.keys())},
            "alignment": {k: state.alignment[k] for k in sorted(state.alignment.keys())},
            "taboos": {k: state.taboos[k] for k in sorted(state.taboos.keys())},
            "last_updated_day": state.last_updated_day,
        }
        if state.recent_drivers:
            entry["recent_drivers"] = {k: state.recent_drivers[k] for k in sorted(state.recent_drivers.keys())}
        wards.append(entry)
    return {"schema": "culture_v1", "wards": wards}


def save_culture_seed(world: Any, path) -> None:
    payload = culture_seed_payload(world)
    if payload is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        import json

        json.dump(payload, fp, indent=2, sort_keys=True)


def culture_signature(world: Any) -> str:
    payload = culture_seed_payload(world) or {}
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(data.encode("utf-8")).hexdigest()


__all__ = [
    "CultureConfig",
    "WardCultureState",
    "culture_seed_payload",
    "culture_signature",
    "run_culture_for_day",
    "save_culture_seed",
]
