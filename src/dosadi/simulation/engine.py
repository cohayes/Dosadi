"""High level orchestration for the Dosadi simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from ..actions.base import ActionProcessor
from ..actions.verbs import register_default_verbs
from ..event import EventBus, TelemetrySnapshot
from ..registry import SharedVariableRegistry, default_registry
from ..state import WorldState
from ..systems import (
    EnvironmentSystem,
    EconomySystem,
    GovernanceSystem,
    LawSystem,
    MaintenanceSystem,
    RumorSystem,
)
from .scheduler import Phase, SimulationScheduler, TickMetrics
from .snapshots import DeltaSnapshot, Snapshot, SnapshotManager, TickJournal


@dataclass
class SimulationEngine:
    """Container wiring together the scheduler and subsystems."""

    world: WorldState
    scheduler: SimulationScheduler = field(default_factory=SimulationScheduler)
    bus: EventBus = field(default_factory=EventBus)
    registry: SharedVariableRegistry = field(default_factory=default_registry)

    def __post_init__(self) -> None:
        self.action_processor = ActionProcessor(self.world, self.bus)
        register_default_verbs(self.action_processor)
        self.systems = [
            EnvironmentSystem(self.world, self.bus, rng_seed=1),
            EconomySystem(self.world, self.bus, rng_seed=2),
            GovernanceSystem(self.world, self.bus, rng_seed=3),
            MaintenanceSystem(self.world, self.bus, rng_seed=4),
            RumorSystem(self.world, self.bus, rng_seed=5),
            LawSystem(self.world, self.bus, rng_seed=6),
        ]
        for system in self.systems:
            for phase, handler in system.phase_handlers().items():
                self.scheduler.register_handler(phase, handler)
        self.snapshot_manager = SnapshotManager()
        self.last_snapshot: Optional[Snapshot] = self.snapshot_manager.prime(
            self.world.to_snapshot(), self.world.tick
        )
        self.last_journal: Optional[TickJournal] = None
        self.last_delta: Optional[DeltaSnapshot] = None

    def run(self, ticks: int) -> None:
        for _ in range(ticks):
            self.scheduler.run_tick()
            metrics = self.scheduler.last_tick_metrics()
            self.world.advance_tick()
            self.registry.set("tick", float(self.world.tick))
            self.registry.set("t_min", float(self.world.minute))
            self.registry.set("t_day", float(self.world.day))
            self.registry.decay_all()
            self.action_processor.run(self.world.tick)
            self.bus.dispatch()
            self._emit_telemetry(metrics)
            journal, artifact = self.snapshot_manager.capture_tick(
                self.world.to_snapshot(), self.world.tick
            )
            self.last_journal = journal
            if isinstance(artifact, Snapshot):
                self.last_snapshot = artifact
                self.last_delta = None
            else:
                self.last_delta = artifact

    def _emit_telemetry(self, metrics: Optional[TickMetrics]) -> None:
        """Emit structured telemetry for the tick via the event bus."""

        snapshot = TelemetrySnapshot(tick=self.world.tick)
        if metrics is not None:
            phase_latency: Dict[str, float] = {}
            handler_latency: Dict[str, float] = {}
            for phase_metrics in metrics.phases:
                if phase_metrics.handlers:
                    avg = sum(h.duration_ms for h in phase_metrics.handlers) / len(
                        phase_metrics.handlers
                    )
                else:
                    avg = 0.0
                phase_latency[phase_metrics.phase.name] = avg
                for handler in phase_metrics.handlers:
                    key = f"{phase_metrics.phase.name}.{handler.name}"
                    handler_latency[key] = handler.duration_ms
            snapshot.phase_latency_ms = phase_latency
            snapshot.handler_latency_ms = handler_latency
        self.bus.emit_telemetry(snapshot)


__all__ = ["SimulationEngine"]

