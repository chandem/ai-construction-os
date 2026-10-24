"""Background AI job helpers for document processing.

Uses FastAPI BackgroundTasks (in-process). No Redis/Celery required for MVP.
Job state lives in document_processing_jobs; callers poll status APIs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .db import supabase_admin
from .document_pipeline import run_document_pipeline_safe


def build_pipeline_kwargs(
    *,
    project_id: str,
    document_id: str,
    job_id: str,
    knowledge_id: str,
    safe_name: str,
    content_type: str,
    data: bytes,
    access_token: str | None = None,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "document_id": document_id,
        "job_id": job_id,
        "knowledge_id": knowledge_id,
        "safe_name": safe_name,
        "content_type": content_type,
        "data": data,
        "access_token": access_token,
    }


def execute_document_job(
    *,
    project_id: str,
    document_id: str,
    job_id: str,
    knowledge_id: str,
    safe_name: str,
    content_type: str,
    data: bytes,
    access_token: str | None = None,
) -> dict[str, Any]:
    """Run pipeline with optional user JWT for RLS-aware Supabase client."""
    if supabase_admin is None:
        return {
            "document_id": document_id,
            "job_id": job_id,
            "status": "failed",
            "error": "Server database client is not configured (SUPABASE_SECRET_KEY).",
        }
    # Background jobs run only after the authenticated upload request has
    # created the job. Use the server-only client here so a shared client
    # never has its auth header mutated by concurrent jobs.
    client = supabase_admin
    return run_document_pipeline_safe(
        client,
        project_id=project_id,
        document_id=document_id,
        job_id=job_id,
        knowledge_id=knowledge_id,
        safe_name=safe_name,
        content_type=content_type,
        data=data,
    )


def schedule_document_job(background_tasks, **kwargs: Any) -> None:
    """Enqueue document pipeline on FastAPI BackgroundTasks."""
    background_tasks.add_task(execute_document_job, **kwargs)


def has_active_job(rows: list[dict[str, Any]] | None) -> bool:
    """Return whether a document already has a queued or running processing job."""
    return any(
        str(row.get("status") or "").lower() in {"queued", "processing"}
        for row in (rows or [])
        if isinstance(row, dict)
    )


STALLED_JOB_TIMEOUT_MINUTES = 45


def _job_is_stalled(row: dict[str, Any]) -> bool:
    """Flag old processing jobs for investigation; never mutate job state here."""
    if str(row.get("status") or "").lower() != "processing":
        return False
    timestamp = row.get("started_at") or row.get("created_at")
    if not timestamp:
        return False
    try:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
        return age_seconds > STALLED_JOB_TIMEOUT_MINUTES * 60
    except (TypeError, ValueError, OverflowError):
        return False


JOB_STATUS_FIELDS = (
    "id,document_id,status,processor,progress,error_message,"
    "started_at,completed_at,created_at"
)


def normalize_job_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "document_id": row.get("document_id"),
        "status": row.get("status"),
        "processor": row.get("processor"),
        "progress": row.get("progress"),
        "error_message": row.get("error_message"),
        "started_at": row.get("started_at"),
        "completed_at": row.get("completed_at"),
        "created_at": row.get("created_at"),
        "is_terminal": (row.get("status") or "") in {"completed", "failed"},
        "is_stalled": _job_is_stalled(row),
    }
