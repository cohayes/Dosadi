from dosadi.simulation.fuzz import ScenarioFuzzHarness


def test_fuzz_harness_runs_and_preserves_invariants():
    harness = ScenarioFuzzHarness(ticks=4, seed=123)
    result = harness.run()
    assert result.ticks_run == 4
    assert all(result.invariants.values())
    assert result.emitted_events >= 0
