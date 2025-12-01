from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MemoryConfig:
    """
    Cadence and capacity hints for episodic memory maintenance.
    Tick counts are expressed in global simulation ticks, using
    the Timebase (D-RUNTIME-0001).

    Defaults are MVP-friendly and can be overridden per scenario.
    """

    # Short-term maintenance cadence (≈ every 10 minutes)
    short_term_maintenance_interval_ticks: int = 1_000

    # Daily promotion cadence (≈ every 4 hours)
    daily_promotion_interval_ticks: int = 24_000

    # Approximate personal wake/sleep durations (per agent)
    wake_duration_ticks: int = 96_000    # ≈ 16 hours
    sleep_duration_ticks: int = 48_000   # ≈ 8 hours

    # Minimum interval between full consolidations (per agent)
    min_consolidation_interval_ticks: int = 120_000  # ≈ 20–24 hours
