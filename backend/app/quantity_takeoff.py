"""Derive construction quantities from engineering elements.

Rules are deterministic and evidence-based. Missing dimensions never invent numbers.
Results are proposed takeoff values for professional review, not certified BOQ items.
"""

from __future__ import annotations

import re
from typing import Any

DEFAULT_UNITS = {
    "column": "nos",
    "beam": "m",
    "slab": "m2",
    "wall": "m2",
    "foundation": "m3",
    "footing": "m3",
    "road": "m2",
    "culvert": "m",
    "pipe": "m",
    "room": "m2",
    "equipment": "nos",
    "stair": "nos",
    "opening": "m2",
    "retaining_wall": "m2",
    "pavement": "m2",
    "drainage": "m",
    "other": None,
}

DIM_KEYS = {
    "length": ("length", "len", "l", "span", "long"),
    "width": ("width", "w", "breadth", "b"),
    "height": ("height", "h", "depth", "d", "thickness", "thk", "t"),
    "diameter": ("diameter", "dia", "dn", "od", "id"),
    "area": ("area", "a"),
    "volume": ("volume", "vol", "v"),
    "count": ("count", "qty", "quantity", "nos", "number"),
}


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower().replace(",", "")
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _pick_dim(dimensions: dict[str, Any], *groups: str) -> float | None:
    if not isinstance(dimensions, dict):
        return None
    lowered = {str(k).lower().strip(): v for k, v in dimensions.items()}
    for group in groups:
        for key in DIM_KEYS.get(group, ()):
            if key in lowered:
                val = _as_float(lowered[key])
                if val is not None:
                    return val
    for group in groups:
        for k, v in lowered.items():
            if group in k.replace("_", " "):
                val = _as_float(v)
                if val is not None:
                    return val
    return None


def _round_qty(value: float) -> float:
    if abs(value) >= 100:
        return round(value, 1)
    if abs(value) >= 10:
        return round(value, 2)
    return round(value, 3)


def derive_quantity(
    element_type: str,
    *,
    quantity: float | None = None,
    unit: str | None = None,
    dimensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return quantity, unit, method, and confidence for one element."""
    dims = dimensions or {}
    explicit_qty = _as_float(quantity)
    if explicit_qty is not None:
        return {
            "quantity": explicit_qty,
            "unit": (unit or DEFAULT_UNITS.get(element_type) or "nos"),
            "method": "explicit",
            "confidence": 0.9,
            "notes": "Quantity provided by source extraction",
        }

    vol = _pick_dim(dims, "volume")
    if vol is not None:
        return {
            "quantity": _round_qty(vol),
            "unit": unit or "m3",
            "method": "dimension_volume",
            "confidence": 0.85,
            "notes": "Volume taken from dimensions",
        }

    area = _pick_dim(dims, "area")
    if area is not None:
        return {
            "quantity": _round_qty(area),
            "unit": unit or "m2",
            "method": "dimension_area",
            "confidence": 0.85,
            "notes": "Area taken from dimensions",
        }

    count = _pick_dim(dims, "count")
    if count is not None:
        return {
            "quantity": count,
            "unit": unit or "nos",
            "method": "dimension_count",
            "confidence": 0.8,
            "notes": "Count taken from dimensions",
        }

    length = _pick_dim(dims, "length")
    width = _pick_dim(dims, "width")
    height = _pick_dim(dims, "height")
    diameter = _pick_dim(dims, "diameter")

    et = (element_type or "other").lower()

    if et in {"foundation", "footing"} and length and width and height:
        return {
            "quantity": _round_qty(length * width * height),
            "unit": "m3",
            "method": "l_w_h_volume",
            "confidence": 0.75,
            "notes": "Volume = length × width × depth/height",
        }

    if et == "column" and length and width and height:
        return {
            "quantity": _round_qty(length * width * height),
            "unit": "m3",
            "method": "l_w_h_volume",
            "confidence": 0.7,
            "notes": "Column volume = section × height",
        }

    if et == "beam" and length and width and height:
        return {
            "quantity": _round_qty(length * width * height),
            "unit": "m3",
            "method": "l_w_h_volume",
            "confidence": 0.7,
            "notes": "Beam volume = length × breadth × depth",
        }

    if et in {"slab", "wall", "retaining_wall", "pavement"} and length and width and height:
        return {
            "quantity": _round_qty(length * width),
            "unit": "m2",
            "method": "l_w_area",
            "confidence": 0.75,
            "notes": f"Area = length × width; thickness={height}",
            "volume_m3": _round_qty(length * width * height),
        }

    if et in {"slab", "room", "opening", "road", "pavement", "wall", "retaining_wall"}:
        if length and width:
            return {
                "quantity": _round_qty(length * width),
                "unit": "m2",
                "method": "l_w_area",
                "confidence": 0.75,
                "notes": "Area = length × width",
            }
        if length and height and et in {"wall", "retaining_wall", "opening"}:
            return {
                "quantity": _round_qty(length * height),
                "unit": "m2",
                "method": "l_h_area",
                "confidence": 0.75,
                "notes": "Area = length × height",
            }

    if et in {"beam", "pipe", "culvert", "drainage", "road"} and length is not None:
        return {
            "quantity": _round_qty(length),
            "unit": "m",
            "method": "length",
            "confidence": 0.8,
            "notes": "Length from dimensions",
        }

    if et == "pipe" and diameter is not None and length is None:
        return {
            "quantity": None,
            "unit": None,
            "method": "insufficient",
            "confidence": 0.0,
            "notes": "Diameter present but length missing",
        }

    if et in {"column", "equipment", "stair", "culvert"}:
        return {
            "quantity": 1.0,
            "unit": "nos",
            "method": "count_fallback",
            "confidence": 0.4,
            "notes": "No measurable dimensions; assumed single item",
        }

    return {
        "quantity": None,
        "unit": unit,
        "method": "insufficient",
        "confidence": 0.0,
        "notes": "Not enough dimensions to derive quantity",
    }


def enrich_element_with_quantity(row: dict[str, Any]) -> dict[str, Any]:
    result = derive_quantity(
        str(row.get("element_type") or "other"),
        quantity=row.get("quantity"),
        unit=row.get("unit"),
        dimensions=row.get("dimensions") or {},
    )
    if result.get("quantity") is not None and row.get("quantity") is None:
        row["quantity"] = result["quantity"]
    if result.get("unit") and not row.get("unit"):
        row["unit"] = result["unit"]

    props = dict(row.get("properties") or {})
    props["quantity_method"] = result.get("method")
    props["quantity_confidence"] = result.get("confidence")
    props["quantity_notes"] = result.get("notes")
    if "volume_m3" in result:
        props["volume_m3"] = result["volume_m3"]
    row["properties"] = props
    return row


def enrich_elements(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_element_with_quantity(dict(r)) for r in rows]


def summarize_quantities(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        qty = _as_float(row.get("quantity"))
        if qty is None:
            continue
        et = str(row.get("element_type") or "other")
        unit = str(row.get("unit") or "nos")
        key = (et, unit)
        if key not in buckets:
            buckets[key] = {
                "element_type": et,
                "unit": unit,
                "total_quantity": 0.0,
                "item_count": 0,
                "identifiers": [],
            }
        buckets[key]["total_quantity"] = _round_qty(buckets[key]["total_quantity"] + qty)
        buckets[key]["item_count"] += 1
        ident = row.get("identifier") or row.get("name")
        if ident and len(buckets[key]["identifiers"]) < 20:
            buckets[key]["identifiers"].append(ident)
    return sorted(buckets.values(), key=lambda x: (x["element_type"], x["unit"]))
