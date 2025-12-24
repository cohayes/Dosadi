from __future__ import annotations

from dataclasses import dataclass, field
import json
from enum import Enum
from hashlib import sha256
from typing import Dict, Iterable, Mapping


class SiteKind(Enum):
    SCRAP_FIELD = "SCRAP_FIELD"
    SALVAGE_CACHE = "SALVAGE_CACHE"
    BRINE_POCKET = "BRINE_POCKET"
    THERMAL_VENT = "THERMAL_VENT"


@dataclass(slots=True)
class ExtractionSite:
    site_id: str
    kind: SiteKind
    node_id: str
    created_day: int
    richness: float = 0.5
    depletion: float = 0.0
    down_until_day: int = -1
    tags: set[str] = field(default_factory=set)
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractionLedger:
    sites: Dict[str, ExtractionSite] = field(default_factory=dict)
    sites_by_node: Dict[str, list[str]] = field(default_factory=dict)

    def add(self, site: ExtractionSite) -> None:
        self.sites[site.site_id] = site
        bucket = self.sites_by_node.setdefault(site.node_id, [])
        if site.site_id not in bucket:
            bucket.append(site.site_id)
            bucket.sort()

    def signature(self) -> str:
        canonical: Mapping[str, object] = {
            site_id: {
                "kind": site.kind.value,
                "node": site.node_id,
                "created": site.created_day,
                "richness": round(site.richness, 6),
                "depletion": round(site.depletion, 6),
                "down_until": site.down_until_day,
                "tags": sorted(site.tags),
                "notes": {k: site.notes[k] for k in sorted(site.notes)},
            }
            for site_id, site in sorted(self.sites.items())
        }
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(payload).hexdigest()


_TAG_MAP: Mapping[str, SiteKind] = {
    "scrap_field": SiteKind.SCRAP_FIELD,
    "salvage_cache": SiteKind.SALVAGE_CACHE,
    "brine_pocket": SiteKind.BRINE_POCKET,
    "thermal_vent": SiteKind.THERMAL_VENT,
}


def ensure_extraction(world) -> ExtractionLedger:
    ledger = getattr(world, "extraction", None)
    if isinstance(ledger, ExtractionLedger):
        return ledger
    ledger = ExtractionLedger()
    world.extraction = ledger
    return ledger


def create_sites_for_node(world, node, *, day: int) -> list[str]:
    ledger = ensure_extraction(world)
    created: list[str] = []
    tags: Iterable[str] = getattr(node, "resource_tags", ()) or ()
    if not tags:
        return created

    richness = float(getattr(node, "resource_richness", 0.5))
    for tag in sorted(tags):
        kind = _TAG_MAP.get(tag)
        if kind is None:
            continue
        site_id = f"site:{node.node_id}:{kind.value}"
        if site_id in ledger.sites:
            continue

        site = ExtractionSite(
            site_id=site_id,
            kind=kind,
            node_id=node.node_id,
            created_day=day,
            richness=richness,
            tags=set(tags),
        )
        ledger.add(site)
        created.append(site_id)
        _emit_event(
            world,
            {
                "type": "EXTRACTION_SITE_CREATED",
                "site_id": site_id,
                "node_id": node.node_id,
                "kind": kind.value,
                "richness": richness,
                "day": day,
            },
        )

    return created


def _emit_event(world, event: Mapping[str, object]) -> None:
    events = getattr(world, "runtime_events", None)
    if not isinstance(events, list):
        events = []
    payload = dict(event)
    payload.setdefault("day", getattr(world, "day", 0))
    events.append(payload)
    world.runtime_events = events


__all__ = [
    "ExtractionLedger",
    "ExtractionSite",
    "SiteKind",
    "create_sites_for_node",
    "ensure_extraction",
]
