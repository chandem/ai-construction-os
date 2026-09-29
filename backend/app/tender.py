"""Tender packages: slice estimate / BOQ lines into bid packages for commercial workflow.

Packages are proposed groupings for professional review. They are not issued tenders
until a user explicitly marks status and applies real market rates.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .quantity_takeoff import _as_float, _round_qty

DEFAULT_CURRENCY = "USD"
PACKAGE_SOURCE = "estimate_baseline"

# Canonical package statuses (lifecycle)
TENDER_STATUSES = (
    "draft",
    "ready",
    "issued",
    "received",
    "evaluated",
    "awarded",
    "cancelled",
)


def _work_section_key(row: dict[str, Any]) -> str:
    ws = (row.get("work_section") or row.get("element_type") or "general").strip()
    return ws or "general"


def group_estimate_by_work_section(
    estimate_lines: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group estimate lines by work_section for package splitting."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in estimate_lines:
        key = _work_section_key(row)
        groups.setdefault(key, []).append(row)
    return groups


def summarize_lines(lines: list[dict[str, Any]], currency: str = DEFAULT_CURRENCY) -> dict[str, Any]:
    total = 0.0
    priced = 0
    for row in lines:
        amt = _as_float(row.get("amount"))
        if amt is not None:
            total += amt
            priced += 1
    return {
        "currency": currency,
        "line_count": len(lines),
        "priced_lines": priced,
        "total_amount": _round_qty(total) if priced else None,
    }


def build_tender_package(
    estimate_lines: list[dict[str, Any]],
    *,
    project_id: str,
    title: str | None = None,
    work_section: str | None = None,
    package_code: str | None = None,
    currency: str = DEFAULT_CURRENCY,
    status: str = "draft",
) -> dict[str, Any]:
    """Build one tender package (in-memory) from estimate lines.

    If work_section is provided, only lines matching that section are included.
    """
    if status not in TENDER_STATUSES:
        status = "draft"

    lines = list(estimate_lines)
    if work_section:
        key = work_section.strip().lower()
        lines = [r for r in lines if _work_section_key(r).lower() == key]

    items: list[dict[str, Any]] = []
    for i, row in enumerate(lines, start=1):
        item = {
            "id": str(uuid4()),
            "line_no": i,
            "item_code": row.get("item_code"),
            "work_section": row.get("work_section") or _work_section_key(row),
            "description": row.get("description") or row.get("element_type") or "Item",
            "element_type": row.get("element_type"),
            "quantity": row.get("quantity"),
            "unit": row.get("unit"),
            "unit_rate": row.get("unit_rate"),
            "amount": row.get("amount"),
            "currency": row.get("currency") or currency,
            "estimate_item_id": row.get("id"),
            "boq_item_id": row.get("boq_item_id"),
            "source_element_ids": row.get("source_element_ids") or [],
            "source_identifiers": row.get("source_identifiers") or [],
            "status": "included",
            "notes": row.get("notes"),
            "properties": {
                "rate_source": row.get("rate_source") or "provisional_default",
                "from_estimate": True,
            },
        }
        items.append(item)

    summary = summarize_lines(items, currency)
    code = package_code or (f"TP-{work_section.upper().replace(' ', '-')[:24]}" if work_section else "TP-FULL")
    name = title or (f"Tender package — {work_section}" if work_section else "Full project tender package")

    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "package_code": code,
        "title": name,
        "work_section": work_section,
        "status": status,
        "currency": currency,
        "baseline_total": summary["total_amount"],
        "line_count": summary["line_count"],
        "priced_lines": summary["priced_lines"],
        "source": PACKAGE_SOURCE,
        "items": items,
        "notes": "Proposed package from provisional estimate. Replace rates before issue.",
        "properties": {
            "rate_disclaimer": "Unit rates are provisional defaults, not market tender rates.",
        },
    }


def build_packages_by_section(
    estimate_lines: list[dict[str, Any]],
    *,
    project_id: str,
    currency: str = DEFAULT_CURRENCY,
) -> list[dict[str, Any]]:
    """One package per work section + optional full-package summary metadata."""
    groups = group_estimate_by_work_section(estimate_lines)
    packages: list[dict[str, Any]] = []
    for section, rows in sorted(groups.items(), key=lambda x: x[0].lower()):
        packages.append(
            build_tender_package(
                rows,
                project_id=project_id,
                work_section=section,
                currency=currency,
            )
        )
    return packages


def commercial_summary(
    estimate_summary: dict[str, Any] | None,
    packages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Roll up baseline estimate vs tender package coverage."""
    baseline = None
    currency = DEFAULT_CURRENCY
    if estimate_summary:
        baseline = estimate_summary.get("total_amount")
        currency = estimate_summary.get("currency") or currency

    by_status: dict[str, int] = {}
    package_total = 0.0
    covered_lines = 0
    for p in packages:
        st = p.get("status") or "draft"
        by_status[st] = by_status.get(st, 0) + 1
        amt = _as_float(p.get("baseline_total"))
        if amt is not None:
            package_total += amt
        covered_lines += int(p.get("line_count") or 0)

    return {
        "currency": currency,
        "baseline_total": baseline,
        "packages_count": len(packages),
        "packages_by_status": by_status,
        "packages_baseline_total": _round_qty(package_total) if packages else None,
        "covered_line_count": covered_lines,
        "variance_placeholder": None,  # filled when awarded rates exist
        "notes": "Variance available after packages move to awarded with market rates.",
    }


def persist_tender_package(client, package: dict[str, Any]) -> dict[str, Any] | None:
    """Persist package header + items. No-op (returns None) if tables missing."""
    header = {
        "id": package["id"],
        "project_id": package["project_id"],
        "package_code": package.get("package_code"),
        "title": package.get("title"),
        "work_section": package.get("work_section"),
        "status": package.get("status") or "draft",
        "currency": package.get("currency") or DEFAULT_CURRENCY,
        "baseline_total": package.get("baseline_total"),
        "line_count": package.get("line_count"),
        "priced_lines": package.get("priced_lines"),
        "source": package.get("source") or PACKAGE_SOURCE,
        "notes": package.get("notes"),
        "properties": package.get("properties") or {},
    }
    try:
        client.table("tender_packages").upsert(header).execute()
    except Exception:
        return None

    items = package.get("items") or []
    rows = []
    for it in items:
        rows.append(
            {
                "id": it.get("id"),
                "tender_package_id": package["id"],
                "project_id": package["project_id"],
                "line_no": it.get("line_no"),
                "item_code": it.get("item_code"),
                "work_section": it.get("work_section"),
                "description": it.get("description"),
                "element_type": it.get("element_type"),
                "quantity": it.get("quantity"),
                "unit": it.get("unit"),
                "unit_rate": it.get("unit_rate"),
                "amount": it.get("amount"),
                "currency": it.get("currency"),
                "estimate_item_id": it.get("estimate_item_id"),
                "boq_item_id": it.get("boq_item_id"),
                "source_element_ids": it.get("source_element_ids") or [],
                "source_identifiers": it.get("source_identifiers") or [],
                "status": it.get("status") or "included",
                "notes": it.get("notes"),
                "properties": it.get("properties") or {},
            }
        )
    if rows:
        try:
            client.table("tender_items").upsert(rows).execute()
        except Exception:
            pass
    return header
