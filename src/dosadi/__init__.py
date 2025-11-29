"""Dosadi simulation package public façade (Founding Wakeup MVP focused)."""

from .admin_log import AdminEventLog
from .documents import (
    DocBlock,
    DocCatalog,
    load_industry_catalog,
    load_info_security_catalog,
    load_military_catalog,
)
from .event import Event, EventBus, EventPriority
from .playbook.scenario_runner import ScenarioEntry, available_scenarios, run_scenario
from .playbook.scenario_validation import (
    ScenarioValidationIssue,
    ScenarioValidationResult,
    verify_scenario,
)
from .registry import SharedVariableRegistry, default_registry
from .state import WorldConfig, WorldState, day_tick, minute_tick

__all__ = [
    "AdminEventLog",
    "DocBlock",
    "DocCatalog",
    "Event",
    "EventBus",
    "EventPriority",
    "ScenarioEntry",
    "ScenarioValidationIssue",
    "ScenarioValidationResult",
    "SharedVariableRegistry",
    "WorldConfig",
    "WorldState",
    "available_scenarios",
    "day_tick",
    "default_registry",
    "load_industry_catalog",
    "load_info_security_catalog",
    "load_military_catalog",
    "minute_tick",
    "run_scenario",
    "verify_scenario",
]
