"""Project-data tools for the Construction AI Agent.

The public tool factory binds a validated project ID before Gemini can call it.
This prevents the model from choosing an arbitrary project's ID.
"""

from __future__ import annotations

from typing import Any

from supabase import Client

MIN_DOCUMENT_SIMILARITY = 0.35
MAX_DOCUMENT_MATCHES = 6
MAX_EXCERPT_CHARS = 1200


def build_project_summary(
    project: dict[str, Any],
    activities: list[dict[str, Any]],
    materials: list[dict[str, Any]],
    equipment: list[dict[str, Any]],
    costs: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a compact, deterministic summary from project records."""
    planned = [float(row.get("planned_percent") or 0) for row in activities]
    actual = [float(row.get("actual_percent") or 0) for row in activities]

    material_shortages = []
    for row in materials:
        stock = float(row.get("stock_quantity") or 0)
        reorder = float(row.get("reorder_level") or 0)
        if stock <= reorder:
            material_shortages.append(
                {
                    "name": row.get("name"),
                    "code": row.get("code"),
                    "unit": row.get("unit"),
                    "stock_quantity": stock,
                    "reorder_level": reorder,
                    "supplier": row.get("supplier"),
                }
            )

    cost_totals: dict[str, float] = {}
    for row in costs:
        currency = row.get("currency") or "unknown"
        cost_totals[currency] = cost_totals.get(currency, 0.0) + float(
            row.get("amount") or 0
        )

    risk_counts: dict[str, int] = {}
    for row in risks:
        level = row.get("level") or "unknown"
        risk_counts[level] = risk_counts.get(level, 0) + 1

    return {
        "project": {
            "id": project.get("id"),
            "name": project.get("name"),
            "code": project.get("code"),
            "status": project.get("status"),
        },
        "activities": {
            "count": len(activities),
            "average_planned_percent": round(sum(planned) / len(planned), 2)
            if planned
            else 0,
            "average_actual_percent": round(sum(actual) / len(actual), 2)
            if actual
            else 0,
        },
        "materials": {
            "count": len(materials),
            "at_or_below_reorder_level": len(material_shortages),
            "shortages": material_shortages[:20],
        },
        "equipment": {
            "count": len(equipment),
            "status_counts": _count_values(equipment, "status"),
        },
        "costs": {
            "entry_count": len(costs),
            "totals_by_currency": {
                key: round(value, 2) for key, value in cost_totals.items()
            },
        },
        "risks": {
            "count": len(risks),
            "level_counts": risk_counts,
        },
    }


def _count_values(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key) or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts


def make_project_summary_tool(client: Client, project_id: str):
    """Return a Gemini-callable function bound to one authorized project."""

    def get_project_summary() -> dict[str, Any]:
        """Get the current summary of the authorized construction project."""
        project_result = (
            client.table("projects")
            .select("id,name,code,status")
            .eq("id", project_id)
            .single()
            .execute()
        )
        if not project_result.data:
            raise ValueError("Project not found")

        def rows(table: str, columns: str) -> list[dict[str, Any]]:
            result = (
                client.table(table)
                .select(columns)
                .eq("project_id", project_id)
                .limit(1000)
                .execute()
            )
            return result.data or []

        activities = rows(
            "activities", "id,name,status,planned_percent,actual_percent"
        )
        materials = rows(
            "materials",
            "id,code,name,unit,stock_quantity,reorder_level,supplier",
        )
        equipment = rows(
            "equipment", "id,code,name,equipment_type,status"
        )
        costs = rows(
            "cost_entries", "id,category,amount,currency,entry_date"
        )
        risks = rows(
            "project_risks", "id,risk_code,title,level,status"
        )

        return build_project_summary(
            project_result.data,
            activities,
            materials,
            equipment,
            costs,
            risks,
        )

    return get_project_summary


def _project_documents(client: Client, project_id: str) -> list[dict[str, Any]]:
    result = (
        client.table("documents")
        .select("id,name,status")
        .eq("project_id", project_id)
        .limit(30)
        .execute()
    )
    return result.data or []


def _keyword_excerpts(client: Client, project_id: str, question: str) -> dict[str, Any]:
    """Read extracted document text when vector search is unavailable."""
    documents = _project_documents(client, project_id)
    if not documents:
        return {
            "matches": [],
            "note": "No documents are uploaded for this project.",
        }

    titles = {str(row["id"]): row.get("name") or "Uploaded document" for row in documents}
    listed = ", ".join(
        f"{row.get('name') or 'document'} ({row.get('status') or 'unknown'})"
        for row in documents
    )
    knowledge = (
        client.table("ai_knowledge_documents")
        .select("document_id,extracted_text,status")
        .in_("document_id", [row["id"] for row in documents])
        .execute()
    )
    words = [word.lower() for word in question.split() if len(word) > 3][:8]
    excerpts = []
    for row in knowledge.data or []:
        text = (row.get("extracted_text") or "").strip()
        if not text:
            continue
        lowered = text.lower()
        hit = next((word for word in words if word in lowered), None)
        start = max(0, lowered.find(hit) - 180) if hit else 0
        excerpts.append(
            {
                "document": titles.get(str(row.get("document_id")), "Uploaded document"),
                "page": None,
                "excerpt": text[start : start + MAX_EXCERPT_CHARS],
            }
        )
    if excerpts:
        return {
            "matches": excerpts[:MAX_DOCUMENT_MATCHES],
            "note": "Returned from extracted document text because vector search was unavailable.",
        }
    return {
        "matches": [],
        "note": (
            "Uploaded files were found, but no extracted text is available yet. "
            f"Files: {listed}. Wait for processing to finish, or reprocess the document."
        ),
    }


def make_document_search_tool(client: Client, project_id: str):
    """Return a Gemini-callable search over text extracted from uploaded files."""

    def search_uploaded_documents(query: str) -> dict[str, Any]:
        """Search text extracted from documents uploaded to this project.

        Use this for questions about drawings, specifications, contracts, reports,
        bills of quantities, or any other uploaded file. Cite the document name
        and page from the returned excerpts. Do not invent file contents.
        """
        question = (query or "").strip()
        if not question:
            return {"matches": [], "note": "A search query is required."}

        try:
            from .embeddings import embed_texts

            embeddings = embed_texts([question])
            if not embeddings:
                return _keyword_excerpts(client, project_id, question)

            vector = embeddings[0]
            if not isinstance(vector, str):
                vector = "[" + ",".join(str(value) for value in vector) + "]"
            result = client.rpc(
                "match_ai_knowledge_chunks",
                {
                    "query_embedding": vector,
                    "match_project_id": project_id,
                    "match_count": MAX_DOCUMENT_MATCHES,
                },
            ).execute()
            matches = [
                row
                for row in (result.data or [])
                if (row.get("similarity") or 0) >= MIN_DOCUMENT_SIMILARITY
            ]
            if not matches:
                fallback = _keyword_excerpts(client, project_id, question)
                if fallback.get("matches"):
                    return fallback
                return {
                    "matches": [],
                    "note": fallback.get("note")
                    or "No relevant text was found in uploaded documents.",
                }

            document_ids = list(
                {str(row.get("document_id")) for row in matches if row.get("document_id")}
            )
            titles = {
                str(row["id"]): row.get("name") or str(row["id"])
                for row in _project_documents(client, project_id)
                if str(row["id"]) in document_ids
            }
            excerpts = []
            for row in matches:
                document_id = str(row.get("document_id") or "")
                excerpts.append(
                    {
                        "document": titles.get(document_id) or document_id or "Uploaded document",
                        "page": row.get("page_number"),
                        "similarity": row.get("similarity"),
                        "excerpt": (row.get("content") or "").strip()[:MAX_EXCERPT_CHARS],
                    }
                )
            return {"matches": excerpts}
        except Exception as exc:
            try:
                fallback = _keyword_excerpts(client, project_id, question)
            except Exception as fallback_exc:
                return {
                    "matches": [],
                    "note": f"Document search failed: {exc}. Text fallback also failed: {fallback_exc}",
                }
            if fallback.get("matches"):
                return fallback
            note = fallback.get("note") or "No extracted document text was found."
            return {
                "matches": [],
                "note": f"{note} Vector search error: {exc}",
            }

    return search_uploaded_documents
