"""Contract packages: lock accepted tender scope into a lightweight contract record.

Flow: estimate → tender package (awarded) → contract package.
Contracts are proposed commercial records for professional review — not signed legal instruments.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .quantity_takeoff import _as_float, _round_qty

DEFAULT_CURRENCY = "USD"
CONTRACT_SOURCE = "tender_award"

CONTRACT_STATUSES = (
    "draft",
    "under_review",
    "executed",
    "active",
    "completed",
    "terminated",
    "cancelled",
)


def _sum_amounts(items: list[dict[str, Any]]) -> float | None:
    total = 0.0
    n = 0
    for row in items:
        amt = _as_float(row.get("amount") or row.get("contract_amount") or row.get("awarded_amount"))
        if amt is not None:
            total += amt
            n += 1
    return _round_qty(total) if n else None


def build_contract_from_tender(
    tender_package: dict[str, Any],
    tender_items: list[dict[str, Any]] | None = None,
    *,
    project_id: str | None = None,
    contractor_name: str | None = None,
    contract_code: str | None = None,
    title: str | None = None,
    status: str = "draft",
    currency: str | None = None,
) -> dict[str, Any]:
    """Build one contract package from an awarded (or evaluated) tender package.

    Copies line items; amounts remain provisional until market rates are applied.
    """
    if status not in CONTRACT_STATUSES:
        status = "draft"

    pid = project_id or tender_package.get("project_id")
    if not pid:
        raise ValueError("project_id is required")

    items_src = tender_items if tender_items is not None else (tender_package.get("items") or [])
    items: list[dict[str, Any]] = []
    for i, row in enumerate(items_src, start=1):
        items.append(
            {
                "id": str(uuid4()),
                "line_no": row.get("line_no") or i,
                "item_code": row.get("item_code"),
                "work_section": row.get("work_section"),
                "description": row.get("description") or row.get("element_type") or "Item",
                "element_type": row.get("element_type"),
                "quantity": row.get("quantity"),
                "unit": row.get("unit"),
                "unit_rate": row.get("unit_rate"),
                "amount": row.get("amount"),
                "currency": row.get("currency") or currency or tender_package.get("currency") or DEFAULT_CURRENCY,
                "tender_item_id": row.get("id"),
                "estimate_item_id": row.get("estimate_item_id"),
                "boq_item_id": row.get("boq_item_id"),
                "source_element_ids": row.get("source_element_ids") or [],
                "source_identifiers": row.get("source_identifiers") or [],
                "status": "included",
                "notes": row.get("notes"),
                "properties": {
                    "from_tender": True,
                    "rate_source": (row.get("properties") or {}).get("rate_source")
                    or "provisional_default",
                },
            }
        )

    contract_value = _sum_amounts(items)
    if contract_value is None:
        contract_value = _as_float(tender_package.get("baseline_total"))

    cur = currency or tender_package.get("currency") or DEFAULT_CURRENCY
    code = contract_code or f"CT-{(tender_package.get('package_code') or 'PKG')[:20]}"
    name = title or f"Contract — {tender_package.get('title') or tender_package.get('work_section') or 'package'}"

    return {
        "id": str(uuid4()),
        "project_id": pid,
        "tender_package_id": tender_package.get("id"),
        "contract_code": code,
        "title": name,
        "work_section": tender_package.get("work_section"),
        "contractor_name": contractor_name,
        "status": status,
        "currency": cur,
        "contract_value": contract_value,
        "baseline_total": tender_package.get("baseline_total"),
        "line_count": len(items),
        "source": CONTRACT_SOURCE,
        "items": items,
        "notes": (
            "Draft contract from tender package. "
            "Not a signed instrument — professional and legal review required."
        ),
        "properties": {
            "tender_package_code": tender_package.get("package_code"),
            "tender_status": tender_package.get("status"),
            "rate_disclaimer": "Amounts inherit provisional/tender rates until replaced.",
        },
    }


def commercial_with_contracts(
    base_summary: dict[str, Any] | None,
    packages: list[dict[str, Any]],
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extend commercial summary with contract rollup.

    Builds package rollup inline so this module does not hard-depend on tender
    import order during unit tests.
    """
    currency = DEFAULT_CURRENCY
    baseline = None
    if base_summary:
        baseline = base_summary.get("total_amount") or base_summary.get("baseline_total")
        currency = base_summary.get("currency") or currency

    pkg_by_status: dict[str, int] = {}
    package_total = 0.0
    covered_lines = 0
    for p in packages:
        st = p.get("status") or "draft"
        pkg_by_status[st] = pkg_by_status.get(st, 0) + 1
        amt = _as_float(p.get("baseline_total"))
        if amt is not None:
            package_total += amt
        covered_lines += int(p.get("line_count") or 0)

    by_status: dict[str, int] = {}
    contract_total = 0.0
    n_valued = 0
    for c in contracts:
        st = c.get("status") or "draft"
        by_status[st] = by_status.get(st, 0) + 1
        amt = _as_float(c.get("contract_value"))
        if amt is not None:
            contract_total += amt
            n_valued += 1

    summary: dict[str, Any] = {
        "currency": currency,
        "baseline_total": baseline,
        "packages_count": len(packages),
        "packages_by_status": pkg_by_status,
        "packages_baseline_total": _round_qty(package_total) if packages else None,
        "covered_line_count": covered_lines,
        "contracts_count": len(contracts),
        "contracts_by_status": by_status,
        "contracts_value_total": _round_qty(contract_total) if n_valued else None,
        "contract_vs_baseline_delta": (
            _round_qty(contract_total - float(baseline))
            if baseline is not None and n_valued
            else None
        ),
        "notes": (
            "Contracts lock awarded tender scope. "
            "Variance uses provisional figures until market rates are applied."
        ),
    }
    return summary


def persist_contract_package(client, package: dict[str, Any]) -> dict[str, Any] | None:
    """Persist contract header + items. Returns None if tables missing."""
    header = {
        "id": package["id"],
        "project_id": package["project_id"],
        "tender_package_id": package.get("tender_package_id"),
        "contract_code": package.get("contract_code"),
        "title": package.get("title"),
        "work_section": package.get("work_section"),
        "contractor_name": package.get("contractor_name"),
        "status": package.get("status") or "draft",
        "currency": package.get("currency") or DEFAULT_CURRENCY,
        "contract_value": package.get("contract_value"),
        "baseline_total": package.get("baseline_total"),
        "line_count": package.get("line_count"),
        "source": package.get("source") or CONTRACT_SOURCE,
        "notes": package.get("notes"),
        "properties": package.get("properties") or {},
    }
    try:
        client.table("contract_packages").upsert(header).execute()
    except Exception:
        return None

    items = package.get("items") or []
    rows = []
    for it in items:
        rows.append(
            {
                "id": it.get("id"),
                "contract_package_id": package["id"],
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
                "tender_item_id": it.get("tender_item_id"),
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
            client.table("contract_items").upsert(rows).execute()
        except Exception:
            pass
    return header
