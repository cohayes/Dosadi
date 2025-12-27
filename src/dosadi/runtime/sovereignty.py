from __future__ import annotations

"""Sovereignty and fragmentation runtime helpers (v1).

This module captures the minimum surface needed for the civil war & fragmentation
checklist (D-RUNTIME-0298) without introducing nondeterministic world scans.
The implementation focuses on:

* Stable configuration + state containers.
* Deterministic fracture pressure evaluation that can trigger splinter polities.
* Contested corridor tracking with lightweight conflict fronts.
* Bounded metrics suitable for cockpit/telemetry inspection.

It intentionally keeps the mechanics simple and bounded so it can be safely
integrated into the wider runtime once the corresponding feature flag is
enabled.
"""

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping


def _clamp01(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


def _stable_rand01(*parts: object) -> float:
    blob = "|".join(str(part) for part in parts)
    digest = sha256(blob.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


@dataclass(slots=True)
class SovereigntyConfig:
    enabled: bool = False
    update_cadence_days: int = 7
    deterministic_salt: str = "sovereignty-v1"
    max_polities: int = 6
    max_contested_corridors: int = 30
    split_threshold: float = 0.75
    merge_threshold: float = 0.25
    border_friction: float = 0.20
    reconquest_bias: float = 0.55
    negotiation_bias: float = 0.45


@dataclass(slots=True)
class PolityState:
    polity_id: str
    name: str
    capital_ward_id: str
    style: str
    legitimacy: float = 0.5
    capacity: float = 0.5
    cohesion: float = 0.5
    treasury: float = 0.0
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class TerritoryState:
    ward_control: dict[str, str] = field(default_factory=dict)
    corridor_control: dict[str, str] = field(default_factory=dict)
    corridor_contested: dict[str, list[str]] = field(default_factory=dict)
    corridor_endpoints: dict[str, tuple[str, str]] = field(default_factory=dict)
    last_update_day: int = -1


@dataclass(slots=True)
class ConflictFront:
    front_id: str
    corridor_id: str
    polity_a: str
    polity_b: str
    intensity: float
    status: str
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SovereigntyState:
    polities: dict[str, PolityState] = field(default_factory=dict)
    territory: TerritoryState = field(default_factory=TerritoryState)
    fronts: dict[str, ConflictFront] = field(default_factory=dict)
    ward_switches: int = 0
    metrics: dict[str, object] = field(default_factory=dict)
    next_polity_seq: int = 1


def ensure_sovereignty_config(world) -> SovereigntyConfig:
    cfg = getattr(world, "sovereignty_cfg", None)
    if not isinstance(cfg, SovereigntyConfig):
        cfg = SovereigntyConfig()
        world.sovereignty_cfg = cfg
    return cfg


def ensure_sovereignty_state(
    world,
    *,
    ward_ids: Iterable[str] | None = None,
    corridors: Mapping[str, tuple[str, str]] | None = None,
) -> SovereigntyState:
    cfg = ensure_sovereignty_config(world)
    state = getattr(world, "sovereignty_state", None)
    if not isinstance(state, SovereigntyState):
        state = SovereigntyState()
        world.sovereignty_state = state

    territory = state.territory
    if ward_ids is not None:
        for ward_id in ward_ids:
            territory.ward_control.setdefault(str(ward_id), "polity:empire")

    if corridors is not None:
        for corridor_id, endpoints in corridors.items():
            a, b = endpoints
            cid = str(corridor_id)
            territory.corridor_endpoints[cid] = (str(a), str(b))
            territory.corridor_control.setdefault(cid, "polity:empire")

    if "polity:empire" not in state.polities:
        first_ward = next(iter(territory.ward_control.keys()), "ward:0")
        state.polities["polity:empire"] = PolityState(
            polity_id="polity:empire",
            name="Empire",
            capital_ward_id=str(first_ward),
            style="COUNCIL",
            legitimacy=0.7,
            capacity=0.7,
            cohesion=0.7,
        )

    _update_metrics(world)
    _refresh_corridor_contest(state, cfg)
    return state


def _pressure_inputs(world, ward_id: str) -> dict[str, float]:
    gov = getattr(world, "governance_failure_pressure", {}).get(ward_id, 0.0)
    insurgency = getattr(world, "insurgency_support", {}).get(ward_id, 0.0)
    hardship = getattr(world, "hardship_pressure", {}).get(ward_id, 0.0)
    backlash = getattr(world, "policing_backlash", {}).get(ward_id, 0.0)
    return {
        "gov": _clamp01(gov),
        "insurgency": _clamp01(insurgency),
        "hardship": _clamp01(hardship),
        "backlash": _clamp01(backlash),
    }


def ward_fracture_pressure(world, ward_id: str) -> float:
    state = ensure_sovereignty_state(world)
    inputs = _pressure_inputs(world, ward_id)
    contested_bonus = 0.0
    for corridor_id, endpoints in state.territory.corridor_endpoints.items():
        if ward_id not in endpoints:
            continue
        if corridor_id in state.territory.corridor_contested:
            contested_bonus = max(contested_bonus, 0.1 + 0.05 * len(state.territory.corridor_contested[corridor_id]))
    avg_pressure = sum(inputs.values()) / 4.0
    max_pressure = max(inputs.values())
    weight = 0.6 * avg_pressure + 0.4 * max_pressure
    return _clamp01(weight + contested_bonus)


def _connected_components(wards: set[str], endpoints: Mapping[str, tuple[str, str]]) -> list[set[str]]:
    adjacency: MutableMapping[str, set[str]] = {ward: set() for ward in wards}
    for a, b in endpoints.values():
        if a in adjacency and b in adjacency:
            adjacency[a].add(b)
            adjacency[b].add(a)

    seen: set[str] = set()
    groups: list[set[str]] = []
    for ward in sorted(wards):
        if ward in seen:
            continue
        stack = [ward]
        group: set[str] = set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            group.add(node)
            stack.extend(sorted(adjacency.get(node, ())))
        groups.append(group)
    return groups


def _spawn_polity(world, wards: set[str]) -> str:
    state = ensure_sovereignty_state(world)
    cfg = ensure_sovereignty_config(world)
    if len(state.polities) >= max(1, cfg.max_polities):
        return "polity:empire"

    seq = state.next_polity_seq
    state.next_polity_seq += 1
    polity_id = f"polity:warlord:{seq}"
    pressures = {ward: ward_fracture_pressure(world, ward) for ward in wards}
    capital = max(pressures.items(), key=lambda item: (round(item[1], 6), item[0]))[0]
    style_candidates = ["THEOCRACY", "MILITARY", "GUILD_CARTEL", "COUNCIL", "WARLORD"]
    style_idx = int(_stable_rand01(cfg.deterministic_salt, polity_id) * len(style_candidates)) % len(style_candidates)
    state.polities[polity_id] = PolityState(
        polity_id=polity_id,
        name=f"Splinter {seq}",
        capital_ward_id=capital,
        style=style_candidates[style_idx],
        legitimacy=_clamp01(0.4 + 0.2 * _stable_rand01(polity_id, "leg")),
        capacity=_clamp01(0.35 + 0.3 * _stable_rand01(polity_id, "cap")),
        cohesion=_clamp01(0.35 + 0.3 * _stable_rand01(polity_id, "coh")),
    )
    return polity_id


def _assign_cluster(world, wards: set[str], polity_id: str) -> None:
    state = ensure_sovereignty_state(world)
    for ward_id in wards:
        prev = state.territory.ward_control.get(ward_id)
        if prev != polity_id:
            state.ward_switches += 1
        state.territory.ward_control[ward_id] = polity_id


def _refresh_corridor_contest(state: SovereigntyState, cfg: SovereigntyConfig) -> None:
    contested: dict[str, list[str]] = {}
    control: dict[str, str] = {}
    for corridor_id, endpoints in state.territory.corridor_endpoints.items():
        a, b = endpoints
        polity_a = state.territory.ward_control.get(a, "polity:empire")
        polity_b = state.territory.ward_control.get(b, "polity:empire")
        if polity_a == polity_b:
            control[corridor_id] = polity_a
            continue
        parties = sorted({polity_a, polity_b})
        contested[corridor_id] = parties
        control[corridor_id] = parties[0]

    if len(contested) > cfg.max_contested_corridors:
        victims = sorted(contested.keys())[cfg.max_contested_corridors :]
        for corridor_id in victims:
            contested.pop(corridor_id, None)

    state.territory.corridor_contested = contested
    state.territory.corridor_control.update(control)


def _update_fronts(world) -> None:
    state = ensure_sovereignty_state(world)
    cfg = ensure_sovereignty_config(world)
    for corridor_id, parties in state.territory.corridor_contested.items():
        if len(parties) < 2:
            continue
        front_id = corridor_id
        a, b = parties[0], parties[1]
        intensity = _clamp01(cfg.border_friction + 0.3 * _stable_rand01(corridor_id, a, b))
        front = state.fronts.get(front_id)
        status = "COLD"
        if intensity > 0.7:
            status = "OPEN_WAR"
        elif intensity > 0.4:
            status = "SKIRMISH"
        notes = {"corridor": corridor_id, "parties": parties}
        if front is None:
            state.fronts[front_id] = ConflictFront(
                front_id=front_id,
                corridor_id=corridor_id,
                polity_a=a,
                polity_b=b,
                intensity=intensity,
                status=status,
                notes=notes,
            )
        else:
            front.intensity = intensity
            front.status = status
            front.polity_a = a
            front.polity_b = b
            front.notes = notes


def _resolve_contested(world) -> None:
    state = ensure_sovereignty_state(world)
    cfg = ensure_sovereignty_config(world)
    for corridor_id, parties in list(state.territory.corridor_contested.items()):
        if len(parties) < 2:
            continue
        front = state.fronts.get(corridor_id)
        intensity = getattr(front, "intensity", cfg.border_friction)
        reconquest_pull = cfg.reconquest_bias + state.polities.get("polity:empire", PolityState("", "", "", "")).capacity
        autonomy_pull = cfg.negotiation_bias
        if len(parties) > 1:
            for polity_id in parties:
                if polity_id == "polity:empire":
                    continue
                autonomy_pull += state.polities.get(polity_id, PolityState(polity_id, "", "", "")).capacity

        settle_threshold = cfg.merge_threshold + 0.2 * (1.0 - intensity)
        if settle_threshold >= 1.0 or _stable_rand01(cfg.deterministic_salt, corridor_id, intensity) < settle_threshold:
            winner = "polity:empire" if reconquest_pull >= autonomy_pull else parties[-1]
            state.territory.corridor_control[corridor_id] = winner
            state.territory.corridor_contested.pop(corridor_id, None)


def _update_metrics(world) -> None:
    state = getattr(world, "sovereignty_state", None)
    if state is None:
        return
    metrics = getattr(world, "metrics", None)
    if metrics is None or not isinstance(metrics, MutableMapping):
        metrics = {}
        world.metrics = metrics
    sov_metrics = metrics.setdefault("sovereignty", {})
    sov_metrics["polities_count"] = len(state.polities)
    sov_metrics["contested_corridors"] = len(state.territory.corridor_contested)
    sov_metrics["fronts_open_war"] = sum(1 for front in state.fronts.values() if front.status == "OPEN_WAR")
    sov_metrics["ward_switches"] = state.ward_switches
    sov_metrics["hot_fronts"] = sorted(front_id for front_id, front in state.fronts.items() if front.status != "COLD")[:10]
    state.metrics = sov_metrics


def update_sovereignty(world, *, day: int) -> None:
    cfg = ensure_sovereignty_config(world)
    if not cfg.enabled:
        return
    state = ensure_sovereignty_state(world)
    territory = state.territory
    if territory.last_update_day >= 0 and day - territory.last_update_day < max(1, cfg.update_cadence_days):
        return

    candidates: set[str] = set()
    for ward_id in sorted(territory.ward_control):
        pressure = ward_fracture_pressure(world, ward_id)
        if pressure >= cfg.split_threshold:
            candidates.add(ward_id)

    if candidates:
        groups = _connected_components(candidates, territory.corridor_endpoints)
        for group in groups:
            polity_id = _spawn_polity(world, group)
            _assign_cluster(world, group, polity_id)

    _refresh_corridor_contest(state, cfg)
    _update_fronts(world)
    _resolve_contested(world)
    territory.last_update_day = day
    _update_metrics(world)


def contested_trade_multiplier(world, corridor_id: str) -> float:
    state = ensure_sovereignty_state(world)
    cfg = ensure_sovereignty_config(world)
    if corridor_id not in state.territory.corridor_contested:
        return 1.0
    parties = state.territory.corridor_contested.get(corridor_id, [])
    return 1.0 + cfg.border_friction * max(1, len(parties))


def displacement_pressure(world, ward_id: str) -> float:
    state = ensure_sovereignty_state(world)
    pressure = 0.0
    for corridor_id, endpoints in state.territory.corridor_endpoints.items():
        if ward_id not in endpoints:
            continue
        if corridor_id in state.territory.corridor_contested:
            pressure += 0.1
    return _clamp01(pressure)


def sovereignty_signature(world) -> str:
    state = ensure_sovereignty_state(world)
    canonical = {
        "polities": {
            pid: {
                "name": pol.name,
                "capital": pol.capital_ward_id,
                "style": pol.style,
                "leg": round(pol.legitimacy, 4),
                "cap": round(pol.capacity, 4),
                "coh": round(pol.cohesion, 4),
            }
            for pid, pol in sorted(state.polities.items())
        },
        "territory": {
            "ward_control": state.territory.ward_control,
            "corridor_control": state.territory.corridor_control,
            "contested": state.territory.corridor_contested,
        },
        "fronts": {
            fid: {
                "corridor": front.corridor_id,
                "a": front.polity_a,
                "b": front.polity_b,
                "int": round(front.intensity, 4),
                "status": front.status,
            }
            for fid, front in sorted(state.fronts.items())
        },
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def export_sovereignty_seed(world, base_path: Path) -> Path:
    state = ensure_sovereignty_state(world)
    path = base_path / "sovereignty.json"
    payload = {
        "polities": [asdict(state.polities[pid]) for pid in sorted(state.polities)],
        "territory": {
            "ward_control": state.territory.ward_control,
            "corridor_control": state.territory.corridor_control,
            "corridor_contested": state.territory.corridor_contested,
        },
        "fronts": [
            {
                "front_id": front.front_id,
                "corridor_id": front.corridor_id,
                "polity_a": front.polity_a,
                "polity_b": front.polity_b,
                "intensity": front.intensity,
                "status": front.status,
            }
            for front in sorted(state.fronts.values(), key=lambda fr: fr.front_id)
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)
    return path

