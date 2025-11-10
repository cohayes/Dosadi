
"""Dosadi v1 — skeletal package.

Exports the primary façade in `api.py` and the event bus in `events.py`.
"""
from .api import DosadiSim
from .events import emit, subscribe, Event
