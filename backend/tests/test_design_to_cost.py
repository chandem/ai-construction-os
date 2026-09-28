from app.design_to_cost import (
    build_design_to_cost,
    cost_drivers,
    design_levers,
    pareto_insight,
    quantity_sensitivity,
    section_concentration,
)
from app.estimate import apply_rates_to_boq_lines


def _boq():
    return [
        {
            "id": "b1",
            "item_code": "C.2.3.01",
            "work_section": "Concrete works — Superstructure",
            "description": "Reinforced concrete slabs",
            "element_type": "slab",
            "quantity": 100,
            "unit": "m2",
            "item_count": 2,
            "source_element_ids": ["e1"],
            "source_identifiers": ["S1"],
            "source": "test",
            "properties": {},
        },
        {
            "id": "b2",
            "item_code": "C.1.1.01",
            "work_section": "Concrete works — Foundations",
            "description": "Foundations",
            "element_type": "foundation",
            "quantity": 10,
            "unit": "m3",
            "item_count": 1,
            "source_element_ids": ["e2"],
            "source_identifiers": ["F1"],
            "source": "test",
            "properties": {},
        },
        {
            "id": "b3",
            "item_code": "D.1.1.01",
            "work_section": "Drainage & services — Pipes",
            "description": "Pipes",
            "element_type": "pipe",
            "quantity": 50,
            "unit": "m",
            "item_count": 1,
            "source_element_ids": ["e3"],
            "source_identifiers": ["P1"],
            "source": "test",
            "properties": {},
        },
    ]


def _estimate():
    return apply_rates_to_boq_lines(_boq(), project_id="p1")


def test_cost_drivers_ordered():
    lines = _estimate()
    drivers = cost_drivers(lines, top_n=2)
    assert len(drivers) == 2
    assert drivers[0]["amount"] >= drivers[1]["amount"]
    assert drivers[0]["element_type"] == "slab"
    assert drivers[0]["share_pct"] > 0


def test_section_concentration():
    sections = section_concentration(_estimate())
    assert len(sections) >= 2
    assert sections[0]["share_pct"] >= sections[-1]["share_pct"]


def test_pareto():
    p = pareto_insight(_estimate(), threshold_pct=80)
    assert p["lines_needed"] >= 1
    assert p["cumulative_share_pct"] >= 80
    assert "slab" in p["element_types"]


def test_quantity_sensitivity_minus_10():
    lines = _estimate()
    s = quantity_sensitivity(lines, element_type="slab", quantity_delta_pct=-10)
    assert s["lines_affected"] == 1
    assert s["delta_amount"] < 0
    assert abs(s["delta_amount"] - (-950.0)) < 0.1


def test_design_levers():
    levers = design_levers(_estimate())
    assert len(levers) >= 1
    assert levers[0]["priority"] in {"high", "medium", "low"}
    assert "suggestion" in levers[0]


def test_build_full_payload():
    boq = _boq()
    lines = apply_rates_to_boq_lines(boq, project_id="p1")
    payload = build_design_to_cost(lines, boq_lines=boq, project_id="p1", top_n=3)
    assert payload["baseline"]["total_amount"] > 0
    assert len(payload["cost_drivers"]) >= 1
    assert len(payload["quantity_scenarios"]) >= 2
    assert len(payload["rate_scenarios"]) >= 1
    assert "disclaimer" in payload


def test_empty_lines():
    payload = build_design_to_cost([], project_id="p1")
    assert payload["baseline"]["total_amount"] == 0
    assert payload["cost_drivers"] == []
    assert payload["pareto"]["lines_needed"] == 0
