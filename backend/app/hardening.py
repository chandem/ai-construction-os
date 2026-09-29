"""Hardening foundation: job queue with retries, cost control, system health.

Builds on document background jobs with a generic queue model, retry policy,
token/cost budgets, and an ops health rollup for the Ops Center.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

HARDENING_SOURCE = "hardening_ops"

JOB_KINDS = (
    "document_pipeline",
    "integration_sync",
    "prediction_generate",
    "procurement_generate",
    "brain_refresh",
    "other",
)
JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled", "dead")
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = (5, 30, 120)

# Illustrative unit costs (USD) for budget tracking — not billing rates
UNIT_COSTS: dict[str, float] = {
    "embedding_1k_tokens": 0.0001,
    "chat_1k_tokens": 0.002,
    "vision_image": 0.01,
    "document_pipeline": 0.05,
    "integration_sync": 0.01,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_queue_job(
    *,
    project_id: str | None = None,
    kind: str = "other",
    payload: dict[str, Any] | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    priority: int = 100,
) -> dict[str, Any]:
    if kind not in JOB_KINDS:
        kind = "other"
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "kind": kind,
        "status": "queued",
        "priority": priority,
        "attempt": 0,
        "max_attempts": max(1, int(max_attempts)),
        "payload": payload or {},
        "last_error": None,
        "available_at": utc_now_iso(),
        "started_at": None,
        "finished_at": None,
        "source": HARDENING_SOURCE,
        "properties": {},
    }


def should_retry(job: dict[str, Any]) -> bool:
    attempt = int(job.get("attempt") or 0)
    max_a = int(job.get("max_attempts") or DEFAULT_MAX_ATTEMPTS)
    status = job.get("status")
    return status == "failed" and attempt < max_a


def backoff_seconds(attempt: int) -> int:
    idx = max(0, min(len(DEFAULT_BACKOFF_SECONDS) - 1, attempt - 1))
    return DEFAULT_BACKOFF_SECONDS[idx]


def mark_running(job: dict[str, Any]) -> dict[str, Any]:
    updated = dict(job)
    updated["status"] = "running"
    updated["attempt"] = int(job.get("attempt") or 0) + 1
    updated["started_at"] = utc_now_iso()
    updated["last_error"] = None
    return updated


def mark_succeeded(job: dict[str, Any]) -> dict[str, Any]:
    updated = dict(job)
    updated["status"] = "succeeded"
    updated["finished_at"] = utc_now_iso()
    updated["last_error"] = None
    return updated


def mark_failed(job: dict[str, Any], error: str) -> dict[str, Any]:
    updated = dict(job)
    updated["last_error"] = (error or "unknown error")[:2000]
    updated["finished_at"] = utc_now_iso()
    if should_retry({**updated, "status": "failed"}):
        updated["status"] = "queued"
        # schedule availability after backoff
        from datetime import timedelta

        delay = backoff_seconds(int(updated.get("attempt") or 1))
        avail = datetime.now(timezone.utc) + timedelta(seconds=delay)
        updated["available_at"] = avail.isoformat()
        updated["properties"] = {
            **(updated.get("properties") or {}),
            "next_retry_seconds": delay,
        }
    else:
        updated["status"] = "dead" if int(updated.get("attempt") or 0) >= int(
            updated.get("max_attempts") or DEFAULT_MAX_ATTEMPTS
        ) else "failed"
    return updated


def estimate_cost(
    *,
    kind: str | None = None,
    embedding_tokens: int = 0,
    chat_tokens: int = 0,
    vision_images: int = 0,
    units: int = 1,
) -> dict[str, Any]:
    """Rough cost estimate for budget display (not invoices)."""
    total = 0.0
    lines: list[dict[str, Any]] = []
    if embedding_tokens:
        c = (embedding_tokens / 1000.0) * UNIT_COSTS["embedding_1k_tokens"]
        total += c
        lines.append({"item": "embeddings", "tokens": embedding_tokens, "cost_usd": round(c, 6)})
    if chat_tokens:
        c = (chat_tokens / 1000.0) * UNIT_COSTS["chat_1k_tokens"]
        total += c
        lines.append({"item": "chat", "tokens": chat_tokens, "cost_usd": round(c, 6)})
    if vision_images:
        c = vision_images * UNIT_COSTS["vision_image"]
        total += c
        lines.append({"item": "vision", "images": vision_images, "cost_usd": round(c, 6)})
    if kind and kind in UNIT_COSTS and not lines:
        c = UNIT_COSTS[kind] * max(1, units)
        total += c
        lines.append({"item": kind, "units": units, "cost_usd": round(c, 6)})
    return {
        "estimated_cost_usd": round(total, 6),
        "lines": lines,
        "notes": "Illustrative unit costs for ops budgets — not provider invoices.",
    }


def build_cost_event(
    *,
    project_id: str | None,
    category: str,
    amount_usd: float,
    units: int = 1,
    reference: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "category": category,
        "amount_usd": round(float(amount_usd), 6),
        "units": units,
        "reference": reference or "",
        "notes": notes or "",
        "recorded_at": utc_now_iso(),
        "source": HARDENING_SOURCE,
        "properties": {},
    }


def cost_summary(events: list[dict[str, Any]], budget_usd: float | None = None) -> dict[str, Any]:
    total = sum(float(e.get("amount_usd") or 0) for e in events)
    by_cat: dict[str, float] = {}
    for e in events:
        cat = e.get("category") or "other"
        by_cat[cat] = by_cat.get(cat, 0.0) + float(e.get("amount_usd") or 0)
    by_cat = {k: round(v, 6) for k, v in by_cat.items()}
    remaining = None if budget_usd is None else round(float(budget_usd) - total, 6)
    over = budget_usd is not None and total > float(budget_usd)
    return {
        "event_count": len(events),
        "total_usd": round(total, 6),
        "by_category": by_cat,
        "budget_usd": budget_usd,
        "remaining_usd": remaining,
        "over_budget": over,
        "notes": "Tracked AI/ops spend for cost control. Not a finance ledger.",
    }


def queue_summary(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for j in jobs:
        s = j.get("status") or "queued"
        by_status[s] = by_status.get(s, 0) + 1
        k = j.get("kind") or "other"
        by_kind[k] = by_kind.get(k, 0) + 1
    return {
        "job_count": len(jobs),
        "by_status": by_status,
        "by_kind": by_kind,
        "queued": by_status.get("queued", 0),
        "running": by_status.get("running", 0),
        "failed": by_status.get("failed", 0) + by_status.get("dead", 0),
        "succeeded": by_status.get("succeeded", 0),
    }


def system_health(
    *,
    queue: dict[str, Any] | None = None,
    cost: dict[str, Any] | None = None,
    checks: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Simple health rollup for Ops Center."""
    q = queue or {}
    c = cost or {}
    ch = checks or {}
    issues: list[str] = []
    if (q.get("failed") or 0) > 0:
        issues.append(f"{q.get('failed')} failed/dead jobs")
    if (q.get("running") or 0) > 20:
        issues.append("High running job count")
    if c.get("over_budget"):
        issues.append("AI/ops budget exceeded")
    for name, ok in ch.items():
        if not ok:
            issues.append(f"Check failed: {name}")
    status = "healthy"
    if issues:
        status = "degraded" if len(issues) < 3 else "unhealthy"
    return {
        "status": status,
        "issues": issues,
        "queue": q,
        "cost": {
            "total_usd": c.get("total_usd"),
            "budget_usd": c.get("budget_usd"),
            "over_budget": c.get("over_budget"),
        },
        "checks": ch,
        "checked_at": utc_now_iso(),
        "notes": "Ops health is indicative for platform reliability.",
    }


def persist_queue_job(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row.get("project_id"),
        "kind": row.get("kind"),
        "status": row.get("status") or "queued",
        "priority": row.get("priority") or 100,
        "attempt": row.get("attempt") or 0,
        "max_attempts": row.get("max_attempts") or DEFAULT_MAX_ATTEMPTS,
        "payload": row.get("payload") or {},
        "last_error": row.get("last_error"),
        "available_at": row.get("available_at"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
        "source": row.get("source") or HARDENING_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("ops_queue_jobs").upsert(payload).execute()
        return payload
    except Exception:
        return None


def persist_cost_event(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row.get("project_id"),
        "category": row.get("category"),
        "amount_usd": row.get("amount_usd"),
        "units": row.get("units") or 1,
        "reference": row.get("reference"),
        "notes": row.get("notes"),
        "recorded_at": row.get("recorded_at"),
        "source": row.get("source") or HARDENING_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("ops_cost_events").upsert(payload).execute()
        return payload
    except Exception:
        return None
