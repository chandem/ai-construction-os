from app.boq import boq_template_for, build_boq_lines
from app.engineering_elements import normalize_engineering_elements


def test_template_known_types():
    t = boq_template_for("slab")
    assert t["item_code"] == "C.2.3"
    assert "slab" in t["description"].lower() or "Slabs" in t["description"]
    assert t["default_unit"] == "m2"

    t2 = boq_template_for("unknown_thing")
    assert t2["item_code"] == "G.1.1"


def test_build_boq_from_elements():
    rows = normalize_engineering_elements(
        [
            {"type": "slab", "name": "S1", "dimensions": {"length": 10, "width": 4}},
            {"type": "slab", "name": "S2", "dimensions": {"length": 5, "width": 4}},
            {"type": "column", "name": "C1"},
            {"type": "foundation", "name": "F1", "dimensions": {"length": 2, "width": 2, "depth": 1}},
        ],
        project_id="proj-boq-1",
    )
    # Inject fake ids for source tracking
    for i, r in enumerate(rows):
        r["id"] = f"el-{i}"

    lines = build_boq_lines(rows, project_id="proj-boq-1")
    assert len(lines) >= 2

    by_type = {line["element_type"]: line for line in lines}
    assert "slab" in by_type
    assert by_type["slab"]["quantity"] == 60
    assert by_type["slab"]["unit"] == "m2"
    assert by_type["slab"]["item_count"] == 2
    assert by_type["slab"]["status"] == "proposed"
    assert by_type["slab"]["project_id"] == "proj-boq-1"
    assert by_type["slab"]["work_section"]

    assert "column" in by_type
    assert by_type["column"]["quantity"] == 1
    assert by_type["column"]["unit"] == "nos"

    assert "foundation" in by_type
    assert by_type["foundation"]["quantity"] == 4
    assert by_type["foundation"]["unit"] == "m3"


def test_empty_elements_yield_no_lines():
    assert build_boq_lines([], project_id="p") == []
    rows = normalize_engineering_elements(
        [{"type": "slab", "name": "no dims"}],
        project_id="p",
    )
    # insufficient dims → no quantity → no BOQ line
    lines = build_boq_lines(rows, project_id="p")
    assert lines == []
