from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.state import WorldState
from dosadi.ui import DebugCockpitCLI


def _sample_world() -> WorldState:
    world = WorldState(seed=99)
    world.day = 3
    telemetry = ensure_metrics(world)
    telemetry.set_gauge("stockpile.shortages_count", 2)
    telemetry.topk_add("projects.blocked", "proj-1", 3.0, payload={"reason": "MATERIALS"})
    telemetry.topk_add("stockpile.shortages", "SEALANT:depot-1", 5.0, payload={"deficit": 5})
    telemetry.topk_add(
        "extraction.top_sites",
        "site-1",
        10.0,
        payload={"node": "loc:1", "kind": "SCRAP_FIELD", "pending_pickup": False},
    )
    telemetry.set_gauge(
        "planner_v2.last_action_json",
        [{"kind": "BUILD_DEPOT", "node": "loc:1", "facility": "DEPOT", "score": 1.0, "terms": {}}],
    )
    telemetry.set_gauge("suits.percent_warn", 5.0)
    telemetry.set_gauge("suits.percent_repair", 3.0)
    telemetry.set_gauge("suits.percent_critical", 1.0)
    telemetry.inc("suits.repairs_started", 1)
    telemetry.inc("suits.repairs_done", 1)
    return world


def test_render_returns_string() -> None:
    world = _sample_world()
    cli = DebugCockpitCLI(width=80)
    rendered = cli.render(world)
    assert isinstance(rendered, str)
    assert rendered.strip()


def test_contains_headings() -> None:
    rendered = DebugCockpitCLI().render(_sample_world())
    assert "Where are we stuck" in rendered
    assert "What is scarce" in rendered
    assert "Planner motives" in rendered


def test_render_is_deterministic() -> None:
    world = _sample_world()
    snap = snapshot_world(world, scenario_id="debug-cockpit")
    restored = restore_world(snap)
    cli = DebugCockpitCLI()
    assert cli.render(world) == cli.render(restored)
