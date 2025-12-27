from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.ideology import AXES, ensure_ward_ideology
from dosadi.runtime.institutions import ensure_policy, ensure_state
from dosadi.runtime.media import MediaMessage
from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.runtime.ledger import STATE_TREASURY, transfer


@dataclass(slots=True)
class ReligionConfig:
    enabled: bool = False
    update_cadence_days: int = 7
    max_sects_per_ward: int = 4
    deterministic_salt: str = "religion-v1"
    conversion_rate: float = 0.03
    suppression_cost_scale: float = 0.10
    ritual_effect_scale: float = 0.08


@dataclass(slots=True)
class SectState:
    sect_id: str
    archetype: str
    global_strength: float = 0.0
    doctrine: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class WardReligionState:
    ward_id: str
    adherence: dict[str, float] = field(default_factory=dict)
    clergy_power: dict[str, float] = field(default_factory=dict)
    tithe_rate: float = 0.0
    ritual_calendar: dict[str, int] = field(default_factory=dict)
    suppression_level: float = 0.0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


SECT_ARCHETYPES: Mapping[str, Mapping[str, object]] = {
    "ORTHODOX_CHURCH": {
        "axes": {"ORTHODOXY": 0.6, "MILITARISM": 0.2, "MERCANTILISM": 0.1, "TECHNICISM": 0.1},
        "rituals": ("PUBLIC_PENITENCE", "WATER_VIGIL", "MARTIAL_PARADE"),
        "alignment": 1.0,
    },
    "WELL_MYSTICS": {
        "axes": {"ORTHODOXY": 0.25, "TECHNICISM": 0.35, "MERCANTILISM": 0.15, "MILITARISM": 0.25},
        "rituals": ("WATER_VIGIL", "HEALING_RITES"),
        "alignment": 0.6,
    },
    "MARTIAL_CULT": {
        "axes": {"MILITARISM": 0.55, "ORTHODOXY": 0.25, "MERCANTILISM": 0.1, "TECHNICISM": 0.1},
        "rituals": ("MARTIAL_PARADE", "PUBLIC_PENITENCE"),
        "alignment": 0.4,
    },
    "HERETIC_NETWORK": {
        "axes": {"TECHNICISM": 0.45, "MERCANTILISM": 0.3, "ORTHODOXY": 0.05, "MILITARISM": 0.2},
        "rituals": ("HERESY_GATHERING", "WATER_VIGIL"),
        "alignment": -0.3,
    },
}

RITUAL_INTERVAL_DAYS = 14
RITUAL_TYPES = (
    "WATER_VIGIL",
    "PUBLIC_PENITENCE",
    "MARTIAL_PARADE",
    "HEALING_RITES",
    "HERESY_GATHERING",
)


def _clamp01(value: float, *, hi: float = 1.0) -> float:
    return max(0.0, min(float(value), hi))


def _stable_float(parts: Iterable[object], *, salt: str) -> float:
    joined = "|".join(str(p) for p in parts)
    digest = sha256((salt + joined).encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12)


def ensure_religion_config(world: Any) -> ReligionConfig:
    cfg = getattr(world, "religion_cfg", None)
    if not isinstance(cfg, ReligionConfig):
        cfg = ReligionConfig()
        world.religion_cfg = cfg
    return cfg


def ensure_sect(world: Any, sect_id: str, archetype: str) -> SectState:
    bucket: dict[str, SectState] = getattr(world, "sects", {}) or {}
    sect = bucket.get(sect_id)
    if not isinstance(sect, SectState):
        archetype_data = SECT_ARCHETYPES.get(archetype, {})
        sect = SectState(
            sect_id=str(sect_id),
            archetype=str(archetype),
            doctrine={axis: float(archetype_data.get("axes", {}).get(axis, 0.0)) for axis in AXES},
        )
        bucket[sect_id] = sect
    world.sects = bucket
    return sect


def ensure_default_sects(world: Any) -> None:
    for archetype in SECT_ARCHETYPES:
        sect_id = f"sect:{archetype.lower()}"
        ensure_sect(world, sect_id=sect_id, archetype=archetype)


def ensure_ward_religion(world: Any, ward_id: str) -> WardReligionState:
    bucket: dict[str, WardReligionState] = getattr(world, "religion_by_ward", {}) or {}
    state = bucket.get(ward_id)
    if not isinstance(state, WardReligionState):
        state = WardReligionState(ward_id=ward_id)
        bucket[ward_id] = state
    world.religion_by_ward = bucket
    return state


def _normalize_distribution(shares: Mapping[str, float]) -> dict[str, float]:
    positive = {k: max(0.0, float(v)) for k, v in shares.items() if v is not None}
    total = sum(positive.values())
    if total <= 0.0:
        return {k: 0.0 for k in shares}
    return {k: v / total for k, v in positive.items()}


def _ward_crisis_score(world: Any, ward_id: str) -> float:
    score = 0.0
    health = getattr(world, "health_by_ward", {}).get(ward_id) if hasattr(world, "health_by_ward") else None
    if health is not None:
        score += 0.3 * sum(getattr(health, "outbreaks", {}).values())
    inst_state = getattr(world, "inst_state_by_ward", {}).get(ward_id) if hasattr(world, "inst_state_by_ward") else None
    if inst_state is not None:
        score += 0.25 * getattr(inst_state, "unrest", 0.0)
    return _clamp01(score)


def _media_sermon_effects(world: Any, ward_id: str, *, day: int, cfg: ReligionConfig) -> tuple[dict[str, float], dict[str, float]]:
    inbox = getattr(world, "media_inbox_by_ward", {}).get(ward_id)
    if not inbox:
        return {}, {}
    if not hasattr(world, "media_in_flight"):
        return {}, {}
    adherence_delta: dict[str, float] = defaultdict(float)
    axis_delta: dict[str, float] = defaultdict(float)
    for msg_id in list(inbox):
        msg: MediaMessage | None = world.media_in_flight.get(msg_id)
        if msg is None or msg.kind not in {"SERMON", "PROPAGANDA"}:
            continue
        already_applied = msg.notes.get("religion_applied_day")
        if already_applied == day:
            continue
        msg.notes["religion_applied_day"] = day
        payload = getattr(msg, "payload", {}) or {}
        sect_id = payload.get("sect_id")
        if sect_id:
            adherence_delta[str(sect_id)] += cfg.conversion_rate * 0.5
        target_axis = payload.get("axis")
        if target_axis in AXES:
            axis_delta[str(target_axis)] += 0.1
    return adherence_delta, axis_delta


def _apply_axes_shift(world: Any, ward_id: str, deltas: Mapping[str, float]) -> None:
    if not deltas:
        return
    state = ensure_ward_ideology(world, ward_id)
    axes = dict(state.curriculum_axes) or {axis: 1.0 / len(AXES) for axis in AXES}
    for axis, delta in deltas.items():
        axes[axis] = _clamp01(axes.get(axis, 0.0) + delta)
    normalized = _normalize_distribution({axis: axes.get(axis, 0.0) for axis in AXES})
    state.curriculum_axes = normalized


def _apply_ritual_effect(world: Any, ward_id: str, ritual: str, *, driver: float, cfg: ReligionConfig) -> None:
    inst_state = ensure_state(world, ward_id)
    effect = cfg.ritual_effect_scale * (1.0 + driver)
    metrics = ensure_metrics(world)
    metrics.inc("religion.rituals_performed", 1.0)
    if ritual == "WATER_VIGIL":
        inst_state.unrest = _clamp01(inst_state.unrest - 0.3 * effect)
        inst_state.legitimacy = _clamp01(inst_state.legitimacy + 0.2 * effect)
    elif ritual == "PUBLIC_PENITENCE":
        inst_state.legitimacy = _clamp01(inst_state.legitimacy + 0.25 * effect)
        inst_state.unrest = _clamp01(inst_state.unrest + 0.1 * getattr(inst_state, "suppression", 0.0))
    elif ritual == "MARTIAL_PARADE":
        inst_state.discipline = _clamp01(inst_state.discipline + 0.3 * effect)
        inst_state.legitimacy = _clamp01(inst_state.legitimacy + 0.05 * effect)
        _apply_axes_shift(world, ward_id, {"MILITARISM": 0.1 * effect})
    elif ritual == "HEALING_RITES":
        health_state = getattr(world, "health_by_ward", {}).get(ward_id) if hasattr(world, "health_by_ward") else None
        if health_state is not None:
            for disease, intensity in list(getattr(health_state, "outbreaks", {}).items()):
                health_state.outbreaks[disease] = max(0.0, intensity * (1.0 - 0.5 * effect))
        inst_state.legitimacy = _clamp01(inst_state.legitimacy + 0.1 * effect)
    elif ritual == "HERESY_GATHERING":
        ward = getattr(world, "wards", {}).get(ward_id)
        if ward is not None:
            ward.smuggle_risk = _clamp01(getattr(ward, "smuggle_risk", 0.1) + 0.2 * effect, hi=2.0)
        inst_state.unrest = _clamp01(inst_state.unrest + 0.15 * effect)
        _apply_axes_shift(world, ward_id, {"MERCANTILISM": 0.1 * effect, "TECHNICISM": 0.05 * effect})
    record_event(
        world,
        {
            "type": "RITUAL_PERFORMED",
            "ward_id": ward_id,
            "ritual": ritual,
            "day": getattr(world, "day", 0),
            "effect_scale": round(effect, 4),
        },
    )


def _schedule_ritual(ward_state: WardReligionState, *, day: int, sect_id: str, cfg: ReligionConfig) -> None:
    archetype = ward_state.notes.get("last_sect_archetype") if ward_state.notes else None
    rit_prefs: Iterable[str] = ()
    if archetype:
        rit_prefs = SECT_ARCHETYPES.get(str(archetype), {}).get("rituals", ())
    if not rit_prefs:
        rit_prefs = RITUAL_TYPES
    choice_idx = int(_stable_float((ward_state.ward_id, sect_id, day), salt=cfg.deterministic_salt) * len(tuple(rit_prefs)))
    choice_idx = min(choice_idx, len(tuple(rit_prefs)) - 1)
    ritual = tuple(rit_prefs)[choice_idx]
    ward_state.ritual_calendar[ritual] = day + max(cfg.update_cadence_days, RITUAL_INTERVAL_DAYS)


def _update_clergy_and_tithes(state: WardReligionState, *, suppression: float, cfg: ReligionConfig) -> None:
    clergy: dict[str, float] = {}
    for sect_id, adherence in sorted(state.adherence.items()):
        prev = state.clergy_power.get(sect_id, 0.0)
        clergy[sect_id] = _clamp01(prev * (1.0 - 0.3 * suppression) + adherence * 0.7)
    state.clergy_power = clergy
    state.tithe_rate = round(sum(clergy.values()) * 0.05, 4)


def _update_global_strength(world: Any) -> None:
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for state in getattr(world, "religion_by_ward", {}).values():
        for sect_id, share in state.adherence.items():
            totals[sect_id] += share
            counts[sect_id] += 1
    for sect_id, sect in getattr(world, "sects", {}).items():
        denom = max(1, counts.get(sect_id, 0))
        sect.global_strength = round(totals.get(sect_id, 0.0) / denom, 6)


def _candidate_sects(world: Any, state: WardReligionState, cfg: ReligionConfig) -> list[str]:
    sect_ids = sorted(getattr(world, "sects", {}).keys())[: cfg.max_sects_per_ward]
    for sect_id in sect_ids:
        state.adherence.setdefault(sect_id, 0.0)
    return sect_ids


def religion_signature(world: Any) -> str:
    data = {
        "sects": {
            sect_id: {
                "archetype": sect.archetype,
                "strength": round(sect.global_strength, 6),
                "doctrine": {k: round(v, 4) for k, v in sorted(sect.doctrine.items())},
            }
            for sect_id, sect in sorted(getattr(world, "sects", {}).items())
        },
        "wards": {
            ward_id: {
                "adherence": {k: round(v, 4) for k, v in sorted(state.adherence.items())},
                "clergy": {k: round(v, 4) for k, v in sorted(state.clergy_power.items())},
                "tithe": round(state.tithe_rate, 4),
                "calendar": dict(sorted(state.ritual_calendar.items())),
            }
            for ward_id, state in sorted(getattr(world, "religion_by_ward", {}).items())
        },
    }
    payload = str(sorted(data.items()))
    return sha256(payload.encode("utf-8")).hexdigest()


def run_religion_for_week(world: Any, *, day: int) -> None:
    cfg = ensure_religion_config(world)
    if not cfg.enabled:
        return
    if day % max(1, int(cfg.update_cadence_days)) != 0:
        return
    ensure_default_sects(world)
    wards = sorted(getattr(world, "wards", {}) or {})
    metrics = ensure_metrics(world)
    adherence_totals = 0.0
    suppression_total = 0.0
    for ward_id in wards:
        state = ensure_ward_religion(world, ward_id)
        if state.last_update_day == day:
            continue
        policy = ensure_policy(world, ward_id)
        inst_state = ensure_state(world, ward_id)
        suppression = _clamp01(getattr(policy, "suppression_intensity", 0.0))
        tolerance = _clamp01(getattr(policy, "religious_tolerance", 0.5))
        state_church_bias = _clamp01(getattr(policy, "state_church_bias", 0.0))
        crisis = _ward_crisis_score(world, ward_id)
        media_shift, axis_shift = _media_sermon_effects(world, ward_id, day=day, cfg=cfg)

        candidates = _candidate_sects(world, state, cfg)
        for sect_id in candidates:
            sect = ensure_sect(world, sect_id, getattr(world.sects[sect_id], "archetype", "ORTHODOX_CHURCH"))
            base = cfg.conversion_rate * (1.0 + crisis + tolerance)
            alignment = SECT_ARCHETYPES.get(sect.archetype, {}).get("alignment", 0.0)
            alignment_bonus = 0.5 * max(0.0, alignment)
            delta = base + alignment_bonus * state_church_bias
            delta += media_shift.get(sect_id, 0.0)
            if sect.archetype == "HERETIC_NETWORK":
                delta += 0.5 * crisis
            prev = state.adherence.get(sect_id, 0.0)
            updated = prev + delta
            if suppression > 0.0 and alignment <= 0:
                updated *= 1.0 - 0.5 * suppression
                updated -= suppression * cfg.conversion_rate
            state.adherence[sect_id] = _clamp01(updated)
            state.notes["last_sect_archetype"] = sect.archetype

        state.adherence = _normalize_distribution(state.adherence)
        if suppression > 0.0:
            for sect_id in list(state.adherence):
                sect = world.sects.get(sect_id)
                alignment = 0.0
                if sect is not None:
                    alignment = SECT_ARCHETYPES.get(sect.archetype, {}).get("alignment", 0.0)
                if alignment <= 0.0:
                    state.adherence[sect_id] = _clamp01(state.adherence[sect_id] * (1.0 - suppression))
            state.adherence = _normalize_distribution(state.adherence)
        _apply_axes_shift(world, ward_id, axis_shift)

        if suppression > 0.0:
            inst_state.unrest = _clamp01(inst_state.unrest + suppression * 0.1)
            transfer(
                world,
                day=day,
                from_acct=STATE_TREASURY,
                to_acct="acct:enforcement",
                amount=cfg.suppression_cost_scale * suppression,
                reason="PAY_RELIGION_SUPPRESSION",
                meta={"ward_id": ward_id},
            )
        if state_church_bias > 0.0:
            transfer(
                world,
                day=day,
                from_acct=STATE_TREASURY,
                to_acct="acct:state_church",
                amount=cfg.ritual_effect_scale * state_church_bias,
                reason="PAY_STATE_CHURCH",
                meta={"ward_id": ward_id},
            )

        _update_clergy_and_tithes(state, suppression=suppression, cfg=cfg)
        suppression_total += suppression
        adherence_totals += sum(state.adherence.values())

        due: list[str] = []
        for ritual, due_day in list(state.ritual_calendar.items()):
            if day >= due_day:
                due.append(ritual)
        if not state.ritual_calendar:
            top_sect = max(state.adherence.items(), key=lambda item: (item[1], item[0]))[0] if state.adherence else candidates[0]
            _schedule_ritual(state, day=day, sect_id=top_sect, cfg=cfg)
        for ritual in due:
            _apply_ritual_effect(world, ward_id, ritual, driver=crisis, cfg=cfg)
            state.ritual_calendar[ritual] = day + max(cfg.update_cadence_days, RITUAL_INTERVAL_DAYS)

        state.suppression_level = suppression
        state.last_update_day = day

    _update_global_strength(world)
    ward_count = len(wards)
    gauges = getattr(metrics, "gauges", None)
    if isinstance(gauges, dict):
        bucket = gauges.setdefault("religion", {})
        if ward_count:
            bucket["suppression_avg"] = round(suppression_total / ward_count, 4)
            bucket["adherence_avg_by_sect"] = {
                sect_id: round(sect.global_strength, 4) for sect_id, sect in getattr(world, "sects", {}).items()
            }
            bucket["tithes_collected"] = round(
                sum(state.tithe_rate for state in getattr(world, "religion_by_ward", {}).values()), 4
            )
