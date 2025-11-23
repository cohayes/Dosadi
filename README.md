# Dosadi v2

Dosadi v2 establishes a top-down omniscient systems model; all prior character-level experiments are deprecated in favour of the structured agents, wards, and playbooks documented under `docs/latest`.

## Running the Sting Wave Day-3 scenario

The scenario harness mirrors `docs/latest/11_scenarios/Dosadi_Scenario_Sting_Wave_Day3.md` and can be exercised either from the CLI or a notebook.

### CLI quickstart

1. List available scenarios:
   ```bash
   python -m dosadi.playbook.cli --list
   ```
2. Run the Sting Wave Day-3 scenario, render the timeline plus dashboards, and execute the verification checks:
   ```bash
   python -m dosadi.playbook.cli --scenario sting_wave_day3 --dashboard --ward ward:12 --agent agent:3 --verify
   ```
   You can override config fields inline, e.g. `--config sting_injection_rate=0.12 --config world_seed=99`.

### Quiet Season sandbox

To exercise the minimal campaign engine against the documented Quiet Season
scenario, run:

```bash
python -m dosadi.runtime.quiet_season_cli --ticks 12
```

The CLI will load `docs/latest/11_scenarios/S-0001_Pre_Sting_Quiet_Season.yaml`,
advance the coarse campaign state for the requested ticks, and print a compact
dashboard showing the current phase, objective statuses, a security summary
derived from the INFO dashboards doc (D-INFO-0014), and a CI posture slice plus
signature assessments derived from the counterintelligence doc set (D-MIL-0108,
D-INFO-0009).

### Notebook / Jupyter quickstart

```python
from dosadi import (
    AdminDashboardCLI,
    ScenarioTimelineCLI,
    available_scenarios,
    run_scenario,
    verify_scenario,
)

print("Available:", [entry.name for entry in available_scenarios()])
report = run_scenario("sting_wave_day3", overrides={"scenario_seed": 7})
print(ScenarioTimelineCLI(width=90).render(report.phases, title="Sting Wave Day-3"))
print(AdminDashboardCLI(width=90).render(report.world, ward_id="ward:12"))
validation = verify_scenario("sting_wave_day3", report)
print(validation)
```

The `report` object exposes the generated `WorldState`, all phase descriptions, the canonical events (matching the doc taxonomy), and KPIs (`bust_rate`, `reserve_floor`, `heat_peak`).  `verify_scenario` asserts those KPIs stay within the documented tolerances.
