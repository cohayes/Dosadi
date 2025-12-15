from __future__ import annotations

import gzip
import importlib
import json
import random
from collections import deque
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

from dosadi.agents.core import GoalStatus
from dosadi.systems.protocols import ProtocolStatus
from dosadi.admin_log import AdminEventLog
from dosadi.memory.episodes import EpisodeBuffers

SNAPSHOT_SCHEMA_VERSION = "world_snapshot_v1"


@dataclass(slots=True)
class WorldSnapshotV1:
    schema_version: str
    scenario_id: str
    seed: int
    tick: int
    rng_state: object
    global_rng_state: object | None
    world: Mapping[str, Any]
    event_queue: Mapping[str, Any] | None = None


def rng_state_to_jsonable(state: object) -> object:
    if isinstance(state, tuple):
        return [rng_state_to_jsonable(item) for item in state]
    if isinstance(state, (list, Mapping)):
        if isinstance(state, Mapping):
            return {str(k): rng_state_to_jsonable(v) for k, v in state.items()}
        return [rng_state_to_jsonable(item) for item in state]
    return state


def rng_state_from_jsonable(value: object) -> object:
    if isinstance(value, list):
        return tuple(rng_state_from_jsonable(item) for item in value)
    if isinstance(value, Mapping):
        return {k: rng_state_from_jsonable(v) for k, v in value.items()}
    return value


def _resolve_type(path: str):
    module_path, _, attr = path.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, attr)


def to_snapshot_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        payload = {field.name: to_snapshot_dict(getattr(obj, field.name)) for field in fields(obj)}
        return {"__type__": f"{obj.__class__.__module__}.{obj.__class__.__qualname__}", "data": payload}

    if isinstance(obj, AdminEventLog):
        return {
            "__type__": f"{AdminEventLog.__module__}.{AdminEventLog.__qualname__}",
            "events": [to_snapshot_dict(evt) for evt in getattr(obj, "_events", [])],
        }

    if isinstance(obj, set):
        return {"__set__": [to_snapshot_dict(item) for item in sorted(obj, key=lambda itm: str(itm))]}

    if isinstance(obj, deque):
        return {"__deque__": [to_snapshot_dict(item) for item in obj]}

    if isinstance(obj, random.Random):
        return {"__random_state__": rng_state_to_jsonable(obj.getstate())}

    if isinstance(obj, Enum):
        return {"__enum__": f"{obj.__class__.__module__}.{obj.__class__.__qualname__}", "value": obj.value}

    if isinstance(obj, Mapping):
        return {str(k): to_snapshot_dict(v) for k, v in sorted(obj.items(), key=lambda item: str(item[0]))}

    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        items = list(obj)
        if all(hasattr(item, "id") for item in items):
            items = sorted(items, key=lambda itm: str(getattr(itm, "id")))
        elif all(isinstance(item, Mapping) and "id" in item for item in items):
            items = sorted(items, key=lambda itm: str(itm.get("id")))
        return [to_snapshot_dict(item) for item in items]

    return obj


def from_snapshot_dict(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        if "__random_state__" in obj:
            rng = random.Random()
            rng.setstate(rng_state_from_jsonable(obj["__random_state__"]))
            return rng

        if "__enum__" in obj:
            enum_cls = _resolve_type(obj["__enum__"])
            return enum_cls(obj["value"])

        if "__set__" in obj:
            return set(from_snapshot_dict(item) for item in obj.get("__set__", []))

        if "__deque__" in obj:
            return deque(from_snapshot_dict(item) for item in obj.get("__deque__", []))

        if "__type__" in obj and "data" in obj:
            cls = _resolve_type(obj["__type__"])
            if is_dataclass(cls):
                if cls is EpisodeBuffers:
                    data = obj.get("data", {})
                    short_term_data = data.get("short_term", [])
                    if isinstance(short_term_data, Mapping) and "__deque__" in short_term_data:
                        short_term_data = short_term_data.get("__deque__", [])
                    buffers = EpisodeBuffers(
                        short_term=deque(from_snapshot_dict(item) for item in short_term_data),
                        daily=[from_snapshot_dict(item) for item in data.get("daily", [])],
                        archive_refs=[from_snapshot_dict(item) for item in data.get("archive_refs", [])],
                        short_term_capacity=data.get("short_term_capacity", 50),
                        daily_capacity=data.get("daily_capacity", 100),
                    )
                    return buffers
                kwargs: MutableMapping[str, Any] = {}
                for field in fields(cls):
                    if field.name in obj["data"]:
                        kwargs[field.name] = from_snapshot_dict(obj["data"][field.name])
                return cls(**kwargs)
            if cls is AdminEventLog:
                log = AdminEventLog()
                for evt in obj.get("events", []):
                    log._events.append(from_snapshot_dict(evt))
                return log

        return {key: from_snapshot_dict(value) for key, value in obj.items()}

    if isinstance(obj, list):
        return [from_snapshot_dict(item) for item in obj]

    return obj


def snapshot_world(world: Any, *, scenario_id: str) -> WorldSnapshotV1:
    rng = getattr(world, "rng", None)
    rng_state = rng.getstate() if isinstance(rng, random.Random) else random.Random(getattr(world, "seed", 0)).getstate()
    world_dict = to_snapshot_dict(world)

    return WorldSnapshotV1(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        scenario_id=scenario_id,
        seed=getattr(world, "seed", 0),
        tick=getattr(world, "tick", 0),
        rng_state=rng_state_to_jsonable(rng_state),
        global_rng_state=rng_state_to_jsonable(random.getstate()),
        world=world_dict,
    )


def restore_world(snapshot: WorldSnapshotV1):
    world = from_snapshot_dict(snapshot.world)
    rng_state = rng_state_from_jsonable(snapshot.rng_state)
    rng = random.Random()
    rng.setstate(rng_state)
    setattr(world, "rng", rng)
    if snapshot.global_rng_state is not None:
        random.setstate(rng_state_from_jsonable(snapshot.global_rng_state))
    return world


def _canonical_dumps(data: Mapping[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def save_snapshot(snapshot: WorldSnapshotV1, path: Path, *, gzip_output: bool = True) -> str:
    snapshot_dict = {
        "schema_version": snapshot.schema_version,
        "scenario_id": snapshot.scenario_id,
        "seed": snapshot.seed,
        "tick": snapshot.tick,
        "rng_state": snapshot.rng_state,
        "global_rng_state": snapshot.global_rng_state,
        "world": snapshot.world,
        "event_queue": snapshot.event_queue,
    }

    payload = _canonical_dumps(snapshot_dict).encode("utf-8")
    digest = sha256(payload).hexdigest()

    path.parent.mkdir(parents=True, exist_ok=True)
    if gzip_output:
        with gzip.open(path, "wb") as fp:
            fp.write(payload)
    else:
        with open(path, "wb") as fp:
            fp.write(payload)

    return digest


def load_snapshot(path: Path) -> WorldSnapshotV1:
    if not path.exists():
        raise FileNotFoundError(path)

    raw: bytes
    if path.suffix.endswith("gz"):
        with gzip.open(path, "rb") as fp:
            raw = fp.read()
    else:
        with open(path, "rb") as fp:
            raw = fp.read()

    data = json.loads(raw.decode("utf-8"))
    return WorldSnapshotV1(
        schema_version=data.get("schema_version", SNAPSHOT_SCHEMA_VERSION),
        scenario_id=data["scenario_id"],
        seed=data["seed"],
        tick=data["tick"],
        rng_state=data["rng_state"],
        global_rng_state=data.get("global_rng_state"),
        world=data["world"],
        event_queue=data.get("event_queue"),
    )


def world_signature(world: Any) -> str:
    agents_summary = []
    for agent_id, agent in sorted(getattr(world, "agents", {}).items()):
        goals = getattr(agent, "goals", [])
        goals_summary = {
            "total": len(goals),
            "active": sum(1 for g in goals if getattr(g, "status", None) == GoalStatus.ACTIVE),
            "pending": sum(1 for g in goals if getattr(g, "status", None) == GoalStatus.PENDING),
            "completed": sum(1 for g in goals if getattr(g, "status", None) == GoalStatus.COMPLETED),
        }
        agents_summary.append(
            {
                "id": agent_id,
                "location": getattr(agent, "location_id", None),
                "queue": getattr(agent, "current_queue_id", None),
                "is_asleep": getattr(agent, "is_asleep", False),
                "rest_ticks": getattr(agent, "rest_ticks_in_pod", 0),
                "goals": goals_summary,
            }
        )

    queues_summary = {
        queue_id: len(getattr(queue, "queue", getattr(queue, "agents", [])))
        for queue_id, queue in sorted(getattr(world, "queues", {}).items())
    }

    protocols = getattr(getattr(world, "protocols", None), "protocols_by_id", {})
    protocol_summary = {
        "total": len(protocols),
        "active": sum(1 for p in protocols.values() if getattr(p, "status", None) == ProtocolStatus.ACTIVE),
    }

    canonical = {
        "tick": getattr(world, "tick", 0),
        "seed": getattr(world, "seed", 0),
        "agents": agents_summary,
        "queues": queues_summary,
        "protocols": protocol_summary,
        "groups": len(getattr(world, "groups", [])),
        "wards": len(getattr(world, "wards", {})),
    }
    return sha256(_canonical_dumps(canonical).encode("utf-8")).hexdigest()


__all__ = [
    "SNAPSHOT_SCHEMA_VERSION",
    "WorldSnapshotV1",
    "load_snapshot",
    "restore_world",
    "rng_state_from_jsonable",
    "rng_state_to_jsonable",
    "save_snapshot",
    "snapshot_world",
    "world_signature",
]
