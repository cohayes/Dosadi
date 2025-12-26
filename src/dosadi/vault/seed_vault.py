from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Mapping

from dosadi.runtime.snapshot import (
    WorldSnapshotV1,
    load_snapshot,
    restore_world,
    save_snapshot,
    snapshot_world,
)
from dosadi.runtime.institutions import save_institutions_seed
from dosadi.runtime.culture_wars import save_culture_seed
from dosadi.runtime.ledger import save_ledger_seed
from dosadi.testing.kpis import collect_kpis


def _manifest_path(vault_dir: Path) -> Path:
    return vault_dir / "seeds" / "manifest.json"


def _snapshots_dir(vault_dir: Path) -> Path:
    return vault_dir / "seeds" / "snapshots"


def load_manifest(vault_dir: Path) -> Dict[str, Any]:
    path = _manifest_path(vault_dir)
    if not path.exists():
        return {"schema": "seed_vault_v1", "seeds": []}
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def write_manifest(vault_dir: Path, manifest: Mapping[str, Any]) -> None:
    path = _manifest_path(vault_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(manifest, fp, indent=2, sort_keys=True)


def list_seeds(vault_dir: Path) -> List[Dict[str, Any]]:
    manifest = load_manifest(vault_dir)
    return list(manifest.get("seeds", []))


def _compute_kpis(world) -> Dict[str, Any]:
    return collect_kpis(world)


def save_seed(
    vault_dir: Path,
    world,
    *,
    seed_id: str,
    scenario_id: str,
    meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    manifest = load_manifest(vault_dir)
    manifest.setdefault("seeds", [])

    snapshot = snapshot_world(world, scenario_id=scenario_id)
    snapshot_path = _snapshots_dir(vault_dir) / f"{seed_id}.json.gz"
    snapshot_sha = save_snapshot(snapshot, snapshot_path, gzip_output=True)
    inst_path = vault_dir / "seeds" / seed_id / "institutions.json"
    save_institutions_seed(world, inst_path)
    culture_path = vault_dir / "seeds" / seed_id / "culture.json"
    save_culture_seed(world, culture_path)
    ledger_path = vault_dir / "seeds" / seed_id / "ledger_accounts.json"
    save_ledger_seed(world, ledger_path)

    entry = {
        "seed_id": seed_id,
        "scenario_id": scenario_id,
        "parent_seed_id": meta.get("parent_seed_id") if meta else None,
        "created_tick": snapshot.tick,
        "elapsed_ticks": snapshot.tick,
        "snapshot_path": str(snapshot_path.relative_to(vault_dir)),
        "snapshot_sha256": snapshot_sha,
        "kpis": collect_kpis(world),
    }
    if inst_path.exists():
        entry["institutions_path"] = str(inst_path.relative_to(vault_dir))
        entry["institutions_sha256"] = sha256(inst_path.read_bytes()).hexdigest()
    if culture_path.exists():
        entry["culture_path"] = str(culture_path.relative_to(vault_dir))
        entry["culture_sha256"] = sha256(culture_path.read_bytes()).hexdigest()
    if ledger_path.exists():
        entry["ledger_path"] = str(ledger_path.relative_to(vault_dir))
        entry["ledger_sha256"] = sha256(ledger_path.read_bytes()).hexdigest()
    if meta:
        entry.update({k: v for k, v in meta.items() if k not in entry})

    manifest["schema"] = manifest.get("schema", "seed_vault_v1")
    manifest["seeds"] = [s for s in manifest["seeds"] if s.get("seed_id") != seed_id]
    manifest["seeds"].append(entry)
    write_manifest(vault_dir, manifest)
    return entry


def load_seed(vault_dir: Path, *, seed_id: str):
    manifest = load_manifest(vault_dir)
    seeds = {entry.get("seed_id"): entry for entry in manifest.get("seeds", [])}
    if seed_id not in seeds:
        raise KeyError(f"seed '{seed_id}' not found in manifest")

    entry = seeds[seed_id]
    snapshot_path = vault_dir / entry["snapshot_path"]
    snapshot = load_snapshot(snapshot_path)
    world = restore_world(snapshot)
    return world, snapshot, snapshot_path


__all__ = [
    "list_seeds",
    "load_manifest",
    "load_seed",
    "save_seed",
    "write_manifest",
]
