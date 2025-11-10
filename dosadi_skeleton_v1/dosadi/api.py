
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from .core import WorldState, minute_tick, day_tick
from .events import emit
from .utils import ok, err

@dataclass
class DosadiSim:
    ws: WorldState

    # ----- Time -----
    def tick(self) -> Dict[str, Any]:
        """Advance one minute (100 ticks) and run per-minute subsystems.
        Wire the real calls in implement phase; this stub only advances time and emits diagnostics.
        """
        minute_tick(self.ws)
        emit("MinuteTick", {"time_min": self.ws.time_min})
        return ok({"time_min": self.ws.time_min})

    def day(self) -> Dict[str, Any]:
        """Advance one day and run per-day subsystems (references, legitimacy)."""
        day_tick(self.ws)
        emit("DayTick", {"time_min": self.ws.time_min})
        return ok({"time_min": self.ws.time_min})

    # ----- Worldgen -----
    def generate_world(self, cfg: Dict[str, Any], seed: int) -> Dict[str, Any]:
        """Stub worldgen. Should populate wards/routes/factions per Worldgen v1, then emit events."""
        self.ws.seed = seed
        self.ws.time_min = 0
        self.ws.wards = []
        self.ws.routes = []
        self.ws.policy = cfg.get("policy", {})
        emit("WorldCreated", {"seed": seed})
        return ok({"seed": seed})

    # ----- Barrel Cascade -----
    def plan_cascade(self, day: int) -> Dict[str, Any]:
        emit("DeliveryPlanned", {"day": day})
        return ok({"plans": []})

    def start_delivery(self, plan_id: str) -> Dict[str, Any]:
        emit("EscortJobPosted", {"plan_id": plan_id})
        return ok({"escort_job_id": "job_placeholder", "manifest": {}})

    def complete_delivery(self, plan_id: str, loss_frac: float = 0.0) -> Dict[str, Any]:
        emit("BarrelDelivered", {"plan_id": plan_id, "loss_frac": loss_frac})
        emit("RoyalTaxAssessed", {"plan_id": plan_id})
        return ok()

    # ----- Market -----
    def update_daily_reference(self, ward_id: str, item_id: str) -> Dict[str, Any]:
        emit("MarketIndexUpdated", {"ward": ward_id, "item": item_id})
        return ok({"P_ref": None})

    def minute_quote_update(self, ward_id: str, item_id: str, venue_id: str) -> Dict[str, Any]:
        emit("PricePosted", {"ward": ward_id, "item": item_id, "venue": venue_id,
                             "bid": None, "ask": None, "mid": None, "spread": None})
        return ok({"bid": None, "ask": None, "mid": None, "spread": None})

    def kiosk_trade(self, ward: str, item: str, side: str, qty: float, account: dict) -> Dict[str, Any]:
        emit("TradeExecuted", {"venue": "KIOSK", "ward": ward, "item": item, "qty": qty, "price": None})
        return ok()

    def bazaar_bargain(self, buyer: str, seller: str, item: str, qty: float, deadline_min: int) -> Dict[str, Any]:
        emit("NegotiationOpened", {"buyer": buyer, "seller": seller, "item": item, "qty": qty})
        emit("TradeExecuted", {"venue": "BAZAAR", "item": item, "qty": qty, "price": None})
        return ok({"price": None, "status": "SUCCESS"})

    # ----- Labor -----
    def post_job(self, job_spec: dict) -> Dict[str, Any]:
        emit("JobPosted", {"job": job_spec})
        return ok({"job_id": job_spec.get("job_id", "job_stub")})

    def minute_labor_tick(self, ward_id: str) -> Dict[str, Any]:
        emit("ShiftAssigned", {"ward": ward_id})
        return ok({"assignments": []})

    def start_shift(self, assignment_id: str) -> Dict[str, Any]:
        emit("ShiftStarted", {"assignment_id": assignment_id})
        return ok()

    def complete_shift(self, assignment_id: str) -> Dict[str, Any]:
        emit("ShiftCompleted", {"assignment_id": assignment_id})
        return ok()

    # ----- Maintenance -----
    def queue_task(self, task_spec: dict) -> Dict[str, Any]:
        emit("MaintenanceTaskQueued", {"task": task_spec})
        return ok({"task_id": task_spec.get("task_id", "t_stub")})

    def start_maintenance(self, task_id: str) -> Dict[str, Any]:
        emit("MaintenanceStarted", {"task_id": task_id})
        return ok()

    def complete_maintenance(self, task_id: str, parts_used: Optional[dict] = None) -> Dict[str, Any]:
        emit("MaintenanceCompleted", {"task_id": task_id, "parts_used": parts_used or {}})
        return ok()

    # ----- Security -----
    def minute_security_update(self) -> Dict[str, Any]:
        emit("SecurityIncidentCreated", {"type": "AMBUSH", "severity": "MINOR"})
        return ok({"incidents": []})

    def respond_to_incident(self, incident_id: str, policy: dict) -> Dict[str, Any]:
        emit("IncidentResolved", {"incident_id": incident_id, "policy": policy})
        return ok()

    def post_bounty(self, incident_id: str, reward: float) -> Dict[str, Any]:
        emit("BountyPosted", {"incident_id": incident_id, "reward": reward})
        return ok()

    # ----- Clinics -----
    def clinic_intake(self, agent_id: str, clinic_id: str) -> Dict[str, Any]:
        emit("ClinicIntake", {"agent": agent_id, "clinic": clinic_id, "ESI": 3})
        emit("TriageAssigned", {"visit": "v_stub", "level": 3})
        return ok({"visit_id": "v_stub", "ESI": 3})

    def minute_clinic_tick(self, clinic_id: str) -> Dict[str, Any]:
        emit("TreatmentStarted", {"visit": "v_stub"})
        emit("TreatmentCompleted", {"visit": "v_stub"})
        return ok()

    def discharge(self, visit_id: str, result: str) -> Dict[str, Any]:
        emit("ClinicOutcome", {"visit": visit_id, "result": result})
        return ok()

    # ----- Kitchens & Rations -----
    def minute_kitchen_tick(self, kitchen_id: str) -> Dict[str, Any]:
        emit("MealServed", {"kitchen": kitchen_id, "count": 0})
        return ok({"produced_lots": [], "served_meals": 0})

    def audit_hygiene(self, kitchen_id: str) -> Dict[str, Any]:
        emit("HygieneGraded", {"kitchen": kitchen_id, "grade": "B"})
        return ok({"grade": "B"})

    # ----- Law & Cases -----
    def open_case(self, plaintiff: str, defendant: str, cause: str, contract_id: str | None = None) -> Dict[str, Any]:
        emit("CaseOpened", {"plaintiff": plaintiff, "defendant": defendant, "cause": cause, "contract_id": contract_id})
        return ok({"case_id": "C_stub"})

    def submit_evidence(self, case_id: str, evidence: dict) -> Dict[str, Any]:
        emit("EvidenceSubmitted", {"case_id": case_id, "evidence": evidence})
        emit("EvidenceAccepted", {"case_id": case_id})
        return ok()

    def score_case(self, case_id: str) -> Dict[str, Any]:
        emit("CaseScoresUpdated", {"case_id": case_id, "strength": 0.0, "confidence": 0.0})
        return ok({"strength": 0.0, "confidence": 0.0})

    def issue_ruling(self, case_id: str, order: dict) -> Dict[str, Any]:
        emit("ArbiterRulingIssued", {"case_id": case_id, "order": order})
        return ok()

    def close_case(self, case_id: str, status: str) -> Dict[str, Any]:
        emit("CaseClosed", {"case_id": case_id, "status": status})
        return ok()

    # ----- Rumor & Perception -----
    def emit_rumor(self, source_id: str, topic: str, cred: float, sal: float) -> Dict[str, Any]:
        emit("RumorEmitted", {"source": source_id, "topic": topic, "cred": cred, "sal": sal})
        return ok()

    def minute_perception_update(self, ward_id: str) -> Dict[str, Any]:
        emit("MemoryCreated", {"ward": ward_id})
        return ok()

    # ----- Metrics -----
    def recalc_legitimacy(self, ward_id: str) -> Dict[str, Any]:
        emit("LegitimacyRecalculated", {"ward": ward_id, "Δ": 0.0})
        return ok()

    def publish_labor_stats(self, ward_id: str) -> Dict[str, Any]:
        emit("LaborStatsUpdated", {"ward": ward_id})
        return ok()

    # ----- Snapshots & Replay (stubs) -----
    def snapshot(self, kind: str) -> Dict[str, Any]:
        return ok({"blob": {}})

    def replay(self, events: List[dict]) -> Dict[str, Any]:
        return ok()
