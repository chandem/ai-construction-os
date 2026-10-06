from app.project_data import (
    build_project_action_plan,
    build_project_monitoring,
    build_project_risk_analysis,
    build_project_forecast,
    build_project_early_warnings,
    build_project_priorities,
    build_project_summary,
)


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


def test_build_project_priorities_identifies_missing_controls():
    summary = build_project_summary(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [],
        [],
        [],
        [],
        [],
    )

    result = build_project_priorities(summary)
    areas = {item["area"] for item in result["priorities"]}

    assert result["priority_count"] == 5
    assert "Progress tracking" in areas
    assert "Materials" in areas
    assert "Risk management" in areas
    assert "Cost control" in areas
    assert "Equipment" in areas
    assert result["priorities"][0]["priority"] == "high"



def test_build_project_action_plan_is_ordered_and_advisory():
    summary = build_project_summary(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [], [], [], [], [],
    )
    result = build_project_action_plan(summary)

    assert result["action_count"] == 5
    assert result["actions"][0]["area"] == "Progress tracking"
    assert result["actions"][0]["priority"] == "high"
    assert "owner" in result["actions"][0]
    assert "evidence" in result["actions"][0]
    assert "does not change project records" in result["note"]


def test_build_project_monitoring_classifies_current_gaps():
    summary = build_project_summary(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [{"planned_percent": 60, "actual_percent": 40}],
        [{"name": "Cement", "stock_quantity": 80, "reorder_level": 100}],
        [{"status": "available"}],
        [{"amount": 1000, "currency": "ETB"}],
        [{"level": "high"}],
    )

    result = build_project_monitoring(summary)

    assert result["overall_status"] == "critical"
    assert result["schedule"]["variance_percentage_points"] == -20
    assert any(item["area"] == "Risk management" for item in result["critical"])
    assert any(item["area"] == "Materials" for item in result["critical"])
    assert any(item["area"] == "Schedule" for item in result["attention"])
    assert result["management_decisions"]
    assert "does not modify project records" in result["note"]


def test_build_project_risk_analysis_empty_register():
    summary = build_project_summary(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [], [], [], [], [],
    )
    result = build_project_risk_analysis(summary)
    assert result["recorded_risk_count"] == 0
    assert result["recorded_risks"] == []
    assert result["recommendations"][0]["priority"] == "high"
    assert result["recommendations"][0]["area"] == "Risk register"


def test_build_project_forecast_reports_insufficient_data():
    summary = build_project_summary(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [], [], [], [], [],
    )
    result = build_project_forecast(summary)

    assert result["readiness"] == "insufficient_data"
    assert result["confidence"] == "low"
    assert result["blockers"]
    assert "No activity or planned/actual progress records are available." in result["blockers"]
    assert "cannot be produced" in result["forecast"]
    assert "does not create or modify project records" in result["note"]


def test_build_project_forecast_ready_when_core_controls_exist():
    summary = build_project_summary(
        {"id": "p1", "name": "G+2 Building", "status": "active"},
        [{"planned_percent": 60, "actual_percent": 55}],
        [{"name": "Cement", "stock_quantity": 200, "reorder_level": 100}],
        [{"status": "available"}],
        [{"amount": 1000, "currency": "ETB"}],
        [{"level": "medium", "status": "open"}],
    )
    result = build_project_forecast(summary)

    assert result["readiness"] == "forecast_ready"
    assert result["confidence"] == "moderate"
    assert not result["blockers"]
    assert "core control registers" in result["forecast"]


def test_build_project_early_warnings_identifies_control_gaps():
    summary = build_project_summary(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [], [], [], [], [],
    )
    result = build_project_early_warnings(summary)

    assert result["warning_count"] == 5
    assert result["warnings"][0]["severity"] == "high"
    assert any(item["area"] == "Schedule visibility" for item in result["warnings"])
    assert any(item["area"] == "Cost visibility" for item in result["warnings"])
    assert "do not modify project records" in result["note"]


def test_build_project_early_warnings_flags_schedule_and_material_signals():
    summary = build_project_summary(
        {"id": "p1", "name": "G+2 Building", "status": "active"},
        [{"planned_percent": 70, "actual_percent": 55}],
        [{"name": "Cement", "stock_quantity": 50, "reorder_level": 100}],
        [{"status": "available"}],
        [{"amount": 1000, "currency": "ETB"}],
        [],
    )
    result = build_project_early_warnings(summary)

    assert result["warning_count"] == 3
    assert any(item["area"] == "Schedule" for item in result["warnings"])
    assert any(item["area"] == "Materials" for item in result["warnings"])
    assert any(item["area"] == "Risk visibility" for item in result["warnings"])
