from app.engineering_elements import classify_element_type, normalize_engineering_elements


def test_classify_common_aliases():
    assert classify_element_type("C1 Column") == "column"
    assert classify_element_type("girder") == "beam"
    assert classify_element_type("retaining wall") == "retaining_wall"
    assert classify_element_type("unknown widget") == "other"


def test_normalize_mixed_payloads():
    raw = [
        "Beam B2 on grid A",
        {
            "type": "slab",
            "name": "First floor slab",
            "identifier": "S1",
            "level": "L1",
            "quantity": 120,
            "unit": "m2",
            "material": "C30/37 concrete",
            "evidence": "S1 120 m2 C30/37",
        },
        {"name": ""},
        {
            "type": "slab",
            "name": "First floor slab",
            "identifier": "S1",
        },
    ]
    rows = normalize_engineering_elements(
        raw,
        project_id="proj-1",
        design_asset_id="asset-1",
        document_id="doc-1",
        discipline="structural",
        source="ai_extraction",
    )
    assert len(rows) == 2
    types = {row["element_type"] for row in rows}
    assert types == {"beam", "slab"}
    slab = next(row for row in rows if row["element_type"] == "slab")
    assert slab["identifier"] == "S1"
    assert slab["quantity"] == 120
    assert slab["unit"] == "m2"
    assert "C30/37 concrete" in slab["materials"]
    assert slab["status"] == "proposed"


def test_normalize_empty_and_nested():
    assert normalize_engineering_elements(None, project_id="p") == []
    nested = {"elements": [{"type": "pipe", "name": "DN300 storm"}]}
    rows = normalize_engineering_elements(nested, project_id="p")
    assert len(rows) == 1
    assert rows[0]["element_type"] == "pipe"
