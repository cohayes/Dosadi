"""Shared variable registry implementation.

The registry enumerates cross-system variables defined in
``docs/Dosadi_Shared_Variable_Registry_v1.md``.  Each entry records
metadata plus the current value.  Subsystems can update values through a
small API while preserving deterministic decay behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, MutableMapping


@dataclass(slots=True)
class VariableDefinition:
    name: str
    key: str
    units: str
    lower: float
    upper: float
    default: float
    decay: float
    notes: str


@dataclass
class VariableState:
    definition: VariableDefinition
    value: float

    def clamp(self) -> None:
        self.value = max(self.definition.lower, min(self.definition.upper, self.value))

    def decay_tick(self) -> None:
        if self.definition.decay == 1.0:
            return
        self.value *= self.definition.decay
        self.clamp()


class SharedVariableRegistry:
    """Runtime container for cross-system shared variables."""

    def __init__(self, definitions: Iterable[VariableDefinition]):
        self._variables: Dict[str, VariableState] = {
            definition.key: VariableState(definition, definition.default)
            for definition in definitions
        }

    def get(self, key: str) -> float:
        return self._variables[key].value

    def set(self, key: str, value: float) -> None:
        state = self._variables[key]
        state.value = value
        state.clamp()

    def decay_all(self) -> None:
        for state in self._variables.values():
            state.decay_tick()

    def items(self) -> Iterator[tuple[str, float]]:
        for key, state in self._variables.items():
            yield key, state.value


def default_registry() -> SharedVariableRegistry:
    """Return a registry populated with the v1 shared variables."""

    definitions = [
        VariableDefinition(
            name="Simulation Tick",
            key="tick",
            units="ticks",
            lower=0.0,
            upper=1e12,
            default=0.0,
            decay=1.0,
            notes="Global monotonic counter",
        ),
        VariableDefinition(
            name="Minute Index",
            key="t_min",
            units="minutes",
            lower=0.0,
            upper=1e9,
            default=0.0,
            decay=1.0,
            notes="⌊tick/100⌋",
        ),
        VariableDefinition(
            name="Day Index",
            key="t_day",
            units="days",
            lower=0.0,
            upper=1e7,
            default=0.0,
            decay=1.0,
            notes="rollover at cascade",
        ),
        VariableDefinition(
            name="Legitimacy",
            key="gov.L",
            units="idx",
            lower=0.0,
            upper=1.0,
            default=0.6,
            decay=0.999,
            notes="Faction legitimacy",
        ),
        VariableDefinition(
            name="Corruption",
            key="gov.C",
            units="idx",
            lower=0.0,
            upper=1.0,
            default=0.2,
            decay=0.998,
            notes="Faction corruption",
        ),
        VariableDefinition(
            name="Reliability",
            key="econ.R",
            units="idx",
            lower=0.0,
            upper=1.0,
            default=0.5,
            decay=0.99,
            notes="EWMA α=0.2",
        ),
        VariableDefinition(
            name="Environmental Stress",
            key="env.S",
            units="idx",
            lower=0.0,
            upper=100.0,
            default=10.0,
            decay=1.0,
            notes="Composite stress",
        ),
        VariableDefinition(
            name="Maintenance Index",
            key="infra.M",
            units="idx",
            lower=0.0,
            upper=1.0,
            default=0.8,
            decay=0.998,
            notes="Maintenance health",
        ),
        VariableDefinition(
            name="Rumor Credibility",
            key="rumor.Cred",
            units="idx",
            lower=0.0,
            upper=1.0,
            default=0.5,
            decay=0.97,
            notes="Agent rumor credibility",
        ),
        VariableDefinition(
            name="Memory Salience",
            key="mem.Sal",
            units="idx",
            lower=0.0,
            upper=1.0,
            default=0.2,
            decay=0.99,
            notes="Event salience",
        ),
    ]
    return SharedVariableRegistry(definitions)


__all__ = ["SharedVariableRegistry", "VariableDefinition", "default_registry"]

