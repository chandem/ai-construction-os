from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from .auth import get_access_token, get_current_user
from .db import supabase
from .document_processing import chunk_text, extract_text

router = APIRouter(prefix="/api/v1")
BUCKET = "construction-documents"
ALLOWED_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain", "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"}

@router.get("/auth/me")
def me(token: str = Depends(get_access_token)):
    return get_current_user(token)

@router.get("/projects")
def list_projects(token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    memberships = client.table("organization_members").select("organization_id").eq("user_id", user["id"]).execute()
    org_ids = [row["organization_id"] for row in (memberships.data or [])]
    if not org_ids:
        return {"data": []}
    result = client.table("projects").select("*").in_("organization_id", org_ids).order("created_at", desc=True).execute()
    return {"data": result.data or []}

@router.post("/projects/{project_id}/documents")
async def upload_document(project_id: str, file: UploadFile = File(...), token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    project = client.table("projects").select("id,organization_id").eq("id", project_id).single().execute()
    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = client.table("organization_members").select("organization_id").eq("organization_id", project.data["organization_id"]).eq("user_id", user["id"]).limit(1).execute()
    if not membership.data:
        raise HTTPException(status_code=403, detail="You are not a member of this project organization")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported document format")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the 50 MB limit")
    document_id = str(uuid4())
    safe_name = Path(file.filename or "document").name
    storage_path = f"{project_id}/{document_id}/{safe_name}"
    try:
        client.storage.from_(BUCKET).upload(storage_path, data, {"content-type": file.content_type or "application/octet-stream", "upsert": "false"})
        doc = client.table("documents").insert({"id": document_id, "project_id": project_id, "uploaded_by": user["id"], "name": safe_name, "storage_path": storage_path, "mime_type": file.content_type, "status": "processing"}).execute()
        if not doc.data:
            raise RuntimeError("Document record was not created")
        job = client.table("document_processing_jobs").insert({"document_id": document_id, "status": "processing", "processor": "construction-text-v1", "progress": 10}).execute()
        if not job.data:
            raise RuntimeError("Processing job was not created")
        job_id = job.data[0]["id"]
        knowledge = client.table("ai_knowledge_documents").insert({"document_id": document_id, "project_id": project_id, "processing_job_id": job_id, "status": "pending"}).execute()
        if not knowledge.data:
            raise RuntimeError("Knowledge document was not created")
        knowledge_id = knowledge.data[0]["id"]
        text, page_count = extract_text(safe_name, file.content_type or "", data)
        chunks = chunk_text(text)
        client.table("ai_knowledge_documents").update({"extracted_text": text, "page_count": page_count, "status": "ready"}).eq("id", knowledge_id).execute()
        if chunks:
            rows = [{"knowledge_document_id": knowledge_id, "document_id": document_id, "chunk_index": index, "content": chunk, "page_number": None, "metadata": {"source": safe_name, "processor": "construction-text-v1"}} for index, chunk in enumerate(chunks)]
            client.table("ai_knowledge_chunks").insert(rows).execute()
        now = datetime.now(timezone.utc).isoformat()
        client.table("document_processing_jobs").update({"status": "completed", "progress": 100, "completed_at": now}).eq("id", job_id).execute()
        client.table("documents").update({"status": "processed"}).eq("id", document_id).execute()
        return {"document_id": document_id, "job_id": job_id, "knowledge_document_id": knowledge_id, "status": "completed", "chunks": len(chunks)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {exc}") from exc

@router.get("/documents/{document_id}/status")
def document_status(document_id: str, token: str = Depends(get_access_token)):
    get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    result = client.table("document_processing_jobs").select("id,document_id,status,processor,progress,error_message,started_at,completed_at,created_at").eq("document_id", document_id).order("created_at", desc=True).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return result.data[0]
