from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from dosadi.runtime.telemetry import EventRing, Metrics, ensure_event_ring, ensure_metrics
from dosadi.world.construction import ProjectStatus
from dosadi.world.facilities import FacilityKind, ensure_facility_ledger
from dosadi.world.logistics import DeliveryStatus, ensure_logistics
from dosadi.world.scout_missions import ScoutMissionLedger


def _section(title: str) -> str:
    return f"\n== {title} =="


def _fmt_row(label: str, value: str) -> str:
    return f"{label:<28} {value}"


def _topk_lines(bucket: Mapping[str, Any] | None, *, prefix: str) -> list[str]:
    lines: list[str] = []
    entries = getattr(bucket, "entries", None)
    if not entries:
        return [f"{prefix} (none)"]
    for entry in entries:
        payload = getattr(entry, "payload", {}) or {}
        detail = ", ".join(
            f"{k}={payload[k]}" for k in sorted(payload) if payload[k] is not None
        )
        lines.append(f"{prefix} {entry.key} | score={entry.score:.2f} | {detail}".rstrip(" | "))
    return lines


def _blocked_projects(telemetry: Metrics) -> list[str]:
    bucket = telemetry.topk.get("projects.blocked")
    return _topk_lines(bucket, prefix="•")


def _shortages(telemetry: Metrics) -> list[str]:
    bucket = telemetry.topk.get("stockpile.shortages")
    return _topk_lines(bucket, prefix="•")


def _extraction_sites(telemetry: Metrics) -> list[str]:
    bucket = telemetry.topk.get("extraction.top_sites")
    return _topk_lines(bucket, prefix="•")


def _ledger_panel(telemetry: Metrics) -> list[str]:
    ledger_metrics = telemetry.gauges.get("ledger", {}) if hasattr(telemetry, "gauges") else {}
    if not isinstance(ledger_metrics, Mapping):
        return ["ledger telemetry unavailable"]
    balances = ledger_metrics.get("balances", {}) if isinstance(ledger_metrics, Mapping) else {}
    lines = [
        _fmt_row("treasury balance", f"{float(balances.get('state_treasury', 0.0)):.2f}"),
        _fmt_row("avg ward balance", f"{float(balances.get('avg_ward', 0.0)):.2f}"),
        _fmt_row("avg faction balance", f"{float(balances.get('avg_faction', 0.0)):.2f}"),
        _fmt_row("tx count", str(ledger_metrics.get("tx_count", 0))),
    ]
    lines.extend(_topk_lines(telemetry.topk.get("ledger.richest_accounts"), prefix="richest:"))
    lines.extend(_topk_lines(telemetry.topk.get("ledger.lowest_accounts"), prefix="lowest:"))
    return lines


def _recent_events(ring: EventRing, *, limit: int = 10) -> list[str]:
    if ring.capacity <= 0 or not ring.events:
        return ["(event ring disabled)"]
    lines = []
    for event in ring.tail(limit):
        day = event.get("day", 0)
        kind = event.get("type") or event.get("kind")
        payload = event.get("payload", {}) if isinstance(event, Mapping) else {}
        if isinstance(payload, Mapping):
            detail = ", ".join(f"{k}={payload[k]}" for k in sorted(payload))
        else:
            detail = ""
        lines.append(f"day {day}: {kind} {detail}".rstrip())
    return lines


def _logistics_health(world, telemetry: Metrics) -> list[str]:
    logistics = ensure_logistics(world)
    active_deliveries = [
        logistics.deliveries[delivery_id]
        for delivery_id in sorted(logistics.active_ids)
        if delivery_id in logistics.deliveries
    ]
    active = [
        d
        for d in active_deliveries
        if d.status not in {DeliveryStatus.DELIVERED, DeliveryStatus.CANCELED, DeliveryStatus.FAILED}
    ]
    requested = int(telemetry.counters.get("stockpile.deliveries_requested", 0))
    completed = int(telemetry.counters.get("stockpile.deliveries_completed", 0))
    lines = [
        _fmt_row("deliveries requested", f"{requested}"),
        _fmt_row("deliveries completed", f"{completed}"),
        _fmt_row("active deliveries", f"{len(active)}"),
    ]
    return lines


def _wear_panel(telemetry: Metrics) -> list[str]:
    warn = telemetry.gauges.get("suits.percent_warn", 0.0)
    repair = telemetry.gauges.get("suits.percent_repair", 0.0)
    critical = telemetry.gauges.get("suits.percent_critical", 0.0)
    started = int(telemetry.counters.get("suits.repairs_started", 0))
    done = int(telemetry.counters.get("suits.repairs_done", 0))
    return [
        _fmt_row("warn threshold", f"{warn:.1f}%"),
        _fmt_row("repair threshold", f"{repair:.1f}%"),
        _fmt_row("critical threshold", f"{critical:.1f}%"),
        _fmt_row("repairs started today", str(started)),
        _fmt_row("repairs completed", str(done)),
    ]


def _planner_panel(world, telemetry: Metrics) -> list[str]:
    last = telemetry.gauges.get("planner_v2.last_action_json")
    lines = []
    if isinstance(last, Iterable):
        for action in last:
            if not isinstance(action, Mapping):
                continue
            parts = [action.get("kind", ""), f"node={action.get('node', '')}"]
            if action.get("facility"):
                parts.append(f"facility={action['facility']}")
            parts.append(f"score={action.get('score', 0)}")
            lines.append(" • " + ", ".join(parts))
    if not lines:
        lines.append("no recent actions")

    state = getattr(world, "plan2_state", None)
    cooldown = getattr(state, "last_action_day", None)
    if cooldown is not None:
        lines.append(_fmt_row("last action day", str(cooldown)))
    return lines


@dataclass(slots=True)
class DebugCockpitCLI:
    width: int = 100

    def render(self, world, *, ward_id: str | None = None) -> str:
        telemetry = ensure_metrics(world)
        ring = ensure_event_ring(world)
        lines: list[str] = []

        lines.append(_section("Executive Summary"))
        lines.extend(self._exec_summary(world, telemetry))

        lines.append(_section("Where are we stuck?"))
        lines.extend(_blocked_projects(telemetry))

        lines.append(_section("What is scarce?"))
        lines.extend(_shortages(telemetry))

        lines.append(_section("What is producing value?"))
        lines.extend(_extraction_sites(telemetry))

        lines.append(_section("Ledger"))
        lines.extend(_ledger_panel(telemetry))

        lines.append(_section("Logistics health"))
        lines.extend(_logistics_health(world, telemetry))

        lines.append(_section("Wear & attrition"))
        lines.extend(_wear_panel(telemetry))

        lines.append(_section("Planner motives"))
        lines.extend(_planner_panel(world, telemetry))

        if ring.capacity > 0:
            lines.append(_section("Recent key events"))
            lines.extend(_recent_events(ring))

        return "\n".join(lines).strip() + "\n"

    def _exec_summary(self, world, telemetry: Metrics) -> list[str]:
        phase_state = getattr(world, "phase_state", None)
        phase_name = getattr(getattr(phase_state, "phase", None), "name", "UNKNOWN")
        agents_total = len(getattr(world, "agents", {}))
        facilities = ensure_facility_ledger(world)
        depots = len(facilities.list_by_kind(FacilityKind.DEPOT))
        workshops = len(facilities.list_by_kind(FacilityKind.WORKSHOP))
        projects = getattr(world, "projects", None)
        active_projects = 0
        if projects is not None:
            active_projects = sum(
                1
                for project in projects.projects.values()
                if project.status not in {ProjectStatus.COMPLETE, ProjectStatus.CANCELED}
            )
        logistics = ensure_logistics(world)
        active_deliveries = [
            d
            for d in logistics.deliveries.values()
            if d.status not in {DeliveryStatus.DELIVERED, DeliveryStatus.CANCELED, DeliveryStatus.FAILED}
        ]
        scouts = getattr(world, "scout_missions", ScoutMissionLedger())
        active_scouts = len(getattr(scouts, "missions", {})) if hasattr(scouts, "missions") else 0
        shortages = telemetry.gauges.get("stockpile.shortages_count", 0)

        return [
            _fmt_row("day", str(getattr(world, "day", 0))),
            _fmt_row("phase", phase_name),
            _fmt_row("agents", str(agents_total)),
            _fmt_row("depots", str(depots)),
            _fmt_row("workshops", str(workshops)),
            _fmt_row("active projects", str(active_projects)),
            _fmt_row("active deliveries", str(len(active_deliveries))),
            _fmt_row("active scouts", str(active_scouts)),
            _fmt_row("global shortages", str(shortages)),
        ]


__all__ = ["DebugCockpitCLI"]
