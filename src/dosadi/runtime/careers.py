from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from dosadi.world.factions import pseudo_rand01


BRANCHES: tuple[str, ...] = (
    "CIVIC",
    "INDUSTRIAL",
    "MILITARY",
    "ESPIONAGE",
    "CLERICAL",
    "RECLAIMER",
)


@dataclass(slots=True)
class RoleArchetype:
    role_id: str
    branch: str
    tier: int
    verbs: list[str] = field(default_factory=list)
    venue_types: list[str] = field(default_factory=list)
    ration_tier: str = "PROBATION"
    requires_credentials: list[str] = field(default_factory=list)
    promotion_to: list[str] = field(default_factory=list)
    risk_profile: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class Credential:
    cred_id: str
    issuer: str
    scope: dict[str, object] = field(default_factory=dict)
    revocable: bool = True


@dataclass(slots=True)
class CareerConfig:
    enabled: bool = False
    promotion_min_reliability: float = 0.65
    promotion_min_skill_delta: float = 1.0
    promotion_cadence_days: int = 7
    deterministic_salt: str = "career-v1"
    ration_by_tier: dict[str, int] = field(
        default_factory=lambda: {"PROBATION": 1, "STANDARD": 2, "PRIVILEGED": 3}
    )
    per_ward_min_slots: dict[str, int] = field(
        default_factory=lambda: {
            "CIVIC": 12,
            "INDUSTRIAL": 10,
            "MILITARY": 8,
            "ESPIONAGE": 3,
            "CLERICAL": 6,
            "RECLAIMER": 4,
        }
    )


def _entry_roles() -> list[RoleArchetype]:
    return [
        RoleArchetype(
            role_id="civic.queue_attendant",
            branch="CIVIC",
            tier=1,
            verbs=["INSPECT", "EMPATHIZE", "RECORD"],
            venue_types=["FOOD_HALL", "WATER_LINE"],
            ration_tier="PROBATION",
            promotion_to=["civic.queue_marshal"],
            risk_profile={"hazard": 0.1, "corruption": 0.3, "visibility": 0.7},
        ),
        RoleArchetype(
            role_id="civic.bunkhouse_runner",
            branch="CIVIC",
            tier=1,
            verbs=["RECORD", "NEGOTIATE", "EMPATHIZE"],
            venue_types=["BUNKHOUSE"],
            ration_tier="PROBATION",
            promotion_to=["civic.bunkhouse_steward"],
            risk_profile={"hazard": 0.1, "corruption": 0.25, "visibility": 0.5},
        ),
        RoleArchetype(
            role_id="civic.clinic_intake_aide",
            branch="CIVIC",
            tier=1,
            verbs=["EMPATHIZE", "RECORD", "INSPECT"],
            venue_types=["CLINIC"],
            ration_tier="PROBATION",
            promotion_to=["civic.intake_supervisor"],
            risk_profile={"hazard": 0.2, "corruption": 0.2, "visibility": 0.6},
        ),
        RoleArchetype(
            role_id="civic.minor_case_clerk",
            branch="CIVIC",
            tier=1,
            verbs=["RECORD", "INSPECT"],
            venue_types=["COURT"],
            ration_tier="PROBATION",
            promotion_to=["civic.docket_supervisor"],
            risk_profile={"hazard": 0.05, "corruption": 0.35, "visibility": 0.7},
        ),
        RoleArchetype(
            role_id="industrial.workshop_apprentice",
            branch="INDUSTRIAL",
            tier=1,
            verbs=["MODIFY", "ANALYZE", "RECORD"],
            venue_types=["WORKSHOP"],
            ration_tier="PROBATION",
            promotion_to=["industrial.line_technician"],
            risk_profile={"hazard": 0.35, "corruption": 0.2, "visibility": 0.5},
        ),
        RoleArchetype(
            role_id="industrial.pump_tender",
            branch="INDUSTRIAL",
            tier=1,
            verbs=["INSPECT", "MODIFY", "RECORD"],
            venue_types=["PLANT"],
            ration_tier="PROBATION",
            promotion_to=["industrial.flow_supervisor"],
            risk_profile={"hazard": 0.4, "corruption": 0.3, "visibility": 0.6},
        ),
        RoleArchetype(
            role_id="industrial.parts_runner",
            branch="INDUSTRIAL",
            tier=1,
            verbs=["NEGOTIATE", "INSPECT", "CONCEAL"],
            venue_types=["DEPOT", "WORKSHOP"],
            ration_tier="PROBATION",
            promotion_to=["industrial.parts_dispatch"],
            risk_profile={"hazard": 0.2, "corruption": 0.4, "visibility": 0.5},
        ),
        RoleArchetype(
            role_id="military.gate_assistant",
            branch="MILITARY",
            tier=1,
            verbs=["INSPECT", "RECORD", "INTIMIDATE"],
            venue_types=["GATE"],
            ration_tier="PROBATION",
            promotion_to=["military.gate_marshal"],
            risk_profile={"hazard": 0.35, "corruption": 0.35, "visibility": 0.8},
        ),
        RoleArchetype(
            role_id="military.patrol_junior",
            branch="MILITARY",
            tier=1,
            verbs=["INSPECT", "RECORD", "INTIMIDATE"],
            venue_types=["STREET"],
            ration_tier="PROBATION",
            promotion_to=["military.patrol_lead"],
            risk_profile={"hazard": 0.5, "corruption": 0.3, "visibility": 0.7},
        ),
        RoleArchetype(
            role_id="military.detention_aide",
            branch="MILITARY",
            tier=1,
            verbs=["ESCORT", "INSPECT", "RECORD"],
            venue_types=["DETENTION"],
            ration_tier="PROBATION",
            promotion_to=["military.detention_overseer"],
            risk_profile={"hazard": 0.45, "corruption": 0.5, "visibility": 0.6},
        ),
        RoleArchetype(
            role_id="espionage.shadow_courier",
            branch="ESPIONAGE",
            tier=1,
            verbs=["SNEAK", "CONCEAL", "EMPATHIZE"],
            venue_types=["SHADOW_ROUTE"],
            ration_tier="PROBATION",
            promotion_to=["espionage.network_runner"],
            risk_profile={"hazard": 0.4, "corruption": 0.5, "visibility": 0.3},
        ),
        RoleArchetype(
            role_id="espionage.watcher",
            branch="ESPIONAGE",
            tier=1,
            verbs=["RECORD", "NEGOTIATE", "EMPATHIZE"],
            venue_types=["OBSERVATION_POST"],
            ration_tier="PROBATION",
            promotion_to=["espionage.counterintel_observer"],
            risk_profile={"hazard": 0.25, "corruption": 0.45, "visibility": 0.25},
        ),
        RoleArchetype(
            role_id="espionage.smuggle_loader",
            branch="ESPIONAGE",
            tier=1,
            verbs=["CONCEAL", "INSPECT", "COORDINATE"],
            venue_types=["DEPOT", "DOCK"],
            ration_tier="PROBATION",
            promotion_to=["espionage.smuggle_foreman"],
            risk_profile={"hazard": 0.35, "corruption": 0.6, "visibility": 0.35},
        ),
        RoleArchetype(
            role_id="clerical.ledger_copyist",
            branch="CLERICAL",
            tier=1,
            verbs=["RECORD", "INSPECT"],
            venue_types=["ARCHIVE"],
            ration_tier="PROBATION",
            promotion_to=["clerical.records_supervisor"],
            risk_profile={"hazard": 0.05, "corruption": 0.25, "visibility": 0.7},
        ),
        RoleArchetype(
            role_id="clerical.permit_counter",
            branch="CLERICAL",
            tier=1,
            verbs=["INSPECT", "RECORD"],
            venue_types=["PERMIT_OFFICE"],
            ration_tier="PROBATION",
            promotion_to=["clerical.permit_officer"],
            risk_profile={"hazard": 0.05, "corruption": 0.45, "visibility": 0.75},
        ),
        RoleArchetype(
            role_id="clerical.audit_runner",
            branch="CLERICAL",
            tier=1,
            verbs=["RECORD", "INSPECT", "NEGOTIATE"],
            venue_types=["FIELD"],
            ration_tier="PROBATION",
            promotion_to=["clerical.audit_lead"],
            risk_profile={"hazard": 0.2, "corruption": 0.4, "visibility": 0.6},
        ),
        RoleArchetype(
            role_id="reclaimer.salvage_sorter",
            branch="RECLAIMER",
            tier=1,
            verbs=["INSPECT", "MODIFY", "RECORD"],
            venue_types=["SALVAGE_YARD"],
            ration_tier="PROBATION",
            promotion_to=["reclaimer.salvage_lead"],
            risk_profile={"hazard": 0.45, "corruption": 0.35, "visibility": 0.4},
        ),
        RoleArchetype(
            role_id="reclaimer.waste_hauler",
            branch="RECLAIMER",
            tier=1,
            verbs=["INTIMIDATE", "MODIFY", "INSPECT"],
            venue_types=["WASTE_ROUTE"],
            ration_tier="PROBATION",
            promotion_to=["reclaimer.waste_overseer"],
            risk_profile={"hazard": 0.5, "corruption": 0.4, "visibility": 0.5},
        ),
        RoleArchetype(
            role_id="reclaimer.suit_recovery_aide",
            branch="RECLAIMER",
            tier=1,
            verbs=["INSPECT", "MODIFY", "RECORD"],
            venue_types=["CLINIC", "FIELD"],
            ration_tier="PROBATION",
            promotion_to=["reclaimer.suit_recovery_lead"],
            risk_profile={"hazard": 0.55, "corruption": 0.3, "visibility": 0.55},
        ),
    ]


def _ladder_roles() -> list[RoleArchetype]:
    return [
        RoleArchetype(
            role_id="civic.queue_marshal",
            branch="CIVIC",
            tier=2,
            verbs=["INSPECT", "RECORD", "INTIMIDATE", "NEGOTIATE"],
            venue_types=["FOOD_HALL", "WATER_LINE"],
            ration_tier="STANDARD",
            promotion_to=["civic.protocol_author"],
            risk_profile={"hazard": 0.2, "corruption": 0.5, "visibility": 0.8},
        ),
        RoleArchetype(
            role_id="civic.protocol_author",
            branch="CIVIC",
            tier=3,
            verbs=["RECORD", "INSPECT", "NEGOTIATE"],
            venue_types=["COUNCIL"],
            ration_tier="PRIVILEGED",
            promotion_to=[],
            risk_profile={"hazard": 0.1, "corruption": 0.55, "visibility": 0.9},
        ),
        RoleArchetype(
            role_id="industrial.line_technician",
            branch="INDUSTRIAL",
            tier=2,
            verbs=["MODIFY", "ANALYZE", "RECORD"],
            venue_types=["WORKSHOP", "PLANT"],
            ration_tier="STANDARD",
            promotion_to=["industrial.protocol_engineer"],
            risk_profile={"hazard": 0.45, "corruption": 0.35, "visibility": 0.6},
        ),
        RoleArchetype(
            role_id="industrial.protocol_engineer",
            branch="INDUSTRIAL",
            tier=3,
            verbs=["ANALYZE", "MODIFY", "RECORD"],
            venue_types=["PLANT", "WORKSHOP"],
            ration_tier="PRIVILEGED",
            promotion_to=[],
            risk_profile={"hazard": 0.4, "corruption": 0.45, "visibility": 0.75},
        ),
        RoleArchetype(
            role_id="military.gate_marshal",
            branch="MILITARY",
            tier=2,
            verbs=["INSPECT", "INTIMIDATE", "RECORD"],
            venue_types=["GATE"],
            ration_tier="STANDARD",
            promotion_to=["military.protocol_officer"],
            risk_profile={"hazard": 0.45, "corruption": 0.55, "visibility": 0.85},
        ),
        RoleArchetype(
            role_id="military.protocol_officer",
            branch="MILITARY",
            tier=3,
            verbs=["INTIMIDATE", "RECORD", "INSPECT"],
            venue_types=["GATE", "STREET"],
            ration_tier="PRIVILEGED",
            promotion_to=[],
            risk_profile={"hazard": 0.4, "corruption": 0.6, "visibility": 0.9},
        ),
        RoleArchetype(
            role_id="espionage.network_runner",
            branch="ESPIONAGE",
            tier=2,
            verbs=["SNEAK", "CONCEAL", "FORGE", "EMPATHIZE"],
            venue_types=["SHADOW_ROUTE", "DEPOT"],
            ration_tier="STANDARD",
            promotion_to=["espionage.protocol_architect"],
            risk_profile={"hazard": 0.5, "corruption": 0.65, "visibility": 0.45},
        ),
        RoleArchetype(
            role_id="espionage.protocol_architect",
            branch="ESPIONAGE",
            tier=3,
            verbs=["FORGE", "CONCEAL", "RECORD"],
            venue_types=["SHADOW_ROUTE", "COUNCIL"],
            ration_tier="PRIVILEGED",
            promotion_to=[],
            risk_profile={"hazard": 0.4, "corruption": 0.7, "visibility": 0.5},
        ),
        RoleArchetype(
            role_id="clerical.records_supervisor",
            branch="CLERICAL",
            tier=2,
            verbs=["RECORD", "INSPECT", "FORGE"],
            venue_types=["ARCHIVE"],
            ration_tier="STANDARD",
            promotion_to=["clerical.protocol_editor"],
            risk_profile={"hazard": 0.1, "corruption": 0.45, "visibility": 0.85},
        ),
        RoleArchetype(
            role_id="clerical.protocol_editor",
            branch="CLERICAL",
            tier=3,
            verbs=["RECORD", "FORGE", "ANALYZE"],
            venue_types=["ARCHIVE", "COUNCIL"],
            ration_tier="PRIVILEGED",
            promotion_to=[],
            risk_profile={"hazard": 0.1, "corruption": 0.5, "visibility": 0.9},
        ),
        RoleArchetype(
            role_id="reclaimer.salvage_lead",
            branch="RECLAIMER",
            tier=2,
            verbs=["MODIFY", "INSPECT", "INTIMIDATE"],
            venue_types=["SALVAGE_YARD"],
            ration_tier="STANDARD",
            promotion_to=["reclaimer.protocol_keeper"],
            risk_profile={"hazard": 0.55, "corruption": 0.45, "visibility": 0.6},
        ),
        RoleArchetype(
            role_id="reclaimer.protocol_keeper",
            branch="RECLAIMER",
            tier=3,
            verbs=["RECORD", "INSPECT", "MODIFY"],
            venue_types=["SALVAGE_YARD", "CLINIC"],
            ration_tier="PRIVILEGED",
            promotion_to=[],
            risk_profile={"hazard": 0.45, "corruption": 0.5, "visibility": 0.75},
        ),
    ]


def role_registry() -> dict[str, RoleArchetype]:
    registry: dict[str, RoleArchetype] = {}
    for role in _entry_roles() + _ladder_roles():
        registry[role.role_id] = role
    return registry


def _ensure_career_cfg(world: Any) -> CareerConfig:
    cfg = getattr(world, "career_cfg", None)
    if not isinstance(cfg, CareerConfig):
        cfg = CareerConfig()
        world.career_cfg = cfg
    return cfg


def _ensure_role_registry(world: Any) -> dict[str, RoleArchetype]:
    registry = getattr(world, "career_roles", None)
    if not isinstance(registry, dict) or not registry:
        registry = role_registry()
        world.career_roles = registry
    return registry


def _career_events(world: Any) -> list[dict[str, object]]:
    events: list[dict[str, object]] = getattr(world, "career_events", []) or []
    world.career_events = events
    return events


def generate_role_postings(world: Any, *, day: int) -> None:
    cfg = _ensure_career_cfg(world)
    if not cfg.enabled:
        return
    registry = _ensure_role_registry(world)
    wards = getattr(world, "wards", {}) or {}

    postings: list[dict[str, object]] = []
    for ward_id in sorted(wards.keys()):
        for branch in BRANCHES:
            min_slots = int(cfg.per_ward_min_slots.get(branch, 0) or 0)
            if min_slots <= 0:
                continue
            branch_roles = [
                role for role in registry.values() if role.branch == branch and role.tier == 1
            ]
            if not branch_roles:
                continue
            branch_roles.sort(key=lambda role: role.role_id)
            for idx in range(min_slots):
                salt = f"{world.seed}:{day}:{ward_id}:{branch}:{idx}:{cfg.deterministic_salt}"
                pick_idx = int(pseudo_rand01(salt) * len(branch_roles))
                role = branch_roles[pick_idx % len(branch_roles)]
                posting_id = f"job:{ward_id}:{branch.lower()}:{idx}"
                postings.append(
                    {
                        "id": posting_id,
                        "ward_id": ward_id,
                        "branch": role.branch,
                        "role_id": role.role_id,
                        "tier": role.tier,
                        "verbs": list(role.verbs),
                        "venue_types": list(role.venue_types),
                        "ration_tier": role.ration_tier,
                        "promotion_to": list(role.promotion_to),
                        "risk_profile": dict(role.risk_profile),
                    }
                )
    world.labor_postings = postings


def _eligible_for_promotion(agent: Any, *, min_ticks: float) -> bool:
    ticks = float(getattr(agent, "total_ticks_employed", 0.0) or 0.0)
    return ticks >= min_ticks


def _promote_agent(agent: Any, role: RoleArchetype, next_role: RoleArchetype) -> None:
    agent.assignment_role = next_role.role_id
    agent.times_promoted = getattr(agent, "times_promoted", 0) + 1
    if next_role.ration_tier not in getattr(agent, "roles", []):
        agent.roles.append(next_role.ration_tier)
    if next_role.role_id not in getattr(agent, "roles", []):
        agent.roles.append(next_role.role_id)


def promotion_review(world: Any, *, day: int) -> None:
    cfg = _ensure_career_cfg(world)
    if not cfg.enabled:
        return
    last_run = getattr(world, "career_last_run_day", -1)
    if last_run >= 0 and day - last_run < max(1, int(cfg.promotion_cadence_days)):
        return
    registry = _ensure_role_registry(world)
    events = _career_events(world)

    min_ticks = float(cfg.promotion_min_skill_delta) * 10_000.0
    for agent in getattr(world, "agents", {}).values():
        role_id = getattr(agent, "assignment_role", None)
        role = registry.get(role_id)
        if role is None or not role.promotion_to:
            continue
        if not _eligible_for_promotion(agent, min_ticks=min_ticks):
            continue
        next_role_id = role.promotion_to[0]
        next_role = registry.get(next_role_id)
        if next_role is None:
            continue
        _promote_agent(agent, role, next_role)
        events.append(
            {
                "type": "PromotionGranted",
                "agent_id": agent.agent_id,
                "from_role": role.role_id,
                "to_role": next_role.role_id,
                "day": day,
                "ration_tier": next_role.ration_tier,
            }
        )
    world.career_last_run_day = day


def update_careers_for_day(world: Any, *, day: int) -> None:
    cfg = _ensure_career_cfg(world)
    if not cfg.enabled:
        return
    _ensure_role_registry(world)
    generate_role_postings(world, day=day)
    promotion_review(world, day=day)
