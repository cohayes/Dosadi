"""Shared physiology helpers for physical state, stress, and performance."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type hints only to avoid circular import
    from dosadi.agents.core import PhysicalState

# Hunger and hydration comfort bounds
HUNGER_COMFORT_THRESHOLD: float = 0.3
HUNGER_MAX: float = 2.0
HYDRATION_COMFORT_LEVEL: float = 0.9

BASE_STRESS_TARGET: float = 0.2
BASE_MORALE_TARGET: float = 0.6

STRESS_RELAX_RATE: float = 1.0 / 100_000.0
MORALE_RELAX_RATE: float = 1.0 / 100_000.0

STRESS_NEEDS_RATE: float = 1.0 / 20_000.0
MORALE_NEEDS_RATE: float = 1.0 / 20_000.0

SLEEP_BASE_ACCUM_PER_TICK: float = 1.0 / 120_000.0
SLEEP_HUNGER_MODIFIER: float = 0.2
SLEEP_STRESS_MODIFIER: float = 0.3

SLEEP_RECOVERY_RATE: float = 1.0 / 40_000.0


def compute_needs_pressure(physical: PhysicalState) -> float:
    """Compute combined pressure from hunger and hydration shortfalls."""

    hunger_component = 0.0
    if physical.hunger_level > HUNGER_COMFORT_THRESHOLD:
        denom = max(1e-6, HUNGER_MAX - HUNGER_COMFORT_THRESHOLD)
        hunger_component = (physical.hunger_level - HUNGER_COMFORT_THRESHOLD) / denom
        if hunger_component > 1.0:
            hunger_component = 1.0

    hydration_component = 0.0
    if physical.hydration_level < HYDRATION_COMFORT_LEVEL:
        hydration_component = (
            (HYDRATION_COMFORT_LEVEL - physical.hydration_level) / HYDRATION_COMFORT_LEVEL
        )
        if hydration_component > 1.0:
            hydration_component = 1.0

    return 0.6 * hunger_component + 0.4 * hydration_component


def update_stress_and_morale(physical: PhysicalState, needs_pressure: float) -> None:
    """Update stress and morale based on baseline drift and needs pressure."""

    physical.stress_level += (BASE_STRESS_TARGET - physical.stress_level) * STRESS_RELAX_RATE
    physical.morale_level += (BASE_MORALE_TARGET - physical.morale_level) * MORALE_RELAX_RATE

    physical.stress_level += needs_pressure * STRESS_NEEDS_RATE
    physical.morale_level -= needs_pressure * MORALE_NEEDS_RATE

    if physical.stress_level < 0.0:
        physical.stress_level = 0.0
    elif physical.stress_level > 1.0:
        physical.stress_level = 1.0

    if physical.morale_level < 0.0:
        physical.morale_level = 0.0
    elif physical.morale_level > 1.0:
        physical.morale_level = 1.0


def compute_performance_multiplier(physical: PhysicalState) -> float:
    """Compute performance multiplier derived from stress and morale."""

    stress = physical.stress_level
    morale = physical.morale_level

    multiplier = 1.0
    multiplier *= 1.0 - 0.3 * stress

    morale_delta = morale - 0.5
    multiplier *= 1.0 + 0.2 * morale_delta

    if multiplier < 0.4:
        multiplier = 0.4
    elif multiplier > 1.2:
        multiplier = 1.2

    return multiplier


def accumulate_sleep_pressure(physical: PhysicalState) -> None:
    if physical.is_sleeping:
        return

    base = SLEEP_BASE_ACCUM_PER_TICK
    extra = (
        SLEEP_HUNGER_MODIFIER * max(0.0, physical.hunger_level)
        + SLEEP_STRESS_MODIFIER * max(0.0, physical.stress_level)
    )
    physical.sleep_pressure += base + extra * SLEEP_BASE_ACCUM_PER_TICK
    if physical.sleep_pressure > 1.0:
        physical.sleep_pressure = 1.0


def recover_sleep_pressure(physical: PhysicalState) -> None:
    if not physical.is_sleeping:
        return

    physical.sleep_pressure -= SLEEP_RECOVERY_RATE
    if physical.sleep_pressure < 0.0:
        physical.sleep_pressure = 0.0
