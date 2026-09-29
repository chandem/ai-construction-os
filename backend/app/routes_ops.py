"""Ops / hardening routes (Phase 13): queue, cost, health."""
from fastapi import APIRouter, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .db import supabase
from .routes import _project_for_member
from .hardening import (
    build_cost_event,
    build_queue_job,
    cost_summary,
    estimate_cost,
    mark_failed,
    mark_running,
    mark_succeeded,
    persist_cost_event,
    persist_queue_job,
    queue_summary,
    system_health,
)

router = APIRouter()

QUEUE_JOB_FIELDS = (
    "id,project_id,kind,status,priority,attempt,max_attempts,payload,last_error,"
    "available_at,started_at,finished_at,source,properties,created_at,updated_at"
)
COST_EVENT_FIELDS = (
    "id,project_id,category,amount_usd,units,reference,notes,recorded_at,source,"
    "properties,created_at,updated_at"
)


@router.get("/projects/{project_id}/ops/summary")
def project_ops_summary(project_id: str, token: str = Depends(get_access_token)):
    """Queue + cost + health rollup for Ops Center."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)

    jobs: list[dict] = []
    events: list[dict] = []
    try:
        jobs = (
            client.table("ops_queue_jobs")
            .select(QUEUE_JOB_FIELDS)
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
    except Exception:
        jobs = []
    try:
        events = (
            client.table("ops_cost_events")
            .select(COST_EVENT_FIELDS)
            .eq("project_id", project_id)
            .order("recorded_at", desc=True)
            .limit(100)
            .execute()
            .data
            or []
        )
    except Exception:
        events = []

    qsum = queue_summary(jobs)
    csum = cost_summary(events, budget_usd=50.0)
    health = system_health(queue=qsum, cost=csum, checks={"api": True, "auth": True})
    return {
        "data": {"health": health, "queue": qsum, "cost": csum},
        "jobs": jobs[:20],
        "cost_events": events[:20],
    }


@router.get("/projects/{project_id}/ops/queue")
def list_queue_jobs(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("ops_queue_jobs")
            .select(QUEUE_JOB_FIELDS)
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return {"data": result.data or [], "summary": queue_summary(result.data or [])}
    except Exception:
        return {
            "data": [],
            "summary": queue_summary([]),
            "warning": "ops_queue_jobs table is not available yet — apply supabase/hardening.sql",
        }


@router.post("/projects/{project_id}/ops/queue")
def enqueue_job(
    project_id: str,
    kind: str = "other",
    token: str = Depends(get_access_token),
):
    """Enqueue a generic ops job (foundation — no worker drain)."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    job = build_queue_job(project_id=project_id, kind=kind, payload={"enqueued_by": user.get("id")})
    persisted = persist_queue_job(client, job)
    out = {"data": job, "persisted": persisted is not None}
    if persisted is None:
        out["warning"] = "ops_queue_jobs table is not available yet — apply supabase/hardening.sql"
    return out


@router.post("/projects/{project_id}/ops/queue/{job_id}/run")
def run_queue_job_once(project_id: str, job_id: str, token: str = Depends(get_access_token)):
    """Simulate one attempt: running → succeeded (foundation worker stub)."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)

    job: dict | None = None
    try:
        result = (
            client.table("ops_queue_jobs")
            .select(QUEUE_JOB_FIELDS)
            .eq("id", job_id)
            .eq("project_id", project_id)
            .maybe_single()
            .execute()
        )
        job = result.data
    except Exception:
        job = None
    if not job:
        job = build_queue_job(project_id=project_id, kind="other")
        job["id"] = job_id

    job = mark_running(job)
    job = mark_succeeded(job)
    persisted = persist_queue_job(client, job)

    est = estimate_cost(kind=job.get("kind") or "other")
    event = build_cost_event(
        project_id=project_id,
        category=job.get("kind") or "other",
        amount_usd=float(est.get("estimated_cost_usd") or 0),
        reference=job_id,
        notes="Simulated job run cost",
    )
    persist_cost_event(client, event)

    out = {"data": job, "cost_event": event, "persisted": persisted is not None}
    if not persisted:
        out["warning"] = "ops tables not available yet — apply supabase/hardening.sql"
    return out


@router.get("/projects/{project_id}/ops/cost")
def list_cost_events(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("ops_cost_events")
            .select(COST_EVENT_FIELDS)
            .eq("project_id", project_id)
            .order("recorded_at", desc=True)
            .limit(100)
            .execute()
        )
        events = result.data or []
        return {"data": events, "summary": cost_summary(events, budget_usd=50.0)}
    except Exception:
        return {
            "data": [],
            "summary": cost_summary([], budget_usd=50.0),
            "warning": "ops_cost_events table is not available yet — apply supabase/hardening.sql",
        }


@router.get("/projects/{project_id}/ops/health")
def project_ops_health(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    jobs: list[dict] = []
    events: list[dict] = []
    try:
        jobs = (
            client.table("ops_queue_jobs")
            .select(QUEUE_JOB_FIELDS)
            .eq("project_id", project_id)
            .limit(50)
            .execute()
            .data
            or []
        )
    except Exception:
        jobs = []
    try:
        events = (
            client.table("ops_cost_events")
            .select(COST_EVENT_FIELDS)
            .eq("project_id", project_id)
            .limit(100)
            .execute()
            .data
            or []
        )
    except Exception:
        events = []
    health = system_health(
        queue=queue_summary(jobs),
        cost=cost_summary(events, budget_usd=50.0),
        checks={"api": True, "auth": True},
    )
    return {"data": health}
