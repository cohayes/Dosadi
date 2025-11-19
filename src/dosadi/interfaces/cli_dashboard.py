"""Simple CLI dashboard renderer built on the admin snapshots."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from ..admin_log import AdminEventLog
from ..state import WorldState
from .admin_debug import snapshot_agent_debug, snapshot_ward, snapshot_world_state
from .cli_components import ProgressBar, Section, Table, TableColumn


class AdminDashboardCLI:
    """Compose the snapshot helpers into a readable CLI dashboard."""

    def __init__(self, width: int = 80) -> None:
        self.width = width

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def render(
        self,
        world: WorldState,
        *,
        ward_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        event_log: Optional[AdminEventLog] = None,
        event_type: Optional[str] = None,
    ) -> str:
        sections = [self._render_world(world)]
        if ward_id and ward_id in world.wards:
            sections.append(self._render_ward(world, ward_id))
        if agent_id and agent_id in world.agents:
            sections.append(self._render_agent(world, agent_id))
        if event_log:
            sections.append(self._render_events(event_log, ward_id=ward_id, event_type=event_type))
        return "\n\n".join(section.render() for section in sections)

    # ------------------------------------------------------------------
    # Internal render helpers
    # ------------------------------------------------------------------
    def _render_world(self, world: WorldState) -> Section:
        snapshot = snapshot_world_state(world)
        columns = [
            TableColumn("Ward", 12),
            TableColumn("Tier1", 6, align="right"),
            TableColumn("Tier2+", 6, align="right"),
            TableColumn("Hunger", 8, align="right"),
            TableColumn("Fear", 6, align="right"),
            TableColumn("Fatigue", 8, align="right"),
        ]
        rows = [
            [
                summary.name,
                str(summary.population_tier1),
                str(summary.population_tier2_plus),
                f"{summary.avg_hunger:0.2f}",
                f"{summary.avg_fear:0.2f}",
                f"{summary.avg_fatigue:0.2f}",
            ]
            for summary in snapshot.ward_summaries
        ]
        metrics = ", ".join(f"{key}={value:0.2f}" for key, value in snapshot.global_metrics.items())
        body = [Table(columns, rows).render(), "", f"Metrics: {metrics}"]
        return Section(f"World @ tick {snapshot.tick}", body, width=self.width)

    def _render_ward(self, world: WorldState, ward_id: str) -> Section:
        ward_snapshot = snapshot_ward(world, ward_id)
        columns = [
            TableColumn("Facility", 18),
            TableColumn("Cap", 4, align="right"),
            TableColumn("Occ", 4, align="right"),
            TableColumn("Queue", 5, align="right"),
            TableColumn("Enforce", 8, align="right"),
        ]
        rows = [
            [
                facility.name,
                str(facility.capacity),
                str(facility.current_occupancy),
                str(facility.queue_length),
                f"{facility.enforcement_presence:0.2f}",
            ]
            for facility in ward_snapshot.facilities
        ]
        metrics = ", ".join(f"{key}={value:0.2f}" for key, value in ward_snapshot.metrics.items())
        body = [
            Table(columns, rows).render(),
            "",
            f"Tier1={ward_snapshot.population_tier1} Tier2+={ward_snapshot.population_tier2_plus}",
            f"Hunger={ward_snapshot.avg_hunger:0.2f} Fear={ward_snapshot.avg_fear:0.2f} Fatigue={ward_snapshot.avg_fatigue:0.2f}",
            f"Metrics: {metrics}",
        ]
        return Section(f"Ward {ward_snapshot.name}", body, width=self.width)

    def _render_agent(self, world: WorldState, agent_id: str) -> Section:
        agent_snapshot = snapshot_agent_debug(world, agent_id)
        vitals = [
            ProgressBar(agent_snapshot.hunger, label="hunger").render(),
            ProgressBar(agent_snapshot.thirst, label="thirst").render(),
            ProgressBar(agent_snapshot.fatigue, label="fatigue").render(),
            ProgressBar(agent_snapshot.drives.fear, label="fear").render(),
        ]
        decision_line = "No decisions yet"
        if agent_snapshot.last_decision:
            decision_line = (
                f"Last decision @{agent_snapshot.last_decision.tick}: {agent_snapshot.last_decision.chosen_action_kind}"
                f" survival={agent_snapshot.last_decision.survival_score:0.2f}"
            )
        known_agents = ", ".join(entry.other_agent_id for entry in agent_snapshot.known_agents[:5]) or "<none>"
        rumors = ", ".join(entry.payload_summary for entry in agent_snapshot.rumors[:5]) or "<none>"
        handles = ", ".join(agent_snapshot.identity.handles) or "<none>"
        permits = ", ".join(agent_snapshot.identity.active_permits) or "<none>"
        trust = ", ".join(
            f"{flag}:{value:0.2f}"
            for flag, value in agent_snapshot.identity.trust_flags.items()
        ) or "<none>"
        body = [
            f"Role={agent_snapshot.role or '-'} Faction={agent_snapshot.faction or '-'} Caste={agent_snapshot.caste or '-'}",
            f"Health={agent_snapshot.health:0.2f}",
            *vitals,
            decision_line,
            f"Known agents: {known_agents}",
            f"Rumors: {rumors}",
            f"Handles: {handles} Clearance={agent_snapshot.identity.clearance_level}",
            f"Permits: {permits}",
            f"Trust flags: {trust}",
            (
                "Loadout primary="
                f"{agent_snapshot.loadout.primary or '-'} secondary={agent_snapshot.loadout.secondary or '-'} "
                f"support={', '.join(agent_snapshot.loadout.support_items) or '<none>'}"
            ),
            (
                f"Kit tags: {', '.join(agent_snapshot.loadout.kit_tags) or '<none>'} "
                f"readiness={agent_snapshot.loadout.readiness:0.2f} signature={agent_snapshot.loadout.signature}"
            ),
        ]
        return Section(f"Agent {agent_snapshot.agent_id}", body, width=self.width)

    def _render_events(
        self,
        log: AdminEventLog,
        *,
        ward_id: Optional[str],
        event_type: Optional[str],
        limit: int = 8,
    ) -> Section:
        events = log.get_recent(event_type=event_type, ward_id=ward_id, limit=limit)
        columns = [
            TableColumn("Tick", 6, align="right"),
            TableColumn("Type", 16),
            TableColumn("Summary", 40),
        ]
        rows = [
            [str(event.tick), event.event_type, event.summary()]
            for event in events
        ]
        body = [Table(columns, rows).render()]
        filter_desc = []
        if ward_id:
            filter_desc.append(f"ward={ward_id}")
        if event_type:
            filter_desc.append(f"type={event_type}")
        if filter_desc:
            body.append("")
            body.append("Filters: " + ", ".join(filter_desc))
        return Section("Recent events", body, width=self.width)


class ScenarioTimelineCLI:
    """Render scenario phase reports into a compact ASCII timeline."""

    def __init__(self, width: int = 90) -> None:
        self.width = width

    def render(self, phases: Sequence[object], *, title: str = "Scenario Timeline") -> str:
        columns = [
            TableColumn("Phase", 6),
            TableColumn("Description", 32),
            TableColumn("Key metrics", 34),
            TableColumn("Events", 6, align="right"),
        ]
        rows = [
            [
                self._phase_key(phase),
                self._phase_description(phase),
                self._format_metrics(getattr(phase, "metrics", {})),
                str(len(getattr(phase, "events", []) or [])),
            ]
            for phase in phases
        ]
        body = [Table(columns, rows).render()]
        return Section(title, body, width=self.width).render()

    def _phase_key(self, phase: object) -> str:
        for attr in ("key", "phase", "name"):
            value = getattr(phase, attr, None)
            if value:
                return str(value)
        return "?"

    def _phase_description(self, phase: object) -> str:
        description = getattr(phase, "description", None) or getattr(phase, "name", "")
        return description[:60]

    def _format_metrics(self, metrics: Mapping[str, object]) -> str:
        if not metrics:
            return "-"
        pairs = list(metrics.items())[:3]
        formatted = [f"{key}={self._format_value(value)}" for key, value in pairs]
        remaining = len(metrics) - len(pairs)
        if remaining > 0:
            formatted.append(f"+{remaining} more")
        return ", ".join(formatted)

    @staticmethod
    def _format_value(value: object) -> str:
        if isinstance(value, float):
            return f"{value:0.2f}"
        return str(value)


__all__ = ["AdminDashboardCLI", "ScenarioTimelineCLI"]
