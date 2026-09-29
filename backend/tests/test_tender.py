"""Unit tests for tender package build (Phase 4)."""

from tender import (
    build_packages_by_section,
    build_tender_package,
    commercial_summary,
    group_estimate_by_work_section,
    summarize_lines,
)


SAMPLE_LINES = [
    {
        "id": "e1",
        "item_code": "FND-001",
        "work_section": "Foundations",
        "description": "RC foundations",
        "element_type": "foundation",
        "quantity": 120.0,
        "unit": "m3",
        "unit_rate": 180.0,
        "amount": 21600.0,
        "currency": "USD",
        "boq_item_id": "b1",
        "source_element_ids": ["el1"],
        "source_identifiers": ["F1"],
    },
    {
        "id": "e2",
        "item_code": "COL-001",
        "work_section": "Structure",
        "description": "RC columns",
        "element_type": "column",
        "quantity": 45.0,
        "unit": "m3",
        "unit_rate": 280.0,
        "amount": 12600.0,
        "currency": "USD",
        "boq_item_id": "b2",
        "source_element_ids": ["el2"],
        "source_identifiers": ["C1"],
    },
    {
        "id": "e3",
        "item_code": "SLB-001",
        "work_section": "Structure",
        "description": "RC slabs",
        "element_type": "slab",
        "quantity": 800.0,
        "unit": "m2",
        "unit_rate": 95.0,
        "amount": 76000.0,
        "currency": "USD",
        "boq_item_id": "b3",
        "source_element_ids": ["el3"],
        "source_identifiers": ["S1"],
    },
]


def test_group_by_work_section():
    groups = group_estimate_by_work_section(SAMPLE_LINES)
    assert set(groups.keys()) == {"Foundations", "Structure"}
    assert len(groups["Foundations"]) == 1
    assert len(groups["Structure"]) == 2


def test_summarize_lines():
    s = summarize_lines(SAMPLE_LINES)
    assert s["line_count"] == 3
    assert s["priced_lines"] == 3
    assert s["total_amount"] == 110200.0
    assert s["currency"] == "USD"


def test_build_single_package_full():
    pkg = build_tender_package(SAMPLE_LINES, project_id="proj-1")
    assert pkg["project_id"] == "proj-1"
    assert pkg["status"] == "draft"
    assert pkg["line_count"] == 3
    assert pkg["baseline_total"] == 110200.0
    assert len(pkg["items"]) == 3
    assert pkg["items"][0]["line_no"] == 1
    assert pkg["source"] == "estimate_baseline"


def test_build_package_filtered_section():
    pkg = build_tender_package(
        SAMPLE_LINES, project_id="proj-1", work_section="Structure"
    )
    assert pkg["work_section"] == "Structure"
    assert pkg["line_count"] == 2
    assert pkg["baseline_total"] == 88600.0


def test_build_packages_by_section():
    packages = build_packages_by_section(SAMPLE_LINES, project_id="proj-1")
    assert len(packages) == 2
    sections = {p["work_section"] for p in packages}
    assert sections == {"Foundations", "Structure"}


def test_commercial_summary():
    packages = build_packages_by_section(SAMPLE_LINES, project_id="proj-1")
    summary = commercial_summary(
        {"total_amount": 110200.0, "currency": "USD"}, packages
    )
    assert summary["baseline_total"] == 110200.0
    assert summary["packages_count"] == 2
    assert summary["packages_by_status"]["draft"] == 2
    assert summary["covered_line_count"] == 3
