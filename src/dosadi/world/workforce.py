from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class AssignmentKind(Enum):
    IDLE = "idle"
    PROJECT_WORK = "project_work"
    FACILITY_STAFF = "facility_staff"
    SCOUT_MISSION = "scout_mission"
    LOGISTICS_COURIER = "logistics_courier"
    LOGISTICS_ESCORT = "logistics_escort"


@dataclass(slots=True)
class Assignment:
    agent_id: str
    kind: AssignmentKind
    target_id: str | None
    start_day: int
    end_day: int | None = None
    notes: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class WorkforceLedger:
    assignments: Dict[str, Assignment] = field(default_factory=dict)

    def get(self, agent_id: str) -> Assignment:
        assignment = self.assignments.get(agent_id)
        if assignment is None:
            assignment = Assignment(
                agent_id=agent_id,
                kind=AssignmentKind.IDLE,
                target_id=None,
                start_day=0,
            )
            self.assignments[agent_id] = assignment
        return assignment

    def is_idle(self, agent_id: str) -> bool:
        return self.get(agent_id).kind is AssignmentKind.IDLE

    def assign(self, assignment: Assignment) -> None:
        current = self.assignments.get(assignment.agent_id)
        if current is not None and current.kind is not AssignmentKind.IDLE:
            raise ValueError(f"Agent {assignment.agent_id} already assigned to {current.kind.name}")
        self.assignments[assignment.agent_id] = assignment

    def unassign(self, agent_id: str) -> None:
        prior = self.assignments.get(
            agent_id,
            Assignment(
                agent_id=agent_id,
                kind=AssignmentKind.IDLE,
                target_id=None,
                start_day=0,
            ),
        )
        self.assignments[agent_id] = Assignment(
            agent_id=agent_id,
            kind=AssignmentKind.IDLE,
            target_id=None,
            start_day=prior.start_day,
        )

    def signature(self) -> str:
        """Return a deterministic signature of current assignments."""

        parts = []
        for agent_id, assignment in sorted(self.assignments.items(), key=lambda item: item[0]):
            if assignment.kind is AssignmentKind.IDLE:
                continue
            notes_blob = ",".join(
                f"{key}={value}" for key, value in sorted(assignment.notes.items())
            )
            end_day = assignment.end_day if assignment.end_day is not None else "-"
            target = assignment.target_id if assignment.target_id is not None else "-"
            parts.append(
                f"{agent_id}:{assignment.kind.name}:{target}:{assignment.start_day}:{end_day}:{notes_blob}"
            )
        return "|".join(parts)


def ensure_workforce(world) -> WorkforceLedger:
    ledger = getattr(world, "workforce", None)
    if isinstance(ledger, WorkforceLedger):
        return ledger

    ledger = WorkforceLedger()
    setattr(world, "workforce", ledger)
    return ledger


__all__ = [
    "Assignment",
    "AssignmentKind",
    "WorkforceLedger",
    "ensure_workforce",
]
