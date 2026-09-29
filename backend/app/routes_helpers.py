"""Shared route helpers for engineering chain."""
from __future__ import annotations

from .boq import build_boq_lines
from .estimate import build_estimate_from_boq
from .quantity_takeoff import enrich_elements

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

def _estimate_lines_for_project(client, project_id: str) -> tuple[list[dict], dict, str | None]:
    """Return (estimate_lines, summary, warning)."""
    boq_lines, warning = _boq_lines_for_project(client, project_id)
    if warning and not boq_lines:
        return [], {}, warning
    payload = build_estimate_from_boq(boq_lines, project_id=project_id)
    return payload["lines"], payload["summary"], warning
