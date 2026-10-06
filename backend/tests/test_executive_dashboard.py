from app.executive_dashboard import build_project_executive_dashboard


def test_dashboard_reports_attention_and_priorities():
    result = build_project_executive_dashboard(
        summary={"project": {"id": "p1", "name": "Demo"}},
        performance={"score": 62, "status": "at_risk", "confidence": "moderate", "data_gaps": []},
        monitoring={"overall_status": "at_risk"},
        early_warnings={"warning_count": 1, "warnings": [{
            "severity": "high",
            "area": "Schedule",
            "recommended_action": "Review delayed activities.",
            "early_warning": "Negative variance persists.",
        }]},
        risk_prediction={"predicted_risks": [{"title": "Supply risk"}]},
        cost={"status": "review"},
        procurement={"status": "review"},
        schedule={"status": "behind_plan"},
        resources={"status": "review"},
        boq={"readiness": "needs_review"},
        contracts={"status": "review"},
        documents={"attention_items": [{"document_id": "d1"}]},
        management={"recommendations": [{
            "priority": "high",
            "area": "Cost",
            "recommendation": "Review cost controls.",
            "reason": "Cost signal needs review.",
        }]},
    )
    assert result["executive_health"] == "attention_required"
    assert result["performance"]["score"] == 62
    assert result["early_warning_count"] == 1
    assert result["top_priorities"]


def test_dashboard_does_not_treat_missing_data_as_zero():
    result = build_project_executive_dashboard(
        summary={"project": {"id": "p1"}},
        performance={"score": None, "status": "insufficient_data", "confidence": "low", "data_gaps": ["No schedule data"]},
        monitoring={"overall_status": "insufficient_data"},
        early_warnings={"warning_count": 0, "warnings": []},
        risk_prediction={}, cost={}, procurement={}, schedule={}, resources={}, boq={}, contracts={},
        documents={"attention_items": []},
        management={"recommendations": []},
    )
    assert result["executive_health"] == "insufficient_data"
    assert result["performance"]["score"] is None
    assert result["data_gaps"] == ["No schedule data"]
