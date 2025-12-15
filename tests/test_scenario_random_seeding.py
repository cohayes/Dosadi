"""Regression tests for deterministic scenario entrypoints seeding the global RNG."""

import random

from dosadi.runtime.founding_wakeup import run_founding_wakeup_mvp
from dosadi.runtime.wakeup_prime import run_wakeup_prime


def _next_random_after_run(run_func, *, pre_seed: int, **kwargs) -> float:
    """Return the next random draw after running a scenario with a disturbed RNG."""

    random.seed(pre_seed)
    random.random()  # disturb global RNG
    run_func(**kwargs)
    return random.random()


def test_run_wakeup_prime_seeds_global_rng() -> None:
    args = {
        "num_agents": 10,
        "max_ticks": 0,
        "seed": 7,
        "include_canteen": False,
        "include_hazard_spurs": False,
    }

    draw_one = _next_random_after_run(run_wakeup_prime, pre_seed=1, **args)
    draw_two = _next_random_after_run(run_wakeup_prime, pre_seed=2, **args)

    assert draw_one == draw_two


def test_run_founding_wakeup_seeds_global_rng() -> None:
    args = {
        "num_agents": 6,
        "max_ticks": 0,
        "seed": 11,
    }

    draw_one = _next_random_after_run(run_founding_wakeup_mvp, pre_seed=3, **args)
    draw_two = _next_random_after_run(run_founding_wakeup_mvp, pre_seed=4, **args)

    assert draw_one == draw_two

