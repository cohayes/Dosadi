"""Runtime configuration constants."""

PROMOTION_CHECK_INTERVAL_TICKS: int = 120_000  # ~one "day"
MIN_TICKS_BEFORE_PROMOTION: float = 200_000.0
MIN_PROFICIENCY_FOR_SUPERVISOR: float = 0.5
MIN_SHIFTS_FOR_SUPERVISOR: int = 10
MAX_SUPERVISORS_PER_WORK_TYPE: int = 3

SENIORITY_HORIZON: float = 400_000.0  # for normalizing total_ticks_employed
