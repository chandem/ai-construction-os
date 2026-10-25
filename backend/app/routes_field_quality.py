"""Field + quality routes (Phases 7–8)."""
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import get_access_token, get_current_user
from .routes import _authenticated_client, _project_for_member
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
    client = _authenticated_client(token)
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
    client = _authenticated_client(token)
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
    except Exception as exc:
        msg = str(exc)[:500]
        low = msg.lower()
        if "schema cache" in low or "could not find" in low or "pgrst" in low or "does not exist" in low:
            hint = (
                "site_diary_entries is not visible to the API yet. "
                "In Supabase SQL run: notify pgrst, 'reload schema'; "
                "Then grant access and restart the Render backend. "
                f"API error: {msg}"
            )
        else:
            hint = f"site_diary_entries query failed: {msg}"
        return {"data": [], "warning": hint, "detail": msg}


@router.post("/projects/{project_id}/field/diary")
def create_site_diary(
    project_id: str,
    body: DiaryCreate,
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    row = build_diary_entry(
        project_id=project_id,
        work_summary=body.work_summary,
        weather=body.weather,
        workforce_on_site=body.workforce_on_site,
        equipment_on_site=body.equipment_on_site,
        issues=body.issues,
        safety_notes=body.safety_notes,
        work_section=body.work_section,
        entry_date=body.entry_date,
        created_by=user.get("email") or user.get("id"),
    )
    out = persist_diary_entry(client, row)
    if out.get("persisted", 0) == 0:
        out["warning"] = (
            "site_diary_entries write failed — apply supabase/field.sql, "
            "run notify pgrst, 'reload schema'; grant table access, restart backend."
        )
    return out


@router.get("/projects/{project_id}/field/progress")
def list_progress_updates(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    result = None
    last_error = None
    for attempt in range(2):
        try:
            result = (
                client.table("progress_updates")
                .select(PROGRESS_FIELDS)
                .eq("project_id", project_id)
                .order("report_date", desc=True)
                .execute()
            )
            break
        except Exception as exc:
            last_error = exc
            msg = str(exc).lower()
            transient = any(
                marker in msg
                for marker in (
                    "resource temporarily unavailable",
                    "readerror",
                    "connection reset",
                    "connection aborted",
                    "timed out",
                    "timeout",
                    "temporarily unavailable",
                )
            )
            if attempt == 0 and transient:
                time.sleep(0.25)
                continue
            break

    if result is not None:
        return {"data": result.data or []}

    msg = str(last_error or "Unknown database error")[:500]
    low = msg.lower()
    if "schema cache" in low or "could not find" in low or "pgrst" in low or "does not exist" in low:
        hint = (
            "progress_updates is not visible to the API yet. "
            "In Supabase SQL run: notify pgrst, 'reload schema'; "
            "Then grant access and restart the Render backend. "
            f"API error: {msg}"
        )
    elif any(marker in low for marker in ("resource temporarily unavailable", "readerror", "connection reset", "connection aborted", "timed out", "timeout", "temporarily unavailable")):
        hint = f"progress_updates is temporarily unavailable after retry; please refresh shortly. API error: {msg}"
    else:
        hint = f"progress_updates query failed: {msg}"
    return {"data": [], "warning": hint, "detail": msg}


@router.post("/projects/{project_id}/field/progress")
def record_progress(
    project_id: str,
    body: ProgressCreate,
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    if not (body.activity_id or "").strip():
        raise HTTPException(status_code=400, detail="activity_id is required")
    activity = None
    try:
        activity = (
            client.table("schedule_activities")
            .select(SCHEDULE_FIELDS)
            .eq("id", body.activity_id)
            .eq("project_id", project_id)
            .maybe_single()
            .execute()
            .data
        )
    except Exception:
        activity = None
    previous = None
    if activity and activity.get("percent_complete") is not None:
        try:
            previous = float(activity.get("percent_complete"))
        except (TypeError, ValueError):
            previous = None
    row = build_progress_update(
        project_id=project_id,
        schedule_activity_id=body.activity_id,
        activity_code=(activity or {}).get("code"),
        activity_name=(activity or {}).get("name"),
        work_section=(activity or {}).get("work_section"),
        percent_complete=body.percent_complete,
        previous_percent=previous,
        note=body.note,
        recorded_by=user.get("email") or user.get("id"),
    )
    out = persist_progress_update(client, row)
    if out.get("persisted", 0) == 0:
        out["warning"] = (
            "progress_updates write failed — apply supabase/field.sql, "
            "run notify pgrst, 'reload schema'; grant table access, restart backend."
        )
        return out
    try:
        persist_activity_progress(client, project_id, body.activity_id, body.percent_complete)
    except Exception:
        pass
    return out


class InspectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    inspection_type: str | None = None
    work_section: str | None = None
    location: str | None = None
    inspector: str | None = None
    result: str | None = None
    findings: str | None = Field(default=None, max_length=8000)
    inspection_date: str | None = None


class NcrCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=8000)
    severity: str | None = None
    work_section: str | None = None
    location: str | None = None
    corrective_action: str | None = Field(default=None, max_length=4000)


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    incident_type: str | None = None
    severity: str | None = None
    description: str | None = Field(default=None, max_length=8000)
    location: str | None = None
    work_section: str | None = None
    persons_involved: str | None = None
    incident_date: str | None = None


@router.get("/projects/{project_id}/quality/summary")
def project_quality_summary(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    inspections, ncrs, incidents = [], [], []
    try:
        inspections = (
            client.table("inspections")
            .select(INSPECTION_FIELDS)
            .eq("project_id", project_id)
            .limit(50)
            .execute()
            .data
            or []
        )
    except Exception:
        pass
    try:
        ncrs = client.table("ncrs").select(NCR_FIELDS).eq("project_id", project_id).limit(50).execute().data or []
    except Exception:
        pass
    try:
        incidents = (
            client.table("incidents")
            .select(INCIDENT_FIELDS)
            .eq("project_id", project_id)
            .limit(50)
            .execute()
            .data
            or []
        )
    except Exception:
        pass
    return {"data": quality_summary(inspections, ncrs, incidents)}


@router.get("/projects/{project_id}/quality/inspections")
def list_inspections(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
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
    except Exception as exc:
        msg = str(exc)[:500]
        return {"data": [], "warning": f"inspections query failed: {msg}", "detail": msg}


@router.post("/projects/{project_id}/quality/inspections")
def create_inspection(
    project_id: str,
    body: InspectionCreate,
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    row = build_inspection(
        project_id=project_id,
        title=body.title,
        inspection_type=body.inspection_type,
        work_section=body.work_section,
        location=body.location,
        inspector=body.inspector or user.get("email"),
        result=body.result,
        findings=body.findings,
        inspection_date=body.inspection_date,
    )
    out = persist_inspection(client, row)
    if out.get("persisted", 0) == 0:
        out["warning"] = "inspections table is not available yet — apply supabase/quality.sql"
    return out


@router.get("/projects/{project_id}/quality/ncrs")
def list_ncrs(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = client.table("ncrs").select(NCR_FIELDS).eq("project_id", project_id).execute()
        return {"data": result.data or []}
    except Exception as exc:
        return {"data": [], "warning": f"ncrs query failed: {str(exc)[:500]}", "detail": str(exc)[:500]}


@router.post("/projects/{project_id}/quality/ncrs")
def create_ncr(project_id: str, body: NcrCreate, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    row = build_ncr(
        project_id=project_id,
        title=body.title,
        description=body.description,
        severity=body.severity,
        work_section=body.work_section,
        location=body.location,
        raised_by=user.get("email") or user.get("id"),
        corrective_action=body.corrective_action,
    )
    out = persist_ncr(client, row)
    if out.get("persisted", 0) == 0:
        out["warning"] = "ncrs table is not available yet — apply supabase/quality.sql"
    return out


@router.get("/projects/{project_id}/quality/incidents")
def list_incidents(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
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
    except Exception as exc:
        return {"data": [], "warning": f"incidents query failed: {str(exc)[:500]}", "detail": str(exc)[:500]}


@router.post("/projects/{project_id}/quality/incidents")
def create_incident(
    project_id: str,
    body: IncidentCreate,
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    row = build_incident(
        project_id=project_id,
        title=body.title,
        incident_type=body.incident_type,
        severity=body.severity,
        description=body.description,
        location=body.location,
        work_section=body.work_section,
        reported_by=user.get("email") or user.get("id"),
        persons_involved=body.persons_involved,
        incident_date=body.incident_date,
    )
    out = persist_incident(client, row)
    if out.get("persisted", 0) == 0:
        out["warning"] = "incidents table is not available yet — apply supabase/quality.sql"
    return out
