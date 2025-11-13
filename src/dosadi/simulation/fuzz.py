"""Scenario fuzz harness used in CI and nightly runs."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from random import Random
from typing import Dict

from ..event import Event, EventPriority
from ..state import WorldState
from ..worldgen import WorldgenConfig, generate_world
from .engine import SimulationEngine


@dataclass(frozen=True)
class FuzzResult:
    """Summary of a fuzz harness execution."""

    ticks_run: int
    invariants: Dict[str, bool]
    emitted_events: int


@dataclass
class ScenarioFuzzHarness:
    """Generate stochastic worlds and ensure runtime invariants hold."""

    ticks: int = 12
    seed: int = 777

    def run(self) -> FuzzResult:
        rng = Random(self.seed)
        config = WorldgenConfig(
            seed=rng.randint(1, 1_000_000),
            ward_count=3,
            faction_count=2,
            agents_per_faction=2,
        )
        world = generate_world(config)
        engine = SimulationEngine(world)
        total_events = 0

        for _ in range(self.ticks):
            if rng.random() < 0.5:
                self._inject_random_event(engine, rng)
            engine.run(1)
            total_events += len(tuple(engine.bus.outbox))
            engine.bus.clear_outbox()
            invariants = self._evaluate_invariants(world)
            if not all(invariants.values()):
                raise AssertionError(f"Fuzz invariant failed: {invariants}")

        final_invariants = self._evaluate_invariants(world)
        return FuzzResult(
            ticks_run=self.ticks,
            invariants=final_invariants,
            emitted_events=total_events,
        )

    def _inject_random_event(self, engine: SimulationEngine, rng: Random) -> None:
        event = Event(
            id=f"fuzz:{engine.world.tick}:{rng.randint(0, 1_000_000)}",
            type=rng.choice(
                [
                    "FuzzMarketShock",
                    "FuzzRumorStorm",
                    "FuzzHealthCrisis",
                ]
            ),
            tick=engine.world.tick,
            ttl=rng.randint(0, 5),
            payload={"magnitude": rng.random(), "ward": rng.choice(list(engine.world.wards))},
            priority=rng.choice(list(EventPriority)),
        )
        engine.bus.publish(event)

    def _evaluate_invariants(self, world: WorldState) -> Dict[str, bool]:
        invariants: Dict[str, bool] = {}
        invariants["water_non_negative"] = all(
            ward.stocks.water_liters >= 0.0 for ward in world.wards.values()
        )
        invariants["biomass_non_negative"] = all(
            ward.stocks.biomass_kg >= 0.0 for ward in world.wards.values()
        )
        invariants["faction_assets_finite"] = all(
            isfinite(asset)
            for faction in world.factions.values()
            for asset in faction.assets.credits.values()
        )
        invariants["agent_health_finite"] = all(
            isfinite(agent.body.health) and isfinite(agent.body.stamina)
            for agent in world.agents.values()
        )
        invariants["rumor_bank_bounded"] = all(
            len(entries) <= 512
            for faction in world.factions.values()
            for entries in faction.rumor_bank.values()
        )
        return invariants


__all__ = ["FuzzResult", "ScenarioFuzzHarness"]
