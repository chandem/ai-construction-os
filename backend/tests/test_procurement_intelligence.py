from app.procurement_intelligence import build_project_procurement_intelligence


def test_procurement_intelligence_identifies_order_and_delivery_gaps():
    result = build_project_procurement_intelligence(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [
            {
                "item_code": "MAT-01",
                "material_name": "Cement",
                "unit": "bag",
                "required_quantity": 1000,
                "requested_quantity": 1000,
                "ordered_quantity": 700,
                "delivered_quantity": 400,
                "supplier": "Supplier A",
                "status": "delayed",
            }
        ],
        [{"name": "Cement", "stock_quantity": 50, "reorder_level": 100}],
    )

    assert result["status"] == "attention_required"
    assert result["item_count"] == 1
    assert result["priority_actions"][0]["priority"] == "high"
    assert result["priority_actions"][0]["remaining_quantity"] == 600
    assert any(item["area"] == "Ordering gap" for item in result["findings"])
    assert any(item["area"] == "Delivery gap" for item in result["findings"])
    assert "does not create, modify, approve" in result["note"]


def test_procurement_intelligence_handles_missing_register_without_inventing_shortages():
    result = build_project_procurement_intelligence(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [],
        [],
    )

    assert result["status"] == "insufficient_data"
    assert result["confidence"] == "low"
    assert result["item_count"] == 0
    assert result["priority_actions"] == []
    assert not result["findings"]
    assert result["data_gaps"]
    assert "No procurement items are recorded" in result["data_gaps"][0]
