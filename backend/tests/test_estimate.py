from app.estimate import (
    apply_rates_to_boq_lines,
    build_estimate_from_boq,
    rate_for,
    summarize_estimate,
)


def test_rate_for_known_types():
    r = rate_for("slab", "m2")
    assert r["unit_rate"] == 95.0
    assert r["unit_match"] is True
    r2 = rate_for("foundation", "m3")
    assert r2["unit_rate"] == 180.0
    r3 = rate_for("unknown_type")
    assert r3["unit_rate"] == 50.0  # other


def _sample_boq():
    return [
        {
            "id": "boq-1",
            "item_code": "C.2.3.01",
            "work_section": "Concrete works — Superstructure",
            "description": "Reinforced concrete slabs",
            "element_type": "slab",
            "quantity": 80,
            "unit": "m2",
            "item_count": 1,
            "source_element_ids": ["e1"],
            "source_identifiers": ["S1"],
            "source": "quantity_takeoff",
            "properties": {},
        },
        {
            "id": "boq-2",
            "item_code": "C.1.1.01",
            "work_section": "Concrete works — Foundations",
            "description": "Mass / reinforced concrete foundations",
            "element_type": "foundation",
            "quantity": 4,
            "unit": "m3",
            "item_count": 1,
            "source_element_ids": ["e2"],
            "source_identifiers": ["F1"],
            "source": "quantity_takeoff",
            "properties": {},
        },
        {
            "id": "boq-3",
            "item_code": "C.2.1.01",
            "work_section": "Concrete works — Superstructure",
            "description": "Reinforced concrete columns",
            "element_type": "column",
            "quantity": 1,
            "unit": "nos",
            "item_count": 1,
            "source_element_ids": ["e3"],
            "source_identifiers": ["C1"],
            "source": "quantity_takeoff",
            "properties": {},
        },
    ]


def test_estimate_from_boq_lines():
    boq = _sample_boq()
    est = build_estimate_from_boq(boq, project_id="p1")
    lines = est["lines"]
    summary = est["summary"]
    assert len(lines) == 3
    for line in lines:
        assert line["unit_rate"] is not None
        assert line["amount"] is not None
        assert line["currency"] == "USD"
        assert line["status"] == "proposed"
        assert line["rate_source"] == "provisional_default"
    # slab 80 * 95 = 7600
    slab = next(l for l in lines if l["element_type"] == "slab")
    assert slab["amount"] == 7600.0
    # foundation 4 * 180 = 720
    found = next(l for l in lines if l["element_type"] == "foundation")
    assert found["amount"] == 720.0
    # column 1 * 280 = 280
    col = next(l for l in lines if l["element_type"] == "column")
    assert col["amount"] == 280.0
    assert summary["total_amount"] == 7600.0 + 720.0 + 280.0
    assert summary["priced_lines"] == 3
    assert len(summary["by_work_section"]) >= 2


def test_rate_override():
    boq = [
        {
            "item_code": "C.2.3.01",
            "work_section": "Concrete works — Superstructure",
            "description": "Reinforced concrete slabs",
            "element_type": "slab",
            "quantity": 10,
            "unit": "m2",
            "item_count": 1,
            "source_element_ids": [],
            "source_identifiers": [],
            "source": "test",
            "properties": {},
        }
    ]
    lines = apply_rates_to_boq_lines(boq, project_id="p1", rate_overrides={"slab": 100.0})
    assert lines[0]["unit_rate"] == 100.0
    assert lines[0]["amount"] == 1000.0
    assert lines[0]["rate_source"] == "override"


def test_empty_boq():
    est = build_estimate_from_boq([], project_id="p1")
    assert est["lines"] == []
    assert est["summary"]["total_amount"] == 0
    assert est["summary"]["line_count"] == 0


def test_summarize_sections():
    lines = apply_rates_to_boq_lines(_sample_boq(), project_id="p1")
    s = summarize_estimate(lines)
    sections = {x["work_section"]: x for x in s["by_work_section"]}
    assert "Concrete works — Superstructure" in sections
    assert sections["Concrete works — Superstructure"]["line_count"] == 2
