"""Background AI job helpers for document processing.

Uses FastAPI BackgroundTasks (in-process). No Redis/Celery required for MVP.
Job state lives in document_processing_jobs; callers poll status APIs.
"""

from __future__ import annotations

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
    }
