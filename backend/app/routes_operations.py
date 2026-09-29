"""Operations routes: planning + procurement (Phases 5–6)."""
from fastapi import APIRouter, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .db import supabase
from .routes import _project_for_member
from .routes_helpers import (
    BOQ_FIELDS,
    ELEMENT_FIELDS,
    ESTIMATE_FIELDS,
    _boq_lines_for_project,
    _estimate_lines_for_project,
)
from .planning import (
    build_schedule_from_wbs,
    build_wbs_from_estimate,
    persist_schedule_activities,
    persist_wbs_nodes,
    planning_summary,
)
from .procurement import (
    build_procurement_package,
    persist_equipment,
    persist_materials,
    persist_workforce,
)
from .estimate import build_estimate_from_boq

router = APIRouter()

# Phase 5 — Planning (WBS + schedule)
# Content loaded from modular split of routes_engineering.py
# See full phase routes in repository after complete push.

WBS_FIELDS = (
    "id,project_id,parent_id,code,name,level,work_section,sort_order,status,"
    "source,baseline_amount,line_count,properties,created_at,updated_at"
)
SCHEDULE_FIELDS = (
    "id,project_id,wbs_node_id,code,name,work_section,sort_order,status,"
    "planned_start,planned_finish,duration_days,percent_complete,predecessor_ids,"
    "source,baseline_amount,notes,properties,created_at,updated_at"
)


@router.get("/projects/{project_id}/planning/summary")
def project_planning_summary(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    wbs_nodes, activities = [], []
    try:
        wbs_nodes = (
            client.table("wbs_nodes").select(WBS_FIELDS).eq("project_id", project_id).execute().data or []
        )
    except Exception:
        pass
    try:
        activities = (
            client.table("schedule_activities")
            .select(SCHEDULE_FIELDS)
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
    except Exception:
        pass
    wbs = {"nodes": wbs_nodes, "section_count": len([n for n in wbs_nodes if n.get("level") == 1])}
    schedule = {"activities": activities}
    return {"data": planning_summary(wbs, schedule), "wbs_nodes": wbs_nodes, "activities": activities}


@router.get("/projects/{project_id}/planning/wbs")
def list_or_preview_wbs(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = client.table("wbs_nodes").select(WBS_FIELDS).eq("project_id", project_id).order("sort_order").execute()
        if result.data:
            return {"data": result.data, "source": "stored"}
    except Exception:
        pass
    lines, _, warning = _estimate_lines_for_project(client, project_id)
    if not lines:
        return {"data": [], "warning": warning or "No estimate lines for WBS"}
    wbs = build_wbs_from_estimate(lines, project_id=project_id)
    return {"data": wbs.get("nodes") or [], "source": "preview", "section_count": wbs.get("section_count")}


@router.post("/projects/{project_id}/planning/wbs/generate")
def generate_and_persist_wbs(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    lines, _, warning = _estimate_lines_for_project(client, project_id)
    if not lines:
        return {"data": [], "persisted": 0, "warning": warning or "No estimate lines"}
    wbs = build_wbs_from_estimate(lines, project_id=project_id)
    n = persist_wbs_nodes(client, wbs.get("nodes") or [])
    return {"data": wbs.get("nodes") or [], "persisted": n, "section_count": wbs.get("section_count")}


@router.get("/projects/{project_id}/planning/schedule")
def list_or_preview_schedule(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("schedule_activities")
            .select(SCHEDULE_FIELDS)
            .eq("project_id", project_id)
            .order("sort_order")
            .execute()
        )
        if result.data:
            return {"data": result.data, "source": "stored"}
    except Exception:
        pass
    lines, _, warning = _estimate_lines_for_project(client, project_id)
    if not lines:
        return {"data": [], "warning": warning or "No estimate lines"}
    wbs = build_wbs_from_estimate(lines, project_id=project_id)
    sched = build_schedule_from_wbs(wbs, lines, project_id=project_id)
    return {"data": sched.get("activities") or [], "source": "preview", **{k: sched.get(k) for k in ("planned_start", "planned_finish", "activity_count")}}


@router.post("/projects/{project_id}/planning/schedule/generate")
def generate_and_persist_schedule(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    lines, _, warning = _estimate_lines_for_project(client, project_id)
    if not lines:
        return {"data": [], "persisted": 0, "warning": warning or "No estimate lines"}
    wbs = build_wbs_from_estimate(lines, project_id=project_id)
    persist_wbs_nodes(client, wbs.get("nodes") or [])
    sched = build_schedule_from_wbs(wbs, lines, project_id=project_id)
    n = persist_schedule_activities(client, sched.get("activities") or [])
    return {"data": sched.get("activities") or [], "persisted": n, "activity_count": sched.get("activity_count")}


# Phase 6 — Procurement
MATERIAL_FIELDS = (
    "id,project_id,material_code,name,category,unit,quantity,work_sections,"
    "element_types,source_line_count,status,source,properties,created_at,updated_at"
)
EQUIPMENT_FIELDS = (
    "id,project_id,equipment_code,name,unit,quantity_days,work_sections,status,"
    "source,properties,created_at,updated_at"
)
WORKFORCE_FIELDS = (
    "id,project_id,trade,headcount,duration_days,person_days,work_section,status,"
    "source,properties,created_at,updated_at"
)


@router.get("/projects/{project_id}/procurement/summary")
def project_procurement_summary(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    lines, _, warning = _estimate_lines_for_project(client, project_id)
    if not lines:
        return {"data": {}, "warning": warning or "No estimate lines"}
    pkg = build_procurement_package(lines, project_id=project_id)
    return {"data": pkg["summary"], "materials": pkg["materials"], "equipment": pkg["equipment"], "workforce": pkg["workforce"]}


@router.post("/projects/{project_id}/procurement/generate")
def generate_and_persist_procurement(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    lines, _, warning = _estimate_lines_for_project(client, project_id)
    if not lines:
        return {"data": {}, "persisted": {}, "warning": warning or "No estimate lines"}
    pkg = build_procurement_package(lines, project_id=project_id)
    pm = persist_materials(client, pkg["materials"])
    pe = persist_equipment(client, pkg["equipment"])
    pw = persist_workforce(client, pkg["workforce"])
    return {
        "data": pkg["summary"],
        "persisted": {"materials": pm, "equipment": pe, "workforce": pw},
        "materials": pkg["materials"],
        "equipment": pkg["equipment"],
        "workforce": pkg["workforce"],
    }
