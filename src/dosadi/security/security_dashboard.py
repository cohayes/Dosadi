"""Security dashboard aggregates derived from INFO and MIL docs.

This module turns the narrative "threat surface" guidance (D-INFO-0014) and
CI signature schema (D-INFO-0009) into deterministic helpers that higher-level
dashboards and sandboxes can consume.  It is intentionally lightweight: the
derived indices are heuristic blends of campaign stress/fragmentation metrics
and CI posture so tests and docs stay aligned without a full simulation layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping, Sequence

from .counterintelligence import CIPosture, CIState


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


@dataclass(slots=True)
class WardSecuritySummary:
    """Aggregate per-ward indices defined in D-INFO-0014."""

    ward_id: str
    threat_level: str
    unrest_index: float
    repression_index: float
    infiltration_risk_index: float
    ci_posture_level: int
    garrison_stability_index: float
    black_market_intensity_index: float
    law_opacity_index: float
    rumor_volatility_index: float


@dataclass(slots=True)
class SignatureAssessment:
    """Normalized CI signature entry from D-INFO-0009."""

    signature_id: str
    source_mix: Mapping[str, float]
    confidence_level: str
    competing_hypotheses: Sequence[str]
    recommended_actions: Sequence[str]


def _threat_level(unrest: float, infiltration: float, stability: float, rumor: float, repression: float) -> str:
    threat_score = 0.35 * unrest + 0.25 * infiltration + 0.2 * (1 - stability)
    threat_score += 0.1 * rumor + 0.1 * repression
    if threat_score >= 0.8:
        return "critical"
    if threat_score >= 0.6:
        return "high"
    if threat_score >= 0.35:
        return "moderate"
    return "low"


def summarize_ward_security(
    *,
    ward_id: str,
    ci_posture: CIPosture | None,
    ci_states: Sequence[CIState],
    global_stress_index: float,
    fragmentation_index: float,
    regime_legitimacy_index: float,
) -> WardSecuritySummary:
    """Blend MIL/INFO levers into the WardSecuritySummary schema."""

    ci_level = ci_posture.level if ci_posture else 0
    infiltration = sum(state.infiltration_risk for state in ci_states) / len(ci_states) if ci_states else 0.15
    unrest_index = _clamp(global_stress_index + 0.2 * fragmentation_index)
    repression_index = _clamp(0.2 + 0.25 * ci_level + 0.3 * (1 - regime_legitimacy_index) + 0.2 * global_stress_index)
    garrison_stability = _clamp(1 - (0.5 * fragmentation_index + 0.3 * global_stress_index + 0.2 * infiltration))
    black_market_intensity = _clamp(0.25 + 0.4 * fragmentation_index + 0.2 * global_stress_index)
    law_opacity = _clamp(0.3 + 0.1 * ci_level + 0.4 * (1 - regime_legitimacy_index))
    rumor_volatility = _clamp(0.25 + 0.45 * global_stress_index + 0.2 * fragmentation_index)
    threat_level = _threat_level(unrest_index, infiltration, garrison_stability, rumor_volatility, repression_index)

    return WardSecuritySummary(
        ward_id=ward_id,
        threat_level=threat_level,
        unrest_index=unrest_index,
        repression_index=repression_index,
        infiltration_risk_index=infiltration,
        ci_posture_level=ci_level,
        garrison_stability_index=garrison_stability,
        black_market_intensity_index=black_market_intensity,
        law_opacity_index=law_opacity,
        rumor_volatility_index=rumor_volatility,
    )


def _confidence_level(ci_state: CIState, posture: CIPosture) -> str:
    score = 0.4 * ci_state.infiltration_risk + 0.4 * ci_state.suspicion_score + 0.2 * (posture.level / 3)
    if score >= 0.7:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _hypotheses(ci_state: CIState) -> list[str]:
    hypotheses: list[str] = []
    if ci_state.patronage_entanglement > 0.4:
        hypotheses.append("guild_infiltration")
    if ci_state.recent_incident_pressure > 0.25 or "watched" in ci_state.rumor_tags:
        hypotheses.append("morale_collapse")
    if ci_state.doctrine_modifier > 0.2 or "clean" in ci_state.rumor_tags:
        hypotheses.append("ducal_power_play")
    if not hypotheses:
        hypotheses.append("unknown_channel")
    return hypotheses


def _actions(ci_state: CIState, posture: CIPosture) -> list[str]:
    actions = ["monitor"]
    if ci_state.infiltration_risk > 0.55:
        actions.append("sting")
    if ci_state.suspicion_score > 0.7 or ci_state.investigation_level in {"focused", "full"} or posture.level >= 3:
        actions.append("purge_recommendation")
    return actions


def assess_ci_signatures(ci_states: Iterable[CIState], posture: CIPosture) -> list[SignatureAssessment]:
    """Convert CI nodes into dashboard-friendly CI signatures."""

    assessments: list[SignatureAssessment] = []
    for ci_state in ci_states:
        source_mix: MutableMapping[str, float] = {
            "telemetry_weight": _clamp(0.3 + 0.4 * ci_state.oversight_strength),
            "ledger_weight": _clamp(0.2 + 0.3 * ci_state.patronage_entanglement),
            "human_weight": _clamp(0.2 + 0.1 * len(ci_state.rumor_tags)),
            "rumor_weight": _clamp(0.15 + 0.25 * (1 if "bought" in ci_state.rumor_tags else 0)),
        }
        confidence = _confidence_level(ci_state, posture)
        hypotheses = _hypotheses(ci_state)
        actions = _actions(ci_state, posture)
        assessments.append(
            SignatureAssessment(
                signature_id=f"ci_signature_{ci_state.node_id}",
                source_mix=source_mix,
                confidence_level=confidence,
                competing_hypotheses=tuple(hypotheses),
                recommended_actions=tuple(actions),
            )
        )

    rank = {"low": 0, "medium": 1, "high": 2}
    return sorted(assessments, key=lambda s: rank.get(s.confidence_level, 0), reverse=True)


__all__ = [
    "SignatureAssessment",
    "WardSecuritySummary",
    "assess_ci_signatures",
    "summarize_ward_security",
]
