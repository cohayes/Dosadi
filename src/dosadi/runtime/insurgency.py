from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.comms import CommsModifiers
from dosadi.runtime.policing import DOCTRINE_PROFILES, WardPolicingState, ensure_policing_state
from dosadi.runtime.telemetry import ensure_metrics, record_event


@dataclass(slots=True)
class InsurgencyConfig:
    enabled: bool = False
    update_cadence_days: int = 7
    deterministic_salt: str = "insurgency-v1"
    max_cells_per_ward: int = 3
    max_ops_active: int = 24
    base_emergence_rate: float = 0.002
    base_op_rate: float = 0.08
    suppression_effect: float = 0.6
    backlash_effect: float = 0.35
    cell_decay_rate: float = 0.05


@dataclass(slots=True)
class CellState:
    cell_id: str
    ward_id: str
    archetype: str
    support: float = 0.0
    capability: float = 0.0
    secrecy: float = 0.5
    heat: float = 0.0
    morale: float = 0.5
    status: str = "DORMANT"
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class CellOpPlan:
    op_id: str
    cell_id: str
    ward_id: str
    op_type: str
    day_started: int
    day_end: int
    target_kind: str
    target_id: str
    intensity: float
    reason: str
    score_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class CellOpOutcome:
    op_id: str
    day: int
    status: str
    effects: dict[str, object] = field(default_factory=dict)
    notes: dict[str, object] = field(default_factory=dict)


ARCHETYPE_OPS: Mapping[str, tuple[str, ...]] = {
    "REVOLUTIONARY": (
        "PROPAGANDA_BROADCAST",
        "ASSASSINATION_ATTEMPT",
        "SABOTAGE_RELAY",
    ),
    "SEPARATIST": (
        "ATTACK_CONVOY",
        "SABOTAGE_DEPOT",
        "BOMB_CUSTOMS",
    ),
    "CRIMINAL_INSURGENT": (
        "SABOTAGE_DEPOT",
        "ATTACK_CONVOY",
        "BOMB_CUSTOMS",
    ),
    "MARTYR_CULT": (
        "PROPAGANDA_BROADCAST",
        "ASSASSINATION_ATTEMPT",
        "SABOTAGE_RELAY",
    ),
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_float(cfg: InsurgencyConfig, *parts: object, spread: float = 1.0) -> float:
    payload = json.dumps([cfg.deterministic_salt, *parts], sort_keys=True)
    digest = sha256(payload.encode("utf-8")).hexdigest()
    return (int(digest[:12], 16) / float(16**12)) * spread


def ensure_insurgency_config(world: Any) -> InsurgencyConfig:
    cfg = getattr(world, "insurgency_cfg", None)
    if not isinstance(cfg, InsurgencyConfig):
        cfg = InsurgencyConfig()
        world.insurgency_cfg = cfg
    return cfg


def ensure_cells(world: Any) -> dict[str, list[CellState]]:
    cells = getattr(world, "cells_by_ward", None) or {}
    if not isinstance(cells, dict):
        cells = {}
    world.cells_by_ward = cells
    return cells


def ensure_active_ops(world: Any) -> dict[str, CellOpPlan]:
    active = getattr(world, "cell_ops_active", None) or {}
    if not isinstance(active, dict):
        active = {}
    world.cell_ops_active = active
    return active


def ensure_op_history(world: Any) -> list[CellOpOutcome]:
    history = getattr(world, "cell_ops_history", None)
    if not isinstance(history, list):
        history = []
    world.cell_ops_history = history
    return history


def _phase_key(world: Any) -> str:
    phase_state = getattr(world, "phase_state", None)
    value = getattr(phase_state, "phase", "P1")
    try:
        intval = int(getattr(value, "value", value))
        return f"P{intval}"
    except Exception:
        return "P1"


def _backlash_score(world: Any, ward_id: str) -> float:
    policing_state: WardPolicingState = ensure_policing_state(world, ward_id)
    doctrine = policing_state.doctrine_mix or {"COMMUNITY": 0.25, "PROCEDURAL": 0.25, "MILITARIZED": 0.25, "TERROR": 0.25}
    terror_weight = float(doctrine.get("TERROR", 0.0) or 0.0)
    harm = 0.0
    for key, mix in doctrine.items():
        effect = DOCTRINE_PROFILES.get(key, {})
        harm += float(effect.get("backlash", 0.0)) * float(mix)
    comms_mods = getattr(world, "comms_mod_by_ward", {}) or {}
    loss = getattr(comms_mods.get(ward_id), "loss_mult", 1.0) or 1.0
    outage = max(0.0, float(loss) - 1.0)
    return _clamp01(terror_weight * 0.6 + harm + outage * 0.2)


def _hardship_score(world: Any, ward_id: str) -> float:
    ward = getattr(world, "wards", {}).get(ward_id)
    need = float(getattr(ward, "need_index", getattr(world, "need_index", 0.0)) or 0.0)
    inequality = float(getattr(world, "inequality_index", 0.0) or 0.0)
    return _clamp01(need * 0.8 + inequality * 0.3)


def _ideology_score(world: Any, ward_id: str) -> float:
    culture = getattr(world, "culture_by_ward", {}).get(ward_id)
    alignment = getattr(culture, "alignment", {}) if culture is not None else {}
    polarization = float(alignment.get("polarization", 0.0) or 0.0)
    return _clamp01(polarization)


def _smuggling_score(world: Any, ward_id: str) -> float:
    smuggling = getattr(world, "smuggling_by_faction", {}) or {}
    value = 0.0
    for network in smuggling.values():
        node_val = getattr(network, "routes", {}).get(ward_id) if hasattr(network, "routes") else None
        try:
            value = max(value, float(node_val or 0.0))
        except Exception:
            continue
    return _clamp01(value)


def _archetype_for_drivers(
    cfg: InsurgencyConfig, world: Any, ward_id: str, hardship: float, backlash: float, ideology: float
) -> str:
    scores = {
        "REVOLUTIONARY": hardship + ideology,
        "SEPARATIST": hardship * 0.6 + backlash * 0.4,
        "CRIMINAL_INSURGENT": hardship * 0.4 + _smuggling_score(world, ward_id),
        "MARTYR_CULT": ideology + backlash * 0.6,
    }
    noise = _stable_float(cfg, ward_id, "archetype") * 0.1
    best = sorted(((score + noise, key) for key, score in scores.items()), reverse=True)
    return best[0][1]


def _spawn_cell(world: Any, ward_id: str, cfg: InsurgencyConfig, hardship: float, backlash: float, ideology: float) -> CellState:
    cells = ensure_cells(world).setdefault(ward_id, [])
    seq = len(cells)
    cell_id = f"cell:{ward_id}:{seq}"
    archetype = _archetype_for_drivers(cfg, world, ward_id, hardship, backlash, ideology)
    support = _clamp01(0.2 + 0.5 * hardship + 0.25 * backlash)
    capability = _clamp01(0.2 + 0.5 * _smuggling_score(world, ward_id) + 0.25 * hardship)
    secrecy = _clamp01(0.5 + 0.2 * (1.0 - float(getattr(world, "counterintel_by_ward", {}).get(ward_id, 0.0))))
    cell = CellState(
        cell_id=cell_id,
        ward_id=ward_id,
        archetype=archetype,
        support=support,
        capability=capability,
        secrecy=secrecy,
        heat=0.05,
        morale=0.6,
        status="DORMANT",
        last_update_day=getattr(world, "day", 0),
        notes={"drivers": {"hardship": hardship, "backlash": backlash, "ideology": ideology}},
    )
    cells.append(cell)
    record_event(
        world,
        {
            "event": "CELL_EMERGED",
            "ward_id": ward_id,
            "cell_id": cell_id,
            "archetype": archetype,
        },
    )
    return cell


def _update_cell_state(world: Any, cell: CellState, cfg: InsurgencyConfig, day: int) -> None:
    hardship = _hardship_score(world, cell.ward_id)
    backlash = _backlash_score(world, cell.ward_id)
    ideology = _ideology_score(world, cell.ward_id)
    drift_up = 0.1 * hardship + 0.1 * backlash
    drift_down = cfg.cell_decay_rate * (1.0 - hardship) * (1.0 - backlash)
    cell.support = _clamp01(cell.support + drift_up - drift_down)
    cap_up = 0.15 * _smuggling_score(world, cell.ward_id)
    cell.capability = _clamp01(cell.capability + cap_up - cfg.cell_decay_rate * 0.5)
    cell.secrecy = _clamp01(cell.secrecy - 0.1 * cell.heat + 0.05 * (1.0 - backlash))
    cell.heat = _clamp01(cell.heat * 0.6)
    cell.last_update_day = day
    cell.notes["drivers"] = {"hardship": hardship, "backlash": backlash, "ideology": ideology}
    if cell.capability < 0.05 and cell.heat > 0.7:
        cell.status = "BROKEN"


def _plan_ops(world: Any, cfg: InsurgencyConfig, day: int) -> None:
    active_ops = ensure_active_ops(world)
    cells_by_ward = ensure_cells(world)
    if len(active_ops) >= cfg.max_ops_active:
        return

    for ward_id, cells in sorted(cells_by_ward.items()):
        for cell in sorted(cells, key=lambda c: c.cell_id):
            if cell.status == "BROKEN":
                continue
            already_active = any(plan.cell_id == cell.cell_id for plan in active_ops.values())
            if already_active or len(active_ops) >= cfg.max_ops_active:
                continue
            op_chance = cfg.base_op_rate * _clamp01(0.5 * cell.support + 0.5 * cell.capability)
            roll = _stable_float(cfg, cell.cell_id, day, "op_chance")
            if roll > op_chance:
                continue
            options = ARCHETYPE_OPS.get(cell.archetype, ("PROPAGANDA_BROADCAST",))
            pick_idx = int(_stable_float(cfg, cell.cell_id, day, "op_pick", spread=len(options))) % len(options)
            op_type = options[pick_idx]
            op_id = f"op:{cell.cell_id}:{day}:{op_type.lower()}"
            plan = CellOpPlan(
                op_id=op_id,
                cell_id=cell.cell_id,
                ward_id=cell.ward_id,
                op_type=op_type,
                day_started=day,
                day_end=day + 2,
                target_kind="WARD" if op_type != "SABOTAGE_RELAY" else "RELAY",
                target_id=cell.ward_id,
                intensity=_clamp01(0.4 + 0.6 * cell.capability),
                reason="auto-plan",
                score_breakdown={"support": cell.support, "capability": cell.capability},
            )
            active_ops[plan.op_id] = plan
            cell.status = "ACTIVE"
            cell.heat = _clamp01(cell.heat + 0.2)
            record_event(
                world,
                {
                    "event": "CELL_OP_STARTED",
                    "op_id": op_id,
                    "cell_id": cell.cell_id,
                    "ward_id": cell.ward_id,
                    "op_type": op_type,
                },
            )


def _apply_effects(world: Any, plan: CellOpPlan, success: bool) -> dict[str, object]:
    effects: dict[str, object] = {"success": success}
    if plan.op_type == "SABOTAGE_RELAY" and success:
        comms_mods = getattr(world, "comms_mod_by_ward", {}) or {}
        mod = comms_mods.get(plan.ward_id)
        if not isinstance(mod, CommsModifiers):
            mod = CommsModifiers()
        mod.loss_mult = max(1.0, float(mod.loss_mult)) + 0.2 * plan.intensity
        comms_mods[plan.ward_id] = mod
        world.comms_mod_by_ward = comms_mods
        effects["comms_loss_mult"] = mod.loss_mult
    return effects


def _response_type(world: Any, ward_id: str) -> str:
    policing_state = ensure_policing_state(world, ward_id)
    mix = policing_state.doctrine_mix or {}
    if not mix:
        return "PROCEDURAL"
    best = sorted(((val, key) for key, val in mix.items()), reverse=True)
    return best[0][1]


def _resolve_ops(world: Any, cfg: InsurgencyConfig, day: int) -> None:
    active_ops = ensure_active_ops(world)
    history = ensure_op_history(world)
    counterintel = getattr(world, "counterintel_by_ward", {}) or {}
    cells_by_ward = ensure_cells(world)
    to_remove: list[str] = []
    metrics = ensure_metrics(world)

    for op_id, plan in sorted(active_ops.items()):
        if day < plan.day_end:
            continue
        detect_base = 0.2 + 0.5 * float(counterintel.get(plan.ward_id, 0.0) or 0.0)
        response = _response_type(world, plan.ward_id)
        response_effect = DOCTRINE_PROFILES.get(response, {})
        detect_base *= float(response_effect.get("detection", 1.0))
        success_chance = _clamp01(plan.intensity * 0.7 + 0.2)
        detect_roll = _stable_float(cfg, op_id, day, "detect")
        detected = detect_roll < _clamp01(detect_base)
        success_roll = _stable_float(cfg, op_id, day, "success")
        success = success_roll < success_chance
        effects = _apply_effects(world, plan, success)
        status = "SUCCEEDED" if success else "FAILED"
        if detected:
            status = "DETECTED" if not success else "ROLLED_UP"
        outcome = CellOpOutcome(op_id=op_id, day=day, status=status, effects=effects)
        history.append(outcome)
        if len(history) > 200:
            del history[: len(history) - 200]
        to_remove.append(op_id)
        metrics.inc("insurgency.ops_resolved", 1)
        if detected:
            metrics.inc("insurgency.ops_detected", 1)
        if success:
            metrics.inc("insurgency.ops_success", 1)
        record_event(
            world,
            {
                "event": "CELL_OP_RESOLVED",
                "op_id": op_id,
                "status": status,
                "ward_id": plan.ward_id,
            },
        )
        # update cell state and backlash
        cell = next((c for c in cells_by_ward.get(plan.ward_id, []) if c.cell_id == plan.cell_id), None)
        if cell:
            cell.heat = _clamp01(cell.heat + 0.3)
            suppression = cfg.suppression_effect * float(response_effect.get("suppression", 1.0))
            cell.capability = _clamp01(cell.capability - suppression * 0.3)
            if detected:
                cell.secrecy = _clamp01(cell.secrecy * 0.6)
                cell.status = "DORMANT"
            if response == "TERROR":
                backlash_delta = cfg.backlash_effect * (0.5 + cell.heat)
                cell.support = _clamp01(cell.support + backlash_delta)
                metrics.set_gauge("insurgency.backlash_proxy", metrics.get("insurgency.backlash_proxy", 0.0) + backlash_delta)
    for op_id in to_remove:
        active_ops.pop(op_id, None)


def _emerge_cells(world: Any, cfg: InsurgencyConfig, day: int) -> None:
    cells_by_ward = ensure_cells(world)
    wards = getattr(world, "wards", {}) or {}
    phase_key = _phase_key(world)
    phase_mult = 1.0 if phase_key == "P1" else 1.2
    for ward_id in sorted(wards.keys()):
        hardship = _hardship_score(world, ward_id)
        backlash = _backlash_score(world, ward_id)
        ideology = _ideology_score(world, ward_id)
        smuggling = _smuggling_score(world, ward_id)
        base_rate = cfg.base_emergence_rate * phase_mult
        driver = hardship + 0.5 * backlash + 0.25 * ideology + 0.25 * smuggling
        p_emerge = base_rate * (1.0 + driver)
        roll = _stable_float(cfg, ward_id, day, "emerge")
        if roll > p_emerge:
            continue
        bucket = cells_by_ward.setdefault(ward_id, [])
        if len(bucket) >= max(1, int(cfg.max_cells_per_ward)):
            continue
        _spawn_cell(world, ward_id, cfg, hardship, backlash, ideology)


def _refresh_metrics(world: Any) -> None:
    metrics = ensure_metrics(world)
    cells_by_ward = ensure_cells(world)
    total_cells = sum(len(cells) for cells in cells_by_ward.values())
    active_ops = len(ensure_active_ops(world))
    metrics.set_gauge("insurgency.cells_active", total_cells)
    metrics.set_gauge("insurgency.ops_active", active_ops)
    topk_path = "insurgency.wards_support"
    metrics.topk.pop(topk_path, None)
    for ward_id, cells in cells_by_ward.items():
        if not cells:
            continue
        avg_support = sum(c.support for c in cells) / len(cells)
        metrics.topk_add(topk_path, ward_id, avg_support, payload={"cells": len(cells)})


def run_insurgency_week(world: Any, day: int | None = None) -> None:
    cfg = ensure_insurgency_config(world)
    if not cfg.enabled:
        return
    day = getattr(world, "day", 0) if day is None else int(day)
    _emerge_cells(world, cfg, day)
    for cells in ensure_cells(world).values():
        for cell in cells:
            _update_cell_state(world, cell, cfg, day)
    _plan_ops(world, cfg, day)
    _resolve_ops(world, cfg, day)
    _refresh_metrics(world)


__all__ = [
    "CellOpOutcome",
    "CellOpPlan",
    "CellState",
    "InsurgencyConfig",
    "ensure_insurgency_config",
    "ensure_cells",
    "ensure_active_ops",
    "ensure_op_history",
    "run_insurgency_week",
]
