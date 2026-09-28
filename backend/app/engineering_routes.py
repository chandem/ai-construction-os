from fastapi import APIRouter, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .boq import build_boq_lines, persist_boq_items
from .db import supabase
from .design_to_cost import build_design_to_cost
from .estimate import build_estimate_from_boq, persist_estimate_items
from .quantity_takeoff import enrich_elements, summarize_quantities
from .routes import _project_for_member

router = APIRouter(prefix="/api/v1")

ELEMENT_FIELDS = (
    "id,project_id,design_asset_id,document_id,element_type,name,identifier,"
    "discipline,level,location_description,quantity,unit,dimensions,materials,"
    "properties,source,evidence,confidence,status,created_at,updated_at"
)

BOQ_FIELDS = (
    "id,project_id,item_code,work_section,description,element_type,quantity,unit,"
    "item_count,source_element_ids,source_identifiers,source,status,notes,"
    "properties,created_at,updated_at"
)

ESTIMATE_FIELDS = (
    "id,project_id,boq_item_id,item_code,work_section,description,element_type,"
    "quantity,unit,unit_rate,amount,currency,rate_source,item_count,"
    "source_element_ids,source_identifiers,source,status,notes,properties,"
    "created_at,updated_at"
)


@router.get("/projects/{project_id}/engineering/elements")
def list_project_engineering_elements(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("engineering_elements")
            .select(ELEMENT_FIELDS)
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {"data": [], "warning": "engineering_elements table is not available yet"}


@router.get("/design/assets/{asset_id}/elements")
def list_asset_engineering_elements(asset_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    asset = client.table("design_assets").select("id,project_id").eq("id", asset_id).maybe_single().execute()
    if not asset.data:
        raise HTTPException(status_code=404, detail="Design asset not found")
    _project_for_member(asset.data["project_id"], user["id"], client)
    try:
        result = (
            client.table("engineering_elements")
            .select(ELEMENT_FIELDS)
            .eq("design_asset_id", asset_id)
            .order("created_at", desc=True)
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {"data": [], "warning": "engineering_elements table is not available yet"}


@router.get("/projects/{project_id}/engineering/quantities")
def list_project_quantities(project_id: str, token: str = Depends(get_access_token)):
    """Aggregated takeoff summary by element type and unit."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("engineering_elements")
            .select(ELEMENT_FIELDS)
            .eq("project_id", project_id)
            .execute()
        )
        rows = result.data or []
    except Exception:
        return {"data": [], "summary": [], "warning": "engineering_elements table is not available yet"}

    enriched = enrich_elements(rows)
    summary = summarize_quantities(enriched)
    return {"data": enriched, "summary": summary}


@router.get("/projects/{project_id}/engineering/boq")
def list_project_boq(project_id: str, token: str = Depends(get_access_token)):
    """Proposed BOQ lines built from current engineering quantity takeoff.

    Does not persist. Use POST .../engineering/boq/generate to store.
    """
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("engineering_elements")
            .select(ELEMENT_FIELDS)
            .eq("project_id", project_id)
            .execute()
        )
        rows = result.data or []
    except Exception:
        return {"data": [], "warning": "engineering_elements table is not available yet"}

    enriched = enrich_elements(rows)
    lines = build_boq_lines(enriched, project_id=project_id)
    return {"data": lines, "source_element_count": len(enriched)}


@router.post("/projects/{project_id}/engineering/boq/generate")
def generate_and_persist_boq(project_id: str, token: str = Depends(get_access_token)):
    """Build proposed BOQ from takeoff and insert into boq_items (if table exists)."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("engineering_elements")
            .select(ELEMENT_FIELDS)
            .eq("project_id", project_id)
            .execute()
        )
        rows = result.data or []
    except Exception:
        return {
            "data": [],
            "persisted": 0,
            "warning": "engineering_elements table is not available yet",
        }

    enriched = enrich_elements(rows)
    lines = build_boq_lines(enriched, project_id=project_id)
    persisted = persist_boq_items(client, lines)
    warning = None
    if lines and persisted == 0:
        warning = "boq_items table is not available yet — apply supabase/boq_items.sql"
    return {
        "data": lines,
        "persisted": persisted,
        "source_element_count": len(enriched),
        **({"warning": warning} if warning else {}),
    }


@router.get("/projects/{project_id}/boq/items")
def list_stored_boq_items(project_id: str, token: str = Depends(get_access_token)):
    """List persisted BOQ items for the project."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("boq_items")
            .select(BOQ_FIELDS)
            .eq("project_id", project_id)
            .order("work_section")
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {"data": [], "warning": "boq_items table is not available yet — apply supabase/boq_items.sql"}


def _boq_lines_for_project(client, project_id: str) -> tuple[list[dict], str | None]:
    """Prefer stored boq_items; fall back to live build from engineering_elements."""
    try:
        result = (
            client.table("boq_items")
            .select(BOQ_FIELDS)
            .eq("project_id", project_id)
            .execute()
        )
        stored = result.data or []
        if stored:
            return stored, None
    except Exception:
        pass
    try:
        result = (
            client.table("engineering_elements")
            .select(ELEMENT_FIELDS)
            .eq("project_id", project_id)
            .execute()
        )
        rows = result.data or []
    except Exception:
        return [], "engineering_elements table is not available yet"
    enriched = enrich_elements(rows)
    return build_boq_lines(enriched, project_id=project_id), None


@router.get("/projects/{project_id}/engineering/estimate")
def list_project_estimate(project_id: str, token: str = Depends(get_access_token)):
    """Proposed estimate: BOQ lines × provisional unit rates.

    Does not persist. Use POST .../engineering/estimate/generate to store.
    Prefers stored boq_items when present; otherwise builds BOQ from takeoff.
    """
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    boq_lines, warning = _boq_lines_for_project(client, project_id)
    if warning and not boq_lines:
        return {"data": [], "summary": {}, "warning": warning}
    payload = build_estimate_from_boq(boq_lines, project_id=project_id)
    out = {
        "data": payload["lines"],
        "summary": payload["summary"],
        "boq_line_count": len(boq_lines),
    }
    if warning:
        out["warning"] = warning
    return out


@router.post("/projects/{project_id}/engineering/estimate/generate")
def generate_and_persist_estimate(project_id: str, token: str = Depends(get_access_token)):
    """Build proposed estimate from BOQ and insert into estimate_items (if table exists)."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    boq_lines, warning = _boq_lines_for_project(client, project_id)
    if warning and not boq_lines:
        return {"data": [], "summary": {}, "persisted": 0, "warning": warning}
    payload = build_estimate_from_boq(boq_lines, project_id=project_id)
    persisted = persist_estimate_items(client, payload["lines"])
    persist_warning = None
    if payload["lines"] and persisted == 0:
        persist_warning = "estimate_items table is not available yet — apply supabase/estimate_items.sql"
    out = {
        "data": payload["lines"],
        "summary": payload["summary"],
        "persisted": persisted,
        "boq_line_count": len(boq_lines),
    }
    if persist_warning:
        out["warning"] = persist_warning
    elif warning:
        out["warning"] = warning
    return out


@router.get("/projects/{project_id}/estimate/items")
def list_stored_estimate_items(project_id: str, token: str = Depends(get_access_token)):
    """List persisted estimate items for the project."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("estimate_items")
            .select(ESTIMATE_FIELDS)
            .eq("project_id", project_id)
            .order("work_section")
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {
            "data": [],
            "warning": "estimate_items table is not available yet — apply supabase/estimate_items.sql",
        }


@router.get("/projects/{project_id}/engineering/design-to-cost")
def project_design_to_cost(project_id: str, token: str = Depends(get_access_token)):
    """Design-to-cost intelligence from the engineering → BOQ → estimate chain.

    Returns cost drivers, section concentration, Pareto insight, design levers,
    and provisional quantity/rate what-if scenarios. Does not persist.
    """
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    boq_lines, warning = _boq_lines_for_project(client, project_id)
    if warning and not boq_lines:
        return {"data": {}, "warning": warning}
    estimate = build_estimate_from_boq(boq_lines, project_id=project_id)
    intelligence = build_design_to_cost(
        estimate["lines"],
        boq_lines=boq_lines,
        project_id=project_id,
        top_n=5,
    )
    out = {
        "data": intelligence,
        "boq_line_count": len(boq_lines),
        "estimate_line_count": len(estimate["lines"]),
    }
    if warning:
        out["warning"] = warning
    return out
