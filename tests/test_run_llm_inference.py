"""Resilience tests for the inference runner: a dead/rate-limited model must be
skipped (circuit-breaker) without aborting the rest of the queue.
"""

from __future__ import annotations

import pytest

import research.release.run_llm_inference as R


def test_circuit_breaker_aborts_dead_model(monkeypatch):
    """If the first CIRCUIT_BREAKER_PROBE docs all hard-fail, the combo aborts
    early (after exactly PROBE × MAX_RETRIES attempts) instead of grinding all docs."""
    monkeypatch.setattr(R.time, "sleep", lambda *a, **k: None)  # no backoff sleeps
    monkeypatch.setattr(R, "make_extractor", lambda *a, **k: object())
    monkeypatch.setattr(R, "make_classifier", lambda *a, **k: object())
    calls = {"n": 0}

    def boom(*_a, **_k):
        calls["n"] += 1
        raise RuntimeError("api down")

    monkeypatch.setattr(R, "_infer_one", boom)

    with pytest.raises(RuntimeError, match=r"first 15 docs all failed"):
        R.run_model_technique(
            "deadmodel", "id", "few_shot", ["doc"] * 50,
            structured="function_calling", provider_order=None,
            azure_deployment=None, selector=None,
        )
    # Aborted at the probe boundary: 15 docs × MAX_RETRIES, not all 50.
    assert calls["n"] == R.CIRCUIT_BREAKER_PROBE * R.MAX_RETRIES


def test_live_model_does_not_trip_breaker(monkeypatch):
    """One success inside the probe window keeps the combo running to the end."""
    monkeypatch.setattr(R.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(R, "make_extractor", lambda *a, **k: object())
    monkeypatch.setattr(R, "_pred_dict", lambda r: {"multas": []})
    n = {"i": 0}

    def sometimes(*_a, **_k):
        n["i"] += 1
        if n["i"] == 1:  # first doc succeeds → model is alive
            return None
        raise RuntimeError("flaky")

    monkeypatch.setattr(R, "_infer_one", sometimes)
    recs = R.run_model_technique(
        "flaky", "id", "few_shot", ["doc"] * 20,
        structured="function_calling", provider_order=None,
        azure_deployment=None, selector=None,
    )
    assert len(recs) == 20  # ran to completion despite later failures


def test_latency_breaker_skips_slow_model(monkeypatch):
    """A rate-limited model whose first LATENCY_PROBE docs are too slow is
    aborted (even though the calls succeed)."""
    monkeypatch.setattr(R.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(R, "make_extractor", lambda *a, **k: object())
    monkeypatch.setattr(R, "_pred_dict", lambda r: {})
    monkeypatch.setattr(R, "_infer_one", lambda *a, **k: None)  # fast success
    # monotonic: combo_start=0, then probe check at +100s → > 90s threshold
    clock = iter([0.0, 100.0, 100.0])
    monkeypatch.setattr(R.time, "monotonic", lambda: next(clock))
    with pytest.raises(RuntimeError, match="too slow"):
        R.run_model_technique(
            "slowmodel", "id", "few_shot", ["doc"] * 50,
            structured="function_calling", provider_order=None,
            azure_deployment=None, selector=None, max_probe_seconds=90.0,
        )


def test_latency_breaker_allows_fast_model(monkeypatch):
    """A fast model passes the latency probe and runs to completion."""
    monkeypatch.setattr(R.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(R, "make_extractor", lambda *a, **k: object())
    monkeypatch.setattr(R, "_pred_dict", lambda r: {})
    monkeypatch.setattr(R, "_infer_one", lambda *a, **k: None)
    clock = iter([0.0, 5.0])  # probe took 5s < 90s
    monkeypatch.setattr(R.time, "monotonic", lambda: next(clock))
    recs = R.run_model_technique(
        "fast", "id", "few_shot", ["doc"] * 4,
        structured="function_calling", provider_order=None,
        azure_deployment=None, selector=None, max_probe_seconds=90.0,
    )
    assert len(recs) == 4


def test_run_skips_failing_model_and_continues(monkeypatch):
    """A model whose combo raises is logged and skipped; the queue continues."""
    monkeypatch.setattr(R, "_load_env", lambda: None)
    monkeypatch.setattr(R, "load_corpus", lambda limit=None: ["d", "d"])
    monkeypatch.setattr(R, "_write", lambda *a, **k: None)
    seen: list[str] = []

    def fake_rmt(key, *_a, **_k):
        seen.append(key)
        if key == "qwen2.5-72b":
            raise RuntimeError("rate-limited to death")
        return [{"index": 0}]

    monkeypatch.setattr(R, "run_model_technique", fake_rmt)
    R.run(
        ["llama-3.3-70b", "qwen2.5-72b", "gpt-4.1"],
        ["few_shot"],
        limit=2,
        structured=None,
        force=True,
    )
    assert seen == ["llama-3.3-70b", "qwen2.5-72b", "gpt-4.1"]
