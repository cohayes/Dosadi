from __future__ import annotations

from dosadi.agents.core import PlaceBelief
from dosadi.memory.episodes import Episode, EpisodeVerb


def apply_episode_to_place_belief(pb: PlaceBelief, ep: Episode) -> None:
    """
    Extend PlaceBelief updates with verb-aware consolidation hooks.

    Base tag-driven updates are still handled via PlaceBelief.update_from_episode;
    this function adds lightweight adjustments for new standardized verbs used by
    work details (D-MEMORY-0210).
    """

    pb.update_from_episode(ep)

    verb = ep.verb

    if verb == EpisodeVerb.SCOUT_PLACE:
        _apply_scout_place_to_place(pb, ep)
    elif verb == EpisodeVerb.CORRIDOR_CROWDING_OBSERVED:
        _apply_corridor_crowding_to_place(pb, ep)
    elif verb == EpisodeVerb.FOOD_SERVED:
        _apply_food_served_to_place(pb, ep)
    elif verb == EpisodeVerb.QUEUE_SERVED:
        _apply_queue_served_to_place(pb, ep)
    elif verb == EpisodeVerb.QUEUE_DENIED:
        _apply_queue_denied_to_place(pb, ep)
    elif verb == EpisodeVerb.FOOD_SHORTAGE_EPISODE:
        _apply_food_shortage_to_place(pb, ep)
    elif verb == EpisodeVerb.LEAK_FOUND:
        _apply_leak_found_to_place(pb, ep)
    elif verb == EpisodeVerb.ENV_NODE_TUNED:
        after = float(getattr(ep, "details", {}).get("comfort_after", pb.comfort_score))
        alpha = 0.3
        pb.comfort_score = (1 - alpha) * pb.comfort_score + alpha * after
        pb.reliability_score = min(1.0, pb.reliability_score + 0.05)
    elif verb == EpisodeVerb.BODY_SIGNAL and ep.details.get("signal_type") == "ENV_COMFORTABLE":
        intensity = float(ep.details.get("intensity", 0.5))
        pb.comfort_score = min(1.0, pb.comfort_score + 0.05 * intensity)
        pb.safety_score = min(1.0, pb.safety_score + 0.02 * intensity)
    elif verb == EpisodeVerb.BODY_SIGNAL and ep.details.get("signal_type") == "ENV_UNCOMFORTABLE":
        intensity = float(ep.details.get("intensity", 0.5))
        pb.comfort_score = max(0.0, pb.comfort_score - 0.05 * intensity)
        pb.safety_score = max(0.0, pb.safety_score - 0.02 * intensity)
    elif verb == EpisodeVerb.WELL_PUMPED:
        pb.reliability_score = min(1.0, pb.reliability_score + 0.02)
    elif verb == EpisodeVerb.WATER_DELIVERED:
        pb.reliability_score = min(1.0, pb.reliability_score + 0.03)
        pb.safety_score = min(1.0, pb.safety_score + 0.01)
    elif verb == EpisodeVerb.DRANK_WATER:
        before = float(ep.details.get("hydration_before", 0.5))
        after = float(ep.details.get("hydration_after", 0.8))
        delta = max(0.0, after - before)

        pb.reliability_score = min(1.0, pb.reliability_score + 0.05 + 0.05 * delta)
        pb.comfort_score = min(1.0, pb.comfort_score + 0.03 * delta)
    elif verb == EpisodeVerb.WATER_DENIED:
        pb.reliability_score = max(0.0, pb.reliability_score - 0.08)
        pb.fairness_score = max(0.0, pb.fairness_score - 0.05)

    _clamp_belief_scores(pb)


def _apply_scout_place_to_place(pb: PlaceBelief, ep: Episode) -> None:
    hazard = float(getattr(ep, "details", {}).get("hazard_level", 0.0))
    hazard = max(0.0, min(1.0, hazard))
    target = 1.0 - hazard
    alpha = 0.15
    pb.safety_score += alpha * (target - pb.safety_score)


def _apply_corridor_crowding_to_place(pb: PlaceBelief, ep: Episode) -> None:
    density = float(getattr(ep, "details", {}).get("estimated_density", 0.0))
    density = max(0.0, min(1.0, density))
    alpha = 0.2
    pb.congestion_score += alpha * (density - pb.congestion_score)

    if getattr(ep, "emotion", None) and ep.emotion.valence < 0:
        pb.comfort_score += 0.1 * (-abs(ep.emotion.valence))


def _apply_food_served_to_place(pb: PlaceBelief, ep: Episode) -> None:
    wait_ticks = float(getattr(ep, "details", {}).get("wait_ticks", 0))
    normalized_wait = min(1.0, max(0.0, wait_ticks / 10_000.0))

    pb.reliability_score += 0.1 * (1.0 - pb.reliability_score)
    pb.congestion_score += 0.1 * (normalized_wait - pb.congestion_score)

    if getattr(ep, "emotion", None) and ep.emotion.valence > 0:
        pb.comfort_score += 0.05 * ep.emotion.valence


def _apply_queue_served_to_place(pb: PlaceBelief, ep: Episode) -> None:
    wait_ticks = float(getattr(ep, "details", {}).get("wait_ticks", 0))
    normalized_wait = min(1.0, max(0.0, wait_ticks / 10_000.0))

    pb.reliability_score += 0.05 * (1.0 - pb.reliability_score)
    pb.fairness_score += 0.05 * (1.0 - normalized_wait - pb.fairness_score)
    pb.congestion_score += 0.1 * (normalized_wait - pb.congestion_score)

    if getattr(ep, "emotion", None):
        pb.comfort_score += 0.05 * ep.emotion.valence


def _apply_queue_denied_to_place(pb: PlaceBelief, ep: Episode) -> None:
    wait_ticks = float(getattr(ep, "details", {}).get("wait_ticks", 0))
    normalized_wait = min(1.0, max(0.0, wait_ticks / 10_000.0))

    pb.reliability_score -= 0.1 * (1.0 - normalized_wait)
    pb.fairness_score -= 0.1
    pb.congestion_score += 0.05 * normalized_wait

    if getattr(ep, "emotion", None):
        pb.comfort_score -= 0.05 * (1.0 + max(0.0, -ep.emotion.valence))


def _apply_food_shortage_to_place(pb: PlaceBelief, ep: Episode) -> None:
    severity = float(getattr(ep, "details", {}).get("severity", 0.5))
    severity = max(0.0, min(1.0, severity))
    pb.reliability_score -= 0.15 * severity
    pb.fairness_score -= 0.1 * severity
    pb.congestion_score += 0.05 * severity
    pb.comfort_score -= 0.05 * severity


def _apply_leak_found_to_place(pb: PlaceBelief, ep: Episode) -> None:
    severity = float(getattr(ep, "details", {}).get("severity", 0.5))
    severity = max(0.0, min(1.0, severity))
    pb.safety_score -= 0.15 * severity
    pb.reliability_score -= 0.1 * severity


def _clamp_belief_scores(pb: PlaceBelief) -> None:
    pb.safety_score = _clamp_range(pb.safety_score)
    pb.congestion_score = _clamp_range(pb.congestion_score)
    pb.reliability_score = _clamp_range(pb.reliability_score)
    pb.comfort_score = _clamp_range(pb.comfort_score)


def _clamp_range(x: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, x))
