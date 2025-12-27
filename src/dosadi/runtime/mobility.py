from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event


@dataclass(slots=True)
class MobilityConfig:
    enabled: bool = False
    update_cadence_days: int = 90
    generation_years: int = 20
    deterministic_salt: str = "mobility-v1"
    tiers: tuple[str, ...] = (
        "UNDERCLASS",
        "WORKING",
        "SKILLED",
        "CLERK",
        "GUILD",
        "ELITE",
    )
    max_events_per_update: int = 12
    mobility_effect_scale: float = 0.25


@dataclass(slots=True)
class PolityMobilityState:
    polity_id: str
    tier_share: dict[str, float] = field(default_factory=dict)
    mobility_matrix: dict[str, dict[str, float]] = field(default_factory=dict)
    upward_index: float = 0.0
    downward_index: float = 0.0
    trap_index: float = 0.0
    generation_last_applied_year: int = 0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class MobilityEvent:
    day: int
    polity_id: str
    kind: str
    magnitude: float
    effects: dict[str, object] = field(default_factory=dict)


def ensure_mobility_config(world: Any) -> MobilityConfig:
    cfg = getattr(world, "mobility_cfg", None)
    if not isinstance(cfg, MobilityConfig):
        cfg = MobilityConfig()
        world.mobility_cfg = cfg
    return cfg


def ensure_mobility_events(world: Any) -> list[MobilityEvent]:
    bucket: list[MobilityEvent] = getattr(world, "mobility_events", None) or []
    if not isinstance(bucket, list):
        bucket = []
    world.mobility_events = bucket
    return bucket


def ensure_polity_mobility_state(world: Any, polity_id: str, *, cfg: MobilityConfig | None = None) -> PolityMobilityState:
    cfg = cfg or ensure_mobility_config(world)
    states: dict[str, PolityMobilityState] = getattr(world, "mobility_by_polity", None) or {}
    state = states.get(polity_id)
    if not isinstance(state, PolityMobilityState):
        state = PolityMobilityState(polity_id=polity_id)
        state.tier_share = _default_tier_share(cfg)
        state.mobility_matrix = _baseline_matrix(cfg.tiers)
        states[polity_id] = state
        world.mobility_by_polity = states
    return state


def _default_tier_share(cfg: MobilityConfig) -> dict[str, float]:
    weights = [0.1, 0.32, 0.22, 0.16, 0.12, 0.08]
    total = sum(weights)
    tiers = list(cfg.tiers)
    share: dict[str, float] = {}
    for tier, weight in zip(tiers, weights):
        share[tier] = weight / total
    for tier in tiers[len(weights) :]:
        share[tier] = 0.0
    return share


def _baseline_matrix(tiers: Iterable[str]) -> dict[str, dict[str, float]]:
    ordered = list(tiers)
    matrix: dict[str, dict[str, float]] = {}
    for idx, tier in enumerate(ordered):
        stay = 0.7
        up = 0.2 if idx + 1 < len(ordered) else 0.0
        down = 0.1 if idx > 0 else 0.0
        matrix[tier] = _normalize_row(ordered, idx, stay=stay, up=up, down=down)
    return matrix


def _normalize_row(tiers: list[str], idx: int, *, stay: float, up: float, down: float, leap: float = 0.0) -> dict[str, float]:
    stay = max(0.0, stay)
    up = max(0.0, up)
    down = max(0.0, down)
    leap = max(0.0, leap)
    weights: dict[str, float] = {}
    weights[tiers[idx]] = stay
    if idx + 1 < len(tiers):
        weights[tiers[idx + 1]] = up
    if idx > 0:
        weights[tiers[idx - 1]] = down
    if leap > 0.0 and idx + 2 < len(tiers):
        weights[tiers[idx + 2]] = leap
    total = sum(weights.values()) or 1.0
    return {tier: value / total for tier, value in weights.items()}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _avg(values: Iterable[float]) -> float:
    items = [float(v) for v in values]
    return sum(items) / len(items) if items else 0.0


def _signal_from_metrics(world: Any, path: str) -> float:
    metrics = getattr(world, "metrics", None)
    if hasattr(metrics, "gauges") and isinstance(getattr(metrics, "gauges", None), Mapping):
        gauges: Mapping[str, object] = metrics.gauges
        value = gauges.get(path)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _collect_signals(world: Any, polity_id: str) -> dict[str, float]:
    education_by_ward = getattr(world, "education_by_ward", {}) or {}
    edu_values = []
    for ward_state in education_by_ward.values():
        domains = getattr(ward_state, "domains", {}) or {}
        if domains:
            edu_values.append(_avg(domains.values()))
    education_access = _avg(edu_values) if edu_values else _signal_from_metrics(world, "education.access")

    debt_pressure = _signal_from_metrics(world, "finance.debt_pressure")
    if debt_pressure <= 0.0:
        loans = getattr(world, "loans", {}) or {}
        outstanding = [float(getattr(loan, "outstanding", 0.0)) for loan in loans.values()]
        debt_pressure = _clamp01(_avg(outstanding) / 100.0)

    union_strength = _signal_from_metrics(world, "labor.union_strength")
    if union_strength <= 0.0:
        orgs_by_ward = getattr(world, "labor_orgs_by_ward", {}) or {}
        strengths = []
        for orgs in orgs_by_ward.values():
            for org in orgs:
                strength = getattr(org, "strength", 0.0)
                if getattr(org, "org_type", "").upper() in {"UNION", "GUILD"}:
                    strengths.append(strength)
        union_strength = _avg(strengths)

    health_burden = _signal_from_metrics(world, "health.burden")
    if health_burden <= 0.0:
        health_states = getattr(world, "health_by_ward", {}) or {}
        burdens = []
        for state in health_states.values():
            outbreak = 0.0
            outbreaks = getattr(state, "outbreaks", {}) or {}
            outbreak = sum(float(v) for v in outbreaks.values()) if isinstance(outbreaks, Mapping) else 0.0
            burden = float(getattr(state, "chronic_burden", 0.0)) + outbreak
            burdens.append(burden)
        health_burden = _clamp01(_avg(burdens))

    zoning_segregation = _signal_from_metrics(world, "urban.segregation")
    if zoning_segregation <= 0.0:
        urban = getattr(world, "urban_by_ward", {}) or {}
        zoning_values = [float(getattr(state, "segregation", 0.0)) for state in urban.values()]
        zoning_segregation = _clamp01(_avg(zoning_values))

    reform_strength = _signal_from_metrics(world, "reform.strength")
    migration_shock = _signal_from_metrics(world, "migration.shock")
    war_pressure = _signal_from_metrics(world, "war.pressure")

    patronage_intensity = _signal_from_metrics(world, "finance.patronage")
    if patronage_intensity <= 0.0:
        patronage = getattr(world, "patronage", []) or []
        patronage_intensity = _clamp01(len(patronage) / 25.0)

    credential_barrier = _signal_from_metrics(world, "education.credential_barrier")
    if credential_barrier <= 0.0:
        corruption_by_ward = getattr(world, "corruption_by_ward", {}) or {}
        corruption_levels = [float(getattr(state, "level", getattr(state, "corruption", 0.0))) for state in corruption_by_ward.values()]
        credential_barrier = _clamp01(_avg(corruption_levels))

    return {
        "education_access": _clamp01(education_access),
        "education_quality": _clamp01(education_access),
        "credential_barrier": _clamp01(credential_barrier),
        "debt_pressure": _clamp01(debt_pressure),
        "patronage_intensity": _clamp01(patronage_intensity),
        "health_burden": _clamp01(health_burden),
        "zoning_segregation": _clamp01(zoning_segregation),
        "union_strength": _clamp01(union_strength),
        "reform_strength": _clamp01(reform_strength),
        "war_pressure": _clamp01(war_pressure),
        "migration_shock": _clamp01(migration_shock),
    }


def build_mobility_matrix_from_signals(cfg: MobilityConfig, signals: Mapping[str, float]) -> dict[str, dict[str, float]]:
    tiers = list(cfg.tiers)
    education = _clamp01(float(signals.get("education_access", 0.0)))
    barrier = _clamp01(float(signals.get("credential_barrier", 0.0)))
    debt = _clamp01(float(signals.get("debt_pressure", 0.0)))
    patronage = _clamp01(float(signals.get("patronage_intensity", 0.0)))
    health = _clamp01(float(signals.get("health_burden", 0.0)))
    zoning = _clamp01(float(signals.get("zoning_segregation", 0.0)))
    union_strength = _clamp01(float(signals.get("union_strength", 0.0)))
    reform = _clamp01(float(signals.get("reform_strength", 0.0)))
    war = _clamp01(float(signals.get("war_pressure", 0.0)))
    migration = _clamp01(float(signals.get("migration_shock", 0.0)))

    upward_push = cfg.mobility_effect_scale * (
        0.45 * education + 0.25 * reform + 0.2 * union_strength - 0.4 * barrier - 0.2 * zoning - 0.15 * patronage
    )
    downward_push = cfg.mobility_effect_scale * (
        0.25 * debt + 0.2 * health + 0.2 * war + 0.15 * migration - 0.25 * union_strength
    )
    trap_push = cfg.mobility_effect_scale * (0.3 * debt + 0.2 * barrier + 0.1 * zoning)

    matrix: dict[str, dict[str, float]] = {}
    for idx, tier in enumerate(tiers):
        base_stay = 0.55 + trap_push
        base_up = 0.3 + upward_push - 0.15 * barrier
        base_down = 0.15 + downward_push
        leap = 0.05 * max(0.0, upward_push) if idx + 2 < len(tiers) else 0.0
        row = _normalize_row(
            tiers,
            idx,
            stay=_clamp01(base_stay),
            up=max(0.0, base_up),
            down=max(0.0, base_down),
            leap=leap,
        )
        matrix[tier] = row
    return matrix


def _indices(matrix: Mapping[str, Mapping[str, float]], cfg: MobilityConfig) -> dict[str, float]:
    tiers = list(cfg.tiers)
    bottom = tiers[:2]
    top = tiers[-2:]
    upward = 0.0
    trap = 0.0
    downward = 0.0
    for tier in bottom:
        row = matrix.get(tier, {})
        trap += float(row.get(tier, 0.0))
        upward += sum(float(prob) for dest, prob in row.items() if tiers.index(dest) > tiers.index(tier))
    for tier in top:
        row = matrix.get(tier, {})
        downward += sum(float(prob) for dest, prob in row.items() if tiers.index(dest) < tiers.index(tier))
    return {
        "upward_index": _clamp01(upward / len(bottom)) if bottom else 0.0,
        "trap_index": _clamp01(trap / len(bottom)) if bottom else 0.0,
        "downward_index": _clamp01(downward / len(top)) if top else 0.0,
    }


def update_mobility_matrix(world: Any, polity_id: str, *, day: int, signals: Mapping[str, float] | None = None) -> None:
    cfg = ensure_mobility_config(world)
    state = ensure_polity_mobility_state(world, polity_id, cfg=cfg)
    signals = signals or _collect_signals(world, polity_id)
    matrix = build_mobility_matrix_from_signals(cfg, signals)
    indices = _indices(matrix, cfg)
    state.mobility_matrix = matrix
    state.upward_index = indices["upward_index"]
    state.trap_index = indices["trap_index"]
    state.downward_index = indices["downward_index"]
    state.last_update_day = day
    state.notes["signals"] = dict(signals)
    _update_metrics(world, polity_id, state)


def _apply_generation_transition(state: PolityMobilityState, cfg: MobilityConfig) -> None:
    current_share = _normalize_share(state.tier_share, cfg.tiers)
    next_share = {tier: 0.0 for tier in cfg.tiers}
    for src, share in current_share.items():
        row = state.mobility_matrix.get(src, {})
        for dest, prob in row.items():
            next_share[dest] = next_share.get(dest, 0.0) + share * float(prob)
    state.tier_share = _normalize_share(next_share, cfg.tiers)


def apply_generation_if_due(world: Any, *, day: int, force: bool = False) -> None:
    cfg = ensure_mobility_config(world)
    if not getattr(cfg, "enabled", False):
        return

    states: Mapping[str, PolityMobilityState] = getattr(world, "mobility_by_polity", {}) or {}
    year = int(day // 365)
    for polity_id in _polities(world):
        state = ensure_polity_mobility_state(world, polity_id, cfg=cfg)
        if not force and year - state.generation_last_applied_year < int(cfg.generation_years):
            continue
        before = dict(state.tier_share)
        _apply_generation_transition(state, cfg)
        state.generation_last_applied_year = year
        _emit_generation_event(world, polity_id, before, state.tier_share, day)
        _update_metrics(world, polity_id, state)


def update_mobility(world: Any, *, day: int | None = None) -> None:
    cfg = ensure_mobility_config(world)
    if not getattr(cfg, "enabled", False):
        return

    current_day = int(day if day is not None else getattr(world, "day", 0))
    cadence = max(1, int(cfg.update_cadence_days))
    if current_day % cadence != 0:
        return

    for polity_id in _polities(world):
        state = ensure_polity_mobility_state(world, polity_id, cfg=cfg)
        if state.last_update_day == current_day:
            continue
        update_mobility_matrix(world, polity_id, day=current_day)
    apply_generation_if_due(world, day=current_day)


def _update_metrics(world: Any, polity_id: str, state: PolityMobilityState) -> None:
    metrics = ensure_metrics(world)
    bucket = metrics.gauges.setdefault("mobility", {}) if hasattr(metrics, "gauges") else {}
    if isinstance(bucket, dict):
        bucket["tier_share"] = dict(state.tier_share)
        bucket["upward_index"] = state.upward_index
        bucket["trap_index"] = state.trap_index
        bucket["downward_index"] = state.downward_index
        bucket["polity"] = polity_id
    gap_by_polity = getattr(world, "legitimacy_gap_by_polity", {}) or {}
    gap_by_polity[polity_id] = _clamp01(state.trap_index - state.upward_index)
    world.legitimacy_gap_by_polity = gap_by_polity


def _emit_generation_event(world: Any, polity_id: str, before: Mapping[str, float], after: Mapping[str, float], day: int) -> None:
    events = ensure_mobility_events(world)
    event = MobilityEvent(
        day=day,
        polity_id=polity_id,
        kind="MOBILITY_GENERATION_APPLIED",
        magnitude=1.0,
        effects={
            "before": dict(before),
            "after": dict(after),
        },
    )
    events.append(event)
    if len(events) > ensure_mobility_config(world).max_events_per_update:
        overflow = len(events) - ensure_mobility_config(world).max_events_per_update
        if overflow > 0:
            del events[:overflow]
    record_event(
        world,
        {
            "type": event.kind,
            "polity_id": polity_id,
            "day": day,
            "upward_index": getattr(getattr(world, "mobility_by_polity", {}).get(polity_id), "upward_index", 0.0),
            "trap_index": getattr(getattr(world, "mobility_by_polity", {}).get(polity_id), "trap_index", 0.0),
        },
    )


def _normalize_share(shares: Mapping[str, float], tiers: Iterable[str]) -> dict[str, float]:
    tiers_list = list(tiers)
    cleaned = {tier: max(0.0, float(shares.get(tier, 0.0))) for tier in tiers_list}
    total = sum(cleaned.values())
    if total <= 0:
        equal = 1.0 / len(tiers_list) if tiers_list else 0.0
        return {tier: equal for tier in tiers_list}
    return {tier: value / total for tier, value in cleaned.items()}


def mobility_signature(state: PolityMobilityState, cfg: MobilityConfig, *, day: int) -> str:
    canonical = {
        "polity": state.polity_id,
        "shares": {tier: round(state.tier_share.get(tier, 0.0), 6) for tier in cfg.tiers},
        "matrix": {
            src: {dst: round(prob, 6) for dst, prob in sorted(row.items())}
            for src, row in sorted(state.mobility_matrix.items())
        },
        "day": int(day),
    }
    payload = f"{cfg.deterministic_salt}:{canonical}"
    return sha256(payload.encode("utf-8")).hexdigest()


def _polities(world: Any) -> list[str]:
    options = []
    leadership = getattr(world, "leadership_by_polity", {}) or {}
    options.extend(list(leadership))
    constitution = getattr(world, "constitution_by_polity", {}) or {}
    options.extend(list(constitution))
    if not options:
        options.append(getattr(world, "polity_id", "default"))
    return sorted(set(options))
