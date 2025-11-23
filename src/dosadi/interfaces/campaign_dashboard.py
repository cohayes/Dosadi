"""CLI dashboard for campaign-focused scenario runs."""

from __future__ import annotations

from typing import Mapping, Sequence

from ..runtime.campaign_engine import CampaignRunResult, CampaignState
from .cli_components import ProgressBar, Section, Table, TableColumn


class CampaignDashboardCLI:
    """Render campaign state and objective progress into a compact view."""

    def __init__(self, width: int = 90) -> None:
        self.width = width

    def render(self, result: CampaignRunResult) -> str:
        sections = [
            self._render_state(result),
            self._render_objectives(result),
        ]
        summary_section = self._render_security_summary(result.states[-1])
        if summary_section:
            sections.insert(1, summary_section)
        ci_section = self._render_counterintelligence(result)
        if ci_section:
            sections.insert(1, ci_section)
        outcome_section = self._render_objective_outcomes(result)
        if outcome_section:
            sections.append(outcome_section)
        return "\n\n".join(section.render() for section in sections)

    def _render_state(self, result: CampaignRunResult) -> Section:
        state = result.states[-1]
        progress = ProgressBar(state.global_stress_index, label="stress").render()
        frag = ProgressBar(state.fragmentation_index, label="fragmentation").render()
        legitimacy = ProgressBar(state.regime_legitimacy_index, label="legitimacy").render()
        rows = [
            ["Phase", state.phase],
            ["Tick", str(state.tick)],
            ["Stress", progress],
            ["Fragmentation", frag],
            ["Legitimacy", legitimacy],
        ]
        columns = [TableColumn("Metric", 16), TableColumn("Value", self.width - 20)]
        table = Table(columns, rows)
        history = ", ".join(entry.phase for entry in state.phase_history)
        body = [table.render(), "", f"Active scenarios: {', '.join(state.active_scenarios)}", f"Phase history: {history}"]
        title = f"{result.scenario.name} @ tick {state.tick}" if result.scenario.name else "Campaign"
        return Section(title, body, width=self.width)

    def _render_objectives(self, result: CampaignRunResult) -> Section:
        objectives = result.objectives
        columns = [
            TableColumn("ID", 18),
            TableColumn("Label", 32),
            TableColumn("Priority", 10),
            TableColumn("Status", 10),
        ]
        rows = [
            [status.objective.id, status.objective.label, status.objective.priority, status.status_current]
            for status in objectives
        ]
        table = Table(columns, rows)
        subtitle = f"Objectives · {result.scenario.id}" if result.scenario.id else "Objectives"
        return Section(subtitle, [table.render()], width=self.width)

    def _render_objective_outcomes(self, result: CampaignRunResult) -> Section | None:
        if not result.objectives:
            return None
        rows = [
            [state.objective.id, state.objective.label, state.final_outcome]
            for state in result.objectives
        ]
        columns = [
            TableColumn("Objective", 22),
            TableColumn("Label", 28),
            TableColumn("Outcome", 12),
        ]
        table = Table(columns, rows)
        return Section("Objective Outcomes", [table.render()], width=self.width)

    def _render_security_summary(self, state: CampaignState) -> Section | None:
        summary = state.security_summary
        if not summary:
            return None
        rows = [
            ["Threat", summary.threat_level],
            ["Unrest", ProgressBar(summary.unrest_index, label="unrest").render()],
            ["Repression", ProgressBar(summary.repression_index, label="repression").render()],
            ["Infiltration", ProgressBar(summary.infiltration_risk_index, label="ci risk").render()],
            ["Stability", ProgressBar(summary.garrison_stability_index, label="garrison").render()],
            ["Rumors", ProgressBar(summary.rumor_volatility_index, label="volatility").render()],
        ]
        columns = [TableColumn("Security", 18), TableColumn("Index", self.width - 22)]
        table = Table(columns, rows)

        signature_rows = []
        for signature in state.ci_signatures[:3]:
            signature_rows.append(
                [
                    signature.signature_id,
                    f"{signature.confidence_level} · actions: {', '.join(signature.recommended_actions)}",
                ]
            )
        signature_table = None
        if signature_rows:
            signature_table = Table([TableColumn("CI Signature", 26), TableColumn("Assessment", self.width - 30)], signature_rows)

        body = [table.render()]
        if signature_table:
            body.extend(["", signature_table.render()])

        return Section(f"Security Summary · {summary.ward_id}", body, width=self.width)

    def _render_counterintelligence(self, result: CampaignRunResult) -> Section | None:
        state = result.states[-1]
        if not state.ci_posture:
            return None
        posture = state.ci_posture
        rows = [
            ["Posture", f"Level {posture.level} ({posture.driver})"],
            ["Stance", state.ci_stance],
            ["Assets", ", ".join(f"{k}:{v}" for k, v in posture.active_assets.items())],
        ]
        top_states = sorted(state.ci_states, key=lambda s: s.infiltration_risk, reverse=True)[:3]
        for ci_state in top_states:
            label = f"{ci_state.node_type}:{ci_state.node_id}"
            rows.append(
                [
                    label,
                    f"risk {ci_state.infiltration_risk:.2f} · suspicion {ci_state.suspicion_score:.2f} ({ci_state.investigation_level})",
                ]
            )
        columns = [TableColumn("CI", 26), TableColumn("Details", self.width - 30)]
        table = Table(columns, rows)
        return Section("Counterintelligence Posture", [table.render()], width=self.width)


__all__ = ["CampaignDashboardCLI"]
