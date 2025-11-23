"""Counterintelligence and infiltration helpers derived from MIL/INFO docs.

The MIL and INFO documentation families define several YAML-backed data
shapes around counterintelligence (CI) posture, infiltration risk, and
espionage interaction points.  This module provides small dataclasses that
mirror those shapes and a few deterministic scoring functions so tests and
lightweight sandboxes can reason about CI dynamics without a full
simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, MutableMapping, Sequence


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


@dataclass(slots=True)
class CIState:
    """Representation of the ``CIState`` YAML schema (D-MIL-0108).

    The doc describes a node-level state composed of exposure, oversight,
    patronage, and doctrine effects.  ``recompute`` deterministically derives
    infiltration risk and suspicion so downstream tooling can classify nodes
    or route CI actions.
    """

    node_id: str
    node_type: str
    ward_id: str
    base_exposure: float
    oversight_strength: float
    patronage_entanglement: float
    doctrine_modifier: float
    recent_incident_pressure: float
    rumor_tags: Sequence[str] = field(default_factory=tuple)

    infiltration_risk: float = 0.0
    suspicion_score: float = 0.0
    investigation_level: str = "none"

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, object]) -> "CIState":
        return cls(
            node_id=str(mapping.get("node_id", "")),
            node_type=str(mapping.get("node_type", "")),
            ward_id=str(mapping.get("ward_id", "")),
            base_exposure=float(mapping.get("base_exposure", 0.0)),
            oversight_strength=float(mapping.get("oversight_strength", 0.0)),
            patronage_entanglement=float(mapping.get("patronage_entanglement", 0.0)),
            doctrine_modifier=float(mapping.get("doctrine_modifier", 0.0)),
            recent_incident_pressure=float(mapping.get("recent_incident_pressure", 0.0)),
            rumor_tags=tuple(mapping.get("rumor_tags", []) or ()),
        )

    def recompute(self, posture: "CIPosture", *, global_stress: float = 0.0, fragmentation: float = 0.0) -> None:
        """Derive infiltration and suspicion scores using the doc levers.

        The formula intentionally mirrors the qualitative relationships in
        D-MIL-0108: exposure and patronage entanglement drive risk upward,
        oversight and active CI posture suppress it, while scandals or purge
        pressure elevate both risk and suspicion.
        """

        risk = self.base_exposure
        risk += 0.35 * self.patronage_entanglement
        risk += 0.2 * self.doctrine_modifier
        risk += 0.15 * self.recent_incident_pressure
        risk -= 0.4 * self.oversight_strength
        risk += 0.05 * posture.level
        risk += 0.05 * global_stress
        risk += 0.02 * fragmentation
        self.infiltration_risk = _clamp(risk)

        suspicion = 0.25 * self.oversight_strength
        suspicion += 0.15 * (posture.level / 3)
        suspicion += 0.25 * self.recent_incident_pressure
        suspicion += 0.1 * global_stress
        suspicion += 0.05 * fragmentation
        if "watched" in self.rumor_tags:
            suspicion += 0.1
        if "clean" in self.rumor_tags:
            suspicion -= 0.05
        self.suspicion_score = _clamp(suspicion)

        if self.suspicion_score > 0.85:
            self.investigation_level = "full"
        elif self.suspicion_score > 0.65:
            self.investigation_level = "focused"
        elif self.suspicion_score > 0.35:
            self.investigation_level = "light"
        else:
            self.investigation_level = "none"


@dataclass(slots=True)
class CIPosture:
    """Ward- or region-level CI stance as described in D-MIL-0108."""

    ward_id: str
    level: int
    driver: str
    active_assets: Mapping[str, int]

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, object]) -> "CIPosture":
        assets: MutableMapping[str, int] = {}
        raw_assets = mapping.get("active_assets", {}) if isinstance(mapping.get("active_assets"), Mapping) else {}
        for key, value in raw_assets.items():
            assets[key] = int(value)
        return cls(
            ward_id=str(mapping.get("ward_id", "")),
            level=int(mapping.get("level", 0)),
            driver=str(mapping.get("driver", "routine")),
            active_assets=assets,
        )

    def adjust_for_stress(self, *, global_stress: float, purge_campaigns: int = 0) -> "CIPosture":
        """Return a posture adjusted by external stressors.

        High stress or repeated purge triggers raise posture levels, matching
        the paranoia escalation described in the CI posture section.
        """

        level = self.level
        if global_stress > 0.8 or purge_campaigns > 1:
            level = max(level, 3)
        elif global_stress > 0.6 or purge_campaigns > 0:
            level = max(level, 2)
        elif global_stress > 0.4:
            level = max(level, 1)
        return CIPosture(ward_id=self.ward_id, level=level, driver=self.driver, active_assets=dict(self.active_assets))


@dataclass(slots=True)
class InfiltrationAttempt:
    """Minimal, deterministic representation of an infiltration attempt."""

    id: str
    actor_type: str
    target_node_id: str
    method: str
    difficulty: float

    def success_probability(self, ci_state: CIState, posture: CIPosture) -> float:
        """Compute a probability using CIState risk and posture levers.

        The mapping mirrors the doc guidance: higher infiltration risk makes
        success more likely, but strong oversight and paranoid posture push the
        probability down.  The calculation is deterministic for testability.
        """

        base = 0.5 + 0.4 * (ci_state.infiltration_risk - 0.5)
        base -= 0.25 * ci_state.suspicion_score
        base -= 0.15 * (posture.level / 3)
        method_modifier = {
            "bribe": -0.05 * ci_state.oversight_strength,
            "patronage": 0.1 * ci_state.patronage_entanglement,
            "blackmail": 0.05 * ci_state.recent_incident_pressure,
            "ideological_appeal": 0.04 * ci_state.doctrine_modifier,
            "family_bond": 0.02,
        }.get(self.method, 0.0)
        base += method_modifier
        base -= 0.25 * self.difficulty
        return _clamp(base)

    def evaluate_outcome(self, ci_state: CIState, posture: CIPosture) -> str:
        """Map success probability into one of the documented outcomes."""

        chance = self.success_probability(ci_state, posture)
        if chance > 0.65:
            return "success"
        if chance > 0.45:
            return "partial"
        return "failure"


def seed_default_ci_states(ward_id: str) -> list[CIState]:
    """Provide a handful of representative CI nodes for sandboxes.

    The values are derived from common patterns in the infiltration doc: high
    exposure checkpoints on logistics corridors, politicized command nodes,
    and lightly watched patrols in quieter wards.
    """

    seeds: Iterable[Mapping[str, object]] = [
        {
            "node_id": "checkpoint_riverside_corridor",
            "node_type": "checkpoint",
            "ward_id": ward_id,
            "base_exposure": 0.6,
            "oversight_strength": 0.35,
            "patronage_entanglement": 0.5,
            "doctrine_modifier": 0.1,
            "recent_incident_pressure": 0.25,
            "rumor_tags": ["watched"],
        },
        {
            "node_id": "command_node_inner_barracks",
            "node_type": "command",
            "ward_id": ward_id,
            "base_exposure": 0.35,
            "oversight_strength": 0.55,
            "patronage_entanglement": 0.25,
            "doctrine_modifier": 0.2,
            "recent_incident_pressure": 0.15,
            "rumor_tags": ["clean"],
        },
        {
            "node_id": "patrol_market_quadrant",
            "node_type": "patrol",
            "ward_id": ward_id,
            "base_exposure": 0.48,
            "oversight_strength": 0.25,
            "patronage_entanglement": 0.4,
            "doctrine_modifier": 0.05,
            "recent_incident_pressure": 0.05,
            "rumor_tags": ["bought"],
        },
    ]
    return [CIState.from_mapping(seed) for seed in seeds]


__all__ = [
    "CIState",
    "CIPosture",
    "InfiltrationAttempt",
    "seed_default_ci_states",
]
