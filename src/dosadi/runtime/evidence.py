from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Any, Iterable, Mapping


def _clamp01(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


@dataclass(slots=True)
class EvidenceConfig:
    enabled: bool = True
    update_cadence_days: int = 1
    max_payload_items: int = 16
    deterministic_salt: str = "evidence-v1"


@dataclass(slots=True)
class EvidenceItem:
    key: str
    polity_id: str
    day: int
    score: float
    confidence: float
    payload: dict[str, object]
    sources: list[str]
    reason_codes: list[str] = field(default_factory=list)

    def signature(self) -> str:
        payload = {
            "key": self.key,
            "polity_id": self.polity_id,
            "day": int(self.day),
            "score": round(self.score, 6),
            "confidence": round(self.confidence, 6),
            "payload": {k: self.payload[k] for k in sorted(self.payload)},
            "sources": list(self.sources),
            "reason_codes": sorted(self.reason_codes),
        }
        blob = str(payload).encode("utf-8")
        return sha256(blob).hexdigest()


@dataclass(slots=True)
class EvidenceBuffer:
    polity_id: str
    max_items: int = 64
    items: dict[str, EvidenceItem] = field(default_factory=dict)
    topk_index: list[str] = field(default_factory=list)
    last_update_day: int = -1

    def _bounded_payload(self, payload: Mapping[str, object], *, max_items: int) -> dict[str, object]:
        bounded: dict[str, object] = {}
        for key, value in sorted(payload.items(), key=lambda kv: kv[0]):
            if isinstance(value, list):
                bounded[key] = list(value)[:max_items]
            elif isinstance(value, tuple):
                bounded[key] = list(value)[:max_items]
            else:
                bounded[key] = value
        return bounded

    def upsert(self, item: EvidenceItem, *, max_payload_items: int = 16) -> None:
        bounded_payload = self._bounded_payload(item.payload, max_items=max_payload_items)
        normalized = replace(item, payload=bounded_payload)
        self.items[item.key] = normalized
        self._refresh_index()
        self._enforce_cap()

    def _refresh_index(self) -> None:
        ranked = sorted(
            self.items.values(), key=lambda itm: (-round(itm.score, 6), itm.key, itm.polity_id)
        )
        self.topk_index = [itm.key for itm in ranked]

    def _enforce_cap(self) -> None:
        if len(self.items) <= self.max_items:
            return
        ranked = sorted(
            self.items.values(), key=lambda itm: (round(itm.score, 6), itm.key, itm.polity_id)
        )
        for victim in ranked[: max(0, len(self.items) - self.max_items)]:
            self.items.pop(victim.key, None)
        self._refresh_index()

    def signature(self) -> str:
        payload = {
            key: item.signature()
            for key, item in sorted(self.items.items(), key=lambda kv: kv[0])
        }
        blob = str(payload).encode("utf-8")
        return sha256(blob).hexdigest()


EvidenceCatalogEntry = dict[str, object]


EVIDENCE_CATALOG: dict[str, EvidenceCatalogEntry] = {
    "evidence.corridor_risk.topk": {
        "payload": "list[{corridor_id, risk, failures_7d, escort_policy}]",
        "cadence_days": 1,
        "sources": ["corridor_risk", "logistics.kpis"],
    },
    "evidence.delivery_failures.rate_7d": {
        "payload": "{count, rate}",
        "cadence_days": 1,
        "sources": ["incidents", "logistics.kpis"],
    },
    "evidence.delivery_delays.p95_7d": {
        "payload": "{p95_delay_days}",
        "cadence_days": 1,
        "sources": ["incidents"],
    },
    "evidence.depot_stockout.topk": {
        "payload": "list[{depot_id, stockout_items, days_to_empty}]",
        "cadence_days": 1,
        "sources": ["stockpile_policy", "inventories"],
    },
    "evidence.route_utilization.topk": {
        "payload": "list[{route_id, utilization}]",
        "cadence_days": 7,
        "sources": ["telemetry.routes"],
    },
    "evidence.incidents.rate_7d": {
        "payload": "{count, rate}",
        "cadence_days": 1,
        "sources": ["incidents"],
    },
    "evidence.raids.rate_30d": {
        "payload": "{count, rate}",
        "cadence_days": 5,
        "sources": ["war"],
    },
    "evidence.predation.pressure_30d": {
        "payload": "{pressure}",
        "cadence_days": 5,
        "sources": ["environment"],
    },
    "evidence.queue_unfairness.topk": {
        "payload": "list[{facility_id, unfairness_score, complaints}]",
        "cadence_days": 1,
        "sources": ["queue.telemetry"],
    },
    "evidence.grievance.index_7d": {
        "payload": "{index}",
        "cadence_days": 3,
        "sources": ["episodes"],
    },
    "evidence.protocol_violations.rate_7d": {
        "payload": "{count, rate}",
        "cadence_days": 1,
        "sources": ["enforcement"],
    },
    "evidence.enforcement.load_7d": {
        "payload": "{actions, load_index}",
        "cadence_days": 1,
        "sources": ["enforcement"],
    },
    "evidence.audit_discrepancies.topk": {
        "payload": "list[{actor, discrepancy}]",
        "cadence_days": 7,
        "sources": ["audits"],
    },
    "evidence.comms_outages.rate_7d": {
        "payload": "{count, rate}",
        "cadence_days": 1,
        "sources": ["comms"],
    },
    "evidence.shortages.topk": {
        "payload": "list[{ward_or_polity, resource, severity}]",
        "cadence_days": 1,
        "sources": ["kpis", "stockpiles"],
    },
    "evidence.ration_pressure.index_7d": {
        "payload": "{pressure}",
        "cadence_days": 1,
        "sources": ["kpis"],
    },
    "evidence.diagnostics.missing_source": {
        "payload": "{missing, impact}",
        "cadence_days": 1,
        "sources": ["diagnostics"],
    },
}


def ensure_evidence_config(world: Any) -> EvidenceConfig:
    cfg = getattr(world, "evidence_cfg", None)
    if not isinstance(cfg, EvidenceConfig):
        cfg = EvidenceConfig()
        world.evidence_cfg = cfg
    return cfg


def ensure_evidence_buffer(world: Any, polity_id: str) -> EvidenceBuffer:
    buffers = getattr(world, "evidence_by_polity", None)
    if not isinstance(buffers, dict):
        buffers = {}
        world.evidence_by_polity = buffers
    buffer = buffers.get(polity_id)
    if not isinstance(buffer, EvidenceBuffer):
        buffer = EvidenceBuffer(polity_id=polity_id)
        buffers[polity_id] = buffer
    return buffer


def get_evidence(buffer: EvidenceBuffer, key: str) -> EvidenceItem | None:
    return buffer.items.get(key)


def get_top_evidence(buffer: EvidenceBuffer, prefix: str, k: int = 10) -> list[EvidenceItem]:
    matched = [
        buffer.items[key]
        for key in buffer.topk_index
        if key.startswith(prefix) and key in buffer.items
    ]
    return matched[: max(0, int(k))]


def evidence_score(buffer: EvidenceBuffer, key: str) -> float:
    evidence = get_evidence(buffer, key)
    return evidence.score if evidence is not None else 0.0


def active_polities(world: Any) -> list[str]:
    polities: set[str] = set()
    for mapping_name in ("constitution_by_polity", "demographics_by_polity", "integrity_by_polity"):
        mapping = getattr(world, mapping_name, None)
        if isinstance(mapping, Mapping):
            polities.update(str(pid) for pid in mapping.keys())
    if not polities:
        polities.add(getattr(world, "default_polity_id", "polity:default"))
    return sorted(polities)


def apply_to_buffers(
    world: Any,
    items: Iterable[EvidenceItem],
    *,
    max_payload_items: int,
) -> None:
    for item in items:
        buffer = ensure_evidence_buffer(world, item.polity_id)
        buffer.upsert(item, max_payload_items=max_payload_items)

