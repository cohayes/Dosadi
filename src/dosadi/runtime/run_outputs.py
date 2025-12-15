from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def generate_run_id(scenario_id: str, seed: int, *, timestamp: datetime | None = None) -> str:
    """Generate a deterministic-looking run identifier.

    The identifier follows the convention `{scenario_id}__seed-{seed}__{YYYYMMDD-HHMMSS}`
    and uses UTC for the timestamp to avoid timezone surprises.
    """

    ts = (timestamp or datetime.now(tz=timezone.utc)).strftime("%Y%m%d-%H%M%S")
    return f"{scenario_id}__seed-{seed}__{ts}"


def _to_jsonable_config(config: Any) -> Mapping[str, Any]:
    if config is None:
        return {}
    if isinstance(config, Mapping):
        return dict(config)
    if isinstance(config, Path):
        return str(config)
    if is_dataclass(config):
        return {k: _to_jsonable_config(v) for k, v in asdict(config).items()}
    if hasattr(config, "__dict__"):
        return {
            key: _to_jsonable_config(value)
            for key, value in vars(config).items()
            if not key.startswith("_")
        }
    return {"value": str(config)}


def prepare_run_directory(
    base_dir: Path,
    run_id: str,
    *,
    config: Any,
    notes: str | None = None,
) -> Path:
    """Create the run directory and emit config/notes files.

    Args:
        base_dir: Root output directory (e.g., Path("runs"))
        run_id: Identifier from :func:`generate_run_id`
        config: Scenario or harness configuration object
        notes: Optional free-form summary to store in ``notes.md``
    """

    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    config_path = run_dir / "config.json"
    with open(config_path, "w", encoding="utf-8") as fp:
        json.dump(_to_jsonable_config(config), fp, indent=2, sort_keys=True)

    if notes:
        notes_path = run_dir / "notes.md"
        with open(notes_path, "w", encoding="utf-8") as fp:
            fp.write(notes.strip() + "\n")

    return run_dir


def _relative_snapshot_path(snapshot_path: Path, run_dir: Path) -> str:
    try:
        return str(snapshot_path.relative_to(run_dir))
    except Exception:
        return str(snapshot_path)


def append_timeline_row(
    run_dir: Path,
    *,
    run_id: str,
    scenario_id: str,
    seed: int,
    day: int,
    tick: int,
    milestone_type: str,
    snapshot_path: Path,
    snapshot_sha256: str,
    kpis: Mapping[str, Any],
    world_signature: str | None = None,
    year: int | None = None,
    write_csv: bool = True,
) -> Mapping[str, Any]:
    """Append a milestone entry to ``timeline.jsonl`` (and CSV).

    Returns the row dict that was written, including the computed ``year``
    and normalized snapshot path.
    """

    computed_year = year if year is not None else int(day) // 365
    normalized_path = _relative_snapshot_path(snapshot_path, run_dir)

    row = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "seed": seed,
        "day": int(day),
        "year": computed_year,
        "tick": int(tick),
        "milestone_type": milestone_type,
        "snapshot_path": normalized_path,
        "snapshot_sha256": snapshot_sha256,
        "world_signature": world_signature,
        "kpis": dict(kpis),
    }

    timeline_path = run_dir / "timeline.jsonl"
    with open(timeline_path, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, sort_keys=True) + "\n")

    if write_csv:
        csv_path = run_dir / "timeline.csv"
        fieldnames = [
            "run_id",
            "scenario_id",
            "seed",
            "day",
            "year",
            "tick",
            "milestone_type",
            "snapshot_path",
            "snapshot_sha256",
            "world_signature",
            "kpis",
        ]
        needs_header = not csv_path.exists()
        with open(csv_path, "a", encoding="utf-8", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            if needs_header:
                writer.writeheader()
            writer.writerow({**{k: row[k] for k in fieldnames if k != "kpis"}, "kpis": json.dumps(row["kpis"], sort_keys=True)})

    return row


__all__ = ["append_timeline_row", "generate_run_id", "prepare_run_directory"]
