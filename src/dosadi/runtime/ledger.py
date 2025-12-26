"""Empire balance sheet v1 implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping

from dosadi.runtime.institutions import ensure_inst_config, ensure_policy, ensure_state
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.world.logistics import LogisticsLedger
from dosadi.world.survey_map import SurveyMap


@dataclass(slots=True)
class LedgerConfig:
    enabled: bool = False
    max_tx_per_day: int = 2000
    max_tx_retained: int = 20000
    deterministic_salt: str = "ledger-v1"


@dataclass(slots=True)
class LedgerAccount:
    acct_id: str
    balance: float = 0.0
    tags: set[str] = field(default_factory=set)
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class LedgerTx:
    day: int
    tx_id: str
    from_acct: str
    to_acct: str
    amount: float
    reason: str
    meta: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class LedgerState:
    accounts: dict[str, LedgerAccount] = field(default_factory=dict)
    txs: list[LedgerTx] = field(default_factory=list)
    last_run_day: int = -1
    tx_counter_day: int = -1
    tx_counter: int = 0
    paid_enforcement: dict[str, float] = field(default_factory=dict)
    paid_audit: dict[str, float] = field(default_factory=dict)

    def signature(self) -> str:
        canonical = {
            "accounts": {
                acct_id: {
                    "balance": round(acct.balance, 6),
                    "tags": sorted(acct.tags),
                    "notes": {k: acct.notes[k] for k in sorted(acct.notes)},
                }
                for acct_id, acct in sorted(self.accounts.items())
            },
            "txs": [
                {
                    "day": tx.day,
                    "tx_id": tx.tx_id,
                    "from": tx.from_acct,
                    "to": tx.to_acct,
                    "amount": round(tx.amount, 6),
                    "reason": tx.reason,
                    "meta": {k: tx.meta[k] for k in sorted(tx.meta)},
                }
                for tx in self.txs
            ],
            "tx_counter_day": self.tx_counter_day,
            "tx_counter": self.tx_counter,
        }
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()


STATE_TREASURY = "acct:state:treasury"
BLACK_MARKET = "acct:blackmarket"


def ensure_ledger_config(world: Any) -> LedgerConfig:
    cfg = getattr(world, "ledger_cfg", None)
    if not isinstance(cfg, LedgerConfig):
        cfg = LedgerConfig()
        world.ledger_cfg = cfg
    return cfg


def ensure_ledger_state(world: Any) -> LedgerState:
    state = getattr(world, "ledger_state", None)
    if not isinstance(state, LedgerState):
        state = LedgerState()
        world.ledger_state = state
    return state


def get_or_create_account(world: Any, acct_id: str, *, tags: set[str] | None = None) -> LedgerAccount:
    state = ensure_ledger_state(world)
    account = state.accounts.get(acct_id)
    if not isinstance(account, LedgerAccount):
        account = LedgerAccount(acct_id=acct_id, tags=set(tags or set()))
        state.accounts[acct_id] = account
    elif tags:
        account.tags.update(tags)
    return account


def _reset_tx_counter(state: LedgerState, day: int) -> None:
    if state.tx_counter_day != day:
        state.tx_counter_day = day
        state.tx_counter = 0


def post_tx(
    world: Any,
    *,
    day: int,
    from_acct: str,
    to_acct: str,
    amount: float,
    reason: str,
    meta: Mapping[str, object] | None = None,
) -> bool:
    cfg = ensure_ledger_config(world)
    if not cfg.enabled:
        return True
    if amount <= 0:
        return False
    state = ensure_ledger_state(world)
    _reset_tx_counter(state, day)
    if state.tx_counter >= max(1, int(cfg.max_tx_per_day)):
        return False

    payer = get_or_create_account(world, from_acct)
    payee = get_or_create_account(world, to_acct)
    available = max(0.0, float(payer.balance))
    effective_amount = min(float(amount), available)
    if effective_amount <= 0.0:
        return False

    payer.balance = max(0.0, payer.balance - effective_amount)
    payee.balance = payee.balance + effective_amount

    tx_id = f"{day}:{state.tx_counter:06d}"
    state.tx_counter += 1
    tx = LedgerTx(
        day=day,
        tx_id=tx_id,
        from_acct=from_acct,
        to_acct=to_acct,
        amount=effective_amount,
        reason=reason,
        meta=dict(meta or {}),
    )
    state.txs.append(tx)
    max_txs = max(1, int(cfg.max_tx_retained))
    if len(state.txs) > max_txs:
        overflow = len(state.txs) - max_txs
        if overflow > 0:
            state.txs = state.txs[overflow:]
    return True


def transfer(
    world: Any,
    day: int,
    from_acct: str,
    to_acct: str,
    amount: float,
    reason: str,
    meta: Mapping[str, object] | None = None,
) -> bool:
    return post_tx(
        world,
        day=day,
        from_acct=from_acct,
        to_acct=to_acct,
        amount=amount,
        reason=reason,
        meta=meta,
    )


def _ticks_per_day(world: Any) -> int:
    ticks = getattr(getattr(world, "config", None), "ticks_per_day", None)
    try:
        return max(1, int(ticks))
    except Exception:
        return 144_000


def _ward_for_location(world: Any, location_id: str | None) -> str | None:
    if not location_id:
        return None
    survey_map: SurveyMap | None = getattr(world, "survey_map", None)
    if survey_map is None:
        return None
    node = getattr(survey_map, "nodes", {}).get(location_id)
    return getattr(node, "ward_id", None)


def _throughput_proxy(world: Any, ward_id: str, *, day: int) -> float:
    ledger: LogisticsLedger | None = getattr(world, "logistics", None)
    if ledger is None:
        return 0.0
    ticks_per_day = _ticks_per_day(world)
    throughput = 0.0
    for delivery_id in sorted(getattr(ledger, "deliveries", {})):
        delivery = ledger.deliveries.get(delivery_id)
        if delivery is None or getattr(delivery, "deliver_tick", None) is None:
            continue
        deliver_day = int(delivery.deliver_tick) // ticks_per_day
        if deliver_day != day:
            continue
        dest_owner = getattr(delivery, "dest_owner_id", None)
        dest_ward = dest_owner or _ward_for_location(world, getattr(delivery, "dest_node_id", None))
        if dest_ward != ward_id:
            continue
        throughput += sum(float(qty) for qty in getattr(delivery, "items", {}).values())
    return throughput


def _apply_throughput_levies(world: Any, *, day: int, state: LedgerState) -> dict[str, float]:
    levies: dict[str, float] = {}
    wards = getattr(world, "wards", {}) or {}
    for ward_id in sorted(wards):
        policy = ensure_policy(world, ward_id)
        throughput = _throughput_proxy(world, ward_id, day=day)
        levy = max(0.0, float(policy.levy_rate)) * throughput
        if levy <= 0.0:
            continue
        prev_len = len(state.txs)
        posted = post_tx(
            world,
            day=day,
            from_acct=f"acct:ward:{ward_id}",
            to_acct=STATE_TREASURY,
            amount=levy,
            reason="LEVY_THROUGHPUT",
            meta={"throughput": throughput},
        )
        if posted and len(state.txs) > prev_len:
            levies[ward_id] = state.txs[-1].amount
    return levies


def _apply_corruption_leaks(world: Any, *, day: int, levies: Mapping[str, float], state: LedgerState) -> None:
    wards = getattr(world, "wards", {}) or {}
    for ward_id in sorted(wards):
        inst_state = ensure_state(world, ward_id)
        corruption = max(0.0, float(getattr(inst_state, "corruption", 0.0)))
        leak_rate = 0.05 * corruption
        base = levies.get(ward_id, 0.0)
        leak = leak_rate * base
        if leak <= 0:
            continue
        get_or_create_account(world, BLACK_MARKET, tags={"sink"})
        prev_len = len(state.txs)
        posted = post_tx(
            world,
            day=day,
            from_acct=f"acct:ward:{ward_id}",
            to_acct=BLACK_MARKET,
            amount=leak,
            reason="CORRUPTION_LEAK",
            meta={"corruption": corruption},
        )
        if posted and len(state.txs) > prev_len:
            state.paid_enforcement.setdefault(ward_id, 0.0)


def _apply_planned_spend(world: Any, *, day: int, state: LedgerState) -> None:
    state.paid_enforcement = {}
    state.paid_audit = {}
    wards = getattr(world, "wards", {}) or {}
    for ward_id in sorted(wards):
        policy = ensure_policy(world, ward_id)
        if getattr(policy, "enforcement_budget_points", 0.0) > 0:
            prev_len = len(state.txs)
            posted = post_tx(
                world,
                day=day,
                from_acct=f"acct:ward:{ward_id}",
                to_acct=STATE_TREASURY,
                amount=policy.enforcement_budget_points,
                reason="PAY_ENFORCEMENT",
            )
            if posted and len(state.txs) > prev_len:
                state.paid_enforcement[ward_id] = state.txs[-1].amount
        if getattr(policy, "audit_budget_points", 0.0) > 0:
            prev_len = len(state.txs)
            posted = post_tx(
                world,
                day=day,
                from_acct=f"acct:ward:{ward_id}",
                to_acct=STATE_TREASURY,
                amount=policy.audit_budget_points,
                reason="PAY_AUDIT",
            )
            if posted and len(state.txs) > prev_len:
                state.paid_audit[ward_id] = state.txs[-1].amount


def _emit_metrics(world: Any, state: LedgerState) -> None:
    metrics = ensure_metrics(world)
    ledger_metrics = metrics.gauges.setdefault("ledger", {})
    ward_balances = [acct.balance for acct_id, acct in state.accounts.items() if acct_id.startswith("acct:ward:")]
    faction_balances = [
        acct.balance for acct_id, acct in state.accounts.items() if acct_id.startswith("acct:fac:")
    ]
    treasury_balance = state.accounts.get(STATE_TREASURY, LedgerAccount(acct_id=STATE_TREASURY)).balance
    if isinstance(ledger_metrics, dict):
        ledger_metrics["balances"] = {
            "state_treasury": treasury_balance,
            "avg_ward": sum(ward_balances) / len(ward_balances) if ward_balances else 0.0,
            "avg_faction": sum(faction_balances) / len(faction_balances) if faction_balances else 0.0,
        }
        ledger_metrics["tx_count"] = len(state.txs)
    for acct_id, acct in sorted(state.accounts.items()):
        metrics.topk_add("ledger.richest_accounts", acct_id, acct.balance)
        metrics.topk_add("ledger.lowest_accounts", acct_id, -acct.balance)


def ensure_accounts(world: Any) -> None:
    get_or_create_account(world, STATE_TREASURY, tags={"state"})
    wards = getattr(world, "wards", {}) or {}
    for ward_id in sorted(wards):
        get_or_create_account(world, f"acct:ward:{ward_id}", tags={"ward"})
    factions = getattr(world, "factions", {}) or {}
    for faction_id in sorted(factions):
        get_or_create_account(world, f"acct:fac:{faction_id}", tags={"faction"})


def run_ledger_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_ledger_config(world)
    if not cfg.enabled:
        return
    ensure_inst_config(world)
    state = ensure_ledger_state(world)
    ensure_accounts(world)
    state.last_run_day = day
    levies = _apply_throughput_levies(world, day=day, state=state)
    _apply_corruption_leaks(world, day=day, levies=levies, state=state)
    _apply_planned_spend(world, day=day, state=state)
    _emit_metrics(world, state)


def ledger_seed_payload(world: Any) -> dict[str, Any] | None:
    cfg = getattr(world, "ledger_cfg", None)
    if not isinstance(cfg, LedgerConfig) or not cfg.enabled:
        return None
    state = getattr(world, "ledger_state", None)
    if not isinstance(state, LedgerState):
        return None
    accounts = []
    for acct_id, acct in sorted(state.accounts.items()):
        accounts.append(
            {
                "acct_id": acct_id,
                "balance": float(acct.balance),
                "tags": sorted(getattr(acct, "tags", set())),
            }
        )
    return {"schema": "ledger_accounts_v1", "accounts": accounts, "tx_counter": state.tx_counter}


def save_ledger_seed(world: Any, path) -> None:
    payload = ledger_seed_payload(world)
    if payload is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)


__all__ = [
    "LedgerAccount",
    "LedgerConfig",
    "LedgerState",
    "LedgerTx",
    "ensure_accounts",
    "ensure_ledger_config",
    "ensure_ledger_state",
    "get_or_create_account",
    "ledger_seed_payload",
    "post_tx",
    "run_ledger_for_day",
    "save_ledger_seed",
    "transfer",
]
