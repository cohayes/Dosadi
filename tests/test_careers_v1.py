from dosadi.runtime.careers import promotion_review, role_registry, update_careers_for_day
from dosadi.state import WardState, WorldState
from dosadi.agents.core import AgentState


def _world_with_careers() -> WorldState:
    world = WorldState(seed=99)
    world.career_cfg.enabled = True
    world.wards["w1"] = WardState(id="w1", name="Ward One", ring=0, sealed_mode="open")
    return world


def test_role_registry_includes_entry_verbs() -> None:
    registry = role_registry()
    queue = registry["civic.queue_attendant"]
    assert {"INSPECT", "EMPATHIZE", "RECORD"}.issubset(set(queue.verbs))

    courier = registry["espionage.shadow_courier"]
    assert {"SNEAK", "CONCEAL"}.issubset(set(courier.verbs))


def test_generate_postings_per_branch_and_ward() -> None:
    world = _world_with_careers()
    world.wards["w2"] = WardState(id="w2", name="Ward Two", ring=1, sealed_mode="open")

    update_careers_for_day(world, day=1)

    expected = sum(world.career_cfg.per_ward_min_slots.values()) * 2
    assert len(world.labor_postings) == expected

    sample_posting = world.labor_postings[0]
    assert sample_posting["ration_tier"] == world.career_roles[sample_posting["role_id"]].ration_tier


def test_promotion_review_advances_agent() -> None:
    world = _world_with_careers()
    registry = role_registry()
    world.career_roles = registry

    agent = world.agents.setdefault(
        "a1",
        AgentState(
            agent_id="a1",
            name="Tester",
            assignment_role="civic.queue_attendant",
            total_ticks_employed=15_000,
        ),
    )

    promotion_review(world, day=7)

    assert agent.assignment_role == "civic.queue_marshal"
    assert world.career_events[0]["type"] == "PromotionGranted"
    assert world.career_last_run_day == 7
