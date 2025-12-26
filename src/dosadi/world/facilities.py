"""Facility schema and behavior registry for facility behaviors v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from hashlib import sha256
from typing import Any, Dict, Iterable, Iterator, Mapping, MutableMapping, Set


class FacilityKind(str, Enum):
    DEPOT = "DEPOT"
    OUTPOST = "OUTPOST"
    OUTPOST_L1 = "OUTPOST_L1"
    WORKSHOP = "WORKSHOP"
    WORKSHOP_T2 = "WORKSHOP_T2"
    RECYCLER = "RECYCLER"
    CHEM_WORKS = "CHEM_WORKS"
    CHEM_LAB_T2 = "CHEM_LAB_T2"
    REFINERY = "REFINERY"
    WATER_WORKS = "WATER_WORKS"
    FAB_SHOP_T3 = "FAB_SHOP_T3"
    WAYSTATION_L2 = "WAYSTATION_L2"
    FORT_L2 = "FORT_L2"
    GARRISON_L2 = "GARRISON_L2"


def coerce_facility_kind(raw: object) -> FacilityKind:
    if isinstance(raw, FacilityKind):
        return raw
    if isinstance(raw, str):
        try:
            return FacilityKind[raw.upper()]
        except KeyError:
            for kind in FacilityKind:
                if raw.lower() == kind.value.lower():
                    return kind
    return FacilityKind.DEPOT


@dataclass(slots=True)
class Facility:
    facility_id: str
    kind: FacilityKind = FacilityKind.DEPOT
    site_node_id: str = ""
    created_tick: int = 0
    status: str = "ACTIVE"
    state: dict = field(default_factory=dict)
    last_update_day: int = -1
    min_staff: int = 0
    is_operational: bool = True
    down_until_day: int = -1
    wear: float = 0.0
    maintenance_due: bool = False
    maintenance_job_id: str | None = None
    tags: Set[str] = field(default_factory=set)
    requires_unlocks: Set[str] = field(default_factory=set)
    tier: int = 1
    role_tags: Set[str] = field(default_factory=set)
    base_throughput: Dict[str, float] = field(default_factory=dict)
    consumes: Dict[str, float] = field(default_factory=dict)
    produces: Dict[str, float] = field(default_factory=dict)
    last_run_day: int = -1

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

    def list_by_kind(self, kind: FacilityKind) -> list[Facility]:
        return [f for f in self.facilities.values() if f.kind == kind]

    def signature(self) -> str:
        canonical = {
            fid: {
                "kind": fac.kind.value if isinstance(fac.kind, FacilityKind) else str(fac.kind),
                "site": fac.site_node_id,
                "status": fac.status,
                "last_day": fac.last_update_day,
                "last_run_day": getattr(fac, "last_run_day", -1),
                "state": fac.state,
                "requires": sorted(getattr(fac, "requires_unlocks", set())),
                "tier": getattr(fac, "tier", 0),
                "role_tags": sorted(getattr(fac, "role_tags", set())),
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


_FACILITY_DEFAULTS: dict[FacilityKind, dict[str, object]] = {
    FacilityKind.CHEM_LAB_T2: {
        "requires_unlocks": {"UNLOCK_CHEM_SEALANTS_T2"},
        "tier": 2,
        "role_tags": {"chem", "industry"},
        "consumes": {"CHEM_SALTS": 3.0, "FIBER": 1.0},
        "produces": {"SEALANT": 4.0, "GASKETS": 2.0},
    },
    FacilityKind.WORKSHOP_T2: {
        "requires_unlocks": {"UNLOCK_WORKSHOP_PARTS_T2"},
        "tier": 2,
        "role_tags": {"industry"},
        "consumes": {"SCRAP_METAL": 4.0},
        "produces": {"FASTENERS": 3.0, "FITTINGS": 2.0, "METAL_PLATE": 1.0},
    },
    FacilityKind.FAB_SHOP_T3: {
        "requires_unlocks": {"UNLOCK_FABRICATION_SIMPLE_T3"},
        "tier": 3,
        "role_tags": {"industry", "fabrication"},
        "consumes": {"FASTENERS": 1.0, "SEALANT": 1.0, "METAL_PLATE": 1.0},
        "produces": {"ADV_COMPONENTS": 1.0},
    },
    FacilityKind.WAYSTATION_L2: {
        "requires_unlocks": {"UNLOCK_CORRIDOR_L2"},
        "tier": 2,
        "role_tags": {"logistics_support", "corridor"},
    },
    FacilityKind.OUTPOST_L1: {
        "requires_unlocks": {"UNLOCK_OUTPOST_L1"},
        "tier": 1,
        "role_tags": {"defense", "corridor"},
        "consumes": {"SCRAP_METAL": 2.0, "FASTENERS": 1.0, "FILTER_MEDIA": 1.0},
    },
    FacilityKind.FORT_L2: {
        "requires_unlocks": {"UNLOCK_FORT_L2"},
        "tier": 2,
        "role_tags": {"defense", "corridor"},
        "consumes": {"ADV_COMPONENTS": 1.0, "SEALANT": 1.0, "FILTER_MEDIA": 1.0},
    },
    FacilityKind.GARRISON_L2: {
        "requires_unlocks": {"UNLOCK_GARRISON_L2"},
        "tier": 2,
        "role_tags": {"defense", "corridor"},
        "consumes": {"ADV_COMPONENTS": 1.0, "SEALANT": 1.0, "TRAINING_SUPPLIES": 1.0},
    },
}


def required_unlocks_for_facility_kind(kind: FacilityKind | str) -> set[str]:
    fk = coerce_facility_kind(kind)
    defaults = _FACILITY_DEFAULTS.get(fk, {})
    unlocks = defaults.get("requires_unlocks", set())
    if isinstance(unlocks, set):
        return set(unlocks)
    if isinstance(unlocks, Iterable):
        return set(unlocks)
    return set()


def apply_facility_defaults(facility: Facility) -> None:
    defaults = _FACILITY_DEFAULTS.get(coerce_facility_kind(facility.kind))
    if not defaults:
        return

    if not facility.requires_unlocks:
        facility.requires_unlocks = set(defaults.get("requires_unlocks", set()))
    if not facility.role_tags:
        facility.role_tags = set(defaults.get("role_tags", set()))
    if not facility.base_throughput:
        facility.base_throughput = dict(defaults.get("base_throughput", {}))
    if not facility.consumes:
        facility.consumes = dict(defaults.get("consumes", {}))
    if not facility.produces:
        facility.produces = dict(defaults.get("produces", {}))
    if facility.tier <= 0:
        facility.tier = int(defaults.get("tier", 1)) or 1

def get_facility_behavior(kind: str) -> FacilityBehavior:
    if isinstance(kind, FacilityKind):
        key = kind.value.lower()
    else:
        key = str(kind).lower()
    behavior = _FACILITY_BEHAVIORS.get(key)
    if behavior is None:
        raise KeyError(f"Unknown facility kind: {kind}")
    return behavior


def ensure_facility_ledger(world) -> FacilityLedger:
    ledger = getattr(world, "facilities", None)
    if isinstance(ledger, FacilityLedger):
        for facility in ledger.facilities.values():
            apply_facility_defaults(facility)
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
                    kind=coerce_facility_kind(fac.get("kind", fac.get("type", FacilityKind.DEPOT.value))),
                    site_node_id=str(fac.get("site_node_id", fid)),
                    created_tick=int(fac.get("created_tick", 0)),
                    status=str(fac.get("status", "ACTIVE")),
                    state=dict(fac),
                    last_update_day=int(fac.get("last_update_day", -1)),
                    min_staff=int(fac.get("min_staff", 0)),
                    is_operational=bool(fac.get("is_operational", True)),
                    down_until_day=int(fac.get("down_until_day", -1)),
                    wear=float(fac.get("wear", 0.0)),
                    maintenance_due=bool(fac.get("maintenance_due", False)),
                    maintenance_job_id=fac.get("maintenance_job_id"),
                    tags=set(fac.get("tags", []) if isinstance(fac.get("tags", []), (list, set, tuple)) else []),
                    requires_unlocks=set(
                        fac.get("requires_unlocks", [])
                        if isinstance(fac.get("requires_unlocks", []), (list, set, tuple))
                        else []
                    ),
                    tier=int(fac.get("tier", 1)),
                    role_tags=set(
                        fac.get("role_tags", [])
                        if isinstance(fac.get("role_tags", []), (list, set, tuple))
                        else []
                    ),
                    base_throughput=dict(fac.get("base_throughput", {})),
                    consumes=dict(fac.get("consumes", {})),
                    produces=dict(fac.get("produces", {})),
                    last_run_day=int(fac.get("last_run_day", fac.get("last_update_day", -1))),
                )
            else:
                facilities[fid] = Facility(
                    facility_id=fid,
                    kind=coerce_facility_kind(getattr(fac, "kind", FacilityKind.DEPOT)),
                    site_node_id=str(getattr(fac, "site_node_id", fid)),
                    created_tick=int(getattr(fac, "created_tick", 0)),
                    status=str(getattr(fac, "status", "ACTIVE")),
                    state=fac.__dict__ if hasattr(fac, "__dict__") else {},
                    last_update_day=int(getattr(fac, "last_update_day", -1)),
                    min_staff=int(getattr(fac, "min_staff", 0)),
                    is_operational=bool(getattr(fac, "is_operational", True)),
                    down_until_day=int(getattr(fac, "down_until_day", -1)),
                    wear=float(getattr(fac, "wear", 0.0)),
                    maintenance_due=bool(getattr(fac, "maintenance_due", False)),
                    maintenance_job_id=getattr(fac, "maintenance_job_id", None),
                    tags=set(getattr(fac, "tags", set()) or set()),
                    requires_unlocks=set(getattr(fac, "requires_unlocks", set()) or set()),
                    tier=int(getattr(fac, "tier", 1)),
                    role_tags=set(getattr(fac, "role_tags", set()) or set()),
                    base_throughput=dict(getattr(fac, "base_throughput", {}) or {}),
                    consumes=dict(getattr(fac, "consumes", {}) or {}),
                    produces=dict(getattr(fac, "produces", {}) or {}),
                    last_run_day=int(getattr(fac, "last_run_day", getattr(fac, "last_update_day", -1))),
                )
        ledger = FacilityLedger(facilities=facilities)

    for facility in ledger.facilities.values():
        apply_facility_defaults(facility)

    setattr(world, "facilities", ledger)
    return ledger


def facility_unlocked(world, facility: Facility) -> bool:
    try:
        from dosadi.runtime.tech_ladder import has_unlock
    except Exception:  # pragma: no cover - defensive fallback
        return True

    required = set(getattr(facility, "requires_unlocks", set()) or set())
    required.update(required_unlocks_for_facility_kind(facility.kind))
    if not required:
        return True
    return all(has_unlock(world, tag) for tag in required)


__all__ = [
    "Facility",
    "FacilityBehavior",
    "FacilityLedger",
    "FacilityKind",
    "apply_facility_defaults",
    "coerce_facility_kind",
    "facility_unlocked",
    "ensure_facility_ledger",
    "get_facility_behavior",
    "required_unlocks_for_facility_kind",
]

