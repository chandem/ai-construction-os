"""AI procurement intelligence tools for the Construction AI Agent."""

from __future__ import annotations

from typing import Any
from datetime import date

from supabase import Client


def build_project_procurement_intelligence(
    project: dict[str, Any],
    procurement_items: list[dict[str, Any]],
    materials: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Analyze recorded procurement controls conservatively and read-only."""
    materials = materials or []
    if not procurement_items:
        return {
            "project": project,
            "status": "insufficient_data",
            "confidence": "low",
            "item_count": 0,
            "findings": [],
            "data_gaps": [
                "No procurement items are recorded for this project.",
                "Procurement requirements, order status, delivery status, and required dates cannot be assessed from the procurement register.",
            ],
            "recommendations": [
                "Create the project procurement register and link items to BOQ items where applicable.",
                "Record required, requested, ordered, and delivered quantities plus required dates and supplier information.",
            ],
            "priority_actions": [],
            "note": "Procurement intelligence is read-only and does not create, modify, approve, or place purchase orders.",
        }

    findings: list[dict[str, Any]] = []
    data_gaps: list[str] = []
    recommendations: list[str] = []
    priority_actions: list[dict[str, Any]] = []

    for item in procurement_items:
        required = float(item.get("required_quantity") or 0)
        requested = float(item.get("requested_quantity") or 0)
        ordered = float(item.get("ordered_quantity") or 0)
        delivered = float(item.get("delivered_quantity") or 0)
        name = item.get("material_name") or item.get("item_code") or "Unnamed procurement item"
        status = str(item.get("status") or "unknown").lower()
        remaining = max(0.0, required - delivered)
        order_gap = max(0.0, required - ordered)

        if required <= 0:
            data_gaps.append(f"{name}: required quantity is not recorded.")
            continue

        if delivered < required:
            severity = "high" if status in {"delayed", "late", "blocked", "cancelled"} else "medium"
            action = (
                "Review supplier/status and expedite procurement."
                if severity == "high"
                else "Confirm ordering and delivery plan for the remaining quantity."
            )
            priority_actions.append({
                "priority": severity,
                "material": name,
                "status": status,
                "required_quantity": required,
                "delivered_quantity": delivered,
                "remaining_quantity": round(remaining, 3),
                "action": action,
            })

        if ordered < required:
            findings.append({
                "area": "Ordering gap",
                "material": name,
                "finding": f"{round(order_gap, 3)} {item.get('unit') or 'unit(s)'} remain between required and ordered quantity.",
                "severity": "high" if status in {"delayed", "late", "blocked"} else "medium",
            })

        if delivered < required:
            findings.append({
                "area": "Delivery gap",
                "material": name,
                "finding": f"{round(remaining, 3)} {item.get('unit') or 'unit(s)'} remain undelivered against the recorded requirement.",
                "severity": "high" if status in {"delayed", "late", "blocked", "cancelled"} else "medium",
            })

        required_date = item.get("required_date")
        if required_date and delivered < required:
            try:
                required_date_value = date.fromisoformat(str(required_date)[:10])
                if required_date_value < date.today():
                    findings.append({
                        "area": "Required date",
                        "material": name,
                        "finding": f"The required date {required_date_value.isoformat()} has passed while the recorded requirement is not fully delivered.",
                        "severity": "high",
                    })
                    priority_actions.append({
                        "priority": "high",
                        "material": name,
                        "status": status,
                        "required_date": required_date_value.isoformat(),
                        "remaining_quantity": round(remaining, 3),
                        "action": "Escalate the delivery risk and confirm a recovery date with the supplier/project team.",
                    })
            except ValueError:
                data_gaps.append(f"{name}: required date is not in a usable date format.")

        if not item.get("supplier"):
            data_gaps.append(f"{name}: supplier is not recorded.")

    if not findings:
        findings.append({
            "area": "Procurement coverage",
            "finding": "Recorded procurement items do not currently show a quantity gap requiring escalation.",
            "severity": "information",
        })

    if not materials:
        data_gaps.append("No material register is available to cross-check procurement against current stock and reorder levels.")
        recommendations.append("Maintain material stock and reorder-level data so procurement priorities can be cross-checked against inventory.")
    else:
        low_stock = [
            row for row in materials
            if float(row.get("stock_quantity") or 0) <= float(row.get("reorder_level") or 0)
        ]
        if low_stock:
            recommendations.append("Cross-check low-stock materials against procurement items and confirm replenishment dates.")

    if any(item.get("priority") == "high" for item in priority_actions):
        recommendations.insert(0, "Prioritize high-risk procurement items and confirm recovery actions with responsible suppliers and project staff.")
    elif priority_actions:
        recommendations.insert(0, "Confirm ordering and delivery dates for procurement items with outstanding quantities.")
    else:
        recommendations.insert(0, "Continue updating procurement quantities, status, suppliers, and required dates as the project progresses.")

    priority_actions.sort(key=lambda item: {"high": 0, "medium": 1, "low": 2}.get(item.get("priority", "low"), 3))

    return {
        "project": project,
        "status": "attention_required" if priority_actions else "no_immediate_gap_detected",
        "confidence": "moderate" if not data_gaps else "low" if len(data_gaps) >= 3 else "moderate",
        "item_count": len(procurement_items),
        "findings": findings[:20],
        "priority_actions": priority_actions[:15],
        "data_gaps": sorted(set(data_gaps))[:20],
        "recommendations": recommendations[:10],
        "note": "Procurement findings are based only on recorded project data. They are advisory and do not create, modify, approve, or place procurement transactions.",
    }


def make_project_procurement_intelligence_tool(client: Client, project_id: str):
    def get_project_procurement_intelligence() -> dict[str, Any]:
        """Analyze recorded procurement items, delivery gaps, and procurement-control gaps."""
        project_result = (
            client.table("projects")
            .select("id,name,code,status")
            .eq("id", project_id)
            .single()
            .execute()
        )
        if not project_result.data:
            raise ValueError("Project not found")

        procurement_result = (
            client.table("procurement_items")
            .select(
                "id,boq_item_id,item_code,material_name,specification,unit,"
                "required_quantity,requested_quantity,ordered_quantity,delivered_quantity,"
                "supplier,status,required_date,notes"
            )
            .eq("project_id", project_id)
            .limit(1000)
            .execute()
        )
        material_result = (
            client.table("materials")
            .select("id,code,name,unit,stock_quantity,reorder_level,supplier")
            .eq("project_id", project_id)
            .limit(1000)
            .execute()
        )

        return build_project_procurement_intelligence(
            project_result.data,
            procurement_result.data or [],
            material_result.data or [],
        )

    return get_project_procurement_intelligence
