from dosadi.world.routing import RoutingConfig, compute_route
from dosadi.world.survey_map import SurveyEdge, SurveyMap


def _make_map() -> SurveyMap:
    smap = SurveyMap()
    smap.upsert_edge(SurveyEdge(a="A", b="B", distance_m=1.0, travel_cost=1.0))
    smap.upsert_edge(SurveyEdge(a="B", b="C", distance_m=1.0, travel_cost=1.0))
    smap.upsert_edge(SurveyEdge(a="A", b="C", distance_m=2.0, travel_cost=2.0))
    return smap


def test_deterministic_route_selection() -> None:
    world = type("Stub", (), {})()
    world.survey_map = _make_map()
    world.routing_cfg = RoutingConfig(tie_break="lex")
    route_a = compute_route(world, from_node="A", to_node="C", perspective_agent_id=None)
    route_b = compute_route(world, from_node="A", to_node="C", perspective_agent_id=None)
    assert route_a is not None
    assert route_b is not None
    assert route_a.edge_keys == route_b.edge_keys


def test_hazard_avoidance_affects_route() -> None:
    world = type("Stub", (), {})()
    smap = SurveyMap()
    smap.upsert_edge(SurveyEdge(a="A", b="B", distance_m=1.0, travel_cost=1.0, hazard=0.9))
    smap.upsert_edge(SurveyEdge(a="B", b="C", distance_m=1.0, travel_cost=1.0, hazard=0.9))
    smap.upsert_edge(SurveyEdge(a="A", b="C", distance_m=2.2, travel_cost=2.2, hazard=0.0))
    world.survey_map = smap
    world.routing_cfg = RoutingConfig(risk_weight=0.5, hazard_weight=1.0, belief_weight=0.0)
    route = compute_route(world, from_node="A", to_node="C", perspective_agent_id=None)
    assert route is not None
    assert route.edge_keys == [SurveyEdge(a="A", b="C", distance_m=0, travel_cost=0).key]
