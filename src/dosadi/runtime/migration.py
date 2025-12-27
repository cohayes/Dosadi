from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from hashlib import sha256
from typing import TYPE_CHECKING, Iterable, Mapping

from dosadi.runtime.class_system import class_hardship
from dosadi.runtime.telemetry import Metrics, TopK

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from dosadi.state import WorldState


@dataclass(slots=True)
class MigrationConfig:
    enabled: bool = False
    update_cadence_days: int = 3
    neighbor_topk: int = 12
    route_topk: int = 24
    max_total_movers_per_update: int = 5000
    deterministic_salt: str = "migration-v1"
    camp_decay_per_day: float = 0.02
    flow_history_limit: int = 120


@dataclass(slots=True)
class WardMigrationState:
    ward_id: str
    pop: int = 0
    displaced: int = 0
    camp: int = 0
    intake_capacity: int = 0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class MigrationFlow:
    day: int
    from_ward: str
    to_ward: str
    movers: int
    reason_codes: list[str]


def _ensure_migration_fields(world: WorldState) -> tuple[MigrationConfig, dict[str, WardMigrationState], list[MigrationFlow]]:
    cfg = getattr(world, "migration_cfg", None)
    if cfg is None:
        cfg = MigrationConfig()
        world.migration_cfg = cfg

    migration_by_ward = getattr(world, "migration_by_ward", None)
    if migration_by_ward is None:
        migration_by_ward = {}
        world.migration_by_ward = migration_by_ward

    migration_flows = getattr(world, "migration_flows", None)
    if migration_flows is None:
        migration_flows = []
        world.migration_flows = migration_flows

    return cfg, migration_by_ward, migration_flows


def _stable_rng(seed: int, day: int, salt: str) -> random.Random:
    digest = sha256(f"{seed}:{day}:{salt}".encode("utf-8")).hexdigest()
    return random.Random(int(digest, 16) % (2**32))


def _neighbor_ids(world: WorldState, ward_id: str) -> list[str]:
    neighbors: set[str] = set()
    for edge in getattr(world, "edges", {}).values():
        origin = getattr(edge, "origin", None) or getattr(edge, "a", None)
        destination = getattr(edge, "destination", None) or getattr(edge, "b", None)
        if origin == ward_id and destination:
            neighbors.add(str(destination))
        if destination == ward_id and origin:
            neighbors.add(str(origin))
    if not neighbors:
        neighbors.update(k for k in getattr(world, "wards", {}).keys() if k != ward_id)
    return sorted(neighbors)


def _edge_allows_flow(edge: object) -> bool:
    if edge is None:
        return True
    if isinstance(edge, Mapping):
        if edge.get("collapsed"):
            return False
        if edge.get("status") == "collapsed":
            return False
    collapsed = getattr(edge, "collapsed", False)
    status = getattr(edge, "status", None)
    if collapsed or status == "collapsed":
        return False
    return True


def _compute_capacity(world: WorldState, ward_id: str) -> int:
    ward = world.wards.get(ward_id)
    if ward is None:
        return 0
    base = 200
    base += int(getattr(getattr(ward, "stocks", None), "water_liters", 0.0) / 50)
    base += int(getattr(getattr(ward, "stocks", None), "biomass_kg", 0.0) / 10)
    policy = getattr(world, "inst_policy_by_ward", {}).get(ward_id, {})
    bias = 0.0
    if isinstance(policy, Mapping):
        bias = float(policy.get("refugee_intake_bias", 0.0))
    capacity = int(base * max(0.1, 1.0 + bias))
    return max(0, capacity)


def _update_camps_and_effects(world: WorldState, ward_state: WardMigrationState, cfg: MigrationConfig) -> None:
    ward = world.wards.get(ward_state.ward_id)
    if ward is None:
        return
    if ward_state.camp > 0:
        ward.need_index = min(1.0, ward.need_index + ward_state.camp * 0.0002)
        ward.legitimacy = max(0.0, ward.legitimacy - ward_state.camp * 0.0001)
    if cfg.camp_decay_per_day > 0:
        ward_state.camp = int(max(0.0, ward_state.camp * (1.0 - cfg.camp_decay_per_day)))


def _compute_displacement(world: WorldState, ward_state: WardMigrationState, rng: random.Random) -> int:
    ward = world.wards.get(ward_state.ward_id)
    if ward is None:
        return 0
    pressure = max(0.0, ward.need_index + ward.risk_index)
    hardship = class_hardship(world, ward_state.ward_id)
    return int((pressure + 0.8 * hardship) * 50 + rng.randint(0, 10))


def _score_destination(
    *,
    origin: WardMigrationState,
    dest: WardMigrationState,
    capacity_remaining: int,
    rng: random.Random,
) -> float:
    base = float(capacity_remaining)
    return base + (1.0 - getattr(dest, "notes", {}).get("risk", 0.0)) + rng.random() * 0.001


def _bounded_append_flows(migration_flows: list[MigrationFlow], new_flows: Iterable[MigrationFlow], *, limit: int) -> None:
    migration_flows.extend(new_flows)
    if len(migration_flows) > limit:
        migration_flows[:] = migration_flows[-limit:]


def run_migration_for_day(world: WorldState, *, day: int | None = None) -> None:
    cfg, migration_by_ward, migration_flows = _ensure_migration_fields(world)
    if not getattr(cfg, "enabled", False):
        return

    current_day = day if day is not None else getattr(world, "day", 0)
    rng = _stable_rng(getattr(world, "seed", 0), current_day, cfg.deterministic_salt)

    for ward_id in sorted(world.wards):
        ward_state = migration_by_ward.get(ward_id)
        if ward_state is None:
            ward_state = WardMigrationState(ward_id=ward_id, pop=int(getattr(world.wards[ward_id], "population", 0) or 0))
            migration_by_ward[ward_id] = ward_state
        ward_state.intake_capacity = _compute_capacity(world, ward_id)
        ward_state.displaced += _compute_displacement(world, ward_state, rng)
        _update_camps_and_effects(world, ward_state, cfg)

    if current_day % max(1, int(cfg.update_cadence_days)) != 0:
        return

    total_allowed = max(0, int(cfg.max_total_movers_per_update))
    global_remaining = total_allowed
    new_flows: list[MigrationFlow] = []

    for origin_id in sorted(migration_by_ward):
        origin_state = migration_by_ward[origin_id]
        if origin_state.displaced <= 0:
            origin_state.last_update_day = current_day
            continue

        neighbors = _neighbor_ids(world, origin_id)[: max(1, int(cfg.neighbor_topk))]
        scored: list[tuple[float, str]] = []

        for neighbor_id in neighbors:
            dest_state = migration_by_ward.get(neighbor_id)
            if dest_state is None:
                continue
            edge = None
            for e in getattr(world, "edges", {}).values():
                if (
                    getattr(e, "origin", None) == origin_id
                    or (isinstance(e, Mapping) and e.get("origin") == origin_id)
                ) and (
                    getattr(e, "destination", None) == neighbor_id
                    or (isinstance(e, Mapping) and e.get("destination") == neighbor_id)
                ):
                    edge = e
                    break
                if (
                    getattr(e, "a", None) == origin_id
                    or (isinstance(e, Mapping) and e.get("a") == origin_id)
                ) and (
                    getattr(e, "b", None) == neighbor_id
                    or (isinstance(e, Mapping) and e.get("b") == neighbor_id)
                ):
                    edge = e
                    break
                if (
                    getattr(e, "a", None) == neighbor_id
                    or (isinstance(e, Mapping) and e.get("a") == neighbor_id)
                ) and (
                    getattr(e, "b", None) == origin_id
                    or (isinstance(e, Mapping) and e.get("b") == origin_id)
                ):
                    edge = e
                    break
            if not _edge_allows_flow(edge):
                continue
            capacity_remaining = max(0, dest_state.intake_capacity - dest_state.displaced)
            scored.append((_score_destination(origin=origin_state, dest=dest_state, capacity_remaining=capacity_remaining, rng=rng), neighbor_id))

        scored.sort(key=lambda item: (-item[0], item[1]))
        scored = scored[: max(1, int(cfg.route_topk))]

        origin_remaining = origin_state.displaced
        for _, dest_id in scored:
            if origin_remaining <= 0 or global_remaining <= 0:
                break
            dest_state = migration_by_ward[dest_id]
            capacity_remaining = max(0, dest_state.intake_capacity - dest_state.displaced)
            movers = min(origin_remaining, capacity_remaining, global_remaining)
            if movers <= 0:
                continue
            dest_state.displaced += movers
            origin_remaining -= movers
            global_remaining -= movers
            new_flows.append(
                MigrationFlow(
                    day=current_day,
                    from_ward=origin_id,
                    to_ward=dest_id,
                    movers=movers,
                    reason_codes=["PRESSURE"],
                )
            )

        if origin_remaining > 0:
            origin_state.camp += origin_remaining
        origin_state.displaced = 0
        origin_state.last_update_day = current_day

    _bounded_append_flows(migration_flows, new_flows, limit=max(1, int(cfg.flow_history_limit)))

    for state in migration_by_ward.values():
        if state.camp > 0:
            _update_camps_and_effects(world, state, cfg)

    metrics: Metrics | None = getattr(world, "metrics", None)
    if metrics is not None:
        total_displaced = sum(state.displaced for state in migration_by_ward.values())
        total_camp = sum(state.camp for state in migration_by_ward.values())
        metrics.set_gauge(
            "migration",
            {
                "total_displaced": total_displaced,
                "total_camp": total_camp,
                "flows_count": len(migration_flows),
                "movers_total": sum(flow.movers for flow in migration_flows),
            },
        )
        metrics.topk["migration.camps"] = metrics.topk.get("migration.camps") or TopK(k=max(1, int(cfg.neighbor_topk)))
        metrics.topk["migration.camps"].entries.clear()
        for ward_id, state in migration_by_ward.items():
            metrics.topk_add("migration.camps", ward_id, float(state.camp))

    event_ring = getattr(world, "event_ring", None)
    if event_ring is not None:
        for flow in new_flows:
            event_ring.append({"type": "REFUGEE_FLOW", "day": flow.day, "from": flow.from_ward, "to": flow.to_ward, "movers": flow.movers})
        for state in migration_by_ward.values():
            if state.camp > 0:
                event_ring.append({"type": "CAMP_GROWTH", "day": current_day, "ward": state.ward_id, "size": state.camp})


def save_migration_seed(world: WorldState, path) -> None:
    _, migration_by_ward, migration_flows = _ensure_migration_fields(world)
    wards = [
        {
            "ward_id": state.ward_id,
            "pop": state.pop,
            "displaced": state.displaced,
            "camp": state.camp,
            "intake_capacity": state.intake_capacity,
        }
        for state in sorted(migration_by_ward.values(), key=lambda s: s.ward_id)
    ]
    flows = [
        {
            "day": flow.day,
            "from_ward": flow.from_ward,
            "to_ward": flow.to_ward,
            "movers": flow.movers,
            "reason_codes": list(flow.reason_codes),
        }
        for flow in migration_flows
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump({"wards": wards, "flows": flows}, fp, indent=2, sort_keys=True)

