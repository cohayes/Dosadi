from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event


SECT_ARCHETYPES: Mapping[str, Mapping[str, object]] = {
    "ORTHODOX": {
        "doctrine": {"purity": 0.8, "hierarchy": 0.9, "violence": 0.2, "universalism": 0.5},
    },
    "ASCETIC_REFORM": {
        "doctrine": {"purity": 0.7, "hierarchy": 0.3, "violence": 0.2, "universalism": 0.4},
    },
    "MARTYR_CULT": {
        "doctrine": {"purity": 0.4, "hierarchy": 0.2, "violence": 0.7, "universalism": 0.2},
    },
    "WELL_MYSTICS": {
        "doctrine": {"purity": 0.5, "hierarchy": 0.6, "violence": 0.3, "universalism": 0.6},
    },
    "SYNTHETISTS": {
        "doctrine": {"purity": 0.2, "hierarchy": 0.2, "violence": 0.1, "universalism": 0.9},
    },
    "APOCALYPTIC": {
        "doctrine": {"purity": 0.6, "hierarchy": 0.2, "violence": 0.8, "universalism": 0.3},
    },
}


@dataclass(slots=True)
class SectsConfig:
    enabled: bool = False
    update_cadence_days: int = 14
    deterministic_salt: str = "sects-v1"
    max_sects_total: int = 24
    max_sects_per_polity: int = 6
    schism_base_rate: float = 0.001
    schism_pressure_scale: float = 0.35
    diffusion_rate: float = 0.05
    holy_conflict_threshold: float = 0.70


@dataclass(slots=True)
class SectDef:
    sect_id: str
    name: str
    archetype: str
    doctrine: dict[str, float]
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class PolitySectState:
    polity_id: str
    strength_by_sect: dict[str, float] = field(default_factory=dict)
    schism_pressure: float = 0.0
    conflict_intensity: float = 0.0
    dominant_sect: str | None = None
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SchismEvent:
    day: int
    polity_id: str
    parent_sect_id: str
    new_sect_id: str
    reason_codes: list[str]
    backers: list[str]


_DEF_PREFIX = "sect"


def _clamp01(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _stable_float(parts: Iterable[object], *, salt: str) -> float:
    digest = sha256("|".join(str(p) for p in parts).encode("utf-8") + salt.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12)


def _stable_choice(sequence: list[str], *, salt: str, parts: Iterable[object]) -> str:
    if not sequence:
        raise ValueError("Cannot choose from empty sequence")
    idx = int(_stable_float(parts, salt=salt) * len(sequence)) % len(sequence)
    return sequence[idx]


def ensure_sects_config(world: Any) -> SectsConfig:
    cfg = getattr(world, "sects_cfg", None)
    if not isinstance(cfg, SectsConfig):
        cfg = SectsConfig()
        world.sects_cfg = cfg
    return cfg


def ensure_sect_def(world: Any, sect_id: str, archetype: str, *, name: str | None = None) -> SectDef:
    bucket: dict[str, SectDef] = getattr(world, "sects", {}) or {}
    sect = bucket.get(sect_id)
    if isinstance(sect, SectDef):
        world.sects = bucket
        return sect
    archetype_data = SECT_ARCHETYPES.get(archetype, {})
    sect = SectDef(
        sect_id=str(sect_id),
        name=name or sect_id,
        archetype=archetype,
        doctrine={k: float(v) for k, v in (archetype_data.get("doctrine") or {}).items()},
    )
    bucket[sect_id] = sect
    world.sects = bucket
    return sect


def ensure_default_sects(world: Any) -> None:
    for archetype in SECT_ARCHETYPES:
        sect_id = f"{_DEF_PREFIX}:{archetype.lower()}"
        ensure_sect_def(world, sect_id, archetype, name=archetype.replace("_", " ").title())


def ensure_polity_sect_state(world: Any, polity_id: str) -> PolitySectState:
    bucket: dict[str, PolitySectState] = getattr(world, "sects_by_polity", {}) or {}
    state = bucket.get(polity_id)
    if not isinstance(state, PolitySectState):
        state = PolitySectState(polity_id=polity_id)
        bucket[polity_id] = state
    world.sects_by_polity = bucket
    return state


def _normalize_strengths(shares: Mapping[str, float]) -> dict[str, float]:
    positive = {k: max(0.0, float(v)) for k, v in shares.items() if v is not None}
    total = sum(positive.values())
    if total <= 0:
        return {k: 0.0 for k in shares}
    return {k: v / total for k, v in positive.items()}


def _collect_pressure_signals(world: Any, polity_id: str) -> float:
    hardship = getattr(world, "hardship_by_polity", {}).get(polity_id, 0.0)
    culture = getattr(world, "culture_war_by_polity", {}).get(polity_id, 0.0)
    legitimacy_gap = getattr(world, "legitimacy_gap_by_polity", {}).get(polity_id, 0.0)
    policing_terror = getattr(world, "policing_terror_by_polity", {}).get(polity_id, 0.0)
    media_distortion = getattr(world, "media_distortion_by_polity", {}).get(polity_id, 0.0)
    war_pressure = getattr(world, "war_pressure_by_polity", {}).get(polity_id, 0.0)
    weighted = 0.15 * hardship + 0.2 * culture + 0.15 * legitimacy_gap + 0.15 * policing_terror + 0.1 * media_distortion + 0.25 * war_pressure
    return _clamp01(weighted)


def _generate_new_sect(world: Any, *, parent: SectDef, polity_id: str, cfg: SectsConfig, index_hint: int) -> SectDef:
    salt_parts = (world.seed, polity_id, parent.sect_id, index_hint)
    archetype = _stable_choice(list(SECT_ARCHETYPES), salt=cfg.deterministic_salt, parts=salt_parts)
    nonce = int(_stable_float(salt_parts, salt=cfg.deterministic_salt) * 10_000)
    sect_id = f"{_DEF_PREFIX}:{archetype.lower()}:{nonce}"
    parent_doctrine = parent.doctrine
    mutated = {}
    for axis, value in parent_doctrine.items():
        jitter = (_stable_float((axis, *salt_parts), salt=cfg.deterministic_salt) - 0.5) * 0.1
        mutated[axis] = _clamp01(value + jitter)
    sect = ensure_sect_def(world, sect_id, archetype, name=f"{archetype.title()} ({polity_id})")
    sect.doctrine = mutated
    return sect


def _bounded_append(events: list[SchismEvent], event: SchismEvent, *, max_events: int) -> list[SchismEvent]:
    events.append(event)
    if len(events) > max_events:
        events.pop(0)
    return events


def _update_dominant(state: PolitySectState) -> None:
    if not state.strength_by_sect:
        state.dominant_sect = None
        return
    dominant = max(state.strength_by_sect.items(), key=lambda item: item[1])
    state.dominant_sect = dominant[0] if dominant[1] > 0 else None


def _update_diffusion(world: Any, polity_id: str, state: PolitySectState, *, cfg: SectsConfig) -> None:
    repression = getattr(world, "policing_repression_by_polity", {}).get(polity_id, 0.0)
    martyr_bonus = repression * 0.2
    adjustments: dict[str, float] = {}
    for sect_id, share in state.strength_by_sect.items():
        sect_def = getattr(world, "sects", {}).get(sect_id)
        if isinstance(sect_def, SectDef) and sect_def.archetype == "MARTYR_CULT":
            adjustments[sect_id] = share + cfg.diffusion_rate * (1.0 + martyr_bonus)
        else:
            adjustments[sect_id] = share + cfg.diffusion_rate * (1.0 - repression * 0.5)
    normalized = _normalize_strengths(adjustments)
    state.strength_by_sect = normalized


def _maybe_trigger_schism(world: Any, polity_id: str, state: PolitySectState, *, day: int, cfg: SectsConfig) -> None:
    total_sects = len(getattr(world, "sects", {}))
    if total_sects >= cfg.max_sects_total:
        return
    if len(state.strength_by_sect) >= cfg.max_sects_per_polity:
        return
    parent_id = None
    parent_strength = -1.0
    for sid, strength in state.strength_by_sect.items():
        if strength > parent_strength:
            parent_id = sid
            parent_strength = strength
    if parent_id is None:
        return
    parent_def: SectDef | None = getattr(world, "sects", {}).get(parent_id)
    if parent_def is None:
        return
    trigger_chance = cfg.schism_base_rate * (1.0 + cfg.schism_pressure_scale * state.schism_pressure)
    pseudo_rand = _stable_float((world.seed, polity_id, day, parent_id), salt=cfg.deterministic_salt)
    if pseudo_rand >= trigger_chance:
        return
    new_sect = _generate_new_sect(world, parent=parent_def, polity_id=polity_id, cfg=cfg, index_hint=total_sects)
    transfer = min(0.1, parent_strength * 0.25)
    state.strength_by_sect[parent_id] = max(0.0, parent_strength - transfer)
    state.strength_by_sect[new_sect.sect_id] = transfer
    world.schism_events = _bounded_append(
        list(getattr(world, "schism_events", []) or []),
        SchismEvent(
            day=day,
            polity_id=polity_id,
            parent_sect_id=parent_id,
            new_sect_id=new_sect.sect_id,
            reason_codes=["SCHISM_PRESSURE"],
            backers=[polity_id],
        ),
        max_events=cfg.max_sects_total,
    )
    ensure_metrics(world).inc("sects.schism_events", 1)


def _update_conflict(world: Any, polity_id: str, state: PolitySectState, *, cfg: SectsConfig) -> None:
    _update_dominant(state)
    dominant_share = state.strength_by_sect.get(state.dominant_sect, 0.0) if state.dominant_sect else 0.0
    sponsor_alignment = getattr(world, "leadership_sponsor_alignment", {}).get(polity_id, 0.0)
    if (dominant_share > cfg.holy_conflict_threshold or state.conflict_intensity > cfg.holy_conflict_threshold) and sponsor_alignment > 0.5:
        state.conflict_intensity = _clamp01(state.conflict_intensity + 0.1 + 0.2 * dominant_share)
        record_event(
            world,
            {
                "kind": "HOLY_CONFLICT_ESCALATED",
                "polity_id": polity_id,
                "sect_id": state.dominant_sect,
            },
        )
        ensure_metrics(world).inc("sects.holy_conflicts_active", 1)
    else:
        state.conflict_intensity = _clamp01(state.conflict_intensity * 0.95)


def update_sects(world: Any, *, day: int) -> None:
    cfg = ensure_sects_config(world)
    if not cfg.enabled:
        return
    ensure_default_sects(world)
    polities: Iterable[str]
    if hasattr(world, "polities"):
        polities = getattr(world, "polities") or []
    else:
        polities = getattr(world, "sects_by_polity", {}).keys() or []
    for polity_id in polities:
        state = ensure_polity_sect_state(world, polity_id)
        if state.last_update_day >= 0 and (day - state.last_update_day) < cfg.update_cadence_days:
            continue
        state.schism_pressure = _collect_pressure_signals(world, polity_id)
        _maybe_trigger_schism(world, polity_id, state, day=day, cfg=cfg)
        _update_diffusion(world, polity_id, state, cfg=cfg)
        _update_conflict(world, polity_id, state, cfg=cfg)
        state.last_update_day = day
    ensure_metrics(world).set_gauge("sects.avg_schism_pressure", _average_pressure(world))


def _average_pressure(world: Any) -> float:
    bucket: Mapping[str, PolitySectState] = getattr(world, "sects_by_polity", {}) or {}
    if not bucket:
        return 0.0
    return sum(state.schism_pressure for state in bucket.values()) / len(bucket)
