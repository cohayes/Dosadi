from dosadi.simulation.scheduler import SimulationClock


def test_ticks_until_turn_boundary_handles_exact_boundary() -> None:
    clock = SimulationClock(current_tick=100)
    assert clock.ticks_until_turn_boundary() == 0


def test_ticks_until_turn_boundary_counts_remaining_ticks() -> None:
    clock = SimulationClock(current_tick=135)
    assert clock.ticks_until_turn_boundary() == 65


def test_ticks_until_cycle_boundary_handles_exact_boundary() -> None:
    clock = SimulationClock(ticks_per_cycle=1000, current_tick=2000)
    assert clock.ticks_until_cycle_boundary() == 0


def test_ticks_until_cycle_boundary_counts_remaining_ticks() -> None:
    clock = SimulationClock(ticks_per_cycle=1200, current_tick=250)
    assert clock.ticks_until_cycle_boundary() == 950
