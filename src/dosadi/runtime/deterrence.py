from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Iterable, Mapping, MutableMapping

from dosadi.runtime.ledger import get_or_create_account, transfer
from dosadi.runtime.telemetry import ensure_event_ring, ensure_metrics, record_event
from dosadi.runtime.treaties import (
    TreatyObligation,
    TreatyTerms,
    activate_treaty,
    ensure_treaties,
    ensure_treaty_config,
    should_accept_treaty,
)
from dosadi.world.survey_map import SurveyMap

if TYPE_CHECKING:  # pragma: no cover - typing only
    from dosadi.runtime.war import RaidOutcome, RaidPlan


@dataclass(slots=True)
class DeterrenceConfig:
    enabled: bool = False
    neighbor_topk: int = 12
    max_new_pacts_per_week: int = 2
    deterministic_salt: str = "deterrence-v1"
    credibility_decay_per_week: float = 0.03
    credibility_gain_per_week: float = 0.02
    bluff_penalty: float = 0.15


@dataclass(slots=True)
class RelationshipState:
    a: str
    b: str
    threat: float = 0.0
    trust: float = 0.5
    credibility_a: float = 0.5
    credibility_b: float = 0.5
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)

    def credibility_towards(self, viewer: str) -> float:
        if viewer == self.a:
            return self.credibility_b
        if viewer == self.b:
            return self.credibility_a
        return min(self.credibility_a, self.credibility_b)


def ensure_deterrence_config(world: Any) -> DeterrenceConfig:
    cfg = getattr(world, "deterrence_cfg", None)
    if not isinstance(cfg, DeterrenceConfig):
        cfg = DeterrenceConfig()
        world.deterrence_cfg = cfg
    return cfg


def ensure_relationships(world: Any) -> MutableMapping[str, RelationshipState]:
    relationships = getattr(world, "relationships", None)
    if not isinstance(relationships, MutableMapping):
        relationships = {}
        world.relationships = relationships
    return relationships


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_float(parts: Iterable[object], salt: str) -> float:
    payload = "|".join(str(part) for part in parts)
    digest = sha256(f"{salt}|{payload}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def relationship_key(a: str, b: str) -> str:
    return "|".join(sorted([a, b]))


def ensure_relationship(world: Any, a: str, b: str) -> RelationshipState:
    relationships = ensure_relationships(world)
    key = relationship_key(a, b)
    rel = relationships.get(key)
    if not isinstance(rel, RelationshipState):
        rel = RelationshipState(a=a, b=b)
        relationships[key] = rel
    return rel


def _wards_for_edge(world: Any, edge_key: str) -> list[str]:
    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    edge = getattr(survey_map, "edges", {}).get(edge_key)
    wards: list[str] = []
    for node_id in (getattr(edge, "a", None), getattr(edge, "b", None)):
        ward_id = getattr(getattr(survey_map, "nodes", {}).get(node_id, None), "ward_id", None)
        if ward_id and ward_id not in wards:
            wards.append(str(ward_id))
    return wards


def _neighbor_pairs(world: Any, cfg: DeterrenceConfig) -> list[tuple[str, str]]:
    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    seen: set[str] = set()
    pairs: list[tuple[str, str, float]] = []
    for edge_key, edge in sorted(getattr(survey_map, "edges", {}).items()):
        wards = _wards_for_edge(world, edge_key)
        if len(wards) < 2:
            continue
        pair_key = relationship_key(wards[0], wards[1])
        if pair_key in seen:
            continue
        seen.add(pair_key)
        weight = _stable_float((edge_key, wards[0], wards[1]), cfg.deterministic_salt)
        pairs.append((wards[0], wards[1], weight))
    pairs.sort(key=lambda itm: (-itm[2], itm[0], itm[1]))
    return [(a, b) for a, b, _ in pairs[: max(1, int(cfg.neighbor_topk))]]


def _update_relationship(rel: RelationshipState, day: int, cfg: DeterrenceConfig) -> None:
    if rel.last_update_day >= 0 and day - rel.last_update_day < 7:
        return
    rel.threat = _clamp01(rel.threat * (1.0 - cfg.credibility_decay_per_week))
    rel.trust = _clamp01(rel.trust + cfg.credibility_gain_per_week * (1.0 - rel.trust))
    rel.credibility_a = _clamp01(rel.credibility_a * (1.0 - cfg.credibility_decay_per_week))
    rel.credibility_b = _clamp01(rel.credibility_b * (1.0 - cfg.credibility_decay_per_week))
    rel.last_update_day = day


def _pact_terms(
    world: Any, cfg: DeterrenceConfig, a: str, b: str, *, threat: float, trust: float, day: int
) -> TreatyTerms:
    if threat >= 0.45:
        treaty_type = "MUTUAL_DEFENSE_PACT"
        obligations_a = [TreatyObligation(kind="escort")]
        obligations_b = [TreatyObligation(kind="escort")]
    else:
        treaty_type = "NONAGGRESSION_PACT"
        obligations_a = [TreatyObligation(kind="allow_passage")]
        obligations_b = [TreatyObligation(kind="allow_passage")]
    return TreatyTerms(
        treaty_type=treaty_type,
        party_a=a,
        party_b=b,
        obligations_a=obligations_a,
        obligations_b=obligations_b,
        duration_days=ensure_treaty_config(world).default_duration_days,
        penalties={"deterrence": cfg.bluff_penalty},
        consideration={"payment_from_a_to_b": 0.0, "payment_from_b_to_a": 0.0},
    )


def propose_deterrence_pacts(world: Any, *, day: int) -> list[TreatyTerms]:
    cfg = ensure_deterrence_config(world)
    if not cfg.enabled:
        return []
    ensure_treaty_config(world)
    existing = ensure_treaties(world)
    candidates: list[tuple[float, TreatyTerms]] = []
    for a, b in _neighbor_pairs(world, cfg):
        rel = ensure_relationship(world, a, b)
        weight = rel.threat - rel.trust + _stable_float((a, b, day), cfg.deterministic_salt)
        terms = _pact_terms(world, cfg, a, b, threat=rel.threat, trust=rel.trust, day=day)
        already = [
            state
            for state in existing.values()
            if getattr(state, "status", "active") == "active"
            and {state.terms.party_a, state.terms.party_b} == {a, b}
        ]
        if already:
            continue
        candidates.append((weight, terms))
    candidates.sort(key=lambda itm: (-round(itm[0], 6), itm[1].party_a, itm[1].party_b))
    return [terms for _, terms in candidates[: max(1, int(cfg.max_new_pacts_per_week))]]


def run_deterrence_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_deterrence_config(world)
    if not cfg.enabled:
        return
    relationships = ensure_relationships(world)
    if day % 7 == 0:
        for rel in relationships.values():
            _update_relationship(rel, day, cfg)
        for terms in propose_deterrence_pacts(world, day=day):
            if should_accept_treaty(world, terms):
                activate_treaty(world, terms, day)
    _emit_deterrence_metrics(world)


def _emit_deterrence_metrics(world: Any) -> None:
    metrics = ensure_metrics(world)
    bucket = metrics.get("deterrence", {}) if isinstance(metrics.get("deterrence", {}), dict) else {}
    relationships = ensure_relationships(world)
    if relationships:
        avg_trust = sum(rel.trust for rel in relationships.values()) / len(relationships)
        avg_threat = sum(rel.threat for rel in relationships.values()) / len(relationships)
        avg_cred = sum(rel.credibility_a + rel.credibility_b for rel in relationships.values()) / (
            2 * len(relationships)
        )
        bucket["avg_trust"] = round(avg_trust, 4)
        bucket["avg_threat"] = round(avg_threat, 4)
        bucket["avg_credibility"] = round(avg_cred, 4)
    treaties = getattr(world, "treaties", {}) or {}
    bucket["pacts_active"] = len(
        [t for t in treaties.values() if getattr(t, "status", "active") == "active" and "PACT" in t.terms.treaty_type]
    )
    metrics.gauges["deterrence"] = bucket


def _apply_bluff_penalty(rel: RelationshipState, cfg: DeterrenceConfig) -> None:
    rel.credibility_a = _clamp01(rel.credibility_a - cfg.bluff_penalty)
    rel.credibility_b = _clamp01(rel.credibility_b - cfg.bluff_penalty)
    rel.trust = _clamp01(rel.trust - 0.5 * cfg.bluff_penalty)


def _deliver_pact_aid(world: Any, ward: str, ally: str, *, day: int, cfg: DeterrenceConfig) -> bool:
    ledger_enabled = bool(getattr(getattr(world, "ledger_cfg", None), "enabled", False))
    if not ledger_enabled:
        return True
    acct_from = f"acct:ward:{ally}"
    acct_to = f"acct:ward:{ward}"
    get_or_create_account(world, acct_from)
    get_or_create_account(world, acct_to)
    return transfer(world, day=day, from_acct=acct_from, to_acct=acct_to, amount=3.0, reason="PACT_AID")


def apply_raid_outcome(world: Any, plan: RaidPlan, outcome: RaidOutcome, *, day: int) -> None:
    cfg = ensure_deterrence_config(world)
    if not cfg.enabled:
        return
    wards = _wards_for_edge(world, plan.target_id)
    relationships = ensure_relationships(world)
    for ward in wards:
        rel = ensure_relationship(world, plan.aggressor_faction, ward)
        if outcome.status == "succeeded":
            rel.threat = _clamp01(rel.threat + 0.2)
            rel.trust = _clamp01(rel.trust - 0.1)
        else:
            rel.trust = _clamp01(rel.trust + 0.05)
        rel.last_update_day = day
    treaties: Mapping[str, Any] = getattr(world, "treaties", {}) or {}
    for state in treaties.values():
        if getattr(state, "status", "active") != "active":
            continue
        if state.terms.treaty_type not in {"MUTUAL_DEFENSE_PACT", "NONAGGRESSION_PACT"}:
            continue
        parties = {state.terms.party_a, state.terms.party_b}
        handled = False
        for ward in wards:
            if ward not in parties:
                continue
            ally = (parties - {ward}).pop()
            rel = ensure_relationship(world, ally, ward)
            if state.terms.treaty_type == "MUTUAL_DEFENSE_PACT":
                delivered = _deliver_pact_aid(world, ward, ally, day=day, cfg=cfg)
                event_type = "PACT_AID_DELIVERED" if delivered else "PACT_AID_FAILED"
                if not delivered:
                    _apply_bluff_penalty(rel, cfg)
                record_event(
                    world,
                    {
                        "type": event_type,
                        "treaty_id": state.treaty_id,
                        "ward": ward,
                        "ally": ally,
                        "day": day,
                    },
                )
            elif state.terms.treaty_type == "NONAGGRESSION_PACT" and plan.aggressor_faction in parties:
                _apply_bluff_penalty(rel, cfg)
                record_event(
                    world,
                    {
                        "type": "PACT_BLUFF_PENALIZED",
                        "treaty_id": state.treaty_id,
                        "ward": ward,
                        "aggressor": plan.aggressor_faction,
                        "day": day,
                    },
                )
            handled = True
            if handled:
                break
    ensure_event_ring(world)


def deterrence_penalty(world: Any, plan: RaidPlan) -> tuple[float, dict[str, float]]:
    cfg = ensure_deterrence_config(world)
    if not cfg.enabled:
        return 0.0, {}
    wards = _wards_for_edge(world, plan.target_id)
    relationships = ensure_relationships(world)
    penalty = 0.0
    breakdown: dict[str, float] = {}
    treaties: Mapping[str, Any] = getattr(world, "treaties", {}) or {}
    for ward in wards:
        rel = ensure_relationship(world, plan.aggressor_faction, ward)
        trust_penalty = 0.2 * rel.trust
        cred_penalty = 0.3 * rel.credibility_towards(plan.aggressor_faction)
        threat_penalty = 0.1 * (1.0 - rel.threat)
        total = trust_penalty + cred_penalty + threat_penalty
        breakdown[ward] = round(total, 4)
        penalty += total
    for state in treaties.values():
        if getattr(state, "status", "active") != "active":
            continue
        parties = {state.terms.party_a, state.terms.party_b}
        if state.terms.treaty_type == "NONAGGRESSION_PACT" and plan.aggressor_faction in parties:
            penalty += 0.5
            breakdown["nonaggression"] = round(breakdown.get("nonaggression", 0.0) + 0.5, 4)
        if state.terms.treaty_type == "MUTUAL_DEFENSE_PACT" and parties.intersection(wards):
            penalty += 0.25
            breakdown["defense_pact"] = round(breakdown.get("defense_pact", 0.0) + 0.25, 4)
    if wards:
        penalty /= float(len(wards))
    penalty = min(0.9, penalty)
    return penalty, breakdown


def deterrence_seed_payload(world: Any) -> dict[str, Any] | None:
    cfg = getattr(world, "deterrence_cfg", None)
    relationships: Mapping[str, RelationshipState] = getattr(world, "relationships", {}) or {}
    if not isinstance(cfg, DeterrenceConfig) or not cfg.enabled or not relationships:
        return None
    entries = []
    for key in sorted(relationships.keys()):
        rel = relationships[key]
        entries.append(
            {
                "a": rel.a,
                "b": rel.b,
                "trust": round(rel.trust, 6),
                "threat": round(rel.threat, 6),
                "credibility_a": round(rel.credibility_a, 6),
                "credibility_b": round(rel.credibility_b, 6),
                "last_update_day": rel.last_update_day,
            }
        )
    return {"schema": "deterrence_v1", "relationships": entries}


__all__ = [
    "DeterrenceConfig",
    "RelationshipState",
    "apply_raid_outcome",
    "deterrence_penalty",
    "deterrence_seed_payload",
    "ensure_deterrence_config",
    "ensure_relationship",
    "ensure_relationships",
    "relationship_key",
    "run_deterrence_for_day",
]
