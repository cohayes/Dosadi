"""Reform movements and anti-corruption drives v1.

This module implements a minimal, deterministic slice of the
`D-RUNTIME-0303` checklist. It wires together bounded reform
campaign state, a bi-weekly emergence loop, a bounded action loop,
and telemetry-compatible exports so worlds can persist and
replay reform activity.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.leadership import ensure_leadership_state
from dosadi.runtime.policing import WardPolicingState, ensure_policing_state
from dosadi.runtime.shadow_state import CorruptionIndex
from dosadi.runtime.sovereignty import TerritoryState, ensure_sovereignty_state
from dosadi.runtime.telemetry import ensure_metrics, record_event


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_rand01(*parts: object) -> float:
    digest = sha256("|".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


@dataclass(slots=True)
class ReformConfig:
    enabled: bool = False
    update_cadence_days: int = 14
    deterministic_salt: str = "reform-v1"
    max_reforms_per_polity: int = 3
    max_actions_per_update: int = 6
    emergence_rate_base: float = 0.001
    success_scale: float = 0.55
    backlash_scale: float = 0.35
    retaliation_scale: float = 0.30


@dataclass(slots=True)
class ReformCampaign:
    reform_id: str
    polity_id: str
    kind: str
    sponsors: list[str]
    targets: list[dict]
    intensity: float
    legitimacy_push: float
    risk_tolerance: float
    progress: float = 0.0
    backlash: float = 0.0
    status: str = "ACTIVE"
    start_day: int = 0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ReformAction:
    day: int
    reform_id: str
    action_type: str
    ward_id: str
    domain: str
    result: str
    effects: dict[str, object] = field(default_factory=dict)


def ensure_reform_config(world: Any) -> ReformConfig:
    cfg = getattr(world, "reform_cfg", None)
    if not isinstance(cfg, ReformConfig):
        cfg = ReformConfig()
        world.reform_cfg = cfg
    return cfg


def ensure_reform_ledgers(world: Any, polities: Iterable[str]) -> tuple[dict[str, list[ReformCampaign]], list[ReformAction]]:
    campaigns = getattr(world, "reforms_by_polity", None)
    if not isinstance(campaigns, dict):
        campaigns = {}
    for polity_id in polities:
        campaigns.setdefault(polity_id, [])
    actions = getattr(world, "reform_actions", None)
    if not isinstance(actions, list):
        actions = []
    world.reforms_by_polity = campaigns
    world.reform_actions = actions
    return campaigns, actions


def _polities(world: Any) -> list[str]:
    state = ensure_sovereignty_state(world)
    polities = sorted(getattr(state, "polities", {}).keys())
    if polities:
        return polities
    return ["polity:empire"]


def _polity_wards(territory: TerritoryState, polity_id: str) -> list[str]:
    wards: list[str] = []
    for ward_id, owner in (territory.ward_control or {}).items():
        if owner == polity_id:
            wards.append(str(ward_id))
    return wards


def _corruption_score(world: Any, ward_ids: Iterable[str]) -> float:
    corruption = getattr(world, "corruption_by_ward", {}) or {}
    values = []
    for wid in ward_ids:
        entry: CorruptionIndex | None = corruption.get(wid)
        if entry is None:
            continue
        values.append(float(entry.capture) + float(entry.shadow_state))
    if not values:
        return 0.0
    return _clamp01(sum(values) / (2 * len(values)))


def _procedural_policing_share(world: Any, ward_ids: Iterable[str]) -> float:
    shares: list[float] = []
    for wid in ward_ids:
        state: WardPolicingState = ensure_policing_state(world, wid)
        shares.append(float(state.doctrine_mix.get("PROCEDURAL", 0.0)))
    if not shares:
        return 0.25
    return _clamp01(sum(shares) / len(shares))


def _media_independence(world: Any) -> float:
    metrics = getattr(world, "metrics", None)
    if metrics is not None:
        media_bucket = getattr(metrics, "gauges", {}).get("media", {}) if hasattr(metrics, "gauges") else {}
        if isinstance(media_bucket, Mapping):
            val = media_bucket.get("independence", None)
            if val is not None:
                try:
                    return _clamp01(float(val))
                except Exception:
                    pass
    return _clamp01(float(getattr(world, "media_independence", 0.0)))


def _hardship(world: Any, ward_ids: Iterable[str]) -> float:
    wards = getattr(world, "wards", {}) or {}
    values = []
    for wid in ward_ids:
        if wid not in wards:
            continue
        try:
            values.append(float(getattr(wards[wid], "need_index", 0.0)))
        except Exception:
            continue
    if not values:
        return _clamp01(float(getattr(world, "need_index", 0.0)))
    return _clamp01(sum(values) / len(values))


def _sponsor_factions(world: Any, *, limit: int = 3) -> list[str]:
    factions = getattr(world, "factions", {}) or {}
    if not isinstance(factions, Mapping):
        return []
    ordered = sorted(factions.keys())
    return ordered[: max(0, int(limit))]


def _target_domains() -> list[str]:
    return ["CUSTOMS", "POLICING", "COURTS", "MEDIA", "DEPOTS"]


def _choose_kind(*, corruption: float, hardship: float, media: float, procedural_share: float) -> str:
    if media + procedural_share >= hardship + 0.2:
        return "PROCEDURAL"
    if hardship > 0.55 and corruption > 0.4:
        return "POPULIST_PURGE"
    if media > 0.6:
        return "TECH_TRANSPARENCY"
    return "RELIGIOUS_REVIVAL"


def _maybe_spawn_campaign(
    world: Any,
    *,
    polity_id: str,
    wards: list[str],
    cfg: ReformConfig,
    day: int,
    campaigns: list[ReformCampaign],
) -> None:
    if len(campaigns) >= cfg.max_reforms_per_polity:
        return

    corruption = _corruption_score(world, wards)
    hardship = _hardship(world, wards)
    media = _media_independence(world)
    procedural_share = _procedural_policing_share(world, wards)

    legitimacy_state = ensure_leadership_state(world, polities=[polity_id]).get(polity_id)
    appetite = 1.0 - float(getattr(legitimacy_state, "proc_legit", 0.5))

    pressure = _clamp01(
        corruption * 0.5 + hardship * 0.15 + media * 0.15 + procedural_share * 0.1 + appetite * 0.1
    )
    if pressure < 0.15:
        return
    trigger = _stable_rand01(cfg.deterministic_salt, "emergence", polity_id, day)
    if trigger > cfg.emergence_rate_base + pressure * 0.5:
        return

    kind = _choose_kind(corruption=corruption, hardship=hardship, media=media, procedural_share=procedural_share)
    sponsors = _sponsor_factions(world)

    corruption_by_ward = getattr(world, "corruption_by_ward", {}) or {}
    ward_scores = []
    for wid in wards:
        entry: CorruptionIndex | None = corruption_by_ward.get(wid)
        score = 0.0
        if entry is not None:
            score = float(entry.capture) + float(entry.shadow_state)
        ward_scores.append((score, wid))
    ward_scores.sort(key=lambda itm: (-itm[0], itm[1]))
    targets = []
    for score, wid in ward_scores[: cfg.max_actions_per_update]:
        domain_idx = int(_stable_rand01(cfg.deterministic_salt, "domain", wid, day) * len(_target_domains()))
        domain = _target_domains()[min(domain_idx, len(_target_domains()) - 1)]
        targets.append({"ward_id": wid, "domain": domain, "priority": _clamp01(score)})

    reform_id = f"reform:{polity_id}:{day}:{len(campaigns)}"
    campaigns.append(
        ReformCampaign(
            reform_id=reform_id,
            polity_id=polity_id,
            kind=kind,
            sponsors=sponsors,
            targets=targets,
            intensity=_clamp01(pressure + corruption * 0.25),
            legitimacy_push=_clamp01(appetite + media * 0.3),
            risk_tolerance=_clamp01(0.4 + corruption * 0.2),
            start_day=day,
            last_update_day=day - 1,
        )
    )
    record_event(world, {"type": "REFORM_CAMPAIGN_STARTED", "polity_id": polity_id, "reform_id": reform_id, "day": day})


def _action_candidates(campaign: ReformCampaign) -> list[dict]:
    return sorted(campaign.targets, key=lambda t: (-float(t.get("priority", 0.0)), t.get("ward_id", "")))


def _action_type_for_kind(kind: str, idx: int) -> str:
    if kind == "PROCEDURAL":
        return ["AUDIT", "PROSECUTE", "DISCLOSE", "PROTECT_WITNESS", "AUDIT", "PROSECUTE"][idx % 6]
    if kind == "POPULIST_PURGE":
        return ["PURGE", "PROSECUTE", "AUDIT", "DISCLOSE", "PURGE", "PROTECT_WITNESS"][idx % 6]
    if kind == "TECH_TRANSPARENCY":
        return ["DISCLOSE", "AUDIT", "PROSECUTE", "DISCLOSE", "PROTECT_WITNESS", "AUDIT"][idx % 6]
    return ["PURGE", "DISCLOSE", "AUDIT", "PROTECT_WITNESS", "PROSECUTE", "PURGE"][idx % 6]


def _apply_success(world: Any, *, ward_id: str, domain: str, strength: float) -> dict[str, float]:
    effects: dict[str, float] = {}
    corruption = getattr(world, "corruption_by_ward", {}) or {}
    entry: CorruptionIndex | None = corruption.get(ward_id)
    if entry is None:
        return effects
    delta = _clamp01(0.05 + strength * 0.15)
    entry.capture = _clamp01(entry.capture * (1.0 - delta))
    entry.shadow_state = _clamp01(entry.shadow_state * (1.0 - delta))
    entry.petty = _clamp01(entry.petty * (1.0 - delta * 0.5))
    effects["capture_delta"] = -delta
    effects["shadow_delta"] = -delta
    effects["domain"] = domain
    return effects


def _apply_backlash(campaign: ReformCampaign, base: float) -> None:
    campaign.backlash = _clamp01(campaign.backlash + base)
    if campaign.backlash > 0.9:
        campaign.status = "FAILED"


def _apply_progress(campaign: ReformCampaign, delta: float) -> None:
    campaign.progress = _clamp01(campaign.progress + delta)
    if campaign.progress >= 1.0:
        campaign.status = "SUCCEEDED"


def _retaliation_prob(strength: float, cfg: ReformConfig) -> float:
    return _clamp01(strength * cfg.retaliation_scale)


def _campaign_shadow_strength(world: Any, ward_id: str) -> float:
    entry: CorruptionIndex | None = getattr(world, "corruption_by_ward", {}).get(ward_id)
    if entry is None:
        return 0.0
    return _clamp01(float(entry.shadow_state) + float(entry.capture) * 0.5)


def _success_prob(
    *,
    campaign: ReformCampaign,
    procedural_share: float,
    shadow_strength: float,
    cfg: ReformConfig,
) -> float:
    base = campaign.intensity * 0.4 + campaign.legitimacy_push * 0.2 + procedural_share * 0.4
    base -= shadow_strength * 0.5
    return _clamp01(cfg.success_scale * base + 0.15)


def _record_action(actions: list[ReformAction], action: ReformAction) -> None:
    actions.append(action)
    if len(actions) > 300:
        del actions[: len(actions) - 300]


def _update_metrics(world: Any, campaigns: Mapping[str, list[ReformCampaign]], actions: list[ReformAction]) -> None:
    metrics = ensure_metrics(world)
    reform_bucket = getattr(metrics, "gauges", {}).setdefault("reform", {})
    if not isinstance(reform_bucket, dict):
        return
    active = [c for lst in campaigns.values() for c in lst if c.status == "ACTIVE"]
    reform_bucket["campaigns_active"] = len(active)
    reform_bucket["avg_progress"] = sum(c.progress for c in active) / max(1, len(active))
    reform_bucket["audits_success"] = sum(1 for a in actions if a.result == "SUCCESS")
    reform_bucket["retaliations"] = sum(1 for a in actions if a.result == "SABOTAGED")


def run_reform_update(world: Any, *, day: int | None = None) -> None:
    cfg = ensure_reform_config(world)
    if not cfg.enabled:
        return
    current_day = int(day if day is not None else getattr(world, "day", 0))
    last_run = getattr(world, "reform_last_update_day", -1)
    if last_run == current_day:
        return

    state = ensure_sovereignty_state(world)
    polities = _polities(world)
    campaigns, actions = ensure_reform_ledgers(world, polities)
    territory = getattr(state, "territory", TerritoryState())

    for polity_id in polities:
        wards = _polity_wards(territory, polity_id)
        _maybe_spawn_campaign(world, polity_id=polity_id, wards=wards, cfg=cfg, day=current_day, campaigns=campaigns[polity_id])

    for polity_id in polities:
        wards = _polity_wards(territory, polity_id)
        procedural_share = _procedural_policing_share(world, wards)
        for campaign in campaigns.get(polity_id, []):
            if campaign.status != "ACTIVE":
                continue
            if current_day - campaign.last_update_day < cfg.update_cadence_days:
                continue
            candidates = _action_candidates(campaign)
            for idx, target in enumerate(candidates[: cfg.max_actions_per_update]):
                ward_id = target.get("ward_id", "")
                domain = target.get("domain", "UNKNOWN")
                shadow_strength = _campaign_shadow_strength(world, ward_id)
                success_prob = _success_prob(
                    campaign=campaign, procedural_share=procedural_share, shadow_strength=shadow_strength, cfg=cfg
                )
                retaliation_prob = _retaliation_prob(shadow_strength, cfg)
                action_type = _action_type_for_kind(campaign.kind, idx)
                roll = _stable_rand01(cfg.deterministic_salt, campaign.reform_id, ward_id, current_day, idx)
                result = "FAILED"
                effects: dict[str, object] = {}
                if roll < retaliation_prob:
                    result = "SABOTAGED"
                    _apply_backlash(campaign, cfg.backlash_scale * 0.5)
                elif roll < success_prob:
                    result = "SUCCESS"
                    strength = campaign.intensity * (1.2 if action_type == "PURGE" else 1.0)
                    effects = _apply_success(world, ward_id=ward_id, domain=domain, strength=strength)
                    _apply_progress(campaign, 0.25 + campaign.intensity * 0.25)
                else:
                    _apply_backlash(campaign, cfg.backlash_scale * 0.25)

                if action_type == "PURGE" and result == "SUCCESS":
                    _apply_backlash(campaign, cfg.backlash_scale)
                    _apply_progress(campaign, 0.2)

                _record_action(
                    actions,
                    ReformAction(
                        day=current_day,
                        reform_id=campaign.reform_id,
                        action_type=action_type,
                        ward_id=ward_id,
                        domain=domain,
                        result=result,
                        effects=effects,
                    ),
                )

                if result == "SABOTAGED":
                    record_event(
                        world,
                        {
                            "type": "REFORM_ACTION_SABOTAGED",
                            "reform_id": campaign.reform_id,
                            "ward_id": ward_id,
                            "polity_id": polity_id,
                            "day": current_day,
                        },
                    )

            campaign.last_update_day = current_day

    _update_metrics(world, campaigns, actions)
    world.reform_last_update_day = current_day


def export_reform_seed(world: Any) -> dict[str, object]:
    ensure_reform_config(world)
    campaigns = getattr(world, "reforms_by_polity", {}) or {}
    actions = getattr(world, "reform_actions", []) or []
    return {
        "config": asdict(world.reform_cfg),
        "campaigns": {pid: [asdict(c) for c in lst] for pid, lst in campaigns.items()},
        "actions": [asdict(a) for a in actions],
        "last_update_day": getattr(world, "reform_last_update_day", -1),
    }


def load_reform_seed(world: Any, payload: Mapping[str, object]) -> None:
    cfg = ensure_reform_config(world)
    for key, val in (payload.get("config", {}) or {}).items():
        if hasattr(cfg, key):
            setattr(cfg, key, val)
    campaigns_raw = payload.get("campaigns", {}) or {}
    campaigns: dict[str, list[ReformCampaign]] = {}
    for polity_id, entries in campaigns_raw.items():
        campaigns[polity_id] = []
        for entry in entries or []:
            campaigns[polity_id].append(ReformCampaign(**entry))
    actions_raw = payload.get("actions", []) or []
    actions = [ReformAction(**entry) for entry in actions_raw]
    world.reforms_by_polity = campaigns
    world.reform_actions = actions
    world.reform_last_update_day = int(payload.get("last_update_day", -1))


__all__ = [
    "ReformConfig",
    "ReformCampaign",
    "ReformAction",
    "ensure_reform_config",
    "ensure_reform_ledgers",
    "run_reform_update",
    "export_reform_seed",
    "load_reform_seed",
]
