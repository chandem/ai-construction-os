"""Intelligence routes: GIS, prediction, brain, integrations, ops (Phases 9–13)."""
from fastapi import APIRouter, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .db import supabase
from .routes import _project_for_member
from .routes_helpers import ELEMENT_FIELDS, _estimate_lines_for_project
from .gis import (
    assets_from_engineering_elements,
    build_location,
    gis_summary,
    persist_assets_batch,
    persist_location,
)
from .prediction import (
    build_forecasts,
    derive_risks_from_signals,
    persist_forecasts_batch,
    persist_risks_batch,
    prediction_summary,
)
from .brain import brain_context_text, brain_summary, build_insights, build_project_snapshot
from .integrations import (
    build_connection,
    build_sync_job,
    integrations_summary,
    list_connector_catalog,
    persist_connection,
    persist_sync_job,
    simulate_sync_complete,
)
from .hardening import (
    build_cost_event,
    build_queue_job,
    cost_summary,
    estimate_cost,
    mark_failed,
    mark_running,
    mark_succeeded,
    persist_cost_event,
    persist_queue_job,
    queue_summary,
    system_health,
)
from .quantity_takeoff import enrich_elements

router = APIRouter()


@router.get("/projects/{project_id}/gis/summary")
def project_gis_summary(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    locs, assets = [], []
    try:
        locs = client.table("gis_locations").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    try:
        assets = client.table("infrastructure_assets").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    return {"data": gis_summary(locs, assets), "locations": locs, "assets": assets}


@router.post("/projects/{project_id}/gis/assets/from-elements")
def generate_gis_assets_from_elements(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        rows = client.table("engineering_elements").select(ELEMENT_FIELDS).eq("project_id", project_id).execute().data or []
    except Exception:
        return {"data": [], "persisted": 0, "warning": "engineering_elements not available"}
    assets = assets_from_engineering_elements(rows, project_id=project_id)
    n = persist_assets_batch(client, assets)
    return {"data": assets, "persisted": n}


@router.get("/projects/{project_id}/prediction/summary")
def project_prediction_summary(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    _, est_summary, _ = _estimate_lines_for_project(client, project_id)
    acts, ncrs, incidents = [], [], []
    try:
        acts = client.table("schedule_activities").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    try:
        ncrs = client.table("ncrs").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    try:
        incidents = client.table("incidents").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    risks = derive_risks_from_signals(
        project_id=project_id,
        estimate_summary=est_summary,
        schedule_activities=acts,
        ncrs=ncrs,
        incidents=incidents,
    )
    forecasts = build_forecasts(
        project_id=project_id,
        estimate_summary=est_summary,
        schedule_activities=acts,
        risks=risks,
    )
    return {"data": prediction_summary(risks, forecasts), "risks": risks, "forecasts": forecasts}


@router.post("/projects/{project_id}/prediction/generate")
def generate_prediction(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    _, est_summary, _ = _estimate_lines_for_project(client, project_id)
    acts, ncrs, incidents = [], [], []
    try:
        acts = client.table("schedule_activities").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    try:
        ncrs = client.table("ncrs").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    try:
        incidents = client.table("incidents").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    risks = derive_risks_from_signals(
        project_id=project_id, estimate_summary=est_summary,
        schedule_activities=acts, ncrs=ncrs, incidents=incidents,
    )
    forecasts = build_forecasts(
        project_id=project_id, estimate_summary=est_summary,
        schedule_activities=acts, risks=risks,
    )
    nr = persist_risks_batch(client, risks)
    nf = persist_forecasts_batch(client, forecasts)
    return {"data": prediction_summary(risks, forecasts), "persisted": {"risks": nr, "forecasts": nf}, "risks": risks, "forecasts": forecasts}


@router.get("/projects/{project_id}/brain/insights")
def project_brain_insights(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    _, est_summary, _ = _estimate_lines_for_project(client, project_id)
    element_count = 0
    try:
        element_count = len(client.table("engineering_elements").select("id").eq("project_id", project_id).execute().data or [])
    except Exception:
        pass
    acts = []
    try:
        acts = client.table("schedule_activities").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    pred = project_prediction_summary(project_id, token)
    snap = build_project_snapshot(
        project_id=project_id,
        estimate_summary=est_summary,
        element_count=element_count,
        schedule_activities=acts,
        prediction_summary=pred.get("data"),
        risks=pred.get("risks"),
        forecasts=pred.get("forecasts"),
    )
    insights = build_insights(snap)
    return {
        "data": brain_summary(snap, insights),
        "snapshot": snap,
        "insights": insights,
        "context_text": brain_context_text(snap, insights),
    }


@router.get("/projects/{project_id}/integrations/summary")
def project_integrations_summary(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    conns, jobs = [], []
    try:
        conns = client.table("integration_connections").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    try:
        jobs = client.table("integration_sync_jobs").select("*").eq("project_id", project_id).execute().data or []
    except Exception:
        pass
    return {"data": integrations_summary(conns, jobs), "catalog": list_connector_catalog(), "connections": conns, "jobs": jobs}


@router.post("/projects/{project_id}/integrations/connections")
def create_integration_connection(
    project_id: str,
    connector_type: str = "p6",
    name: str | None = None,
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    conn = build_connection(project_id=project_id, connector_type=connector_type, name=name)
    persisted = persist_connection(client, conn)
    return {"data": conn, "persisted": persisted is not None}


@router.get("/ops/health")
def ops_system_health(token: str = Depends(get_access_token)):
    get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    jobs, events = [], []
    try:
        jobs = client.table("ops_queue_jobs").select("*").execute().data or []
    except Exception:
        pass
    try:
        events = client.table("ops_cost_events").select("*").execute().data or []
    except Exception:
        pass
    qs = queue_summary(jobs)
    cs = cost_summary(events, budget_usd=10.0)
    return {"data": system_health(queue=qs, cost=cs, checks={"db": True})}


@router.post("/ops/queue/jobs")
def enqueue_ops_job(
    kind: str = "other",
    project_id: str | None = None,
    token: str = Depends(get_access_token),
):
    get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    job = build_queue_job(project_id=project_id, kind=kind)
    persisted = persist_queue_job(client, job)
    return {"data": job, "persisted": persisted is not None}
