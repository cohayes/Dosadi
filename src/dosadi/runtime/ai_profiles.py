"""AI personality definitions for scenario runtime actors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

Stance = Literal["cautious", "balanced", "aggressive"]


@dataclass(frozen=True)
class AiPersonality:
    """Represents a tunable AI personality profile."""

    id: str
    label: str
    description: str
    role: str  # e.g. "duke_house", "espionage_branch", "mil_command", "guild_faction"
    # weights: what this actor cares about
    weight_survival: float  # regime / faction survival
    weight_legitimacy: float  # cares about legitimacy vs brute force
    weight_order: float  # wants low unrest
    weight_control: float  # likes high repression / centralization
    weight_economy: float  # cares about black markets / stability of industry
    weight_secrecy: float  # cares about information control / OpSec
    risk_tolerance: float  # 0–1: willingness to take actions that increase stress
    paranoia: float  # 0–1: tendency to see infiltration everywhere
    patience: float  # 0–1: willingness to delay decisive moves
    crackdown_threshold: float  # stress level where they start favoring harsh actions
    fragmentation_tolerance: float  # tolerance for de facto decentralization
    purge_tolerance: float  # comfort with frequent or large purges
    soft_power_preference: float  # 0–1: prefer LAW / CI tools over open MIL violence
    negotiation_preference: float  # 0–1: preference for bargaining vs coercion
    ci_stance_bias: Dict[Stance, float]
    mil_posture_bias: Dict[str, float]
    law_intensity_bias: Dict[str, float]

    @property
    def crackdown_stress_threshold(self) -> float:
        """Alias used by docs for the crackdown pivot point."""

        return self.crackdown_threshold


AI_PERSONALITIES: Dict[str, AiPersonality] = {
    "duke_paranoid_hardline": AiPersonality(
        id="duke_paranoid_hardline",
        label="Paranoid Hardline Duke",
        description="Highly controlling duke with low legitimacy concern and low tolerance for fragmentation.",
        role="duke_house",
        weight_survival=0.9,
        weight_legitimacy=0.2,
        weight_order=0.85,
        weight_control=0.95,
        weight_economy=0.4,
        weight_secrecy=0.6,
        risk_tolerance=0.55,
        paranoia=0.9,
        patience=0.25,
        crackdown_threshold=0.3,
        fragmentation_tolerance=0.15,
        purge_tolerance=0.85,
        soft_power_preference=0.2,
        negotiation_preference=0.2,
        ci_stance_bias={"cautious": 0.2, "balanced": 0.3, "aggressive": 0.5},
        mil_posture_bias={"low_alert": 0.15, "normal_alert": 0.45, "high_alert": 0.4},
        law_intensity_bias={"procedural": 0.2, "expedited": 0.4, "draconian": 0.4},
    ),
    "duke_pragmatic_balancer": AiPersonality(
        id="duke_pragmatic_balancer",
        label="Pragmatic Balancer Duke",
        description="Balances order, legitimacy, and economy; prefers restraint and bargaining under pressure.",
        role="duke_house",
        weight_survival=0.85,
        weight_legitimacy=0.75,
        weight_order=0.8,
        weight_control=0.6,
        weight_economy=0.65,
        weight_secrecy=0.5,
        risk_tolerance=0.45,
        paranoia=0.4,
        patience=0.7,
        crackdown_threshold=0.6,
        fragmentation_tolerance=0.55,
        purge_tolerance=0.35,
        soft_power_preference=0.6,
        negotiation_preference=0.7,
        ci_stance_bias={"cautious": 0.4, "balanced": 0.45, "aggressive": 0.15},
        mil_posture_bias={"low_alert": 0.2, "normal_alert": 0.6, "high_alert": 0.2},
        law_intensity_bias={"procedural": 0.45, "expedited": 0.4, "draconian": 0.15},
    ),
    "espionage_cautious_analyst": AiPersonality(
        id="espionage_cautious_analyst",
        label="Cautious Analyst",
        description="Legitimacy-minded analyst who prefers monitoring and investigation over aggressive stings.",
        role="espionage_branch",
        weight_survival=0.75,
        weight_legitimacy=0.8,
        weight_order=0.6,
        weight_control=0.5,
        weight_economy=0.55,
        weight_secrecy=0.8,
        risk_tolerance=0.25,
        paranoia=0.4,
        patience=0.75,
        crackdown_threshold=0.65,
        fragmentation_tolerance=0.5,
        purge_tolerance=0.2,
        soft_power_preference=0.85,
        negotiation_preference=0.55,
        ci_stance_bias={"cautious": 0.6, "balanced": 0.35, "aggressive": 0.05},
        mil_posture_bias={"low_alert": 0.4, "normal_alert": 0.5, "high_alert": 0.1},
        law_intensity_bias={"procedural": 0.55, "expedited": 0.35, "draconian": 0.1},
    ),
    "espionage_proactive_hawk": AiPersonality(
        id="espionage_proactive_hawk",
        label="Proactive Hawk",
        description="Control-focused hawk with higher risk appetite and paranoia; pushes aggressive CI when threats rise.",
        role="espionage_branch",
        weight_survival=0.8,
        weight_legitimacy=0.45,
        weight_order=0.7,
        weight_control=0.75,
        weight_economy=0.45,
        weight_secrecy=0.65,
        risk_tolerance=0.65,
        paranoia=0.65,
        patience=0.35,
        crackdown_threshold=0.4,
        fragmentation_tolerance=0.4,
        purge_tolerance=0.55,
        soft_power_preference=0.6,
        negotiation_preference=0.35,
        ci_stance_bias={"cautious": 0.15, "balanced": 0.45, "aggressive": 0.4},
        mil_posture_bias={"low_alert": 0.15, "normal_alert": 0.45, "high_alert": 0.4},
        law_intensity_bias={"procedural": 0.25, "expedited": 0.45, "draconian": 0.3},
    ),
    "mil_professional_order": AiPersonality(
        id="mil_professional_order",
        label="Professional Order MIL",
        description="Order-focused professionals who escalate when threats are clear and avoid arbitrary purges.",
        role="mil_command",
        weight_survival=0.8,
        weight_legitimacy=0.6,
        weight_order=0.85,
        weight_control=0.7,
        weight_economy=0.5,
        weight_secrecy=0.45,
        risk_tolerance=0.5,
        paranoia=0.35,
        patience=0.55,
        crackdown_threshold=0.5,
        fragmentation_tolerance=0.5,
        purge_tolerance=0.2,
        soft_power_preference=0.35,
        negotiation_preference=0.45,
        ci_stance_bias={"cautious": 0.35, "balanced": 0.5, "aggressive": 0.15},
        mil_posture_bias={"low_alert": 0.2, "normal_alert": 0.55, "high_alert": 0.25},
        law_intensity_bias={"procedural": 0.45, "expedited": 0.4, "draconian": 0.15},
    ),
    "mil_zealot_crusader": AiPersonality(
        id="mil_zealot_crusader",
        label="Zealot Crusader MIL",
        description="Aggressive MIL leadership comfortable with high alert postures and harsh crackdowns.",
        role="mil_command",
        weight_survival=0.8,
        weight_legitimacy=0.3,
        weight_order=0.8,
        weight_control=0.9,
        weight_economy=0.35,
        weight_secrecy=0.55,
        risk_tolerance=0.7,
        paranoia=0.6,
        patience=0.35,
        crackdown_threshold=0.35,
        fragmentation_tolerance=0.25,
        purge_tolerance=0.75,
        soft_power_preference=0.15,
        negotiation_preference=0.25,
        ci_stance_bias={"cautious": 0.15, "balanced": 0.35, "aggressive": 0.5},
        mil_posture_bias={"low_alert": 0.1, "normal_alert": 0.35, "high_alert": 0.55},
        law_intensity_bias={"procedural": 0.15, "expedited": 0.35, "draconian": 0.5},
    ),
    "guild_shadow_profit": AiPersonality(
        id="guild_shadow_profit",
        label="Shadow Profit Guild",
        description="Profit-first guild that favors slowdown and quiet sabotage over open confrontation.",
        role="guild_faction",
        weight_survival=0.65,
        weight_legitimacy=0.55,
        weight_order=0.5,
        weight_control=0.35,
        weight_economy=0.9,
        weight_secrecy=0.8,
        risk_tolerance=0.35,
        paranoia=0.5,
        patience=0.6,
        crackdown_threshold=0.6,
        fragmentation_tolerance=0.6,
        purge_tolerance=0.25,
        soft_power_preference=0.75,
        negotiation_preference=0.65,
        ci_stance_bias={"cautious": 0.45, "balanced": 0.45, "aggressive": 0.1},
        mil_posture_bias={"low_alert": 0.45, "normal_alert": 0.4, "high_alert": 0.15},
        law_intensity_bias={"procedural": 0.4, "expedited": 0.4, "draconian": 0.2},
    ),
    "cartel_expansionist": AiPersonality(
        id="cartel_expansionist",
        label="Expansionist Cartel",
        description="Growth-oriented cartel willing to sabotage or escalate to violence under repression.",
        role="cartel",
        weight_survival=0.75,
        weight_legitimacy=0.2,
        weight_order=0.4,
        weight_control=0.55,
        weight_economy=0.85,
        weight_secrecy=0.65,
        risk_tolerance=0.8,
        paranoia=0.4,
        patience=0.45,
        crackdown_threshold=0.45,
        fragmentation_tolerance=0.5,
        purge_tolerance=0.55,
        soft_power_preference=0.3,
        negotiation_preference=0.4,
        ci_stance_bias={"cautious": 0.25, "balanced": 0.4, "aggressive": 0.35},
        mil_posture_bias={"low_alert": 0.25, "normal_alert": 0.45, "high_alert": 0.3},
        law_intensity_bias={"procedural": 0.2, "expedited": 0.4, "draconian": 0.4},
    ),
}


def get_ai_personality(personality_id: str) -> AiPersonality:
    """Return a canonical AI personality profile or raise ``KeyError``."""

    try:
        return AI_PERSONALITIES[personality_id]
    except KeyError as exc:
        raise KeyError(f"Unknown AI personality id: {personality_id!r}") from exc


__all__ = [
    "AiPersonality",
    "Stance",
    "AI_PERSONALITIES",
    "get_ai_personality",
]
