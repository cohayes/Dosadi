
from __future__ import annotations
from typing import Any, Dict

def ok(data: Any | None = None) -> Dict[str, Any]:
    return {"ok": True, "data": data}

def err(code: str, data: Any | None = None) -> Dict[str, Any]:
    return {"ok": False, "err": code, "data": data}

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
