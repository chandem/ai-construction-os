from fastapi import APIRouter, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .db import supabase
from .routes import _project_for_member

router = APIRouter(prefix="/api/v1")

ELEMENT_FIELDS = (
    "id,project_id,design_asset_id,document_id,element_type,name,identifier,"
    "discipline,level,location_description,quantity,unit,dimensions,materials,"
    "properties,source,evidence,confidence,status,created_at,updated_at"
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
