from dosadi.admin_log import AdminEventLog


def test_admin_event_log_filters_and_capacity():
    log = AdminEventLog(capacity=2)
    log.record(tick=1, event_type="A", payload={"value": 1})
    log.record(tick=2, event_type="B", payload={"value": 2})
    log.record(tick=3, event_type="B", payload={"value": 3})
    events = log.get_recent()
    assert len(events) == 2
    assert events[0].tick == 2 and events[1].tick == 3
    filtered = log.get_recent(event_type="B")
    assert all(event.event_type == "B" for event in filtered)


def test_admin_event_helpers_create_payloads():
    log = AdminEventLog()
    decision = log.log_agent_decision(
        tick=5,
        agent_id="A1",
        ward_id="W1",
        facility_id="F1",
        action="SCAVENGE",
        survival_score=0.6,
        long_term_score=0.3,
        risk_score=0.1,
    )
    assert decision.event_type == "AGENT_DECISION"
    rumor = log.log_rumor_spread(
        tick=6,
        speaker_id="A1",
        listener_id="A2",
        rumor_id="R1",
        topic="CRACKDOWN",
        credibility_before=0.2,
        credibility_after=0.5,
    )
    assert rumor.payload["credibility_delta"] == 0.3
    facility = log.log_facility_event(
        tick=7,
        ward_id="W1",
        facility_id="W1:SOUP",
        event_kind="SHORTAGE",
        impact="food",
    )
    assert facility.payload["event_kind"] == "SHORTAGE"
