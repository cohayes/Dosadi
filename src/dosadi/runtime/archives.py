"""Federated archives and historical narrative v1 implementation."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event


@dataclass(slots=True)
class ArchivesConfig:
    enabled: bool = False
    update_cadence_days: int = 30
    deterministic_salt: str = "archives-v1"
    max_canon_events_per_polity: int = 64
    max_counter_narratives_per_polity: int = 8
    canon_promote_threshold: float = 0.60
    revision_threshold: float = 0.70
    narrative_effect_scale: float = 0.20


@dataclass(slots=True)
class CanonEvent:
    canon_id: str
    polity_id: str
    day: int
    source_event_id: str | None
    topic: str
    stance: dict[str, float]
    salience: float
    truth_weight: float
    status: str = "CANON"
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class NarrativeState:
    polity_id: str
    topics: dict[str, float] = field(default_factory=dict)
    stances: dict[str, float] = field(default_factory=dict)
    cohesion_effect: float = 0.0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ArchiveState:
    polity_id: str
    archive_capacity: float = 0.5
    archive_integrity: float = 0.5
    censorship_pressure: float = 0.0
    revisionism_pressure: float = 0.0
    pluralism: float = 0.5
    last_update_day: int = -1


@dataclass(slots=True)
class CounterNarrative:
    counter_id: str
    polity_id: str
    topic: str
    stance: dict[str, float]
    support: float
    risk: float
    status: str = "ACTIVE"
    notes: dict[str, object] = field(default_factory=dict)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_rng(*parts: object) -> random.Random:
    blob = "|".join(str(part) for part in parts)
    digest = sha256(blob.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big")
    return random.Random(seed)


def ensure_archives_config(world: Any) -> ArchivesConfig:
    cfg = getattr(world, "archives_cfg", None)
    if not isinstance(cfg, ArchivesConfig):
        cfg = ArchivesConfig()
        world.archives_cfg = cfg
    return cfg


def ensure_archive_ledgers(
    world: Any, *, polities: Iterable[str] | None = None
) -> tuple[
    dict[str, ArchiveState],
    dict[str, NarrativeState],
    dict[str, list[CanonEvent]],
    dict[str, list[CounterNarrative]],
]:
    archive_by_polity = getattr(world, "archive_by_polity", None)
    if not isinstance(archive_by_polity, dict):
        archive_by_polity = {}
    narrative_by_polity = getattr(world, "narrative_by_polity", None)
    if not isinstance(narrative_by_polity, dict):
        narrative_by_polity = {}
    canon_events = getattr(world, "canon_events", None)
    if not isinstance(canon_events, dict):
        canon_events = {}
    counter_narratives = getattr(world, "counter_narratives", None)
    if not isinstance(counter_narratives, dict):
        counter_narratives = {}

    if polities:
        for polity_id in polities:
            if polity_id not in archive_by_polity:
                archive_by_polity[polity_id] = ArchiveState(polity_id=polity_id)
            if polity_id not in narrative_by_polity:
                narrative_by_polity[polity_id] = NarrativeState(polity_id=polity_id)
            canon_events.setdefault(polity_id, [])
            counter_narratives.setdefault(polity_id, [])

    world.archive_by_polity = archive_by_polity
    world.narrative_by_polity = narrative_by_polity
    world.canon_events = canon_events
    world.counter_narratives = counter_narratives
    return archive_by_polity, narrative_by_polity, canon_events, counter_narratives


def _polities(world: Any) -> list[str]:
    candidates: set[str] = set()
    settlements = getattr(world, "settlements", {}) or {}
    for settlement_id, settlement in settlements.items():
        polity_id = getattr(settlement, "polity_id", None) or getattr(settlement, "id", None)
        if polity_id:
            candidates.add(str(polity_id))
        else:
            candidates.add(str(settlement_id))
    constitution = getattr(world, "constitution_by_polity", {}) or {}
    candidates.update(constitution.keys())
    leadership = getattr(world, "leadership_by_polity", {}) or {}
    candidates.update(leadership.keys())
    if not candidates:
        candidates.add("polity:central")
    return sorted(candidates)


_TOPIC_MAP = {
    "DELIVERY_LOSS": "DISASTER",
    "DELIVERY_DELAY": "DISASTER",
    "FACILITY_DOWNTIME": "REFORM",
    "WORKER_INJURY": "MARTYRDOM",
    "THEFT_CARGO": "SCHISM",
    "THEFT_DEPOT": "SCHISM",
    "SABOTAGE_PROJECT": "SCHISM",
    "STRIKE": "REFORM",
    "RIOT": "WAR",
    "SECESSION_ATTEMPT": "SCHISM",
    "COUP_PLOT": "SCHISM",
}


def _topic_for_incident(incident: Any) -> str:
    kind = getattr(incident, "kind", None)
    key = getattr(kind, "value", None) or str(kind) or ""
    return _TOPIC_MAP.get(key, "FOUNDING")


def _stance_for_topic(topic: str, *, truth_weight: float) -> dict[str, float]:
    topic = topic.upper()
    stance_key = {
        "MARTYRDOM": "martyrdom",
        "WAR": "militarism",
        "REFORM": "reformism",
        "SCHISM": "pluralism",
        "TECH": "progress",
        "DISASTER": "resilience",
    }.get(topic, "legitimacy")
    return {stance_key: _clamp01(0.4 + 0.6 * truth_weight)}


def _salience_from_incident(incident: Any) -> float:
    severity = getattr(incident, "severity", 0.0)
    try:
        severity = float(severity)
    except Exception:
        severity = 0.0
    return _clamp01(abs(severity))


def _integrity_for_polity(world: Any, polity_id: str) -> float:
    integrity = getattr(world, "integrity_by_polity", {}).get(polity_id)
    if integrity is None:
        return 0.5
    attrs = [
        "metrology",
        "ledger",
        "census",
        "telemetry",
        "judiciary",
    ]
    values = [getattr(integrity, attr, 0.5) for attr in attrs]
    return _clamp01(sum(values) / len(values))


def _candidate_incidents(world: Any, *, since_day: int, until_day: int, polity_id: str) -> list[Any]:
    ledger = getattr(world, "incidents", None)
    if ledger is None:
        return []
    incidents = []
    for incident in getattr(ledger, "incidents", {}).values():
        try:
            inc_day = int(getattr(incident, "day", -1))
        except Exception:
            continue
        if inc_day <= since_day or inc_day > until_day:
            continue
        target_id = getattr(incident, "target_id", "")
        if target_id and str(target_id) not in {polity_id, "*", "all"}:
            continue
        incidents.append(incident)
    incidents.sort(key=lambda inc: (getattr(inc, "day", 0), getattr(inc, "incident_id", "")))
    return incidents


def _canon_id(polity_id: str, source_id: str | None, day: int, salt: str) -> str:
    parts = [salt, polity_id, source_id or "", str(day)]
    digest = sha256("|".join(parts).encode("utf-8")).digest()
    return f"canon:{int.from_bytes(digest[:6], 'big')}"


def _retention_score(event: CanonEvent, *, now_day: int) -> float:
    age = max(0, now_day - int(getattr(event, "day", 0)))
    return float(event.salience) * (1.0 + 0.01 * age)


def _apply_capacity_bounds(events: list[CanonEvent], *, max_events: int, now_day: int) -> None:
    if len(events) <= max_events:
        return
    ranked = sorted(events, key=lambda evt: (_retention_score(evt, now_day=now_day), evt.canon_id))
    keep = ranked[-max_events:]
    keep_ids = {evt.canon_id for evt in keep}
    events[:] = [evt for evt in events if evt.canon_id in keep_ids]


def _promote_to_canon(
    *,
    polity_id: str,
    candidates: list[Any],
    canon_events: list[CanonEvent],
    state: ArchiveState,
    cfg: ArchivesConfig,
    now_day: int,
) -> None:
    for incident in candidates:
        salience = _salience_from_incident(incident)
        if salience * state.archive_capacity < cfg.canon_promote_threshold:
            continue
        truth_weight = _clamp01(state.archive_integrity * (1.0 - 0.3 * state.censorship_pressure))
        topic = _topic_for_incident(incident)
        canon = CanonEvent(
            canon_id=_canon_id(
                polity_id,
                getattr(incident, "incident_id", None),
                getattr(incident, "day", 0),
                cfg.deterministic_salt,
            ),
            polity_id=polity_id,
            day=int(getattr(incident, "day", 0)),
            source_event_id=getattr(incident, "incident_id", None),
            topic=topic,
            stance=_stance_for_topic(topic, truth_weight=truth_weight),
            salience=salience,
            truth_weight=truth_weight,
        )
        canon_events.append(canon)
    _apply_capacity_bounds(canon_events, max_events=cfg.max_canon_events_per_polity, now_day=now_day)


def _maybe_revisionism(
    *,
    world: Any,
    polity_id: str,
    canon_events: list[CanonEvent],
    state: ArchiveState,
    cfg: ArchivesConfig,
    day: int,
) -> None:
    rng = _stable_rng(cfg.deterministic_salt, polity_id, day)
    suppression_prob = _clamp01(state.censorship_pressure * (1.0 - state.pluralism) * (1.0 - state.archive_integrity))
    revision_prob = _clamp01(state.revisionism_pressure * (1.0 - state.archive_integrity))

    for event in sorted(canon_events, key=lambda evt: (evt.day, evt.canon_id)):
        roll = rng.random()
        if roll < suppression_prob:
            event.status = "SUPPRESSED"
            event.truth_weight = _clamp01(event.truth_weight * 0.5)
            record_event(
                world,
                {
                    "kind": "CANON_EVENT_SUPPRESSED",
                    "polity_id": polity_id,
                    "canon_id": event.canon_id,
                    "day": day,
                },
            )
            continue
        if roll < suppression_prob + revision_prob:
            event.status = "REVISED"
            event.truth_weight = _clamp01(event.truth_weight * 0.7)
            for key in list(event.stance.keys()):
                event.stance[key] = _clamp01(event.stance[key] * (1.0 - cfg.narrative_effect_scale))
            record_event(
                world,
                {
                    "kind": "CANON_EVENT_REVISED",
                    "polity_id": polity_id,
                    "canon_id": event.canon_id,
                    "day": day,
                },
            )


def _maybe_counter_narratives(
    *,
    world: Any,
    polity_id: str,
    canon_events: list[CanonEvent],
    counters: list[CounterNarrative],
    state: ArchiveState,
    cfg: ArchivesConfig,
    day: int,
) -> None:
    suppression_pressure = _clamp01(state.censorship_pressure * (1.0 - state.pluralism))
    if suppression_pressure <= 0.3 or state.pluralism <= 0.05:
        return
    if len(counters) >= cfg.max_counter_narratives_per_polity:
        return

    rng = _stable_rng(cfg.deterministic_salt, polity_id, "counter", day)
    topic = "SCHISM"
    if canon_events:
        topic = max(canon_events, key=lambda evt: evt.salience).topic
    support = _clamp01(0.2 + suppression_pressure + 0.2 * rng.random())
    risk = _clamp01((1.0 - state.archive_integrity) * (0.5 + 0.5 * rng.random()))
    counter = CounterNarrative(
        counter_id=f"counter:{polity_id}:{len(counters)+1}",
        polity_id=polity_id,
        topic=topic,
        stance=_stance_for_topic(topic, truth_weight=1.0 - state.archive_integrity),
        support=support,
        risk=risk,
    )
    counters.append(counter)
    if len(counters) > cfg.max_counter_narratives_per_polity:
        counters[:] = sorted(counters, key=lambda cn: (cn.support, cn.counter_id))[-cfg.max_counter_narratives_per_polity :]
    record_event(
        world,
        {
            "kind": "COUNTER_NARRATIVE_FORMED",
            "polity_id": polity_id,
            "counter_id": counter.counter_id,
            "day": day,
        },
    )


def _update_narrative(
    *, polity_id: str, canon_events: list[CanonEvent], narrative: NarrativeState, state: ArchiveState
) -> None:
    relevant = [evt for evt in canon_events if evt.status != "SUPPRESSED"]
    total = sum(evt.salience for evt in relevant) or 1.0
    topics: dict[str, float] = {}
    stances: dict[str, float] = {}
    truth_weights = [evt.truth_weight for evt in relevant] or [0.5]
    for evt in relevant:
        topics[evt.topic] = topics.get(evt.topic, 0.0) + evt.salience / total
        for key, value in evt.stance.items():
            stances[key] = stances.get(key, 0.0) + value * (evt.salience / total)

    narrative.topics = {k: _clamp01(v) for k, v in sorted(topics.items())}
    narrative.stances = {k: _clamp01(v) for k, v in sorted(stances.items())}
    coherence = 1.0 - (math.sqrt(len(narrative.topics)) - 1) * 0.1
    coherence = max(0.0, coherence)
    truth_avg = sum(truth_weights) / len(truth_weights)
    fragility = (1.0 - state.pluralism) * (1.0 - truth_avg)
    narrative.cohesion_effect = _clamp01(truth_avg * coherence - fragility * 0.5)
    narrative.last_update_day = getattr(narrative, "last_update_day", -1)


def archives_signature(world: Any) -> str:
    payload = {
        "canon": {
            polity: [
                {
                    "id": evt.canon_id,
                    "topic": evt.topic,
                    "salience": round(evt.salience, 4),
                    "truth": round(evt.truth_weight, 4),
                    "status": evt.status,
                }
                for evt in sorted(events, key=lambda e: (e.day, e.canon_id))
            ]
            for polity, events in sorted((getattr(world, "canon_events", {}) or {}).items())
        },
        "narrative": {
            polity: {
                "topics": sorted(state.topics.items()),
                "stances": sorted(state.stances.items()),
                "cohesion": round(state.cohesion_effect, 4),
            }
            for polity, state in sorted((getattr(world, "narrative_by_polity", {}) or {}).items())
        },
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def archives_seed_payload(world: Any) -> dict[str, object] | None:
    canon_events = getattr(world, "canon_events", None)
    archive_by_polity = getattr(world, "archive_by_polity", None)
    narrative_by_polity = getattr(world, "narrative_by_polity", None)
    counters = getattr(world, "counter_narratives", None)
    if not isinstance(canon_events, dict):
        return None

    payload: dict[str, object] = {"schema": "archives_v1", "polities": []}
    polities = sorted(set(canon_events.keys()) | set((archive_by_polity or {}).keys()) | set((narrative_by_polity or {}).keys()))
    for polity_id in polities:
        entry: dict[str, object] = {"polity_id": polity_id}
        if isinstance(archive_by_polity, Mapping) and polity_id in archive_by_polity:
            state = archive_by_polity[polity_id]
            entry["archive_state"] = {
                "capacity": getattr(state, "archive_capacity", 0.0),
                "integrity": getattr(state, "archive_integrity", 0.0),
                "censorship": getattr(state, "censorship_pressure", 0.0),
                "revisionism": getattr(state, "revisionism_pressure", 0.0),
                "pluralism": getattr(state, "pluralism", 0.0),
                "last_update_day": getattr(state, "last_update_day", -1),
            }
        if polity_id in canon_events:
            entry["canon"] = [
                {
                    "canon_id": evt.canon_id,
                    "day": evt.day,
                    "topic": evt.topic,
                    "salience": evt.salience,
                    "truth_weight": evt.truth_weight,
                    "status": evt.status,
                    "source_event_id": evt.source_event_id,
                }
                for evt in sorted(canon_events.get(polity_id, []), key=lambda e: (e.day, e.canon_id))
            ]
        if isinstance(narrative_by_polity, Mapping) and polity_id in narrative_by_polity:
            state = narrative_by_polity[polity_id]
            entry["narrative"] = {
                "topics": dict(state.topics),
                "stances": dict(state.stances),
                "cohesion_effect": state.cohesion_effect,
                "last_update_day": state.last_update_day,
            }
        if isinstance(counters, Mapping) and polity_id in counters:
            entry["counter_narratives"] = [
                {
                    "counter_id": counter.counter_id,
                    "topic": counter.topic,
                    "stance": dict(counter.stance),
                    "support": counter.support,
                    "risk": counter.risk,
                    "status": counter.status,
                }
                for counter in sorted(counters.get(polity_id, []), key=lambda c: c.counter_id)
            ]
        payload["polities"].append(entry)
    return payload


def save_archives_seed(world: Any, path) -> None:
    payload = archives_seed_payload(world)
    if payload is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)


def run_archives_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_archives_config(world)
    if not cfg.enabled:
        return

    polities = _polities(world)
    archive_by_polity, narrative_by_polity, canon_events_by_polity, counters_by_polity = ensure_archive_ledgers(
        world, polities=polities
    )
    metrics = ensure_metrics(world)

    for polity_id in polities:
        state = archive_by_polity.get(polity_id) or ArchiveState(polity_id=polity_id)
        narrative = narrative_by_polity.get(polity_id) or NarrativeState(polity_id=polity_id)

        if state.last_update_day >= day:
            continue
        if state.last_update_day >= 0 and (day - state.last_update_day) < cfg.update_cadence_days:
            continue

        state.archive_integrity = _integrity_for_polity(world, polity_id)
        incidents = _candidate_incidents(world, since_day=state.last_update_day, until_day=day, polity_id=polity_id)
        canon_events = canon_events_by_polity.get(polity_id, [])

        _promote_to_canon(
            polity_id=polity_id,
            candidates=incidents,
            canon_events=canon_events,
            state=state,
            cfg=cfg,
            now_day=day,
        )
        _maybe_revisionism(
            world=world,
            polity_id=polity_id,
            canon_events=canon_events,
            state=state,
            cfg=cfg,
            day=day,
        )
        _maybe_counter_narratives(
            world=world,
            polity_id=polity_id,
            canon_events=canon_events,
            counters=counters_by_polity.get(polity_id, []),
            state=state,
            cfg=cfg,
            day=day,
        )
        _update_narrative(polity_id=polity_id, canon_events=canon_events, narrative=narrative, state=state)

        state.last_update_day = day
        narrative.last_update_day = day
        archive_by_polity[polity_id] = state
        narrative_by_polity[polity_id] = narrative
        canon_events_by_polity[polity_id] = canon_events

    total_canon = sum(len(events) for events in canon_events_by_polity.values())
    suppressed = sum(1 for events in canon_events_by_polity.values() for evt in events if evt.status == "SUPPRESSED")
    revised = sum(1 for events in canon_events_by_polity.values() for evt in events if evt.status == "REVISED")
    truth_weights = [evt.truth_weight for events in canon_events_by_polity.values() for evt in events]
    avg_truth = sum(truth_weights) / len(truth_weights) if truth_weights else 0.0
    metrics.set_gauge("archives/canon_events_total", total_canon)
    metrics.set_gauge("archives/suppressed_events", suppressed)
    metrics.set_gauge("archives/revised_events", revised)
    metrics.set_gauge("archives/avg_truth_weight", avg_truth)
    metrics.set_gauge("archives/counter_narratives", sum(len(v) for v in counters_by_polity.values()))


__all__ = [
    "ArchiveState",
    "ArchivesConfig",
    "CanonEvent",
    "CounterNarrative",
    "NarrativeState",
    "archives_signature",
    "archives_seed_payload",
    "ensure_archive_ledgers",
    "ensure_archives_config",
    "save_archives_seed",
    "run_archives_for_day",
]
