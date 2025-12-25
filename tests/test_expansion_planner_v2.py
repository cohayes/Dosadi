from dosadi.runtime.expansion_planner_v2 import (
    ExpansionPlannerV2Config,
    ExpansionPlannerV2State,
    maybe_plan_expansion_v2,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.state import WorldState
from dosadi.world.construction import ProjectLedger
from dosadi.world.extraction import ExtractionSite, SiteKind, ensure_extraction
from dosadi.world.materials import Material, ensure_inventory_registry
from dosadi.world.survey_map import SurveyNode


def _basic_world(seed: int = 1) -> WorldState:
    world = WorldState(seed=seed)
    world.projects = ProjectLedger()
    return world


def _add_node(world: WorldState, node_id: str, hazard: float = 0.0, ward_id: str = "ward:core") -> None:
    world.survey_map.upsert_node(
        SurveyNode(
            node_id=node_id,
            kind="outpost_site",
            ward_id=ward_id,
            hazard=hazard,
            water=1.0,
            confidence=0.9,
            last_seen_tick=world.tick,
        ),
        confidence_delta=0.1,
    )


def _add_scrap_site(world: WorldState, node_id: str, richness: float = 1.0) -> None:
    ledger = ensure_extraction(world)
    site = ExtractionSite(
        site_id=f"site:{node_id}:scrap",
        kind=SiteKind.SCRAP_FIELD,
        node_id=node_id,
        created_day=world.day,
        richness=richness,
    )
    ledger.add(site)


def test_deterministic_plan_matches_between_clones() -> None:
    cfg = ExpansionPlannerV2Config(enabled=True)
    state_a = ExpansionPlannerV2State()
    state_b = ExpansionPlannerV2State()

    world_a = _basic_world(seed=10)
    world_b = _basic_world(seed=10)
    _add_node(world_a, "loc:a")
    _add_node(world_b, "loc:a")
    _add_scrap_site(world_a, "loc:a", richness=1.2)
    _add_scrap_site(world_b, "loc:a", richness=1.2)

    created_a = maybe_plan_expansion_v2(world_a, cfg=cfg, state=state_a)
    created_b = maybe_plan_expansion_v2(world_b, cfg=cfg, state=state_b)

    assert created_a == created_b
    assert state_a.last_plan_signature == state_b.last_plan_signature


def test_shortage_prefers_workshop() -> None:
    world = _basic_world(seed=11)
    _add_node(world, "loc:core")
    registry = ensure_inventory_registry(world)
    inv = registry.inv("loc:core")
    inv.items = {Material.FASTENERS: 0}

    cfg = ExpansionPlannerV2Config(enabled=True)
    state = ExpansionPlannerV2State()

    maybe_plan_expansion_v2(world, cfg=cfg, state=state)
    kinds = {project.kind for project in world.projects.projects.values()}
    assert "WORKSHOP" in kinds


def test_scrap_and_shortage_push_recycler() -> None:
    world = _basic_world(seed=12)
    _add_node(world, "loc:scrap")
    _add_scrap_site(world, "loc:scrap", richness=2.0)
    registry = ensure_inventory_registry(world)
    inv = registry.inv("loc:scrap")
    inv.items = {Material.SCRAP_METAL: 0}

    cfg = ExpansionPlannerV2Config(enabled=True)
    state = ExpansionPlannerV2State()

    maybe_plan_expansion_v2(world, cfg=cfg, state=state)
    kinds = {project.kind for project in world.projects.projects.values()}
    assert "RECYCLER" in kinds


def test_extraction_without_shortage_still_builds_depot() -> None:
    world = _basic_world(seed=13)
    _add_node(world, "loc:yield")
    _add_scrap_site(world, "loc:yield", richness=3.0)

    cfg = ExpansionPlannerV2Config(enabled=True)
    state = ExpansionPlannerV2State()

    maybe_plan_expansion_v2(world, cfg=cfg, state=state)
    kinds = {project.kind for project in world.projects.projects.values()}
    assert "DEPOT" in kinds


def test_cooldown_blocks_actions() -> None:
    world = _basic_world(seed=14)
    _add_node(world, "loc:cooldown")
    cfg = ExpansionPlannerV2Config(enabled=True, min_days_between_actions=5)
    state = ExpansionPlannerV2State(last_action_day=3, actions_taken_today=cfg.max_actions_per_day)
    world.day = 5

    created = maybe_plan_expansion_v2(world, cfg=cfg, state=state)
    assert created == []
    assert not world.projects.projects


def test_top_k_caps_actions_considered() -> None:
    world = _basic_world(seed=15)
    for idx in range(10):
        node_id = f"loc:{idx}"
        _add_node(world, node_id)
        _add_scrap_site(world, node_id, richness=1.0)
    cfg = ExpansionPlannerV2Config(enabled=True, top_k_nodes=3, top_k_actions=3, max_actions_per_day=2)
    state = ExpansionPlannerV2State()

    maybe_plan_expansion_v2(world, cfg=cfg, state=state)

    metrics = world.metrics.get("planner_v2", {})
    assert metrics.get("actions_considered", 0) <= cfg.top_k_actions
    assert metrics.get("actions_taken", 0) <= cfg.max_actions_per_day


def test_snapshot_roundtrip_keeps_plans_deterministic() -> None:
    world = _basic_world(seed=16)
    _add_node(world, "loc:snap")
    _add_scrap_site(world, "loc:snap", richness=1.5)
    cfg = ExpansionPlannerV2Config(enabled=True)
    state = ExpansionPlannerV2State()

    maybe_plan_expansion_v2(world, cfg=cfg, state=state)
    snap = snapshot_world(world, scenario_id="planner-v2")
    restored = restore_world(snap)
    restored_state = getattr(restored, "plan2_state", ExpansionPlannerV2State())
    restored_cfg = getattr(restored, "plan2_cfg", cfg)

    maybe_plan_expansion_v2(restored, cfg=restored_cfg, state=restored_state)

    assert world_signature(world) == world_signature(restored)
