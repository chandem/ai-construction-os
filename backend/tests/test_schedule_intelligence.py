from app.schedule_intelligence import build_project_schedule_intelligence


def test_schedule_intelligence_reports_insufficient_data_without_activities():
    result = build_project_schedule_intelligence(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [],
    )

    assert result["status"] == "insufficient_data"
    assert result["confidence"] == "low"
    assert result["activity_count"] == 0
    assert result["schedule_variance_percentage_points"] is None
    assert result["behind_plan_count"] == 0
    assert result["priorities"][0]["priority"] == "high"
    assert result["data_gaps"] == ["No activities are recorded."]
    assert "does not modify project records" in result["note"]


def test_schedule_intelligence_identifies_activities_behind_plan():
    result = build_project_schedule_intelligence(
        {"id": "p1", "name": "G+2 Building", "status": "active"},
        [
            {"id": "a1", "name": "Foundation", "status": "in_progress", "planned_percent": 80, "actual_percent": 60},
            {"id": "a2", "name": "Columns", "status": "in_progress", "planned_percent": 40, "actual_percent": 45},
            {"id": "a3", "name": "Roof", "status": "not_started", "planned_percent": 20, "actual_percent": 10},
        ],
    )

    assert result["status"] == "attention_required"
    assert result["confidence"] == "high"
    assert result["activity_count"] == 3
    assert result["analyzed_activity_count"] == 3
    assert result["behind_plan_count"] == 2
    assert result["schedule_variance_percentage_points"] == -8.33
    assert {item["name"] for item in result["activities_behind_plan"]} == {"Foundation", "Roof"}
    assert result["priorities"][0]["priority"] == "medium"


def test_schedule_intelligence_reports_missing_progress_without_inventing_delay():
    result = build_project_schedule_intelligence(
        {"id": "p1", "name": "Road Project", "status": "active"},
        [
            {"id": "a1", "name": "Earthworks", "status": "in_progress", "planned_percent": 50, "actual_percent": None},
            {"id": "a2", "name": "Drainage", "status": "in_progress", "planned_percent": 30, "actual_percent": 20},
        ],
    )

    assert result["status"] == "attention_required"
    assert result["confidence"] == "moderate"
    assert result["behind_plan_count"] == 1
    assert result["schedule_variance_percentage_points"] == -10
    assert len(result["data_gaps"]) == 1
    assert result["data_gaps"][0] == "Some activities are missing valid planned or actual progress."
    assert "calendar delay" in result["note"]
