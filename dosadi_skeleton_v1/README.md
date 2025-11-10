
# Dosadi Prototype (Skeletal Package)

Skeletal Python package for the Dosadi Day‑0 prototype. This mirrors the **Compact API Checklist (Dosadi v1)** and the **Day‑0 Dry‑Run Playbook v1** so Codex (or a developer) can fill in logic.

## Structure
- `dosadi/` — core modules and subsystems (stubs with signatures + docstrings)
- `tests/`  — minimal Day‑0 harness skeleton

## Timebase
- `Tick = 0.6 seconds`, `Minute = 100 ticks`, `Day = 1440 minutes`

## How to use
1. Install in editable mode: `pip install -e .` (optional – `pyproject.toml` is not provided in this skeleton).
2. Read `dosadi/api.py` for the unified façade.
3. Implement subsystems following docstrings and v1 specs.
4. Run the Day‑0 harness: `python -m tests.day0_dry_run` (once implemented).

This package is intentionally minimal and typed; all functions return `{ok, err?, data?}`.
