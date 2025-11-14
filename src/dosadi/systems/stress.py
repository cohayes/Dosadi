"""Agent stress reactivity aggregation system."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .base import SimulationSystem
from ..event import Event, EventPriority
from ..simulation.scheduler import Phase, SimulationClock
from ..state import AgentState


@dataclass
class StressSystem(SimulationSystem):
    """Aggregate agent stress and feed shared registry updates."""

    def __post_init__(self) -> None:  # type: ignore[override]
        super().__post_init__()
        self.register(Phase.SOCIAL_AUDIT, self.on_social_audit)

    def on_social_audit(self, clock: SimulationClock) -> None:
        """Blend stress factors once per cycle and publish audits."""

        if clock.current_tick % clock.ticks_per_cycle != 0:
            return
        agents = list(self.world.agents.values())
        if not agents:
            return
        stress_scores = []
        for agent in agents:
            stress = self._compute_agent_stress(agent)
            stress_scores.append(stress)
            self._apply_stress_consequences(agent, stress)
            self.bus.publish(
                Event(
                    id=f"stress:{agent.id}:{clock.current_tick}",
                    type="AgentStressAudit",
                    tick=clock.current_tick,
                    ttl=480,
                    payload={
                        "agent": agent.id,
                        "stress": stress,
                        "faction": agent.faction,
                    },
                    priority=EventPriority.NORMAL,
                    emitter="StressSystem",
                )
            )
        if stress_scores and self.registry is not None:
            self.registry.set("agent.stress_react", float(mean(stress_scores)))

    def _compute_agent_stress(self, agent: AgentState) -> float:
        mpb_overuse = max(0.0, 1.0 - agent.body.mental_energy / 100.0)
        suit_heat_rating = agent.suit.ratings.get("heat", 0.5)
        suit_strain = max(0.0, 1.0 - (suit_heat_rating + agent.suit.comfort) / 2.0)
        rumor_load = min(1.0, len(agent.memory.events) / 25.0)
        stress = 100.0 * (0.5 * mpb_overuse + 0.3 * suit_strain + 0.2 * rumor_load)
        return max(0.0, min(100.0, stress))

    def _apply_stress_consequences(self, agent: AgentState, stress: float) -> None:
        stamina_loss = stress * 0.05
        health_loss = stress * 0.02
        agent.body.stamina = max(0.0, agent.body.stamina - stamina_loss)
        agent.body.health = max(0.0, agent.body.health - health_loss)
        weights = dict(agent.drives.weights)
        survival = min(1.0, weights.get("Survival", 0.6) + stress / 150.0)
        hoard = max(0.05, weights.get("Hoard", 0.2) * (1.0 - stress / 250.0))
        advancement = max(0.05, weights.get("Advancement", 0.2) * (1.0 - stress / 220.0))
        total = survival + hoard + advancement
        agent.drives.weights["Survival"] = survival / total
        agent.drives.weights["Hoard"] = hoard / total
        agent.drives.weights["Advancement"] = advancement / total


__all__ = ["StressSystem"]
