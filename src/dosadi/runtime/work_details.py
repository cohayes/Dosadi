from __future__ import annotations

"""Work detail taxonomy for Founding Wakeup MVP (D-RUNTIME-0212)."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dosadi.agents.core import AgentState
    from dosadi.state import WorldState


class WorkDetailType(Enum):
    SCOUT_INTERIOR = auto()
    SCOUT_EXTERIOR = auto()
    INVENTORY_STORES = auto()
    STORES_STEWARD = auto()
    ENV_CONTROL = auto()
    ENV_CONTROL_DETAIL = ENV_CONTROL
    SUIT_INSPECTION_DETAIL = auto()
    FOOD_PROCESSING_DETAIL = auto()
    WATER_HANDLING_DETAIL = auto()
    SCRIBE_DETAIL = auto()
    DISPATCH_DETAIL = auto()
    FOOD_PROCESSING = FOOD_PROCESSING_DETAIL


@dataclass
class WorkDetailConfig:
    work_type: WorkDetailType
    category: str
    description: str
    preferred_attributes: Dict[str, int] = field(default_factory=dict)
    preferred_traits: List[str] = field(default_factory=list)
    risk_level: str = "medium"
    typical_verbs: List[str] = field(default_factory=list)
    macro_goals: List[str] = field(default_factory=list)
    default_team_size: int = 1
    typical_duration_ticks: int = 0


WORK_DETAIL_CATALOG: Dict[WorkDetailType, WorkDetailConfig] = {
    WorkDetailType.SCOUT_INTERIOR: WorkDetailConfig(
        work_type=WorkDetailType.SCOUT_INTERIOR,
        category="scout",
        description="Walk pods and corridors to map topology and bottlenecks.",
        preferred_attributes={"END": 1, "AGI": 1},
        preferred_traits=["curious", "moderate_bravery"],
        risk_level="medium",
        typical_verbs=["SCOUT_PLACE", "CORRIDOR_CROWDING_OBSERVED"],
        macro_goals=["MAP_INTERIOR", "STABILIZE_ENVIRONMENT"],
        default_team_size=1,
        typical_duration_ticks=10_000,
    ),
    WorkDetailType.SCOUT_EXTERIOR: WorkDetailConfig(
        work_type=WorkDetailType.SCOUT_EXTERIOR,
        category="scout",
        description="Short sorties outside to identify terrain and hazards.",
        preferred_attributes={"END": 2, "AGI": 1},
        preferred_traits=["brave", "curious"],
        risk_level="high",
        typical_verbs=["SCOUT_PLACE", "HAZARD_FOUND"],
        macro_goals=["MAP_EXTERIOR"],
        default_team_size=2,
        typical_duration_ticks=12_000,
    ),
    WorkDetailType.INVENTORY_STORES: WorkDetailConfig(
        work_type=WorkDetailType.INVENTORY_STORES,
        category="inventory",
        description="Open crates and tag critical supplies in stores.",
        preferred_attributes={"INT": 1, "END": 1},
        preferred_traits=["methodical", "calm"],
        risk_level="low",
        typical_verbs=["CRATE_OPENED", "STOCK_LOGGED"],
        macro_goals=["MAP_STORES", "STABILIZE_SUPPLY"],
        default_team_size=2,
        typical_duration_ticks=9_000,
    ),
    WorkDetailType.STORES_STEWARD: WorkDetailConfig(
        work_type=WorkDetailType.STORES_STEWARD,
        category="inventory",
        description="Keep the stores queue flowing and ration critical items.",
        preferred_attributes={"INT": 1, "CHA": 1},
        preferred_traits=["patient", "organizer"],
        risk_level="medium",
        typical_verbs=["ISSUE_RATIONS", "QUEUE_MANAGED"],
        macro_goals=["STABILIZE_SUPPLY"],
        default_team_size=1,
        typical_duration_ticks=8_000,
    ),
    WorkDetailType.ENV_CONTROL: WorkDetailConfig(
        work_type=WorkDetailType.ENV_CONTROL,
        category="infrastructure",
        description="Maintain interior comfort for a small set of places.",
        preferred_attributes={"INT": 1, "END": 1},
        preferred_traits=["careful", "mechanically_inclined"],
        risk_level="medium",
        typical_verbs=["ENV_NODE_TUNED"],
        macro_goals=["STABILIZE_ENVIRONMENT"],
        default_team_size=2,
        typical_duration_ticks=10_000,
    ),
    WorkDetailType.SUIT_INSPECTION_DETAIL: WorkDetailConfig(
        work_type=WorkDetailType.SUIT_INSPECTION_DETAIL,
        category="equipment",
        description="Inspect issued suits, seals, and telemetry tags.",
        preferred_attributes={"INT": 1, "PER": 1},
        preferred_traits=["careful", "procedural"],
        risk_level="medium",
        typical_verbs=["SUIT_INSPECTED", "SUIT_FLAGGED"],
        macro_goals=["KEEP_SUIT_READY"],
        default_team_size=1,
        typical_duration_ticks=7_500,
    ),
    WorkDetailType.FOOD_PROCESSING_DETAIL: WorkDetailConfig(
        work_type=WorkDetailType.FOOD_PROCESSING_DETAIL,
        category="sustenance",
        description="Process biomass into ration packs and track spoilage.",
        preferred_attributes={"END": 1, "INT": 1},
        preferred_traits=["steady", "collaborative"],
        risk_level="medium",
        typical_verbs=["FOOD_BATCH", "RATIONS_PACKED"],
        macro_goals=["MAINTAIN_FOOD"],
        default_team_size=3,
        typical_duration_ticks=9_500,
    ),
    WorkDetailType.WATER_HANDLING_DETAIL: WorkDetailConfig(
        work_type=WorkDetailType.WATER_HANDLING_DETAIL,
        category="sustenance",
        description="Monitor condensers, haul drums, and record flow rates.",
        preferred_attributes={"STR": 1, "INT": 1},
        preferred_traits=["steady", "careful"],
        risk_level="medium",
        typical_verbs=["CONDENSER_CHECK", "WATER_DRUM_FILLED"],
        macro_goals=["MAINTAIN_WATER"],
        default_team_size=2,
        typical_duration_ticks=9_000,
    ),
    WorkDetailType.SCRIBE_DETAIL: WorkDetailConfig(
        work_type=WorkDetailType.SCRIBE_DETAIL,
        category="information",
        description="Take notes on incidents, assignments, and council chatter.",
        preferred_attributes={"INT": 1},
        preferred_traits=["observant", "patient"],
        risk_level="low",
        typical_verbs=["NOTES_LOGGED", "REPORT_FILED"],
        macro_goals=["MAINTAIN_RECORDS", "SUPPORT_COUNCIL"],
        default_team_size=1,
        typical_duration_ticks=6_000,
    ),
    WorkDetailType.DISPATCH_DETAIL: WorkDetailConfig(
        work_type=WorkDetailType.DISPATCH_DETAIL,
        category="coordination",
        description="Relay assignments and runners between pods and hall.",
        preferred_attributes={"CHA": 1, "END": 1},
        preferred_traits=["communicative", "confident"],
        risk_level="medium",
        typical_verbs=["ASSIGNMENT_SENT", "RUNNER_DISPATCHED"],
        macro_goals=["COORDINATE_LABOR", "SUPPORT_COUNCIL"],
        default_team_size=1,
        typical_duration_ticks=7_500,
    ),
}


def choose_work_detail_for_agent(world: "WorldState", agent: "AgentState") -> Optional[WorkDetailType]:
    """
    MVP chooser: pick the work detail with the largest unmet demand.

    Later iterations can incorporate agent attributes and preferences.
    """

    best_type: Optional[WorkDetailType] = None
    best_gap = 0

    for work_type, desired in world.desired_work_details.items():
        active = world.active_work_details.get(work_type, 0)
        gap = desired - active
        if gap > best_gap:
            best_gap = gap
            best_type = work_type

    if best_type is not None:
        print(
            f"[work-detail] chosen {best_type.name} for agent {agent.agent_id} "
            f"(gap={best_gap})"
        )
    else:
        print(f"[work-detail] no gaps for agent {agent.agent_id}")

    return best_type

