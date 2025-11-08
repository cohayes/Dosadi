import pytest

from dosadi.simulation.scheduler import Phase, SimulationScheduler


def test_phase_order_execution():
    scheduler = SimulationScheduler()
    executed = []

    for phase in Phase.ordered():
        scheduler.register_handler(phase, lambda clock, phase=phase: executed.append(phase))

    scheduler.run(1)
    assert executed == list(Phase.ordered())


def test_delayed_event_runs_in_future_tick():
    scheduler = SimulationScheduler()
    executions = []

    def handler(clock):
        executions.append(clock.current_tick)

    scheduler.schedule_event(3, handler)
    scheduler.run(5)

    # The handler executes on tick 3 because the scheduler advances the clock
    # before processing the queue, meaning a delay of ``n`` ticks fires on the
    # nth tick after scheduling.
    assert executions == [3]


def test_time_dilation_defaults_and_overrides():
    scheduler = SimulationScheduler()

    assert scheduler.get_time_dilation("ward:alpha") == pytest.approx(1.0)

    scheduler.set_time_dilation("ward:alpha", 0.25)
    assert scheduler.get_time_dilation("ward:alpha") == pytest.approx(0.25)

    with pytest.raises(ValueError):
        scheduler.set_time_dilation("ward:alpha", 0)


def test_register_handler_invoked_each_tick():
    scheduler = SimulationScheduler()
    ticks = []

    def handler(clock):
        ticks.append(clock.current_tick)

    scheduler.register_handler(Phase.WELL_AND_KING, handler)
    scheduler.run(3)

    assert ticks == [1, 2, 3]
