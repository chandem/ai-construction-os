"""Construction OS home routes (Phase 15)."""
import time

from fastapi import APIRouter, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .db import supabase
from .routes import _project_for_member
from .project_data import build_project_summary, build_project_priorities
from .construction_os import (
    MODULE_REGISTRY,
    build_os_snapshot,
    module_status,
    os_summary,
)

router = APIRouter()

# table -> supabase/*.sql hint for operators
TABLE_SQL_HINTS = {
    "engineering_elements": "supabase/engineering_elements.sql",
    "boq_items": "supabase/boq_items.sql",
    "estimate_items": "supabase/estimate_items.sql",
    "tender_packages": "supabase/tender_packages.sql",
    "contract_packages": "supabase/contract_packages.sql",
    "wbs_nodes": "supabase/planning.sql",
    "material_requirements": "supabase/procurement.sql",
    "site_diary_entries": "supabase/field.sql",
    "inspections": "supabase/quality.sql",
    "infrastructure_assets": "supabase/gis.sql",
    "project_risks": "supabase/prediction.sql",
    "integration_connections": "supabase/integrations.sql",
    "ops_queue_jobs": "supabase/hardening.sql",
}


def _looks_like_missing_table(message: str) -> bool:
    text = (message or "").lower()
    markers = (
        "does not exist",
        "could not find the table",
        "schema cache",
        "undefined table",
        "relation",
    )
    return any(marker in text for marker in markers)


def _safe_get(client, table: str, project_id: str, limit: int = 5) -> dict:
    # Supabase/HTTP connections can briefly fail with EAGAIN (Errno 11) under
    # resource pressure. Retry transient failures only; schema and permission
    # errors should surface immediately instead of being misclassified.
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            result = (
                client.table(table)
                .select("*")
                .eq("project_id", project_id)
                .limit(limit)
                .execute()
            )
            return {"data": result.data or [], "table": table}
        except Exception as e:
            last_error = e
            err = str(e)[:300]
            lowered = err.lower()
            transient = any(marker in lowered for marker in (
                "resource temporarily unavailable",
                "errno 11",
                "eagain",
                "timeout",
                "connection reset",
                "readerror",
            ))
            if not transient or attempt == 2:
                break
            time.sleep(0.2 * (attempt + 1))

    err = str(last_error or "Unknown database error")[:300]
    payload: dict = {"data": [], "warning": err, "table": table}
    if _looks_like_missing_table(err):
        sql_hint = TABLE_SQL_HINTS.get(table)
        payload["missing_table"] = table
        payload["warning"] = (
            f"Table '{table}' is not available."
            + (f" Apply {sql_hint} in Supabase SQL editor." if sql_hint else " Apply the matching supabase/*.sql script.")
        )
    return payload


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

    # Primary probe tables per product module (plus BOQ for design readiness).
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
    missing_tables: list[dict] = []
    for mid, table in probes:
        payload = _safe_get(client, table, project_id)
        modules.append(module_status(module_id=mid, payload=payload, error=None))
        if payload.get("missing_table"):
            missing_tables.append(
                {
                    "module": mid,
                    "table": payload["missing_table"],
                    "sql": TABLE_SQL_HINTS.get(payload["missing_table"]),
                    "message": payload.get("warning"),
                }
            )

    # BOQ table is critical for document import + commercial chain; surface separately under design.
    boq_payload = _safe_get(client, "boq_items", project_id)
    if boq_payload.get("missing_table"):
        missing_tables.append(
            {
                "module": "design",
                "table": "boq_items",
                "sql": TABLE_SQL_HINTS.get("boq_items"),
                "message": boq_payload.get("warning"),
            }
        )
        # If design looked empty only because elements table is fine but BOQ schema is missing,
        # still recommend schema apply via ops action (missing_tables drives the note).
    elif boq_payload.get("data") and not any(m["id"] == "design" and m["status"] == "active" for m in modules):
        # Promote design signal when BOQ rows exist even if engineering_elements is empty.
        for i, m in enumerate(modules):
            if m["id"] == "design" and m["status"] == "empty":
                modules[i] = module_status(
                    module_id="design",
                    payload={"data": boq_payload.get("data") or [1]},
                    error=None,
                )
                break

    design = next((m for m in modules if m["id"] == "design"), None)
    modules.append(
        module_status(
            module_id="brain",
            payload={"data": [1]} if design and design["status"] == "active" else {"data": []},
        )
    )

    ops_health = {"status": "unknown"}
    ops_mod = next((m for m in modules if m["id"] == "ops"), None)
    if missing_tables:
        ops_health = {"status": "degraded", "missing_tables": missing_tables}
    elif ops_mod and ops_mod["status"] == "active":
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
    if missing_tables:
        names = ", ".join(sorted({t["table"] for t in missing_tables}))
        snapshot["notes"] = (
            (snapshot.get("notes") or "")
            + f" Missing Supabase table(s): {names}. Apply the matching supabase/*.sql scripts in the Supabase SQL editor, then refresh."
        ).strip()
        # Ensure ops recommended action is present even if module statuses were only "empty".
        actions = list(snapshot.get("recommended_actions") or [])
        if not any("Supabase" in str(a.get("title") or "") for a in actions):
            actions.insert(
                0,
                {
                    "priority": 1,
                    "module": "ops",
                    "title": "Apply Supabase schemas",
                    "detail": f"Missing tables: {names}. Run the SQL files listed under supabase/ for those tables.",
                },
            )
            snapshot["recommended_actions"] = actions

    return {
        "data": snapshot,
        "summary": os_summary(snapshot),
        "registry": MODULE_REGISTRY,
        "setup": {"missing_tables": missing_tables},
    }


@router.get("/projects/{project_id}/executive-summary")
def project_executive_summary(project_id: str, token: str = Depends(get_access_token)):
    """Read-only consolidated summary of project progress, materials, equipment, costs, and risks."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)

    warnings: list[dict] = []
    project_result = None
    last_error: Exception | None = None
    # Supabase/httpx can briefly fail with ReadError while the service is under load.
    # Retry once before returning a clear, recoverable response to the dashboard.
    for attempt in range(2):
        try:
            project_result = (
                client.table("projects")
                .select("id,name,code,status")
                .eq("id", project_id)
                .single()
                .execute()
            )
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.25)

    if last_error is not None:
        raise HTTPException(
            status_code=503,
            detail="Project summary is temporarily unavailable because the database connection failed. Please refresh in a moment.",
        ) from last_error
    if not project_result or not project_result.data:
        return {"data": None, "warnings": [{"message": "Project record is unavailable."}]}

    def rows(table: str, columns: str) -> list[dict]:
        try:
            result = (
                client.table(table)
                .select(columns)
                .eq("project_id", project_id)
                .limit(1000)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            warnings.append({"table": table, "message": str(exc)[:180]})
            return []

    summary = build_project_summary(
        project_result.data,
        rows("activities", "id,name,status,planned_percent,actual_percent"),
        rows("materials", "id,code,name,unit,stock_quantity,reorder_level,supplier"),
        rows("equipment", "id,code,name,equipment_type,status"),
        rows("cost_entries", "id,category,amount,currency,entry_date"),
        rows("project_risks", "id,risk_code,title,level,status"),
    )
    priorities = build_project_priorities(summary)
    return {"data": summary, "priorities": priorities, "warnings": warnings}


@router.get("/os/modules")
def list_os_modules(token: str = Depends(get_access_token)):
    """Product module registry for Construction OS navigation."""
    get_current_user(token)
    return {"data": MODULE_REGISTRY}
