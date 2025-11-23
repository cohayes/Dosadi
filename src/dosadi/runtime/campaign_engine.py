"""Minimal campaign engine for scenario experimentation.

The engine is intentionally lightweight: it can load a scenario definition
from YAML (using :mod:`dosadi.runtime.yaml_loader`), maintain a coarse
``CampaignState`` during tick simulation, evaluate objectives, and emit a
compact report that the CLI can render.  It is geared toward the documented
``S-0001_Pre_Sting_Quiet_Season`` scenario and should not be mistaken for the
full systems simulation.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from .yaml_loader import ParsedDocument, SimpleYAMLError
from ..security.counterintelligence import CIPosture, CIState, seed_default_ci_states
from ..security.security_dashboard import SignatureAssessment, WardSecuritySummary, assess_ci_signatures, summarize_ward_security


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ObjectiveCondition:
    kind: str
    constraints: Mapping[str, object]


@dataclass(slots=True)
class ObjectiveDefinition:
    id: str
    label: str
    type: str
    success_condition: Optional[ObjectiveCondition]
    failure_condition: Optional[ObjectiveCondition]
    priority: str
    scoring_weight: float = 1.0


@dataclass(slots=True)
class ScenarioDefinition:
    id: str
    name: str
    description: str
    starting_campaign_phase: str
    starting_tick: int
    duration_limit_ticks: Optional[int]
    starting_state_ref: Optional[str]
    world_overrides: Mapping[str, object]
    role_configs: Sequence[Mapping[str, object]]
    objectives: Mapping[str, Sequence[ObjectiveDefinition]]
    special_rules: Mapping[str, object]

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, object]) -> "ScenarioDefinition":
        try:
            body = mapping["ScenarioDefinition"]
        except KeyError as exc:
            raise SimpleYAMLError("ScenarioDefinition root key is required") from exc
        if not isinstance(body, Mapping):
            raise SimpleYAMLError("ScenarioDefinition must be a mapping")
        objectives = _parse_objectives(body.get("objectives", {}))
        return cls(
            id=str(body.get("id", "")),
            name=str(body.get("name", "")),
            description=str(body.get("description", "")),
            starting_campaign_phase=str(body.get("starting_campaign_phase", "STABLE_CONTROL")),
            starting_tick=int(body.get("starting_tick", 0)),
            duration_limit_ticks=body.get("duration_limit_ticks"),
            starting_state_ref=body.get("starting_state_ref"),
            world_overrides=body.get("world_overrides", {}),
            role_configs=tuple(body.get("role_configs", []) or ()),
            objectives=objectives,
            special_rules=body.get("special_rules", {}),
        )

    def all_objectives(self) -> Iterable[ObjectiveDefinition]:
        for bucket in self.objectives.values():
            for obj in bucket:
                yield obj


def _parse_objectives(raw: object) -> Mapping[str, Sequence[ObjectiveDefinition]]:
    if not isinstance(raw, Mapping):
        return {}
    parsed: Dict[str, List[ObjectiveDefinition]] = {}
    for bucket, items in raw.items():
        parsed[bucket] = []
        for item in items or []:
            if not isinstance(item, Mapping):
                continue
            parsed[bucket].append(
                ObjectiveDefinition(
                    id=str(item.get("id", "")),
                    label=str(item.get("label", "")),
                    type=str(item.get("type", "state")),
                    success_condition=_condition_from_mapping(item.get("success_condition")),
                    failure_condition=_condition_from_mapping(item.get("failure_condition")),
                    priority=str(item.get("priority", bucket)),
                    scoring_weight=float(item.get("scoring_weight", 1.0)),
                )
            )
    return parsed


def _condition_from_mapping(raw: object) -> Optional[ObjectiveCondition]:
    if not isinstance(raw, Mapping):
        return None
    if not raw:
        return None
    constraints = raw.get("constraints", {}) if isinstance(raw.get("constraints", {}), Mapping) else {}
    kind = str(raw.get("kind", raw.get("type", "state")))
    return ObjectiveCondition(kind=kind, constraints=constraints)


# ---------------------------------------------------------------------------
# Campaign state and simulation
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CampaignPhaseHistory:
    phase: str
    start_tick: int
    end_tick: Optional[int] = None
    trigger_event_id: Optional[str] = None


@dataclass(slots=True)
class CampaignState:
    tick: int
    phase: str
    phase_tick_started: int
    phase_history: List[CampaignPhaseHistory] = field(default_factory=list)
    global_stress_index: float = 0.25
    regime_legitimacy_index: float = 0.75
    fragmentation_index: float = 0.2
    crisis_flags: List[str] = field(default_factory=list)
    active_scenarios: List[str] = field(default_factory=list)
    max_global_stress_index: float = 0.25
    max_fragmentation_index: float = 0.2
    ci_posture: Optional[CIPosture] = None
    ci_states: List[CIState] = field(default_factory=list)
    ci_signatures: List[SignatureAssessment] = field(default_factory=list)
    security_summary: Optional[WardSecuritySummary] = None

    def transition_phase(self, new_phase: str, *, tick: int, trigger_event_id: Optional[str] = None) -> None:
        if new_phase == self.phase:
            return
        if self.phase_history:
            self.phase_history[-1].end_tick = tick
        self.phase = new_phase
        self.phase_tick_started = tick
        self.phase_history.append(
            CampaignPhaseHistory(phase=new_phase, start_tick=tick, trigger_event_id=trigger_event_id)
        )

    def snapshot(self) -> "CampaignState":
        return replace(
            self,
            phase_history=list(self.phase_history),
            crisis_flags=list(self.crisis_flags),
            active_scenarios=list(self.active_scenarios),
            ci_posture=copy.deepcopy(self.ci_posture),
            ci_states=[copy.deepcopy(state) for state in self.ci_states],
            ci_signatures=[copy.deepcopy(signature) for signature in self.ci_signatures],
            security_summary=copy.deepcopy(self.security_summary),
        )


@dataclass(slots=True)
class ObjectiveStatus:
    objective: ObjectiveDefinition
    status: str = "pending"
    message: Optional[str] = None


@dataclass(slots=True)
class CampaignRunResult:
    scenario: ScenarioDefinition
    states: List[CampaignState]
    objectives: List[ObjectiveStatus]
    events: Mapping[str, int]


class CampaignEngine:
    """Tick-level simulator that keeps coarse campaign state."""

    def __init__(self, scenario: ScenarioDefinition):
        self.scenario = scenario
        self.state = CampaignState(
            tick=scenario.starting_tick,
            phase=scenario.starting_campaign_phase,
            phase_tick_started=scenario.starting_tick,
            phase_history=[CampaignPhaseHistory(phase=scenario.starting_campaign_phase, start_tick=scenario.starting_tick)],
            active_scenarios=[scenario.id],
            ci_posture=CIPosture(ward_id=scenario.id or "ward", level=1, driver="routine", active_assets={
                "special_detachments": 1,
                "commissar_cadres": 0,
                "espionage_branch_cells": 1,
            }),
            ci_states=seed_default_ci_states(scenario.id or "ward"),
        )
        self.objectives: Dict[str, ObjectiveStatus] = {
            obj.id: ObjectiveStatus(objective=obj) for obj in scenario.all_objectives()
        }
        self.events: MutableMapping[str, int] = {}
        self._update_counterintelligence()
        self._update_security_summary()

    def run(self, ticks: int) -> CampaignRunResult:
        history: List[CampaignState] = [self.state.snapshot()]
        for _ in range(ticks):
            self._advance_tick()
            history.append(self.state.snapshot())
            self._evaluate_objectives()
        return CampaignRunResult(
            scenario=self.scenario,
            states=history,
            objectives=list(self.objectives.values()),
            events=dict(self.events),
        )

    # ------------------------------------------------------------------
    # Simulation helpers
    # ------------------------------------------------------------------
    def _advance_tick(self) -> None:
        self.state.tick += 1
        self._update_indices()
        self._update_counterintelligence()
        self._update_security_summary()
        self._maybe_transition_phase()

    def _update_indices(self) -> None:
        drift = 0.002 + 0.001 * ((self.state.tick % 5) / 5)
        self.state.global_stress_index = min(1.0, self.state.global_stress_index + drift)
        self.state.fragmentation_index = min(1.0, self.state.fragmentation_index + drift * 0.6)
        self.state.regime_legitimacy_index = max(0.0, self.state.regime_legitimacy_index - drift * 0.4)
        self.state.max_global_stress_index = max(self.state.max_global_stress_index, self.state.global_stress_index)
        self.state.max_fragmentation_index = max(self.state.max_fragmentation_index, self.state.fragmentation_index)

    def _maybe_transition_phase(self) -> None:
        stress = self.state.global_stress_index
        frag = self.state.fragmentation_index
        current = self.state.phase
        if stress > 0.8 and current not in {"HARD_CRACKDOWN", "OPEN_CONFLICT"}:
            self._record_event("purge_campaign_starts")
            self.state.transition_phase("HARD_CRACKDOWN", tick=self.state.tick)
        elif stress > 0.65 and current == "STABLE_CONTROL":
            self.state.transition_phase("RUMBLING_UNREST", tick=self.state.tick)
        elif frag > 0.6 and current not in {"FRAGMENTED_REGIME", "OPEN_CONFLICT"}:
            self.state.transition_phase("FRAGMENTED_REGIME", tick=self.state.tick)

    def _record_event(self, name: str) -> None:
        self.events[name] = self.events.get(name, 0) + 1

    def _update_counterintelligence(self) -> None:
        if not self.state.ci_posture:
            return
        purge_campaigns = self.events.get("purge_campaign_starts", 0)
        posture = self.state.ci_posture.adjust_for_stress(
            global_stress=self.state.global_stress_index, purge_campaigns=purge_campaigns
        )
        self.state.ci_posture = posture
        for ci_state in self.state.ci_states:
            ci_state.recompute(
                posture,
                global_stress=self.state.global_stress_index,
                fragmentation=self.state.fragmentation_index,
            )
        self.state.ci_signatures = assess_ci_signatures(self.state.ci_states, posture)

    def _update_security_summary(self) -> None:
        self.state.security_summary = summarize_ward_security(
            ward_id=self.state.ci_posture.ward_id if self.state.ci_posture else self.scenario.id or "ward",
            ci_posture=self.state.ci_posture,
            ci_states=self.state.ci_states,
            global_stress_index=self.state.global_stress_index,
            fragmentation_index=self.state.fragmentation_index,
            regime_legitimacy_index=self.state.regime_legitimacy_index,
        )

    # ------------------------------------------------------------------
    # Objectives
    # ------------------------------------------------------------------
    def _evaluate_objectives(self) -> None:
        for status in self.objectives.values():
            if status.status in {"achieved", "failed"}:
                continue
            failure = status.objective.failure_condition
            success = status.objective.success_condition
            if failure and self._condition_met(failure):
                status.status = "failed"
                status.message = "failure condition met"
                continue
            if success and self._condition_met(success):
                status.status = "achieved"
                status.message = "success condition met"

    def _condition_met(self, condition: ObjectiveCondition) -> bool:
        if condition.kind == "state":
            return self._state_condition_met(condition.constraints)
        if condition.kind == "event":
            return self._event_condition_met(condition.constraints)
        return False

    def _state_condition_met(self, constraints: Mapping[str, object]) -> bool:
        phase_not_in = constraints.get("campaign_phase_not_in") or []
        if phase_not_in and self.state.phase in phase_not_in:
            return False
        phase_in = constraints.get("campaign_phase_in") or []
        if phase_in and self.state.phase not in phase_in:
            return False
        max_stress = constraints.get("max_global_stress_index")
        if max_stress is not None and self.state.max_global_stress_index > float(max_stress):
            return False
        max_frag = constraints.get("max_fragmentation_index")
        if max_frag is not None and self.state.max_fragmentation_index > float(max_frag):
            return False
        return True

    def _event_condition_met(self, constraints: Mapping[str, object]) -> bool:
        required = constraints.get("required_events") or []
        for name in required:
            if self.events.get(name, 0) <= 0:
                return False
        limits = constraints.get("max_events") or {}
        if isinstance(limits, Mapping):
            for name, max_count in limits.items():
                if self.events.get(name, 0) > float(max_count):
                    return False
        return True


# ---------------------------------------------------------------------------
# Loader helpers
# ---------------------------------------------------------------------------


def load_scenario_definition(path: Path) -> ScenarioDefinition:
    document = ParsedDocument.from_file(path)
    return ScenarioDefinition.from_mapping(document.content)


__all__ = [
    "CampaignEngine",
    "CampaignRunResult",
    "CampaignState",
    "ObjectiveDefinition",
    "ObjectiveStatus",
    "ScenarioDefinition",
    "load_scenario_definition",
]
