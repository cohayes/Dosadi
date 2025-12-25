from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Dict, Mapping


class Material(Enum):
    SCRAP_INPUT = "SCRAP_INPUT"
    SALVAGE_MIX = "SALVAGE_MIX"
    SCRAP_METAL = "SCRAP_METAL"
    FASTENERS = "FASTENERS"
    SEALANT = "SEALANT"
    PLASTICS = "PLASTICS"
    FABRIC = "FABRIC"
    FIBER = "FIBER"
    CHEM_SALTS = "CHEM_SALTS"
    GASKETS = "GASKETS"
    FILTER_MEDIA = "FILTER_MEDIA"
    CIRCUIT_SIMPLE = "CIRCUIT_SIMPLE"
    ELECTRICAL = "ELECTRICAL"
    CONCRETE_AGGREGATE = "CONCRETE_AGGREGATE"
    WATER_BARREL_PARTS = "WATER_BARREL_PARTS"


@dataclass(slots=True)
class MaterialStack:
    material: Material
    qty: int


@dataclass(slots=True)
class Inventory:
    items: Dict[Material, int] = field(default_factory=dict)

    def _coerce_keys(self) -> None:
        if not self.items:
            return
        coerced: Dict[Material, int] = {}
        for key, qty in list(self.items.items()):
            material = material_from_key(key)
            if material is None:
                continue
            try:
                amount = int(qty)
            except (TypeError, ValueError):
                continue
            coerced[material] = coerced.get(material, 0) + amount
        self.items = coerced

    def get(self, material: Material) -> int:
        self._coerce_keys()
        return int(self.items.get(material, 0))

    def add(self, material: Material, qty: int) -> None:
        self._coerce_keys()
        if qty <= 0:
            return
        self.items[material] = self.get(material) + int(qty)

    def remove(self, material: Material, qty: int) -> int:
        self._coerce_keys()
        if qty <= 0:
            return 0
        current = self.get(material)
        new_value = max(0, current - int(qty))
        self.items[material] = new_value
        return current - new_value

    def can_afford(self, bom: Mapping[Material, int]) -> bool:
        self._coerce_keys()
        return all(self.get(mat) >= int(qty) for mat, qty in bom.items())

    def apply_bom(self, bom: Mapping[Material, int]) -> None:
        self._coerce_keys()
        for material, qty in bom.items():
            self.remove(material, int(qty))

    def signature(self) -> str:
        self._coerce_keys()
        payload = {mat.name: self.get(mat) for mat in sorted(self.items, key=lambda m: m.name)}
        digest = sha256(str(payload).encode("utf-8")).hexdigest()
        return digest


@dataclass(slots=True)
class InventoryRegistry:
    by_owner: Dict[str, Inventory] = field(default_factory=dict)

    def inv(self, owner_id: str) -> Inventory:
        inventory = self.by_owner.get(owner_id)
        if inventory is None:
            inventory = Inventory()
            self.by_owner[owner_id] = inventory
        return inventory

    def signature(self) -> str:
        canonical = {
            owner: inv.signature()
            for owner, inv in sorted(self.by_owner.items(), key=lambda item: item[0])
        }
        digest = sha256(str(canonical).encode("utf-8")).hexdigest()
        return digest


def ensure_inventory_registry(world) -> InventoryRegistry:
    registry: InventoryRegistry = getattr(world, "inventories", None) or InventoryRegistry()
    world.inventories = registry
    return registry


def material_from_key(key: object) -> Material | None:
    if isinstance(key, Material):
        return key
    if not isinstance(key, str):
        return None
    if "." in key:
        key = key.split(".")[-1]
    try:
        return Material[key.upper()]
    except KeyError:
        return None


def normalize_bom(raw: Mapping[object, object]) -> Dict[Material, int]:
    bom: Dict[Material, int] = {}
    for key, qty in raw.items():
        material = material_from_key(key)
        if material is None:
            continue
        try:
            amount = int(qty)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        bom[material] = bom.get(material, 0) + amount
    return bom


__all__ = [
    "Inventory",
    "InventoryRegistry",
    "Material",
    "MaterialStack",
    "ensure_inventory_registry",
    "material_from_key",
    "normalize_bom",
]

