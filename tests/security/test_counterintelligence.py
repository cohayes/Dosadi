import pytest

from dosadi.security.counterintelligence import (
    CIPosture,
    CIState,
    InfiltrationAttempt,
    seed_default_ci_states,
)


def test_ci_state_recompute_uses_doc_levers():
    posture = CIPosture(ward_id="dosadi", level=2, driver="scandal", active_assets={})
    ci_state = CIState(
        node_id="checkpoint_alpha",
        node_type="checkpoint",
        ward_id="dosadi",
        base_exposure=0.6,
        oversight_strength=0.2,
        patronage_entanglement=0.4,
        doctrine_modifier=0.1,
        recent_incident_pressure=0.3,
    )

    ci_state.recompute(posture, global_stress=0.5, fragmentation=0.2)

    assert ci_state.infiltration_risk == pytest.approx(0.85, rel=0.05)
    assert ci_state.suspicion_score == pytest.approx(0.28, rel=0.05)
    assert ci_state.investigation_level == "none"


def test_infiltration_attempt_penalizes_high_posture():
    ci_state = CIState(
        node_id="command_node",
        node_type="command",
        ward_id="dosadi",
        base_exposure=0.55,
        oversight_strength=0.35,
        patronage_entanglement=0.5,
        doctrine_modifier=0.15,
        recent_incident_pressure=0.1,
    )
    relaxed = CIPosture(ward_id="dosadi", level=0, driver="routine", active_assets={})
    paranoid = CIPosture(ward_id="dosadi", level=3, driver="purge_campaign", active_assets={})
    ci_state.recompute(relaxed, global_stress=0.2, fragmentation=0.05)

    attempt = InfiltrationAttempt(
        id="bribe_probe",
        actor_type="guild_faction",
        target_node_id=ci_state.node_id,
        method="bribe",
        difficulty=0.4,
    )

    relaxed_prob = attempt.success_probability(ci_state, relaxed)
    paranoid_prob = attempt.success_probability(ci_state, paranoid)

    assert relaxed_prob > paranoid_prob
    assert 0.0 <= paranoid_prob <= 1.0


def test_seed_default_ci_states_produces_rankable_nodes():
    posture = CIPosture(ward_id="dosadi", level=1, driver="routine", active_assets={"espionage_branch_cells": 1})
    states = seed_default_ci_states("dosadi")
    assert len(states) == 3
    for ci_state in states:
        ci_state.recompute(posture, global_stress=0.1, fragmentation=0.05)
    risks = sorted((state.infiltration_risk for state in states), reverse=True)
    assert risks[0] >= risks[-1]

