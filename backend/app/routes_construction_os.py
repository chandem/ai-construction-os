"""Construction OS home routes (Phase 15)."""
from fastapi import APIRouter, Depends

from .auth import get_access_token, get_current_user
from .db import supabase
from .routes import _project_for_member
from .construction_os import (
    MODULE_REGISTRY,
    build_os_snapshot,
    module_status,
    os_summary,
)

router = APIRouter()


def _safe_get(client, table: str, project_id: str, limit: int = 5) -> tuple[object, str | None]:
    try:
        result = (
            client.table(table)
            .select("*")
            .eq("project_id", project_id)
            .limit(limit)
            .execute()
        )
        return {"data": result.data or []}, None
    except Exception as e:
        return {"data": [], "warning": str(e)[:200]}, str(e)[:200]


@router.get("/projects/{project_id}/os/snapshot")
def project_os_snapshot(project_id: str, token: str = Depends(get_access_token)):
    """Unified Construction OS snapshot: module readiness + recommended actions."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    name = None
    try:
        prow = client.table("projects").select("id,name").eq("id", project_id).maybe_single().execute()
        if prow.data:
            name = prow.data.get("name")
    except Exception:
        name = None

    probes = [
        ("design", "engineering_elements"),
        ("commercial", "tender_packages"),
        ("planning", "wbs_nodes"),
        ("procurement", "material_requirements"),
        ("field", "site_diary_entries"),
        ("quality", "inspections"),
        ("gis", "infrastructure_assets"),
        ("prediction", "project_risks"),
        ("integrations", "integration_connections"),
        ("ops", "ops_queue_jobs"),
    ]
    modules = []
    for mid, table in probes:
        payload, _err = _safe_get(client, table, project_id)
        modules.append(module_status(module_id=mid, payload=payload, error=None))

    design = next((m for m in modules if m["id"] == "design"), None)
    modules.append(
        module_status(
            module_id="brain",
            payload={"data": [1]} if design and design["status"] == "active" else {"data": []},
        )
    )

    ops_health = {"status": "unknown"}
    ops_mod = next((m for m in modules if m["id"] == "ops"), None)
    if ops_mod and ops_mod["status"] == "active":
        ops_health = {"status": "healthy"}
    elif ops_mod and ops_mod["status"] == "needs_setup":
        ops_health = {"status": "degraded"}

    order = {m["id"]: i for i, m in enumerate(MODULE_REGISTRY)}
    modules.sort(key=lambda m: order.get(m["id"], 99))

    snapshot = build_os_snapshot(
        project_id=project_id,
        project_name=name,
        modules=modules,
        ops_health=ops_health,
    )
    return {"data": snapshot, "summary": os_summary(snapshot), "registry": MODULE_REGISTRY}


@router.get("/os/modules")
def list_os_modules(token: str = Depends(get_access_token)):
    """Product module registry for Construction OS navigation."""
    get_current_user(token)
    return {"data": MODULE_REGISTRY}
