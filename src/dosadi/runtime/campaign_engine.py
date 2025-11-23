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
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from .ai_profiles import AiPersonality
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
    ci_stance: str = "balanced"
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
class ObjectiveRuntimeState:
    objective: ObjectiveDefinition
    status_current: str = "on_track"
    final_outcome: str = "unknown"
    message: Optional[str] = None


@dataclass(slots=True)
class CampaignRunResult:
    scenario: ScenarioDefinition
    states: List[CampaignState]
    objectives: List[ObjectiveRuntimeState]
    events: Mapping[str, int]


class DukalDecision(Enum):
    ACCEPT_CRACKDOWN = "accept_crackdown"
    ACCEPT_FRAGMENTATION = "accept_fragmentation"
    SEEK_RESTRAINT = "seek_restraint"


def ai_duke_decide_campaign_path(
    personality: AiPersonality,
    stress: float,
    fragmentation: float,
    legitimacy: float,
) -> DukalDecision:
    """Pick a ducal campaign direction based on current pressures."""

    high_control = personality.weight_control >= 0.65
    high_paranoia = personality.paranoia >= 0.6
    high_legitimacy = personality.weight_legitimacy >= 0.6
    low_survival = personality.weight_survival <= 0.45
    economy_focus = personality.weight_economy >= 0.65
    legitimacy_stable = legitimacy >= 0.45

    if fragmentation >= 0.55 and low_survival and economy_focus:
        return DukalDecision.ACCEPT_FRAGMENTATION

    if stress >= personality.crackdown_threshold and high_control and high_paranoia:
        return DukalDecision.ACCEPT_CRACKDOWN

    if high_legitimacy and personality.paranoia < 0.55 and (legitimacy_stable or stress < 0.85):
        return DukalDecision.SEEK_RESTRAINT

    if stress >= 0.75 and (high_control or high_paranoia):
        return DukalDecision.ACCEPT_CRACKDOWN

    return DukalDecision.SEEK_RESTRAINT


class CampaignEngine:
    """Tick-level simulator that keeps coarse campaign state."""

    def __init__(self, scenario: ScenarioDefinition, ai_duke_personality: AiPersonality | None = None):
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
        self.objectives: Dict[str, ObjectiveRuntimeState] = {
            obj.id: ObjectiveRuntimeState(objective=obj) for obj in scenario.all_objectives()
        }
        self.events: MutableMapping[str, int] = {}
        self.duke_ai_personality = ai_duke_personality
        self._update_counterintelligence()
        self._update_security_summary()

    def run(self, ticks: int) -> CampaignRunResult:
        history: List[CampaignState] = [self.state.snapshot()]
        for _ in range(ticks):
            history.append(self.step())
        return self.build_result(history)

    def step(self) -> CampaignState:
        """Advance the simulation by a single tick and evaluate objectives."""

        self._advance_tick()
        self._evaluate_objectives()
        return self.state.snapshot()

    def build_result(self, history: List[CampaignState]) -> CampaignRunResult:
        self._finalize_objectives()
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
        self._update_counterintelligence()
        self._update_indices()
        self._update_security_summary()
        self._maybe_transition_phase()

    def _update_indices(self) -> None:
        summary = self._signature_action_summary(self.state.ci_signatures)
        modifiers = self._stance_modifiers(self.state.ci_stance)
        infiltration_avg = (
            sum(state.infiltration_risk for state in self.state.ci_states) / len(self.state.ci_states)
            if self.state.ci_states
            else 0.0
        )

        stress = self.state.global_stress_index
        frag = self.state.fragmentation_index
        legitimacy = self.state.regime_legitimacy_index

        stress += 0.01 * modifiers["stress_scale"]
        frag += 0.006 * modifiers["fragmentation_scale"]
        legitimacy -= 0.004 * modifiers["legitimacy_scale"]

        stress += 0.006 * infiltration_avg * modifiers["stress_scale"]
        frag += 0.005 * infiltration_avg * modifiers["fragmentation_scale"]
        legitimacy -= 0.005 * infiltration_avg * modifiers["legitimacy_scale"]

        stress += summary["sting"] * 0.02 * modifiers["stress_scale"]
        legitimacy -= summary["sting"] * 0.01 * modifiers["legitimacy_scale"]
        frag += summary["sting"] * 0.005 * modifiers["fragmentation_scale"]

        stress += summary["purge"] * 0.025 * modifiers["stress_scale"]
        legitimacy -= summary["purge"] * 0.015 * modifiers["legitimacy_scale"]

        infiltration_pressure = summary["monitor_only"] * 0.003 * modifiers["infiltration_pressure_scale"]
        infiltration_relief = (summary["sting"] * 0.006 + summary["purge"] * 0.008) * modifiers[
            "infiltration_suppression_scale"
        ]
        infiltration_drift = infiltration_pressure - infiltration_relief
        frag += infiltration_drift * 0.5
        legitimacy -= infiltration_drift * 0.4

        self.state.global_stress_index = _clamp01(stress)
        self.state.fragmentation_index = _clamp01(frag)
        self.state.regime_legitimacy_index = _clamp01(legitimacy)
        self.state.max_global_stress_index = max(self.state.max_global_stress_index, self.state.global_stress_index)
        self.state.max_fragmentation_index = max(self.state.max_fragmentation_index, self.state.fragmentation_index)

    def _maybe_transition_phase(self) -> None:
        stress = self.state.global_stress_index
        frag = self.state.fragmentation_index
        legitimacy = self.state.regime_legitimacy_index
        current = self.state.phase
        crackdown_threshold = 0.8
        fragmentation_threshold = 0.6

        if current == "RUMBLING_UNREST" and self.duke_ai_personality:
            duke_choice = ai_duke_decide_campaign_path(
                self.duke_ai_personality,
                stress=stress,
                fragmentation=frag,
                legitimacy=legitimacy,
            )
            print(f"[Tick {self.state.tick}] Duke AI ({self.duke_ai_personality.id}) chooses {duke_choice.value}")
            if duke_choice == DukalDecision.ACCEPT_CRACKDOWN:
                crackdown_threshold = 0.72
            elif duke_choice == DukalDecision.ACCEPT_FRAGMENTATION:
                fragmentation_threshold = 0.5
            elif duke_choice == DukalDecision.SEEK_RESTRAINT:
                crackdown_threshold = 0.9
                fragmentation_threshold = 0.7

        if stress > crackdown_threshold and current not in {"HARD_CRACKDOWN", "OPEN_CONFLICT"}:
            self._record_event("purge_campaign_starts")
            self.state.transition_phase("HARD_CRACKDOWN", tick=self.state.tick)
        elif stress > 0.65 and current == "STABLE_CONTROL":
            self.state.transition_phase("RUMBLING_UNREST", tick=self.state.tick)
        elif frag > fragmentation_threshold and current not in {"FRAGMENTED_REGIME", "OPEN_CONFLICT"}:
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
        stance = self.state.ci_stance
        infiltration_scale = 1.0
        suspicion_delta = 0.0
        if stance == "cautious":
            infiltration_scale = 1.1
            suspicion_delta = -0.02
        elif stance == "aggressive":
            infiltration_scale = 0.9
            suspicion_delta = 0.03
        for ci_state in self.state.ci_states:
            ci_state.recompute(
                posture,
                global_stress=self.state.global_stress_index,
                fragmentation=self.state.fragmentation_index,
            )
            ci_state.infiltration_risk = min(1.0, max(0.0, ci_state.infiltration_risk * infiltration_scale))
            ci_state.suspicion_score = min(1.0, max(0.0, ci_state.suspicion_score + suspicion_delta))
        self.state.ci_signatures = assess_ci_signatures(self.state.ci_states, posture)
        self._apply_signature_infiltration_pressure()

    def _signature_action_summary(self, signatures: Iterable[SignatureAssessment]) -> dict[str, int]:
        summary = {"sting": 0, "monitor_only": 0, "purge": 0}
        for signature in signatures:
            actions = set(signature.recommended_actions)
            if "sting" in actions:
                summary["sting"] += 1
            if "purge_recommendation" in actions:
                summary["purge"] += 1
            if actions == {"monitor"}:
                summary["monitor_only"] += 1
        return summary

    def _stance_modifiers(self, stance: str) -> dict[str, float]:
        if stance == "cautious":
            return {
                "stress_scale": 0.5,
                "legitimacy_scale": 0.7,
                "fragmentation_scale": 0.9,
                "infiltration_pressure_scale": 1.3,
                "infiltration_suppression_scale": 0.7,
            }
        if stance == "aggressive":
            return {
                "stress_scale": 1.5,
                "legitimacy_scale": 1.2,
                "fragmentation_scale": 1.1,
                "infiltration_pressure_scale": 0.7,
                "infiltration_suppression_scale": 1.4,
            }
        return {
            "stress_scale": 1.0,
            "legitimacy_scale": 1.0,
            "fragmentation_scale": 1.0,
            "infiltration_pressure_scale": 1.0,
            "infiltration_suppression_scale": 1.0,
        }

    def _apply_signature_infiltration_pressure(self) -> None:
        summary = self._signature_action_summary(self.state.ci_signatures)
        modifiers = self._stance_modifiers(self.state.ci_stance)

        pressure = 0.004 * summary["monitor_only"] * modifiers["infiltration_pressure_scale"]
        relief = (0.01 * summary["sting"] + 0.012 * summary["purge"]) * modifiers["infiltration_suppression_scale"]
        delta = pressure - relief

        for ci_state in self.state.ci_states:
            ci_state.infiltration_risk = _clamp01(ci_state.infiltration_risk + delta)

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
            if status.status_current == "failed":
                continue
            failure = status.objective.failure_condition
            success = status.objective.success_condition
            if failure and self._condition_met(failure):
                status.status_current = "failed"
                status.message = "failure condition met"
                continue
            if success and self._condition_met(success):
                status.status_current = "on_track"
                status.message = "constraints satisfied"
            elif status.status_current != "failed":
                status.status_current = "at_risk"
                status.message = status.message or "constraints not yet satisfied"

    def _finalize_objectives(self) -> None:
        for status in self.objectives.values():
            if status.status_current == "failed":
                status.final_outcome = "failure"
                continue
            success = status.objective.success_condition
            if success and self._condition_met(success):
                status.final_outcome = "success"
            else:
                status.final_outcome = "failure"

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


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


__all__ = [
    "CampaignEngine",
    "CampaignRunResult",
    "CampaignState",
    "ObjectiveDefinition",
    "ObjectiveRuntimeState",
    "ScenarioDefinition",
    "load_scenario_definition",
]
