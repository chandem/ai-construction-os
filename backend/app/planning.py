"""Planning foundation: WBS from commercial/estimate work sections + schedule activities.

Chain: estimate/BOQ work sections → WBS nodes → schedule activities (proposed).
Durations are illustrative heuristics for planning exploration — not certified programmes.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from .quantity_takeoff import _as_float, _round_qty

WBS_SOURCE = "estimate_work_section"
SCHEDULE_SOURCE = "wbs_heuristic"

WBS_STATUSES = ("proposed", "approved", "active", "complete", "cancelled")
ACTIVITY_STATUSES = (
    "not_started",
    "in_progress",
    "complete",
    "delayed",
    "on_hold",
    "cancelled",
)

# Illustrative duration heuristics (days) by element_type / work section keywords.
# Used only when building a proposed baseline schedule from takeoff/estimate.
DURATION_BY_ELEMENT: dict[str, int] = {
    "foundation": 14,
    "footing": 10,
    "column": 12,
    "beam": 10,
    "slab": 14,
    "wall": 12,
    "retaining_wall": 16,
    "stair": 8,
    "opening": 5,
    "room": 7,
    "pipe": 6,
    "drainage": 8,
    "culvert": 12,
    "road": 20,
    "pavement": 15,
    "equipment": 10,
    "other": 7,
}

# Work-section level default duration when no element breakdown is available
SECTION_DEFAULT_DAYS = 21


def _section_key(row: dict[str, Any]) -> str:
    ws = (row.get("work_section") or row.get("element_type") or "General").strip()
    return ws or "General"


def _duration_for_line(row: dict[str, Any]) -> int:
    et = str(row.get("element_type") or "other").lower().strip()
    base = DURATION_BY_ELEMENT.get(et, DURATION_BY_ELEMENT["other"])
    qty = _as_float(row.get("quantity"))
    # Mild scale with quantity (cap growth)
    if qty is not None and qty > 0:
        scale = min(2.5, 1.0 + (qty / 500.0))
        return max(3, int(round(base * scale)))
    return base


def build_wbs_from_estimate(
    estimate_lines: list[dict[str, Any]],
    *,
    project_id: str,
    project_name: str | None = None,
) -> dict[str, Any]:
    """Build a simple 2-level WBS: project root + one node per work section.

    Child nodes can optionally mirror high-level element groups under each section.
    """
    root_id = str(uuid4())
    root = {
        "id": root_id,
        "project_id": project_id,
        "parent_id": None,
        "code": "1",
        "name": project_name or "Project",
        "level": 0,
        "work_section": None,
        "sort_order": 0,
        "status": "proposed",
        "source": WBS_SOURCE,
        "baseline_amount": None,
        "line_count": 0,
        "properties": {"role": "root"},
    }

    # Group by work section
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in estimate_lines:
        key = _section_key(row)
        groups.setdefault(key, []).append(row)

    nodes: list[dict[str, Any]] = [root]
    section_nodes: list[dict[str, Any]] = []
    total_amount = 0.0
    priced = 0

    for i, (section, rows) in enumerate(sorted(groups.items(), key=lambda x: x[0].lower()), start=1):
        amt = 0.0
        n_priced = 0
        for r in rows:
            a = _as_float(r.get("amount"))
            if a is not None:
                amt += a
                n_priced += 1
        if n_priced:
            total_amount += amt
            priced += n_priced

        node_id = str(uuid4())
        node = {
            "id": node_id,
            "project_id": project_id,
            "parent_id": root_id,
            "code": f"1.{i}",
            "name": section,
            "level": 1,
            "work_section": section,
            "sort_order": i,
            "status": "proposed",
            "source": WBS_SOURCE,
            "baseline_amount": _round_qty(amt) if n_priced else None,
            "line_count": len(rows),
            "properties": {
                "estimate_line_ids": [r.get("id") for r in rows if r.get("id")],
                "element_types": sorted(
                    {str(r.get("element_type") or "other") for r in rows}
                ),
            },
        }
        nodes.append(node)
        section_nodes.append(node)

    root["baseline_amount"] = _round_qty(total_amount) if priced else None
    root["line_count"] = len(estimate_lines)

    return {
        "project_id": project_id,
        "root_id": root_id,
        "nodes": nodes,
        "section_nodes": section_nodes,
        "node_count": len(nodes),
        "section_count": len(section_nodes),
        "source": WBS_SOURCE,
    }


def build_schedule_from_wbs(
    wbs: dict[str, Any],
    estimate_lines: list[dict[str, Any]] | None = None,
    *,
    project_id: str | None = None,
    start_date: date | None = None,
) -> dict[str, Any]:
    """Create one schedule activity per level-1 WBS node, sequenced end-to-start.

    Duration = max line heuristic in that section, or SECTION_DEFAULT_DAYS.
    """
    pid = project_id or wbs.get("project_id")
    if not pid:
        raise ValueError("project_id is required")

    start = start_date or date.today()
    lines = estimate_lines or []
    by_section: dict[str, list[dict[str, Any]]] = {}
    for row in lines:
        by_section.setdefault(_section_key(row), []).append(row)

    section_nodes = wbs.get("section_nodes") or [
        n for n in (wbs.get("nodes") or []) if n.get("level") == 1
    ]

    activities: list[dict[str, Any]] = []
    cursor = start
    pred_id: str | None = None

    for i, node in enumerate(section_nodes, start=1):
        section = node.get("work_section") or node.get("name") or "General"
        section_lines = by_section.get(section, [])
        if section_lines:
            duration = max(_duration_for_line(r) for r in section_lines)
        else:
            duration = SECTION_DEFAULT_DAYS

        finish = cursor + timedelta(days=max(1, duration) - 1)
        act_id = str(uuid4())
        act = {
            "id": act_id,
            "project_id": pid,
            "wbs_node_id": node.get("id"),
            "code": f"A{i:03d}",
            "name": f"{section} works",
            "work_section": section,
            "sort_order": i,
            "status": "not_started",
            "planned_start": cursor.isoformat(),
            "planned_finish": finish.isoformat(),
            "duration_days": duration,
            "percent_complete": 0,
            "predecessor_ids": [pred_id] if pred_id else [],
            "source": SCHEDULE_SOURCE,
            "baseline_amount": node.get("baseline_amount"),
            "notes": "Proposed activity from WBS heuristic — not a certified programme.",
            "properties": {
                "wbs_code": node.get("code"),
                "duration_basis": "element_heuristic" if section_lines else "section_default",
            },
        }
        activities.append(act)
        pred_id = act_id
        cursor = finish + timedelta(days=1)

    planned_finish = activities[-1]["planned_finish"] if activities else start.isoformat()
    return {
        "project_id": pid,
        "activities": activities,
        "activity_count": len(activities),
        "planned_start": start.isoformat(),
        "planned_finish": planned_finish,
        "source": SCHEDULE_SOURCE,
    }


def planning_summary(
    wbs: dict[str, Any] | None,
    schedule: dict[str, Any] | None,
) -> dict[str, Any]:
    """Rollup for Planning Center."""
    nodes = (wbs or {}).get("nodes") or []
    activities = (schedule or {}).get("activities") or []
    by_status: dict[str, int] = {}
    for a in activities:
        st = a.get("status") or "not_started"
        by_status[st] = by_status.get(st, 0) + 1

    total_days = sum(int(a.get("duration_days") or 0) for a in activities)
    return {
        "wbs_node_count": len(nodes),
        "wbs_section_count": (wbs or {}).get("section_count")
        or len([n for n in nodes if n.get("level") == 1]),
        "activity_count": len(activities),
        "activities_by_status": by_status,
        "planned_start": (schedule or {}).get("planned_start"),
        "planned_finish": (schedule or {}).get("planned_finish"),
        "total_duration_days": total_days if activities else None,
        "baseline_amount": (wbs or {}).get("nodes", [{}])[0].get("baseline_amount")
        if nodes
        else None,
        "notes": "WBS and schedule are proposed from the estimate chain for planning exploration.",
    }


def persist_wbs_nodes(client, nodes: list[dict[str, Any]]) -> int:
    """Upsert WBS nodes. Returns count persisted; 0 if table missing."""
    if not nodes:
        return 0
    rows = []
    for n in nodes:
        rows.append(
            {
                "id": n["id"],
                "project_id": n["project_id"],
                "parent_id": n.get("parent_id"),
                "code": n.get("code"),
                "name": n.get("name"),
                "level": n.get("level", 0),
                "work_section": n.get("work_section"),
                "sort_order": n.get("sort_order", 0),
                "status": n.get("status") or "proposed",
                "source": n.get("source") or WBS_SOURCE,
                "baseline_amount": n.get("baseline_amount"),
                "line_count": n.get("line_count"),
                "properties": n.get("properties") or {},
            }
        )
    try:
        client.table("wbs_nodes").upsert(rows).execute()
        return len(rows)
    except Exception:
        return 0


def persist_schedule_activities(client, activities: list[dict[str, Any]]) -> int:
    """Upsert schedule activities. Returns count persisted; 0 if table missing."""
    if not activities:
        return 0
    rows = []
    for a in activities:
        rows.append(
            {
                "id": a["id"],
                "project_id": a["project_id"],
                "wbs_node_id": a.get("wbs_node_id"),
                "code": a.get("code"),
                "name": a.get("name"),
                "work_section": a.get("work_section"),
                "sort_order": a.get("sort_order", 0),
                "status": a.get("status") or "not_started",
                "planned_start": a.get("planned_start"),
                "planned_finish": a.get("planned_finish"),
                "duration_days": a.get("duration_days"),
                "percent_complete": a.get("percent_complete") or 0,
                "predecessor_ids": a.get("predecessor_ids") or [],
                "source": a.get("source") or SCHEDULE_SOURCE,
                "baseline_amount": a.get("baseline_amount"),
                "notes": a.get("notes"),
                "properties": a.get("properties") or {},
            }
        )
    try:
        client.table("schedule_activities").upsert(rows).execute()
        return len(rows)
    except Exception:
        return 0
