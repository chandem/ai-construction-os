"""Field + quality routes (Phases 7–8)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import get_access_token, get_current_user
from .db import supabase
from .routes import _project_for_member
from .field import (
    apply_progress_to_activity,
    build_diary_entry,
    build_progress_update,
    field_summary,
    persist_activity_progress,
    persist_diary_entry,
    persist_progress_update,
)
from .quality import (
    build_incident,
    build_inspection,
    build_ncr,
    persist_incident,
    persist_inspection,
    persist_ncr,
    quality_summary,
)

router = APIRouter()


class DiaryCreate(BaseModel):
    work_summary: str | None = Field(default=None, max_length=8000)
    weather: str | None = None
    workforce_on_site: int | None = Field(default=None, ge=0)
    equipment_on_site: str | None = Field(default=None, max_length=2000)
    issues: str | None = Field(default=None, max_length=4000)
    safety_notes: str | None = Field(default=None, max_length=4000)
    work_section: str | None = Field(default=None, max_length=500)
    entry_date: str | None = None


class ProgressCreate(BaseModel):
    activity_id: str
    percent_complete: float = Field(ge=0, le=100)
    note: str | None = Field(default=None, max_length=4000)


SCHEDULE_FIELDS = (
    "id,project_id,wbs_node_id,code,name,work_section,sort_order,status,"
    "planned_start,planned_finish,duration_days,percent_complete,predecessor_ids,"
    "source,baseline_amount,notes,properties,created_at,updated_at"
)

DIARY_FIELDS = (
    "id,project_id,entry_date,weather,work_summary,workforce_on_site,equipment_on_site,"
    "issues,safety_notes,work_section,schedule_activity_id,status,source,created_by,"
    "properties,created_at,updated_at"
)
PROGRESS_FIELDS = (
    "id,project_id,schedule_activity_id,activity_code,activity_name,work_section,"
    "report_date,percent_complete,previous_percent,delta_percent,note,status,source,"
    "recorded_by,properties,created_at,updated_at"
)

INSPECTION_FIELDS = (
    "id,project_id,title,inspection_type,work_section,location,inspector,result,"
    "findings,schedule_activity_id,inspection_date,status,source,properties,created_at,updated_at"
)
NCR_FIELDS = (
    "id,project_id,ncr_code,title,description,severity,work_section,location,inspection_id,"
    "raised_by,corrective_action,status,raised_date,source,properties,created_at,updated_at"
)
INCIDENT_FIELDS = (
    "id,project_id,incident_code,title,incident_type,severity,description,location,"
    "work_section,reported_by,persons_involved,status,incident_date,source,properties,"
    "created_at,updated_at"
)


@router.get("/projects/{project_id}/field/summary")
def project_field_summary(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    diary, progress, activities = [], [], []
    try:
        diary = (
            client.table("site_diary_entries")
            .select(DIARY_FIELDS)
            .eq("project_id", project_id)
            .order("entry_date", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
    except Exception:
        pass
    try:
        progress = (
            client.table("progress_updates")
            .select(PROGRESS_FIELDS)
            .eq("project_id", project_id)
            .order("report_date", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
    except Exception:
        pass
    try:
        activities = (
            client.table("schedule_activities")
            .select(SCHEDULE_FIELDS)
            .eq("project_id", project_id)
            .order("sort_order")
            .execute()
            .data
            or []
        )
    except Exception:
        pass
    return {
        "data": field_summary(diary, progress, activities),
        "diary": diary[:10],
        "progress": progress[:10],
        "activities": activities,
    }


@router.get("/projects/{project_id}/field/diary")
def list_site_diary(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("site_diary_entries")
            .select(DIARY_FIELDS)
            .eq("project_id", project_id)
            .order("entry_date", desc=True)
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {
            "data": [],
            "warning": "site_diary_entries table is not available yet — apply supabase/field.sql",
        }


@router.post("/projects/{project_id}/field/diary")
def create_site_diary(
    project_id: str,
    body: DiaryCreate | None = None,
    work_summary: str | None = None,
    weather: str | None = None,
    workforce_on_site: int | None = None,
    equipment_on_site: str | None = None,
    issues: str | None = None,
    safety_notes: str | None = None,
    work_section: str | None = None,
    entry_date: str | None = None,
    token: str = Depends(get_access_token),
):
    """Create diary entry. Accepts JSON body (preferred) or query params (legacy)."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)

    b = body or DiaryCreate()
    entry = build_diary_entry(
        project_id=project_id,
        entry_date=b.entry_date or entry_date,
        weather=b.weather or weather,
        work_summary=b.work_summary or work_summary or "Site works ongoing",
        workforce_on_site=b.workforce_on_site if b.workforce_on_site is not None else workforce_on_site,
        equipment_on_site=b.equipment_on_site or equipment_on_site,
        issues=b.issues or issues,
        safety_notes=b.safety_notes or safety_notes,
        work_section=b.work_section or work_section,
        created_by=user.get("id") or user.get("email"),
        status="submitted",
    )
    persisted = persist_diary_entry(client, entry)
    out = {"data": entry, "persisted": persisted is not None}
    if persisted is None:
        out["warning"] = "site_diary_entries table is not available yet — apply supabase/field.sql"
    return out


@router.get("/projects/{project_id}/field/progress")
def list_progress_updates(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("progress_updates")
            .select(PROGRESS_FIELDS)
            .eq("project_id", project_id)
            .order("report_date", desc=True)
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {
            "data": [],
            "warning": "progress_updates table is not available yet — apply supabase/field.sql",
        }


@router.post("/projects/{project_id}/field/progress")
def record_progress(
    project_id: str,
    body: ProgressCreate | None = None,
    activity_id: str | None = None,
    percent_complete: float | None = None,
    note: str | None = None,
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)

    aid = (body.activity_id if body else None) or activity_id
    pct = (body.percent_complete if body else None)
    if pct is None:
        pct = percent_complete if percent_complete is not None else 0.0
    note_val = (body.note if body else None) or note

    if not aid:
        raise HTTPException(status_code=400, detail="activity_id is required")

    activity = None
    try:
        result = (
            client.table("schedule_activities")
            .select(SCHEDULE_FIELDS)
            .eq("id", aid)
            .eq("project_id", project_id)
            .maybe_single()
            .execute()
        )
        activity = result.data
    except Exception:
        pass
    if not activity:
        activity = {
            "id": aid,
            "project_id": project_id,
            "code": "A?",
            "name": "Activity",
            "percent_complete": 0,
            "status": "not_started",
        }
    update = build_progress_update(
        activity,
        project_id=project_id,
        percent_complete=float(pct),
        note=note_val,
        recorded_by=user.get("id") or user.get("email"),
    )
    persisted = persist_progress_update(client, update)
    updated_act = apply_progress_to_activity(activity, float(pct))
    act_ok = persist_activity_progress(
        client, aid, project_id, float(updated_act["percent_complete"]), updated_act.get("status")
    )
    out = {
        "data": update,
        "activity": updated_act,
        "persisted": persisted is not None,
        "activity_updated": act_ok,
    }
    if persisted is None:
        out["warning"] = "progress_updates table is not available yet — apply supabase/field.sql"
    return out


@router.get("/projects/{project_id}/quality/summary")
def project_quality_summary(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    inspections, ncrs, incidents = [], [], []
    try:
        inspections = (
            client.table("inspections")
            .select(INSPECTION_FIELDS)
            .eq("project_id", project_id)
            .order("inspection_date", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
    except Exception:
        pass
    try:
        ncrs = (
            client.table("ncrs")
            .select(NCR_FIELDS)
            .eq("project_id", project_id)
            .order("raised_date", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
    except Exception:
        pass
    try:
        incidents = (
            client.table("incidents")
            .select(INCIDENT_FIELDS)
            .eq("project_id", project_id)
            .order("incident_date", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
    except Exception:
        pass
    return {
        "data": quality_summary(inspections, ncrs, incidents),
        "inspections": inspections,
        "ncrs": ncrs,
        "incidents": incidents,
    }


@router.get("/projects/{project_id}/quality/inspections")
def list_inspections(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("inspections")
            .select(INSPECTION_FIELDS)
            .eq("project_id", project_id)
            .order("inspection_date", desc=True)
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {
            "data": [],
            "warning": "inspections table is not available yet — apply supabase/quality.sql",
        }


@router.post("/projects/{project_id}/quality/inspections")
def create_inspection(
    project_id: str,
    title: str = "Inspection",
    inspection_type: str = "workmanship",
    result: str = "pending",
    findings: str | None = None,
    work_section: str | None = None,
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    row = build_inspection(
        project_id=project_id,
        title=title,
        inspection_type=inspection_type,
        result=result,
        findings=findings,
        work_section=work_section,
        inspector=user.get("email") or user.get("id"),
        status="completed" if result != "pending" else "in_progress",
    )
    persisted = persist_inspection(client, row)
    out = {"data": row, "persisted": persisted is not None}
    if persisted is None:
        out["warning"] = "inspections table is not available yet — apply supabase/quality.sql"
    return out


@router.get("/projects/{project_id}/quality/ncrs")
def list_ncrs(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("ncrs")
            .select(NCR_FIELDS)
            .eq("project_id", project_id)
            .order("raised_date", desc=True)
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {"data": [], "warning": "ncrs table is not available yet — apply supabase/quality.sql"}


@router.post("/projects/{project_id}/quality/ncrs")
def create_ncr(
    project_id: str,
    title: str = "Non-conformance",
    description: str | None = None,
    severity: str = "minor",
    work_section: str | None = None,
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    row = build_ncr(
        project_id=project_id,
        title=title,
        description=description,
        severity=severity,
        work_section=work_section,
        raised_by=user.get("email") or user.get("id"),
    )
    persisted = persist_ncr(client, row)
    out = {"data": row, "persisted": persisted is not None}
    if persisted is None:
        out["warning"] = "ncrs table is not available yet — apply supabase/quality.sql"
    return out


@router.get("/projects/{project_id}/quality/incidents")
def list_incidents(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("incidents")
            .select(INCIDENT_FIELDS)
            .eq("project_id", project_id)
            .order("incident_date", desc=True)
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {
            "data": [],
            "warning": "incidents table is not available yet — apply supabase/quality.sql",
        }


@router.post("/projects/{project_id}/quality/incidents")
def create_incident(
    project_id: str,
    title: str = "Incident",
    incident_type: str = "near_miss",
    severity: str = "low",
    description: str | None = None,
    work_section: str | None = None,
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    row = build_incident(
        project_id=project_id,
        title=title,
        incident_type=incident_type,
        severity=severity,
        description=description,
        work_section=work_section,
        reported_by=user.get("email") or user.get("id"),
    )
    persisted = persist_incident(client, row)
    out = {"data": row, "persisted": persisted is not None}
    if persisted is None:
        out["warning"] = "incidents table is not available yet — apply supabase/quality.sql"
    return out
