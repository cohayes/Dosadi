"""Group structures and helper logic for pods and proto-councils (D-AGENT-0025)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING
import random
import uuid

from .core import (
    AgentState,
    Goal,
    GoalHorizon,
    GoalOrigin,
    GoalStatus,
    GoalType,
    make_goal_id,
)

if TYPE_CHECKING:
    from dosadi.runtime.founding_wakeup import RuntimeConfig


class GroupType(str, Enum):
    POD = "POD"
    COUNCIL = "COUNCIL"
    TASK_FORCE = "TASK_FORCE"  # may be used later for scouts, etc.


class GroupRole(str, Enum):
    MEMBER = "MEMBER"
    POD_REPRESENTATIVE = "POD_REPRESENTATIVE"
    COUNCIL_MEMBER = "COUNCIL_MEMBER"
    SCOUT = "SCOUT"
    SCRIBE = "SCRIBE"


@dataclass
class Group:
    """MVP group representation for pods and proto-councils."""

    group_id: str
    group_type: GroupType
    name: str

    member_ids: List[str] = field(default_factory=list)
    roles_by_agent: Dict[str, List[GroupRole]] = field(default_factory=dict)

    goal_ids: List[str] = field(default_factory=list)

    parent_location_id: Optional[str] = None  # e.g. "loc:pod-1" or "loc:well-core"
    created_at_tick: int = 0
    last_meeting_tick: int = 0

    tags: List[str] = field(default_factory=list)


def make_group_id(prefix: str = "group") -> str:
    return f"{prefix}:{uuid.uuid4().hex}"


# Simple in-module registry so helper functions can detect existing goals that were
# created via this module. This avoids tight coupling to any global store while still
# letting ensure_* helpers be idempotent when called repeatedly.
_GOAL_REGISTRY: Dict[str, Goal] = {}


def create_pod_group(pod_location_id: str, member_ids: List[str], tick: int) -> Group:
    """
    Create a Group of type POD for a given pod location.

    - group_id can be derived from the location id or generated via make_group_id.
    - parent_location_id is set to pod_location_id.
    - Each member gets GroupRole.MEMBER in roles_by_agent.
    """
    group_id = f"group:pod:{pod_location_id.split(':')[-1]}"
    group = Group(
        group_id=group_id,
        group_type=GroupType.POD,
        name=f"Pod group {pod_location_id}",
        member_ids=list(member_ids),
        parent_location_id=pod_location_id,
        created_at_tick=tick,
        last_meeting_tick=tick,
    )

    for aid in member_ids:
        roles = group.roles_by_agent.setdefault(aid, [])
        if GroupRole.MEMBER not in roles:
            roles.append(GroupRole.MEMBER)

    return group


def create_proto_council(member_ids: List[str], tick: int) -> Group:
    """
    Create the initial proto-council Group at the well-core hub.

    - group_type = COUNCIL
    - parent_location_id = "loc:well-core"
    - Members get COUNCIL_MEMBER role.
    """
    group_id = "group:council:alpha"  # fixed id is fine for MVP
    group = Group(
        group_id=group_id,
        group_type=GroupType.COUNCIL,
        name="Founding Proto-Council",
        member_ids=list(member_ids),
        parent_location_id="loc:well-core",
        created_at_tick=tick,
        last_meeting_tick=tick,
    )

    for aid in member_ids:
        roles = group.roles_by_agent.setdefault(aid, [])
        if GroupRole.COUNCIL_MEMBER not in roles:
            roles.append(GroupRole.COUNCIL_MEMBER)

    return group


def maybe_run_pod_meeting(
    pod_group: Group,
    agents_by_id: Dict[str, AgentState],
    tick: int,
    rng: random.Random,
    meeting_interval_ticks: int,
    rep_vote_fraction_threshold: float = 0.4,
    min_leadership_threshold: float = 0.6,
    max_representatives: int = 2,
) -> None:
    """
    Possibly run a pod meeting and update pod representatives.

    - Only run if enough ticks have passed since last_meeting_tick.
    - Attendees are agents whose location_id == pod_group.parent_location_id.
    - Each attendee 'votes' for the most competent podmate (based on leadership_weight).
    - Candidate becomes POD_REPRESENTATIVE if:
      - They get >= rep_vote_fraction_threshold of votes, AND
      - Their leadership_weight >= min_leadership_threshold.
    - Ensure at most max_representatives reps per pod.
    """
    if meeting_interval_ticks <= 0:
        return

    if tick - pod_group.last_meeting_tick < meeting_interval_ticks:
        return

    # Determine attendees
    location_id = pod_group.parent_location_id
    if location_id is None:
        return

    attendees = [
        aid
        for aid in pod_group.member_ids
        if (aid in agents_by_id and agents_by_id[aid].location_id == location_id)
    ]
    if len(attendees) < 2:
        # Not enough people to form opinions
        pod_group.last_meeting_tick = tick
        return

    # Voting: each attendee picks a candidate based on leadership_weight
    votes: Dict[str, int] = {}
    for voter_id in attendees:
        # Candidate pool: all pod members (including self for simplicity)
        candidates = [
            aid for aid in pod_group.member_ids
            if aid in agents_by_id
        ]
        if not candidates:
            continue
        # Score each candidate
        best_id = None
        best_score = float("-inf")
        for cid in candidates:
            leadership = agents_by_id[cid].personality.leadership_weight
            noise = rng.uniform(-0.05, 0.05)
            score = leadership + noise
            if score > best_score:
                best_score = score
                best_id = cid
        if best_id is not None:
            votes[best_id] = votes.get(best_id, 0) + 1

    if not votes:
        pod_group.last_meeting_tick = tick
        return

    # Who is currently a representative?
    current_reps = {
        aid
        for aid, roles in pod_group.roles_by_agent.items()
        if GroupRole.POD_REPRESENTATIVE in roles
    }

    previous_reps = set(current_reps)

    total_votes = sum(votes.values())
    # Sort candidates by vote count
    ranked = sorted(votes.items(), key=lambda kv: kv[1], reverse=True)

    new_reps = set(current_reps)
    for candidate_id, count in ranked:
        frac = count / total_votes
        agent = agents_by_id.get(candidate_id)
        if agent is None:
            continue
        if frac >= rep_vote_fraction_threshold and agent.personality.leadership_weight >= min_leadership_threshold:
            new_reps.add(candidate_id)
        if len(new_reps) >= max_representatives:
            break

    # Update roles_by_agent to reflect new_reps
    for aid in pod_group.member_ids:
        roles = pod_group.roles_by_agent.setdefault(aid, [])
        if aid in new_reps:
            if GroupRole.POD_REPRESENTATIVE not in roles:
                roles.append(GroupRole.POD_REPRESENTATIVE)
        else:
            if GroupRole.POD_REPRESENTATIVE in roles:
                roles.remove(GroupRole.POD_REPRESENTATIVE)

    pod_group.last_meeting_tick = tick

    newly_added_reps = new_reps - previous_reps
    for aid in newly_added_reps:
        agent = agents_by_id.get(aid)
        if agent is None:
            continue
        existing = next((g for g in agent.goals if g.goal_type == GoalType.FORM_GROUP), None)
        if existing:
            existing.priority = max(existing.priority, 0.95)
            existing.urgency = max(existing.urgency, 0.95)
            existing.status = GoalStatus.ACTIVE
            existing.last_updated_tick = tick
            continue
        form_group_goal = Goal(
            goal_id=make_goal_id(),
            owner_id=agent.agent_id,
            goal_type=GoalType.FORM_GROUP,
            description="Join or build a council to represent the pod.",
            priority=0.95,
            urgency=0.95,
            horizon=GoalHorizon.SHORT,
            status=GoalStatus.ACTIVE,
            origin=GoalOrigin.GROUP_DECISION,
            created_at_tick=tick,
            last_updated_tick=tick,
        )
        agent.goals.append(form_group_goal)


def maybe_form_proto_council(
    groups: List[Group],
    agents_by_id: Dict[str, AgentState],
    tick: int,
    hub_location_id: str = "loc:well-core",
    max_council_size: int = 10,
) -> Optional[Group]:
    """
    Create or extend the proto-council if conditions are met.

    - If a COUNCIL group exists, return it (after adding any new reps present).
    - If no COUNCIL exists:
      - Find pod representatives at hub_location_id.
      - If >= 2 present, create a new council group.
    """
    council = next((g for g in groups if g.group_type == GroupType.COUNCIL), None)

    # Identify all pod reps currently at hub
    rep_ids_at_hub: List[str] = []
    for g in groups:
        if g.group_type != GroupType.POD:
            continue
        for aid, roles in g.roles_by_agent.items():
            if GroupRole.POD_REPRESENTATIVE in roles:
                agent = agents_by_id.get(aid)
                if agent and agent.location_id == hub_location_id:
                    rep_ids_at_hub.append(aid)

    rep_ids_at_hub = list(set(rep_ids_at_hub))

    if council is None:
        if len(rep_ids_at_hub) < 2:
            return None
        council = create_proto_council(rep_ids_at_hub, tick)
        groups.append(council)
        return council

    # Council exists; add new reps up to max size
    for aid in rep_ids_at_hub:
        if aid not in council.member_ids and len(council.member_ids) < max_council_size:
            council.member_ids.append(aid)
            roles = council.roles_by_agent.setdefault(aid, [])
            if GroupRole.COUNCIL_MEMBER not in roles:
                roles.append(GroupRole.COUNCIL_MEMBER)

    return council


def maybe_run_council_meeting(
    council_group: Group,
    agents_by_id: Dict[str, AgentState],
    tick: int,
    rng: random.Random,
    cooldown_ticks: int,
    hub_location_id: str = "loc:well-core",
    metrics: Optional[Dict[str, float]] = None,
    cfg: Optional["RuntimeConfig"] = None,
) -> None:
    """
    Possibly run a council meeting.

    - Requires at least 2 council members present at hub_location_id.
    - Enforce cooldown based on last_meeting_tick.
    - If meeting occurs:
      - Generate COUNCIL_MEETING episodes for participants (TODO in agent loop).
      - Council can later aggregate hazard episodes and create group goals.
    """
    if cooldown_ticks <= 0:
        return

    if tick - council_group.last_meeting_tick < cooldown_ticks:
        return

    present_members = [aid for aid in council_group.member_ids if aid in agents_by_id]

    if len(present_members) < 1:
        return

    # For now, groups.py just updates last_meeting_tick.
    # Actual episode creation will be handled in the simulation loop
    # using this event as a trigger.
    council_group.last_meeting_tick = tick

    if metrics is None or cfg is None:
        return

    dangerous_edge_ids = _find_dangerous_corridors_from_metrics(
        metrics=metrics,
        min_incidents_for_protocol=cfg.min_incidents_for_protocol,
        risk_threshold_for_protocol=cfg.risk_threshold_for_protocol,
    )

    if not dangerous_edge_ids:
        return

    scribe_agent_id = _select_council_scribe(council_group, agents_by_id)
    if scribe_agent_id is None:
        return

    scribe = agents_by_id.get(scribe_agent_id)
    if scribe is None:
        return

    target = {
        "edge_ids": dangerous_edge_ids,
        "corridor_ids": list(dangerous_edge_ids),
        "council_group_id": council_group.group_id,
    }

    author_goal = Goal(
        goal_id=make_goal_id(),
        owner_id=scribe.agent_id,
        goal_type=GoalType.AUTHOR_PROTOCOL,
        description=(
            f"Draft movement/safety protocol for dangerous corridors: "
            + ", ".join(dangerous_edge_ids)
        ),
        target=target,
        priority=0.95,
        urgency=0.95,
        horizon=GoalHorizon.MEDIUM,
        status=GoalStatus.ACTIVE,
        origin=GoalOrigin.GROUP_DECISION,
        created_at_tick=tick,
        last_updated_tick=tick,
    )

    scribe.goals.append(author_goal)

    roles = council_group.roles_by_agent.setdefault(scribe.agent_id, [])
    if GroupRole.SCRIBE not in roles:
        roles.append(GroupRole.SCRIBE)


def ensure_council_gather_information_goal(
    council_group: Group,
    corridors_of_interest: List[str],
    tick: int,
) -> Goal:
    """
    Ensure the council has an active GATHER_INFORMATION group goal.

    - If an ACTIVE goal of this type already exists, return it.
    - Otherwise, create one and add its id to council_group.goal_ids.
    """
    # Check existing goals created via this module's registry.
    for goal_id in council_group.goal_ids:
        existing = _GOAL_REGISTRY.get(goal_id)
        if existing and existing.goal_type == GoalType.GATHER_INFORMATION and existing.status == GoalStatus.ACTIVE:
            return existing

    goal = Goal(
        goal_id=make_goal_id(),
        owner_id=council_group.group_id,
        goal_type=GoalType.GATHER_INFORMATION,
        description="Gather information about corridor risk.",
        target={"corridor_ids": corridors_of_interest},
        priority=0.95,
        urgency=0.95,
        horizon=GoalHorizon.MEDIUM,
        status=GoalStatus.ACTIVE,
        created_at_tick=tick,
        last_updated_tick=tick,
        origin=GoalOrigin.GROUP_DECISION,
    )
    council_group.goal_ids.append(goal.goal_id)
    _GOAL_REGISTRY[goal.goal_id] = goal
    return goal


def project_gather_information_to_scouts(
    council_group: Group,
    group_goal: Goal,
    agents_by_id: Dict[str, AgentState],
    rng: random.Random,
    max_scouts: int = 3,
) -> None:
    """
    Assign GATHER_INFORMATION goals to selected scouts.

    - Select up to max_scouts agents favoring higher DEX/END and bravery.
    - Add SCOUT role for each in council_group.roles_by_agent.
    - Append a personal GATHER_INFORMATION goal to each AgentState.goals with
      origin = GROUP_DECISION.
    """
    candidates = [
        agents_by_id[aid]
        for aid in council_group.member_ids
        if aid in agents_by_id
    ]
    if not candidates:
        return

    def scout_score(agent: AgentState) -> float:
        return (
            agent.attributes.DEX
            + agent.attributes.END
            + 5.0 * agent.personality.bravery
        )

    candidates.sort(key=scout_score, reverse=True)
    chosen = candidates[:max_scouts]

    for agent in chosen:
        roles = council_group.roles_by_agent.setdefault(agent.agent_id, [])
        if GroupRole.SCOUT not in roles:
            roles.append(GroupRole.SCOUT)
        personal_goal = Goal(
            goal_id=make_goal_id(),
            owner_id=agent.agent_id,
            goal_type=GoalType.GATHER_INFORMATION,
            description="Scout corridors on behalf of the council.",
            parent_goal_id=group_goal.goal_id,
            target={
                "corridor_ids": group_goal.target.get("corridor_ids", []),
                "group_goal_id": group_goal.goal_id,
            },
            priority=0.95,
            urgency=0.95,
            horizon=GoalHorizon.SHORT,
            status=GoalStatus.ACTIVE,
            created_at_tick=group_goal.created_at_tick,
            last_updated_tick=group_goal.last_updated_tick,
            origin=GoalOrigin.GROUP_DECISION,
        )
        agent.goals.append(personal_goal)


def project_author_protocol_to_scribe(
    council_group: Group,
    group_goal: Goal,
    agents_by_id: Dict[str, AgentState],
    rng: random.Random,
) -> None:
    """
    Assign an AUTHOR_PROTOCOL goal to a selected scribe.

    - Choose scribe favoring higher INT/WIL and lower curiosity (routine-seeking).
    - Add SCRIBE role.
    - Append an AUTHOR_PROTOCOL goal to AgentState.goals with origin = GROUP_DECISION.
    """
    candidates = [
        agents_by_id[aid]
        for aid in council_group.member_ids
        if aid in agents_by_id
    ]
    if not candidates:
        return

    def scribe_score(agent: AgentState) -> float:
        return (
            agent.attributes.INT
            + agent.attributes.WIL
            + 5.0 * (1.0 - agent.personality.curiosity)
        )

    candidates.sort(key=scribe_score, reverse=True)
    scribe = candidates[0]

    roles = council_group.roles_by_agent.setdefault(scribe.agent_id, [])
    if GroupRole.SCRIBE not in roles:
        roles.append(GroupRole.SCRIBE)

    personal_goal = Goal(
        goal_id=make_goal_id(),
        owner_id=scribe.agent_id,
        goal_type=GoalType.AUTHOR_PROTOCOL,
        description="Draft a movement/safety protocol for high-risk corridors.",
        parent_goal_id=group_goal.goal_id,
        target={
            "corridor_ids": group_goal.target.get("corridor_ids", []),
            "group_goal_id": group_goal.goal_id,
        },
        priority=0.95,
        urgency=0.95,
        horizon=GoalHorizon.MEDIUM,
        status=GoalStatus.ACTIVE,
        created_at_tick=group_goal.created_at_tick,
        last_updated_tick=group_goal.last_updated_tick,
        origin=GoalOrigin.GROUP_DECISION,
    )
    scribe.goals.append(personal_goal)


def _find_dangerous_corridors_from_metrics(
    metrics: Dict[str, float],
    min_incidents_for_protocol: int,
    risk_threshold_for_protocol: float,
) -> List[str]:
    """
    Inspect world-level metrics and return a list of corridor/edge ids that are
    'dangerous enough' to warrant a movement protocol.

    Uses keys like:
      - 'traversals:{edge_id}'
      - 'incidents:{edge_id}'
    """
    dangerous: List[str] = []

    for key, traversals_val in metrics.items():
        if not key.startswith("traversals:"):
            continue

        edge_id = key.split(":", 1)[1]
        traversals = float(traversals_val)
        if traversals <= 0:
            continue

        incidents_key = f"incidents:{edge_id}"
        incidents = float(metrics.get(incidents_key, 0.0))
        if incidents < float(min_incidents_for_protocol):
            continue

        risk = incidents / traversals
        if risk >= risk_threshold_for_protocol:
            dangerous.append(edge_id)

    return dangerous


def _select_council_scribe(
    council_group: Group,
    agents_by_id: Dict[str, AgentState],
) -> Optional[str]:
    """
    Choose a scribe from council members, favoring higher INT/WIL and
    more routine-seeking personalities (lower curiosity).
    """
    best_id: Optional[str] = None
    best_score: float = float("-inf")

    for aid in council_group.member_ids:
        agent = agents_by_id.get(aid)
        if agent is None:
            continue

        attrs = agent.attributes
        personality = agent.personality
        score = (
            float(attrs.INT)
            + float(attrs.WIL)
            + 5.0 * (1.0 - float(personality.curiosity))
        )
        if score > best_score:
            best_score = score
            best_id = aid

    return best_id
