"""Estimate linkage: attach provisional unit rates to BOQ lines and compute costs.

Rates are indicative defaults for design-to-cost exploration. They are not market
prices, tender rates, or certified estimates. Users must replace with project rates.
"""

from __future__ import annotations

from typing import Any

from .quantity_takeoff import _as_float, _round_qty

# Provisional unit rates (currency-neutral numeric; default currency USD).
# Keyed by element_type. Values are per default measured unit of the BOQ line.
# Source note: illustrative mid-range order-of-magnitude for early cost intelligence only.
PROVISIONAL_UNIT_RATES: dict[str, dict[str, Any]] = {
    "foundation": {"rate": 180.0, "unit": "m3", "basis": "concrete foundations incl. formwork allowance"},
    "footing": {"rate": 200.0, "unit": "m3", "basis": "isolated/strip footings"},
    "column": {"rate": 280.0, "unit": "m3", "basis": "RC columns"},
    "beam": {"rate": 260.0, "unit": "m3", "basis": "RC beams"},
    "slab": {"rate": 95.0, "unit": "m2", "basis": "RC slab (area-based provisional)"},
    "wall": {"rate": 120.0, "unit": "m2", "basis": "structural/shear wall"},
    "retaining_wall": {"rate": 160.0, "unit": "m2", "basis": "retaining wall"},
    "stair": {"rate": 2500.0, "unit": "nos", "basis": "staircase unit allowance"},
    "opening": {"rate": 80.0, "unit": "m2", "basis": "opening formation allowance"},
    "room": {"rate": 25.0, "unit": "m2", "basis": "floor area reference only"},
    "pipe": {"rate": 45.0, "unit": "m", "basis": "pipe/pipeline run"},
    "drainage": {"rate": 55.0, "unit": "m", "basis": "drainage run"},
    "culvert": {"rate": 400.0, "unit": "m", "basis": "culvert length"},
    "road": {"rate": 85.0, "unit": "m2", "basis": "road/carriageway"},
    "pavement": {"rate": 70.0, "unit": "m2", "basis": "pavement/hardstanding"},
    "equipment": {"rate": 5000.0, "unit": "nos", "basis": "equipment item allowance"},
    "other": {"rate": 50.0, "unit": "nos", "basis": "unclassified provisional"},
}

DEFAULT_CURRENCY = "USD"
RATE_SOURCE = "provisional_default"


def rate_for(element_type: str, unit: str | None = None) -> dict[str, Any]:
    """Return provisional rate metadata for an element type."""
    et = (element_type or "other").lower().strip()
    entry = PROVISIONAL_UNIT_RATES.get(et, PROVISIONAL_UNIT_RATES["other"])
    return {
        "unit_rate": float(entry["rate"]),
        "rate_unit": entry["unit"],
        "rate_basis": entry["basis"],
        "rate_source": RATE_SOURCE,
        "currency": DEFAULT_CURRENCY,
        "measured_unit": unit or entry["unit"],
        "unit_match": (unit or entry["unit"]).lower() == str(entry["unit"]).lower(),
    }


def _line_amount(quantity: float | None, unit_rate: float) -> float | None:
    qty = _as_float(quantity)
    if qty is None:
        return None
    return _round_qty(qty * unit_rate)


def apply_rates_to_boq_lines(
    boq_lines: list[dict[str, Any]],
    *,
    project_id: str,
    currency: str = DEFAULT_CURRENCY,
    rate_overrides: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Attach unit rates and line amounts to BOQ lines → estimate lines.

    rate_overrides: optional map of element_type → unit_rate to replace defaults.
    """
    overrides = rate_overrides or {}
    lines: list[dict[str, Any]] = []
    for row in boq_lines:
        et = str(row.get("element_type") or "other")
        unit = row.get("unit")
        meta = rate_for(et, unit)
        if et in overrides:
            unit_rate = float(overrides[et])
            rate_source = "override"
        else:
            unit_rate = meta["unit_rate"]
            rate_source = meta["rate_source"]
        qty = _as_float(row.get("quantity"))
        amount = _line_amount(qty, unit_rate)
        props = dict(row.get("properties") or {})
        props["rate_basis"] = meta["rate_basis"]
        props["rate_unit_expected"] = meta["rate_unit"]
        props["unit_match"] = meta["unit_match"]
        props["estimate_note"] = (
            "Provisional rate for design-to-cost exploration only — "
            "replace with project/tender rates before use as an estimate"
        )
        lines.append(
            {
                "project_id": project_id,
                "boq_item_id": row.get("id"),
                "item_code": row.get("item_code"),
                "work_section": row.get("work_section"),
                "description": row.get("description"),
                "element_type": et,
                "quantity": qty,
                "unit": unit,
                "unit_rate": unit_rate,
                "amount": amount,
                "currency": currency,
                "rate_source": rate_source,
                "item_count": row.get("item_count"),
                "source_element_ids": row.get("source_element_ids") or [],
                "source_identifiers": row.get("source_identifiers") or [],
                "source": row.get("source") or "boq",
                "status": "proposed",
                "notes": row.get("notes"),
                "properties": props,
            }
        )
    lines.sort(key=lambda x: (x.get("work_section") or "", x.get("item_code") or ""))
    return lines


def summarize_estimate(lines: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate estimate totals by work section and overall."""
    by_section: dict[str, dict[str, Any]] = {}
    total = 0.0
    priced = 0
    unpriced = 0
    currency = DEFAULT_CURRENCY
    for line in lines:
        amount = _as_float(line.get("amount"))
        section = str(line.get("work_section") or "General")
        if line.get("currency"):
            currency = str(line["currency"])
        if section not in by_section:
            by_section[section] = {
                "work_section": section,
                "line_count": 0,
                "total_amount": 0.0,
            }
        by_section[section]["line_count"] += 1
        if amount is not None:
            by_section[section]["total_amount"] = _round_qty(
                by_section[section]["total_amount"] + amount
            )
            total = _round_qty(total + amount)
            priced += 1
        else:
            unpriced += 1
    sections = sorted(by_section.values(), key=lambda x: x["work_section"])
    for s in sections:
        s["total_amount"] = _round_qty(s["total_amount"])
    return {
        "currency": currency,
        "total_amount": _round_qty(total),
        "line_count": len(lines),
        "priced_lines": priced,
        "unpriced_lines": unpriced,
        "by_work_section": sections,
        "rate_disclaimer": (
            "Amounts use provisional default unit rates for design-to-cost "
            "exploration only. Not a tender estimate."
        ),
    }


def build_estimate_from_boq(
    boq_lines: list[dict[str, Any]],
    *,
    project_id: str,
    currency: str = DEFAULT_CURRENCY,
    rate_overrides: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Full estimate payload: lines + summary."""
    lines = apply_rates_to_boq_lines(
        boq_lines,
        project_id=project_id,
        currency=currency,
        rate_overrides=rate_overrides,
    )
    summary = summarize_estimate(lines)
    return {"lines": lines, "summary": summary}


def persist_estimate_items(client, rows: list[dict[str, Any]]) -> int:
    """Insert proposed estimate lines. No-op if table missing."""
    if not rows:
        return 0
    payload = []
    for r in rows:
        payload.append(
            {
                "project_id": r["project_id"],
                "boq_item_id": r.get("boq_item_id"),
                "item_code": r.get("item_code"),
                "work_section": r.get("work_section"),
                "description": r.get("description"),
                "element_type": r.get("element_type"),
                "quantity": r.get("quantity"),
                "unit": r.get("unit"),
                "unit_rate": r.get("unit_rate"),
                "amount": r.get("amount"),
                "currency": r.get("currency") or DEFAULT_CURRENCY,
                "rate_source": r.get("rate_source") or RATE_SOURCE,
                "item_count": r.get("item_count"),
                "source_element_ids": r.get("source_element_ids") or [],
                "source_identifiers": r.get("source_identifiers") or [],
                "source": r.get("source") or "boq",
                "status": r.get("status") or "proposed",
                "notes": r.get("notes"),
                "properties": r.get("properties") or {},
            }
        )
    try:
        result = client.table("estimate_items").insert(payload).execute()
        return len(result.data or payload)
    except Exception:
        return 0
