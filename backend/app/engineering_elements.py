from __future__ import annotations

from typing import Any

ELEMENT_TYPES = {
    "column",
    "beam",
    "slab",
    "wall",
    "foundation",
    "footing",
    "road",
    "culvert",
    "pipe",
    "room",
    "equipment",
    "stair",
    "opening",
    "retaining_wall",
    "pavement",
    "drainage",
    "other",
}

ALIASES = {
    "columns": "column",
    "col": "column",
    "beams": "beam",
    "girder": "beam",
    "slabs": "slab",
    "deck": "slab",
    "walls": "wall",
    "shear wall": "wall",
    "foundations": "foundation",
    "footing": "footing",
    "footings": "footing",
    "pile": "foundation",
    "piles": "foundation",
    "roadway": "road",
    "carriageway": "road",
    "culverts": "culvert",
    "pipes": "pipe",
    "pipeline": "pipe",
    "rooms": "room",
    "space": "room",
    "equipment item": "equipment",
    "stairs": "stair",
    "staircase": "stair",
    "opening": "opening",
    "door": "opening",
    "window": "opening",
    "retaining wall": "retaining_wall",
    "pavement": "pavement",
    "drain": "drainage",
    "drainage": "drainage",
}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_element_type(raw: Any) -> str:
    text = _clean_text(raw)
    if not text:
        return "other"
    key = text.lower().replace("-", " ").replace("_", " ").strip()
    if key in ELEMENT_TYPES:
        return key
    if key in ALIASES:
        return ALIASES[key]
    for alias, mapped in ALIASES.items():
        if alias in key:
            return mapped
    for known in ELEMENT_TYPES:
        if known.replace("_", " ") in key:
            return known
    return "other"


def _from_string(item: str) -> dict[str, Any]:
    name = item.strip()
    return {
        "element_type": classify_element_type(name),
        "name": name,
        "identifier": None,
        "location_description": None,
        "quantity": None,
        "unit": None,
        "dimensions": {},
        "materials": [],
        "properties": {},
        "evidence": name,
        "confidence": None,
    }


def _from_mapping(item: dict[str, Any]) -> dict[str, Any]:
    element_type = classify_element_type(
        item.get("element_type") or item.get("type") or item.get("kind") or item.get("name")
    )
    dimensions = item.get("dimensions") if isinstance(item.get("dimensions"), dict) else {}
    materials = item.get("materials") if isinstance(item.get("materials"), list) else []
    if item.get("material") and item.get("material") not in materials:
        materials = [*materials, item.get("material")]
    properties = item.get("properties") if isinstance(item.get("properties"), dict) else {}
    return {
        "element_type": element_type,
        "name": _clean_text(item.get("name") or item.get("title") or item.get("description")),
        "identifier": _clean_text(item.get("identifier") or item.get("mark") or item.get("tag") or item.get("id")),
        "level": _clean_text(item.get("level") or item.get("storey") or item.get("floor")),
        "location_description": _clean_text(item.get("location_description") or item.get("location")),
        "quantity": _as_float(item.get("quantity") or item.get("count")),
        "unit": _clean_text(item.get("unit")),
        "dimensions": dimensions,
        "materials": [str(m).strip() for m in materials if str(m).strip()],
        "properties": properties,
        "evidence": _clean_text(item.get("evidence") or item.get("source_text")),
        "confidence": _as_float(item.get("confidence")),
    }


def normalize_engineering_elements(
    raw_elements: Any,
    *,
    project_id: str,
    design_asset_id: str | None = None,
    document_id: str | None = None,
    discipline: str | None = None,
    source: str = "ai_extraction",
) -> list[dict[str, Any]]:
    if not raw_elements:
        return []
    if isinstance(raw_elements, dict):
        raw_list = raw_elements.get("elements") or raw_elements.get("items") or [raw_elements]
    elif isinstance(raw_elements, list):
        raw_list = raw_elements
    else:
        raw_list = [raw_elements]

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for item in raw_list:
        if isinstance(item, str):
            parsed = _from_string(item)
        elif isinstance(item, dict):
            parsed = _from_mapping(item)
        else:
            continue
        name = parsed.get("name")
        identifier = parsed.get("identifier")
        if not name and not identifier:
            continue
        key = (parsed["element_type"], identifier, name)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "project_id": project_id,
                "design_asset_id": design_asset_id,
                "document_id": document_id,
                "element_type": parsed["element_type"],
                "name": name,
                "identifier": identifier,
                "discipline": _clean_text(discipline),
                "level": parsed.get("level"),
                "location_description": parsed.get("location_description"),
                "quantity": parsed.get("quantity"),
                "unit": parsed.get("unit"),
                "dimensions": parsed.get("dimensions") or {},
                "materials": parsed.get("materials") or [],
                "properties": parsed.get("properties") or {},
                "source": source,
                "evidence": parsed.get("evidence"),
                "confidence": parsed.get("confidence"),
                "status": "proposed",
            }
        )
    return rows


def persist_engineering_elements(client, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    try:
        result = client.table("engineering_elements").insert(rows).execute()
        return len(result.data or rows)
    except Exception:
        # Table may not exist yet in older schemas; document processing must still complete.
        return 0
