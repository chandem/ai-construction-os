from fastapi import APIRouter, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .boq import build_boq_lines, persist_boq_items
from .db import supabase
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
