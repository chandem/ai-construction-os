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


def make_project_monitoring_tool(client: Client, project_id: str):
    get_summary = make_project_summary_tool(client, project_id)

    def get_project_monitoring() -> dict[str, Any]:
        """Monitor current project health and return read-only management decision support."""
        return build_project_monitoring(get_summary())

    return get_project_monitoring
