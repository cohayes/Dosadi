from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from dosadi.runtime.work_details import WorkDetailType


@dataclass
class AdminLogEntry:
    log_id: str

    # Author and context
    author_agent_id: str
    work_type: WorkDetailType
    crew_id: Optional[str]

    tick_start: int
    tick_end: int

    # Aggregated metrics for this window
    metrics: Dict[str, float] = field(default_factory=dict)

    # Simple categorical flags (0.0 or 1.0 for now)
    flags: Dict[str, float] = field(default_factory=dict)

    # Optional short notes
    notes: Dict[str, str] = field(default_factory=dict)


def create_admin_log_id(world: "WorldState") -> str:
    seq = getattr(world, "next_admin_log_seq", 0)
    world.next_admin_log_seq = seq + 1
    return f"admin_log:{seq}"


__all__ = ["AdminLogEntry", "create_admin_log_id"]
