from __future__ import annotations

import copy

import pytest

from dosadi.runtime.rng_service import RNGConfig, RNGService, ensure_rng_service


def test_deterministic_rand_outputs():
    svc_a = RNGService(seed=123)
    svc_b = RNGService(seed=123)

    draws_a = [svc_a.rand("stream:a", scope={"x": 1}) for _ in range(3)]
    draws_b = [svc_b.rand("stream:a", scope={"x": 1}) for _ in range(3)]

    assert draws_a == draws_b


def test_scope_key_order_stable():
    svc = RNGService(seed=99)
    val_a = svc.rand("stream:scope", scope={"a": 1, "b": 2})
    svc = RNGService(seed=99)
    val_b = svc.rand("stream:scope", scope={"b": 2, "a": 1})

    assert val_a == val_b


def test_independent_streams_diverge():
    svc = RNGService(seed=77)
    first = svc.rand("stream:first", scope={"x": 1})
    second = svc.rand("stream:second", scope={"x": 1})

    assert first != second


def test_counter_increments_and_signature_stable():
    svc = RNGService(seed=42)
    first = svc.rand("stream:counter", scope={"k": "v"})
    second = svc.rand("stream:counter", scope={"k": "v"})

    assert first != second
    stream_ids = list(svc.counters.values())
    assert stream_ids == [2]

    sig = svc.signature()
    clone = copy.deepcopy(svc)
    assert clone.signature() == sig
    assert clone.rand("stream:counter", scope={"k": "v"}) == svc.rand("stream:counter", scope={"k": "v"})


def test_audit_summary_sorted():
    cfg = RNGConfig(audit_enabled=True, max_audit_streams=4)
    svc = RNGService(seed=5, config=cfg)
    for _ in range(3):
        svc.rand("stream:alpha", scope={})
    for _ in range(2):
        svc.rand("stream:beta", scope={})

    summary = svc.audit_summary()
    assert summary[0][0] == "stream:alpha"
    assert summary[0][1] == 3
    assert summary[1][0] == "stream:beta"
    assert summary[1][1] == 2


def test_ensure_rng_service_lazily_initializes_world():
    class Dummy:
        seed = 11

    world = Dummy()
    svc = ensure_rng_service(world)
    assert isinstance(svc, RNGService)
    assert isinstance(world.rng_service_cfg, RNGConfig)
    assert world.rng_service is svc
