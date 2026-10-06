from app.resource_optimization import build_project_resource_optimization


def test_resource_optimization_reports_missing_registers():
    result = build_project_resource_optimization(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [],
        [],
        [],
        [],
    )

    assert result["status"] == "insufficient_data"
    assert result["confidence"] == "low"
    assert result["workforce_count"] == 0
    assert result["equipment_count"] == 0
    assert result["material_count"] == 0
    assert result["activity_count"] == 0
    assert result["priorities"][0]["area"] == "Activity-resource alignment"
    assert "does not modify project records" in result["note"]


def test_resource_optimization_identifies_material_and_equipment_bottlenecks():
    result = build_project_resource_optimization(
        {"id": "p1", "name": "Road Project", "status": "active"},
        [{"id": "w1", "name": "Foreman", "role": "foreman", "status": "active"}],
        [{"id": "e1", "name": "Excavator", "status": "maintenance"}],
        [{"id": "m1", "name": "Cement", "stock_quantity": 20, "reorder_level": 50, "unit": "bag"}],
        [{"id": "a1", "name": "Earthworks", "planned_percent": 50, "actual_percent": 40}],
    )

    assert result["status"] == "analyzable"
    assert result["confidence"] == "moderate"
    assert result["material_bottleneck_count"] == 1
    assert result["equipment_status_counts"]["maintenance"] == 1
    assert result["priorities"][0]["priority"] == "high"
    assert any(item["area"] == "Materials" for item in result["priorities"])


def test_resource_optimization_does_not_invent_utilization():
    result = build_project_resource_optimization(
        {"id": "p1", "name": "Building Project", "status": "active"},
        [{"id": "w1", "name": "Mason", "role": "mason", "status": "active"}],
        [{"id": "e1", "name": "Mixer", "status": "available"}],
        [{"id": "m1", "name": "Aggregate", "stock_quantity": 100, "reorder_level": 20, "unit": "m3"}],
        [{"id": "a1", "name": "Concrete", "planned_percent": 20, "actual_percent": None}],
    )

    assert result["activity_progress_gaps"]
    assert "utilization" in result["note"]
    assert "future resource needs" in result["note"]
