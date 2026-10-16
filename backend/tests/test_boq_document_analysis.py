from app.boq_document_analysis import normalize_boq_extraction


def test_normalizes_boq_rows_and_calculates_amounts():
    result = normalize_boq_extraction({
        "document_type": "boq",
        "summary": "Road works BOQ",
        "data": {"items": [
            {"code": "1.1", "description": "Excavation", "unit": "m3",
             "quantity": "1,200", "rate": "50.00", "amount": "60,000"},
            {"item_number": "1.2", "item_description": "Selected material",
             "uom": "m3", "qty": 10, "unit_price": 40, "total_amount": 390},
        ]},
    })

    assert result["item_count"] == 2
    assert result["rows"][0]["calculated_amount"] == 60000
    assert result["rows"][0]["difference"] == 0
    assert result["rows"][1]["calculated_amount"] == 400
    assert result["rows"][1]["difference"] == -10
    assert "amount_mismatch" in result["rows"][1]["issues"]
    assert result["stated_total"] == 60390
    assert result["calculated_total"] == 60400


def test_does_not_invent_missing_values():
    result = normalize_boq_extraction({"data": {"items": [
        {"code": "A", "description": "Concrete", "unit": "m3", "quantity": None, "rate": None}
    ]}})

    row = result["rows"][0]
    assert row["quantity"] is None
    assert row["rate"] is None
    assert row["calculated_amount"] is None
    assert row["stated_amount"] is None
    assert {"missing_quantity", "missing_rate", "missing_stated_amount"} <= set(row["issues"])


def test_handles_missing_or_malformed_extraction():
    assert normalize_boq_extraction(None)["item_count"] == 0
    assert normalize_boq_extraction({"data": {"items": "not a list"}})["rows"] == []
    result = normalize_boq_extraction({"data": {"items": [None, {"description": "Item"}]}})
    assert result["item_count"] == 1
    assert result["flag_count"] == 1
