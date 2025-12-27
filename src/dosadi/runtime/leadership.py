"""Succession and leadership legitimacy v1.

The implementation follows the checklist from D-RUNTIME-0299 while keeping the
mechanics bounded and deterministic. It runs on a monthly cadence and produces
bounded history for succession events.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from dosadi.runtime.policing import DOCTRINE_PROFILES, WardPolicingState, ensure_policing_state
from dosadi.runtime.sovereignty import TerritoryState, ensure_sovereignty_state
from dosadi.runtime.telemetry import ensure_metrics, record_event


__all__ = [
    "LeadershipConfig",
    "PolityLeadership",
    "SuccessionEvent",
    "ensure_leadership_config",
    "ensure_leadership_state",
    "ensure_succession_history",
    "run_leadership_for_day",
    "export_leadership_seed",
]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_rand01(*parts: object) -> float:
    digest = sha256("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


@dataclass(slots=True)
class LeadershipConfig:
    enabled: bool = False
    update_cadence_days: int = 30
    deterministic_salt: str = "leadership-v1"
    base_succession_rate: float = 0.003
    coup_rate_p2: float = 0.010
    purge_rate_p2: float = 0.006
    legitimacy_shock_scale: float = 0.20
    max_contenders: int = 6


@dataclass(slots=True)
class PolityLeadership:
    polity_id: str
    office_type: str
    leader_id: str
    tenure_months: int = 0
    legitimacy: float = 0.5
    perf_legit: float = 0.5
    proc_legit: float = 0.5
    ideo_legit: float = 0.5
    fear_legit: float = 0.0
    alignment: dict[str, float] = field(default_factory=dict)
    sponsor_faction: str | None = None
    status: str = "STABLE"
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SuccessionEvent:
    day: int
    polity_id: str
    kind: str
    from_leader_id: str
    to_leader_id: str
    winner_faction: str | None
    legitimacy_delta: float
    reason_codes: list[str]


def ensure_leadership_config(world: Any) -> LeadershipConfig:
    cfg = getattr(world, "leadership_cfg", None)
    if not isinstance(cfg, LeadershipConfig):
        cfg = LeadershipConfig()
        world.leadership_cfg = cfg
    return cfg


def ensure_leadership_state(world: Any, *, polities: Iterable[str]) -> dict[str, PolityLeadership]:
    state = getattr(world, "leadership_by_polity", None) or {}
    if not isinstance(state, dict):
        state = {}

    for polity_id in polities:
        if polity_id in state and isinstance(state[polity_id], PolityLeadership):
            continue
        office_type = "COUNCIL" if polity_id.endswith("empire") else "SOVEREIGN"
        leader_id = f"leader:{polity_id}:0"
        state[polity_id] = PolityLeadership(
            polity_id=polity_id,
            office_type=office_type,
            leader_id=leader_id,
        )

    world.leadership_by_polity = state
    return state


def ensure_succession_history(world: Any) -> list[SuccessionEvent]:
    history = getattr(world, "succession_events", None)
    if not isinstance(history, list):
        history = []
    world.succession_events = history
    return history


def _phase_key(world: Any) -> str:
    value = getattr(getattr(world, "phase_state", None), "phase", "P1")
    try:
        intval = int(getattr(value, "value", value))
        return f"P{intval}"
    except Exception:
        return "P1"


def _polity_wards(territory: TerritoryState, polity_id: str) -> list[str]:
    return [ward for ward, owner in (territory.ward_control or {}).items() if owner == polity_id]


def _policing_mix(world: Any, ward_ids: Iterable[str]) -> dict[str, float]:
    totals: dict[str, float] = {key: 0.0 for key in DOCTRINE_PROFILES}
    count = 0
    for ward_id in ward_ids:
        ward_state: WardPolicingState = ensure_policing_state(world, ward_id)
        for key, val in ward_state.doctrine_mix.items():
            totals[key] = totals.get(key, 0.0) + float(val)
        count += 1
    if count <= 0:
        return {key: 1.0 / len(DOCTRINE_PROFILES) for key in DOCTRINE_PROFILES}
    return {key: totals.get(key, 0.0) / count for key in DOCTRINE_PROFILES}


def _hardship_score(world: Any, ward_ids: Iterable[str]) -> float:
    wards = getattr(world, "wards", {}) or {}
    values = []
    for wid in ward_ids:
        need = getattr(wards.get(wid), "need_index", None)
        if need is None:
            continue
        try:
            values.append(float(need))
        except Exception:
            continue
    if not values:
        base = getattr(world, "need_index", 0.0) or 0.0
        try:
            return _clamp01(float(base))
        except Exception:
            return 0.0
    return _clamp01(sum(values) / len(values))


def _inequality(world: Any) -> float:
    try:
        return _clamp01(float(getattr(world, "inequality_index", 0.0) or 0.0))
    except Exception:
        return 0.0


def _war_pressure(world: Any, territory: TerritoryState, polity_id: str) -> float:
    contested = 0
    total = 0
    for corridor, owner in (territory.corridor_control or {}).items():
        if owner == polity_id:
            total += 1
            if corridor in (territory.corridor_contested or {}):
                contested += 1
    if total <= 0:
        return 0.0
    return _clamp01(contested / total)


def _ideology_alignment(world: Any, ward_ids: Iterable[str], leader_alignment: Mapping[str, float]) -> tuple[float, float]:
    cultures = getattr(world, "culture_by_ward", {}) or {}
    mismatches: list[float] = []
    polarizations: list[float] = []
    for wid in ward_ids:
        culture = cultures.get(wid)
        alignment = getattr(culture, "alignment", {}) if culture is not None else {}
        polarizations.append(float(alignment.get("polarization", 0.0) or 0.0))
        overlap = 0.0
        for key, val in leader_alignment.items():
            diff = abs(float(alignment.get(key, 0.0)) - float(val))
            overlap += diff
        mismatches.append(overlap)
    pol = sum(polarizations) / len(polarizations) if polarizations else 0.0
    mis = sum(mismatches) / len(mismatches) if mismatches else 0.0
    return _clamp01(pol), _clamp01(mis)


def _compute_components(
    world: Any,
    leadership: PolityLeadership,
    *,
    territory: TerritoryState,
    ward_ids: list[str],
) -> tuple[float, float, float, float, float]:
    hardship = _hardship_score(world, ward_ids)
    inequality = _inequality(world)
    war_pressure = _war_pressure(world, territory, leadership.polity_id)
    policing_mix = _policing_mix(world, ward_ids)
    terror_share = float(policing_mix.get("TERROR", 0.0) or 0.0)
    procedural = float(policing_mix.get("PROCEDURAL", 0.0) or 0.0)
    corruption_proxy = 0.0
    for wid in ward_ids:
        state = ensure_policing_state(world, wid)
        corruption_proxy += float(state.corruption)
    if ward_ids:
        corruption_proxy /= len(ward_ids)
    polarization, mismatch = _ideology_alignment(world, ward_ids, leadership.alignment)

    perf_legit = _clamp01(1.0 - 0.6 * hardship - 0.25 * war_pressure - 0.15 * inequality)
    proc_legit = _clamp01(procedural + 0.1 - terror_share * 0.2 - corruption_proxy * 0.3)
    ideo_legit = _clamp01(1.0 - 0.4 * polarization - 0.6 * mismatch)
    fear_legit = _clamp01(terror_share * 0.8)
    legitimacy = _clamp01(
        0.35 * perf_legit + 0.25 * proc_legit + 0.25 * ideo_legit + 0.15 * fear_legit - terror_share * 0.1
    )
    return legitimacy, perf_legit, proc_legit, ideo_legit, fear_legit


def _contender_scores(world: Any, cfg: LeadershipConfig, polity_id: str) -> list[tuple[float, str]]:
    factions = getattr(world, "factions", {}) or {}
    contenders: list[tuple[float, str]] = []
    for faction_id in sorted(factions.keys())[: max(1, int(cfg.max_contenders))]:
        faction = factions[faction_id]
        try:
            influence = float(getattr(faction, "influence", 0.5) or 0.5)
        except Exception:
            influence = 0.5
        score = influence + _stable_rand01(cfg.deterministic_salt, polity_id, faction_id)
        contenders.append((score, faction_id))
    contenders.sort(key=lambda itm: (-itm[0], itm[1]))
    return contenders


def _resolve_winner(world: Any, cfg: LeadershipConfig, polity_id: str) -> str | None:
    contenders = _contender_scores(world, cfg, polity_id)
    if not contenders:
        return None
    return contenders[0][1]


def _succession_probabilities(
    cfg: LeadershipConfig,
    *,
    world: Any,
    leadership: PolityLeadership,
    legitimacy: float,
    war_pressure: float,
    terror_share: float,
    day: int,
) -> tuple[float, float, float, float]:
    orderly = cfg.base_succession_rate
    if leadership.office_type == "COUNCIL":
        orderly *= 1.3
    legitimacy_gap = _clamp01(1.0 - legitimacy)
    phase_key = _phase_key(world)
    coup = cfg.coup_rate_p2 * (1.0 + legitimacy_gap + war_pressure)
    purge = cfg.purge_rate_p2 * (1.0 + terror_share)
    reshuffle = 0.01 * legitimacy_gap if leadership.office_type == "COUNCIL" else 0.0
    if phase_key != "P2":
        coup *= 0.5
        purge *= 0.5
    deterministic_bump = _stable_rand01(cfg.deterministic_salt, leadership.polity_id, day)
    coup += 0.25 * legitimacy_gap * deterministic_bump
    purge += 0.15 * terror_share * deterministic_bump
    return orderly, reshuffle, coup, purge


def _choose_event(
    cfg: LeadershipConfig,
    *,
    world: Any,
    leadership: PolityLeadership,
    legitimacy: float,
    war_pressure: float,
    terror_share: float,
    ward_ids: list[str],
    day: int,
) -> tuple[str | None, list[str]]:
    orderly, reshuffle, coup, purge = _succession_probabilities(
        cfg,
        world=world,
        leadership=leadership,
        legitimacy=legitimacy,
        war_pressure=war_pressure,
        terror_share=terror_share,
        day=day,
    )
    roll = _stable_rand01(cfg.deterministic_salt, leadership.polity_id, day, "event")
    reasons: list[str] = []
    thresholds = [
        ("COUP", coup),
        ("PURGE", purge),
        ("RESHUFFLE", reshuffle),
        ("ORDERLY", orderly),
    ]
    for kind, prob in thresholds:
        if prob <= 0:
            continue
        if roll < prob:
            reasons.append(f"roll<{kind.lower()}:{roll:.3f}<{prob:.3f}")
            return kind, reasons
        roll -= prob
    return None, reasons


def _apply_event(
    world: Any,
    cfg: LeadershipConfig,
    *,
    leadership: PolityLeadership,
    legitimacy: float,
    perf: float,
    proc: float,
    ideo: float,
    fear: float,
    ward_ids: list[str],
    day: int,
) -> SuccessionEvent | None:
    territory = ensure_sovereignty_state(world).territory
    war_pressure = _war_pressure(world, territory, leadership.polity_id)
    policing_mix = _policing_mix(world, ward_ids)
    terror_share = float(policing_mix.get("TERROR", 0.0) or 0.0)
    kind, reasons = _choose_event(
        cfg,
        world=world,
        leadership=leadership,
        legitimacy=legitimacy,
        war_pressure=war_pressure,
        terror_share=terror_share,
        ward_ids=ward_ids,
        day=day,
    )
    if kind is None:
        return None
    winner = _resolve_winner(world, cfg, leadership.polity_id)
    from_leader = leadership.leader_id
    seq = 1
    try:
        seq = int(from_leader.split(":")[-1]) + 1
    except Exception:
        seq = leadership.tenure_months + 1
    leadership.leader_id = f"leader:{leadership.polity_id}:{seq}"
    leadership.sponsor_faction = winner
    delta = cfg.legitimacy_shock_scale
    if kind == "ORDERLY":
        delta *= 0.5
    elif kind == "COUP":
        delta *= 1.2
    elif kind == "PURGE":
        delta *= 1.0
    elif kind == "RESHUFFLE":
        delta *= 0.6
    prior_legitimacy = legitimacy
    legitimacy = _clamp01(legitimacy - delta if kind in {"COUP", "PURGE"} else legitimacy + 0.05)
    leadership.legitimacy = legitimacy
    leadership.perf_legit = perf
    leadership.proc_legit = proc
    leadership.ideo_legit = ideo
    leadership.fear_legit = fear
    leadership.status = "CONTESTED" if kind in {"COUP", "PURGE"} else "STABLE"
    event = SuccessionEvent(
        day=day,
        polity_id=leadership.polity_id,
        kind=kind,
        from_leader_id=from_leader,
        to_leader_id=leadership.leader_id,
        winner_faction=winner,
        legitimacy_delta=leadership.legitimacy - prior_legitimacy,
        reason_codes=reasons,
    )
    _apply_effects(world, leadership, event, ward_ids)
    return event


def _apply_effects(world: Any, leadership: PolityLeadership, event: SuccessionEvent, ward_ids: list[str]) -> None:
    governance_pressure = getattr(world, "governance_failure_pressure", {}) or {}
    insurgency_support = getattr(world, "insurgency_support", {}) or {}
    pressure_delta = _clamp01(abs(event.legitimacy_delta))
    if event.kind in {"COUP", "PURGE"}:
        pressure_delta = _clamp01(pressure_delta + 0.1)
    for wid in ward_ids:
        governance_pressure[wid] = _clamp01(float(governance_pressure.get(wid, 0.0)) + pressure_delta)
        insurgency_support[wid] = _clamp01(float(insurgency_support.get(wid, 0.0)) + 0.5 * pressure_delta)
    world.governance_failure_pressure = governance_pressure
    world.insurgency_support = insurgency_support
    if event.winner_faction:
        world.policy = getattr(world, "policy", {}) or {}
        bias = world.policy.get("leadership_bias", {}) or {}
        bias[event.polity_id] = event.winner_faction
        world.policy["leadership_bias"] = bias


def _update_metrics(world: Any, *, leadership: Mapping[str, PolityLeadership], events: list[SuccessionEvent]) -> None:
    metrics = ensure_metrics(world)
    if not leadership:
        return
    avg_leg = sum(item.legitimacy for item in leadership.values()) / len(leadership)
    metrics.set_gauge("leadership.avg_legitimacy", avg_leg)
    metrics.set_gauge("leadership.succession_events", len(events))
    metrics.set_gauge(
        "leadership.coups",
        sum(1 for evt in events if getattr(evt, "kind", "").upper() == "COUP"),
    )
    metrics.set_gauge(
        "leadership.purges",
        sum(1 for evt in events if getattr(evt, "kind", "").upper() == "PURGE"),
    )
    metrics.topk.pop("leadership.low_legitimacy", None)
    for pid, state in leadership.items():
        metrics.topk_add(
            "leadership.low_legitimacy",
            pid,
            1.0 - state.legitimacy,
            payload={"status": state.status},
        )


def run_leadership_for_day(world: Any, day: int | None = None) -> None:
    cfg = ensure_leadership_config(world)
    if not cfg.enabled:
        return
    day = getattr(world, "day", 0) if day is None else int(day)
    sovereignty_state = ensure_sovereignty_state(world)
    polities = sorted(sovereignty_state.polities.keys()) or ["polity:empire"]
    leadership_state = ensure_leadership_state(world, polities=polities)
    history = ensure_succession_history(world)
    territory = sovereignty_state.territory

    for polity_id, leadership in leadership_state.items():
        if leadership.last_update_day >= 0 and day - leadership.last_update_day < max(1, cfg.update_cadence_days):
            continue
        ward_ids = _polity_wards(territory, polity_id) or list(getattr(world, "wards", {}).keys())
        legitimacy, perf, proc, ideo, fear = _compute_components(
            world,
            leadership,
            territory=territory,
            ward_ids=ward_ids,
        )
        leadership.legitimacy = legitimacy
        leadership.perf_legit = perf
        leadership.proc_legit = proc
        leadership.ideo_legit = ideo
        leadership.fear_legit = fear
        leadership.tenure_months += 1
        leadership.last_update_day = day
        event = _apply_event(
            world,
            cfg,
            leadership=leadership,
            legitimacy=legitimacy,
            perf=perf,
            proc=proc,
            ideo=ideo,
            fear=fear,
            ward_ids=ward_ids,
            day=day,
        )
        if event:
            history.append(event)
            if len(history) > 120:
                del history[: len(history) - 120]
            record_event(
                world,
                {
                    "event": f"LEADERSHIP_{event.kind}",
                    "polity_id": polity_id,
                    "from": event.from_leader_id,
                    "to": event.to_leader_id,
                    "winner_faction": event.winner_faction,
                },
            )

    _update_metrics(world, leadership=leadership_state, events=history)


def export_leadership_seed(world: Any, base_path: Path) -> Path:
    history = ensure_succession_history(world)
    payload = {
        "leadership": [asdict(state) for _, state in sorted(getattr(world, "leadership_by_polity", {}).items())],
        "succession_events": [asdict(evt) for evt in history],
    }
    path = base_path / "leadership.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)
    return path
