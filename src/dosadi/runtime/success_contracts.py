from __future__ import annotations

"""Scenario success contracts and milestone evaluators (v1).

This module implements the core data structures and deterministic evaluation
helpers outlined in ``D-RUNTIME-0310``. Contract evaluation is deliberately
bounded: evaluators only inspect compact telemetry, specific ledgers, or
stable flags. World-wide scans are avoided and all evidence lists are clipped
to ``max_evidence_items`` to ensure O(1) memory growth.
"""

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence

from dosadi.runtime.telemetry import Metrics, ensure_metrics
from dosadi.world.facilities import FacilityKind, ensure_facility_ledger
from dosadi.world.incidents import IncidentLedger
from dosadi.world.scout_missions import MissionStatus, ScoutMissionLedger
from dosadi.systems.protocols import ProtocolRegistry, ProtocolStatus, ProtocolType


@dataclass(slots=True)
class ContractConfig:
    enabled: bool = True
    evaluation_cadence_ticks: int = 100
    stop_on_success: bool = True
    stop_on_failure: bool = True
    timeout_ticks: int | None = None
    max_evidence_items: int = 64


class MilestoneStatus(str, Enum):
    PENDING = "PENDING"
    ACHIEVED = "ACHIEVED"
    FAILED = "FAILED"


@dataclass(slots=True)
class Milestone:
    milestone_id: str
    name: str
    description: str
    status: MilestoneStatus = MilestoneStatus.PENDING
    achieved_tick: int | None = None
    failed_tick: int | None = None
    priority: int = 0
    evidence: list[dict] = field(default_factory=list)

    def add_evidence(self, payload: Mapping[str, object] | None, *, max_items: int) -> None:
        if not payload:
            return
        self.evidence.append(dict(payload))
        if len(self.evidence) > max_items:
            self.evidence = self.evidence[-max_items:]


@dataclass(slots=True)
class SuccessContract:
    contract_id: str
    scenario_id: str
    milestones: list[Milestone]
    failure_conditions: list[dict]
    stop_policy: dict[str, object]
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ContractResult:
    contract_id: str
    scenario_id: str
    tick_end: int
    ended_reason: str
    ended_detail: str
    milestones: list[Milestone]
    kpis: dict[str, float] = field(default_factory=dict)
    evidence: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class ContractRuntimeState:
    last_evaluation_tick: int = -1
    last_progress_signature: tuple | None = None
    progress_history: list[tuple[int, tuple]] = field(default_factory=list)
    result: ContractResult | None = None


def ensure_contract_state(world: Any) -> ContractRuntimeState:
    state = getattr(world, "contract_state", None)
    if isinstance(state, ContractRuntimeState):
        return state
    state = ContractRuntimeState()
    world.contract_state = state
    return state


def get_metric(world: Any, path: str) -> float | int | None:
    telemetry = ensure_metrics(world)
    if isinstance(telemetry, Metrics):
        if path in telemetry.counters:
            return telemetry.counters.get(path)
        if path in telemetry.gauges:
            return telemetry.gauges.get(path)
        if path in telemetry.legacy:
            return telemetry.legacy.get(path)
    if isinstance(telemetry, Mapping):
        value = telemetry.get(path)
        if isinstance(value, (int, float)):
            return value
    return None


def get_recent_incidents(world: Any, incident_kind: str, *, limit: int = 5) -> list[Mapping[str, object]]:
    ledger: IncidentLedger | None = getattr(world, "incidents", None)
    if not isinstance(ledger, IncidentLedger):
        return []
    collected: list[Mapping[str, object]] = []
    for inc_id in ledger.history[-limit:]:
        incident = ledger.incidents.get(inc_id)
        if incident is None:
            continue
        if str(getattr(incident, "kind", "")) != incident_kind and getattr(incident, "kind", None) != incident_kind:
            continue
        collected.append({
            "incident_id": incident.incident_id,
            "kind": getattr(incident.kind, "value", str(getattr(incident, "kind", ""))),
            "day": incident.day,
            "target_id": incident.target_id,
            "severity": incident.severity,
        })
        if len(collected) >= limit:
            break
    return collected


def get_flag(world: Any, path: str) -> bool:
    parts = path.split(".")
    cursor: Any = world
    for part in parts:
        cursor = getattr(cursor, part, None)
    return bool(cursor)


def _protocols(world: Any) -> Sequence:
    registry = getattr(world, "protocols", None)
    if isinstance(registry, ProtocolRegistry):
        return list(registry.protocols_by_id.values())
    if isinstance(registry, Mapping):
        return list(registry.values())
    values_fn = getattr(registry, "values", None)
    if callable(values_fn):
        try:
            return tuple(values_fn())
        except Exception:
            return ()
    return ()


def eval_council_formed(world: Any) -> tuple[bool, Mapping[str, object]]:
    groups: Iterable = getattr(world, "groups", []) or []
    council = None
    for group in groups:
        group_type = getattr(group, "group_type", None)
        name = str(getattr(group_type, "name", group_type))
        value = str(getattr(group_type, "value", group_type))
        if name == "COUNCIL" or value == "COUNCIL" or str(group_type) == "GroupType.COUNCIL":
            council = group
            break
    member_ids = [] if council is None else list(getattr(council, "member_ids", []) or [])
    evidence = {"members": member_ids, "count": len(member_ids)}
    return bool(member_ids), evidence


def eval_first_protocol_authored(world: Any) -> tuple[bool, Mapping[str, object]]:
    protocols = [
        p
        for p in _protocols(world)
        if getattr(p, "status", None) == ProtocolStatus.ACTIVE
        and getattr(p, "protocol_type", getattr(p, "field", None)) in {ProtocolType.TRAFFIC_AND_SAFETY, ProtocolType.MOVEMENT}
    ]
    evidence = {"protocols": [getattr(p, "protocol_id", getattr(p, "id", "?")) for p in protocols]}
    return bool(protocols), evidence


def eval_first_scout_mission_completed(world: Any) -> tuple[bool, Mapping[str, object]]:
    ledger: ScoutMissionLedger | None = getattr(world, "scout_missions", None)
    if not isinstance(ledger, ScoutMissionLedger):
        return False, {"missing_metric": "scout_missions"}
    completed = [mid for mid, mission in ledger.missions.items() if getattr(mission, "status", None) == MissionStatus.COMPLETE]
    evidence = {"completed": sorted(completed)}
    return bool(completed), evidence


def eval_first_depot_built(world: Any) -> tuple[bool, Mapping[str, object]]:
    facilities = ensure_facility_ledger(world)
    depots = facilities.list_by_kind(FacilityKind.DEPOT)
    evidence = {"depots": [fac.facility_id for fac in depots[:5]]}
    return bool(depots), evidence


def eval_first_corridor_established(world: Any) -> tuple[bool, Mapping[str, object]]:
    routes: MutableMapping[str, Any] = getattr(world, "routes", {}) or {}
    evidence = {"routes": sorted(list(routes)[:5])}
    return bool(routes), evidence


def eval_first_delivery_completed(world: Any) -> tuple[bool, Mapping[str, object]]:
    delivery_metric = get_metric(world, "stockpile.deliveries_completed")
    legacy_metric = get_metric(world, "deliveries_completed")
    deliveries = delivery_metric if delivery_metric is not None else legacy_metric
    if deliveries is None:
        return False, {"missing_metric": "deliveries_completed"}
    return deliveries > 0, {"deliveries_completed": float(deliveries)}


def eval_first_injury_or_incident(world: Any) -> tuple[bool, Mapping[str, object]]:
    incidents = get_recent_incidents(world, "IncidentKind.WORKER_INJURY")
    delivered = get_recent_incidents(world, "WORKER_INJURY") if not incidents else incidents
    return bool(delivered), {"incidents": delivered}


def _required_milestones(contract: SuccessContract) -> set[str]:
    required = contract.notes.get("required_ids") if isinstance(contract.notes, Mapping) else None
    if isinstance(required, Sequence):
        return {str(mid) for mid in required}
    return {m.milestone_id for m in contract.milestones}


def _progress_signature(world: Any, contract: SuccessContract) -> tuple:
    telemetry = ensure_metrics(world)
    deliveries = get_metric(world, "stockpile.deliveries_completed") or 0
    depots = len(ensure_facility_ledger(world).list_by_kind(FacilityKind.DEPOT))
    routes_active = len(getattr(world, "routes", {}) or {})
    achieved = sum(1 for m in contract.milestones if m.status == MilestoneStatus.ACHIEVED)
    telemetry_signature = telemetry.snapshot_signature() if isinstance(telemetry, Metrics) else "telemetry"
    return (
        achieved,
        float(deliveries),
        int(depots),
        int(routes_active),
        telemetry_signature,
    )


def _append_progress(state: ContractRuntimeState, signature: tuple, *, window_ticks: int, cadence: int, tick: int) -> None:
    state.progress_history.append((tick, signature))
    max_entries = max(1, window_ticks // max(1, cadence) + 1)
    if len(state.progress_history) > max_entries:
        state.progress_history = state.progress_history[-max_entries:]
    state.last_progress_signature = signature


def _check_deadlock(state: ContractRuntimeState, *, window_ticks: int, cadence: int) -> bool:
    if not state.progress_history:
        return False
    oldest_tick = state.progress_history[0][0]
    newest_tick = state.progress_history[-1][0]
    if newest_tick - oldest_tick < window_ticks:
        return False
    signatures = {sig for _, sig in state.progress_history}
    return len(signatures) == 1


def _evaluate_failure_conditions(
    world: Any,
    contract: SuccessContract,
    cfg: ContractConfig,
    state: ContractRuntimeState,
    tick: int,
    *,
    progress_signature: tuple,
) -> tuple[bool, str, list[dict]]:
    for condition in contract.failure_conditions:
        ctype = condition.get("type") if isinstance(condition, Mapping) else None
        if ctype == "collapsed_corridors":
            threshold = float(condition.get("threshold", 0))
            collapsed = getattr(world, "collapsed_corridors", set()) or set()
            if len(collapsed) >= threshold:
                return True, condition.get("reason", "collapsed corridors"), [
                    {"collapsed_corridors": sorted(collapsed), "threshold": threshold}
                ]
        elif ctype == "metric_below":
            metric = str(condition.get("metric", ""))
            threshold = float(condition.get("threshold", 0))
            value = get_metric(world, metric)
            if value is not None and float(value) < threshold:
                return True, condition.get("reason", metric), [{"metric": metric, "value": float(value), "threshold": threshold}]
        elif ctype == "metric_at_least":
            metric = str(condition.get("metric", ""))
            threshold = float(condition.get("threshold", 0))
            value = get_metric(world, metric)
            if value is not None and float(value) >= threshold:
                return True, condition.get("reason", metric), [{"metric": metric, "value": float(value), "threshold": threshold}]
        elif ctype == "deadlock":
            window_ticks = int(condition.get("window_ticks", cfg.evaluation_cadence_ticks * 5))
            _append_progress(state, progress_signature, window_ticks=window_ticks, cadence=cfg.evaluation_cadence_ticks, tick=tick)
            if _check_deadlock(state, window_ticks=window_ticks, cadence=cfg.evaluation_cadence_ticks):
                return True, condition.get("reason", "DEADLOCK"), [
                    {"window_ticks": window_ticks, "signature": progress_signature}
                ]
    return False, "", []


def _copy_milestones(milestones: Sequence[Milestone]) -> list[Milestone]:
    return [replace(m, evidence=list(m.evidence)) for m in milestones]


def evaluate_contract(
    world: Any,
    tick: int,
    *,
    cfg: ContractConfig | None = None,
    progress_signature_fn: Callable[[Any, SuccessContract], tuple] | None = None,
) -> ContractResult | None:
    contract: SuccessContract | None = getattr(world, "active_contract", None)
    if contract is None:
        return None
    cfg = cfg or getattr(world, "contract_cfg", None) or ContractConfig()
    world.contract_cfg = cfg
    stop_on_success = cfg.stop_on_success
    stop_on_failure = cfg.stop_on_failure
    if isinstance(getattr(contract, "stop_policy", None), Mapping):
        stop_on_success = bool(contract.stop_policy.get("stop_on_success", stop_on_success))
        stop_on_failure = bool(contract.stop_policy.get("stop_on_failure", stop_on_failure))
    state = ensure_contract_state(world)
    if state.result is not None:
        return state.result
    if not cfg.enabled:
        return None
    if cfg.timeout_ticks is not None and tick >= cfg.timeout_ticks:
        state.last_evaluation_tick = tick
        result = ContractResult(
            contract_id=contract.contract_id,
            scenario_id=contract.scenario_id,
            tick_end=tick,
            ended_reason="TIMEOUT",
            ended_detail=f"timeout at tick {tick}",
            milestones=_copy_milestones(contract.milestones),
        )
        state.result = result
        return result
    if cfg.evaluation_cadence_ticks <= 0:
        cadence_ok = True
    else:
        cadence_ok = tick % int(cfg.evaluation_cadence_ticks) == 0
    if not cadence_ok and tick != 0:
        return None

    evaluators: Mapping[str, Callable[[Any], tuple[bool, Mapping[str, object]]]] = (
        contract.notes.get("evaluators") if isinstance(contract.notes, Mapping) else {}
    )
    for milestone in sorted(contract.milestones, key=lambda m: (m.priority, m.milestone_id)):
        if milestone.status != MilestoneStatus.PENDING:
            continue
        evaluator = evaluators.get(milestone.milestone_id)
        if evaluator is None:
            continue
        achieved, evidence = evaluator(world)
        milestone.add_evidence(evidence, max_items=cfg.max_evidence_items)
        if achieved:
            milestone.status = MilestoneStatus.ACHIEVED
            milestone.achieved_tick = tick

    progress_signature = (
        progress_signature_fn(world, contract) if progress_signature_fn else _progress_signature(world, contract)
    )
    state.last_progress_signature = progress_signature
    failed, fail_reason, fail_evidence = _evaluate_failure_conditions(
        world, contract, cfg, state, tick, progress_signature=progress_signature
    )
    if failed:
        state.last_evaluation_tick = tick
        result = ContractResult(
            contract_id=contract.contract_id,
            scenario_id=contract.scenario_id,
            tick_end=tick,
            ended_reason="FAILURE",
            ended_detail=fail_reason,
            milestones=_copy_milestones(contract.milestones),
            evidence=fail_evidence[: cfg.max_evidence_items],
        )
        state.result = result
        if stop_on_failure:
            return result
        return None

    required_ids = _required_milestones(contract)
    all_done = all(m.status == MilestoneStatus.ACHIEVED for m in contract.milestones if m.milestone_id in required_ids)
    if all_done:
        state.last_evaluation_tick = tick
        result = ContractResult(
            contract_id=contract.contract_id,
            scenario_id=contract.scenario_id,
            tick_end=tick,
            ended_reason="SUCCESS",
            ended_detail=f"achieved {len(required_ids)} milestones",
            milestones=_copy_milestones(contract.milestones),
        )
        state.result = result
        if stop_on_success:
            return result
    state.last_evaluation_tick = tick
    return state.result


__all__ = [
    "ContractConfig",
    "ContractResult",
    "ContractRuntimeState",
    "Milestone",
    "MilestoneStatus",
    "SuccessContract",
    "eval_council_formed",
    "eval_first_corridor_established",
    "eval_first_depot_built",
    "eval_first_delivery_completed",
    "eval_first_injury_or_incident",
    "eval_first_protocol_authored",
    "eval_first_scout_mission_completed",
    "evaluate_contract",
    "get_flag",
    "get_metric",
    "get_recent_incidents",
    "ensure_contract_state",
]
