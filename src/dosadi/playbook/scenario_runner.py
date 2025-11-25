"""Scenario registry and convenience runners.

The registry keeps a light-weight catalogue linking scenario IDs back to the
supporting documentation.  Tooling (CLI, notebooks, regression suites) can
reuse the helpers to discover the available playbooks, construct configs with
simple overrides, and invoke the deterministic runners.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from dataclasses import dataclass

from .sting_wave import StingWaveConfig, run_sting_wave_day3


@dataclass(frozen=True)
class ScenarioEntry:
    """Metadata describing a documented scenario."""

    name: str
    description: str
    doc_path: str
    config_type: type
    runner: Callable[[Any], Any]

    def build_config(self, overrides: Optional[Mapping[str, object]] = None) -> Any:
        if self.config_type is None:
            raise ValueError(f"Scenario '{self.name}' does not expose a config type")
        config = self.config_type()
        if overrides:
            for key, value in overrides.items():
                if not hasattr(config, key):
                    raise AttributeError(f"Config '{self.config_type.__name__}' has no field '{key}'")
                setattr(config, key, value)
        return config


_SCENARIO_REGISTRY: Dict[str, ScenarioEntry] = {}


def register_scenario(entry: ScenarioEntry) -> ScenarioEntry:
    if entry.name in _SCENARIO_REGISTRY:
        raise ValueError(f"Scenario '{entry.name}' is already registered")
    _SCENARIO_REGISTRY[entry.name] = entry
    return entry


def get_scenario_entry(name: str) -> ScenarioEntry:
    try:
        return _SCENARIO_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown scenario '{name}'") from exc


def available_scenarios() -> Sequence[ScenarioEntry]:
    return tuple(sorted(_SCENARIO_REGISTRY.values(), key=lambda entry: entry.name))


def run_scenario(
    name: str,
    *,
    config: Optional[Any] = None,
    overrides: Optional[Mapping[str, object]] = None,
) -> Any:
    entry = get_scenario_entry(name)
    if config is not None and overrides:
        raise ValueError("Pass either 'config' or 'overrides', not both")
    if config is None:
        config = entry.build_config(overrides)
    return entry.runner(config)


register_scenario(
    ScenarioEntry(
        name="sting_wave_day3",
        description="Sting Wave Day-3 infiltration w/ reserve + rumor KPIs",
        doc_path="docs/latest/11_scenarios/Dosadi_Scenario_Sting_Wave_Day3.md",
        config_type=StingWaveConfig,
        runner=lambda config: run_sting_wave_day3(config),
    )
)

@dataclass(slots=True)
class FoundingWakeupScenarioConfig:
    num_agents: int = 12
    max_ticks: int = 10_000
    seed: int = 1337


def _run_founding_wakeup(config: FoundingWakeupScenarioConfig):
    from ..runtime import founding_wakeup as fw

    if isinstance(config, dict):
        config = FoundingWakeupScenarioConfig(**config)
    return fw.run_founding_wakeup_mvp(
        num_agents=config.num_agents,
        max_ticks=config.max_ticks,
        seed=config.seed,
    )


register_scenario(
    ScenarioEntry(
        name="founding_wakeup_mvp",
        description="Founding wakeup MVP runtime wiring",
        doc_path="docs/latest/02_runtime/D-RUNTIME-0200_Founding_Wakeup_MVP_Runtime_v1-1-0.md",
        config_type=FoundingWakeupScenarioConfig,
        runner=lambda config: _run_founding_wakeup(config),
    )
)


__all__ = [
    "ScenarioEntry",
    "available_scenarios",
    "get_scenario_entry",
    "register_scenario",
    "run_scenario",
]
