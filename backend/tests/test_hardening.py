"""Unit tests for hardening queue / retries / cost / health (Phase 13)."""

from typing import Any


def _load():
    ns: dict[str, Any] = {
        "Any": Any,
        "uuid4": __import__("uuid").uuid4,
        "datetime": __import__("datetime").datetime,
        "timezone": __import__("datetime").timezone,
        "timedelta": __import__("datetime").timedelta,
    }
    src = open(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app" / "hardening.py")).read()
    src = src.replace("from __future__ import annotations\n", "")
    src = src.replace("from datetime import datetime, timezone\n", "")
    exec(compile(src, "hardening.py", "exec"), ns)
    return ns


def test_queue_retry():
    ns = _load()
    job = ns["build_queue_job"](project_id="p", kind="document_pipeline", max_attempts=3)
    assert job["status"] == "queued"
    job = ns["mark_running"](job)
    assert job["attempt"] == 1 and job["status"] == "running"
    job = ns["mark_failed"](job, "timeout")
    assert job["status"] == "queued"  # retry scheduled
    assert job["attempt"] == 1
    job = ns["mark_running"](job)
    job = ns["mark_failed"](job, "timeout")
    job = ns["mark_running"](job)
    job = ns["mark_failed"](job, "timeout")
    assert job["status"] == "dead"
    assert not ns["should_retry"](job)


def test_success():
    ns = _load()
    job = ns["build_queue_job"](kind="prediction_generate")
    job = ns["mark_running"](job)
    job = ns["mark_succeeded"](job)
    assert job["status"] == "succeeded"


def test_cost_and_health():
    ns = _load()
    est = ns["estimate_cost"](chat_tokens=5000, embedding_tokens=10000)
    assert est["estimated_cost_usd"] > 0
    events = [
        ns["build_cost_event"](project_id="p", category="chat", amount_usd=0.01),
        ns["build_cost_event"](project_id="p", category="embeddings", amount_usd=0.002),
    ]
    cs = ns["cost_summary"](events, budget_usd=0.005)
    assert cs["over_budget"] is True
    qs = ns["queue_summary"](
        [
            {"status": "queued", "kind": "other"},
            {"status": "failed", "kind": "document_pipeline"},
        ]
    )
    assert qs["failed"] == 1
    health = ns["system_health"](queue=qs, cost=cs, checks={"db": True, "storage": True})
    assert health["status"] in ("degraded", "unhealthy")
    assert len(health["issues"]) >= 1


if __name__ == "__main__":
    test_queue_retry()
    test_success()
    test_cost_and_health()
    print("All hardening unit tests passed.")
