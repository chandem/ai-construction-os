"""Normalize extracted BOQ rows for review and spreadsheet export.

This module is deliberately deterministic: it does not call an AI model or invent
missing values. Original extracted values are preserved alongside calculated checks.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def _number(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"null", "none", "n/a", "-", "—"}:
        return None
    # Allow currency symbols and parenthesized negatives in common BOQ formats.
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    for symbol in ("ETB", "USD", "EUR", "GBP", "Birr", "ብር", "$", "€", "£"):
        text = text.replace(symbol, "")
    text = text.strip()
    try:
        result = Decimal(text)
        return -result if negative else result
    except InvalidOperation:
        return None


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _round(value: Decimal | None) -> float | None:
    return round(float(value), 2) if value is not None else None


def normalize_boq_extraction(extraction: dict[str, Any] | None) -> dict[str, Any]:
    """Return a normalized BOQ analysis for document extraction JSON."""
    extraction = extraction if isinstance(extraction, dict) else {}
    data = extraction.get("data")
    data = data if isinstance(data, dict) else {}
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raw_items = data.get("boq_items")
    if not isinstance(raw_items, list):
        raw_items = []

    rows: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []
    stated_total = Decimal("0")
    calculated_total = Decimal("0")
    stated_total_count = 0
    calculated_total_count = 0

    for index, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            flags.append({"row": index, "issue": "invalid_item_shape"})
            continue
        code = _first(raw, "code", "item_number", "item_no", "item_code", "number")
        description = _first(raw, "description", "item_description", "name")
        unit = _first(raw, "unit", "uom", "unit_of_measure")
        quantity = _number(_first(raw, "quantity", "qty"))
        rate = _number(_first(raw, "rate", "unit_rate", "unit_price", "price"))
        amount = _number(_first(raw, "amount", "total_amount", "line_total", "total"))
        calculated = quantity * rate if quantity is not None and rate is not None else None
        discrepancy = (
            amount - calculated
            if amount is not None and calculated is not None
            else None
        )
        row_flags = []
        if not description:
            row_flags.append("missing_description")
        if quantity is None:
            row_flags.append("missing_quantity")
        elif quantity < 0:
            row_flags.append("negative_quantity")
        if rate is None:
            row_flags.append("missing_rate")
        elif rate < 0:
            row_flags.append("negative_rate")
        if amount is None:
            row_flags.append("missing_stated_amount")
        if discrepancy is not None and abs(discrepancy) > Decimal("0.02"):
            row_flags.append("amount_mismatch")
        if row_flags:
            flags.append({"row": index, "code": code, "description": description, "issues": row_flags})

        if amount is not None:
            stated_total += amount
            stated_total_count += 1
        if calculated is not None:
            calculated_total += calculated
            calculated_total_count += 1

        rows.append({
            "row_number": index,
            "code": str(code) if code is not None else None,
            "description": str(description) if description is not None else "",
            "unit": str(unit) if unit is not None else None,
            "quantity": _round(quantity),
            "rate": _round(rate),
            "stated_amount": _round(amount),
            "calculated_amount": _round(calculated),
            "difference": _round(discrepancy),
            "work_section": _first(raw, "work_section", "section", "category"),
            "issues": row_flags,
        })

    return {
        "document_type": extraction.get("document_type"),
        "summary": extraction.get("summary") or "",
        "item_count": len(rows),
        "rows": rows,
        "stated_total": _round(stated_total) if stated_total_count else None,
        "calculated_total": _round(calculated_total) if calculated_total_count else None,
        "flag_count": len(flags),
        "quality_flags": flags[:200],
        "note": (
            "Calculated amounts are quantity × rate where both values exist. "
            "Stated amounts are preserved from extraction. Differences are review flags, "
            "not proof of an error; verify against the original BOQ and approved contract."
        ),
    }
