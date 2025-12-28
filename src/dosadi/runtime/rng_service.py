from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Dict, Sequence, Tuple, TypeVar

T = TypeVar("T")


def _to_jsonable(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    raise TypeError(f"Unsupported scope value type: {type(value)!r}")


def _canonical_scope(scope: Dict[str, object] | None) -> str:
    if not scope:
        return "{}"
    jsonable = _to_jsonable(scope)
    return json.dumps(jsonable, sort_keys=True, separators=(",", ":"))


@dataclass(slots=True)
class RNGConfig:
    enabled: bool = True
    salt: str = "rng-v1"
    audit_enabled: bool = True
    max_audit_streams: int = 256
    warn_on_global_random: bool = False


@dataclass
class RNGService:
    seed: int
    config: RNGConfig = field(default_factory=RNGConfig)
    counters: dict[str, int] = field(default_factory=dict)
    audit: dict[str, Dict[str, object]] = field(default_factory=dict)

    def _stream_id(self, stream_key: str, scope_json: str) -> str:
        digest = sha256(f"{self.config.salt}|{self.seed}|{stream_key}|{scope_json}".encode()).hexdigest()
        return digest[:16]

    def _derived_seed(self, stream_key: str, scope_json: str, draw_index: int) -> int:
        blob = f"{self.config.salt}|{self.seed}|{stream_key}|{scope_json}|{draw_index}"
        digest = sha256(blob.encode()).digest()
        return int.from_bytes(digest[:8], "big", signed=False)

    def _next_index(self, stream_id: str) -> int:
        current = self.counters.get(stream_id, 0)
        self.counters[stream_id] = current + 1
        return current

    def _record_audit(self, stream_id: str, stream_key: str, scope_json: str) -> None:
        if not self.config.audit_enabled:
            return
        entry = self.audit.get(stream_id, {"stream_key": stream_key, "count": 0, "last_scope": scope_json})
        entry["stream_key"] = stream_key
        entry["count"] = self.counters.get(stream_id, entry.get("count", 0))
        entry["last_scope"] = scope_json
        self.audit[stream_id] = entry
        if len(self.audit) > self.config.max_audit_streams:
            # Drop the smallest counts to keep memory bounded.
            sorted_streams = sorted(self.audit.items(), key=lambda item: (item[1].get("count", 0), item[0]))
            for stream_to_drop, _ in sorted_streams[:-self.config.max_audit_streams]:
                self.audit.pop(stream_to_drop, None)

    def _derive_random(self, stream_key: str, scope: Dict[str, object] | None) -> Tuple[random.Random, str]:
        scope_json = _canonical_scope(scope)
        stream_id = self._stream_id(stream_key, scope_json)
        draw_index = self._next_index(stream_id)
        seed = self._derived_seed(stream_key, scope_json, draw_index)
        rng = random.Random(seed)
        self._record_audit(stream_id, stream_key, scope_json)
        return rng, stream_id

    def stream(self, stream_key: str, *, scope: Dict[str, object] | None = None) -> random.Random:
        rng, _ = self._derive_random(stream_key, scope)
        return rng

    def rand(self, stream_key: str, *, scope: Dict[str, object] | None = None) -> float:
        rng, _ = self._derive_random(stream_key, scope)
        return rng.random()

    def randint(self, stream_key: str, a: int, b: int, *, scope: Dict[str, object] | None = None) -> int:
        rng, _ = self._derive_random(stream_key, scope)
        return rng.randint(a, b)

    def choice(self, stream_key: str, seq: Sequence[T], *, scope: Dict[str, object] | None = None) -> T:
        rng, _ = self._derive_random(stream_key, scope)
        if not seq:
            raise IndexError("Cannot choose from an empty sequence")
        idx = rng.randrange(len(seq))
        return seq[idx]

    def signature(self) -> str:
        sorted_items = sorted(self.counters.items())
        payload = json.dumps(sorted_items, separators=(",", ":"))
        digest = sha256(payload.encode()).hexdigest()
        return digest[:16]

    def audit_summary(self) -> list[tuple[str, int]]:
        if not self.config.audit_enabled:
            return []
        pairs = [
            (entry.get("stream_key") or stream_id, int(entry.get("count", 0)))
            for stream_id, entry in self.audit.items()
        ]
        return sorted(pairs, key=lambda pair: (-pair[1], pair[0]))


def ensure_rng_service(world: Any) -> RNGService:
    cfg = getattr(world, "rng_service_cfg", None)
    if not isinstance(cfg, RNGConfig):
        cfg = RNGConfig()
        setattr(world, "rng_service_cfg", cfg)

    service = getattr(world, "rng_service", None)
    if not isinstance(service, RNGService):
        service = RNGService(seed=getattr(world, "seed", 0), config=cfg)
        setattr(world, "rng_service", service)
    return service


__all__ = ["RNGConfig", "RNGService", "ensure_rng_service"]
