from __future__ import annotations

"""Diplomacy and Treaties v1.

This module introduces a minimal diplomacy surface for wards/factions to
coordinate on nonviolent agreements. Two agreement types are supported:

* corridor stabilization: cooperating to reduce risk on shared corridors
* resource sharing: transferring budget when one party has surplus

The engine is deterministic, bounded, and gated behind a config flag so the
rest of the simulation is unchanged unless explicitly enabled.
"""

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Iterable, Mapping, MutableMapping, Sequence

from dosadi.world.factions import Faction, FactionTerritory
from .corridor_risk import CorridorRiskLedger, ensure_corridor_risk_ledger


@dataclass(slots=True)
class DiplomacyConfig:
    enabled: bool = False
    max_active_treaties: int = 12
    max_new_per_day: int = 6
    min_overlap_strength: float = 0.15
    min_risk_for_stabilization: float = 0.35
    min_budget_gap_for_sharing: float = 5.0
    deterministic_salt: str = "diplomacy-treaties-v1"


@dataclass(slots=True)
class TreatyClause:
    kind: str
    scope: str
    weight: float = 1.0
    metadata: MutableMapping[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class Treaty:
    treaty_id: str
    parties: tuple[str, ...]
    clauses: tuple[TreatyClause, ...]
    proposed_day: int
    status: str = "proposed"
    activated_day: int | None = None
    expires_day: int | None = None
    summary: str = ""

    def signature_fragment(self) -> Mapping[str, object]:
        return {
            "id": self.treaty_id,
            "parties": list(self.parties),
            "status": self.status,
            "clauses": [
                {
                    "kind": clause.kind,
                    "scope": clause.scope,
                    "weight": round(clause.weight, 6),
                    "meta": {k: clause.metadata[k] for k in sorted(clause.metadata.keys())},
                }
                for clause in self.clauses
            ],
        }


@dataclass(slots=True)
class DiplomacyLedger:
    active_treaties: list[Treaty] = field(default_factory=list)
    history: list[Treaty] = field(default_factory=list)

    def signature(self) -> str:
        payload = json.dumps(
            [t.signature_fragment() for t in sorted(self.active_treaties, key=lambda t: t.treaty_id)],
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    def _index(self) -> set[str]:
        return {t.treaty_id for t in self.active_treaties} | {t.treaty_id for t in self.history}


def ensure_diplomacy_config(world) -> DiplomacyConfig:
    cfg = getattr(world, "diplomacy_cfg", None)
    if not isinstance(cfg, DiplomacyConfig):
        cfg = DiplomacyConfig()
        world.diplomacy_cfg = cfg
    return cfg


def ensure_diplomacy_ledger(world) -> DiplomacyLedger:
    ledger = getattr(world, "diplomacy_ledger", None)
    if not isinstance(ledger, DiplomacyLedger):
        ledger = DiplomacyLedger()
        world.diplomacy_ledger = ledger
    return ledger


def _stable_id(parts: Sequence[str], *, salt: str) -> str:
    material = "|".join(str(p) for p in sorted(parts))
    payload = f"{salt}|{material}"
    return sha256(payload.encode("utf-8")).hexdigest()[:16]


def _overlapping_corridor_claims(
    territories: Mapping[str, FactionTerritory],
    *,
    min_overlap: float,
) -> Mapping[str, list[tuple[str, float]]]:
    overlaps: MutableMapping[str, list[tuple[str, float]]] = {}
    for faction_id, terr in territories.items():
        for edge_id, strength in terr.edges.items():
            if strength < min_overlap:
                continue
            overlaps.setdefault(edge_id, []).append((faction_id, strength))
    for claims in overlaps.values():
        claims.sort(key=lambda row: (-round(row[1], 6), row[0]))
    return overlaps


def _corridor_stabilization_proposals(
    *,
    world,
    day: int,
    cfg: DiplomacyConfig,
    territories: Mapping[str, FactionTerritory],
    risk_ledger: CorridorRiskLedger,
) -> list[Treaty]:
    proposals: list[Treaty] = []
    overlaps = _overlapping_corridor_claims(territories, min_overlap=cfg.min_overlap_strength)
    for edge_id, claims in overlaps.items():
        risk_record = risk_ledger.edges.get(edge_id)
        risk_score = getattr(risk_record, "risk", 0.0)
        if risk_score < cfg.min_risk_for_stabilization:
            continue
        if len(claims) < 2:
            continue

        parties = tuple(sorted([claims[0][0], claims[1][0]]))
        clause = TreatyClause(
            kind="corridor_stabilization",
            scope=edge_id,
            weight=risk_score,
            metadata={"risk": round(risk_score, 3)},
        )
        treaty_id = _stable_id(parties + (edge_id,), salt=cfg.deterministic_salt)
        proposals.append(
            Treaty(
                treaty_id=treaty_id,
                parties=parties,
                clauses=(clause,),
                proposed_day=day,
                summary=f"Stabilize corridor {edge_id}",
            )
        )

    proposals.sort(key=lambda t: (-round(t.clauses[0].weight, 6), t.treaty_id))
    return proposals[: max(0, cfg.max_new_per_day)]


def _resource_sharing_proposals(
    *,
    factions: Mapping[str, Faction],
    day: int,
    cfg: DiplomacyConfig,
) -> list[Treaty]:
    if len(factions) < 2:
        return []

    richest = max(factions.values(), key=lambda f: (round(f.budget_points, 6), f.faction_id))
    poorest = min(factions.values(), key=lambda f: (round(f.budget_points, 6), f.faction_id))
    gap = richest.budget_points - poorest.budget_points
    if gap < cfg.min_budget_gap_for_sharing:
        return []

    share_amount = round(gap * 0.25, 3)
    parties = tuple(sorted([richest.faction_id, poorest.faction_id]))
    clause = TreatyClause(
        kind="resource_sharing",
        scope="budget",
        weight=gap,
        metadata={"share_amount": share_amount},
    )
    treaty_id = _stable_id(parties + ("budget",), salt=cfg.deterministic_salt)
    return [
        Treaty(
            treaty_id=treaty_id,
            parties=parties,
            clauses=(clause,),
            proposed_day=day,
            summary=f"Budget sharing {share_amount} from {richest.faction_id} to {poorest.faction_id}",
        )
    ]


def run_diplomacy_and_treaties(world, *, day: int) -> None:
    """Evaluate and activate diplomacy treaties.

    Behavior is deterministic and bounded by the configuration values. Treaties
    are only created when the feature flag is enabled, otherwise this function
    is a no-op.
    """

    cfg = ensure_diplomacy_config(world)
    if not getattr(cfg, "enabled", False):
        return

    ledger = ensure_diplomacy_ledger(world)
    factions: Mapping[str, Faction] = getattr(world, "factions", {}) or {}
    territories: Mapping[str, FactionTerritory] = getattr(world, "faction_territory", {}) or {}
    risk_ledger = ensure_corridor_risk_ledger(world)

    proposals: list[Treaty] = []
    proposals.extend(
        _corridor_stabilization_proposals(
            world=world,
            day=day,
            cfg=cfg,
            territories=territories,
            risk_ledger=risk_ledger,
        )
    )
    proposals.extend(
        _resource_sharing_proposals(
            factions=factions,
            day=day,
            cfg=cfg,
        )
    )

    existing_ids = ledger._index()
    allowed = max(0, cfg.max_active_treaties)
    for proposal in proposals:
        if len(ledger.active_treaties) >= allowed:
            break
        if proposal.treaty_id in existing_ids:
            continue
        proposal.status = "active"
        proposal.activated_day = day
        ledger.active_treaties.append(proposal)

    ledger.active_treaties.sort(key=lambda t: (t.activated_day or t.proposed_day, t.treaty_id))


__all__ = [
    "DiplomacyConfig",
    "DiplomacyLedger",
    "Treaty",
    "TreatyClause",
    "ensure_diplomacy_config",
    "ensure_diplomacy_ledger",
    "run_diplomacy_and_treaties",
]

