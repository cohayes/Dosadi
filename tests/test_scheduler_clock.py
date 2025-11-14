from dosadi.simulation.scheduler import SimulationClock


def test_ticks_until_turn_boundary_returns_full_cadence_on_boundary() -> None:
    clock = SimulationClock(current_tick=200)
    assert clock.ticks_until_turn_boundary() == clock.ticks_per_turn


def test_ticks_until_turn_boundary_returns_full_cadence_at_origin() -> None:
    clock = SimulationClock()
    assert clock.ticks_until_turn_boundary() == clock.ticks_per_turn


def test_ticks_until_turn_boundary_counts_remaining_ticks() -> None:
    clock = SimulationClock(current_tick=135)
    assert clock.ticks_until_turn_boundary() == 65


def test_ticks_until_cycle_boundary_returns_full_cadence_on_boundary() -> None:
    clock = SimulationClock(ticks_per_cycle=1_000, current_tick=2_000)
    assert clock.ticks_until_cycle_boundary() == 1_000


def test_ticks_until_cycle_boundary_returns_full_cadence_at_origin() -> None:
    clock = SimulationClock(ticks_per_cycle=1_000)
    assert clock.ticks_until_cycle_boundary() == 1_000


def test_ticks_until_cycle_boundary_counts_remaining_ticks() -> None:
    clock = SimulationClock(ticks_per_cycle=1_200, current_tick=250)
    assert clock.ticks_until_cycle_boundary() == 950
