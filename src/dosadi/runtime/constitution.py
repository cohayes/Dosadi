from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.sovereignty import TerritoryState, ensure_sovereignty_state
from dosadi.runtime.telemetry import ensure_metrics, record_event


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_rand01(*parts: object) -> float:
    blob = "|".join(str(p) for p in parts)
    digest = sha256(blob.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


RIGHTS_DIMENSIONS = (
    "due_process",
    "movement",
    "speech",
    "labor_organizing",
    "property_security",
    "religious_freedom",
)

CONSTRAINT_DIMENSIONS = ("court_independence", "audit_independence", "term_limits")


@dataclass(slots=True)
class ConstitutionConfig:
    enabled: bool = False
    update_cadence_days: int = 30
    deterministic_salt: str = "constitution-v1"
    adoption_rate_base: float = 0.001
    rollback_rate_p2: float = 0.004
    rights_effect_scale: float = 0.25
    crisis_threshold: float = 0.70


@dataclass(slots=True)
class Settlement:
    settlement_id: str
    polity_id: str
    name: str
    governance_form: str
    rights: dict[str, float]
    constraints: dict[str, float]
    emergency_power_ease: float
    adopted_day: int
    status: str = "ACTIVE"
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ConstitutionState:
    polity_id: str
    active_settlement_id: str | None = None
    rights_current: dict[str, float] = field(default_factory=dict)
    constraints_current: dict[str, float] = field(default_factory=dict)
    emergency_active: bool = False
    emergency_until_day: int = -1
    last_update_day: int = -1


@dataclass(slots=True)
class ConstitutionalEvent:
    day: int
    polity_id: str
    kind: str
    settlement_id: str | None
    reason_codes: list[str]


def ensure_constitution_config(world: Any) -> ConstitutionConfig:
    cfg = getattr(world, "constitution_cfg", None)
    if not isinstance(cfg, ConstitutionConfig):
        cfg = ConstitutionConfig()
        world.constitution_cfg = cfg
    return cfg


def ensure_settlements(world: Any) -> dict[str, Settlement]:
    settlements = getattr(world, "settlements", None)
    if isinstance(settlements, dict):
        return settlements
    settlements = {}
    world.settlements = settlements
    return settlements


def ensure_constitution_state(world: Any, *, polities: Iterable[str]) -> dict[str, ConstitutionState]:
    state = getattr(world, "constitution_by_polity", None)
    if not isinstance(state, dict):
        state = {}
    for polity_id in polities:
        if isinstance(state.get(polity_id), ConstitutionState):
            continue
        state[polity_id] = ConstitutionState(polity_id=polity_id)
    world.constitution_by_polity = state
    return state


def ensure_constitution_events(world: Any) -> list[ConstitutionalEvent]:
    events = getattr(world, "constitution_events", None)
    if isinstance(events, list):
        return events
    events = []
    world.constitution_events = events
    return events


def _polities(world: Any) -> list[str]:
    state = ensure_sovereignty_state(world)
    polities = sorted(getattr(state, "polities", {}).keys())
    return polities or ["polity:empire"]


def _polity_for_ward(territory: TerritoryState, ward_id: str) -> str:
    owner = territory.ward_control.get(ward_id)
    if owner:
        return str(owner)
    return "polity:empire"


def _settlement_name(polity_id: str, current_day: int) -> str:
    return f"Settlement {polity_id.split(':')[-1]} @ day {current_day}"


def _governance_form(world: Any, polity_id: str) -> str:
    leadership = getattr(world, "leadership_by_polity", {}).get(polity_id)
    office = getattr(leadership, "office_type", "COUNCIL") or "COUNCIL"
    mapping = {
        "COUNCIL": "REPUBLIC",
        "SOVEREIGN": "MONARCHY_COUNCIL",
        "HIEROPHANT": "THEOCRACY",
        "GENERAL": "JUNTA",
    }
    return mapping.get(str(office).upper(), "REPUBLIC")


def _rights_payload(seed: int, polity_id: str, day: int, governance_form: str) -> tuple[dict[str, float], dict[str, float], float]:
    base = 0.35 + 0.15 * _stable_rand01(seed, polity_id, day, governance_form)
    rights = {key: _clamp01(base) for key in RIGHTS_DIMENSIONS}
    constraints = {key: _clamp01(0.45 + 0.1 * base) for key in CONSTRAINT_DIMENSIONS}
    emergency_power = _clamp01(0.5)

    if governance_form == "THEOCRACY":
        rights["religious_freedom"] = _clamp01(0.25 + 0.1 * base)
        constraints["court_independence"] = _clamp01(0.3 + 0.1 * base)
        emergency_power = _clamp01(0.6 + 0.1 * base)
    elif governance_form == "JUNTA":
        rights["speech"] = _clamp01(0.2 + 0.1 * base)
        rights["labor_organizing"] = _clamp01(0.25 + 0.1 * base)
        emergency_power = _clamp01(0.7 + 0.1 * base)
    else:
        rights["due_process"] = _clamp01(0.6 + 0.2 * base)
        constraints["court_independence"] = _clamp01(0.5 + 0.2 * base)
        constraints["audit_independence"] = _clamp01(0.55 + 0.2 * base)

    return rights, constraints, emergency_power


def _adoption_pressure(world: Any, polity_id: str, cfg: ConstitutionConfig) -> float:
    base = cfg.adoption_rate_base
    campaigns = getattr(world, "reforms_by_polity", {}).get(polity_id, []) or []
    success = sum(1 for c in campaigns if getattr(c, "status", "").upper() == "SUCCEEDED")
    base += 0.15 * min(1.0, success / max(1, len(campaigns) or 1))

    legitimacy = getattr(getattr(world, "leadership_by_polity", {}).get(polity_id), "legitimacy", 0.5)
    base += max(0.0, (0.6 - float(legitimacy))) * 0.2
    post_conflict = getattr(world, "post_conflict_settlement", {}).get(polity_id)
    if post_conflict:
        base += 0.25
    return _clamp01(base)


def _crisis_pressure(world: Any, polity_id: str) -> float:
    pressure = float(getattr(world, "crisis_pressure", 0.0) or 0.0)
    pressure += float(getattr(world, "crisis_pressure_by_polity", {}).get(polity_id, 0.0) or 0.0)
    return _clamp01(pressure)


def _record_constitution_event(world: Any, event: ConstitutionalEvent) -> None:
    events = ensure_constitution_events(world)
    events.append(event)
    if len(events) > 300:
        del events[: len(events) - 300]
    record_event(
        world,
        {
            "type": f"CONST_{event.kind}",
            "day": event.day,
            "polity_id": event.polity_id,
            "settlement_id": event.settlement_id,
            "reason_codes": list(event.reason_codes),
        },
    )


def _apply_settlement(world: Any, state: ConstitutionState, settlement: Settlement, day: int) -> None:
    state.active_settlement_id = settlement.settlement_id
    state.rights_current = {k: _clamp01(settlement.rights.get(k, 0.0)) for k in RIGHTS_DIMENSIONS}
    state.constraints_current = {k: _clamp01(settlement.constraints.get(k, 0.0)) for k in CONSTRAINT_DIMENSIONS}
    state.emergency_until_day = -1
    state.emergency_active = False
    state.last_update_day = day


def _maybe_adopt(world: Any, *, polity_id: str, day: int, cfg: ConstitutionConfig) -> Settlement | None:
    pressure = _adoption_pressure(world, polity_id, cfg)
    roll = _stable_rand01(cfg.deterministic_salt, polity_id, day, getattr(world, "seed", 0))
    if roll >= pressure:
        return None

    governance_form = _governance_form(world, polity_id)
    rights, constraints, emergency_power = _rights_payload(getattr(world, "seed", 0), polity_id, day, governance_form)
    settlement_id = f"settlement:{polity_id}:{day}:{int(roll * 1e6):06d}"
    settlement = Settlement(
        settlement_id=settlement_id,
        polity_id=polity_id,
        name=_settlement_name(polity_id, day),
        governance_form=governance_form,
        rights=rights,
        constraints=constraints,
        emergency_power_ease=emergency_power,
        adopted_day=day,
    )
    ensure_settlements(world)[settlement_id] = settlement
    _record_constitution_event(
        world,
        ConstitutionalEvent(
            day=day,
            polity_id=polity_id,
            kind="ADOPTED",
            settlement_id=settlement_id,
            reason_codes=["REFORM_PRESSURE" if pressure > cfg.adoption_rate_base else "BASELINE"],
        ),
    )
    return settlement


def _maybe_emergency(world: Any, *, state: ConstitutionState, settlement: Settlement, day: int, cfg: ConstitutionConfig) -> None:
    pressure = _crisis_pressure(world, settlement.polity_id)
    if pressure <= cfg.crisis_threshold:
        if state.emergency_active and day >= state.emergency_until_day:
            state.emergency_active = False
            state.emergency_until_day = -1
            _record_constitution_event(
                world,
                ConstitutionalEvent(
                    day=day,
                    polity_id=settlement.polity_id,
                    kind="EMERGENCY_LIFTED",
                    settlement_id=settlement.settlement_id,
                    reason_codes=["PRESSURE_RELIEF"],
                ),
            )
        return

    roll = _stable_rand01(cfg.deterministic_salt, settlement.polity_id, day, "emergency")
    trigger = roll < _clamp01(settlement.emergency_power_ease)
    if trigger and not state.emergency_active:
        state.emergency_active = True
        state.emergency_until_day = day + max(5, int(10 * (0.5 + settlement.emergency_power_ease)))
        _record_constitution_event(
            world,
            ConstitutionalEvent(
                day=day,
                polity_id=settlement.polity_id,
                kind="EMERGENCY_DECLARED",
                settlement_id=settlement.settlement_id,
                reason_codes=["CRISIS_PRESSURE"],
            ),
        )


def maybe_update_constitution(world: Any, *, day: int | None = None) -> None:
    cfg = ensure_constitution_config(world)
    if not cfg.enabled:
        return
    current_day = int(day if day is not None else getattr(world, "day", 0))
    if current_day % max(1, int(cfg.update_cadence_days)) != 0:
        return

    polities = _polities(world)
    states = ensure_constitution_state(world, polities=polities)
    settlements = ensure_settlements(world)
    adoption_count = 0
    emergency_count = 0
    due_process_scores: list[float] = []

    for polity_id in polities:
        state = states[polity_id]
        state.last_update_day = current_day
        settlement: Settlement | None = None
        if state.active_settlement_id:
            settlement = settlements.get(state.active_settlement_id)
        if settlement is None:
            settlement = _maybe_adopt(world, polity_id=polity_id, day=current_day, cfg=cfg)
            if settlement is None:
                continue
            _apply_settlement(world, state, settlement, current_day)
            adoption_count += 1

        _maybe_emergency(world, state=state, settlement=settlement, day=current_day, cfg=cfg)
        if state.emergency_active:
            emergency_count += 1
        due_process_scores.append(state.rights_current.get("due_process", 0.0))

    metrics = ensure_metrics(world)
    bucket = getattr(metrics, "gauges", {}).setdefault("constitution", {})
    if isinstance(bucket, dict):
        bucket["polities_with_settlement"] = sum(1 for st in states.values() if st.active_settlement_id)
        if due_process_scores:
            bucket["avg_due_process"] = sum(due_process_scores) / len(due_process_scores)
        bucket["emergencies_active"] = emergency_count
        bucket["suspensions"] = sum(1 for st in states.values() if st.emergency_active)


def effective_rights(world: Any, polity_id: str, *, day: int | None = None) -> dict[str, float]:
    state = ensure_constitution_state(world, polities=[polity_id]).get(polity_id)
    if state is None:
        return {key: 0.0 for key in RIGHTS_DIMENSIONS}
    rights = {key: _clamp01(state.rights_current.get(key, 0.0)) for key in RIGHTS_DIMENSIONS}
    current_day = int(day if day is not None else getattr(world, "day", 0))
    if state.emergency_active and (state.emergency_until_day < 0 or current_day <= state.emergency_until_day):
        rights["speech"] *= 0.35
        rights["movement"] *= 0.35
    return rights


def policing_constraints_for_polity(world: Any, polity_id: str, *, day: int | None = None) -> dict[str, float]:
    rights = effective_rights(world, polity_id, day=day)
    state = ensure_constitution_state(world, polities=[polity_id]).get(polity_id)
    if state is None:
        return {}
    due_process = rights.get("due_process", 0.0)
    terror_cap = 1.0 if state.emergency_active else max(0.0, 1.0 - due_process)
    procedural_floor = max(0.0, min(0.8, due_process * 0.5))
    return {
        "terror_cap": _clamp01(terror_cap),
        "procedural_floor": _clamp01(procedural_floor),
        "emergency": bool(state.emergency_active),
    }


def policing_constraints_for_ward(world: Any, ward_id: str, *, day: int | None = None) -> dict[str, float]:
    territory = ensure_sovereignty_state(world).territory
    polity_id = _polity_for_ward(territory, ward_id)
    return policing_constraints_for_polity(world, polity_id, day=day)


def sovereignty_modifier(world: Any, ward_id: str) -> float:
    territory = ensure_sovereignty_state(world).territory
    polity_id = _polity_for_ward(territory, ward_id)
    rights = effective_rights(world, polity_id, day=getattr(world, "day", 0))
    avg = sum(rights.values()) / max(1, len(rights))
    return _clamp01(avg * 0.35)


def constitution_seed_payload(world: Any) -> dict[str, Any] | None:
    cfg = getattr(world, "constitution_cfg", None)
    if not isinstance(cfg, ConstitutionConfig) or not cfg.enabled:
        return None
    settlements = ensure_settlements(world)
    states = getattr(world, "constitution_by_polity", {}) or {}
    payload: dict[str, Any] = {
        "schema": "constitution_v1",
        "settlements": [
            {
                "settlement_id": st.settlement_id,
                "polity_id": st.polity_id,
                "governance_form": st.governance_form,
                "rights": dict(st.rights),
                "constraints": dict(st.constraints),
                "emergency_power_ease": st.emergency_power_ease,
                "adopted_day": st.adopted_day,
                "status": st.status,
            }
            for st in sorted(settlements.values(), key=lambda s: s.settlement_id)
        ],
        "state": [],
    }
    for polity_id, state in sorted(states.items()):
        payload["state"].append(
            {
                "polity_id": polity_id,
                "active_settlement_id": state.active_settlement_id,
                "rights_current": dict(state.rights_current),
                "constraints_current": dict(state.constraints_current),
                "emergency_active": state.emergency_active,
                "emergency_until_day": state.emergency_until_day,
                "last_update_day": state.last_update_day,
            }
        )
    return payload

