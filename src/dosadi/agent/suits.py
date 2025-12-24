"""Suit state representation for agents.

This module captures the minimal fields needed for suit wear and repair
flows described in D-RUNTIME-0254.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass(slots=True)
class SuitState:
    """Track the integrity and repair status of an agent's suit."""

    integrity: float = 1.0
    repair_needed: bool = False
    last_repair_day: int = 0
    notes: Dict[str, object] = field(default_factory=dict)
    seal_quality: float = 1.0
    filter_quality: float = 1.0

    def reset_flags(self) -> None:
        """Clear transient markers set during wear/repair flows."""

        for key in ("warn_emitted", "repair_emitted", "critical_emitted"):
            self.notes.pop(key, None)
