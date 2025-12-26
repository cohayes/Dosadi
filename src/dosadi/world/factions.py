from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Dict, Iterable, Mapping


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def pseudo_rand01(key: str) -> float:
    digest = sha256(key.encode("utf-8")).digest()
    sample = int.from_bytes(digest[:8], "big")
    return sample / float(2**64)


@dataclass(slots=True)
class Faction:
    faction_id: str
    name: str
    kind: str
    color: str = ""
    influence: float = 10.0
    budget_points: float = 10.0
    security_capacity: int = 0
    raiding_capacity: int = 0
    logistics_capacity: int = 0
    policy: dict[str, object] = field(default_factory=dict)
    last_updated_day: int = -1


@dataclass(slots=True)
class FactionTerritory:
    wards: dict[str, float] = field(default_factory=dict)
    edges: dict[str, float] = field(default_factory=dict)
    nodes: dict[str, float] = field(default_factory=dict)
    last_claim_day: dict[str, int] = field(default_factory=dict)

    def decay(self, *, cfg: "FactionSystemConfig") -> None:
        if cfg.claim_decay_per_day <= 0:
            return
        factor = 1.0 - cfg.claim_decay_per_day
        for bucket in (self.wards, self.edges, self.nodes):
            for key, strength in list(bucket.items()):
                decayed = strength * factor
                if decayed <= 0.0:
                    bucket.pop(key, None)
                    self.last_claim_day.pop(key, None)
                else:
                    bucket[key] = decayed


@dataclass(slots=True)
class FactionSystemConfig:
    enabled: bool = False
    max_factions: int = 32
    max_claims_per_faction: int = 200
    claim_decay_per_day: float = 0.002
    claim_gain_on_success: float = 0.05
    claim_loss_on_failure: float = 0.04
    min_days_between_claim_updates: int = 3
    topk_opportunities: int = 25
    max_actions_per_faction_per_day: int = 2
    deterministic_salt: str = "factions-v1"


@dataclass(slots=True)
class FactionSystemState:
    last_run_day: int = -1
    actions_taken_today: dict[str, int] = field(default_factory=dict)


def ensure_faction_territory(world: Any, faction_id: str) -> FactionTerritory:
    territories: Dict[str, FactionTerritory] = getattr(world, "faction_territory", {})
    if faction_id not in territories:
        territories[faction_id] = FactionTerritory()
        world.faction_territory = territories
    return territories[faction_id]


def update_claim(
    *,
    territory: FactionTerritory,
    bucket: str,
    key: str,
    delta: float,
    day: int,
    cfg: FactionSystemConfig,
) -> float:
    store = territory.wards if bucket == "ward" else territory.edges if bucket == "edge" else territory.nodes
    current = store.get(key, 0.0)
    updated = _clamp01(current + delta)
    if abs(updated - current) < 1e-9:
        return updated
    store[key] = updated
    territory.last_claim_day[key] = day
    return updated


def enforce_claim_cap(territory: FactionTerritory, *, cfg: FactionSystemConfig) -> None:
    items: list[tuple[str, str, float]] = []
    for bucket_name, bucket in ("ward", territory.wards), ("edge", territory.edges), ("node", territory.nodes):
        for key, strength in bucket.items():
            items.append((bucket_name, key, strength))

    if len(items) <= cfg.max_claims_per_faction:
        return

    items.sort(key=lambda row: (row[2], row[0], row[1]))
    to_prune = len(items) - cfg.max_claims_per_faction
    for bucket_name, key, _strength in items[:to_prune]:
        target_bucket = territory.wards if bucket_name == "ward" else territory.edges if bucket_name == "edge" else territory.nodes
        target_bucket.pop(key, None)
        territory.last_claim_day.pop(key, None)


def stable_faction_definitions(factions: Mapping[str, Faction]) -> list[Faction]:
    return [factions[key] for key in sorted(factions.keys())]


def export_factions_seed(world: Any) -> list[dict[str, object]]:
    factions: Mapping[str, Faction] = getattr(world, "factions", {})
    territories: Mapping[str, FactionTerritory] = getattr(world, "faction_territory", {})

    payload: list[dict[str, object]] = []
    for faction in stable_faction_definitions(factions):
        terr = territories.get(faction.faction_id, FactionTerritory())
        payload.append(
            {
                "faction_id": faction.faction_id,
                "name": faction.name,
                "kind": faction.kind,
                "territory": {
                    "wards": {k: terr.wards[k] for k in sorted(terr.wards.keys())},
                    "edges": {k: terr.edges[k] for k in sorted(terr.edges.keys())},
                    "nodes": {k: terr.nodes[k] for k in sorted(terr.nodes.keys())},
                },
            }
        )
    return payload


__all__ = [
    "Faction",
    "FactionTerritory",
    "FactionSystemConfig",
    "FactionSystemState",
    "ensure_faction_territory",
    "update_claim",
    "enforce_claim_cap",
    "export_factions_seed",
    "pseudo_rand01",
]
