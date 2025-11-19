"""Sting Wave Day-3 scenario harness.

The implementation follows the instrumentation requests outlined in
``docs/latest/11_scenarios/Dosadi_Scenario_Sting_Wave_Day3.md``.  Rather than
attempting to simulate the entire smuggler economy, the harness produces a
deterministic, multi-phase report with the KPIs needed for regression tests and
UI previews.  It manipulates the canonical :class:`~dosadi.state.WorldState`
and emits :class:`~dosadi.event.Event` records that mirror the taxonomy names in
the document so downstream tooling (dashboards, notebooks, scenario sweeps) can
assert on them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import itertools
import random
from typing import Dict, List, MutableMapping, Optional, Sequence

from ..event import Event, EventBus, EventPriority
from ..state import AgentState, WorldState
from ..worldgen import WorldgenConfig, generate_world


# ---------------------------------------------------------------------------
# Scenario data classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class StingWaveConfig:
    world_seed: int = 1337
    scenario_seed: int = 1337
    sting_injection_rate: float = 0.08
    escort_mismatch_penalty: float = 0.18
    min_evidence_witness: int = 2
    crackdown_wave_size: int = 2
    reserve_floor: float = 0.25
    reserve_ratios: MutableMapping[str, float] = field(
        default_factory=lambda: {"king": 0.62, "dukeA": 0.31, "ward12": 0.26}
    )
    lane_ids: Sequence[str] = (
        "L-M12-OUTER-03",
        "L-M07-MIDDLE-11",
    )


@dataclass(slots=True)
class StingWavePhaseResult:
    key: str
    description: str
    events: List[Event]
    metrics: Dict[str, object]


@dataclass(slots=True)
class StingWaveReport:
    config: StingWaveConfig
    world: WorldState
    phases: List[StingWavePhaseResult]
    events: List[Event]
    kpis: Dict[str, float]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class _StingWaveRunner:
    def __init__(self, config: StingWaveConfig):
        self.config = config
        self.bus = EventBus()
        self.world = self._build_world()
        self._event_counter = itertools.count(1)
        self._rng = random.Random(config.scenario_seed)
        self.phases: List[StingWavePhaseResult] = []
        self.events: List[Event] = []
        self.kpis: Dict[str, float] = {}
        self.rumor_heat: Dict[str, float] = {
            "L-M12-OUTER-03": 0.35,
            "L-M07-MIDDLE-11": 0.12,
        }
        self.reserve_ratios: Dict[str, float] = dict(config.reserve_ratios)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> StingWaveReport:
        self._phase_initial_conditions()
        self._phase_listing()
        self._phase_route_planning()
        self._phase_escrow_handoff()
        self._phase_sting_injection()
        self._phase_movement()
        self._phase_crackdown()
        self._phase_audit()
        self._phase_fx_feedback()
        self._phase_rumor_feedback()
        self._finalize_kpis()
        return StingWaveReport(
            config=self.config,
            world=self.world,
            phases=self.phases,
            events=list(self.events),
            kpis=dict(self.kpis),
        )

    # ------------------------------------------------------------------
    # Phase helpers
    # ------------------------------------------------------------------
    def _phase_initial_conditions(self) -> None:
        metrics = {
            "reserve_king": self.reserve_ratios["king"],
            "reserve_dukeA": self.reserve_ratios["dukeA"],
            "reserve_ward12": self.reserve_ratios["ward12"],
            "sting_injection_rate": self.config.sting_injection_rate,
            "escort_mismatch_penalty": self.config.escort_mismatch_penalty,
        }
        self._record_phase("0", "Initial conditions", [], metrics)

    def _phase_listing(self) -> None:
        events = [
            self._emit(
                "ListingPosted",
                {
                    "node_id": "N-BackAlley-W12",
                    "commodity": "forged_permits",
                    "quantity": 12,
                    "reserve_liters": 40,
                },
            ),
            self._emit(
                "ListingMirrored",
                {
                    "node_ids": ["N-BackAlley-W12", "N-RepairDen-W07"],
                    "privacy": "DARK_ESCROW",
                },
            ),
        ]
        metrics = {
            "listings": 1,
            "escrowed_value_l": 480.0,
        }
        self._record_phase("A", "Anonymous listing posted", events, metrics)

    def _phase_route_planning(self) -> None:
        events = [
            self._emit(
                "DarkRoutePlanned",
                {
                    "lane_id": "L-M12-OUTER-03",
                    "safehouses": ["SH-D-Stonecut", "SH-D-RedVane"],
                    "escort": "Op-GreyJackal",
                },
            ),
            self._emit(
                "StagingBooked",
                {"safehouses": 2, "broker": "B-Whisper"},
            ),
        ]
        metrics = {"safehouse_slots": 2, "escort_risk": 0.18}
        self._record_phase("B", "Broker match & routing", events, metrics)

    def _phase_escrow_handoff(self) -> None:
        events = [
            self._emit(
                "OrderPlaced",
                {
                    "escrow_id": "escrow:forged-771",
                    "currency": "dukeA",
                    "value_liters": 480.0,
                },
            ),
            self._emit(
                "HandoffCompleted",
                {
                    "node_id": "N-BackAlley-W12",
                    "ritual": "seal-tree",
                },
            ),
        ]
        metrics = {"escrow_dukeA": 480.0, "custody": "FACTION_SEALED"}
        self._record_phase("C", "Escrow funded and handoff", events, metrics)

    def _phase_sting_injection(self) -> None:
        events = []
        for commodity in ("meds_high", "forged_permits"):
            events.append(
                self._emit(
                    "StingInjected",
                    {
                        "node_id": "N-RepairDen-W07",
                        "commodity": commodity,
                        "arbiter_panel": "AP-North",
                    },
                )
            )
        metrics = {
            "decoys": 2,
            "sting_budget": self.config.crackdown_wave_size,
        }
        self._record_phase("D", "Decoy sting injected", events, metrics)

    def _phase_movement(self) -> None:
        ambush_roll = self._rng.random()
        ambush_triggered = ambush_roll < 0.35
        loss_rate = 0.18 if ambush_triggered else 0.0
        events = [
            self._emit(
                "ConvoyDispatched",
                {"operator": "Op-GreyJackal", "lane_id": "L-M12-OUTER-03"},
            ),
            self._emit(
                "AmbushAttempted",
                {
                    "lane_id": "L-M12-OUTER-03",
                    "success": ambush_triggered,
                    "loss_rate": loss_rate,
                },
            ),
        ]
        if ambush_triggered:
            events.append(
                self._emit(
                    "ClinicIntake",
                    {
                        "ward": "ward:12",
                        "severity": "MODERATE",
                        "cases": 2,
                    },
                )
            )
        metrics = {
            "ambush_triggered": ambush_triggered,
            "loss_rate": loss_rate,
            "clinic_cases": 2 if ambush_triggered else 0,
        }
        self._record_phase("E", "Movement & encounter", events, metrics)

    def _phase_crackdown(self) -> None:
        events = [
            self._emit(
                "InspectionOccurred",
                {"lane_id": "L-M07-MIDDLE-11", "checkpoint": True},
            ),
            self._emit(
                "CrackdownExecuted",
                {
                    "node_id": "N-RepairDen-W07",
                    "closures_hours": 24,
                    "seizures": {
                        "forged_permits": 8,
                        "weapons": 2,
                    },
                },
            ),
        ]
        metrics = {"closures": 24, "seized_permits": 8}
        self._record_phase("F", "Checkpoint sting & crackdown", events, metrics)

    def _phase_audit(self) -> None:
        events = [
            self._emit(
                "AuditOpened",
                {"entity": "Op-GreyJackal", "scope": "forged_permits_wave"},
            ),
            self._emit(
                "ArbiterDecree",
                {
                    "panel": "AP-North",
                    "penalties": ["fines", "license_revocation"],
                },
            ),
            self._emit(
                "LicenseRevoked",
                {"agent": "Op-GreyJackal", "permit": "carry:HEAVY_WEAPON"},
            ),
        ]
        metrics = {"decrees": 1, "revocations": 1}
        self._record_phase("G", "Audit and decrees", events, metrics)

    def _phase_fx_feedback(self) -> None:
        self.reserve_ratios["dukeA"] -= 0.04
        self.reserve_ratios["ward12"] -= 0.01
        events = [
            self._emit(
                "FXMarked",
                {"issuer": "dukeA", "spread_bps": 40},
            ),
            self._emit(
                "ReserveBreachCheck",
                {"issuer": "ward12", "reserve": self.reserve_ratios["ward12"]},
            ),
        ]
        metrics = {
            "reserve_dukeA": self.reserve_ratios["dukeA"],
            "reserve_ward12": self.reserve_ratios["ward12"],
        }
        self._record_phase("H", "FX & reserve feedback", events, metrics)

    def _phase_rumor_feedback(self) -> None:
        self.rumor_heat["L-M12-OUTER-03"] += 0.2
        self.rumor_heat["L-M07-MIDDLE-11"] += 0.05
        events = [
            self._emit(
                "RumorHeatUpdated",
                {
                    "lane_id": "L-M12-OUTER-03",
                    "delta": 0.2,
                },
            ),
            self._emit(
                "ListingsMigrated",
                {
                    "from_node": "N-RepairDen-W07",
                    "to_nodes": ["N-BackAlley-W12"],
                    "commodities": ["data_wipes", "intel"],
                },
            ),
        ]
        metrics = {
            "heat_outer": self.rumor_heat["L-M12-OUTER-03"],
            "heat_middle": self.rumor_heat["L-M07-MIDDLE-11"],
        }
        self._record_phase("I", "Rumor & migration feedback", events, metrics)

    def _finalize_kpis(self) -> None:
        bust_rate = 1.0  # crackdown succeeded against forged permits
        reserve_floor = min(self.reserve_ratios.values())
        heat_peak = max(self.rumor_heat.values())
        self.kpis = {
            "bust_rate": bust_rate,
            "reserve_floor": reserve_floor,
            "heat_peak": heat_peak,
        }

    # ------------------------------------------------------------------
    # World helpers
    # ------------------------------------------------------------------
    def _build_world(self) -> WorldState:
        config = WorldgenConfig.minimal(seed=self.config.world_seed, wards=12)
        config.enable_agents = True
        config.agent_roll = type(config.agent_roll)(8, 12)
        world = generate_world(config)
        world.policy.setdefault("black_market", {})["sting_injection_rate"] = self.config.sting_injection_rate
        world.policy.setdefault("logistics", {})["escort_mismatch_penalty"] = self.config.escort_mismatch_penalty
        world.policy.setdefault("telemetry_audit", {})[
            "min_evidence_for_decree.WITNESS"
        ] = self.config.min_evidence_witness
        self._annotate_key_actors(world)
        return world

    def _annotate_key_actors(self, world: WorldState) -> None:
        key_pairs = [
            ("agent:broker", "B-Whisper", "faction:broker", "ward:12", "CLEARANCE_CIVIC"),
            ("agent:operator", "Op-GreyJackal", "faction:crew", "ward:12", "CLEARANCE_OUTER"),
            ("agent:fence", "F-CopperLoom", "faction:fence", "ward:7", "CLEARANCE_MIDDLE"),
        ]
        for agent_id, handle, faction_id, ward_id, clearance in key_pairs:
            agent = world.agents.get(agent_id)
            if not agent:
                agent = AgentState(
                    id=agent_id,
                    name=handle,
                    faction=faction_id,
                    ward=ward_id,
                    role="SCENARIO",
                )
                world.register_agent(agent)
            agent.identity.add_handle(handle)
            agent.identity.clearance_level = clearance
            agent.identity.issue_permit(
                permit_id=f"permit:{agent_id}",
                kind="carry:HEAVY_WEAPON" if "operator" in agent_id else "brokerage",
                issued_by="AP-North",
                issued_tick=world.tick,
            )
            agent.identity.set_trust_flag("sting_watchlist", 0.75)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _emit(
        self,
        event_type: str,
        payload: MutableMapping[str, object],
        *,
        ward: Optional[str] = None,
        actors: Optional[Sequence[str]] = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> Event:
        event = Event(
            id=f"sting:{next(self._event_counter)}",
            type=event_type,
            tick=self.world.tick,
            ttl=10,
            payload=dict(payload),
            ward=ward,
            actors=list(actors or []),
            emitter="sting_wave",
            priority=priority,
        )
        self.bus.publish(event)
        self.events.append(event)
        return event

    def _record_phase(
        self,
        key: str,
        description: str,
        events: Sequence[Event],
        metrics: Dict[str, object],
    ) -> None:
        self.phases.append(
            StingWavePhaseResult(
                key=key,
                description=description,
                events=list(events),
                metrics=dict(metrics),
            )
        )


def run_sting_wave_day3(config: Optional[StingWaveConfig] = None) -> StingWaveReport:
    runner = _StingWaveRunner(config or StingWaveConfig())
    return runner.run()


__all__ = [
    "StingWaveConfig",
    "StingWavePhaseResult",
    "StingWaveReport",
    "run_sting_wave_day3",
]
