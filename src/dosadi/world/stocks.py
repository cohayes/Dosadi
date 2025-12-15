"""Minimal stockpile helper functions for facility updates."""

from __future__ import annotations

from typing import MutableMapping


def _stock_ledger(world) -> MutableMapping[str, float]:
    ledger = getattr(world, "stockpiles", None)
    if ledger is None:
        ledger = {}
        setattr(world, "stockpiles", ledger)
    return ledger


def has(world, item: str, qty: float) -> bool:
    stock = _stock_ledger(world)
    return stock.get(item, 0.0) >= qty


def add(world, item: str, qty: float) -> None:
    if qty == 0:
        return
    stock = _stock_ledger(world)
    stock[item] = stock.get(item, 0.0) + qty


def consume(world, item: str, qty: float) -> bool:
    stock = _stock_ledger(world)
    if stock.get(item, 0.0) < qty:
        return False
    stock[item] -= qty
    return True


def snapshot_totals(world) -> dict[str, float]:
    stock = _stock_ledger(world)
    return dict(sorted(stock.items()))

