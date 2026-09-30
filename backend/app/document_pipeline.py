"""Document AI pipeline: extract, embed, design assets, elements, visual analysis.

Runs synchronously when called; intended to be scheduled via BackgroundTasks
so upload returns immediately with a processing job id.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .document_intelligence import analyze_drawing_page, extract_construction_data
from .document_processing import chunk_text_with_metadata, extract_pages
from .embeddings import embed_texts
from .engineering_elements import normalize_engineering_elements, persist_engineering_elements


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
    _set_job(client, job_id, status="processing", progress=10, error_message=None)
    _set_document(client, document_id, status="processing")

    try:
        pages = extract_pages(safe_name, content_type or "", data)
        text_content = "\n\n".join(text for text, _ in pages)
        page_count = len(pages) if any(page_number is not None for _, page_number in pages) else None
        chunks = chunk_text_with_metadata(pages)

        _set_job(client, job_id, progress=40)

        embeddings = embed_texts([chunk["content"] for chunk in chunks]) if chunks else []
        _set_job(client, job_id, progress=60)

        client.table("ai_knowledge_documents").update(
            {"extracted_text": text_content, "page_count": page_count, "status": "ready"}
        ).eq("id", knowledge_id).execute()

        extraction = extract_construction_data(safe_name, text_content)
        client.table("ai_extractions").insert(
            {
                "document_id": document_id,
                "extraction_type": extraction["document_type"],
                "data": extraction,
            }
        ).execute()
        _set_job(client, job_id, progress=75)

        if extraction.get("document_type") == "drawing_specification":
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
                        "scale": engineering.get("scale"),
                        "sheet_size": engineering.get("sheet_size"),
                        "levels": engineering.get("levels", []),
                        "dimensions": engineering.get("dimensions", []),
                        "materials": engineering.get("materials", []),
                        "standards": engineering.get("standards", []),
                        "elements": engineering.get("elements", []),
                        "technical_notes": engineering.get("technical_notes", []),
                        "design_parameters": engineering.get("design_parameters", {}),
                        "coordination_items": engineering.get("coordination_items", []),
                        "review_findings": engineering.get("review_findings", []),
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
                        "model": "gpt-4.1-mini",
                        "confidence": extraction.get("confidence", 0),
                        "reviewed_at": _now(),
                    }
                ).execute()

                if safe_name.lower().endswith(".pdf"):
                    try:
                        import fitz

                        pdf = fitz.open(stream=data, filetype="pdf")
                        for page_index in range(min(3, pdf.page_count)):
                            page = pdf.load_page(page_index)
                            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                            visual = analyze_drawing_page(
                                pix.tobytes("png"), engineering.get("discipline") or "general"
                            )
                            visual_result = client.table("design_visual_analyses").insert(
                                {
                                    "project_id": project_id,
                                    "design_asset_id": asset_id,
                                    "document_id": document_id,
                                    "page_number": page_index + 1,
                                    "analysis_status": "completed",
                                    "elements": visual.get("elements", []),
                                    "dimensions": visual.get("dimensions", []),
                                    "symbols": visual.get("symbols", []),
                                    "findings": visual.get("findings", []),
                                    "model": "gpt-5.6-luna",
                                    "confidence": visual.get("confidence", 0),
                                    "error_message": None,
                                }
                            ).execute()
                            visual_analysis_id = (
                                visual_result.data[0]["id"] if visual_result.data else None
                            )
                            visual_elements = normalize_engineering_elements(
                                visual.get("elements", []),
                                project_id=project_id,
                                design_asset_id=asset_id,
                                document_id=document_id,
                                discipline=engineering.get("discipline") or "general",
                                source="ai_visual_analysis",
                                visual_analysis_id=visual_analysis_id,
                                source_page=page_index + 1,
                            )
                            persist_engineering_elements(client, visual_elements)
                    except Exception as visual_exc:
                        client.table("design_visual_analyses").insert(
                            {
                                "project_id": project_id,
                                "design_asset_id": asset_id,
                                "document_id": document_id,
                                "analysis_status": "failed",
                                "error_message": str(visual_exc),
                                "model": "gpt-5.6-luna",
                            }
                        ).execute()

        _set_job(client, job_id, progress=90)

        if chunks:
            # Reprocessing must be idempotent for the vector index. Remove
            # prior chunks for this knowledge document before inserting the
            # newly extracted/embedded chunks.
            client.table("ai_knowledge_chunks").delete().eq(
                "knowledge_document_id", knowledge_id
            ).execute()

            rows = [
                {
                    "knowledge_document_id": knowledge_id,
                    "document_id": document_id,
                    "chunk_index": i,
                    "content": chunk["content"],
                    "page_number": chunk["page_number"],
                    "metadata": {
                        "source": safe_name,
                        "processor": "construction-text-embedding-v1",
                    },
                    "embedding": embeddings[i],
                }
                for i, chunk in enumerate(chunks)
            ]
            client.table("ai_knowledge_chunks").insert(rows).execute()
        else:
            # A valid document with no extracted text should not retain stale
            # vectors from an earlier processing run.
            client.table("ai_knowledge_chunks").delete().eq(
                "knowledge_document_id", knowledge_id
            ).execute()

        _set_job(
            client,
            job_id,
            status="completed",
            progress=100,
            completed_at=_now(),
            error_message=None,
        )
        _set_document(client, document_id, status="processed")

        return {
            "document_id": document_id,
            "job_id": job_id,
            "knowledge_document_id": knowledge_id,
            "status": "completed",
            "chunks": len(chunks),
            "embeddings": len(embeddings),
        }
    except Exception as exc:
        _set_knowledge(client, knowledge_id, status="failed")
        _set_job(
            client,
            job_id,
            status="failed",
            progress=100,
            error_message=str(exc)[:2000],
            completed_at=_now(),
        )
        _set_document(client, document_id, status="failed")
        raise


def run_document_pipeline_safe(client, **kwargs: Any) -> dict[str, Any]:
    """Background entrypoint: never raises to the task runner."""
    try:
        return run_document_pipeline(client, **kwargs)
    except Exception as exc:
        return {
            "document_id": kwargs.get("document_id"),
            "job_id": kwargs.get("job_id"),
            "status": "failed",
            "error": str(exc)[:500],
        }
