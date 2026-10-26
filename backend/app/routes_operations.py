"""Operations routes: planning + procurement (Phases 5–6)."""
from fastapi import APIRouter, Body, Depends, HTTPException

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



@router.post("/projects/{project_id}/planning/wbs/manual")
def create_manual_wbs_node(project_id: str, payload: dict = Body(...), token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="WBS item name is required.")
    try:
        existing = client.table("wbs_nodes").select("id,level,sort_order").eq("project_id", project_id).execute().data or []
        level = int(payload.get("level") or 1)
        if level < 1 or level > 10:
            raise HTTPException(status_code=422, detail="WBS level must be between 1 and 10.")
        code = str(payload.get("code") or f"M{len(existing) + 1}")
        row = {"project_id": project_id, "code": code, "name": name, "level": level,
               "work_section": str(payload.get("work_section") or name).strip(),
               "sort_order": int(payload.get("sort_order") or len(existing) + 1),
               "status": "proposed", "source": "manual", "properties": {"created_manually": True}}
        saved = client.table("wbs_nodes").insert(row).execute()
        if not saved.data:
            raise HTTPException(status_code=503, detail="WBS item was not saved.")
        return {"data": saved.data[0], "message": "WBS item added."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not add WBS item. Check the wbs_nodes schema.") from exc


@router.patch("/projects/{project_id}/planning/wbs/{node_id}")
def edit_manual_wbs_node(project_id: str, node_id: str, payload: dict = Body(...), token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    allowed = ("code", "name", "level", "work_section", "sort_order", "status")
    changes = {key: payload[key] for key in allowed if key in payload}
    if "name" in changes and not str(changes["name"]).strip():
        raise HTTPException(status_code=422, detail="WBS item name cannot be empty.")
    if not changes:
        raise HTTPException(status_code=422, detail="No editable WBS fields supplied.")
    try:
        saved = client.table("wbs_nodes").update(changes).eq("project_id", project_id).eq("id", node_id).execute()
        if not saved.data:
            raise HTTPException(status_code=404, detail="WBS item not found.")
        return {"data": saved.data[0], "message": "WBS item updated."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not update WBS item.") from exc


@router.post("/projects/{project_id}/planning/schedule/manual")
def create_manual_schedule_activity(project_id: str, payload: dict = Body(...), token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Activity name is required.")
    try:
        existing = client.table("schedule_activities").select("id,sort_order").eq("project_id", project_id).execute().data or []
        start = payload.get("planned_start")
        finish = payload.get("planned_finish")
        duration = int(payload.get("duration_days") or 1)
        if duration < 1 or duration > 36500:
            raise HTTPException(status_code=422, detail="Duration must be between 1 and 36500 days.")
        if start and finish and str(finish) < str(start):
            raise HTTPException(status_code=422, detail="Finish date cannot be before start date.")
        row = {"project_id": project_id, "code": str(payload.get("code") or f"M{len(existing) + 1}"),
               "name": name, "work_section": str(payload.get("work_section") or "General").strip(),
               "sort_order": int(payload.get("sort_order") or len(existing) + 1),
               "status": str(payload.get("status") or "not_started"),
               "planned_start": start or None, "planned_finish": finish or None,
               "duration_days": duration, "percent_complete": 0,
               "predecessor_ids": payload.get("predecessor_ids") or [],
               "source": "manual", "notes": str(payload.get("notes") or "").strip() or None,
               "properties": {"created_manually": True}}
        saved = client.table("schedule_activities").insert(row).execute()
        if not saved.data:
            raise HTTPException(status_code=503, detail="Activity was not saved.")
        return {"data": saved.data[0], "message": "Schedule activity added."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not add activity. Check the schedule_activities schema.") from exc


@router.patch("/projects/{project_id}/planning/schedule/{activity_id}")
def edit_schedule_activity(project_id: str, activity_id: str, payload: dict = Body(...), token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    allowed = ("code", "name", "work_section", "sort_order", "status", "planned_start", "planned_finish", "duration_days", "notes")
    changes = {key: payload[key] for key in allowed if key in payload}
    if "name" in changes and not str(changes["name"]).strip():
        raise HTTPException(status_code=422, detail="Activity name cannot be empty.")
    if "duration_days" in changes and not 1 <= int(changes["duration_days"]) <= 36500:
        raise HTTPException(status_code=422, detail="Duration must be between 1 and 36500 days.")
    try:
        current = client.table("schedule_activities").select("id,planned_start,planned_finish").eq("project_id", project_id).eq("id", activity_id).execute().data
        if not current:
            raise HTTPException(status_code=404, detail="Schedule activity not found.")
        start = changes.get("planned_start", current[0].get("planned_start"))
        finish = changes.get("planned_finish", current[0].get("planned_finish"))
        if start and finish and str(finish) < str(start):
            raise HTTPException(status_code=422, detail="Finish date cannot be before start date.")
        if not changes:
            raise HTTPException(status_code=422, detail="No editable activity fields supplied.")
        saved = client.table("schedule_activities").update(changes).eq("project_id", project_id).eq("id", activity_id).execute()
        if not saved.data:
            raise HTTPException(status_code=404, detail="Schedule activity was not updated.")
        return {"data": saved.data[0], "message": "Schedule activity updated."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not update schedule activity.") from exc


@router.post("/projects/{project_id}/planning/schedule/{activity_id}/dependencies")
def update_schedule_dependencies(
    project_id: str,
    activity_id: str,
    payload: dict = Body(...),
    token: str = Depends(get_access_token),
):
    """Update predecessor links for one schedule activity, scoped to its project."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    raw_ids = payload.get("predecessor_ids", [])
    if not isinstance(raw_ids, list) or any(not isinstance(item, str) for item in raw_ids):
        raise HTTPException(status_code=422, detail="predecessor_ids must be a list of activity IDs.")
    predecessor_ids = list(dict.fromkeys(item.strip() for item in raw_ids if item.strip()))
    if activity_id in predecessor_ids:
        raise HTTPException(status_code=422, detail="An activity cannot depend on itself.")
    try:
        result = (
            client.table("schedule_activities").select("id,predecessor_ids")
            .eq("project_id", project_id).execute()
        )
        rows = result.data or []
        by_id = {str(row["id"]): row for row in rows if row.get("id")}
        if activity_id not in by_id:
            raise HTTPException(status_code=404, detail="Schedule activity not found.")
        unknown = [item for item in predecessor_ids if item not in by_id]
        if unknown:
            raise HTTPException(status_code=422, detail="All predecessors must belong to this project's schedule.")
        graph = {
            key: list(dict.fromkeys(value.get("predecessor_ids") or []))
            for key, value in by_id.items()
        }
        graph[activity_id] = predecessor_ids
        for node, preds in graph.items():
            if any(pred not in by_id or pred == node for pred in preds):
                raise HTTPException(status_code=422, detail="Dependency links contain an invalid or self reference.")
        visiting, visited = set(), set()
        def has_cycle(node):
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for pred in graph.get(node, []):
                if has_cycle(pred):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False
        if any(has_cycle(node) for node in graph if node not in visited):
            raise HTTPException(status_code=422, detail="These dependencies create a cycle. Change the predecessor selection and try again.")
        saved = (
            client.table("schedule_activities").update({"predecessor_ids": predecessor_ids})
            .eq("project_id", project_id).eq("id", activity_id).execute()
        )
        if not saved.data:
            raise HTTPException(status_code=404, detail="Schedule activity was not updated.")
        return {"data": saved.data[0], "warning": "Dependencies saved. Critical path recalculated from the updated schedule."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not update schedule dependencies. Verify schedule_activities.predecessor_ids is writable.") from exc


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
