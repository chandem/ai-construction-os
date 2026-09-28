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
