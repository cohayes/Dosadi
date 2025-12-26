"""Diplomacy & treaties v1 runtime helpers.

This module implements a light-weight, deterministic contract layer for
stabilising corridor traffic and resource sharing between wards. It mirrors the
v1 checklist (D-RUNTIME-0274) with bounded proposal/acceptance, obligation
execution, breach detection, telemetry, and seed-vault persistence.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping, MutableMapping

from dosadi.runtime.ledger import transfer
from dosadi.runtime.telemetry import ensure_event_ring, ensure_metrics, record_event
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, LogisticsLedger, ensure_logistics


@dataclass(slots=True)
class TreatyConfig:
    enabled: bool = False
    max_active_treaties: int = 200
    max_new_treaties_per_day: int = 3
    counterparty_topk: int = 12
    corridor_topk: int = 24
    deterministic_salt: str = "treaties-v1"
    default_duration_days: int = 60
    renewal_window_days: int = 10
    breach_threshold: float = 1.0
    breach_increment: float = 0.6
    breach_decay: float = 0.1
    history_max: int = 50


@dataclass(slots=True)
class TreatyObligation:
    kind: str
    material: str | None = None
    amount: int | float | None = None
    cadence_days: int = 1
    corridor_ids: list[str] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class TreatyTerms:
    treaty_type: str
    party_a: str
    party_b: str
    obligations_a: list[TreatyObligation]
    obligations_b: list[TreatyObligation]
    consideration: dict[str, object] = field(default_factory=dict)
    penalties: dict[str, object] = field(default_factory=dict)
    duration_days: int = 60


@dataclass(slots=True)
class TreatyState:
    treaty_id: str
    terms: TreatyTerms
    start_day: int
    end_day: int
    status: str = "active"  # active | breached | expired | cancelled
    breach_score: float = 0.0
    last_checked_day: int = -1
    history: list[dict[str, object]] = field(default_factory=list)


def ensure_treaty_config(world: Any) -> TreatyConfig:
    cfg = getattr(world, "treaty_cfg", None)
    if not isinstance(cfg, TreatyConfig):
        cfg = TreatyConfig()
        world.treaty_cfg = cfg
    return cfg


def ensure_treaties(world: Any) -> MutableMapping[str, TreatyState]:
    treaties = getattr(world, "treaties", None)
    if not isinstance(treaties, MutableMapping):
        treaties = {}
        world.treaties = treaties
    if not hasattr(world, "treaty_penalties"):
        world.treaty_penalties = {}
    return treaties


def _stable_float(parts: Iterable[object], salt: str) -> float:
    blob = ":".join([str(part) for part in (*parts, salt)])
    digest = sha256(blob.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def _treaty_id(terms: TreatyTerms, day: int, seed: int, salt: str) -> str:
    return f"treaty:{sha256(f'{terms.party_a}:{terms.party_b}:{terms.treaty_type}:{day}:{seed}:{salt}'.encode('utf-8')).hexdigest()[:12]}"


def _bounded_history(state: TreatyState, cfg: TreatyConfig) -> None:
    max_len = max(1, int(cfg.history_max))
    if len(state.history) > max_len:
        state.history = state.history[-max_len:]


def _ward_pressure(world: Any, ward_id: str) -> float:
    ward = getattr(world, "wards", {}).get(ward_id)
    if ward is None:
        return 0.0
    need = float(getattr(ward, "need_index", 0.0) or 0.0)
    risk = float(getattr(ward, "risk_index", 0.0) or 0.0)
    legitimacy = float(getattr(ward, "legitimacy", 0.5) or 0.5)
    return max(0.0, need + risk - 0.3 * legitimacy)


def propose_treaties_for_day(world: Any, day: int) -> list[TreatyTerms]:
    cfg = ensure_treaty_config(world)
    if not cfg.enabled:
        return []
    treaties = ensure_treaties(world)
    if len(treaties) >= max(1, int(cfg.max_active_treaties)):
        return []

    wards: list[str] = sorted(getattr(world, "wards", {}).keys())
    seed = getattr(world, "seed", 0)
    terms: list[TreatyTerms] = []

    for idx, ward_id in enumerate(wards):
        pressures = []
        for counterparty in wards[idx + 1 :]:
            score = _ward_pressure(world, counterparty) + _ward_pressure(world, ward_id)
            pressures.append((score, counterparty))
        pressures.sort(key=lambda itm: (-itm[0], itm[1]))
        for score, counterparty in pressures[: max(1, int(cfg.counterparty_topk))]:
            if score <= 0.0:
                continue
            existing = [
                state
                for state in treaties.values()
                if {state.terms.party_a, state.terms.party_b} == {ward_id, counterparty}
                and state.status == "active"
            ]
            if existing:
                continue
            risk = max(_ward_pressure(world, ward_id), _ward_pressure(world, counterparty))
            need_gap = abs(
                float(getattr(getattr(world, "wards", {}).get(ward_id, None), "need_index", 0.0) or 0.0)
                - float(getattr(getattr(world, "wards", {}).get(counterparty, None), "need_index", 0.0) or 0.0)
            )
            if risk > 0.8:
                treaty_type = "ESCORT_PACT"
                obligations_a = [TreatyObligation(kind="escort", corridor_ids=_top_corridors(world, cfg, seed, ward_id))]
                obligations_b = [TreatyObligation(kind="escort", corridor_ids=_top_corridors(world, cfg, seed, counterparty))]
            elif need_gap > 0.2:
                treaty_type = "RESOURCE_SWAP"
                obligations_a = [
                    TreatyObligation(kind="deliver", material="water", amount=5, cadence_days=7),
                ]
                obligations_b = [
                    TreatyObligation(kind="deliver", material="food", amount=5, cadence_days=7),
                ]
            elif risk > 0.4:
                treaty_type = "SAFE_PASSAGE"
                obligations_a = [TreatyObligation(kind="allow_passage", corridor_ids=_top_corridors(world, cfg, seed, ward_id))]
                obligations_b = [TreatyObligation(kind="allow_passage", corridor_ids=_top_corridors(world, cfg, seed, counterparty))]
            else:
                treaty_type = "MAINTENANCE_COMPACT"
                obligations_a = [TreatyObligation(kind="maintain", corridor_ids=_top_corridors(world, cfg, seed, ward_id))]
                obligations_b = [TreatyObligation(kind="maintain", corridor_ids=_top_corridors(world, cfg, seed, counterparty))]

            term = TreatyTerms(
                treaty_type=treaty_type,
                party_a=ward_id,
                party_b=counterparty,
                obligations_a=obligations_a,
                obligations_b=obligations_b,
                consideration={
                    "payment_from_a_to_b": 1.0 if treaty_type != "RESOURCE_SWAP" else 0.0,
                    "payment_from_b_to_a": 0.0 if treaty_type != "RESOURCE_SWAP" else 1.0,
                },
                duration_days=cfg.default_duration_days,
            )
            terms.append(term)
            if len(terms) >= max(1, int(cfg.max_new_treaties_per_day)):
                return terms
    return terms


def _top_corridors(world: Any, cfg: TreatyConfig, seed: int, ward_id: str) -> list[str]:
    edges: Iterable[str]
    infra_edges = getattr(world, "infra_edges", None)
    if isinstance(infra_edges, Mapping):
        edges = list(sorted(infra_edges.keys()))
    else:
        survey_edges = getattr(getattr(world, "survey_map", None), "edges", {})
        edges = list(sorted(survey_edges.keys()))
    ranked = []
    for edge_key in edges:
        weight = _stable_float((seed, ward_id, edge_key, cfg.deterministic_salt), "corridor")
        ranked.append((weight, edge_key))
    ranked.sort(key=lambda itm: (-itm[0], itm[1]))
    return [edge for _, edge in ranked[: max(1, int(cfg.corridor_topk))]]


def should_accept_treaty(world: Any, terms: TreatyTerms) -> bool:
    cfg = ensure_treaty_config(world)
    base = _ward_pressure(world, terms.party_a) + _ward_pressure(world, terms.party_b)
    obligation_cost = sum(
        float(ob.amount or 0.0) for ob in [*terms.obligations_a, *terms.obligations_b] if ob.kind == "deliver"
    )
    cultural_bonus = 0.1 if getattr(world, "culture_by_ward", {}) else 0.0
    phase = getattr(world, "phase", "P0")
    phase_modifier = -0.05 if str(phase).upper() == "P2" else 0.0
    utility = base + cultural_bonus - 0.05 * obligation_cost + phase_modifier
    return utility >= 0.1 + phase_modifier


def activate_treaty(world: Any, terms: TreatyTerms, day: int) -> TreatyState:
    cfg = ensure_treaty_config(world)
    treaties = ensure_treaties(world)
    treaty_id = _treaty_id(terms, day, getattr(world, "seed", 0), cfg.deterministic_salt)
    state = TreatyState(
        treaty_id=treaty_id,
        terms=terms,
        start_day=day,
        end_day=day + max(1, int(getattr(terms, "duration_days", cfg.default_duration_days))),
    )
    treaties[treaty_id] = state
    metrics = ensure_metrics(world)
    metrics.inc("treaties.signed")
    metrics.set_gauge("treaties.active", len([t for t in treaties.values() if t.status == "active"]))
    ensure_event_ring(world)
    record_event(
        world,
        {
            "type": "TREATY_SIGNED",
            "treaty_id": treaty_id,
            "parties": [terms.party_a, terms.party_b],
            "day": day,
            "treaty_type": terms.treaty_type,
        },
    )
    return state


def _maybe_payment(world: Any, terms: TreatyTerms, day: int, party_from: str, party_to: str) -> bool:
    if party_from == terms.party_a and party_to == terms.party_b:
        key = "payment_from_a_to_b"
    elif party_from == terms.party_b and party_to == terms.party_a:
        key = "payment_from_b_to_a"
    else:
        key = f"payment:{party_from}->{party_to}"
    amount = float(terms.consideration.get(key, 0.0))
    if amount <= 0:
        return True
    acct_from = f"acct:{party_from}"
    acct_to = f"acct:{party_to}"
    return transfer(world, day=day, from_acct=acct_from, to_acct=acct_to, amount=amount, reason="treaty-payment")


def _execute_obligation(
    world: Any, state: TreatyState, obligation: TreatyObligation, party: str, counterparty: str, day: int
) -> bool:
    cfg = ensure_treaty_config(world)
    if obligation.cadence_days <= 0:
        return True
    if (day - state.start_day) % max(1, int(obligation.cadence_days)) != 0:
        return True
    success = True
    if obligation.kind == "deliver" and obligation.material:
        ledger: LogisticsLedger = ensure_logistics(world)
        delivery_id = f"{state.treaty_id}:{party}:{day}"
        due_tick = getattr(world, "config", None)
        ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", 144_000)
        if not isinstance(ticks_per_day, int):
            try:
                ticks_per_day = int(ticks_per_day)
            except Exception:
                ticks_per_day = 144_000
        created_tick = int(day * max(1, ticks_per_day))
        request = DeliveryRequest(
            delivery_id=delivery_id,
            project_id=state.treaty_id,
            origin_node_id=f"node:{party}",
            dest_node_id=f"node:{counterparty}",
            items={str(obligation.material): float(obligation.amount or 0.0)},
            status=DeliveryStatus.REQUESTED,
            created_tick=created_tick,
            due_tick=created_tick + ticks_per_day,
            notes={"kind": "treaty"},
            origin_owner_id=party,
            dest_owner_id=counterparty,
        )
        ledger.add(request)
    elif obligation.kind in {"escort", "allow_passage", "maintain"}:
        penalties = getattr(world, "treaty_penalties", {})
        penalties.setdefault(party, 1.0)
        world.treaty_penalties = penalties
    else:
        success = False
    history_entry = {
        "day": day,
        "party": party,
        "kind": obligation.kind,
        "status": "executed" if success else "failed",
    }
    state.history.append(history_entry)
    _bounded_history(state, cfg)
    return success


def run_treaties_for_day(world: Any, day: int) -> None:
    cfg = ensure_treaty_config(world)
    if not cfg.enabled:
        return
    treaties = ensure_treaties(world)
    metrics = ensure_metrics(world)

    for state in list(treaties.values()):
        if state.status != "active":
            continue
        if day >= state.end_day:
            state.status = "expired"
            record_event(world, {"type": "TREATY_EXPIRED", "treaty_id": state.treaty_id, "day": day})
            continue

        failures = 0
        terms = state.terms
        if not _maybe_payment(world, terms, day, terms.party_a, terms.party_b):
            failures += 1
        if not _maybe_payment(world, terms, day, terms.party_b, terms.party_a):
            failures += 1
        for obligation in terms.obligations_a:
            if not _execute_obligation(world, state, obligation, terms.party_a, terms.party_b, day):
                failures += 1
        for obligation in terms.obligations_b:
            if not _execute_obligation(world, state, obligation, terms.party_b, terms.party_a, day):
                failures += 1

        if failures > 0:
            state.breach_score += cfg.breach_increment * failures
        else:
            state.breach_score = max(0.0, state.breach_score - cfg.breach_decay)
        state.last_checked_day = day

        record_event(
            world,
            {
                "type": "TREATY_EXECUTED",
                "treaty_id": state.treaty_id,
                "day": day,
                "failures": failures,
                "breach_score": round(state.breach_score, 3),
            },
        )

        if state.breach_score > cfg.breach_threshold:
            state.status = "breached"
            world.treaty_penalties[state.terms.party_a] = 1.25
            world.treaty_penalties[state.terms.party_b] = 1.25
            metrics.inc("treaties.breached")
            record_event(
                world,
                {
                    "type": "TREATY_BREACHED",
                    "treaty_id": state.treaty_id,
                    "day": day,
                    "penalty": 1.25,
                },
            )

    active = [t for t in treaties.values() if t.status == "active"]
    metrics.set_gauge("treaties.active", len(active))
    breach_scores = [t.breach_score for t in treaties.values()]
    if breach_scores:
        metrics.set_gauge("treaties.avg_breach_score", sum(breach_scores) / len(breach_scores))


def treaties_seed_payload(world: Any) -> dict[str, Any] | None:
    cfg = getattr(world, "treaty_cfg", None)
    treaties: Mapping[str, TreatyState] = getattr(world, "treaties", {}) or {}
    if not isinstance(cfg, TreatyConfig) or not cfg.enabled or not treaties:
        return None
    entries: list[dict[str, object]] = []
    for treaty_id in sorted(treaties.keys()):
        state = treaties[treaty_id]
        entry = {
            "treaty_id": treaty_id,
            "status": state.status,
            "start_day": state.start_day,
            "end_day": state.end_day,
            "breach_score": round(state.breach_score, 6),
            "terms": {
                "treaty_type": state.terms.treaty_type,
                "party_a": state.terms.party_a,
                "party_b": state.terms.party_b,
                "duration_days": state.terms.duration_days,
                "obligations_a": [asdict(ob) for ob in state.terms.obligations_a],
                "obligations_b": [asdict(ob) for ob in state.terms.obligations_b],
                "consideration": dict(state.terms.consideration),
                "penalties": dict(state.terms.penalties),
            },
        }
        if state.history:
            entry["history"] = list(state.history[-max(1, int(cfg.history_max)):])
        entries.append(entry)
    return {"schema": "treaties_v1", "treaties": entries}


def save_treaties_seed(world: Any, path) -> None:
    payload = treaties_seed_payload(world)
    if payload is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)


def treaties_signature(world: Any) -> str:
    payload = treaties_seed_payload(world) or {}
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(data.encode("utf-8")).hexdigest()


__all__ = [
    "TreatyConfig",
    "TreatyObligation",
    "TreatyTerms",
    "TreatyState",
    "activate_treaty",
    "ensure_treaties",
    "ensure_treaty_config",
    "propose_treaties_for_day",
    "run_treaties_for_day",
    "should_accept_treaty",
    "treaties_seed_payload",
    "treaties_signature",
    "save_treaties_seed",
]

