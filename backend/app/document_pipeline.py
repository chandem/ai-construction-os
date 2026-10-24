"""Document AI pipeline: extract, embed, design assets, elements, visual analysis.

Runs synchronously when called; intended to be scheduled via BackgroundTasks
so upload returns immediately with a processing job id.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Any

from .document_intelligence import analyze_drawing_page, extract_construction_data
from .document_processing import chunk_text_with_metadata, extract_pages
from .embeddings import embed_texts
from .engineering_elements import normalize_engineering_elements, persist_engineering_elements
from .boq_from_document import persist_boq_from_document

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_job(client, job_id: str, **fields: Any) -> None:
    if not job_id:
        return
    try:
        client.table("document_processing_jobs").update(fields).eq("id", job_id).execute()
    except Exception:
        pass


def _set_document(client, document_id: str, **fields: Any) -> None:
    try:
        client.table("documents").update(fields).eq("id", document_id).execute()
    except Exception:
        pass


def _set_knowledge(client, knowledge_id: str, **fields: Any) -> None:
    try:
        client.table("ai_knowledge_documents").update(fields).eq("id", knowledge_id).execute()
    except Exception:
        pass


def run_document_pipeline(
    client,
    *,
    project_id: str,
    document_id: str,
    job_id: str,
    knowledge_id: str,
    safe_name: str,
    content_type: str,
    data: bytes,
) -> dict[str, Any]:
    """Execute the full AI processing chain for one document.

    Updates job progress: queued → processing → completed|failed.
    Reprocessing replaces the document's prior vector chunks instead of
    accumulating duplicate/stale chunks.
    """
    stage = "start"
    _set_job(client, job_id, status="processing", progress=10, error_message=None, started_at=_now())
    _set_document(client, document_id, status="processing")

    try:
        stage = "pdf_text_extraction"
        pages = extract_pages(safe_name, content_type or "", data)
        text_content = "\n\n".join(text for text, _ in pages)
        page_count = len(pages) if any(page_number is not None for _, page_number in pages) else None
        chunks = chunk_text_with_metadata(pages)

        _set_job(client, job_id, progress=40)

        stage = "save_extracted_text"
        client.table("ai_knowledge_documents").update(
            {"extracted_text": text_content, "page_count": page_count, "status": "processing"}
        ).eq("id", knowledge_id).execute()

        processing_warnings: list[str] = []
        embeddings: list[list[float]] = []

        client.table("ai_knowledge_chunks").delete().eq(
            "knowledge_document_id", knowledge_id
        ).execute()

        stage = "generate_embeddings"
        try:
            embeddings = embed_texts([chunk["content"] for chunk in chunks]) if chunks else []
        except Exception as exc:
            logger.exception(
                "Document pipeline stage failed: stage=generate_embeddings document_id=%s job_id=%s",
                document_id, job_id,
            )
            processing_warnings.append(f"Semantic embeddings unavailable: {str(exc)[:500]}")
        _set_job(client, job_id, progress=60)

        stage = "gemini_structured_extraction"
        extraction = None
        try:
            extraction = extract_construction_data(safe_name, text_content)
            client.table("ai_extractions").insert(
                {
                    "document_id": document_id,
                    "extraction_type": extraction["document_type"],
                    "data": extraction,
                }
            ).execute()
        except Exception as exc:
            logger.exception(
                "Document pipeline stage failed: stage=gemini_structured_extraction document_id=%s job_id=%s",
                document_id, job_id,
            )
            processing_warnings.append(f"AI structured extraction unavailable: {str(exc)[:500]}")
        _set_job(client, job_id, progress=75)

        if extraction:
            stage = "boq_import"
            try:
                boq_count = persist_boq_from_document(
                    client,
                    project_id=project_id,
                    document_id=document_id,
                    extraction=extraction,
                    source_name=safe_name,
                )
                # A successful BOQ import is informational, not an enrichment warning.
                # Only actual failures should mark the document as partially enriched.
            except Exception as exc:
                processing_warnings.append(f"BOQ import from document skipped: {str(exc)[:300]}")

        if extraction and extraction.get("document_type") == "drawing_specification":
            stage = "design_asset_persist"
            engineering = extraction.get("data", {}).get("engineering", {})
            design_asset_result = client.table("design_assets").insert(
                {
                    "project_id": project_id,
                    "document_id": document_id,
                    "name": engineering.get("drawing_title") or safe_name,
                    "discipline": engineering.get("discipline") or "general",
                    "asset_type": "drawing_specification",
                    "revision": engineering.get("revision"),
                    "sheet_number": engineering.get("drawing_number"),
                    "status": "ai_analyzed",
                    "metadata": {
                        "ai_confidence": extraction.get("confidence", 0),
                        "ai_warnings": extraction.get("warnings", []),
                    },
                }
            ).execute()
            if design_asset_result.data:
                asset_id = design_asset_result.data[0]["id"]
                extraction_elements = normalize_engineering_elements(
                    engineering.get("elements", []),
                    project_id=project_id,
                    design_asset_id=asset_id,
                    document_id=document_id,
                    discipline=engineering.get("discipline") or "general",
                    source="ai_document_extraction",
                )
                persist_engineering_elements(client, extraction_elements)
                client.table("design_reviews").insert(
                    {
                        "project_id": project_id,
                        "design_asset_id": asset_id,
                        "review_type": "ai_document_review",
                        "status": "completed",
                        "summary": extraction.get("summary", ""),
                        "findings": engineering.get("review_findings", []),
                        "source_pages": [],
                        "model": "gemini",
                        "confidence": extraction.get("confidence", 0),
                        "reviewed_at": _now(),
                    }
                ).execute()

        stage = "persist_search_chunks"
        if chunks:
            chunk_rows = []
            for i, chunk in enumerate(chunks):
                row = {
                    "knowledge_document_id": knowledge_id,
                    "document_id": document_id,
                    "project_id": project_id,
                    "content": chunk["content"],
                    "chunk_index": i,
                    "page_number": chunk.get("page_number"),
                    "metadata": chunk.get("metadata") or {},
                }
                if embeddings and i < len(embeddings):
                    row["embedding"] = embeddings[i]
                chunk_rows.append(row)

            # Small batches + retries: Render free tier can hit Errno 11 (EAGAIN)
            # under memory/connection pressure when inserting embeddings.
            batch_size = 15
            failed_batches = 0
            for start in range(0, len(chunk_rows), batch_size):
                batch = chunk_rows[start : start + batch_size]
                last_exc: Exception | None = None
                for attempt in range(4):
                    try:
                        client.table("ai_knowledge_chunks").upsert(
                            batch, on_conflict="knowledge_document_id,chunk_index"
                        ).execute()
                        last_exc = None
                        break
                    except Exception as exc:
                        last_exc = exc
                        msg = str(exc).lower()
                        transient = (
                            "resource temporarily unavailable" in msg
                            or "errno 11" in msg
                            or "eagain" in msg
                            or "timeout" in msg
                            or "connection" in msg
                        )
                        if not transient or attempt == 3:
                            break
                        time.sleep(0.4 * (attempt + 1))
                if last_exc is not None:
                    # Retry batch without embeddings (lighter payload)
                    light = [{k: v for k, v in row.items() if k != "embedding"} for row in batch]
                    try:
                        client.table("ai_knowledge_chunks").upsert(
                            light, on_conflict="knowledge_document_id,chunk_index"
                        ).execute()
                        processing_warnings.append(
                            f"Search chunks stored without embeddings for batch {start // batch_size + 1} "
                            f"(resource pressure: {str(last_exc)[:200]})"
                        )
                    except Exception as exc2:
                        # Older production schemas may not yet expose project_id
                        # on ai_knowledge_chunks. The knowledge_document_id and
                        # document_id still preserve the relationship, so retry
                        # without this optional denormalized column only when
                        # PostgREST explicitly reports that column as missing.
                        missing_project_id = (
                            "project_id" in str(exc2).lower()
                            and (
                                "schema cache" in str(exc2).lower()
                                or "does not exist" in str(exc2).lower()
                                or "could not find" in str(exc2).lower()
                            )
                        )
                        if missing_project_id:
                            compatible = [
                                {key: value for key, value in row.items() if key != "project_id"}
                                for row in light
                            ]
                            try:
                                client.table("ai_knowledge_chunks").upsert(
                                    compatible, on_conflict="knowledge_document_id,chunk_index"
                                ).execute()
                                processing_warnings.append(
                                    "Search chunks stored without embeddings or project_id; "
                                    "the database schema needs migration for full project-scoped indexing."
                                )
                                continue
                            except Exception as exc3:
                                exc2 = exc3
                        failed_batches += 1
                        processing_warnings.append(
                            f"Search chunk batch {start // batch_size + 1} skipped: {str(exc2)[:200]}"
                        )
            if failed_batches:
                processing_warnings.append(
                    f"{failed_batches} chunk batch(es) could not be saved; "
                    "document text is still available — use Reprocess later if search is incomplete."
                )

        final_status = "processed"
        error_message = None
        if processing_warnings:
            error_message = "; ".join(processing_warnings)[:1000]

        client.table("ai_knowledge_documents").update(
            {
                "status": "ready" if text_content.strip() else "needs_review",
                "extracted_text": text_content,
                "page_count": page_count,
            }
        ).eq("id", knowledge_id).execute()

        _set_document(client, document_id, status=final_status)
        _set_job(
            client,
            job_id,
            status="completed",
            progress=100,
            error_message=error_message,
        )
        return {
            "status": "completed",
            "document_id": document_id,
            "warnings": processing_warnings,
            "chunk_count": len(chunks),
        }
    except Exception as exc:
        logger.exception(
            "Document pipeline failed: stage=%s document_id=%s job_id=%s filename=%r",
            stage, document_id, job_id, safe_name,
        )
        msg = f"{stage}: {str(exc)}"[:1000]
        _set_job(client, job_id, status="failed", progress=100, error_message=msg)
        _set_document(client, document_id, status="failed")
        try:
            client.table("ai_knowledge_documents").update({"status": "failed"}).eq(
                "id", knowledge_id
            ).execute()
        except Exception:
            pass
        return {"status": "failed", "document_id": document_id, "error": msg}


def run_document_pipeline_safe(client, **kwargs: Any) -> dict[str, Any]:
    """Run the document pipeline while containing unexpected background-job errors.

    The safe entry point is used by background_jobs.py. The main pipeline
    already handles most processing failures; this wrapper also catches errors
    raised before or outside its internal processing block.
    """
    try:
        return run_document_pipeline(client, **kwargs)
    except Exception as exc:
        msg = str(exc)[:1000]
        job_id = str(kwargs.get("job_id") or "")
        document_id = str(kwargs.get("document_id") or "")
        knowledge_id = str(kwargs.get("knowledge_id") or "")
        _set_job(client, job_id, status="failed", progress=100, error_message=msg)
        _set_document(client, document_id, status="failed")
        _set_knowledge(client, knowledge_id, status="failed")
        return {
            "status": "failed",
            "document_id": document_id,
            "error": msg,
        }
