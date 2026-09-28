"""BOQ linkage: map engineering quantity takeoffs to proposed Bill of Quantities lines.

Proposed BOQ items are for professional review. They are not certified tender quantities.
Element type + unit drive a work-section code and description template; quantities
are aggregated from takeoff. Source element ids are retained for traceability.
"""

from __future__ import annotations

from typing import Any

from .quantity_takeoff import _as_float, _round_qty, summarize_quantities

# Canonical mapping: element_type → (work_section, item_code_prefix, description_template, default_unit)
# Codes follow a simple construction work-breakdown style suitable for later CESMM/SMM alignment.
ELEMENT_BOQ_MAP: dict[str, dict[str, str]] = {
    "foundation": {
        "work_section": "Concrete works — Foundations",
        "item_code": "C.1.1",
        "description": "Mass / reinforced concrete foundations",
        "default_unit": "m3",
    },
    "footing": {
        "work_section": "Concrete works — Foundations",
        "item_code": "C.1.2",
        "description": "Isolated / strip footings",
        "default_unit": "m3",
    },
    "column": {
        "work_section": "Concrete works — Superstructure",
        "item_code": "C.2.1",
        "description": "Reinforced concrete columns",
        "default_unit": "m3",
    },
    "beam": {
        "work_section": "Concrete works — Superstructure",
        "item_code": "C.2.2",
        "description": "Reinforced concrete beams",
        "default_unit": "m3",
    },
    "slab": {
        "work_section": "Concrete works — Superstructure",
        "item_code": "C.2.3",
        "description": "Reinforced concrete slabs",
        "default_unit": "m2",
    },
    "wall": {
        "work_section": "Concrete / Masonry — Walls",
        "item_code": "C.3.1",
        "description": "Structural / shear walls",
        "default_unit": "m2",
    },
    "retaining_wall": {
        "work_section": "Concrete works — Earth retaining",
        "item_code": "C.3.2",
        "description": "Retaining walls",
        "default_unit": "m2",
    },
    "stair": {
        "work_section": "Concrete works — Superstructure",
        "item_code": "C.2.4",
        "description": "Staircases / steps",
        "default_unit": "nos",
    },
    "opening": {
        "work_section": "Builders work — Openings",
        "item_code": "B.1.1",
        "description": "Openings (doors / windows) — area",
        "default_unit": "m2",
    },
    "room": {
        "work_section": "Space / finishes reference",
        "item_code": "S.1.1",
        "description": "Room / floor area (reference)",
        "default_unit": "m2",
    },
    "pipe": {
        "work_section": "Drainage & services — Pipes",
        "item_code": "D.1.1",
        "description": "Pipes / pipelines",
        "default_unit": "m",
    },
    "drainage": {
        "work_section": "Drainage & services",
        "item_code": "D.1.2",
        "description": "Drainage runs",
        "default_unit": "m",
    },
    "culvert": {
        "work_section": "Drainage & civil — Culverts",
        "item_code": "D.2.1",
        "description": "Culverts",
        "default_unit": "m",
    },
    "road": {
        "work_section": "Roads & pavements",
        "item_code": "R.1.1",
        "description": "Road / carriageway",
        "default_unit": "m2",
    },
    "pavement": {
        "work_section": "Roads & pavements",
        "item_code": "R.1.2",
        "description": "Pavement / hardstanding",
        "default_unit": "m2",
    },
    "equipment": {
        "work_section": "Equipment / plant items",
        "item_code": "E.1.1",
        "description": "Equipment items",
        "default_unit": "nos",
    },
    "other": {
        "work_section": "General / unclassified",
        "item_code": "G.1.1",
        "description": "Other engineering elements",
        "default_unit": "nos",
    },
}


def boq_template_for(element_type: str) -> dict[str, str]:
    et = (element_type or "other").lower().strip()
    return dict(ELEMENT_BOQ_MAP.get(et, ELEMENT_BOQ_MAP["other"]))


def build_boq_lines(
    elements: list[dict[str, Any]],
    *,
    project_id: str,
    source: str = "quantity_takeoff",
) -> list[dict[str, Any]]:
    """Aggregate engineering elements into proposed BOQ line items.

    Grouping key: (element_type, unit). One line per group.
    Source element ids are listed for audit trail (capped).
    """
    summary = summarize_quantities(elements)
    # Build element-id lists per (type, unit)
    id_buckets: dict[tuple[str, str], list[str]] = {}
    for row in elements:
        qty = _as_float(row.get("quantity"))
        if qty is None:
            continue
        et = str(row.get("element_type") or "other")
        unit = str(row.get("unit") or "nos")
        key = (et, unit)
        eid = row.get("id")
        id_buckets.setdefault(key, [])
        if eid and len(id_buckets[key]) < 50:
            id_buckets[key].append(str(eid))

    lines: list[dict[str, Any]] = []
    for i, bucket in enumerate(summary, start=1):
        et = bucket["element_type"]
        unit = bucket["unit"]
        template = boq_template_for(et)
        # Prefer measured unit from takeoff; fall back to template default
        measured_unit = unit or template["default_unit"]
        item_code = f"{template['item_code']}.{i:02d}"
        key = (et, unit)
        source_ids = id_buckets.get(key, [])
        lines.append(
            {
                "project_id": project_id,
                "item_code": item_code,
                "work_section": template["work_section"],
                "description": template["description"],
                "element_type": et,
                "quantity": _round_qty(float(bucket["total_quantity"])),
                "unit": measured_unit,
                "item_count": bucket["item_count"],
                "source_element_ids": source_ids,
                "source_identifiers": bucket.get("identifiers") or [],
                "source": source,
                "status": "proposed",
                "notes": (
                    f"Aggregated from {bucket['item_count']} engineering element(s); "
                    "proposed takeoff — review before use as tender BOQ"
                ),
                "properties": {
                    "quantity_basis": "engineering_elements",
                    "template_code": template["item_code"],
                },
            }
        )
    # Stable order by work section then item code
    lines.sort(key=lambda x: (x["work_section"], x["item_code"]))
    return lines


def persist_boq_items(client, rows: list[dict[str, Any]]) -> int:
    """Insert proposed BOQ items. No-op if table missing."""
    if not rows:
        return 0
    # Strip fields that may not match DB columns on older schemas
    payload = []
    for r in rows:
        payload.append(
            {
                "project_id": r["project_id"],
                "item_code": r.get("item_code"),
                "work_section": r.get("work_section"),
                "description": r.get("description"),
                "element_type": r.get("element_type"),
                "quantity": r.get("quantity"),
                "unit": r.get("unit"),
                "item_count": r.get("item_count"),
                "source_element_ids": r.get("source_element_ids") or [],
                "source_identifiers": r.get("source_identifiers") or [],
                "source": r.get("source") or "quantity_takeoff",
                "status": r.get("status") or "proposed",
                "notes": r.get("notes"),
                "properties": r.get("properties") or {},
            }
        )
    try:
        result = client.table("boq_items").insert(payload).execute()
        return len(result.data or payload)
    except Exception:
        return 0
