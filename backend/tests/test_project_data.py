from app.project_data import build_project_summary


def test_build_project_summary():
    summary = build_project_summary(
        {"id": "p1", "name": "G+2 Building", "code": "P-001", "status": "active"},
        [
            {"planned_percent": 80, "actual_percent": 70},
            {"planned_percent": 60, "actual_percent": 50},
        ],
        [
            {
                "name": "Cement",
                "code": "MAT-01",
                "unit": "bag",
                "stock_quantity": 80,
                "reorder_level": 100,
                "supplier": "Supplier A",
            },
            {
                "name": "Steel",
                "code": "MAT-02",
                "unit": "kg",
                "stock_quantity": 500,
                "reorder_level": 300,
                "supplier": "Supplier B",
            },
        ],
        [
            {"status": "available"},
            {"status": "available"},
            {"status": "maintenance"},
        ],
        [
            {"amount": 1000, "currency": "ETB"},
            {"amount": 500, "currency": "ETB"},
            {"amount": 20, "currency": "USD"},
        ],
        [
            {"level": "high"},
            {"level": "medium"},
            {"level": "high"},
        ],
    )

    assert summary["project"]["name"] == "G+2 Building"
    assert summary["activities"]["average_actual_percent"] == 60
    assert summary["materials"]["at_or_below_reorder_level"] == 1
    assert summary["costs"]["totals_by_currency"]["ETB"] == 1500
    assert summary["risks"]["level_counts"]["high"] == 2
