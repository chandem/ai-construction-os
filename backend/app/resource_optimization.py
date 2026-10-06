"""AI resource optimization for recorded project resources.

This module analyzes only recorded workforce, equipment, materials, activities,
and progress data. It does not infer unavailable utilization rates or future
resource requirements.
"""

from __future__ import annotations

from typing import Any


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_project_resource_optimization(
    project: dict[str, Any],
    workforce: list[dict[str, Any]],
    equipment: list[dict[str, Any]],
    materials: list[dict[str, Any]],
    activities: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return conservative resource-allocation insights from recorded data."""
    equipment_status: dict[str, int] = {}
    for row in equipment:
        status = row.get("status") or "unknown"
        equipment_status[status] = equipment_status.get(status, 0) + 1

    material_bottlenecks: list[dict[str, Any]] = []
    for row in materials:
        stock = _number(row.get("stock_quantity"))
        reorder = _number(row.get("reorder_level"))
        if stock is not None and reorder is not None and stock <= reorder:
            material_bottlenecks.append({
                "name": row.get("name") or row.get("code") or "Unnamed material",
                "stock_quantity": stock,
                "reorder_level": reorder,
                "unit": row.get("unit"),
                "supplier": row.get("supplier"),
            })

    activity_gaps: list[dict[str, Any]] = []
    for row in activities:
        planned = _number(row.get("planned_percent"))
        actual = _number(row.get("actual_percent"))
        if planned is None or actual is None:
            activity_gaps.append({
                "name": row.get("name") or row.get("code") or "Unnamed activity",
                "planned_percent": row.get("planned_percent"),
                "actual_percent": row.get("actual_percent"),
                "reason": "Missing valid planned or actual progress.",
            })

    priorities: list[dict[str, Any]] = []
    if not workforce:
        priorities.append({
            "priority": "medium",
            "area": "Workforce",
            "action": "Register project workforce and record roles, quantities, and availability.",
            "reason": "No workforce records are available for resource allocation analysis.",
        })

    if not equipment:
        priorities.append({
            "priority": "medium",
            "area": "Equipment",
            "action": "Register project equipment and record operational availability and status.",
            "reason": "No equipment records are available for resource allocation analysis.",
        })
    else:
        unavailable = sum(
            count for status, count in equipment_status.items()
            if status.lower() in {"unavailable", "out_of_service", "maintenance", "down"}
        )
        if unavailable:
            priorities.append({
                "priority": "high",
                "area": "Equipment",
                "action": "Review unavailable equipment and its impact on active work before reallocating resources.",
                "reason": f"{unavailable} recorded equipment item(s) have an unavailable/down status.",
            })

    if material_bottlenecks:
        priorities.append({
            "priority": "high",
            "area": "Materials",
            "action": "Review materials at or below reorder level and coordinate replenishment.",
            "reason": f"{len(material_bottlenecks)} tracked material item(s) are at or below reorder level.",
            "items": material_bottlenecks[:10],
        })
    elif not materials:
        priorities.append({
            "priority": "medium",
            "area": "Materials",
            "action": "Register project materials with stock quantities and reorder levels.",
            "reason": "No material records are available for resource optimization.",
        })

    if not activities:
        priorities.append({
            "priority": "high",
            "area": "Activity-resource alignment",
            "action": "Create the approved activity register before assessing resource allocation by activity.",
            "reason": "No activities are recorded, so resources cannot be linked to active work.",
        })
    elif activity_gaps:
        priorities.append({
            "priority": "medium",
            "area": "Progress data",
            "action": "Complete planned and actual progress fields before using activity progress to guide resource allocation.",
            "reason": f"{len(activity_gaps)} activity record(s) have incomplete progress data.",
        })

    if not priorities:
        priorities.append({
            "priority": "low",
            "area": "Resource control",
            "action": "Continue recording workforce, equipment, materials, and activity progress consistently.",
            "reason": "No immediate resource data gap or recorded bottleneck was identified.",
        })

    rank = {"high": 0, "medium": 1, "low": 2}
    priorities.sort(key=lambda item: rank.get(item["priority"], 3))

    return {
        "project": project,
        "status": "insufficient_data" if not workforce and not equipment and not materials else "analyzable",
        "confidence": "low" if (not workforce or not equipment or not materials or not activities) else "moderate",
        "workforce_count": len(workforce),
        "equipment_count": len(equipment),
        "equipment_status_counts": equipment_status,
        "material_count": len(materials),
        "material_bottleneck_count": len(material_bottlenecks),
        "material_bottlenecks": material_bottlenecks[:20],
        "activity_count": len(activities),
        "activity_progress_gaps": activity_gaps[:20],
        "priorities": priorities[:10],
        "note": (
            "This analysis uses only recorded project resources and activity data. "
            "It does not infer utilization, productivity, shortages, future requirements, "
            "or resource-to-activity assignments when those fields are not recorded, and "
            "it does not modify project records."
        ),
    }


def make_project_resource_optimization_tool(client, project_id: str):
    def get_project_resource_optimization() -> dict[str, Any]:
        """Analyze recorded workforce, equipment, materials, and activity data for resource optimization."""
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
            return (
                client.table(table)
                .select(columns)
                .eq("project_id", project_id)
                .limit(1000)
                .execute()
            ).data or []

        return build_project_resource_optimization(
            project_result.data,
            rows("workforce", "id,name,role,status"),
            rows("equipment", "id,code,name,equipment_type,status"),
            rows("materials", "id,code,name,unit,stock_quantity,reorder_level,supplier"),
            rows("activities", "id,name,status,planned_percent,actual_percent"),
        )

    return get_project_resource_optimization
