"""Reform movements and anti-corruption drives v1.

Implements the deterministic, bounded reform loop from
`D-RUNTIME-0316_Reform_Movements_and_Anti_Corruption_Drives_v1`.

The module keeps lightweight world state (config, watchdogs, movements,
and a bounded event log), exposes helpers for snapshot/save, and provides
`run_reforms_for_day` to evolve movements on cadence days.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.leadership import ensure_leadership_state
from dosadi.runtime.policing import WardPolicingState, ensure_policing_state
from dosadi.runtime.shadow_state import CorruptionIndex
from dosadi.runtime.sovereignty import TerritoryState, ensure_sovereignty_state
from dosadi.runtime.telemetry import ensure_metrics, record_event


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_rand01(*parts: object) -> float:
    digest = sha256("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


@dataclass(slots=True)
class ReformConfig:
    enabled: bool = True
    cadence_days: int = 7
    max_movements: int = 12
    max_watchdogs: int = 24
    max_events: int = 200

    scandal_exposure_trigger: float = 0.75
    hardship_trigger: float = 0.70
    legitimacy_trigger: float = 0.35

    formation_chance_base: float = 0.08
    decay_rate: float = 0.03
    capture_risk_base: float = 0.05
    backlash_base: float = 0.04

    policing_proc_shift_max: float = 0.15
    capture_reduction_max: float = 0.20
    fear_legit_penalty: float = 0.10
    rumor_amplification: float = 0.25
    deterministic_salt: str = "reforms-v1"


@dataclass(slots=True)
class WatchdogInstitution:
    watchdog_id: str
    ward_id: str | None
    kind: str
    sponsor_faction: str | None
    independence: float
    capture: float
    capacity: float
    last_update_day: int = -1


@dataclass(slots=True)
class ReformMovement:
    movement_id: str
    scope: str
    ward_id: str | None
    polity_id: str | None
    sponsor_faction: str | None
    coalition: dict[str, float]
    agenda: dict[str, float]
    momentum: float
    legitimacy_claim: float
    risk_of_backlash: float
    status: str = "ACTIVE"
    start_day: int = 0
    last_update_day: int = -1


@dataclass(slots=True)
class ReformEvent:
    day: int
    movement_id: str
    kind: str
    payload: dict[str, object]


def ensure_reform_config(world: Any) -> ReformConfig:
    cfg = getattr(world, "reform_cfg", None)
    if not isinstance(cfg, ReformConfig):
        cfg = ReformConfig()
        world.reform_cfg = cfg
    return cfg


def ensure_watchdogs(world: Any) -> dict[str, WatchdogInstitution]:
    watchdogs = getattr(world, "watchdogs", None)
    if not isinstance(watchdogs, dict):
        watchdogs = {}
    world.watchdogs = watchdogs
    return watchdogs


def ensure_reform_movements(world: Any) -> dict[str, ReformMovement]:
    movements = getattr(world, "reform_movements", None)
    if not isinstance(movements, dict):
        movements = {}
    world.reform_movements = movements
    return movements


def ensure_reform_events(world: Any) -> list[ReformEvent]:
    events = getattr(world, "reform_events", None)
    if not isinstance(events, list):
        events = []
    world.reform_events = events
    return events


def _ring_append(events: list[ReformEvent], event: ReformEvent, *, max_size: int) -> None:
    events.append(event)
    if len(events) > max_size:
        del events[: len(events) - max_size]


def _polities(world: Any) -> list[str]:
    state = ensure_sovereignty_state(world)
    polities = sorted(getattr(state, "polities", {}).keys())
    if polities:
        return polities
    return ["polity:empire"]


def _wards_for_polity(territory: TerritoryState, polity_id: str) -> list[str]:
    wards: list[str] = []
    for ward_id, owner in (territory.ward_control or {}).items():
        if owner == polity_id:
            wards.append(str(ward_id))
    return sorted(wards)


def _hardship(world: Any, ward_id: str) -> float:
    wards = getattr(world, "wards", {}) or {}
    ward = wards.get(ward_id)
    if ward is None:
        return 0.0
    value = getattr(ward, "need_index", getattr(ward, "hardship", 0.0))
    try:
        return _clamp01(float(value))
    except Exception:
        return 0.0


def _capture(world: Any, ward_id: str) -> float:
    corruption: Mapping[str, CorruptionIndex] = getattr(world, "corruption_by_ward", {}) or {}
    entry: CorruptionIndex | None = corruption.get(ward_id)
    if entry is None:
        return 0.0
    return _clamp01(float(entry.capture))


def _shadow(world: Any, ward_id: str) -> float:
    corruption: Mapping[str, CorruptionIndex] = getattr(world, "corruption_by_ward", {}) or {}
    entry: CorruptionIndex | None = corruption.get(ward_id)
    if entry is None:
        return 0.0
    return _clamp01(float(entry.shadow_state))


def _exposure(world: Any, ward_id: str) -> float:
    return _clamp01((_capture(world, ward_id) + _shadow(world, ward_id)) / 2.0)


def _legitimacy(world: Any, polity_id: str) -> float:
    leadership = ensure_leadership_state(world, polities=[polity_id]).get(polity_id)
    return _clamp01(float(getattr(leadership, "legitimacy", 0.5)))


def _media_pressure(world: Any) -> float:
    metrics = getattr(world, "metrics", None)
    if metrics is None:
        return 0.0
    gauges = getattr(metrics, "gauges", {}) or {}
    reform_bucket = gauges.get("media", {}) if isinstance(gauges, Mapping) else {}
    if isinstance(reform_bucket, Mapping):
        try:
            return _clamp01(float(reform_bucket.get("pressure", 0.0)))
        except Exception:
            return 0.0
    return 0.0


def _pressure_score(world: Any, *, ward_id: str, polity_id: str) -> float:
    exposure = _exposure(world, ward_id)
    hardship = _hardship(world, ward_id)
    legitimacy = _legitimacy(world, polity_id)
    media = _media_pressure(world)
    return _clamp01(0.35 * exposure + 0.25 * hardship + 0.2 * (1.0 - legitimacy) + 0.2 * media)


def _agenda_for_zone(exposure: float, capture: float) -> dict[str, float]:
    return {
        "audit_strictness": _clamp01(0.6 * exposure + 0.2 * capture),
        "procedural_policing": _clamp01(0.5 + 0.3 * (1.0 - capture)),
        "evidence_threshold": _clamp01(0.4 + 0.4 * exposure),
    }


def _ensure_watchdog_for_zone(
    watchdogs: dict[str, WatchdogInstitution], *, ward_id: str, sponsor: str | None, cfg: ReformConfig, day: int
) -> WatchdogInstitution:
    existing = watchdogs.get(ward_id)
    if isinstance(existing, WatchdogInstitution):
        return existing
    watchdog_id = f"watchdog:{ward_id}:{day}"
    watchdog = WatchdogInstitution(
        watchdog_id=watchdog_id,
        ward_id=ward_id,
        kind="AUDIT",
        sponsor_faction=sponsor,
        independence=0.5,
        capture=0.3,
        capacity=0.5,
        last_update_day=day,
    )
    if len(watchdogs) < cfg.max_watchdogs:
        watchdogs[ward_id] = watchdog
    return watchdog


def _formation_probability(cfg: ReformConfig, *, exposure: float, hardship: float, legitimacy: float, media: float, has_existing: bool) -> float:
    score = exposure * 0.4 + hardship * 0.25 + (1.0 - legitimacy) * 0.2 + media * 0.15
    penalty = 0.1 if has_existing else 0.0
    return _clamp01(cfg.formation_chance_base + score * 0.25 - penalty)


def _update_watchdog(watchdog: WatchdogInstitution, *, exposure: float, cfg: ReformConfig) -> None:
    drift = cfg.capture_risk_base + exposure * 0.1 - watchdog.independence * 0.05
    watchdog.capture = _clamp01(watchdog.capture + drift)
    watchdog.independence = _clamp01(watchdog.independence - drift * 0.4)
    watchdog.capacity = _clamp01(watchdog.capacity + 0.05 - watchdog.capture * 0.05)


def _update_movement(
    movement: ReformMovement, *, exposure: float, hardship: float, legitimacy: float, watchdog: WatchdogInstitution | None, cfg: ReformConfig
) -> None:
    decay = cfg.decay_rate
    momentum_boost = exposure * 0.2 + hardship * 0.1 + (1.0 - legitimacy) * 0.1
    independence = getattr(watchdog, "independence", 0.0) if watchdog else 0.0
    momentum_boost += independence * 0.1
    movement.momentum = _clamp01(movement.momentum * (1.0 - decay) + momentum_boost)
    movement.legitimacy_claim = _clamp01(movement.legitimacy_claim * (1.0 - decay * 0.5) + momentum_boost * 0.5)
    movement.risk_of_backlash = _clamp01(cfg.backlash_base + movement.momentum * 0.2 + exposure * 0.1)
    movement.last_update_day = movement.last_update_day + 1 if movement.last_update_day >= 0 else 0
    if movement.momentum < 0.05:
        movement.status = "STALLED"
    if movement.momentum > 0.95 and movement.status == "ACTIVE":
        movement.status = "SUCCESS"


def _apply_effects(
    world: Any, *, movement: ReformMovement, cfg: ReformConfig, exposure: float, legitimacy: float, watchdog: WatchdogInstitution | None
) -> None:
    if movement.ward_id:
        p_state: WardPolicingState = ensure_policing_state(world, movement.ward_id)
        procedural = float(p_state.doctrine_mix.get("PROCEDURAL", 0.0))
        delta = cfg.policing_proc_shift_max * movement.momentum * (1.0 - procedural)
        p_state.doctrine_mix["PROCEDURAL"] = _clamp01(procedural + delta)
        terror = p_state.doctrine_mix.get("TERROR", 0.0)
        if terror > 0:
            p_state.doctrine_mix["TERROR"] = _clamp01(max(0.0, terror - delta * 0.5))

        corruption = getattr(world, "corruption_by_ward", {}) or {}
        entry: CorruptionIndex | None = corruption.get(movement.ward_id)
        if entry is not None:
            reduction = cfg.capture_reduction_max * movement.momentum * (0.5 + exposure * 0.5)
            entry.capture = _clamp01(entry.capture * (1.0 - reduction))
            entry.shadow_state = _clamp01(entry.shadow_state * (1.0 - reduction * 0.7))
            entry.petty = _clamp01(entry.petty * (1.0 - reduction * 0.5))

    if movement.polity_id:
        leadership = ensure_leadership_state(world, polities=[movement.polity_id]).get(movement.polity_id)
        leadership.proc_legit = _clamp01(leadership.proc_legit + movement.momentum * 0.1)
        leadership.fear_legit = _clamp01(leadership.fear_legit - cfg.fear_legit_penalty * movement.momentum)
        leadership.legitimacy = _clamp01(
            (leadership.proc_legit + leadership.perf_legit + leadership.ideo_legit + leadership.fear_legit) / 4.0
        )

    metrics = ensure_metrics(world)
    gauges = getattr(metrics, "gauges", {}).setdefault("reform", {})
    if isinstance(gauges, dict):
        gauges["rumor_amplification"] = cfg.rumor_amplification * movement.momentum
    if watchdog and watchdog.independence > 0.6 and exposure > 0.6:
        record_event(
            world,
            {
                "type": "REFORM_LEAK",
                "ward_id": movement.ward_id,
                "movement_id": movement.movement_id,
                "independence": watchdog.independence,
            },
        )


def _backlash(world: Any, *, movement: ReformMovement, cfg: ReformConfig, legitimacy: float, exposure: float, day: int) -> None:
    threat_to_elites = exposure * 0.3 + movement.momentum * 0.3
    fear_dependence = max(0.0, 0.5 - legitimacy)
    chance = _clamp01(cfg.backlash_base + movement.momentum * 0.2 + threat_to_elites * 0.3 + fear_dependence * 0.2)
    roll = _stable_rand01(cfg.deterministic_salt, movement.movement_id, day, "backlash")
    if roll >= chance:
        return

    pick = _stable_rand01(cfg.deterministic_salt, movement.movement_id, day, "response")
    if pick < 0.25:
        movement.status = "COOPTED"
    elif pick < 0.55:
        movement.status = "CRUSHED"
        if movement.ward_id:
            p_state: WardPolicingState = ensure_policing_state(world, movement.ward_id)
            terror = float(p_state.doctrine_mix.get("TERROR", 0.0))
            p_state.doctrine_mix["TERROR"] = _clamp01(terror + 0.1)
    elif pick < 0.85:
        movement.status = "COUNTER_COUP"
    else:
        movement.status = "STALL"

    if movement.ward_id:
        p_state: WardPolicingState = ensure_policing_state(world, movement.ward_id)
        terror = float(p_state.doctrine_mix.get("TERROR", 0.0))
        p_state.doctrine_mix["TERROR"] = _clamp01(terror + 0.05)

    record_event(
        world,
        {
            "type": "REFORM_BACKLASH",
            "movement_id": movement.movement_id,
            "status": movement.status,
            "day": day,
        },
    )


def run_reforms_for_day(world: Any, *, day: int | None = None) -> None:
    cfg = ensure_reform_config(world)
    if not cfg.enabled:
        return
    current_day = int(day if day is not None else getattr(world, "day", 0))
    if cfg.cadence_days > 0 and current_day % cfg.cadence_days != 0:
        return
    if getattr(world, "reform_last_update_day", -1) == current_day:
        return

    movements = ensure_reform_movements(world)
    watchdogs = ensure_watchdogs(world)
    events = ensure_reform_events(world)

    territory = getattr(ensure_sovereignty_state(world), "territory", TerritoryState())
    polities = _polities(world)
    media = _media_pressure(world)

    pressure_entries: list[tuple[float, str, str]] = []
    for polity_id in polities:
        wards = _wards_for_polity(territory, polity_id)
        for ward_id in wards:
            score = _pressure_score(world, ward_id=ward_id, polity_id=polity_id)
            pressure_entries.append((score, ward_id, polity_id))

    pressure_entries.sort(key=lambda itm: (-round(itm[0], 6), itm[1], itm[2]))
    for score, ward_id, polity_id in pressure_entries[: cfg.max_movements]:
        has_existing = any(mv.ward_id == ward_id and mv.status == "ACTIVE" for mv in movements.values())
        exposure = _exposure(world, ward_id)
        hardship = _hardship(world, ward_id)
        legitimacy = _legitimacy(world, polity_id)
        formation_prob = _formation_probability(
            cfg,
            exposure=exposure,
            hardship=hardship,
            legitimacy=legitimacy,
            media=media,
            has_existing=has_existing,
        )
        if exposure >= cfg.scandal_exposure_trigger or hardship >= cfg.hardship_trigger or legitimacy <= cfg.legitimacy_trigger:
            formation_prob = 1.0
        roll = _stable_rand01(cfg.deterministic_salt, ward_id, polity_id, current_day, "form")
        if roll >= formation_prob or score < cfg.formation_chance_base:
            continue
        sponsor = None
        factions = getattr(world, "factions", {}) or {}
        if factions:
            sponsor = sorted(factions.keys())[0]
        exposure = _exposure(world, ward_id)
        agenda = _agenda_for_zone(exposure, _capture(world, ward_id))
        movement_id = f"reform:{ward_id}:{current_day}:{len(movements)}"
        movements[movement_id] = ReformMovement(
            movement_id=movement_id,
            scope="WARD",
            ward_id=ward_id,
            polity_id=polity_id,
            sponsor_faction=sponsor,
            coalition={sponsor: 1.0} if sponsor else {},
            agenda=agenda,
            momentum=_clamp01(score + exposure * 0.2),
            legitimacy_claim=_clamp01(media + 0.2),
            risk_of_backlash=cfg.backlash_base,
            start_day=current_day,
            last_update_day=current_day,
        )
        _ensure_watchdog_for_zone(watchdogs, ward_id=ward_id, sponsor=sponsor, cfg=cfg, day=current_day)
        evt = ReformEvent(day=current_day, movement_id=movement_id, kind="FORMATION", payload={"score": score})
        _ring_append(events, evt, max_size=cfg.max_events)
        record_event(world, {"type": "REFORM_FORMED", "movement_id": movement_id, "ward_id": ward_id, "day": current_day})

    for _, ward_id, _ in pressure_entries[: cfg.max_watchdogs]:
        watchdog = watchdogs.get(ward_id)
        if watchdog:
            _update_watchdog(watchdog, exposure=_exposure(world, ward_id), cfg=cfg)
            watchdog.last_update_day = current_day

    for movement in movements.values():
        if movement.status not in {"ACTIVE", "STALLED"}:
            continue
        exposure = _exposure(world, movement.ward_id or "") if movement.ward_id else 0.0
        legitimacy = _legitimacy(world, movement.polity_id or polities[0]) if movement.polity_id else 0.5
        hardship = _hardship(world, movement.ward_id or "") if movement.ward_id else 0.0
        watchdog = watchdogs.get(movement.ward_id or "") if movement.ward_id else None
        if watchdog:
            _update_watchdog(watchdog, exposure=exposure, cfg=cfg)
            watchdog.last_update_day = current_day
        _update_movement(movement, exposure=exposure, hardship=hardship, legitimacy=legitimacy, watchdog=watchdog, cfg=cfg)
        _apply_effects(world, movement=movement, cfg=cfg, exposure=exposure, legitimacy=legitimacy, watchdog=watchdog)
        _backlash(world, movement=movement, cfg=cfg, legitimacy=legitimacy, exposure=exposure, day=current_day)
        if movement.status == "SUCCESS":
            record_event(world, {"type": "REFORM_SUCCESS", "movement_id": movement.movement_id, "day": current_day})

    metrics = ensure_metrics(world)
    gauges = getattr(metrics, "gauges", {}).setdefault("reform", {})
    if isinstance(gauges, dict):
        gauges["movements_active"] = sum(1 for mv in movements.values() if mv.status == "ACTIVE")
        gauges["watchdogs"] = len(watchdogs)
    world.reform_last_update_day = current_day


def reform_signature(world: Any) -> str:
    movements = ensure_reform_movements(world)
    events = ensure_reform_events(world)
    payload = {
        "movements": {mid: asdict(mv) for mid, mv in sorted(movements.items())},
        "events": [asdict(evt) for evt in events],
    }
    digest = sha256(str(payload).encode("utf-8")).hexdigest()
    return digest


def export_reform_seed(world: Any) -> dict[str, object]:
    ensure_reform_config(world)
    ensure_watchdogs(world)
    ensure_reform_movements(world)
    ensure_reform_events(world)
    return {
        "config": asdict(world.reform_cfg),
        "watchdogs": {wid: asdict(wd) for wid, wd in sorted(world.watchdogs.items())},
        "movements": {mid: asdict(mv) for mid, mv in sorted(world.reform_movements.items())},
        "events": [asdict(evt) for evt in world.reform_events],
        "last_update_day": getattr(world, "reform_last_update_day", -1),
    }


def load_reform_seed(world: Any, payload: Mapping[str, object]) -> None:
    cfg = ensure_reform_config(world)
    for key, val in (payload.get("config", {}) or {}).items():
        if hasattr(cfg, key):
            setattr(cfg, key, val)
    watchdogs_raw = payload.get("watchdogs", {}) or {}
    watchdogs: dict[str, WatchdogInstitution] = {}
    for ward_id, entry in watchdogs_raw.items():
        watchdogs[ward_id] = WatchdogInstitution(**entry)
    movements_raw = payload.get("movements", {}) or {}
    movements: dict[str, ReformMovement] = {}
    for mid, entry in movements_raw.items():
        movements[mid] = ReformMovement(**entry)
    events_raw = payload.get("events", []) or []
    events = [ReformEvent(**entry) for entry in events_raw]
    world.watchdogs = watchdogs
    world.reform_movements = movements
    world.reform_events = events
    world.reform_last_update_day = int(payload.get("last_update_day", -1))


__all__ = [
    "ReformConfig",
    "WatchdogInstitution",
    "ReformMovement",
    "ReformEvent",
    "ensure_reform_config",
    "ensure_watchdogs",
    "ensure_reform_movements",
    "ensure_reform_events",
    "run_reforms_for_day",
    "reform_signature",
    "export_reform_seed",
    "load_reform_seed",
]
