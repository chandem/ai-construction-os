from app.quantity_takeoff import derive_quantity, enrich_element_with_quantity, summarize_quantities
from app.engineering_elements import normalize_engineering_elements


def test_explicit_quantity_preserved():
    r = derive_quantity("slab", quantity=120, unit="m2", dimensions={})
    assert r["quantity"] == 120
    assert r["method"] == "explicit"


def test_slab_area_from_l_w():
    r = derive_quantity("slab", dimensions={"length": 10, "width": 8})
    assert r["quantity"] == 80
    assert r["unit"] == "m2"
    assert r["method"] == "l_w_area"


def test_foundation_volume():
    r = derive_quantity("foundation", dimensions={"length": 2, "width": 2, "depth": 1.5})
    assert r["quantity"] == 6
    assert r["unit"] == "m3"


def test_beam_length():
    r = derive_quantity("beam", dimensions={"length": "12.5 m"})
    assert r["quantity"] == 12.5
    assert r["unit"] == "m"


def test_column_count_fallback():
    r = derive_quantity("column", dimensions={})
    assert r["quantity"] == 1
    assert r["unit"] == "nos"
    assert r["method"] == "count_fallback"


def test_insufficient_dims():
    r = derive_quantity("slab", dimensions={"length": 5})
    assert r["quantity"] is None
    assert r["method"] == "insufficient"


def test_enrich_and_summarize():
    rows = normalize_engineering_elements(
        [
            {"type": "slab", "name": "S1", "dimensions": {"length": 10, "width": 4}},
            {"type": "slab", "name": "S2", "dimensions": {"length": 5, "width": 4}},
            {"type": "column", "name": "C1"},
        ],
        project_id="p1",
    )
    assert rows[0]["quantity"] == 40
    assert rows[0]["unit"] == "m2"
    assert rows[0]["properties"]["quantity_method"] == "l_w_area"
    summary = summarize_quantities(rows)
    slab = next(s for s in summary if s["element_type"] == "slab")
    assert slab["total_quantity"] == 60
    assert slab["item_count"] == 2


def test_assumed_fallback_count_is_excluded_from_summary():
    rows = [
        {
            "element_type": "column",
            "name": "C1",
            "quantity": 1,
            "unit": "nos",
            "properties": {"quantity_method": "count_fallback"},
        },
        {
            "element_type": "column",
            "name": "C2",
            "quantity": 4,
            "unit": "nos",
            "properties": {"quantity_method": "explicit"},
        },
    ]
    summary = summarize_quantities(rows)
    assert len(summary) == 1
    assert summary[0]["total_quantity"] == 4
    assert summary[0]["item_count"] == 1


def test_zero_or_negative_dimensions_are_not_used_for_takeoff():
    zero_length = derive_quantity("slab", dimensions={"length": 0, "width": 8})
    negative_length = derive_quantity("slab", dimensions={"length": -10, "width": 8})
    zero_area = derive_quantity("slab", dimensions={"area": 0})
    negative_volume = derive_quantity("foundation", dimensions={"volume": -2})

    assert zero_length["quantity"] is None
    assert zero_length["method"] == "insufficient"
    assert negative_length["quantity"] is None
    assert negative_length["method"] == "insufficient"
    assert zero_area["quantity"] is None
    assert zero_area["method"] == "insufficient"
    assert negative_volume["quantity"] is None
    assert negative_volume["method"] == "insufficient"


def test_negative_dimensions_do_not_produce_column_beam_or_slab_quantities():
    column = derive_quantity("column", dimensions={"length": -2, "width": 0.3, "height": 3})
    beam = derive_quantity("beam", dimensions={"length": 5, "width": -0.2, "height": 0.4})
    slab = derive_quantity("slab", dimensions={"length": 5, "width": 4, "height": -0.15})

    assert column["method"] == "count_fallback"
    assert beam["method"] == "insufficient"
    assert slab["method"] == "insufficient"



def test_explicit_metric_dimension_units_are_accepted():
    r = derive_quantity("beam", dimensions={"length": "12.5 m"})
    assert r["quantity"] == 12.5
    assert r["method"] == "length"


def test_incompatible_dimension_units_are_not_used_for_takeoff():
    slab = derive_quantity("slab", dimensions={"length": "500 mm", "width": "8 m"})
    foundation = derive_quantity("foundation", dimensions={"length": "2 m", "width": "2 m", "depth": "150 cm"})
    area = derive_quantity("slab", dimensions={"area": "80 ft2"})

    assert slab["quantity"] is None
    assert slab["method"] == "insufficient"
    assert foundation["quantity"] is None
    assert foundation["method"] == "insufficient"
    assert area["quantity"] is None
    assert area["method"] == "insufficient"
