"""Scenario registry and convenience runners.

The registry keeps a light-weight catalogue linking scenario IDs back to the
supporting documentation.  Tooling (CLI, notebooks, regression suites) can
reuse the helpers to discover the available playbooks, construct configs with
simple overrides, and invoke the deterministic runners.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence


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

@dataclass(slots=True)
class FoundingWakeupScenarioConfig:
    num_agents: int = 12
    max_ticks: int = 10_000
    seed: int = 1337


@dataclass(slots=True)
class WakeupPrimeScenarioConfig:
    num_agents: int = 240
    seed: int = 1337
    include_canteen: bool = True
    include_hazard_spurs: bool = True
    max_ticks: int = 10_000
    basic_suit_stock: int | None = None


def _run_founding_wakeup(config: FoundingWakeupScenarioConfig):
    from ..runtime.founding_wakeup import run_founding_wakeup_mvp

    return run_founding_wakeup_mvp(
        num_agents=config.num_agents,
        max_ticks=config.max_ticks,
        seed=config.seed,
    )


def _run_wakeup_prime(config: WakeupPrimeScenarioConfig):
    from ..runtime.wakeup_prime import run_wakeup_prime

    if isinstance(config, dict):
        config = WakeupPrimeScenarioConfig(**config)
    return run_wakeup_prime(
        num_agents=config.num_agents,
        max_ticks=config.max_ticks,
        seed=config.seed,
        include_canteen=config.include_canteen,
        include_hazard_spurs=config.include_hazard_spurs,
        basic_suit_stock=config.basic_suit_stock,
    )


register_scenario(
    ScenarioEntry(
        name="founding_wakeup_mvp",
        description="Founding wakeup MVP: pods, proto-council, movement protocol",
        doc_path="docs/latest/11_scenarios/D-SCEN-0002_Founding_Wakeup_MVP_Scenario.md",
        config_type=FoundingWakeupScenarioConfig,
        runner=lambda config: _run_founding_wakeup(config),
    )
)

register_scenario(
    ScenarioEntry(
        name="wakeup_prime",
        description="Wakeup Scenario Prime",
        doc_path="docs/latest/11_scenarios/D-SCEN-0001_Wakeup_Scenario_Prime_v0.md",
        config_type=WakeupPrimeScenarioConfig,
        runner=lambda config: _run_wakeup_prime(config),
    )
)


__all__ = [
    "ScenarioEntry",
    "available_scenarios",
    "get_scenario_entry",
    "WakeupPrimeScenarioConfig",
    "register_scenario",
    "run_scenario",
]
