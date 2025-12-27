from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from dosadi.runtime.telemetry import ensure_metrics
from dosadi.world.factions import pseudo_rand01


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class ShadowStateConfig:
    enabled: bool = False
    update_cadence_days: int = 14
    deterministic_salt: str = "shadowstate-v1"
    max_edges_per_ward: int = 12
    max_shadow_accounts: int = 64
    capture_growth_p2: float = 0.03
    reform_pressure_scale: float = 0.25
    exposure_rate_base: float = 0.002
    laundering_efficiency: float = 0.6


@dataclass(slots=True)
class InfluenceEdge:
    ward_id: str
    from_faction: str
    to_domain: str
    strength: float
    mode: str
    exposure: float = 0.0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ShadowAccount:
    account_id: str
    faction_id: str
    ward_id: str
    balance: float = 0.0
    sources: dict[str, float] = field(default_factory=dict)
    uses: dict[str, float] = field(default_factory=dict)
    last_update_day: int = -1


@dataclass(slots=True)
class CorruptionIndex:
    ward_id: str
    petty: float = 0.0
    capture: float = 0.0
    shadow_state: float = 0.0
    exposure_risk: float = 0.0
    last_update_day: int = -1


def ensure_shadow_config(world: Any) -> ShadowStateConfig:
    cfg = getattr(world, "shadow_cfg", None)
    if not isinstance(cfg, ShadowStateConfig):
        cfg = ShadowStateConfig()
        world.shadow_cfg = cfg
    return cfg


def ensure_shadow_ledgers(world: Any) -> tuple[dict[str, list[InfluenceEdge]], dict[str, ShadowAccount], dict[str, CorruptionIndex], list[dict[str, object]]]:
    edges = getattr(world, "influence_edges_by_ward", None)
    if not isinstance(edges, dict):
        edges = {}
        world.influence_edges_by_ward = edges
    accounts = getattr(world, "shadow_accounts", None)
    if not isinstance(accounts, dict):
        accounts = {}
        world.shadow_accounts = accounts
    corruption = getattr(world, "corruption_by_ward", None)
    if not isinstance(corruption, dict):
        corruption = {}
        world.corruption_by_ward = corruption
    events = getattr(world, "shadow_events", None)
    if not isinstance(events, list):
        events = []
        world.shadow_events = events
    return edges, accounts, corruption, events


def _stable_topk_edges(edges: Iterable[InfluenceEdge], k: int) -> list[InfluenceEdge]:
    sorted_edges = sorted(edges, key=lambda e: (-float(e.strength), e.from_faction, e.to_domain))
    return sorted_edges[: max(0, int(k))]


def _inflow_from_smuggling(world: Any, ward_id: str, faction_id: str, *, cfg: ShadowStateConfig, day: int) -> float:
    ward_state = getattr(world, "wards", {}).get(ward_id)
    smuggle_risk = float(getattr(ward_state, "smuggle_risk", 0.0) or getattr(ward_state, "need_index", 0.0) or 0.0)
    shadow_weight = 0.1 + 0.4 * _clamp01(smuggle_risk)
    seed = "|".join([cfg.deterministic_salt, "inflow", ward_id, faction_id, str(day)])
    jitter = 0.5 + 0.5 * pseudo_rand01(seed)
    return shadow_weight * jitter


def _inflow_from_cartel(world: Any, ward_id: str, faction_id: str, *, cfg: ShadowStateConfig, day: int) -> float:
    has_cartel = False
    for cartel in getattr(world, "cartels", {}).values():
        members = getattr(cartel, "members", set()) or set()
        if faction_id in members:
            has_cartel = True
            break
    if not has_cartel:
        return 0.0
    seed = "|".join([cfg.deterministic_salt, "cartel", ward_id, faction_id, str(day)])
    return 0.5 * (0.5 + pseudo_rand01(seed))


def _ensure_account(accounts: dict[str, ShadowAccount], *, faction_id: str, ward_id: str) -> ShadowAccount:
    account_id = f"shadow:{faction_id}:{ward_id}"
    account = accounts.get(account_id)
    if account is None:
        account = ShadowAccount(account_id=account_id, faction_id=faction_id, ward_id=ward_id)
        accounts[account_id] = account
    return account


def _bound_accounts(accounts: dict[str, ShadowAccount], *, cfg: ShadowStateConfig) -> None:
    if len(accounts) <= cfg.max_shadow_accounts:
        return
    ranked = sorted(accounts.values(), key=lambda acc: (-float(acc.balance), acc.account_id))
    keep_ids = {acc.account_id for acc in ranked[: cfg.max_shadow_accounts]}
    for acc_id in list(accounts.keys()):
        if acc_id not in keep_ids:
            del accounts[acc_id]


def _allocate_spend(account: ShadowAccount) -> float:
    spend = max(0.0, float(account.balance) * 0.2)
    if spend <= 0:
        return 0.0
    account.balance -= spend
    account.uses["BRIBES"] = account.uses.get("BRIBES", 0.0) + spend
    return spend


def _strengthen_edge(
    edges_by_ward: dict[str, list[InfluenceEdge]],
    *,
    ward_id: str,
    faction_id: str,
    domain: str,
    spend: float,
    mode: str,
    day: int,
    cfg: ShadowStateConfig,
) -> None:
    edge_list = edges_by_ward.setdefault(ward_id, [])
    target: InfluenceEdge | None = None
    for edge in edge_list:
        if edge.from_faction == faction_id and edge.to_domain == domain:
            target = edge
            break
    delta = _clamp01(spend * 0.02)
    if target is None:
        target = InfluenceEdge(
            ward_id=ward_id,
            from_faction=faction_id,
            to_domain=domain,
            strength=min(1.0, 0.1 + delta),
            mode=mode,
        )
        edge_list.append(target)
    else:
        target.strength = _clamp01(target.strength + delta)
    target.exposure = _clamp01(target.exposure + delta * 0.5)
    target.last_update_day = day
    target.notes["spend"] = target.notes.get("spend", 0.0) + spend

    edge_list[:] = _stable_topk_edges(edge_list, cfg.max_edges_per_ward)


def _domain_preferences() -> dict[str, float]:
    return {
        "CUSTOMS": 1.0,
        "POLICING": 0.9,
        "COURTS": 0.8,
        "DEPOTS": 0.7,
        "MARKETS": 0.6,
        "MEDIA": 0.5,
        "COUNCIL": 0.4,
    }


def _choose_domain(cfg: ShadowStateConfig, *, ward_id: str, faction_id: str, day: int) -> str:
    prefs = _domain_preferences()
    ranked = sorted(prefs.items(), key=lambda itm: (-itm[1], itm[0]))
    bias = pseudo_rand01("|".join([cfg.deterministic_salt, "domain", ward_id, faction_id, str(day)]))
    idx = int(bias * min(len(ranked), 3))
    return ranked[idx][0]


def _update_corruption_index(
    corruption_entry: CorruptionIndex,
    *,
    edges: list[InfluenceEdge],
    total_balance: float,
    cfg: ShadowStateConfig,
    day: int,
) -> None:
    strength = sum(edge.strength for edge in edges) / max(1, len(edges))
    exposure = sum(edge.exposure for edge in edges) / max(1, len(edges))
    corruption_entry.petty = _clamp01(0.05 + 0.05 * len(edges) + exposure * 0.3)
    corruption_entry.capture = _clamp01(strength * 0.8 + corruption_entry.petty * 0.2)
    corruption_entry.shadow_state = _clamp01(corruption_entry.capture * 0.5 + total_balance * 0.02)
    corruption_entry.exposure_risk = _clamp01(exposure * 0.6 + corruption_entry.shadow_state * 0.4)
    corruption_entry.last_update_day = day


def _maybe_record_scandal(
    world: Any,
    *,
    corruption: CorruptionIndex,
    edges: list[InfluenceEdge],
    events: list[dict[str, object]],
    cfg: ShadowStateConfig,
    day: int,
) -> None:
    threshold = max(cfg.exposure_rate_base, 0.2)
    if corruption.exposure_risk < threshold:
        return
    scandal_key = "|".join([cfg.deterministic_salt, "scandal", corruption.ward_id, str(day)])
    trigger = pseudo_rand01(scandal_key)
    if trigger < corruption.exposure_risk:
        corruption.capture = _clamp01(corruption.capture * (1.0 - cfg.reform_pressure_scale))
        corruption.shadow_state = _clamp01(corruption.shadow_state * (1.0 - cfg.reform_pressure_scale))
        corruption.petty = _clamp01(corruption.petty * (1.0 - cfg.reform_pressure_scale * 0.5))
        corruption.exposure_risk = _clamp01(corruption.exposure_risk * 0.5)
        events.append(
            {
                "type": "SCANDAL_EXPOSED",
                "ward_id": corruption.ward_id,
                "day": day,
                "capture_before": strength_signature(edges),
            }
        )
        if len(events) > 250:
            del events[: len(events) - 250]


def strength_signature(edges: Iterable[InfluenceEdge]) -> float:
    edge_list = list(edges)
    return sum(edge.strength for edge in edge_list) / max(1, len(edge_list))


def run_shadow_state_update(world: Any, day: int) -> None:
    cfg = ensure_shadow_config(world)
    if not cfg.enabled:
        return
    edges_by_ward, accounts, corruption_by_ward, events = ensure_shadow_ledgers(world)

    factions = sorted(getattr(world, "factions", {}).keys())
    wards = sorted(getattr(world, "wards", {}).keys())

    for ward_id in wards:
        corruption = corruption_by_ward.setdefault(ward_id, CorruptionIndex(ward_id=ward_id))
        total_balance = 0.0
        for faction_id in factions:
            account = _ensure_account(accounts, faction_id=faction_id, ward_id=ward_id)
            inflow = _inflow_from_smuggling(world, ward_id, faction_id, cfg=cfg, day=day)
            inflow += _inflow_from_cartel(world, ward_id, faction_id, cfg=cfg, day=day)
            if inflow > 0:
                account.balance += inflow
                account.sources["SMUGGLING_TITHE"] = account.sources.get("SMUGGLING_TITHE", 0.0) + inflow
            spend = _allocate_spend(account)
            if spend > 0:
                domain = _choose_domain(cfg, ward_id=ward_id, faction_id=faction_id, day=day)
                _strengthen_edge(
                    edges_by_ward,
                    ward_id=ward_id,
                    faction_id=faction_id,
                    domain=domain,
                    spend=spend,
                    mode="BRIBE",
                    day=day,
                    cfg=cfg,
                )
            account.last_update_day = day
            total_balance += account.balance
        ward_edges = edges_by_ward.get(ward_id, [])
        _update_corruption_index(corruption, edges=ward_edges, total_balance=total_balance, cfg=cfg, day=day)
        _maybe_record_scandal(world, corruption=corruption, edges=ward_edges, events=events, cfg=cfg, day=day)

    _bound_accounts(accounts, cfg=cfg)

    metrics = ensure_metrics(world)
    bucket = metrics.gauges.setdefault("shadow", {})
    if isinstance(bucket, dict):
        values = list(corruption_by_ward.values())
        petty_avg = sum(c.petty for c in values) / max(1, len(values))
        capture_avg = sum(c.capture for c in values) / max(1, len(values))
        shadow_avg = sum(c.shadow_state for c in values) / max(1, len(values))
        bucket["petty_avg"] = petty_avg
        bucket["capture_avg"] = capture_avg
        bucket["shadow_state_avg"] = shadow_avg
        bucket["shadow_balance_total"] = sum(acc.balance for acc in accounts.values())
        bucket["scandals"] = len(events)


def apply_capture_modifier(
    world: Any,
    ward_id: str | None,
    domain: str,
    base_value: float,
    actor_faction_id: str | None = None,
) -> tuple[float, list[str]]:
    cfg = getattr(world, "shadow_cfg", None)
    if not getattr(cfg, "enabled", False) or not ward_id:
        return float(base_value), []
    _, _, corruption_by_ward, _ = ensure_shadow_ledgers(world)
    corruption = corruption_by_ward.get(ward_id)
    edges = getattr(world, "influence_edges_by_ward", {}).get(ward_id, [])
    domain_edges = [edge for edge in edges if edge.to_domain == domain]
    edge_strength = sum(edge.strength for edge in domain_edges) / max(1, len(domain_edges))
    capture_level = getattr(corruption, "capture", 0.0)
    shadow_level = getattr(corruption, "shadow_state", 0.0)
    bias = _clamp01(0.4 * capture_level + 0.4 * edge_strength + 0.2 * shadow_level)
    adjusted = float(base_value) * (1.0 - 0.5 * bias)
    audit_flags: list[str] = []
    if bias > 0:
        audit_flags.append(f"capture:{domain.lower()}")
    if actor_faction_id and any(edge.from_faction == actor_faction_id for edge in domain_edges):
        adjusted = float(base_value) * (1.0 - 0.7 * bias)
        audit_flags.append("favored_faction")
    return max(0.0, adjusted), audit_flags


__all__ = [
    "ShadowStateConfig",
    "InfluenceEdge",
    "ShadowAccount",
    "CorruptionIndex",
    "run_shadow_state_update",
    "apply_capture_modifier",
    "ensure_shadow_config",
    "ensure_shadow_ledgers",
]
