"""Read-only AI intelligence for project Bill of Quantities records."""

from __future__ import annotations

from typing import Any


def build_boq_intelligence(
    project: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    if not items:
        return {
            "project": project,
            "status": "insufficient_data",
            "confidence": "low",
            "item_count": 0,
            "total_amount": 0,
            "work_section_counts": {},
            "data_gaps": ["No BOQ items are currently recorded for this project."],
            "quality_flags": [],
            "priorities": [{
                "priority": "high",
                "action": "Import or enter the approved project BOQ into the BOQ register.",
                "reason": "No structured BOQ items are available for analysis.",
            }],
            "note": (
                "Uploaded BOQ documents can provide context, but this structured analysis "
                "uses only recorded BOQ items and does not invent quantities or prices."
            ),
        }

    total_amount = 0.0
    work_sections: dict[str, int] = {}
    quality_flags: list[dict[str, Any]] = []

    for row in items:
        amount = row.get("amount")
        try:
            amount_value = float(amount) if amount is not None else None
        except (TypeError, ValueError):
            amount_value = None

        if amount_value is not None:
            total_amount += amount_value

        section = str(row.get("work_section") or "Unclassified")
        work_sections[section] = work_sections.get(section, 0) + 1

        quantity = row.get("quantity")
        rate = row.get("unit_rate")
        if quantity is None or quantity <= 0:
            quality_flags.append({
                "code": row.get("code") or row.get("item_code"),
                "issue": "missing_or_nonpositive_quantity",
                "description": row.get("description"),
            })
        if rate is None or rate < 0:
            quality_flags.append({
                "code": row.get("code") or row.get("item_code"),
                "issue": "missing_or_invalid_unit_rate",
                "description": row.get("description"),
            })
        if amount_value is None:
            quality_flags.append({
                "code": row.get("code") or row.get("item_code"),
                "issue": "missing_amount",
                "description": row.get("description"),
            })

    priorities = []
    if quality_flags:
        priorities.append({
            "priority": "high",
            "action": "Review BOQ items with missing or invalid quantities, rates, or amounts.",
            "reason": f"{len(quality_flags)} BOQ data-quality flag(s) were detected.",
        })
    if len(work_sections) > 0:
        largest_section = max(work_sections, key=work_sections.get)
        priorities.append({
            "priority": "medium",
            "action": f"Review the {largest_section} work section for quantity, cost, and procurement coordination.",
            "reason": f"It contains {work_sections[largest_section]} recorded BOQ item(s).",
        })
    if not priorities:
        priorities.append({
            "priority": "low",
            "action": "Continue reconciling BOQ quantities and rates against the approved drawings and contract.",
            "reason": "No immediate structured BOQ data-quality issue was detected.",
        })

    return {
        "project": project,
        "status": "analyzable",
        "confidence": "moderate" if not quality_flags else "low",
        "item_count": len(items),
        "total_amount": round(total_amount, 2),
        "work_section_counts": work_sections,
        "data_gaps": [],
        "quality_flags": quality_flags[:50],
        "priorities": priorities[:10],
        "note": (
            "This analysis uses recorded BOQ fields only. It does not infer missing quantities, "
            "rates, scope, design intent, or contractual entitlement. Approved BOQ, drawings, "
            "specifications, and qualified engineering review remain authoritative."
        ),
    }


def make_project_boq_intelligence_tool(client, project_id: str):
    def get_project_boq_intelligence() -> dict[str, Any]:
        """Analyze the authorized project's structured BOQ records."""
        project_result = (
            client.table("projects")
            .select("id,name,code,status")
            .eq("id", project_id)
            .single()
            .execute()
        )
        if not project_result.data:
            raise ValueError("Project not found")

        items = (
            client.table("boq_items")
            .select(
                "id,code,description,unit,quantity,unit_rate,amount,"
                "item_code,work_section,element_type,item_count,source,status,notes"
            )
            .eq("project_id", project_id)
            .limit(5000)
            .execute()
        ).data or []

        return build_boq_intelligence(project_result.data, items)

    return get_project_boq_intelligence
