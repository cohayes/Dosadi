"""Dosadi simulation package public façade."""

from .admin_log import AdminEventLog
from .event import Event, EventBus, EventPriority
from .interfaces.admin_debug import (
    AdminDebugView,
    AgentDebugSnapshot,
    WardSnapshot,
    WardSummary,
    WorldSnapshot,
    snapshot_agent_debug,
    snapshot_ward,
    snapshot_world_state,
)
from .interfaces.campaign_dashboard import CampaignDashboardCLI
from .interfaces.cli_dashboard import AdminDashboardCLI, ScenarioTimelineCLI
from .playbook.day0 import Day0Config, Day0Report, Day0StepResult, run_day0_playbook
from .playbook.scenario_runner import ScenarioEntry, available_scenarios, run_scenario
from .playbook.scenario_validation import (
    ScenarioValidationIssue,
    ScenarioValidationResult,
    verify_scenario,
)
from .playbook.sting_wave import (
    StingWaveConfig,
    StingWavePhaseResult,
    StingWaveReport,
    run_sting_wave_day3,
)
from .security.counterintelligence import CIPosture, CIState, InfiltrationAttempt, seed_default_ci_states
from .security.security_dashboard import (
    SignatureAssessment,
    WardSecuritySummary,
    assess_ci_signatures,
    summarize_ward_security,
)
from .documents import (
    DocBlock,
    DocCatalog,
    load_industry_catalog,
    load_info_security_catalog,
    load_military_catalog,
)
from .registry import SharedVariableRegistry, default_registry
from .runtime.campaign_engine import CampaignEngine, CampaignRunResult, CampaignState, ScenarioDefinition
from .simulation.engine import SimulationEngine
from .simulation.scheduler import Phase, SimulationClock, SimulationScheduler
from .state import WorldConfig, WorldState, day_tick, minute_tick

__all__ = [
    "CampaignDashboardCLI",
    "CampaignEngine",
    "CampaignRunResult",
    "CampaignState",
    "Day0Config",
    "Day0Report",
    "Day0StepResult",
    "DocBlock",
    "DocCatalog",
    "Event",
    "EventBus",
    "EventPriority",
    "AdminDebugView",
    "AdminDashboardCLI",
    "ScenarioEntry",
    "ScenarioTimelineCLI",
    "ScenarioValidationIssue",
    "ScenarioValidationResult",
    "AgentDebugSnapshot",
    "AdminEventLog",
    "Phase",
    "SharedVariableRegistry",
    "SimulationClock",
    "ScenarioDefinition",
    "SimulationEngine",
    "SimulationScheduler",
    "StingWaveConfig",
    "StingWavePhaseResult",
    "StingWaveReport",
    "WardSnapshot",
    "WardSummary",
    "WorldSnapshot",
    "WorldConfig",
    "WorldState",
    "day_tick",
    "default_registry",
    "snapshot_agent_debug",
    "snapshot_ward",
    "snapshot_world_state",
    "minute_tick",
    "run_day0_playbook",
    "run_scenario",
    "run_sting_wave_day3",
    "verify_scenario",
    "available_scenarios",
    "CIPosture",
    "CIState",
    "InfiltrationAttempt",
    "seed_default_ci_states",
    "SignatureAssessment",
    "WardSecuritySummary",
    "assess_ci_signatures",
    "summarize_ward_security",
    "load_industry_catalog",
    "load_info_security_catalog",
    "load_military_catalog",
]
