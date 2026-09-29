"""Commercial routes: tender + contracts (Phase 4)."""
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
from .contract import (
    build_contract_from_tender,
    commercial_with_contracts,
    persist_contract_package,
)
from .tender import (
    build_packages_by_section,
    build_tender_package,
    commercial_summary,
    persist_tender_package,
)
from .estimate import build_estimate_from_boq

router = APIRouter()

CONTRACT_PACKAGE_FIELDS = (
    "id,project_id,tender_package_id,contract_code,title,work_section,"
    "contractor_name,status,currency,contract_value,baseline_total,line_count,"
    "source,notes,properties,created_at,updated_at"
)
CONTRACT_ITEM_FIELDS = (
    "id,contract_package_id,project_id,line_no,item_code,work_section,description,"
    "element_type,quantity,unit,unit_rate,amount,currency,tender_item_id,"
    "estimate_item_id,boq_item_id,source_element_ids,source_identifiers,status,"
    "notes,properties,created_at,updated_at"
)

# Phase 4 — Tender & Commercial
# ---------------------------------------------------------------------------

TENDER_PACKAGE_FIELDS = (
    "id,project_id,package_code,title,work_section,status,currency,"
    "baseline_total,line_count,priced_lines,source,notes,properties,"
    "created_at,updated_at"
)

TENDER_ITEM_FIELDS = (
    "id,tender_package_id,project_id,line_no,item_code,work_section,description,"
    "element_type,quantity,unit,unit_rate,amount,currency,estimate_item_id,"
    "boq_item_id,source_element_ids,source_identifiers,status,notes,properties,"
    "created_at,updated_at"
)


@router.get("/projects/{project_id}/commercial/summary")
def project_commercial_summary(project_id: str, token: str = Depends(get_access_token)):
    """Commercial rollup: baseline estimate + tender packages + contracts."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)

    _, estimate_summary, warning = _estimate_lines_for_project(client, project_id)

    packages: list[dict] = []
    try:
        result = (
            client.table("tender_packages")
            .select(TENDER_PACKAGE_FIELDS)
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        packages = result.data or []
    except Exception:
        packages = []

    contracts: list[dict] = []
    try:
        result = (
            client.table("contract_packages")
            .select(CONTRACT_PACKAGE_FIELDS)
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        contracts = result.data or []
    except Exception:
        contracts = []

    summary = commercial_with_contracts(estimate_summary, packages, contracts)
    out = {"data": summary, "packages": packages, "contracts": contracts}
    if warning:
        out["warning"] = warning
    return out


@router.get("/projects/{project_id}/tender/packages")
def list_tender_packages(project_id: str, token: str = Depends(get_access_token)):
    """List stored tender packages for the project."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("tender_packages")
            .select(TENDER_PACKAGE_FIELDS)
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {
            "data": [],
            "warning": "tender_packages table is not available yet — apply supabase/tender_packages.sql",
        }


@router.get("/projects/{project_id}/tender/packages/preview")
def preview_tender_packages(project_id: str, token: str = Depends(get_access_token)):
    """Preview packages split by work section from current estimate (does not persist)."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    lines, summary, warning = _estimate_lines_for_project(client, project_id)
    if warning and not lines:
        return {"data": [], "summary": {}, "warning": warning}
    packages = build_packages_by_section(lines, project_id=project_id)
    preview = []
    for p in packages:
        preview.append(
            {
                "package_code": p.get("package_code"),
                "title": p.get("title"),
                "work_section": p.get("work_section"),
                "status": p.get("status"),
                "currency": p.get("currency"),
                "baseline_total": p.get("baseline_total"),
                "line_count": p.get("line_count"),
                "priced_lines": p.get("priced_lines"),
                "source": p.get("source"),
            }
        )
    out = {
        "data": preview,
        "estimate_summary": summary,
        "commercial": commercial_summary(summary, packages),
    }
    if warning:
        out["warning"] = warning
    return out


@router.post("/projects/{project_id}/tender/packages/generate")
def generate_tender_packages(project_id: str, token: str = Depends(get_access_token)):
    """Build one package per work section from estimate and persist (if tables exist)."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    lines, summary, warning = _estimate_lines_for_project(client, project_id)
    if warning and not lines:
        return {"data": [], "persisted": 0, "summary": {}, "warning": warning}

    packages = build_packages_by_section(lines, project_id=project_id)
    persisted = 0
    for p in packages:
        if persist_tender_package(client, p) is not None:
            persisted += 1

    persist_warning = None
    if packages and persisted == 0:
        persist_warning = "tender_packages table is not available yet — apply supabase/tender_packages.sql"

    headers = []
    for p in packages:
        headers.append(
            {
                "id": p["id"],
                "package_code": p.get("package_code"),
                "title": p.get("title"),
                "work_section": p.get("work_section"),
                "status": p.get("status"),
                "currency": p.get("currency"),
                "baseline_total": p.get("baseline_total"),
                "line_count": p.get("line_count"),
                "priced_lines": p.get("priced_lines"),
            }
        )
    out = {
        "data": headers,
        "persisted": persisted,
        "estimate_summary": summary,
        "commercial": commercial_summary(summary, packages),
    }
    if persist_warning:
        out["warning"] = persist_warning
    elif warning:
        out["warning"] = warning
    return out


@router.get("/projects/{project_id}/tender/packages/{package_id}/items")
def list_tender_package_items(
    project_id: str, package_id: str, token: str = Depends(get_access_token)
):
    """List line items for a tender package."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("tender_items")
            .select(TENDER_ITEM_FIELDS)
            .eq("project_id", project_id)
            .eq("tender_package_id", package_id)
            .order("line_no")
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {
            "data": [],
            "warning": "tender_items table is not available yet — apply supabase/tender_packages.sql",
        }


@router.patch("/projects/{project_id}/tender/packages/{package_id}/status")
def update_tender_package_status(
    project_id: str, package_id: str, token: str = Depends(get_access_token)
):
    """Update package status helper — use PATCH .../packages/{id}?status=ready."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    return {
        "detail": "Pass status as query param: PATCH .../packages/{id}?status=ready",
        "allowed": list(
            ("draft", "ready", "issued", "received", "evaluated", "awarded", "cancelled")
        ),
    }


@router.patch("/projects/{project_id}/tender/packages/{package_id}")
def patch_tender_package(
    project_id: str,
    package_id: str,
    status: str | None = None,
    token: str = Depends(get_access_token),
):
    """Update tender package fields (status via query: ?status=ready)."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    allowed = ("draft", "ready", "issued", "received", "evaluated", "awarded", "cancelled")
    if not status or status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")
    try:
        result = (
            client.table("tender_packages")
            .update({"status": status})
            .eq("id", package_id)
            .eq("project_id", project_id)
            .execute()
        )
        return {"data": (result.data or [None])[0], "status": status}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="tender_packages table is not available yet — apply supabase/tender_packages.sql",
        )


# ---------------------------------------------------------------------------
# Phase 4 Step 17 — Contract packages
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/contracts")
def list_contract_packages(project_id: str, token: str = Depends(get_access_token)):
    """List stored contract packages for the project."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("contract_packages")
            .select(CONTRACT_PACKAGE_FIELDS)
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {
            "data": [],
            "warning": "contract_packages table is not available yet — apply supabase/contract_packages.sql",
        }


@router.post("/projects/{project_id}/tender/packages/{package_id}/contract")
def create_contract_from_tender(
    project_id: str,
    package_id: str,
    contractor_name: str | None = None,
    token: str = Depends(get_access_token),
):
    """Create a draft contract package from a tender package (preferably awarded)."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)

    tender_pkg: dict | None = None
    try:
        result = (
            client.table("tender_packages")
            .select(TENDER_PACKAGE_FIELDS)
            .eq("id", package_id)
            .eq("project_id", project_id)
            .maybe_single()
            .execute()
        )
        tender_pkg = result.data
    except Exception:
        tender_pkg = None

    if not tender_pkg:
        raise HTTPException(
            status_code=404,
            detail="Tender package not found (or tender_packages table not applied)",
        )

    items: list[dict] = []
    try:
        items_result = (
            client.table("tender_items")
            .select(TENDER_ITEM_FIELDS)
            .eq("tender_package_id", package_id)
            .eq("project_id", project_id)
            .order("line_no")
            .execute()
        )
        items = items_result.data or []
    except Exception:
        items = []

    contract = build_contract_from_tender(
        tender_pkg,
        items,
        project_id=project_id,
        contractor_name=contractor_name,
    )
    persisted_header = persist_contract_package(client, contract)
    persist_warning = None
    if persisted_header is None:
        persist_warning = "contract_packages table is not available yet — apply supabase/contract_packages.sql"

    header = {
        "id": contract["id"],
        "contract_code": contract.get("contract_code"),
        "title": contract.get("title"),
        "work_section": contract.get("work_section"),
        "contractor_name": contract.get("contractor_name"),
        "status": contract.get("status"),
        "currency": contract.get("currency"),
        "contract_value": contract.get("contract_value"),
        "baseline_total": contract.get("baseline_total"),
        "line_count": contract.get("line_count"),
        "tender_package_id": contract.get("tender_package_id"),
        "persisted": persisted_header is not None,
    }
    out = {"data": header, "item_count": len(contract.get("items") or [])}
    if persist_warning:
        out["warning"] = persist_warning
    return out


@router.get("/projects/{project_id}/contracts/{contract_id}/items")
def list_contract_items(
    project_id: str, contract_id: str, token: str = Depends(get_access_token)
):
    """List line items for a contract package."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = (
            client.table("contract_items")
            .select(CONTRACT_ITEM_FIELDS)
            .eq("project_id", project_id)
            .eq("contract_package_id", contract_id)
            .order("line_no")
            .execute()
        )
        return {"data": result.data or []}
    except Exception:
        return {
            "data": [],
            "warning": "contract_items table is not available yet — apply supabase/contract_packages.sql",
        }


@router.patch("/projects/{project_id}/contracts/{contract_id}")
def patch_contract_package(
    project_id: str,
    contract_id: str,
    status: str | None = None,
    token: str = Depends(get_access_token),
):
    """Update contract status via query: ?status=executed."""
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    _project_for_member(project_id, user["id"], client)
    allowed = (
        "draft",
        "under_review",
        "executed",
        "active",
        "completed",
        "terminated",
        "cancelled",
    )
    if not status or status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")
    try:
        result = (
            client.table("contract_packages")
            .update({"status": status})
            .eq("id", contract_id)
            .eq("project_id", project_id)
            .execute()
        )
        return {"data": (result.data or [None])[0], "status": status}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="contract_packages table is not available yet — apply supabase/contract_packages.sql",
        )
