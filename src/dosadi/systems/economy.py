"""Economic subsystem covering credits, barrels, and conservation."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from collections import defaultdict

from collections import defaultdict

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..runtime.timebase import DAILY, Phase
from ..simulation.scheduler import SimulationClock


@dataclass
class EconomySystem(SimulationSystem):
    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.ACCOUNTING, self.on_accounting)

    def on_accounting(self, clock: SimulationClock) -> None:
        self.reseed(clock.current_tick)
        self._run_well(clock)
        self._run_factions(clock)

    def _run_well(self, clock: SimulationClock) -> None:
        if clock.current_tick % DAILY != 0:
            return
        wards = list(self.world.wards.values())
        if not wards:
            return
        total_bias = sum(1.0 / (ward.ring or 1) for ward in wards)
        allocation = 1000.0
        for ward in wards:
            share = allocation * (1.0 / (ward.ring or 1)) / total_bias
            ward.stocks.delta_water(share)
            self.bus.publish(
                Event(
                    id=f"barrel:{ward.id}:{clock.current_tick}",
                    type="BarrelCascadeIssued",
                    tick=clock.current_tick,
                    ttl=600,
                    payload={"ward": ward.id, "water": share},
                    priority=EventPriority.NORMAL,
                    emitter="EconomySystem",
                )
            )

    def _run_factions(self, clock: SimulationClock) -> None:
        pending = self.world.suit_service_ledger.drain_pending()
        costs: defaultdict[str, float] = defaultdict(float)
        deferred: defaultdict[str, int] = defaultdict(int)
        for entry in pending:
            costs[entry.faction_id] += entry.parts_cost
            if entry.deferred:
                deferred[entry.faction_id] += 1
        for faction in self.world.factions.values():
            legit = faction.metrics.gov.legitimacy
            corruption = faction.metrics.gov.corruption
            delta = (legit - corruption) * 0.001
            faction.assets.delta_credit(faction.id, max(0.0, delta))
            faction.metrics.econ.reliability = max(0.0, min(1.0, faction.metrics.econ.reliability * 0.99 + 0.01))
            work_order = costs.get(faction.id, 0.0)
            if work_order <= 0.0:
                continue
            balance = faction.assets.credits.get(faction.id, 0.0)
            if balance >= work_order:
                faction.assets.delta_credit(faction.id, -work_order)
            else:
                deficiency = work_order - balance
                faction.assets.delta_credit(faction.id, -balance)
                self.bus.publish(
                    Event(
                        id=f"maintenance:deferral:{faction.id}:{clock.current_tick}",
                        type="MaintenanceDeferralRisk",
                        tick=clock.current_tick,
                        ttl=480,
                        payload={
                            "faction": faction.id,
                            "deficiency": deficiency,
                            "orders": deferred.get(faction.id, 0),
                        },
                        priority=EventPriority.HIGH,
                        emitter="EconomySystem",
                    )
                )
                faction.metrics.econ.reliability = max(0.0, faction.metrics.econ.reliability - 0.01)

        if self.registry is not None and self.world.factions:
            avg_reliability = mean(
                faction.metrics.econ.reliability for faction in self.world.factions.values()
            )
            self.registry.set("econ.R", avg_reliability)


__all__ = ["EconomySystem"]

