"""Implementation of the Day-0 dry-run playbook.

The script follows the deterministic walkthrough described in
``docs/Dosadi_Day0_Dry_Run_Playbook_v1.md``.  Rather than depending on the
general-purpose simulation scheduler, the playbook wires a purpose-built
runner that manipulates the shared :class:`~dosadi.state.WorldState`, emits
events on the canonical :class:`~dosadi.event.EventBus`, and records
snapshots plus assertions for every phase.

The result is a structured report that can be inspected by regression tests
or interactive notebooks.  Each step captures the emitted events and the key
metrics that justify the expectations stated in the playbook document.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import itertools
from typing import Dict, Iterable, List, MutableMapping, Optional, Tuple

from ..event import Event, EventBus, EventPriority
from ..registry import SharedVariableRegistry, default_registry
from ..state import (
    AgentState,
    ContractObligation,
    ContractState,
    FactionState,
    RouteState,
    WardState,
    WorldState,
)
from ..worldgen import WorldgenConfig, generate_world


# ---------------------------------------------------------------------------
# Configuration and reporting structures
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Day0Config:
    """Configuration extracted from the playbook document."""

    world_seed: int = 7719
    route_gate_density: float = 0.6
    tax_rate: float = 0.10
    market_alpha_ref: float = 0.7
    market_base_spread: float = 0.04
    min_wage_floor_by_venue: MutableMapping[str, float] = field(
        default_factory=lambda: {
            "CIVIC": 20.0,
            "GUILD": 30.0,
            "MERC": 35.0,
            "ROYAL": 50.0,
            "BLACK_NODE": 0.0,
        }
    )
    security_response_latency_target_min: int = 10
    clinic_esi_wait_threshold_min: MutableMapping[str, int] = field(
        default_factory=lambda: {"1": 1, "2": 10, "3": 30, "4": 90, "5": 180}
    )
    maint_warn_threshold: float = 0.35
    law_dispute_window_min: int = 720
    law_grace_min_default: int = 240
    focus_wards: Tuple[str, str, str, str] = ("ward:1", "ward:2", "ward:8", "ward:21")


@dataclass(slots=True)
class Day0StepResult:
    key: str
    description: str
    events: List[Event]
    metrics: Dict[str, object]


@dataclass(slots=True)
class Day0Report:
    config: Day0Config
    world: WorldState
    steps: List[Day0StepResult]
    snapshots: Dict[str, object]
    events: List[Event]


# ---------------------------------------------------------------------------
# Runner implementation
# ---------------------------------------------------------------------------


class _Day0Runner:
    def __init__(self, config: Day0Config):
        self.config = config
        self.bus = EventBus()
        self.registry: SharedVariableRegistry = default_registry()
        self.world = self._build_world()
        self._event_counter = itertools.count(1)
        self._current_tick = self.world.tick
        self.steps: List[Day0StepResult] = []
        self.snapshots: Dict[str, object] = {}

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------
    def _build_world(self) -> WorldState:
        world = generate_world(
            WorldgenConfig(seed=self.config.world_seed, ward_count=24, faction_count=8, agents_per_faction=8)
        )
        self._annotate_world(world)
        return world

    def _annotate_world(self, world: WorldState) -> None:
        focus = self.config.focus_wards
        w1 = world.wards[focus[0]]
        w2 = world.wards[focus[1]]
        w8 = world.wards[focus[2]]
        w21 = world.wards[focus[3]]

        w1.name = "Well"
        w1.facilities.update({"well": 1, "depot": 1, "barracks": 1})
        w1.legitimacy = 0.82

        w2.name = "Inner W2"
        w2.facilities.update({"kitchen": 2, "workshop": 1, "clinic": 1})
        w2.legitimacy = 0.74

        w8.name = "Middle W8"
        w8.facilities.update({"kitchen": 1, "reclaimer": 1, "bazaar": 1})
        w8.legitimacy = 0.62

        w21.name = "Outer W21"
        w21.facilities.update({"kitchen": 2, "workshop": 1, "queue": 1})
        w21.legitimacy = 0.48

        # Ensure the royal faction exists to receive royalties.
        if "faction:king" not in world.factions:
            king = FactionState(
                id="faction:king",
                name="Royal Treasury",
                archetype="ROYAL",
                home_ward=w1.id,
            )
            king.assets.credits["king-credit"] = 12_000.0
            world.register_faction(king)
        world.wards[w1.id].governor_faction = "faction:king"

        # Wire explicit routes from the Well to the focus wards.
        routes = [
            RouteState(
                id="route:well-w2",
                origin=w1.id,
                destination=w2.id,
                distance_km=4.5,
                risk=0.08,
                surcharge=0.05,
            ),
            RouteState(
                id="route:well-w8",
                origin=w1.id,
                destination=w8.id,
                distance_km=9.0,
                risk=0.12,
                surcharge=0.09,
            ),
            RouteState(
                id="route:well-w21",
                origin=w1.id,
                destination=w21.id,
                distance_km=14.0,
                risk=0.18,
                surcharge=0.16,
            ),
        ]
        for route in routes:
            world.register_route(route)

    def _emit(
        self,
        event_type: str,
        payload: Dict[str, object],
        *,
        ward: Optional[str] = None,
        actors: Optional[Iterable[str]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        ttl: int = 10,
    ) -> Event:
        event = Event(
            id=f"day0-{next(self._event_counter)}",
            type=event_type,
            tick=self._current_tick,
            ttl=ttl,
            payload=dict(payload),
            ward=ward,
            actors=list(actors or ()),
            emitter="day0.playbook",
            priority=priority,
        )
        self.bus.publish(event)
        return event

    def _advance_time(self, minutes: float) -> None:
        ticks = int(minutes * 100)
        for _ in range(ticks):
            self.world.advance_tick()
        self._current_tick = self.world.tick

    def _run_step(self, key: str, description: str, fn) -> None:
        start_len = len(tuple(self.bus.outbox))
        metrics = fn()
        # Deliver events (no subscribers yet, but keeps the queue tidy).
        self.bus.dispatch()
        events = list(self.bus.outbox)[start_len:]
        self.steps.append(Day0StepResult(key=key, description=description, events=events, metrics=metrics))

    # ------------------------------------------------------------------
    # Scenario steps
    # ------------------------------------------------------------------
    def run(self) -> Day0Report:
        self._run_step("1", "Boot & Sanity", self._step_boot_and_sanity)
        self._run_step("2", "Day-0 Barrel Cascade", self._step_barrel_cascade)
        self._run_step("3", "Market Quotes & Trades", self._step_market_quotes)
        self._run_step("4", "Labor Assignments", self._step_labor)
        self._run_step("5", "Maintenance Fault & Repair", self._step_maintenance)
        self._run_step("6", "Kitchens & Rations", self._step_kitchens)
        self._run_step("7", "Escort & Clinic", self._step_clinic)
        self._run_step("8", "Law Dispute", self._step_law_case)
        self._run_step("9", "Security Feedback", self._step_security_feedback)
        self.bus.dispatch()
        return Day0Report(
            config=self.config,
            world=self.world,
            steps=self.steps,
            snapshots=self.snapshots,
            events=list(self.bus.outbox),
        )

    def _step_boot_and_sanity(self) -> Dict[str, object]:
        focus = self.config.focus_wards
        w1 = self.world.wards[focus[0]]
        w2 = self.world.wards[focus[1]]
        w8 = self.world.wards[focus[2]]
        w21 = self.world.wards[focus[3]]

        self._emit(
            "WorldCreated",
            {
                "seed": self.config.world_seed,
                "routes": list(self.world.routes.keys()),
                "wards": len(self.world.wards),
            },
            ward=w1.id,
        )
        self._emit(
            "CreditRateUpdated",
            {"currency": "king-credit", "rate": 1.0, "source": "royal_treasury"},
            ward=w1.id,
        )
        standing_contract = ContractState(
            id="contract:standing:barrel",
            parties=("faction:king", "faction:0"),
            type="SUPPLY_ESCORT",
            obligations=(
                ContractObligation(
                    what="WATER_DELIVERY",
                    quantity=1800.0,
                    quality="CLEAN",
                    location=w1.id,
                    due=self.world.tick + 600,
                ),
            ),
            consideration=({"credits": 540.0, "currency": "king-credit"},),
            jurisdiction="CROWN",
            status="ACTIVE",
            created_tick=self.world.tick,
            activated_tick=self.world.tick,
        )
        self.world.contracts[standing_contract.id] = standing_contract
        self._emit(
            "ContractActivated",
            {"contract_id": standing_contract.id, "type": standing_contract.type},
            ward=w1.id,
        )
        maint_task = {
            "task_id": "maint:init",
            "ward": w21.id,
            "component": "condensers",
            "severity": "ROUTINE",
        }
        self.world.maintenance_tasks.append(maint_task)
        self._emit(
            "MaintenanceTaskQueued",
            maint_task,
            ward=w21.id,
        )

        self.snapshots["ward:focus"] = {
            w.id: {
                "name": w.name,
                "ring": w.ring,
                "sealed_mode": w.sealed_mode,
                "legitimacy": w.legitimacy,
                "facilities": dict(w.facilities),
                "water_liters": w.stocks.water_liters,
                "biomass_kg": w.stocks.biomass_kg,
            }
            for w in (w1, w2, w8, w21)
        }
        self.snapshots["routes:focus"] = {
            route.id: {
                "origin": route.origin,
                "destination": route.destination,
                "distance_km": route.distance_km,
                "risk": route.risk,
                "surcharge": route.surcharge,
            }
            for route in self.world.routes.values()
        }

        return {
            "focus_wards": focus,
            "legitimacy_gradient": [w2.legitimacy, w8.legitimacy, w21.legitimacy],
            "kitchens_w21": w21.facilities.get("kitchen", 0),
            "workshops_w21": w21.facilities.get("workshop", 0),
            "reclaimers_w8": w8.facilities.get("reclaimer", 0),
        }

    def _step_barrel_cascade(self) -> Dict[str, object]:
        focus = self.config.focus_wards
        w1 = self.world.wards[focus[0]]
        w2 = self.world.wards[focus[1]]
        w8 = self.world.wards[focus[2]]
        w21 = self.world.wards[focus[3]]
        manifest_per_route = 600.0
        tax_rate = self.config.tax_rate

        royalties: Dict[str, float] = {}
        for route_id, dest in (
            ("route:well-w2", w2),
            ("route:well-w8", w8),
            ("route:well-w21", w21),
        ):
            contract_id = f"contract:escort:{route_id}"
            contract = ContractState(
                id=contract_id,
                parties=("faction:king", "faction:1"),
                type="ESCORT",
                obligations=(
                    ContractObligation(
                        what="PROTECT_ROUTE",
                        quantity=manifest_per_route,
                        quality="CIVIC",
                        location=dest.id,
                        due=self.world.tick + 200,
                    ),
                ),
                consideration=({"credits": manifest_per_route * 0.18, "currency": "king-credit"},),
                jurisdiction="CIVIC",
                status="ACTIVE",
                created_tick=self.world.tick,
                activated_tick=self.world.tick,
            )
            self.world.contracts[contract_id] = contract
            self._emit(
                "ContractActivated",
                {"contract_id": contract.id, "type": contract.type, "route_id": route_id},
                ward=w1.id,
            )
            job_id = f"job:escort:{route_id}"
            self.world.labor_postings.append(
                {
                    "job_id": job_id,
                    "ward": dest.id,
                    "type": "ESCORT_GUARD",
                    "venue": "CIVIC",
                }
            )
            self._emit(
                "JobPosted",
                {"job_id": job_id, "ward": dest.id, "type": "ESCORT_GUARD", "venue": "CIVIC"},
                ward=dest.id,
            )

        # Execute deliveries.
        route_results = {}
        for route_id, dest in (
            ("route:well-w2", w2),
            ("route:well-w8", w8),
            ("route:well-w21", w21),
        ):
            route = self.world.routes[route_id]
            pre_volume = dest.stocks.water_liters
            delivered = manifest_per_route
            loss = 0.0
            incident: Optional[Dict[str, object]] = None
            if dest is w21:
                loss = manifest_per_route * 0.05
                delivered -= loss
                route.record_incident(
                    kind="AMBUSH",
                    severity="MINOR",
                    tick=self.world.tick,
                    notes="Minor ambush en route to W21",
                )
                incident = {
                    "route_id": route_id,
                    "type": "AMBUSH",
                    "loss_liters": loss,
                }
                self._emit(
                    "SecurityIncidentCreated",
                    {
                        "route_id": route_id,
                        "incident_type": "AMBUSH",
                        "severity": "MINOR",
                        "loss_liters": loss,
                    },
                    ward=dest.id,
                    priority=EventPriority.HIGH,
                )
            dest.stocks.delta_water(delivered)
            route.apply_delivery(delivered)
            royalty = delivered * tax_rate
            royalties[dest.id] = royalty
            king = self.world.factions["faction:king"]
            king.assets.delta_credit("king-credit", royalty)
            self._emit(
                "RoyaltyCollected",
                {
                    "ward": dest.id,
                    "volume_liters": delivered,
                    "royalty": royalty,
                    "tax_rate": tax_rate,
                },
                ward=dest.id,
            )
            payload = {
                "route_id": route_id,
                "origin": route.origin,
                "destination": route.destination,
                "manifest_liters": manifest_per_route,
                "delivered_liters": delivered,
                "loss_liters": loss,
                "surcharge": route.surcharge,
            }
            self._emit("BarrelDelivered", payload, ward=dest.id)
            route_results[route_id] = {
                "pre_volume": pre_volume,
                "post_volume": dest.stocks.water_liters,
                "delivered": delivered,
                "loss": loss,
                "incident": incident,
            }

        return {
            "manifest_per_route": manifest_per_route,
            "route_results": route_results,
            "royalties": royalties,
        }

    def _step_market_quotes(self) -> Dict[str, object]:
        focus = self.config.focus_wards
        w2 = self.world.wards[focus[1]]
        w21 = self.world.wards[focus[3]]
        route = self.world.routes["route:well-w21"]
        base_price = 1.4
        delivered_price = base_price * (1.0 + route.surcharge)
        spread_inner = self.config.market_base_spread
        spread_outer = spread_inner + 0.05

        quotes = [
            {"ward": w21.id, "commodity": "water", "price": delivered_price, "spread": spread_outer},
            {"ward": w21.id, "commodity": "ration:LOW", "price": 2.3, "spread": spread_outer + 0.02},
            {"ward": w2.id, "commodity": "water", "price": base_price * (1.0 + self.world.routes["route:well-w2"].surcharge), "spread": spread_inner},
        ]
        self.world.market_quotes.extend(quotes)
        for quote in quotes:
            self._emit("PricePosted", quote, ward=quote["ward"])

        self._emit(
            "CreditRateUpdated",
            {"currency": "credit:lord_W21", "rate": 0.92, "reference": "king-credit"},
            ward=w21.id,
        )

        kiosk_trade = {
            "trade_id": "trade:kiosk:w21",
            "ward": w21.id,
            "commodity": "water",
            "volume_liters": 500.0,
            "venue": "KIOSK",
            "price": delivered_price,
        }
        self.world.trades.append(kiosk_trade)
        self._emit("TradeExecuted", kiosk_trade, ward=w21.id)
        self.world.wards[w21.id].stocks.delta_water(-kiosk_trade["volume_liters"])

        bazaar_trade = {
            "trade_id": "trade:bazaar:ration",
            "ward": w21.id,
            "commodity": "ration:LOW",
            "venue": "BAZAAR",
            "served_agents": 40,
            "service_minutes": 30,
            "price": 2.3,
        }
        self.world.trades.append(bazaar_trade)
        self._emit("TradeExecuted", bazaar_trade, ward=w21.id)

        return {
            "delivered_price_w21": delivered_price,
            "spread_inner": spread_inner,
            "spread_outer": spread_outer,
        }

    def _step_labor(self) -> Dict[str, object]:
        focus = self.config.focus_wards
        w21 = self.world.wards[focus[3]]
        wage_floor_civic = self.config.min_wage_floor_by_venue["CIVIC"]
        wage_floor_merc = self.config.min_wage_floor_by_venue["MERC"]

        jobs = [
            {"job_id": "job:w21:maint", "type": "MAINT_REPAIR", "ward": w21.id, "venue": "CIVIC"},
            {"job_id": "job:w21:escort", "type": "ESCORT_GUARD", "ward": w21.id, "venue": "CIVIC"},
        ]
        for job in jobs:
            self.world.labor_postings.append(job)
            self._emit("JobPosted", job, ward=w21.id)

        # Spawn available workers (conceptual – we just count them).
        available_workers = 30
        self._advance_time(20)

        assignments = [
            {
                "assignment_id": "shift:maint",
                "job_id": "job:w21:maint",
                "worker_count": 2,
                "wage": wage_floor_civic + 8.0,
                "hazard_premium": 4.0,
                "currency": "credit:lord_W21",
            },
            {
                "assignment_id": "shift:kitchen",
                "job_id": "job:w21:kitchen",
                "worker_count": 3,
                "wage": wage_floor_civic + 2.0,
                "hazard_premium": 1.0,
                "currency": "credit:lord_W21",
            },
            {
                "assignment_id": "shift:escort",
                "job_id": "job:w21:escort",
                "worker_count": 1,
                "wage": wage_floor_merc + 6.0,
                "hazard_premium": 5.0,
                "currency": "credit:lord_W21",
            },
        ]
        no_show_rate = 0.07
        for assignment in assignments:
            record = dict(assignment)
            record["no_show_rate"] = no_show_rate
            self.world.labor_assignments.append(record)
            self._emit("ShiftAssigned", record, ward=w21.id)

        return {
            "available_workers": available_workers,
            "assignments": assignments,
            "no_show_rate": no_show_rate,
        }

    def _step_maintenance(self) -> Dict[str, object]:
        focus = self.config.focus_wards
        w21 = self.world.wards[focus[3]]
        fault = {
            "fault_id": "fault:w21:reservoir",
            "component": "RESERVOIR",
            "detail": "SEAL",
            "severity": "DEGRADED",
        }
        self._emit("FaultDetected", fault, ward=w21.id)
        task = {
            "task_id": "maint:w21:seal",
            "ward": w21.id,
            "component": "RESERVOIR",
            "parts": ["seal_A"],
            "eta_minutes": 180,
        }
        self.world.maintenance_tasks.append(task)
        self._emit("MaintenanceTaskQueued", task, ward=w21.id)
        pre_leak = w21.environment.water_loss
        pre_spread = next(q for q in self.world.market_quotes if q["ward"] == w21.id and q["commodity"] == "water")["spread"]
        self._advance_time(180)
        w21.infrastructure.repair(0.06)
        w21.environment.water_loss = max(0.0, w21.environment.water_loss - 0.0004)
        post_leak = w21.environment.water_loss
        post_spread = max(self.config.market_base_spread + 0.03, pre_spread - 0.01)
        for quote in self.world.market_quotes:
            if quote["ward"] == w21.id and quote["commodity"] == "water":
                quote["spread"] = post_spread
        completion = {
            "task_id": task["task_id"],
            "duration_minutes": 180,
            "leak_rate_before": pre_leak,
            "leak_rate_after": post_leak,
        }
        self._emit("MaintenanceCompleted", completion, ward=w21.id)

        return {
            "leak_rate_before": pre_leak,
            "leak_rate_after": post_leak,
            "spread_before": pre_spread,
            "spread_after": post_spread,
        }

    def _step_kitchens(self) -> Dict[str, object]:
        focus = self.config.focus_wards
        w21 = self.world.wards[focus[3]]
        production = {
            "ward": w21.id,
            "commodity": "ration:LOW",
            "sealed_lots": 80,
            "unsealed_lots": 40,
            "duration_minutes": 120,
        }
        self._emit("RationProduced", production, ward=w21.id)
        self._advance_time(120)
        service = {
            "ward": w21.id,
            "served_agents": 60,
            "average_wait_minutes": 24.5,
            "queue_incidents": 0,
        }
        self._emit("MealServed", service, ward=w21.id)
        self._advance_time(360)
        decay = {
            "ward": w21.id,
            "expired_lots": 20,
            "reclaimed_mass_ratio": 0.15,
        }
        self._emit("StockExpired", decay, ward=w21.id)
        reclaim = {
            "ward": w21.id,
            "resource": "greywater",
            "reclaimed_mass_ratio": 0.15,
        }
        self._emit("Reclaimed", reclaim, ward=w21.id)

        return {
            "served_agents": service["served_agents"],
            "average_wait_minutes": service["average_wait_minutes"],
            "reclaim_ratio": reclaim["reclaimed_mass_ratio"],
        }

    def _step_clinic(self) -> Dict[str, object]:
        focus = self.config.focus_wards
        w21 = self.world.wards[focus[3]]
        guard = self._select_guard(w21)
        injury = {
            "agent_id": guard.id,
            "injury": "BLUNT_TRAUMA",
            "severity": "MODERATE",
            "source_incident": "route:well-w21",
        }
        self._emit("ClinicIntake", injury, ward=w21.id, priority=EventPriority.HIGH)
        triage = {
            "agent_id": guard.id,
            "esi": 3,
            "treatment_minutes": 40,
            "outcome": "RECOVERED",
        }
        self._advance_time(40)
        guard.body.health = max(guard.body.health - 15.0, 0.0)
        guard.body.stamina = max(guard.body.stamina - 10.0, 0.0)
        self._emit("ClinicOutcome", triage, ward=w21.id)
        restriction = {
            "agent_id": guard.id,
            "work_restriction_days": 1,
        }
        self._emit("WorkCapacityAdjusted", restriction, ward=w21.id)
        rumor = {
            "rumor_id": "rumor:escort:injury",
            "topic": "AMBUSH_REPORT",
            "salience": 0.54,
        }
        self.world.security_reports.append({"ward": w21.id, "rumor": rumor})
        self._emit("RumorCreated", rumor, ward=w21.id)

        return {
            "guard": guard.id,
            "stamina_after": guard.body.stamina,
            "work_restriction_days": restriction["work_restriction_days"],
        }

    def _step_law_case(self) -> Dict[str, object]:
        focus = self.config.focus_wards
        w21 = self.world.wards[focus[3]]
        case = {
            "case_id": "case:late_delivery",
            "ward": w21.id,
            "arbiter": "CIVIC_BOARD",
            "dispute": "LATE_WATER",
            "status": "OPEN",
        }
        self.world.law_cases.append(case)
        self._emit("CaseOpened", case, ward=w21.id)
        evidence_items = [
            {"case_id": case["case_id"], "type": "LEDGER", "credibility": "HIGH"},
            {"case_id": case["case_id"], "type": "WITNESS", "credibility": "MEDIUM"},
            {"case_id": case["case_id"], "type": "SENSOR", "credibility": "HIGH"},
        ]
        for evidence in evidence_items:
            self._emit("EvidenceLogged", evidence, ward=w21.id)
        ruling = {
            "case_id": case["case_id"],
            "outcome": "RESTORATIVE",
            "penalty_credits": 45.0,
            "deadline_extension_minutes": 120,
        }
        self._emit("CaseRuling", ruling, ward=w21.id)
        settlement = {
            "case_id": case["case_id"],
            "status": "SETTLED",
        }
        self._emit("CaseSettled", settlement, ward=w21.id)
        carrier = self.world.factions.get("faction:1")
        if carrier is not None:
            carrier.metrics.econ.reliability = min(1.0, carrier.metrics.econ.reliability + 0.02)
        w21.legitimacy = min(1.0, w21.legitimacy + 0.01)

        return {
            "case_id": case["case_id"],
            "ruling_outcome": ruling["outcome"],
            "legitimacy_after": w21.legitimacy,
        }

    def _step_security_feedback(self) -> Dict[str, object]:
        focus = self.config.focus_wards
        w21 = self.world.wards[focus[3]]
        route = self.world.routes["route:well-w21"]
        pre_legitimacy = w21.legitimacy
        delta_legitimacy = 0.03
        w21.legitimacy = min(1.0, w21.legitimacy + delta_legitimacy)
        self._emit(
            "LegitimacyRecalculated",
            {
                "ward": w21.id,
                "delta": delta_legitimacy,
                "new_value": w21.legitimacy,
            },
            ward=w21.id,
        )
        adjustment = {
            "ward": w21.id,
            "commodity": "water",
            "spread_adjustment": -0.01,
        }
        for quote in self.world.market_quotes:
            if quote["ward"] == w21.id and quote["commodity"] == "water":
                quote["spread"] = max(self.config.market_base_spread + 0.02, quote["spread"] - 0.01)
        self._emit("MarketSpreadAdjusted", adjustment, ward=w21.id)
        risk_before = route.risk
        route.risk = max(0.0, route.risk - 0.02)
        self._emit(
            "SecurityRiskAdjusted",
            {"route_id": route.id, "risk_before": risk_before, "risk_after": route.risk},
            ward=w21.id,
        )

        return {
            "legitimacy_before": pre_legitimacy,
            "legitimacy_after": w21.legitimacy,
            "risk_before": risk_before,
            "risk_after": route.risk,
        }

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _select_guard(self, ward: WardState) -> AgentState:
        for agent in self.world.agents.values():
            if agent.ward == ward.id:
                return agent
        # Fall back to arbitrary agent if ward has no members.
        return next(iter(self.world.agents.values()))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_day0_playbook(config: Optional[Day0Config] = None) -> Day0Report:
    """Execute the deterministic Day-0 scenario and return the report."""

    runner = _Day0Runner(config or Day0Config())
    return runner.run()


__all__ = ["Day0Config", "Day0Report", "Day0StepResult", "run_day0_playbook"]

