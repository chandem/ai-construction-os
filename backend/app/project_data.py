"""Project-data tools for the Construction AI Agent."""

from __future__ import annotations

from typing import Any

MAX_DOCUMENT_MATCHES = 6
MAX_EXCERPT_CHARS = 1500


def build_project_summary(
    project: dict[str, Any],
    activities: list[dict[str, Any]],
    materials: list[dict[str, Any]],
    equipment: list[dict[str, Any]],
    costs: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> dict[str, Any]:
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
        cost_totals[currency] = cost_totals.get(currency, 0.0) + float(row.get("amount") or 0)
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
            "average_planned_percent": round(sum(planned) / len(planned), 2) if planned else 0,
            "average_actual_percent": round(sum(actual) / len(actual), 2) if actual else 0,
        },
        "materials": {
            "count": len(materials),
            "at_or_below_reorder_level": len(material_shortages),
            "shortages": material_shortages[:20],
        },
        "equipment": {"count": len(equipment), "status_counts": _count_values(equipment, "status")},
        "costs": {
            "entry_count": len(costs),
            "totals_by_currency": {key: round(value, 2) for key, value in cost_totals.items()},
        },
        "risks": {"count": len(risks), "level_counts": risk_counts},
    }


def build_project_priorities(summary: dict[str, Any]) -> dict[str, Any]:
    """Turn a project summary into conservative, actionable management priorities."""
    priorities: list[dict[str, Any]] = []
    activities = summary.get("activities", {})
    materials = summary.get("materials", {})
    equipment = summary.get("equipment", {})
    costs = summary.get("costs", {})
    risks = summary.get("risks", {})

    if activities.get("count", 0) == 0:
        priorities.append({
            "priority": "high",
            "area": "Progress tracking",
            "action": "Create the project's activities and start recording planned and actual progress.",
            "reason": "No activities are currently tracked, so schedule performance cannot be measured.",
        })
    elif activities.get("average_actual_percent", 0) < activities.get("average_planned_percent", 0):
        priorities.append({
            "priority": "high",
            "area": "Schedule",
            "action": "Review activities behind plan and identify recovery actions.",
            "reason": "Average actual progress is below average planned progress.",
        })

    shortages = materials.get("shortages", [])
    if shortages:
        priorities.append({
            "priority": "high",
            "area": "Materials",
            "action": "Review and replenish materials at or below reorder level.",
            "reason": "One or more tracked materials are at or below their reorder level.",
            "items": shortages[:10],
        })
    elif materials.get("count", 0) == 0:
        priorities.append({
            "priority": "medium",
            "area": "Materials",
            "action": "Set up the material register with quantities and reorder levels.",
            "reason": "No materials are currently tracked.",
        })

    if risks.get("count", 0) == 0:
        priorities.append({
            "priority": "medium",
            "area": "Risk management",
            "action": "Create an initial project risk register and review it regularly.",
            "reason": "No project risks are currently logged.",
        })
    elif risks.get("level_counts", {}).get("high", 0):
        priorities.append({
            "priority": "high",
            "area": "Risk management",
            "action": "Review and assign mitigation actions for high-level risks.",
            "reason": "High-level risks are present in the project register.",
        })

    if costs.get("entry_count", 0) == 0:
        priorities.append({
            "priority": "medium",
            "area": "Cost control",
            "action": "Start recording project cost entries and link them to the relevant work.",
            "reason": "No cost entries are currently recorded, so cost performance cannot be assessed.",
        })

    if equipment.get("count", 0) == 0:
        priorities.append({
            "priority": "medium",
            "area": "Equipment",
            "action": "Register project equipment and track availability and maintenance status.",
            "reason": "No equipment is currently tracked.",
        })

    if not priorities:
        priorities.append({
            "priority": "low",
            "area": "Routine control",
            "action": "Continue updating progress, costs, materials, equipment, and risks.",
            "reason": "No immediate data-quality or control gap was identified from the current summary.",
        })

    rank = {"high": 0, "medium": 1, "low": 2}
    priorities.sort(key=lambda item: rank.get(item["priority"], 3))
    return {
        "project": summary.get("project", {}),
        "priority_count": len(priorities),
        "priorities": priorities[:10],
    }


def _count_values(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key) or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts


def make_project_summary_tool(client: Client, project_id: str):
    def get_project_summary() -> dict[str, Any]:
        """Get the current summary of the authorized construction project."""
        project_result = (
            client.table("projects").select("id,name,code,status").eq("id", project_id).single().execute()
        )
        if not project_result.data:
            raise ValueError("Project not found")

        def rows(table: str, columns: str) -> list[dict[str, Any]]:
            result = client.table(table).select(columns).eq("project_id", project_id).limit(1000).execute()
            return result.data or []

        return build_project_summary(
            project_result.data,
            rows("activities", "id,name,status,planned_percent,actual_percent"),
            rows("materials", "id,code,name,unit,stock_quantity,reorder_level,supplier"),
            rows("equipment", "id,code,name,equipment_type,status"),
            rows("cost_entries", "id,category,amount,currency,entry_date"),
            rows("project_risks", "id,risk_code,title,level,status"),
        )

    return get_project_summary


def make_project_priorities_tool(client: Client, project_id: str):
    get_summary = make_project_summary_tool(client, project_id)

    def get_project_priorities() -> dict[str, Any]:
        """Analyze the current project data and return prioritized management actions."""
        return build_project_priorities(get_summary())

    return get_project_priorities


def _excerpt(text: str, question: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    words = [word.lower() for word in question.split() if len(word) > 3][:8]
    hit = next((word for word in words if word in lowered), None)
    start = max(0, lowered.find(hit) - 200) if hit else 0
    return cleaned[start : start + MAX_EXCERPT_CHARS]


def make_document_search_tool(client: Client, project_id: str):
    def search_uploaded_documents(query: str) -> dict:
        """Search text extracted from documents uploaded to this project.

        Use this for drawings, specifications, contracts, reports, bills of quantities,
        and maintenance plans. Cite the document name. Do not invent file contents.
        """
        question = (query or "").strip() or "project document"
        try:
            documents = (
                client.table("documents")
                .select("id,name,status")
                .eq("project_id", project_id)
                .limit(30)
                .execute()
            ).data or []
        except Exception as exc:
            return {"matches": [], "note": "Could not list documents: %s" % exc}
        if not documents:
            return {"matches": [], "note": "No documents are uploaded for this project."}

        titles = {str(row.get("id")): row.get("name") or "Uploaded document" for row in documents}
        allowed = set(titles)
        listed = ", ".join(
            "%s (%s)" % (row.get("name") or "document", row.get("status") or "unknown")
            for row in documents
        )
        excerpts = []
        errors = []

        try:
            knowledge = (
                client.table("ai_knowledge_documents")
                .select("document_id,extracted_text,status")
                .eq("project_id", project_id)
                .limit(20)
                .execute()
            ).data or []
            for row in knowledge:
                if str(row.get("document_id")) not in allowed:
                    continue
                excerpt = _excerpt(row.get("extracted_text") or "", question)
                if excerpt:
                    excerpts.append(
                        {
                            "document": titles.get(str(row.get("document_id")), "Uploaded document"),
                            "excerpt": excerpt,
                        }
                    )
        except Exception as exc:
            errors.append("extracted text: %s" % exc)

        if not excerpts:
            try:
                chunks = (
                    client.table("ai_knowledge_chunks")
                    .select("document_id,content,page_number")
                    .limit(40)
                    .execute()
                ).data or []
                for row in chunks:
                    if str(row.get("document_id")) not in allowed:
                        continue
                    excerpt = _excerpt(row.get("content") or "", question)
                    if excerpt:
                        excerpts.append(
                            {
                                "document": titles.get(str(row.get("document_id")), "Uploaded document"),
                                "page": row.get("page_number"),
                                "excerpt": excerpt,
                            }
                        )
            except Exception as exc:
                errors.append("chunks: %s" % exc)

        if excerpts:
            return {"matches": excerpts[:MAX_DOCUMENT_MATCHES], "files": listed}
        note = "Uploaded files: %s. No extracted text is available yet." % listed
        if errors:
            note = "%s Lookup detail: %s" % (note, "; ".join(errors))
        return {"matches": [], "files": listed, "note": note}

    return search_uploaded_documents
