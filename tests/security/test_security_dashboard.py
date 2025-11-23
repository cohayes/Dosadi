from dosadi.security.counterintelligence import CIPosture, CIState
from dosadi.security.security_dashboard import assess_ci_signatures, summarize_ward_security


def _state_for_summary():
    posture = CIPosture(ward_id="ward_alpha", level=2, driver="sting", active_assets={})
    ci_state = CIState(
        node_id="checkpoint_alpha",
        node_type="checkpoint",
        ward_id="ward_alpha",
        base_exposure=0.55,
        oversight_strength=0.35,
        patronage_entanglement=0.45,
        doctrine_modifier=0.1,
        recent_incident_pressure=0.25,
        rumor_tags=["watched"],
    )
    ci_state.recompute(posture, global_stress=0.55, fragmentation=0.3)
    return posture, [ci_state]


def test_summarize_ward_security_blends_doc_indices():
    posture, ci_states = _state_for_summary()

    summary = summarize_ward_security(
        ward_id="ward_alpha",
        ci_posture=posture,
        ci_states=ci_states,
        global_stress_index=0.55,
        fragmentation_index=0.3,
        regime_legitimacy_index=0.6,
    )

    assert summary.threat_level in {"moderate", "high", "critical"}
    assert summary.infiltration_risk_index == ci_states[0].infiltration_risk
    assert 0.0 <= summary.black_market_intensity_index <= 1.0
    assert summary.garrison_stability_index < 1.0


def test_assess_ci_signatures_produces_actions_and_hypotheses():
    posture, ci_states = _state_for_summary()

    assessments = assess_ci_signatures(ci_states, posture)
    assert assessments, "CI signatures should be generated"
    signature = assessments[0]

    assert "monitor" in signature.recommended_actions
    assert any(action in signature.recommended_actions for action in {"sting", "purge_recommendation"})
    assert any(hypothesis in signature.competing_hypotheses for hypothesis in {"guild_infiltration", "morale_collapse"})
