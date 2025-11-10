
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, DefaultDict
from collections import defaultdict

@dataclass
class Event:
    name: str
    payload: Dict[str, Any]

_subs: DefaultDict[str, List[Callable[[Event], None]]] = defaultdict(list)

def subscribe(name: str, fn: Callable[[Event], None]) -> None:
    _subs[name].append(fn)

def emit(name: str, payload: Dict[str, Any]) -> None:
    evt = Event(name=name, payload=payload)
    for fn in list(_subs.get(name, [])):
        try:
            fn(evt)
        except Exception:
            # swallow in skeleton; wire logging later
            pass
