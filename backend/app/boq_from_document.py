"""Import structured BOQ lines from AI document extractions into boq_items."""

from __future__ import annotations

from typing import Any


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _item_fields(raw: dict[str, Any]) -> dict[str, Any]:
    code = raw.get("code") or raw.get("item_code") or raw.get("itemCode")
    description = raw.get("description") or raw.get("desc") or raw.get("item")
    unit = raw.get("unit") or raw.get("uom")
    quantity = _as_float(raw.get("quantity") if raw.get("quantity") is not None else raw.get("qty"))
    rate = _as_float(raw.get("rate") if raw.get("rate") is not None else raw.get("unit_rate"))
    amount = _as_float(raw.get("amount") if raw.get("amount") is not None else raw.get("total"))
    work_section = raw.get("work_section") or raw.get("section") or raw.get("bill") or "Imported BOQ"

    if amount is None and quantity is not None and rate is not None:
        amount = quantity * rate

    return {
        "item_code": str(code).strip() if code is not None else None,
        "work_section": str(work_section).strip() if work_section else "Imported BOQ",
        "description": str(description).strip() if description else None,
        "quantity": quantity,
        "unit": str(unit).strip() if unit else None,
        "rate": rate,
        "amount": amount,
    }


def build_boq_rows_from_extraction(
    *,
    project_id: str,
    document_id: str,
    extraction: dict[str, Any],
    source_name: str | None = None,
) -> list[dict[str, Any]]:
    """Map AI extraction payload into proposed boq_items rows."""
    if not extraction:
        return []

    document_type = str(extraction.get("document_type") or "").lower()
    data = extraction.get("data") if isinstance(extraction.get("data"), dict) else {}
    # Nested shapes: data may itself be the extraction envelope.
    if isinstance(data.get("data"), dict) and not data.get("items"):
        data = data.get("data") or {}

    items = data.get("items") or data.get("boq_items") or data.get("line_items") or []
    if not isinstance(items, list):
        return []

    # Prefer explicit BOQ classification, but still accept item lists from general docs
    # when they look like quantity lines (description + quantity/unit).
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(items[:2000]):
        if not isinstance(raw, dict):
            continue
        fields = _item_fields(raw)
        if not fields["description"] and fields["quantity"] is None:
            continue
        if document_type not in {"boq", "tender", "general"} and fields["quantity"] is None:
            continue

        rows.append(
            {
                "project_id": project_id,
                "item_code": fields["item_code"] or f"DOC-{index + 1}",
                "work_section": fields["work_section"],
                "description": fields["description"] or fields["item_code"] or f"BOQ item {index + 1}",
                "element_type": "imported_boq_line",
                "quantity": fields["quantity"],
                "unit": fields["unit"],
                "item_count": 1,
                "source_element_ids": [],
                "source_identifiers": [document_id],
                "source": "document_extraction",
                "status": "proposed",
                "notes": (
                    "Imported from uploaded document extraction for professional review. "
                    "Not a certified tender BOQ."
                    + (f" Source file: {source_name}." if source_name else "")
                ),
                "properties": {
                    "source_document_id": document_id,
                    "source_filename": source_name,
                    "unit_rate": fields["rate"],
                    "amount": fields["amount"],
                    "extraction_confidence": extraction.get("confidence"),
                },
            }
        )
    return rows


def persist_boq_from_document(
    client,
    *,
    project_id: str,
    document_id: str,
    extraction: dict[str, Any],
    source_name: str | None = None,
) -> int:
    """Import BOQ lines safely, preserving reviewed rows on reprocessing.

    New rows are inserted before stale proposed rows are removed. Reviewed or
    accepted rows are never deleted. If the existing rows cannot be inspected,
    fail closed rather than risk an uncontrolled duplicate import.
    """
    rows = build_boq_rows_from_extraction(
        project_id=project_id,
        document_id=document_id,
        extraction=extraction,
        source_name=source_name,
    )
    # Do not remove existing rows when extraction produces no usable BOQ items.
    if not rows:
        return 0

    # Inspect existing imports first. Do not silently continue if this fails:
    # without this list we cannot safely determine what is eligible for cleanup.
    existing = (
        client.table("boq_items")
        .select("id,status,properties")
        .eq("project_id", project_id)
        .eq("source", "document_extraction")
        .limit(5000)
        .execute()
    ).data or []

    same_document = []
    for row in existing:
        props = row.get("properties") or {}
        if props.get("source_document_id") == document_id:
            same_document.append(row)

    # Only replace machine-generated rows that remain proposed. Preserve
    # accepted/reviewed rows and any rows whose status is missing or unknown.
    stale_proposed_ids = [
        row["id"]
        for row in same_document
        if str(row.get("status") or "").lower() == "proposed" and row.get("id")
    ]

    payload = [
        {
            "project_id": r["project_id"],
            "item_code": r.get("item_code"),
            "work_section": r.get("work_section"),
            "description": r.get("description"),
            "element_type": r.get("element_type"),
            "quantity": r.get("quantity"),
            "unit": r.get("unit"),
            "item_count": r.get("item_count") or 1,
            "source_element_ids": r.get("source_element_ids") or [],
            "source_identifiers": r.get("source_identifiers") or [],
            "source": "document_extraction",
            "status": "proposed",
            "notes": r.get("notes"),
            "properties": r.get("properties") or {},
        }
        for r in rows
    ]

    # Insert first so an insertion failure does not destroy the prior proposed
    # rows. If insertion fails, propagate it to the pipeline warning handler.
    result = client.table("boq_items").insert(payload).execute()
    inserted_count = len(result.data or payload)

    # Clean up only after successful insertion. Failures are surfaced to the
    # caller; they must not be silently reported as a successful replacement.
    for item_id in stale_proposed_ids:
        client.table("boq_items").delete().eq("id", item_id).execute()

    return inserted_count
