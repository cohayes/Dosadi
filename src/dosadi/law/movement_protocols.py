from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FacilityProtocolTuning:
    facility_id: str

    # Queue discipline
    max_queue_length: int = 12  # [5, 20] recommended range

    # Presence / staffing (if guards/volunteers exist, else unused)
    min_guard_presence: int = 0  # [0, 3]

    # Information knobs
    post_protocol_summary: bool = False
    queue_status_board: bool = False

    # Simple cooldown in "days" to avoid thrash
    cooldown_until_day: int = 0
