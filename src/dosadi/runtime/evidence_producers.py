from __future__ import annotations

from typing import Iterable, List, Mapping, Sequence

from dosadi.runtime.evidence import (
    EVIDENCE_CATALOG,
    EvidenceConfig,
    EvidenceItem,
    active_polities,
    apply_to_buffers,
    ensure_evidence_buffer,
    ensure_evidence_config,
)
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.runtime.corridor_risk import CorridorRiskLedger
from dosadi.world.incidents import IncidentLedger
from dosadi.runtime.stockpile_policy import DepotPolicyLedger, MaterialThreshold
from dosadi.world.materials import InventoryRegistry
from dosadi.runtime.queues import QueueState


def _clamp01(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


def _scores_from_thresholds(
    inventory: Mapping[str, float], thresholds: Mapping[str, MaterialThreshold]
) -> list[tuple[str, float]]:
    entries: list[tuple[str, float]] = []
    for mat_name, threshold in sorted(thresholds.items()):
        have = float(inventory.get(mat_name, 0.0))
        deficit = max(0.0, threshold.min_level - have)
        if deficit <= 0:
            continue
        severity = deficit / max(1.0, float(threshold.min_level))
        entries.append((mat_name, _clamp01(severity)))
    return entries


def _diagnostic(polity_id: str, day: int, missing: str, impact: str) -> EvidenceItem:
    return EvidenceItem(
        key="evidence.diagnostics.missing_source",
        polity_id=polity_id,
        day=day,
        score=0.1,
        confidence=0.2,
        payload={"missing": missing, "impact": impact},
        sources=[missing],
        reason_codes=["diagnostic"],
    )


def _corridor_risk(world, polity_id: str, day: int) -> list[EvidenceItem]:
    ledger = getattr(world, "risk_ledger", None)
    if not isinstance(ledger, CorridorRiskLedger):
        placeholder = EvidenceItem(
            key="evidence.corridor_risk.topk",
            polity_id=polity_id,
            day=day,
            score=0.0,
            confidence=0.2,
            payload={"items": []},
            sources=["corridor_risk"],
            reason_codes=["fallback"],
        )
        return [placeholder, _diagnostic(polity_id, day, "corridor_risk", "no corridor risk ledger")]

    items: list[dict[str, object]] = []
    for edge_key in getattr(ledger, "hot_edges", [])[:50]:
        rec = ledger.edges.get(edge_key)
        if rec is None:
            continue
        payload = {
            "corridor_id": edge_key,
            "risk": _clamp01(rec.risk),
            "failures_7d": round(rec.incidents_lookback, 3),
            "escort_policy": getattr(rec, "notes", {}).get("escort_policy"),
        }
        items.append(payload)

    if not items:
        placeholder = EvidenceItem(
            key="evidence.corridor_risk.topk",
            polity_id=polity_id,
            day=day,
            score=0.0,
            confidence=0.2,
            payload={"items": []},
            sources=["corridor_risk"],
            reason_codes=["fallback"],
        )
        return [placeholder, _diagnostic(polity_id, day, "corridor_risk", "no hot edges tracked")]

    return [
        EvidenceItem(
            key="evidence.corridor_risk.topk",
            polity_id=polity_id,
            day=day,
            score=_clamp01(max(payload.get("risk", 0.0) for payload in items)),
            confidence=0.9,
            payload={"items": items},
            sources=["corridor_risk"],
            reason_codes=[],
        )
    ]


def _stockout(world, polity_id: str, day: int) -> list[EvidenceItem]:
    ledger = getattr(world, "stock_policies", None)
    inventories = getattr(world, "inventories", None)
    if not isinstance(ledger, DepotPolicyLedger) or not isinstance(inventories, InventoryRegistry):
        return [_diagnostic(polity_id, day, "stockpile_policy", "no depot thresholds")]

    entries: list[dict[str, object]] = []
    for depot_id, profile in sorted(ledger.profiles.items()):
        inv = inventories.inv(f"facility:{depot_id}")
        deficits = _scores_from_thresholds(inv, profile.thresholds)
        if not deficits:
            continue
        top_deficits = sorted(deficits, key=lambda itm: (-round(itm[1], 6), itm[0]))
        entries.append(
            {
                "depot_id": depot_id,
                "stockout_items": [mat for mat, _ in top_deficits],
                "days_to_empty": None,
                "severity": float(top_deficits[0][1]),
            }
        )

    if not entries:
        return []

    entries = sorted(entries, key=lambda item: (-round(item["severity"], 6), item["depot_id"]))
    score = _clamp01(entries[0]["severity"] if entries else 0.0)
    return [
        EvidenceItem(
            key="evidence.depot_stockout.topk",
            polity_id=polity_id,
            day=day,
            score=score,
            confidence=0.75,
            payload={"items": entries},
            sources=["stockpile_policy", "inventories"],
            reason_codes=[],
        )
    ]


def _shortages(world, polity_id: str, day: int) -> list[EvidenceItem]:
    ledger = getattr(world, "stock_policies", None)
    inventories = getattr(world, "inventories", None)
    if not isinstance(ledger, DepotPolicyLedger) or not isinstance(inventories, InventoryRegistry):
        return [_diagnostic(polity_id, day, "stockpile_policy", "no shortage telemetry")]

    aggregates: dict[str, float] = {}
    for depot_id, profile in sorted(ledger.profiles.items()):
        inv = inventories.inv(f"facility:{depot_id}")
        for mat_name, severity in _scores_from_thresholds(inv, profile.thresholds):
            aggregates[mat_name] = max(aggregates.get(mat_name, 0.0), severity)

    if not aggregates:
        return []

    entries = [
        {"ward_or_polity": polity_id, "resource": mat, "severity": round(sev, 3)}
        for mat, sev in sorted(aggregates.items(), key=lambda item: (-round(item[1], 6), item[0]))
    ]
    score = _clamp01(entries[0]["severity"] if entries else 0.0)
    return [
        EvidenceItem(
            key="evidence.shortages.topk",
            polity_id=polity_id,
            day=day,
            score=score,
            confidence=0.7,
            payload={"items": entries},
            sources=["stockpile_policy", "inventories"],
            reason_codes=[],
        )
    ]


def _queue_unfairness(world, polity_id: str, day: int) -> list[EvidenceItem]:
    queues = getattr(world, "queues", None)
    if not isinstance(queues, Mapping) or not queues:
        return [_diagnostic(polity_id, day, "queue.telemetry", "no active queues")]

    entries: list[dict[str, object]] = []
    for queue_id, queue in sorted(queues.items()):
        if not isinstance(queue, QueueState):
            continue
        processed = getattr(getattr(queue, "stats", None), "total_processed", 0)
        denied = getattr(getattr(queue, "stats", None), "total_denied", 0)
        unfairness = denied / max(1.0, float(processed + denied))
        waiting_bias = len(getattr(queue, "agents_waiting", [])) / max(
            1.0, float(getattr(queue, "processing_rate", 1))
        )
        score = _clamp01(0.6 * unfairness + 0.4 * _clamp01(waiting_bias / 10.0))
        if score <= 0:
            continue
        entries.append(
            {
                "facility_id": getattr(queue, "associated_facility", queue_id),
                "unfairness_score": round(score, 3),
                "complaints": int(denied),
            }
        )

    if not entries:
        return []

    entries = sorted(entries, key=lambda item: (-round(item["unfairness_score"], 6), str(item["facility_id"])))
    score = float(entries[0]["unfairness_score"])
    return [
        EvidenceItem(
            key="evidence.queue_unfairness.topk",
            polity_id=polity_id,
            day=day,
            score=score,
            confidence=0.65,
            payload={"items": entries},
            sources=["queue.telemetry"],
            reason_codes=[],
        )
    ]


def _incident_rate(world, polity_id: str, day: int) -> list[EvidenceItem]:
    ledger = getattr(world, "incidents", None)
    if not isinstance(ledger, IncidentLedger):
        return [_diagnostic(polity_id, day, "incidents", "no incident log")]

    window_start = max(0, day - 6)
    incidents = [
        inc
        for inc in ledger.incidents.values()
        if getattr(inc, "day", getattr(inc, "created_day", 0)) >= window_start
    ]
    count = len(incidents)
    rate = count / 7.0
    score = _clamp01(rate)
    return [
        EvidenceItem(
            key="evidence.incidents.rate_7d",
            polity_id=polity_id,
            day=day,
            score=score,
            confidence=0.9,
            payload={"count": count, "rate": rate},
            sources=["incidents"],
            reason_codes=[],
        )
    ]


def _protocol_violations(world, polity_id: str, day: int) -> list[EvidenceItem]:
    metrics = ensure_metrics(world)
    count = int(metrics.counters.get("protocols.violations", 0))
    if count <= 0:
        placeholder = EvidenceItem(
            key="evidence.protocol_violations.rate_7d",
            polity_id=polity_id,
            day=day,
            score=0.0,
            confidence=0.2,
            payload={"count": 0, "rate": 0.0},
            sources=["enforcement"],
            reason_codes=["fallback"],
        )
        return [placeholder, _diagnostic(polity_id, day, "protocols.violations", "no violation telemetry")]
    rate = count / 7.0
    return [
        EvidenceItem(
            key="evidence.protocol_violations.rate_7d",
            polity_id=polity_id,
            day=day,
            score=_clamp01(rate),
            confidence=0.5,
            payload={"count": count, "rate": rate},
            sources=["enforcement"],
            reason_codes=[],
        )
    ]


def _enforcement_load(world, polity_id: str, day: int) -> list[EvidenceItem]:
    metrics = ensure_metrics(world)
    patrols = float(metrics.gauges.get("enforcement", {}).get("patrols_total", 0.0)) if hasattr(metrics, "gauges") else 0.0
    checkpoints = float(metrics.gauges.get("enforcement", {}).get("checkpoints_total", 0.0)) if hasattr(metrics, "gauges") else 0.0
    actions = patrols + checkpoints
    if actions <= 0:
        placeholder = EvidenceItem(
            key="evidence.enforcement.load_7d",
            polity_id=polity_id,
            day=day,
            score=0.0,
            confidence=0.25,
            payload={"actions": 0.0, "load_index": 0.0},
            sources=["enforcement"],
            reason_codes=["fallback"],
        )
        return [placeholder, _diagnostic(polity_id, day, "enforcement.load", "no enforcement load telemetry")]
    load_index = _clamp01(actions / 50.0)
    return [
        EvidenceItem(
            key="evidence.enforcement.load_7d",
            polity_id=polity_id,
            day=day,
            score=load_index,
            confidence=0.6,
            payload={"actions": actions, "load_index": load_index},
            sources=["enforcement"],
            reason_codes=[],
        )
    ]


def _delivery_failure_proxy(world, polity_id: str, day: int) -> list[EvidenceItem]:
    metrics = ensure_metrics(world)
    failed = float(metrics.counters.get("stockpile.deliveries_failed", 0.0))
    completed = float(metrics.counters.get("stockpile.deliveries_completed", 0.0))
    total = completed + failed
    rate = failed / max(1.0, total)
    if total <= 0:
        return [
            EvidenceItem(
                key="evidence.delivery_failures.rate_7d",
                polity_id=polity_id,
                day=day,
                score=0.0,
                confidence=0.25,
                payload={"count": 0.0, "rate": 0.0},
                sources=["logistics.kpis"],
                reason_codes=["fallback"],
            )
        ]
    return [
        EvidenceItem(
            key="evidence.delivery_failures.rate_7d",
            polity_id=polity_id,
            day=day,
            score=_clamp01(rate),
            confidence=0.55,
            payload={"count": failed, "rate": rate},
            sources=["logistics.kpis"],
            reason_codes=[],
        )
    ]


def run_evidence_update(world, *, day: int | None = None) -> None:
    cfg: EvidenceConfig = ensure_evidence_config(world)
    if not cfg.enabled:
        return

    current_day = int(day if day is not None else getattr(world, "day", 0))
    polity_ids = active_polities(world)
    for polity_id in polity_ids:
        buffer = ensure_evidence_buffer(world, polity_id)
        if buffer.last_update_day == current_day:
            continue
        buffer.last_update_day = current_day

        batch: list[EvidenceItem] = []
        batch.extend(_corridor_risk(world, polity_id, current_day))
        batch.extend(_stockout(world, polity_id, current_day))
        batch.extend(_shortages(world, polity_id, current_day))
        batch.extend(_queue_unfairness(world, polity_id, current_day))
        batch.extend(_incident_rate(world, polity_id, current_day))
        batch.extend(_protocol_violations(world, polity_id, current_day))
        batch.extend(_enforcement_load(world, polity_id, current_day))
        batch.extend(_delivery_failure_proxy(world, polity_id, current_day))

        apply_to_buffers(world, batch, max_payload_items=cfg.max_payload_items)


def dangerous_edges_from_evidence(
    world, polity_id: str, *, min_score: float = 0.35, limit: int = 5
) -> list[str]:
    buffer = ensure_evidence_buffer(world, polity_id)
    item = buffer.items.get("evidence.corridor_risk.topk")
    if item is None:
        return []
    payload = item.payload or {}
    items: Sequence[Mapping[str, object]] = payload.get("items", []) if isinstance(payload, Mapping) else []
    ranked = [
        entry
        for entry in items
        if float(entry.get("risk", 0.0)) >= min_score and "corridor_id" in entry
    ]
    ranked = sorted(
        ranked,
        key=lambda entry: (
            -round(float(entry.get("risk", 0.0)), 6),
            str(entry.get("corridor_id", "")),
        ),
    )
    return [str(entry.get("corridor_id")) for entry in ranked[: max(0, int(limit))]]


__all__ = [
    "run_evidence_update",
    "dangerous_edges_from_evidence",
]

