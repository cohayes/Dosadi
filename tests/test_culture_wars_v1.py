import json

import pytest

from dosadi.agent.beliefs import Belief, BeliefStore
from dosadi.agents.core import AgentState
from dosadi.runtime.culture_wars import (
    CultureConfig,
    WardCultureState,
    culture_signature,
    run_culture_for_day,
)
from dosadi.runtime.factions import Opportunity, _success_probability
from dosadi.runtime.institutions import ensure_state, run_institutions_for_day
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.timewarp import DEFAULT_TICKS_PER_DAY
from dosadi.vault.seed_vault import save_seed
from dosadi.world.factions import Faction
from dosadi.world.survey_map import SurveyMap, SurveyNode
from dosadi.state import WardState, WorldState


def _make_world() -> WorldState:
    world = WorldState(seed=123)
    world.culture_cfg = CultureConfig(enabled=True, max_norms_per_ward=4)
    world.inst_cfg.enabled = True

    ward = WardState(id="ward:a", name="Alpha", ring=1, sealed_mode="core")
    ward.need_index = 0.8
    world.register_ward(ward)

    survey_map = SurveyMap()
    survey_map.nodes["loc:a"] = SurveyNode(node_id="loc:a", kind="facility", ward_id="ward:a")
    world.survey_map = survey_map

    agent = AgentState(agent_id="agent:1", name="Agent One")
    agent.location_id = "loc:a"
    agent.beliefs = BeliefStore(max_items=8)
    agent.beliefs.upsert(Belief(key="belief:predation_fear", value=0.9, weight=0.9, last_day=0))
    agent.beliefs.upsert(Belief(key="belief:queue_fairness", value=0.8, weight=0.8, last_day=0))
    agent.beliefs.upsert(Belief(key="belief:anger", value=0.7, weight=0.7, last_day=0))
    world.agents[agent.agent_id] = agent

    world.ticks_per_day = DEFAULT_TICKS_PER_DAY
    world.day = 1
    return world


def test_culture_determinism() -> None:
    world_a = _make_world()
    run_culture_for_day(world_a, day=world_a.day)
    sig_a = culture_signature(world_a)

    world_b = _make_world()
    run_culture_for_day(world_b, day=world_b.day)
    sig_b = culture_signature(world_b)

    assert sig_a == sig_b


def test_culture_norm_caps_and_eviction() -> None:
    world = _make_world()
    world.culture_cfg.max_norms_per_ward = 2
    agent = next(iter(world.agents.values()))
    agent.beliefs.upsert(Belief(key="belief:shortage_corruption", value=1.0, weight=0.9, last_day=0))
    agent.beliefs.upsert(Belief(key="belief:guild_pride", value=0.6, weight=0.6, last_day=0))

    run_culture_for_day(world, day=world.day)

    state = world.culture_by_ward["ward:a"]
    assert len(state.norms) == 2
    assert set(state.norms.keys()) == {"norm:anti_raider", "norm:queue_order"}


def test_culture_modifies_institution_legitimacy() -> None:
    base_world = _make_world()
    culture_world = _make_world()
    culture_world.culture_by_ward["ward:a"] = WardCultureState(
        ward_id="ward:a", norms={"norm:anti_state": 0.9, "norm:queue_order": 0.1}
    )

    for world in (base_world, culture_world):
        inst_state = ensure_state(world, "ward:a", cfg=world.inst_cfg)
        inst_state.legitimacy = 0.6
        inst_state.discipline = 0.5

    run_institutions_for_day(base_world, day=base_world.day)
    run_institutions_for_day(culture_world, day=culture_world.day)

    base_legitimacy = base_world.inst_state_by_ward["ward:a"].legitimacy
    culture_legitimacy = culture_world.inst_state_by_ward["ward:a"].legitimacy
    assert culture_legitimacy < base_legitimacy


def test_culture_shifts_faction_success_probability() -> None:
    world_plain = _make_world()
    world_plain.culture_cfg.enabled = False

    world_culture = _make_world()
    world_culture.culture_by_ward["ward:a"] = WardCultureState(
        ward_id="ward:a", norms={"norm:smuggling_tolerance": 0.9}
    )

    faction = Faction(faction_id="fac:raiders", name="Raiders", kind="RAIDERS")
    opportunity = Opportunity(kind="ward", target_id="ward:a", value=0.5)

    prob_plain = _success_probability(faction, opportunity, world_plain)
    prob_culture = _success_probability(faction, opportunity, world_culture)

    assert prob_culture > prob_plain


def test_culture_persists_snapshot_and_seed(tmp_path) -> None:
    world = _make_world()
    world.culture_by_ward["ward:a"] = WardCultureState(
        ward_id="ward:a",
        norms={"norm:anti_state": 0.4, "norm:anti_raider": 0.2},
        alignment={"fac:state": -0.1},
        last_updated_day=world.day,
    )

    snapshot = snapshot_world(world, scenario_id="scenario")
    restored = restore_world(snapshot)

    restored_state = restored.culture_by_ward["ward:a"]
    assert pytest.approx(restored_state.norms["norm:anti_state"], rel=1e-6) == 0.4
    assert pytest.approx(restored_state.alignment["fac:state"], rel=1e-6) == -0.1

    save_seed(tmp_path, world, seed_id="seed-1", scenario_id="scenario")
    payload_path = tmp_path / "seeds" / "seed-1" / "culture.json"
    assert payload_path.exists()
    payload = json.loads(payload_path.read_text())
    assert payload.get("schema") == "culture_v1"
    assert payload["wards"][0]["ward_id"] == "ward:a"
