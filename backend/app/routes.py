from datetime import datetime, timezone
from io import BytesIO
import hashlib
import time

import httpx
from pathlib import Path
from uuid import uuid4
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field

from .auth import get_access_token, get_current_user
from .background_jobs import JOB_STATUS_FIELDS, has_active_job, normalize_job_row, schedule_document_job
from .config import settings
from .db import supabase_admin
from .document_processing import chunk_text_with_metadata, extract_pages
from .embeddings import embed_texts
from .document_intelligence import extract_construction_data, analyze_drawing_page
from .engineering_elements import normalize_engineering_elements, persist_engineering_elements
from .boq_document_analysis import normalize_boq_extraction

router = APIRouter(prefix="/api/v1")
BUCKET = "construction-documents"
DB_RETRIES = 3
DB_RETRY_DELAYS = (0.25, 0.75)
ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=2000)
    project_type: Literal["road", "building", "bridge", "water", "utilities", "industrial", "other"] = "other"


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=2000)
    project_type: Literal["road", "building", "bridge", "water", "utilities", "industrial", "other"] | None = None


@router.get("/auth/me")
def me(token: str = Depends(get_access_token)):
    return get_current_user(token)


def _authenticated_client(token: str):
    """Return the shared server client after the caller JWT is validated.

    Database authorization is enforced explicitly by _project_for_member.
    The server-only Supabase secret client avoids mutating a shared
    PostgREST auth header and avoids creating a new HTTP pool per request.
    """
    if supabase_admin is None:
        raise HTTPException(
            status_code=500,
            detail="Server database client is not configured (SUPABASE_SECRET_KEY).",
        )
    return supabase_admin


def _execute_with_retry(operation, operation_name: str):
    """Retry transient Supabase/PostgREST transport failures without retrying API errors."""
    for attempt in range(DB_RETRIES):
        try:
            return operation()
        except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
            if attempt == DB_RETRIES - 1:
                raise HTTPException(
                    status_code=503,
                    detail=f"Database service temporarily unavailable while {operation_name}. Please retry.",
                ) from exc
            time.sleep(DB_RETRY_DELAYS[attempt])
    raise RuntimeError("Unreachable")


def _project_for_member(project_id: str, user_id: str, client):
    project = _execute_with_retry(
        lambda: client.table("projects")
        .select("id,organization_id")
        .eq("id", project_id)
        .single()
        .execute(),
        "checking project access",
    )
    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = _execute_with_retry(
        lambda: client.table("organization_members")
        .select("organization_id")
        .eq("organization_id", project.data["organization_id"])
        .eq("user_id", user_id)
        .limit(1)
        .execute(),
        "checking organization membership",
    )
    if not membership.data:
        raise HTTPException(status_code=403, detail="You are not a member of this project organization")
    return project.data


def _document_for_member(document_id: str, user_id: str, client):
    document = _execute_with_retry(
        lambda: client.table("documents").select("id,project_id").eq("id", document_id).single().execute(),
        "checking document access",
    )
    if not document.data:
        raise HTTPException(status_code=404, detail="Document not found")
    _project_for_member(document.data["project_id"], user_id, client)
    return document.data


def _ensure_organization(user: dict, client) -> str:
    """Return an organization id, creating the user's personal org if needed.

    The caller JWT is validated before this function runs. Bootstrap writes
    use the server-only secret-key client because these are trusted backend
    operations and must not depend on client-side RLS policy evaluation.
    """
    memberships = (
        client.table("organization_members")
        .select("organization_id,role")
        .eq("user_id", user["id"])
        .execute()
    )
    if memberships.data:
        return memberships.data[0]["organization_id"]

    if supabase_admin is None:
        raise HTTPException(
            status_code=500,
            detail="Server organization bootstrap is not configured (SUPABASE_SECRET_KEY).",
        )

    email = (user.get("email") or "user").split("@")[0]
    org_name = f"{email.title()}'s Organization"

    try:
        org = supabase_admin.table("organizations").insert({"name": org_name}).execute()
        if not org.data:
            raise HTTPException(status_code=500, detail="Could not create organization")
        org_id = org.data[0]["id"]

        member = (
            supabase_admin.table("organization_members")
            .insert({"organization_id": org_id, "user_id": user["id"], "role": "owner"})
            .execute()
        )
        if not member.data:
            raise HTTPException(status_code=500, detail="Could not create organization membership")
        return org_id
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Organization bootstrap failed: {exc}") from exc


@router.get("/projects/{project_id}/design/reviews")
def list_design_reviews(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    result = (
        client.table("design_reviews")
        .select(
            "id,project_id,design_asset_id,review_type,status,summary,findings,source_pages,model,confidence,reviewed_at,created_at,updated_at"
        )
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return {"data": result.data or []}


@router.get("/design/assets/{asset_id}/reviews")
def list_asset_reviews(asset_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    asset = client.table("design_assets").select("id,project_id").eq("id", asset_id).maybe_single().execute()
    if not asset.data:
        raise HTTPException(status_code=404, detail="Design asset not found")
    _project_for_member(asset.data["project_id"], user["id"], client)
    result = (
        client.table("design_reviews")
        .select(
            "id,project_id,design_asset_id,review_type,status,summary,findings,source_pages,model,confidence,reviewed_at,created_at,updated_at"
        )
        .eq("design_asset_id", asset_id)
        .order("created_at", desc=True)
        .execute()
    )
    return {"data": result.data or []}


@router.get("/projects/{project_id}/design/assets")
def list_design_assets(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    result = _execute_with_retry(
        lambda: (
            client.table("design_assets")
            .select(
                "id,project_id,document_id,name,discipline,asset_type,revision,sheet_number,status,metadata,created_at,updated_at"
            )
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        ),
        "listing design assets",
    )
    return {"data": result.data or []}


@router.post("/projects/{project_id}/design/assets")
def create_design_asset(project_id: str, payload: dict, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Design asset name is required")
    row = {
        "project_id": project_id,
        "name": name,
        "discipline": str(payload.get("discipline") or "general"),
        "asset_type": str(payload.get("asset_type") or "drawing"),
        "revision": payload.get("revision"),
        "sheet_number": payload.get("sheet_number"),
        "status": str(payload.get("status") or "uploaded"),
        "metadata": payload.get("metadata") or {},
    }
    if payload.get("document_id"):
        _document_for_member(str(payload["document_id"]), user["id"], client)
        row["document_id"] = str(payload["document_id"])
    result = client.table("design_assets").insert(row).execute()
    return result.data[0] if result.data else row


@router.get("/projects")
def list_projects(token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    memberships = _execute_with_retry(
        lambda: client.table("organization_members")
        .select("organization_id")
        .eq("user_id", user["id"])
        .execute(),
        "listing organization memberships",
    )
    org_ids = [row["organization_id"] for row in (memberships.data or [])]
    if not org_ids:
        return {"data": []}
    result = _execute_with_retry(
        lambda: (
            client.table("projects")
            .select("*")
            .in_("organization_id", org_ids)
            .order("created_at", desc=True)
            .execute()
        ),
        "listing projects",
    )
    return {"data": result.data or []}


@router.post("/projects")
def create_project(payload: CreateProjectRequest, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")

    code = (payload.code or "").strip() or None
    description = (payload.description or "").strip() or None

    org_id = _ensure_organization(user, client)

    row = {
        "organization_id": org_id,
        "name": name,
        "code": code,
        "description": description,
        "project_type": payload.project_type,
        "status": "active",
        "created_by": user["id"],
    }

    try:
        result = client.table("projects").insert(row).execute()
    except Exception as exc:
        fallback = {"organization_id": org_id, "name": name}
        if code:
            fallback["code"] = code
        fallback["project_type"] = payload.project_type
        try:
            result = client.table("projects").insert(fallback).execute()
        except Exception as inner:
            raise HTTPException(status_code=500, detail=f"Could not create project: {inner}") from inner

    if not result.data:
        raise HTTPException(status_code=500, detail="Project was not created")

    return {"data": result.data[0]}


@router.patch("/projects/{project_id}")
def update_project(project_id: str, payload: UpdateProjectRequest, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    project = _project_for_member(project_id, user["id"], client)

    updates = {}
    fields = payload.model_fields_set
    if "name" in fields:
        name = (payload.name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Project name is required")
        updates["name"] = name
    if "code" in fields:
        updates["code"] = (payload.code or "").strip() or None
    if "description" in fields:
        updates["description"] = (payload.description or "").strip() or None
    if "project_type" in fields and payload.project_type is not None:
        updates["project_type"] = payload.project_type
    if not updates:
        raise HTTPException(status_code=400, detail="Provide at least one project field to update")

    result = client.table("projects").update(updates).eq("id", project_id).eq("organization_id", project["organization_id"]).select("*").execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found or no changes were saved")
    return {"data": result.data[0]}


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, token: str = Depends(get_access_token)):
    """Delete an empty project only; preserve all linked construction records."""
    user = get_current_user(token)
    client = _authenticated_client(token)
    project = _project_for_member(project_id, user["id"], client)

    documents = client.table("documents").select("id").eq("project_id", project_id).limit(1).execute()
    if documents.data:
        raise HTTPException(status_code=409, detail="This project still has uploaded documents. Delete its documents first, then try again.")

    # Other project modules may have linked records. Let foreign-key constraints
    # protect those records instead of cascading destructive deletes.
    try:
        result = client.table("projects").delete().eq("id", project_id).eq("organization_id", project["organization_id"]).select("id").execute()
    except Exception as exc:
        raise HTTPException(status_code=409, detail="This project has linked construction records. Remove or reassign those records before deleting the project.") from exc
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found or could not be deleted")
    return {"success": True, "project_id": project_id, "message": "Project deleted"}


@router.get("/projects/{project_id}/documents")
def list_documents(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    result = _execute_with_retry(
        lambda: (
            client.table("documents")
            .select("id,name,mime_type,status,created_at,storage_path")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        ),
        "listing project documents",
    )
    return {"data": result.data or []}


@router.post("/projects/{project_id}/documents")
async def upload_document(project_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported document format")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the 50 MB limit")

    file_sha256 = hashlib.sha256(data).hexdigest()
    duplicate = (
        client.table("documents")
        .select("id,name,status")
        .eq("project_id", project_id)
        .eq("file_sha256", file_sha256)
        .limit(1)
        .execute()
    )
    if duplicate.data:
        raise HTTPException(status_code=409, detail="This document is already uploaded to this project")

    document_id = str(uuid4())
    safe_name = Path(file.filename or "document").name
    storage_path = f"{project_id}/{document_id}/{safe_name}"
    job_id = None

    try:
        client.storage.from_(BUCKET).upload(
            storage_path,
            data,
            {"content-type": file.content_type or "application/octet-stream", "upsert": "false"},
        )
        doc = client.table("documents").insert(
            {
                "id": document_id,
                "project_id": project_id,
                "uploaded_by": user["id"],
                "name": safe_name,
                "storage_path": storage_path,
                "mime_type": file.content_type,
                "status": "processing",
                "file_size_bytes": len(data),
                "file_sha256": file_sha256,
            }
        ).execute()
        if not doc.data:
            raise RuntimeError("Document record was not created")

        job = client.table("document_processing_jobs").insert(
            {
                "document_id": document_id,
                "status": "queued",
                "processor": "construction-text-embedding-v1",
                "progress": 0,
            }
        ).execute()
        if not job.data:
            raise RuntimeError("Processing job was not created")
        job_id = job.data[0]["id"]

        knowledge = client.table("ai_knowledge_documents").insert(
            {
                "document_id": document_id,
                "project_id": project_id,
                "processing_job_id": job_id,
                "status": "pending",
            }
        ).execute()
        if not knowledge.data:
            raise RuntimeError("Knowledge document was not created")
        knowledge_id = knowledge.data[0]["id"]

        schedule_document_job(
            background_tasks,
            project_id=project_id,
            document_id=document_id,
            job_id=job_id,
            knowledge_id=knowledge_id,
            safe_name=safe_name,
            content_type=file.content_type or "",
            data=data,
            access_token=token,
        )

        return {
            "document_id": document_id,
            "job_id": job_id,
            "knowledge_document_id": knowledge_id,
            "status": "queued",
            "message": "Document accepted; AI processing started in the background. Poll /documents/{id}/status.",
        }
    except Exception as exc:
        if job_id:
            client.table("document_processing_jobs").update(
                {
                    "status": "failed",
                    "progress": 100,
                    "error_message": str(exc),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", job_id).execute()
        try:
            client.table("documents").update({"status": "failed"}).eq("id", document_id).execute()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Document upload failed: {exc}") from exc


@router.delete("/documents/{document_id}")
def delete_document(document_id: str, token: str = Depends(get_access_token)):
    """Permanently delete an authorized project document and its related AI data."""
    user = get_current_user(token)
    client = _authenticated_client(token)
    document_result = (
        client.table("documents")
        .select("id,project_id,storage_path,name")
        .eq("id", document_id)
        .maybe_single()
        .execute()
    )
    document = document_result.data
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    _project_for_member(document["project_id"], user["id"], client)

    # Remove the original file first; do not delete the database record if storage fails.
    storage_path = document.get("storage_path")
    if storage_path:
        try:
            client.storage.from_(BUCKET).remove([storage_path])
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Could not remove the stored document file. No document records were deleted.") from exc

    # Delete dependent records before the parent document to avoid orphaned AI data.
    try:
        assets = (
            client.table("design_assets")
            .select("id")
            .eq("document_id", document_id)
            .execute()
        )
        asset_ids = [row["id"] for row in (assets.data or []) if row.get("id")]
        if asset_ids:
            client.table("design_reviews").delete().in_("design_asset_id", asset_ids).execute()
            client.table("design_assets").delete().in_("id", asset_ids).execute()

        for table in ("ai_knowledge_chunks", "ai_extractions", "ai_knowledge_documents", "document_processing_jobs"):
            client.table(table).delete().eq("document_id", document_id).execute()

        client.table("documents").delete().eq("id", document_id).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="The file was removed, but related document records could not all be deleted. Please contact the administrator before retrying.",
        ) from exc

    return {"success": True, "document_id": document_id, "message": "Document deleted"}
    

@router.get("/documents/{document_id}/extraction")
def document_extraction(document_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _document_for_member(document_id, user["id"], client)
    result = (
        client.table("ai_extractions")
        .select("id,document_id,extraction_type,data,created_at")
        .eq("document_id", document_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="AI extraction not found")
    return result.data[0]




@router.get("/documents/{document_id}/results")
def document_results(document_id: str, token: str = Depends(get_access_token)):
    """Return extracted text and the latest structured AI extraction for an authorized document."""
    user = get_current_user(token)
    client = _authenticated_client(token)
    _document_for_member(document_id, user["id"], client)

    extraction_result = _execute_with_retry(
        lambda: (
            client.table("ai_extractions")
            .select("id,document_id,extraction_type,data,created_at")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ),
        "loading document extraction results",
    )
    knowledge_result = _execute_with_retry(
        lambda: (
            client.table("ai_knowledge_documents")
            .select("extracted_text,page_count,status,processing_job_id,created_at")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ),
        "loading extracted document text",
    )
    extraction = extraction_result.data[0] if extraction_result.data else None
    extraction_data = extraction.get("data") if isinstance(extraction, dict) else None
    is_boq = (
        isinstance(extraction, dict)
        and (
            extraction.get("extraction_type") == "boq"
            or (isinstance(extraction_data, dict) and isinstance(extraction_data.get("items"), list))
        )
    )
    return {
        "extraction": extraction,
        "knowledge": knowledge_result.data[0] if knowledge_result.data else None,
        "boq_analysis": normalize_boq_extraction({
            "data": extraction.get("data"),
            "document_type": extraction.get("extraction_type"),
        }) if is_boq else None,
    }


@router.get("/documents/{document_id}/boq.xlsx")
def export_document_boq_excel(document_id: str, token: str = Depends(get_access_token)):
    """Export extracted BOQ rows to an Excel workbook after checking document access."""
    user = get_current_user(token)
    client = _authenticated_client(token)
    _document_for_member(document_id, user["id"], client)
    result = _execute_with_retry(
        lambda: (
            client.table("ai_extractions")
            .select("extraction_type,data")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ),
        "loading BOQ extraction for Excel export",
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No extraction is available for this document")
    extraction = result.data[0]
    data = extraction.get("data") if isinstance(extraction.get("data"), dict) else {}
    if extraction.get("extraction_type") != "boq" and not isinstance(data.get("items"), list):
        raise HTTPException(status_code=422, detail="This document does not contain a recognized BOQ extraction")
    analysis = normalize_boq_extraction({
        "document_type": extraction.get("extraction_type"),
        "data": data,
    })
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "BOQ Analysis"
    sheet.append(["Item No.", "Description", "Unit", "Quantity", "Rate", "Stated Amount", "Calculated Amount", "Difference", "Review Flags"])
    for row in analysis["rows"]:
        sheet.append([
            row["code"], row["description"], row["unit"], row["quantity"], row["rate"],
            row["stated_amount"], row["calculated_amount"], row["difference"],
            ", ".join(row["issues"]),
        ])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column, width in {"A": 14, "B": 52, "C": 12, "D": 16, "E": 16, "F": 20, "G": 20, "H": 16, "I": 34}.items():
        sheet.column_dimensions[column].width = width
    summary = workbook.create_sheet("Summary")
    summary.append(["Metric", "Value"])
    summary.append(["Extracted item count", analysis["item_count"]])
    summary.append(["Stated amount total", analysis["stated_total"]])
    summary.append(["Calculated amount total", analysis["calculated_total"]])
    summary.append(["Rows with review flags", analysis["flag_count"]])
    summary.append(["Review note", analysis["note"]])
    summary.column_dimensions["A"].width = 28
    summary.column_dimensions["B"].width = 100
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="boq-analysis-{document_id[:8]}.xlsx"'},
    )


@router.get("/documents/{document_id}/status")
def document_status(document_id: str, token: str = Depends(get_access_token)):
    """Latest processing job for a document (queued | processing | completed | failed)."""
    user = get_current_user(token)
    client = _authenticated_client(token)
    _document_for_member(document_id, user["id"], client)
    result = _execute_with_retry(
        lambda: (
            client.table("document_processing_jobs")
            .select(JOB_STATUS_FIELDS)
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ),
        "checking document processing status",
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return normalize_job_row(result.data[0])


@router.get("/projects/{project_id}/jobs")
def list_project_jobs(project_id: str, token: str = Depends(get_access_token)):
    """List recent document processing jobs for a project."""
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    docs = (
        client.table("documents")
        .select("id")
        .eq("project_id", project_id)
        .execute()
    )
    doc_ids = [d["id"] for d in (docs.data or [])]
    if not doc_ids:
        return {"data": []}
    result = (
        client.table("document_processing_jobs")
        .select(JOB_STATUS_FIELDS)
        .in_("document_id", doc_ids)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return {"data": [normalize_job_row(r) for r in (result.data or [])]}


@router.post("/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    token: str = Depends(get_access_token),
):
    """Re-queue AI processing for an existing document (downloads bytes from storage)."""
    user = get_current_user(token)
    client = _authenticated_client(token)
    doc_row = (
        client.table("documents")
        .select("id,project_id,name,mime_type,storage_path,status")
        .eq("id", document_id)
        .single()
        .execute()
    )
    if not doc_row.data:
        raise HTTPException(status_code=404, detail="Document not found")
    document = doc_row.data
    _project_for_member(document["project_id"], user["id"], client)

    # Avoid creating another job when a previous attempt is still queued/running.
    active_jobs = _execute_with_retry(
        lambda: (
            client.table("document_processing_jobs")
            .select("id,status,created_at,started_at")
            .eq("document_id", document_id)
            .in_("status", ["queued", "processing"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ),
        "checking for an active document processing job",
    )
    if has_active_job(active_jobs.data or []):
        active = (active_jobs.data or [])[0]
        status = str(active.get("status") or "active").lower()
        raise HTTPException(
            status_code=409,
            detail=(
                f"This document already has a {status} processing job. "
                "Wait for it to finish before requesting reprocessing. "
                "If it is marked 'Taking longer', check service logs before retrying."
            ),
        )

    storage_path = document.get("storage_path")
    if not storage_path:
        raise HTTPException(status_code=400, detail="Document has no storage path")

    try:
        file_bytes = client.storage.from_(BUCKET).download(storage_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not download document: {exc}") from exc
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty storage object")

    try:
        job = client.table("document_processing_jobs").insert(
            {
                "document_id": document_id,
                "status": "queued",
                "processor": "construction-text-embedding-v1",
                "progress": 0,
            }
        ).execute()
    except Exception as exc:
        # The partial unique index is the race-safe authority. If another
        # request inserted an active job after our pre-check, return a conflict.
        error_code = getattr(exc, "code", None)
        if error_code == "23505" or "23505" in str(exc):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This document already has an active processing job. "
                    "Wait for it to finish before requesting reprocessing."
                ),
            ) from exc
        raise HTTPException(status_code=500, detail="Could not create processing job") from exc
    if not job.data:
        raise HTTPException(status_code=500, detail="Could not create processing job")
    job_id = job.data[0]["id"]

    knowledge = (
        client.table("ai_knowledge_documents")
        .select("id")
        .eq("document_id", document_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if knowledge.data:
        knowledge_id = knowledge.data[0]["id"]
        client.table("ai_knowledge_documents").update(
            {"status": "pending", "processing_job_id": job_id}
        ).eq("id", knowledge_id).execute()
    else:
        knowledge = client.table("ai_knowledge_documents").insert(
            {
                "document_id": document_id,
                "project_id": document["project_id"],
                "processing_job_id": job_id,
                "status": "pending",
            }
        ).execute()
        if not knowledge.data:
            raise HTTPException(status_code=500, detail="Could not create knowledge document")
        knowledge_id = knowledge.data[0]["id"]

    client.table("documents").update({"status": "processing"}).eq("id", document_id).execute()

    schedule_document_job(
        background_tasks,
        project_id=document["project_id"],
        document_id=document_id,
        job_id=job_id,
        knowledge_id=knowledge_id,
        safe_name=document.get("name") or "document",
        content_type=document.get("mime_type") or "",
        data=file_bytes if isinstance(file_bytes, (bytes, bytearray)) else bytes(file_bytes),
        access_token=token,
    )

    return {
        "document_id": document_id,
        "job_id": job_id,
        "knowledge_document_id": knowledge_id,
        "status": "queued",
        "message": "Reprocessing queued. Poll /documents/{id}/status.",
    }
