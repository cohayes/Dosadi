"""AI personality definitions for scenario runtime actors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

Stance = Literal["cautious", "balanced", "aggressive"]


@dataclass(frozen=True)
class AiPersonality:
    """Represents a tunable AI personality profile."""

    id: str
    role: str  # e.g. "duke_house", "espionage_branch", "mil_command", "guild_faction"
    # weights: what this actor cares about
    weight_survival: float  # regime / faction survival
    weight_legitimacy: float  # cares about legitimacy vs brute force
    weight_order: float  # wants low unrest
    weight_control: float  # likes high repression / centralization
    weight_economy: float  # cares about black markets / stability of industry
    risk_tolerance: float  # 0–1: willingness to take actions that increase stress
    paranoia: float  # 0–1: tendency to see infiltration everywhere
    crackdown_threshold: float  # stress level where they start favoring harsh actions
    soft_power_preference: float  # 0–1: prefer LAW / CI tools over open MIL violence


AI_PERSONALITIES: Dict[str, AiPersonality] = {
    "duke_paranoid_hardline": AiPersonality(
        id="duke_paranoid_hardline",
        role="duke_house",
        weight_survival=0.9,
        weight_legitimacy=0.2,
        weight_order=0.85,
        weight_control=0.95,
        weight_economy=0.4,
        risk_tolerance=0.55,
        paranoia=0.9,
        crackdown_threshold=0.3,
        soft_power_preference=0.2,
    ),
    "duke_pragmatic": AiPersonality(
        id="duke_pragmatic",
        role="duke_house",
        weight_survival=0.9,
        weight_legitimacy=0.7,
        weight_order=0.75,
        weight_control=0.6,
        weight_economy=0.65,
        risk_tolerance=0.45,
        paranoia=0.35,
        crackdown_threshold=0.55,
        soft_power_preference=0.6,
    ),
    "espionage_cautious_analyst": AiPersonality(
        id="espionage_cautious_analyst",
        role="espionage_branch",
        weight_survival=0.75,
        weight_legitimacy=0.8,
        weight_order=0.6,
        weight_control=0.5,
        weight_economy=0.55,
        risk_tolerance=0.25,
        paranoia=0.4,
        crackdown_threshold=0.65,
        soft_power_preference=0.85,
    ),
    "espionage_proactive_hawk": AiPersonality(
        id="espionage_proactive_hawk",
        role="espionage_branch",
        weight_survival=0.8,
        weight_legitimacy=0.45,
        weight_order=0.7,
        weight_control=0.7,
        weight_economy=0.45,
        risk_tolerance=0.65,
        paranoia=0.65,
        crackdown_threshold=0.4,
        soft_power_preference=0.6,
    ),
    "mil_professional_order": AiPersonality(
        id="mil_professional_order",
        role="mil_command",
        weight_survival=0.8,
        weight_legitimacy=0.6,
        weight_order=0.85,
        weight_control=0.7,
        weight_economy=0.5,
        risk_tolerance=0.5,
        paranoia=0.35,
        crackdown_threshold=0.5,
        soft_power_preference=0.35,
    ),
    "mil_zealot": AiPersonality(
        id="mil_zealot",
        role="mil_command",
        weight_survival=0.75,
        weight_legitimacy=0.3,
        weight_order=0.8,
        weight_control=0.85,
        weight_economy=0.35,
        risk_tolerance=0.7,
        paranoia=0.55,
        crackdown_threshold=0.35,
        soft_power_preference=0.15,
    ),
    "guild_shadow_profit": AiPersonality(
        id="guild_shadow_profit",
        role="guild_faction",
        weight_survival=0.65,
        weight_legitimacy=0.55,
        weight_order=0.5,
        weight_control=0.35,
        weight_economy=0.9,
        risk_tolerance=0.45,
        paranoia=0.5,
        crackdown_threshold=0.6,
        soft_power_preference=0.75,
    ),
    "cartel_expansionist": AiPersonality(
        id="cartel_expansionist",
        role="cartel",
        weight_survival=0.7,
        weight_legitimacy=0.2,
        weight_order=0.4,
        weight_control=0.5,
        weight_economy=0.85,
        risk_tolerance=0.8,
        paranoia=0.35,
        crackdown_threshold=0.45,
        soft_power_preference=0.3,
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
