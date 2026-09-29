"""Quality & safety: inspections, NCRs (non-conformance reports), incidents.

Chain: field/schedule context → inspections → NCRs → incidents → quality summary.
Records are operational for professional review — not certified audit evidence alone.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

QUALITY_SOURCE = "quality_ops"

INSPECTION_TYPES = (
    "material",
    "workmanship",
    "hold_point",
    "witness_point",
    "final",
    "safety",
    "other",
)
INSPECTION_RESULTS = ("pass", "fail", "conditional", "pending")
INSPECTION_STATUSES = ("planned", "in_progress", "completed", "cancelled")

NCR_SEVERITIES = ("minor", "major", "critical")
NCR_STATUSES = ("open", "under_review", "corrective_action", "closed", "cancelled")

INCIDENT_TYPES = (
    "near_miss",
    "first_aid",
    "lost_time",
    "property_damage",
    "environmental",
    "other",
)
INCIDENT_SEVERITIES = ("low", "medium", "high", "critical")
INCIDENT_STATUSES = ("reported", "investigating", "actions_open", "closed", "cancelled")


def build_inspection(
    *,
    project_id: str,
    title: str,
    inspection_type: str = "workmanship",
    work_section: str | None = None,
    location: str | None = None,
    inspector: str | None = None,
    result: str = "pending",
    findings: str | None = None,
    schedule_activity_id: str | None = None,
    inspection_date: str | None = None,
    status: str = "planned",
) -> dict[str, Any]:
    if inspection_type not in INSPECTION_TYPES:
        inspection_type = "other"
    if result not in INSPECTION_RESULTS:
        result = "pending"
    if status not in INSPECTION_STATUSES:
        status = "planned"
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "title": title or "Inspection",
        "inspection_type": inspection_type,
        "work_section": work_section,
        "location": location or "",
        "inspector": inspector or "",
        "result": result,
        "findings": findings or "",
        "schedule_activity_id": schedule_activity_id,
        "inspection_date": inspection_date or date.today().isoformat(),
        "status": status,
        "source": QUALITY_SOURCE,
        "properties": {},
    }


def build_ncr(
    *,
    project_id: str,
    title: str,
    description: str | None = None,
    severity: str = "minor",
    work_section: str | None = None,
    location: str | None = None,
    inspection_id: str | None = None,
    raised_by: str | None = None,
    corrective_action: str | None = None,
    status: str = "open",
    raised_date: str | None = None,
) -> dict[str, Any]:
    if severity not in NCR_SEVERITIES:
        severity = "minor"
    if status not in NCR_STATUSES:
        status = "open"
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "ncr_code": f"NCR-{str(uuid4())[:8].upper()}",
        "title": title or "Non-conformance",
        "description": description or "",
        "severity": severity,
        "work_section": work_section,
        "location": location or "",
        "inspection_id": inspection_id,
        "raised_by": raised_by,
        "corrective_action": corrective_action or "",
        "status": status,
        "raised_date": raised_date or date.today().isoformat(),
        "source": QUALITY_SOURCE,
        "properties": {},
    }


def build_incident(
    *,
    project_id: str,
    title: str,
    incident_type: str = "near_miss",
    severity: str = "low",
    description: str | None = None,
    location: str | None = None,
    work_section: str | None = None,
    reported_by: str | None = None,
    persons_involved: int | None = None,
    status: str = "reported",
    incident_date: str | None = None,
) -> dict[str, Any]:
    if incident_type not in INCIDENT_TYPES:
        incident_type = "other"
    if severity not in INCIDENT_SEVERITIES:
        severity = "low"
    if status not in INCIDENT_STATUSES:
        status = "reported"
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "incident_code": f"INC-{str(uuid4())[:8].upper()}",
        "title": title or "Incident",
        "incident_type": incident_type,
        "severity": severity,
        "description": description or "",
        "location": location or "",
        "work_section": work_section,
        "reported_by": reported_by,
        "persons_involved": persons_involved,
        "status": status,
        "incident_date": incident_date or date.today().isoformat(),
        "source": QUALITY_SOURCE,
        "properties": {},
    }


def quality_summary(
    inspections: list[dict[str, Any]],
    ncrs: list[dict[str, Any]],
    incidents: list[dict[str, Any]],
) -> dict[str, Any]:
    insp_by_result: dict[str, int] = {}
    for i in inspections:
        r = i.get("result") or "pending"
        insp_by_result[r] = insp_by_result.get(r, 0) + 1
    ncr_open = sum(1 for n in ncrs if n.get("status") not in ("closed", "cancelled"))
    ncr_by_sev: dict[str, int] = {}
    for n in ncrs:
        s = n.get("severity") or "minor"
        ncr_by_sev[s] = ncr_by_sev.get(s, 0) + 1
    inc_open = sum(1 for x in incidents if x.get("status") not in ("closed", "cancelled"))
    inc_by_type: dict[str, int] = {}
    for x in incidents:
        t = x.get("incident_type") or "other"
        inc_by_type[t] = inc_by_type.get(t, 0) + 1
    return {
        "inspection_count": len(inspections),
        "inspections_by_result": insp_by_result,
        "ncr_count": len(ncrs),
        "ncr_open": ncr_open,
        "ncrs_by_severity": ncr_by_sev,
        "incident_count": len(incidents),
        "incidents_open": inc_open,
        "incidents_by_type": inc_by_type,
        "notes": "Quality & safety records for site control and review.",
    }


def persist_inspection(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row["project_id"],
        "title": row.get("title"),
        "inspection_type": row.get("inspection_type"),
        "work_section": row.get("work_section"),
        "location": row.get("location"),
        "inspector": row.get("inspector"),
        "result": row.get("result"),
        "findings": row.get("findings"),
        "schedule_activity_id": row.get("schedule_activity_id"),
        "inspection_date": row.get("inspection_date"),
        "status": row.get("status") or "planned",
        "source": row.get("source") or QUALITY_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("inspections").upsert(payload).execute()
        return payload
    except Exception:
        return None


def persist_ncr(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row["project_id"],
        "ncr_code": row.get("ncr_code"),
        "title": row.get("title"),
        "description": row.get("description"),
        "severity": row.get("severity"),
        "work_section": row.get("work_section"),
        "location": row.get("location"),
        "inspection_id": row.get("inspection_id"),
        "raised_by": row.get("raised_by"),
        "corrective_action": row.get("corrective_action"),
        "status": row.get("status") or "open",
        "raised_date": row.get("raised_date"),
        "source": row.get("source") or QUALITY_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("ncrs").upsert(payload).execute()
        return payload
    except Exception:
        return None


def persist_incident(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row["project_id"],
        "incident_code": row.get("incident_code"),
        "title": row.get("title"),
        "incident_type": row.get("incident_type"),
        "severity": row.get("severity"),
        "description": row.get("description"),
        "location": row.get("location"),
        "work_section": row.get("work_section"),
        "reported_by": row.get("reported_by"),
        "persons_involved": row.get("persons_involved"),
        "status": row.get("status") or "reported",
        "incident_date": row.get("incident_date"),
        "source": row.get("source") or QUALITY_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("incidents").upsert(payload).execute()
        return payload
    except Exception:
        return None
