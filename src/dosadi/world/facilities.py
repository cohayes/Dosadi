"""Facility schema and behavior registry for facility behaviors v1."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from hashlib import sha256
from typing import Any, Dict, Iterator, MutableMapping


@dataclass(slots=True)
class Facility:
    facility_id: str
    kind: str
    site_node_id: str
    created_tick: int
    status: str = "ACTIVE"
    state: dict = field(default_factory=dict)
    last_update_day: int = -1

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - trivial passthrough
        if name == "state":
            raise AttributeError(name)
        state = object.__getattribute__(self, "state")
        if isinstance(state, dict) and name in state:
            return state[name]
        raise AttributeError(name)


@dataclass(slots=True)
class FacilityLedger:
    facilities: MutableMapping[str, Facility] = field(default_factory=dict)

    def add(self, f: Facility) -> None:
        self.facilities[f.facility_id] = f

    def get(self, facility_id: str):
        return self.facilities.get(facility_id)

    def list_by_kind(self, kind: str) -> list[Facility]:
        return [f for f in self.facilities.values() if f.kind == kind]

    def signature(self) -> str:
        canonical = {
            fid: {
                "kind": fac.kind,
                "site": fac.site_node_id,
                "status": fac.status,
                "last_day": fac.last_update_day,
                "state": fac.state,
            }
            for fid, fac in sorted(self.facilities.items())
        }
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return sha256(payload).hexdigest()

    # Mapping helpers for compatibility with existing code paths.
    def __iter__(self) -> Iterator[str]:
        return iter(self.facilities)

    def __len__(self) -> int:
        return len(self.facilities)

    def __contains__(self, key: object) -> bool:
        return key in self.facilities

    def items(self):
        return self.facilities.items()

    def values(self):
        return self.facilities.values()

    def keys(self):
        return self.facilities.keys()

    def __getitem__(self, key: str) -> Facility:
        return self.facilities[key]


@dataclass(slots=True)
class FacilityBehavior:
    kind: str
    inputs_per_day: Dict[str, float]
    outputs_per_day: Dict[str, float]
    requires_labor: bool = False
    labor_agents: int = 0
    labor_efficiency: float = 1.0


_FACILITY_BEHAVIORS: Dict[str, FacilityBehavior] = {
    "outpost": FacilityBehavior(
        kind="outpost", inputs_per_day={}, outputs_per_day={"survey_progress": 1.0}
    ),
    "pump_station": FacilityBehavior(
        kind="pump_station",
        inputs_per_day={"filters": 0.1},
        outputs_per_day={"water": 5.0},
    ),
    "workshop": FacilityBehavior(
        kind="workshop",
        inputs_per_day={"metal_scrap": 1.0, "polymer": 0.5},
        outputs_per_day={"filters": 0.2},
    ),
}


def get_facility_behavior(kind: str) -> FacilityBehavior:
    behavior = _FACILITY_BEHAVIORS.get(kind)
    if behavior is None:
        raise KeyError(f"Unknown facility kind: {kind}")
    return behavior


def ensure_facility_ledger(world) -> FacilityLedger:
    ledger = getattr(world, "facilities", None)
    if isinstance(ledger, FacilityLedger):
        return ledger

    if ledger is None:
        ledger = FacilityLedger()
    elif isinstance(ledger, MutableMapping):
        facilities: Dict[str, Facility] = {}
        for fid, fac in ledger.items():
            if isinstance(fac, Facility):
                facilities[fid] = fac
            elif isinstance(fac, MutableMapping):
                facilities[fid] = Facility(
                    facility_id=fid,
                    kind=str(fac.get("kind", fac.get("type", "unknown"))),
                    site_node_id=str(fac.get("site_node_id", fid)),
                    created_tick=int(fac.get("created_tick", 0)),
                    status=str(fac.get("status", "ACTIVE")),
                    state=dict(fac),
                    last_update_day=int(fac.get("last_update_day", -1)),
                )
            else:
                facilities[fid] = Facility(
                    facility_id=fid,
                    kind=str(getattr(fac, "kind", "unknown")),
                    site_node_id=str(getattr(fac, "site_node_id", fid)),
                    created_tick=int(getattr(fac, "created_tick", 0)),
                    status=str(getattr(fac, "status", "ACTIVE")),
                    state=fac.__dict__ if hasattr(fac, "__dict__") else {},
                    last_update_day=int(getattr(fac, "last_update_day", -1)),
                )
        ledger = FacilityLedger(facilities=facilities)

    setattr(world, "facilities", ledger)
    return ledger

