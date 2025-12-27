from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from dosadi.runtime.class_system import class_hardship, class_inequality
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.runtime.institutions import ensure_policy, ensure_state
from dosadi.world.factions import pseudo_rand01


LABOR_ORGS: tuple[tuple[str, str, str], ...] = (
    ("guild:couriers", "GUILD", "COURIER"),
    ("guild:maintenance", "GUILD", "MAINTENANCE"),
    ("guild:refiners", "GUILD", "REFINING"),
    ("guild:builders", "GUILD", "CONSTRUCTION"),
    ("guild:water", "GUILD", "WATER"),
    ("union:guards", "UNION", "SECURITY"),
)


def _clamp(lo: float, hi: float, value: float) -> float:
    return max(lo, min(hi, float(value)))


def _clamp01(value: float) -> float:
    return _clamp(0.0, 1.0, value)


@dataclass(slots=True)
class LaborConfig:
    enabled: bool = False
    update_cadence_days: int = 7
    max_orgs_per_ward: int = 8
    deterministic_salt: str = "labor-v1"
    base_strike_rate: float = 0.01
    negotiation_step: float = 0.15
    repression_backlash: float = 0.12
    sabotage_rate: float = 0.03


@dataclass(slots=True)
class LaborOrgState:
    org_id: str
    org_type: str
    sector: str
    ward_id: str
    strength: float = 0.0
    militancy: float = 0.0
    corruption: float = 0.0
    contract_state: dict[str, float] = field(default_factory=dict)
    status: str = "NORMAL"
    status_until_day: int = -1
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class BargainingEvent:
    day: int
    ward_id: str
    org_id: str
    kind: str
    terms: dict[str, float]
    outcome: str
    reason_codes: list[str]


def _ensure_cfg(world: Any) -> LaborConfig:
    cfg = getattr(world, "labor_cfg", None)
    if not isinstance(cfg, LaborConfig):
        cfg = LaborConfig()
        world.labor_cfg = cfg
    return cfg


def _ensure_orgs(world: Any, ward_id: str, *, cfg: LaborConfig) -> list[LaborOrgState]:
    by_ward: dict[str, list[LaborOrgState]] = getattr(world, "labor_orgs_by_ward", {}) or {}
    orgs = by_ward.get(ward_id)
    if orgs is None:
        orgs = []
    if not orgs:
        for org_id, org_type, sector in LABOR_ORGS[: cfg.max_orgs_per_ward]:
            orgs.append(LaborOrgState(org_id=org_id, org_type=org_type, sector=sector, ward_id=ward_id))
    by_ward[ward_id] = orgs
    world.labor_orgs_by_ward = by_ward
    return orgs


def _events(world: Any) -> list[BargainingEvent]:
    events: list[BargainingEvent] = getattr(world, "labor_events", []) or []
    world.labor_events = events
    return events


def _ward_grievance(world: Any, ward_id: str, org: LaborOrgState) -> float:
    wards = getattr(world, "wards", {}) or {}
    ward = wards.get(ward_id)
    if ward is None:
        return 0.0
    shortage = _clamp01(getattr(ward, "need_index", 0.0))
    infrastructure = getattr(getattr(ward, "infrastructure", None), "maintenance_index", 0.0)
    safety = _clamp01(1.0 - infrastructure)
    inst_state = ensure_state(world, ward_id)
    corruption = _clamp01(getattr(inst_state, "corruption", 0.0))
    unrest = _clamp01(getattr(inst_state, "unrest", 0.0))
    hardship = class_hardship(world, ward_id)
    inequality = class_inequality(world, ward_id)
    weight = 0.45 * shortage + 0.25 * safety + 0.15 * corruption + 0.1 * unrest
    weight += 0.15 * hardship + 0.10 * inequality
    if org.org_type == "UNION":
        weight += 0.05 * shortage
    return _clamp01(weight)


def _ward_power(world: Any, ward_id: str, org: LaborOrgState) -> float:
    wards = getattr(world, "wards", {}) or {}
    ward = wards.get(ward_id)
    if ward is None:
        return 0.0
    specialization = 0.0
    for key, value in getattr(ward, "specialisations", {}).items():
        if key.lower().startswith(org.sector.lower()[:3]):
            specialization = max(specialization, float(value))
    scarcity = 0.2 if len(getattr(ward, "specialisations", {})) <= 1 else 0.0
    return _clamp01(0.6 * specialization + scarcity)


def _labor_roll(world: Any, day: int, org_id: str, salt: str) -> float:
    return pseudo_rand01(f"{salt}:{getattr(world, 'seed', 0)}:{day}:{org_id}")


def _append_event(world: Any, event: BargainingEvent) -> None:
    events = _events(world)
    events.append(event)
    max_events = 200
    if len(events) > max_events:
        del events[:-max_events]


def _update_metrics(world: Any, *, ward_id: str, orgs: Iterable[LaborOrgState]) -> None:
    telemetry = ensure_metrics(world)
    labor_metrics = telemetry.gauges.setdefault("labor", {})
    if not isinstance(labor_metrics, dict):
        labor_metrics = {}
        telemetry.gauges["labor"] = labor_metrics
    strikes = sum(1 for org in orgs if org.status == "STRIKE")
    slowdowns = sum(1 for org in orgs if org.status == "SLOWDOWN")
    labor_metrics[f"{ward_id}.strikes"] = float(strikes)
    labor_metrics[f"{ward_id}.slowdowns"] = float(slowdowns)
    labor_metrics[f"{ward_id}.militancy_max"] = max((org.militancy for org in orgs), default=0.0)


def _apply_response(world: Any, *, day: int, ward_id: str, org: LaborOrgState, cfg: LaborConfig) -> None:
    policy = ensure_policy(world, ward_id)
    negotiate_bias = float(getattr(policy, "labor_negotiation_bias", 0.0))
    repression_bias = float(getattr(policy, "labor_repression_bias", 0.0))
    patronage_bias = float(getattr(policy, "labor_patronage_bias", 0.0))

    negotiate_score = 0.5 + negotiate_bias - 0.2 * patronage_bias
    repress_score = 0.4 + repression_bias + 0.1 * max(org.militancy - 0.4, 0.0)
    if negotiate_score >= repress_score:
        org.contract_state["wage"] = _clamp01(org.contract_state.get("wage", 0.0) + 0.1 + 0.1 * negotiate_bias)
        org.contract_state["safety"] = _clamp01(org.contract_state.get("safety", 0.0) + 0.05)
        org.militancy = _clamp01(org.militancy - cfg.negotiation_step)
        org.status = "NORMAL"
        org.status_until_day = day
        _append_event(
            world,
            BargainingEvent(
                day=day,
                ward_id=ward_id,
                org_id=org.org_id,
                kind="AGREEMENT",
                terms=dict(org.contract_state),
                outcome="ACCEPTED",
                reason_codes=["negotiation"],
            ),
        )
    else:
        org.strength = _clamp01(org.strength - 0.05)
        org.militancy = _clamp01(org.militancy + cfg.repression_backlash + patronage_bias * 0.05)
        org.status_until_day = max(org.status_until_day, day + 3)
        _append_event(
            world,
            BargainingEvent(
                day=day,
                ward_id=ward_id,
                org_id=org.org_id,
                kind="REPRESSION",
                terms={},
                outcome="BACKLASH",
                reason_codes=["repression"],
            ),
        )


def update_labor_for_day(world: Any, *, day: int) -> None:
    cfg = _ensure_cfg(world)
    if not getattr(cfg, "enabled", False):
        return
    wards = getattr(world, "wards", {}) or {}
    for ward_id in sorted(wards.keys()):
        orgs = _ensure_orgs(world, ward_id, cfg=cfg)
        for org in orgs:
            if org.status_until_day >= 0 and day < org.status_until_day and org.last_update_day == day:
                continue
            if org.status_until_day >= 0 and day >= org.status_until_day:
                org.status = "NORMAL"
            if org.last_update_day >= 0 and day - org.last_update_day < max(1, int(cfg.update_cadence_days)):
                continue

            grievance = _ward_grievance(world, ward_id, org)
            power = _ward_power(world, ward_id, org)
            org.strength = _clamp01(org.strength + 0.2 * power)
            org.militancy = _clamp01(0.55 * org.militancy + 0.35 * grievance + 0.15 * power)

            inst_state = ensure_state(world, ward_id)
            legitimacy = _clamp01(getattr(inst_state, "legitimacy", 0.0))
            p_action = _clamp01(cfg.base_strike_rate + 0.6 * grievance + 0.35 * org.militancy - 0.25 * legitimacy)
            roll = _labor_roll(world, day, org.org_id, cfg.deterministic_salt)
            if roll < p_action:
                org.status = "STRIKE" if org.militancy > 0.6 else "SLOWDOWN"
                duration = 7 + int(7 * org.militancy)
                org.status_until_day = day + duration
                _append_event(
                    world,
                    BargainingEvent(
                        day=day,
                        ward_id=ward_id,
                        org_id=org.org_id,
                        kind=org.status,
                        terms={},
                        outcome="TRIGGERED",
                        reason_codes=["grievance", f"p={p_action:.3f}"],
                    ),
                )
                _apply_response(world, day=day, ward_id=ward_id, org=org, cfg=cfg)
            org.last_update_day = day
        _update_metrics(world, ward_id=ward_id, orgs=orgs)


def labor_sector_multiplier(world: Any, ward_id: str | None, sector: str) -> float:
    if ward_id is None:
        return 1.0
    cfg = _ensure_cfg(world)
    if not getattr(cfg, "enabled", False):
        return 1.0
    orgs = _ensure_orgs(world, str(ward_id), cfg=cfg)
    day = getattr(world, "day", 0)
    mult = 1.0
    for org in orgs:
        if org.sector != sector:
            continue
        if org.status in {"STRIKE", "SLOWDOWN", "LOCKOUT"} and (org.status_until_day < 0 or day <= org.status_until_day):
            impact = 0.75 if org.status == "SLOWDOWN" else 0.5
            mult = min(mult, impact)
    return _clamp01(mult)
