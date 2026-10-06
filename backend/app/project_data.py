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
        "risks": {
            "count": len(risks),
            "level_counts": risk_counts,
            "status_counts": _count_values(risks, "status"),
            "items": [
                {
                    "risk_code": row.get("risk_code"),
                    "title": row.get("title"),
                    "level": row.get("level"),
                    "status": row.get("status"),
                }
                for row in risks
            ][:20],
        },
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


def build_document_intelligence(
    documents: list[dict[str, Any]],
    knowledge_documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    extractions: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize document processing and extraction readiness without changing records."""
    from collections import Counter

    knowledge_by_document = {str(row.get("document_id")): row for row in knowledge_documents}
    chunk_counts = Counter(str(row.get("document_id")) for row in chunks)
    extraction_counts = Counter(str(row.get("document_id")) for row in extractions)
    latest_jobs: dict[str, dict[str, Any]] = {}
    for row in jobs:
        document_id = str(row.get("document_id"))
        if document_id not in latest_jobs or str(row.get("created_at") or "") >= str(latest_jobs[document_id].get("created_at") or ""):
            latest_jobs[document_id] = row

    document_health = []
    priorities = []
    for document in documents:
        document_id = str(document.get("id"))
        knowledge = knowledge_by_document.get(document_id, {})
        job = latest_jobs.get(document_id, {})
        extracted_text = str(knowledge.get("extracted_text") or "")
        document_status = str(document.get("status") or "unknown").lower()
        knowledge_status = str(knowledge.get("status") or "missing").lower()
        job_status = str(job.get("status") or "missing").lower()
        issues: list[str] = []

        if document_status in {"failed", "error"} or knowledge_status in {"failed", "error"} or job_status in {"failed", "error"}:
            issues.append("processing_failed")
        if not knowledge:
            issues.append("missing_knowledge_record")
        if knowledge and not extracted_text.strip():
            issues.append("no_extracted_text")
        if extracted_text.strip() and chunk_counts.get(document_id, 0) == 0:
            issues.append("no_search_chunks")
        if extracted_text.strip() and extraction_counts.get(document_id, 0) == 0:
            issues.append("no_ai_extraction")
        if job_status in {"queued", "running", "processing"}:
            issues.append("processing_in_progress")

        document_health.append({
            "document": document.get("name") or "Uploaded document",
            "status": document_status,
            "knowledge_status": knowledge_status,
            "job_status": job_status,
            "page_count": knowledge.get("page_count"),
            "extracted_characters": len(extracted_text),
            "chunk_count": chunk_counts.get(document_id, 0),
            "extraction_count": extraction_counts.get(document_id, 0),
            "issues": issues,
        })

        if issues:
            priorities.append({
                "priority": "high" if "processing_failed" in issues else "medium",
                "document": document.get("name") or "Uploaded document",
                "action": "Review document processing and extraction before relying on this file for project decisions.",
                "issues": issues,
            })

    if not documents:
        priorities.append({
            "priority": "high",
            "action": "Upload the approved project drawings, specifications, contracts, BOQ, and key reports.",
            "reason": "No project documents are available to ground document-based AI answers.",
        })
    elif not priorities:
        priorities.append({
            "priority": "low",
            "action": "Keep project documents current and reconcile important extracted data against approved originals.",
            "reason": "No immediate document-processing gap was detected.",
        })

    rank = {"high": 0, "medium": 1, "low": 2}
    priorities.sort(key=lambda item: rank.get(item.get("priority"), 3))
    return {
        "status": "no_documents" if not documents else "needs_review" if any(row["issues"] for row in document_health) else "ready",
        "document_count": len(documents),
        "status_counts": dict(Counter(str(row.get("status") or "unknown").lower() for row in documents)),
        "documents": document_health,
        "priority_count": len(priorities),
        "priorities": priorities[:10],
        "note": "Document health describes processing and extraction readiness; it does not certify that a document is approved, complete, current, or technically correct.",
    }


def make_project_document_intelligence_tool(client: Client, project_id: str):
    def get_project_document_intelligence() -> dict[str, Any]:
        """Assess uploaded project documents for extraction and AI-search readiness."""
        documents = (
            client.table("documents")
            .select("id,name,status,mime_type,file_size_bytes,created_at")
            .eq("project_id", project_id)
            .limit(200)
            .execute()
        ).data or []
        if not documents:
            return build_document_intelligence([], [], [], [], [])

        ids = [row["id"] for row in documents]
        knowledge = (
            client.table("ai_knowledge_documents")
            .select("document_id,extracted_text,page_count,language,status,created_at,updated_at")
            .eq("project_id", project_id)
            .in_("document_id", ids)
            .limit(500)
            .execute()
        ).data or []
        chunks = (
            client.table("ai_knowledge_chunks")
            .select("document_id")
            .in_("document_id", ids)
            .limit(10000)
            .execute()
        ).data or []
        extractions = (
            client.table("ai_extractions")
            .select("document_id,extraction_type,created_at")
            .in_("document_id", ids)
            .limit(2000)
            .execute()
        ).data or []
        jobs = (
            client.table("document_processing_jobs")
            .select("document_id,status,processor,progress,error_message,started_at,completed_at,created_at")
            .in_("document_id", ids)
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        ).data or []
        return build_document_intelligence(documents, knowledge, chunks, extractions, jobs)

    return get_project_document_intelligence

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



def build_project_action_plan(summary: dict[str, Any]) -> dict[str, Any]:
    """Convert current project priorities into a conservative, ordered action plan."""
    priority_result = build_project_priorities(summary)
    actions: list[dict[str, Any]] = []
    templates = {
        "Progress tracking": {
            "owner": "Project manager / planning engineer",
            "step": "Create the activity register, define planned quantities and dates, then record actual progress regularly.",
            "evidence": "Approved activity list and updated progress records.",
        },
        "Schedule": {
            "owner": "Project manager / planning engineer",
            "step": "Identify activities behind plan, determine causes, and agree recovery measures with the responsible team.",
            "evidence": "Updated schedule and documented recovery actions.",
        },
        "Materials": {
            "owner": "Procurement / store officer",
            "step": "Review low-stock materials, confirm required quantities and lead times, then initiate replenishment where justified.",
            "evidence": "Updated material register and procurement/replenishment records.",
        },
        "Risk management": {
            "owner": "Project manager / risk owner",
            "step": "Create or review the risk register, assign owners, assess priority, and record mitigation actions.",
            "evidence": "Current risk register with owners and mitigation actions.",
        },
        "Cost control": {
            "owner": "Quantity surveyor / cost controller",
            "step": "Start recording project costs and link each entry to the relevant activity, category, date, and currency.",
            "evidence": "Updated cost ledger and supporting records.",
        },
        "Equipment": {
            "owner": "Plant / equipment officer",
            "step": "Register equipment and record availability, operational status, and maintenance requirements.",
            "evidence": "Current equipment register and maintenance status.",
        },
        "Routine control": {
            "owner": "Project management team",
            "step": "Continue routine updates and review progress, costs, materials, equipment, and risks at the agreed reporting interval.",
            "evidence": "Current project dashboard and periodic management report.",
        },
    }
    for index, priority in enumerate(priority_result["priorities"], start=1):
        template = templates.get(priority["area"], templates["Routine control"])
        actions.append({
            "sequence": index,
            "priority": priority["priority"],
            "area": priority["area"],
            "owner": template["owner"],
            "action": template["step"],
            "reason": priority["reason"],
            "evidence": template["evidence"],
        })
    return {
        "project": summary.get("project", {}),
        "action_count": len(actions),
        "actions": actions,
        "note": "This plan recommends actions but does not change project records automatically.",
    }


def make_project_action_plan_tool(client: Client, project_id: str):
    get_summary = make_project_summary_tool(client, project_id)

    def get_project_action_plan() -> dict[str, Any]:
        """Create an ordered management action plan from current project data."""
        return build_project_action_plan(get_summary())

    return get_project_action_plan


def build_project_monitoring(summary: dict[str, Any]) -> dict[str, Any]:
    """Classify current project health and recommend read-only management decisions."""
    activities = summary.get("activities", {})
    materials = summary.get("materials", {})
    equipment = summary.get("equipment", {})
    costs = summary.get("costs", {})
    risks = summary.get("risks", {})

    planned = float(activities.get("average_planned_percent", 0) or 0)
    actual = float(activities.get("average_actual_percent", 0) or 0)
    schedule_variance = round(actual - planned, 2) if activities.get("count", 0) else None

    critical: list[dict[str, Any]] = []
    attention: list[dict[str, Any]] = []
    on_track: list[dict[str, Any]] = []

    high_risks = int(risks.get("level_counts", {}).get("high", 0) or 0)
    shortages = int(materials.get("at_or_below_reorder_level", 0) or 0)

    if high_risks:
        critical.append({
            "area": "Risk management",
            "finding": f"{high_risks} high-level risk(s) are logged.",
            "decision": "Review ownership and mitigation actions for high-level risks.",
        })
    if shortages:
        critical.append({
            "area": "Materials",
            "finding": f"{shortages} material item(s) are at or below reorder level.",
            "decision": "Confirm requirements and replenishment lead times before work is affected.",
        })
    if activities.get("count", 0) == 0:
        attention.append({
            "area": "Progress tracking",
            "finding": "No activities are tracked, so schedule performance cannot be measured.",
            "decision": "Establish the approved activity register and begin planned/actual progress reporting.",
        })
    elif schedule_variance is not None and schedule_variance < 0:
        attention.append({
            "area": "Schedule",
            "finding": f"Average actual progress is {abs(schedule_variance):.2f} percentage points below plan.",
            "decision": "Identify the causes of delay and agree recovery measures with responsible owners.",
        })
    elif schedule_variance is not None:
        on_track.append({
            "area": "Schedule",
            "finding": f"Average actual progress is {schedule_variance:.2f} percentage points at or above plan.",
        })

    if materials.get("count", 0) == 0:
        attention.append({
            "area": "Materials",
            "finding": "No materials are tracked.",
            "decision": "Establish the material register and reorder levels.",
        })
    if risks.get("count", 0) == 0:
        attention.append({
            "area": "Risk management",
            "finding": "No project risks are logged.",
            "decision": "Create and review a project risk register.",
        })
    if costs.get("entry_count", 0) == 0:
        attention.append({
            "area": "Cost control",
            "finding": "No cost entries are recorded.",
            "decision": "Start a project cost ledger before cost performance can be assessed.",
        })
    if equipment.get("count", 0) == 0:
        attention.append({
            "area": "Equipment",
            "finding": "No equipment is tracked.",
            "decision": "Register equipment and record availability and maintenance status.",
        })

    if not critical and not attention:
        on_track.append({
            "area": "Overall control",
            "finding": "No critical issue or immediate control gap was identified from the available project data.",
        })

    overall = "critical" if critical else "attention" if attention else "on_track"
    return {
        "project": summary.get("project", {}),
        "overall_status": overall,
        "schedule": {
            "planned_percent": planned,
            "actual_percent": actual,
            "variance_percentage_points": schedule_variance,
            "trend": "not_available" if activities.get("count", 0) == 0 else "below_plan" if schedule_variance < 0 else "at_or_above_plan",
        },
        "critical": critical,
        "attention": attention,
        "on_track": on_track,
        "management_decisions": [
            item["decision"]
            for item in [*critical, *attention]
            if item.get("decision")
        ],
        "note": "Monitoring is based only on currently recorded project data and does not modify project records.",
    }


def build_project_risk_analysis(summary: dict[str, Any]) -> dict[str, Any]:
    """Analyze recorded risks and identify conservative risk-control gaps."""
    risks = summary.get("risks", {})
    recorded = risks.get("items", [])
    level_counts = risks.get("level_counts", {})
    status_counts = risks.get("status_counts", {})

    high = int(level_counts.get("high", 0) or 0)
    medium = int(level_counts.get("medium", 0) or 0)
    low = int(level_counts.get("low", 0) or 0)

    recommendations: list[dict[str, Any]] = []
    if not recorded:
        recommendations.append({
            "priority": "high",
            "area": "Risk register",
            "finding": "No project risks are currently recorded.",
            "action": "Create an initial risk register covering schedule, procurement/materials, cost, quality, safety, equipment, and contractual interfaces as applicable.",
        })
    if high:
        recommendations.append({
            "priority": "high",
            "area": "High-level risks",
            "finding": f"{high} high-level risk(s) are recorded.",
            "action": "Review each high-level risk, confirm an owner, current status, mitigation measure, and target review date.",
        })
    elif medium:
        recommendations.append({
            "priority": "medium",
            "area": "Medium-level risks",
            "finding": f"{medium} medium-level risk(s) are recorded.",
            "action": "Confirm ownership and active mitigation measures for medium-level risks.",
        })

    if risks.get("count", 0) and not status_counts:
        recommendations.append({
            "priority": "medium",
            "area": "Risk status",
            "finding": "Risk status information is incomplete in the available summary.",
            "action": "Review risk status fields before using the register for formal management reporting.",
        })

    return {
        "project": summary.get("project", {}),
        "recorded_risk_count": risks.get("count", 0),
        "recorded_risks": recorded[:20],
        "level_counts": {"high": high, "medium": medium, "low": low},
        "status_counts": status_counts,
        "recommendations": recommendations,
        "note": "This analysis reports recorded risk data and control recommendations only. It does not create, edit, or close risks automatically.",
    }

def make_project_risk_analysis_tool(client: Client, project_id: str):
    get_summary = make_project_summary_tool(client, project_id)

    def get_project_risk_analysis() -> dict[str, Any]:
        """Analyze recorded project risks and recommend conservative risk-control actions."""
        return build_project_risk_analysis(get_summary())

    return get_project_risk_analysis


def make_project_monitoring_tool(client: Client, project_id: str):
    get_summary = make_project_summary_tool(client, project_id)

    def get_project_monitoring() -> dict[str, Any]:
        """Monitor current project health and return read-only management decision support."""
        return build_project_monitoring(get_summary())

    return get_project_monitoring


def build_project_forecast(summary: dict[str, Any]) -> dict[str, Any]:
    """Assess forecast readiness and provide conservative forward-looking guidance."""
    activities = summary.get("activities", {})
    materials = summary.get("materials", {})
    equipment = summary.get("equipment", {})
    costs = summary.get("costs", {})
    risks = summary.get("risks", {})

    blockers: list[str] = []
    available_signals: list[str] = []

    if activities.get("count", 0) == 0:
        blockers.append("No activity or planned/actual progress records are available.")
    else:
        available_signals.append(
            "Activity planned and actual progress percentages are available."
        )

    if costs.get("entry_count", 0) == 0:
        blockers.append("No project cost entries are available.")
    else:
        available_signals.append("Recorded project cost entries are available.")

    if materials.get("count", 0) == 0:
        blockers.append("No material stock and reorder-level records are available.")
    else:
        available_signals.append("Material stock and reorder-level records are available.")

    if risks.get("count", 0) == 0:
        blockers.append("No project risk records are available.")
    else:
        available_signals.append("Recorded project risk information is available.")

    if equipment.get("count", 0) == 0:
        blockers.append("No equipment status records are available.")
    else:
        available_signals.append("Equipment status records are available.")

    if blockers:
        readiness = "insufficient_data"
        confidence = "low"
        forecast = (
            "A reliable quantitative forecast cannot be produced from the current "
            "project data. The system should establish baseline controls before "
            "forecasting schedule, cost, material, or equipment performance."
        )
    else:
        readiness = "forecast_ready"
        confidence = "moderate"
        forecast = (
            "The project has the core control registers needed for a forward-looking "
            "assessment. Forecast outputs should be based on recorded trends and "
            "reviewed against the approved baseline."
        )

    return {
        "project": summary.get("project", {}),
        "readiness": readiness,
        "confidence": confidence,
        "forecast": forecast,
        "available_signals": available_signals,
        "blockers": blockers,
        "required_inputs": [
            "Approved baseline schedule with planned dates and activity progress.",
            "Regular actual progress updates against the baseline.",
            "Project budget or approved cost baseline plus recorded actual costs.",
            "Material consumption, stock, reorder levels, and procurement lead times.",
            "Current risk register with owners, status, and mitigation actions.",
            "Equipment availability and maintenance status where equipment affects delivery.",
        ],
        "conditional_guidance": [
            "Once progress history exists, compare actual versus planned trends before projecting completion.",
            "Once cost history and a baseline exist, assess cost movement against approved budget.",
            "Use material stock and procurement lead-time history to identify potential supply interruptions.",
            "Use the risk register to distinguish recorded risks from conditional future scenarios.",
        ],
        "note": (
            "This forecast is read-only. It does not create or modify project records, "
            "and it does not treat hypothetical future events as recorded project facts."
        ),
    }


def make_project_forecast_tool(client: Client, project_id: str):
    get_summary = make_project_summary_tool(client, project_id)

    def get_project_forecast() -> dict[str, Any]:
        """Assess project forecast readiness and provide conservative forward-looking guidance."""
        return build_project_forecast(get_summary())

    return get_project_forecast


def build_project_early_warnings(summary: dict[str, Any]) -> dict[str, Any]:
    """Identify conservative early-warning signals from currently recorded project data."""
    activities = summary.get("activities", {})
    materials = summary.get("materials", {})
    equipment = summary.get("equipment", {})
    costs = summary.get("costs", {})
    risks = summary.get("risks", {})

    warnings: list[dict[str, Any]] = []

    if activities.get("count", 0) == 0:
        warnings.append({
            "severity": "high",
            "area": "Schedule visibility",
            "signal": "No activity or planned/actual progress records are available.",
            "early_warning": "Schedule slippage could go undetected because there is no baseline progress signal.",
            "recommended_action": "Establish the approved activity register and begin regular planned-versus-actual updates.",
        })
    else:
        planned = float(activities.get("average_planned_percent", 0) or 0)
        actual = float(activities.get("average_actual_percent", 0) or 0)
        variance = round(actual - planned, 2)
        if variance < 0:
            warnings.append({
                "severity": "high" if variance <= -10 else "medium",
                "area": "Schedule",
                "signal": f"Average actual progress is {abs(variance):.2f} percentage points below plan.",
                "early_warning": "If the negative variance persists, planned completion may be affected.",
                "recommended_action": "Identify the activities driving the variance and agree documented recovery measures.",
            })

    shortages = materials.get("shortages", [])
    if shortages:
        warnings.append({
            "severity": "high",
            "area": "Materials",
            "signal": f"{len(shortages)} material item(s) are at or below reorder level.",
            "early_warning": "Continued consumption without replenishment could interrupt planned work.",
            "recommended_action": "Confirm quantities, supplier lead times, and replenishment actions for the affected items.",
        })
    elif materials.get("count", 0) == 0:
        warnings.append({
            "severity": "medium",
            "area": "Materials visibility",
            "signal": "No material records are available.",
            "early_warning": "Material shortages may remain undetected without stock and reorder-level tracking.",
            "recommended_action": "Establish material stock, consumption, reorder-level, and procurement tracking.",
        })

    high_risks = int(risks.get("level_counts", {}).get("high", 0) or 0)
    if high_risks:
        warnings.append({
            "severity": "high",
            "area": "Risk",
            "signal": f"{high_risks} high-level risk(s) are recorded.",
            "early_warning": "Uncontrolled high-level risks may affect project delivery.",
            "recommended_action": "Confirm risk owners, mitigation measures, current status, and review dates.",
        })
    elif risks.get("count", 0) == 0:
        warnings.append({
            "severity": "medium",
            "area": "Risk visibility",
            "signal": "No project risks are recorded.",
            "early_warning": "Emerging threats may not be visible to management without a risk register.",
            "recommended_action": "Create and routinely review a project risk register.",
        })

    if costs.get("entry_count", 0) == 0:
        warnings.append({
            "severity": "medium",
            "area": "Cost visibility",
            "signal": "No project cost entries are recorded.",
            "early_warning": "Cost overruns cannot be detected from the system until a cost baseline and actual entries exist.",
            "recommended_action": "Establish an approved cost baseline and start recording actual project costs.",
        })

    if equipment.get("count", 0) == 0:
        warnings.append({
            "severity": "low",
            "area": "Equipment visibility",
            "signal": "No equipment records are available.",
            "early_warning": "Equipment availability or maintenance constraints may not be visible.",
            "recommended_action": "Register critical equipment and maintain availability and maintenance status.",
        })

    rank = {"high": 0, "medium": 1, "low": 2}
    warnings.sort(key=lambda item: rank.get(item["severity"], 3))

    return {
        "project": summary.get("project", {}),
        "warning_count": len(warnings),
        "warnings": warnings[:15],
        "severity_counts": {
            level: sum(1 for item in warnings if item["severity"] == level)
            for level in ("high", "medium", "low")
        },
        "note": (
            "Early warnings are signals derived only from currently recorded data. "
            "They are not predictions of events that have already occurred and do not modify project records."
        ),
    }


def build_project_performance_score(summary: dict[str, Any]) -> dict[str, Any]:
    """Calculate a transparent, read-only project performance score from recorded controls."""
    activities = summary.get("activities", {})
    materials = summary.get("materials", {})
    equipment = summary.get("equipment", {})
    costs = summary.get("costs", {})
    risks = summary.get("risks", {})

    components: list[dict[str, Any]] = []
    data_gaps: list[str] = []

    if activities.get("count", 0):
        planned = float(activities.get("average_planned_percent", 0) or 0)
        actual = float(activities.get("average_actual_percent", 0) or 0)
        schedule_score = max(0.0, min(100.0, 100.0 + (actual - planned)))
        components.append({"area": "Schedule", "score": round(schedule_score, 1), "weight": 25, "basis": f"Average actual progress is {actual:.2f}% versus {planned:.2f}% planned."})
    else:
        data_gaps.append("No activity or planned/actual progress records are available.")
        components.append({"area": "Schedule", "score": None, "weight": 25, "basis": "Insufficient schedule data."})

    if costs.get("entry_count", 0):
        components.append({"area": "Cost", "score": 100.0, "weight": 15, "basis": "Cost entries are recorded, but no approved cost baseline is available for variance scoring."})
        data_gaps.append("No approved cost baseline is available, so cost performance is not quantitatively scored.")
    else:
        components.append({"area": "Cost", "score": None, "weight": 15, "basis": "No cost entries are recorded."})
        data_gaps.append("No project cost entries are available.")

    if materials.get("count", 0):
        shortages = int(materials.get("at_or_below_reorder_level", 0) or 0)
        count = int(materials.get("count", 0) or 0)
        material_score = 100.0 if shortages == 0 else max(0.0, 100.0 * (1 - shortages / count))
        components.append({"area": "Materials", "score": round(material_score, 1), "weight": 15, "basis": f"{shortages} of {count} tracked material item(s) are at or below reorder level."})
    else:
        components.append({"area": "Materials", "score": None, "weight": 15, "basis": "No material records are available."})
        data_gaps.append("No material stock and reorder-level records are available.")

    if equipment.get("count", 0):
        components.append({"area": "Equipment", "score": 100.0, "weight": 10, "basis": "Equipment records are present, but utilization/availability history is not available for a more precise score."})
        data_gaps.append("Equipment availability history is not available for quantitative performance scoring.")
    else:
        components.append({"area": "Equipment", "score": None, "weight": 10, "basis": "No equipment records are available."})
        data_gaps.append("No equipment status records are available.")

    high_risks = int(risks.get("level_counts", {}).get("high", 0) or 0)
    medium_risks = int(risks.get("level_counts", {}).get("medium", 0) or 0)
    if risks.get("count", 0):
        risk_score = max(0.0, 100.0 - high_risks * 25.0 - medium_risks * 10.0)
        components.append({"area": "Risk", "score": round(risk_score, 1), "weight": 15, "basis": f"{high_risks} high and {medium_risks} medium risk(s) are recorded."})
    else:
        components.append({"area": "Risk", "score": None, "weight": 15, "basis": "No project risks are recorded."})
        data_gaps.append("No project risk records are available.")

    available_weight = sum(item["weight"] for item in components if item["score"] is not None)
    weighted_total = sum(item["score"] * item["weight"] for item in components if item["score"] is not None)
    score = round(weighted_total / available_weight, 1) if available_weight else None

    if score is None:
        status = "insufficient_data"
    elif len(data_gaps) >= 4 or available_weight < 50:
        status = "low_confidence"
    elif score < 50:
        status = "critical"
    elif score < 70:
        status = "at_risk"
    elif score < 85:
        status = "stable"
    else:
        status = "healthy"

    return {
        "project": summary.get("project", {}),
        "score": score,
        "status": status,
        "confidence": "low" if len(data_gaps) >= 4 else "moderate" if data_gaps else "high",
        "components": components,
        "scoring_method": "Weighted score from recorded schedule, cost, materials, equipment, and risk signals. Missing components are excluded rather than treated as zero.",
        "data_gaps": data_gaps,
        "note": "This score is read-only and indicative. It does not replace approved baselines, engineering judgment, project controls, or formal management reporting.",
    }

def make_project_performance_score_tool(client: Client, project_id: str):
    get_summary = make_project_summary_tool(client, project_id)

    def get_project_performance_score() -> dict[str, Any]:
        """Calculate a transparent, read-only project performance score."""
        return build_project_performance_score(get_summary())

    return get_project_performance_score

def build_project_management_recommendations(summary: dict[str, Any]) -> dict[str, Any]:
    """Synthesize current project signals into prioritized, read-only management recommendations."""
    monitoring = build_project_monitoring(summary)
    risk_analysis = build_project_risk_analysis(summary)
    forecast = build_project_forecast(summary)
    early_warnings = build_project_early_warnings(summary)
    priorities = build_project_priorities(summary)

    recommendations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(priority: str, area: str, recommendation: str, reason: str, source: str) -> None:
        key = (area, recommendation)
        if key in seen:
            return
        seen.add(key)
        recommendations.append({
            "priority": priority,
            "area": area,
            "recommendation": recommendation,
            "reason": reason,
            "source": source,
        })

    for item in monitoring.get("critical", []):
        add("critical", item["area"], item["decision"], item["finding"], "project monitoring")
    for item in early_warnings.get("warnings", []):
        severity = item.get("severity", "medium")
        priority = "critical" if severity == "high" and item.get("area") in {"Schedule", "Materials", "Risk"} else severity
        add(priority, item["area"], item["recommended_action"], item["early_warning"], "early warning system")
    for item in risk_analysis.get("recommendations", []):
        add(item["priority"], item["area"], item["action"], item["finding"], "risk analysis")
    for item in priorities.get("priorities", []):
        add(item["priority"], item["area"], item["action"], item["reason"], "project priorities")

    if forecast.get("readiness") == "insufficient_data":
        add("high", "Forecast readiness", "Establish the missing baseline controls before relying on quantitative project forecasts.", "Forecast readiness is low because required project control data is missing.", "project forecasting")

    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda item: rank.get(item["priority"], 4))
    recommendations = recommendations[:12]

    return {
        "project": summary.get("project", {}),
        "recommendation_count": len(recommendations),
        "overall_priority": recommendations[0]["priority"] if recommendations else "low",
        "recommendations": recommendations,
        "decision_basis": {
            "monitoring_status": monitoring.get("overall_status"),
            "forecast_readiness": forecast.get("readiness"),
            "early_warning_count": early_warnings.get("warning_count", 0),
            "risk_count": risk_analysis.get("recorded_risk_count", 0),
        },
        "note": "Recommendations synthesize currently recorded project data and remain read-only. Management should validate recommendations against approved project documents and professional judgment before action.",
    }


def make_project_management_recommendations_tool(client: Client, project_id: str):
    get_summary = make_project_summary_tool(client, project_id)

    def get_project_management_recommendations() -> dict[str, Any]:
        """Synthesize project signals into prioritized management recommendations."""
        return build_project_management_recommendations(get_summary())

    return get_project_management_recommendations


def make_project_early_warnings_tool(client: Client, project_id: str):
    get_summary = make_project_summary_tool(client, project_id)

    def get_project_early_warnings() -> dict[str, Any]:
        """Identify early-warning signals and recommended preventive actions."""
        return build_project_early_warnings(get_summary())

    return get_project_early_warnings
