"""Unit tests for contract package build (Phase 4 Step 17)."""

from typing import Any


def _as_float(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def _round_qty(v):
    return round(float(v), 2) if v is not None else None


# Inline load of contract.py with stubs (same pattern as tender tests)
ns: dict[str, Any] = {
    "_as_float": _as_float,
    "_round_qty": _round_qty,
    "Any": Any,
    "uuid4": __import__("uuid").uuid4,
}


def _load():
    src = open(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app" / "contract.py")).read()
    src = src.replace("from __future__ import annotations\n", "")
    src = src.replace("from .quantity_takeoff import _as_float, _round_qty\n", "")
    # stub tender.commercial_summary for commercial_with_contracts
    class TenderMod:
        @staticmethod
        def commercial_summary(base, packages):
            return {
                "currency": (base or {}).get("currency", "USD"),
                "baseline_total": (base or {}).get("total_amount"),
                "packages_count": len(packages),
                "packages_by_status": {},
                "packages_baseline_total": None,
                "covered_line_count": 0,
                "notes": "",
            }

    import sys
    from types import ModuleType

    mod = ModuleType("tender")
    mod.commercial_summary = TenderMod.commercial_summary
    # contract imports from .tender — patch via namespace after rewrite
    src = src.replace("from .tender import commercial_summary\n", "")
    src = src.replace(
        "    from .tender import commercial_summary\n\n    summary = commercial_summary(base_summary, packages)\n",
        "    summary = _tender_commercial_summary(base_summary, packages)\n",
    )
    ns["_tender_commercial_summary"] = TenderMod.commercial_summary
    exec(compile(src, "contract.py", "exec"), ns)


_load()

TENDER_PKG = {
    "id": "tp-1",
    "project_id": "proj-1",
    "package_code": "TP-STRUCTURE",
    "title": "Tender package — Structure",
    "work_section": "Structure",
    "status": "awarded",
    "currency": "USD",
    "baseline_total": 88600.0,
}

TENDER_ITEMS = [
    {
        "id": "ti-1",
        "line_no": 1,
        "item_code": "COL-001",
        "work_section": "Structure",
        "description": "RC columns",
        "element_type": "column",
        "quantity": 45.0,
        "unit": "m3",
        "unit_rate": 280.0,
        "amount": 12600.0,
        "currency": "USD",
        "estimate_item_id": "e2",
        "boq_item_id": "b2",
        "source_element_ids": ["el2"],
        "source_identifiers": ["C1"],
    },
    {
        "id": "ti-2",
        "line_no": 2,
        "item_code": "SLB-001",
        "work_section": "Structure",
        "description": "RC slabs",
        "element_type": "slab",
        "quantity": 800.0,
        "unit": "m2",
        "unit_rate": 95.0,
        "amount": 76000.0,
        "currency": "USD",
        "estimate_item_id": "e3",
        "boq_item_id": "b3",
        "source_element_ids": ["el3"],
        "source_identifiers": ["S1"],
    },
]


def test_build_contract_from_tender():
    c = ns["build_contract_from_tender"](
        TENDER_PKG, TENDER_ITEMS, contractor_name="Acme Civil Ltd"
    )
    assert c["project_id"] == "proj-1"
    assert c["tender_package_id"] == "tp-1"
    assert c["status"] == "draft"
    assert c["contractor_name"] == "Acme Civil Ltd"
    assert c["line_count"] == 2
    assert c["contract_value"] == 88600.0
    assert c["source"] == "tender_award"
    assert len(c["items"]) == 2
    assert c["items"][0]["tender_item_id"] == "ti-1"


def test_build_contract_code_default():
    c = ns["build_contract_from_tender"](TENDER_PKG, TENDER_ITEMS)
    assert c["contract_code"].startswith("CT-")
    assert "STRUCTURE" in c["contract_code"] or "TP-STRUCTURE" in c["contract_code"]


def test_commercial_with_contracts():
    c = ns["commercial_with_contracts"](
        {"total_amount": 110200.0, "currency": "USD"},
        [TENDER_PKG],
        [ns["build_contract_from_tender"](TENDER_PKG, TENDER_ITEMS)],
    ) if False else ns["commercial_with_contracts"](
        {"total_amount": 110200.0, "currency": "USD"},
        [TENDER_PKG],
        [ns["build_contract_from_tender"](TENDER_PKG, TENDER_ITEMS)],
    )
    assert summary["contracts_count"] == 1 if False else True
    c = ns["build_contract_from_tender"](TENDER_PKG, TENDER_ITEMS)
    summary = ns["commercial_with_contracts"](
        {"total_amount": 110200.0, "currency": "USD"},
        [TENDER_PKG],
        [c],
    )
    assert summary["contracts_count"] == 1
    assert summary["contracts_by_status"]["draft"] == 1
    assert summary["contracts_value_total"] == 88600.0
    assert summary["contract_vs_baseline_delta"] == _round_qty(88600.0 - 110200.0)


if __name__ == "__main__":
    test_build_contract_from_tender()
    test_build_contract_code_default()
    test_commercial_with_contracts()
    print("All contract unit tests passed.")
