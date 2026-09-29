"""Field operations: site diary entries + progress updates against schedule activities.

Chain: schedule activities → progress % → diary narrative → field summary.
Progress and diary content are operational records for professional review.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from .quantity_takeoff import _as_float, _round_qty

FIELD_SOURCE = "field_ops"

DIARY_STATUSES = ("draft", "submitted", "reviewed", "archived")
PROGRESS_STATUSES = ("recorded", "verified", "disputed", "cancelled")
WEATHER_OPTIONS = ("clear", "cloudy", "rain", "storm", "hot", "cold", "windy", "other")


def build_diary_entry(
    *,
    project_id: str,
    entry_date: str | None = None,
    weather: str | None = None,
    work_summary: str | None = None,
    workforce_on_site: int | None = None,
    equipment_on_site: str | None = None,
    issues: str | None = None,
    safety_notes: str | None = None,
    work_section: str | None = None,
    schedule_activity_id: str | None = None,
    created_by: str | None = None,
    status: str = "draft",
) -> dict[str, Any]:
    """Build one site diary entry (in-memory)."""
    if status not in DIARY_STATUSES:
        status = "draft"
    wx = weather if weather in WEATHER_OPTIONS else (weather or "clear")
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "entry_date": entry_date or date.today().isoformat(),
        "weather": wx,
        "work_summary": work_summary or "",
        "workforce_on_site": workforce_on_site,
        "equipment_on_site": equipment_on_site or "",
        "issues": issues or "",
        "safety_notes": safety_notes or "",
        "work_section": work_section,
        "schedule_activity_id": schedule_activity_id,
        "status": status,
        "source": FIELD_SOURCE,
        "created_by": created_by,
        "properties": {},
    }


def build_progress_update(
    activity: dict[str, Any],
    *,
    project_id: str | None = None,
    percent_complete: float,
    note: str | None = None,
    report_date: str | None = None,
    recorded_by: str | None = None,
    status: str = "recorded",
) -> dict[str, Any]:
    """Build a progress update for a schedule activity."""
    if status not in PROGRESS_STATUSES:
        status = "recorded"
    pct = _as_float(percent_complete)
    if pct is None:
        pct = 0.0
    pct = max(0.0, min(100.0, pct))
    pid = project_id or activity.get("project_id")
    if not pid:
        raise ValueError("project_id is required")

    prev = _as_float(activity.get("percent_complete")) or 0.0
    return {
        "id": str(uuid4()),
        "project_id": pid,
        "schedule_activity_id": activity.get("id"),
        "activity_code": activity.get("code"),
        "activity_name": activity.get("name"),
        "work_section": activity.get("work_section"),
        "report_date": report_date or date.today().isoformat(),
        "percent_complete": _round_qty(pct),
        "previous_percent": _round_qty(prev),
        "delta_percent": _round_qty(pct - prev),
        "note": note or "",
        "status": status,
        "source": FIELD_SOURCE,
        "recorded_by": recorded_by,
        "properties": {
            "planned_start": activity.get("planned_start"),
            "planned_finish": activity.get("planned_finish"),
        },
    }


def apply_progress_to_activity(activity: dict[str, Any], percent_complete: float) -> dict[str, Any]:
    """Return activity copy with updated percent and status heuristic."""
    pct = max(0.0, min(100.0, float(percent_complete)))
    updated = dict(activity)
    updated["percent_complete"] = _round_qty(pct)
    if pct >= 100:
        updated["status"] = "complete"
    elif pct > 0:
        # preserve delayed if already delayed
        if activity.get("status") not in ("delayed", "on_hold", "cancelled"):
            updated["status"] = "in_progress"
    return updated


def field_summary(
    diary_entries: list[dict[str, Any]],
    progress_updates: list[dict[str, Any]],
    activities: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rollup for Field Center."""
    acts = activities or []
    if acts:
        avg_pct = 0.0
        n = 0
        by_status: dict[str, int] = {}
        for a in acts:
            st = a.get("status") or "not_started"
            by_status[st] = by_status.get(st, 0) + 1
            p = _as_float(a.get("percent_complete"))
            if p is not None:
                avg_pct += p
                n += 1
        overall = _round_qty(avg_pct / n) if n else 0.0
    else:
        by_status = {}
        overall = None
        # derive from latest progress per activity
        latest: dict[str, float] = {}
        for u in progress_updates:
            aid = u.get("schedule_activity_id") or u.get("activity_code") or ""
            pct = _as_float(u.get("percent_complete"))
            if aid and pct is not None:
                latest[str(aid)] = pct
        if latest:
            overall = _round_qty(sum(latest.values()) / len(latest))

    return {
        "diary_count": len(diary_entries),
        "progress_update_count": len(progress_updates),
        "activity_count": len(acts) if acts else None,
        "activities_by_status": by_status,
        "overall_percent_complete": overall,
        "latest_diary_date": max((d.get("entry_date") or "" for d in diary_entries), default=None)
        or None,
        "notes": "Field progress and diary are operational records for site control.",
    }


def persist_diary_entry(client, entry: dict[str, Any]) -> dict[str, Any] | None:
    row = {
        "id": entry["id"],
        "project_id": entry["project_id"],
        "entry_date": entry.get("entry_date"),
        "weather": entry.get("weather"),
        "work_summary": entry.get("work_summary"),
        "workforce_on_site": entry.get("workforce_on_site"),
        "equipment_on_site": entry.get("equipment_on_site"),
        "issues": entry.get("issues"),
        "safety_notes": entry.get("safety_notes"),
        "work_section": entry.get("work_section"),
        "schedule_activity_id": entry.get("schedule_activity_id"),
        "status": entry.get("status") or "draft",
        "source": entry.get("source") or FIELD_SOURCE,
        "created_by": entry.get("created_by"),
        "properties": entry.get("properties") or {},
    }
    try:
        client.table("site_diary_entries").upsert(row).execute()
        return row
    except Exception:
        return None


def persist_progress_update(client, update: dict[str, Any]) -> dict[str, Any] | None:
    row = {
        "id": update["id"],
        "project_id": update["project_id"],
        "schedule_activity_id": update.get("schedule_activity_id"),
        "activity_code": update.get("activity_code"),
        "activity_name": update.get("activity_name"),
        "work_section": update.get("work_section"),
        "report_date": update.get("report_date"),
        "percent_complete": update.get("percent_complete"),
        "previous_percent": update.get("previous_percent"),
        "delta_percent": update.get("delta_percent"),
        "note": update.get("note"),
        "status": update.get("status") or "recorded",
        "source": update.get("source") or FIELD_SOURCE,
        "recorded_by": update.get("recorded_by"),
        "properties": update.get("properties") or {},
    }
    try:
        client.table("progress_updates").upsert(row).execute()
        return row
    except Exception:
        return None


def persist_activity_progress(client, activity_id: str, project_id: str, percent_complete: float, status: str | None = None) -> bool:
    """Update schedule_activities percent_complete (and optional status)."""
    payload: dict[str, Any] = {"percent_complete": percent_complete}
    if status:
        payload["status"] = status
    try:
        client.table("schedule_activities").update(payload).eq("id", activity_id).eq("project_id", project_id).execute()
        return True
    except Exception:
        return False
