from fastapi import APIRouter, Depends
from .auth import get_access_token, get_current_user
from .db import supabase

router = APIRouter(prefix="/api/v1")

@router.get("/auth/me")
def me(token: str = Depends(get_access_token)):
    return get_current_user(token)

@router.get("/projects")
def list_projects(token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    memberships = client.table("organization_members").select("organization_id").eq("user_id", user["id"]).execute()
    org_ids = [row["organization_id"] for row in (memberships.data or [])]
    if not org_ids:
        return {"data": []}
    result = client.table("projects").select("*").in_("organization_id", org_ids).order("created_at", desc=True).execute()
    return {"data": result.data or []}
