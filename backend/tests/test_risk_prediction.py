from app.risk_prediction import build_project_risk_prediction


def test_risk_prediction_reports_insufficient_data_without_risks():
    result = build_project_risk_prediction(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [],
    )
    assert result["status"] == "insufficient_data"
    assert result["confidence"] == "low"
    assert result["predicted_risk_level"] == "unknown"
    assert result["priorities"][0]["priority"] == "high"


def test_risk_prediction_flags_unresolved_high_risks():
    result = build_project_risk_prediction(
        {"id": "p1", "name": "Road Project", "status": "active"},
        [
            {
                "risk_code": "R-01",
                "title": "Material supply",
                "level": "high",
                "status": "open",
                "owner": None,
                "mitigation": None,
            },
            {
                "risk_code": "R-02",
                "title": "Weather",
                "level": "medium",
                "status": "open",
                "owner": "Engineer",
                "mitigation": "Monitor",
            },
        ],
    )
    assert result["predicted_risk_level"] == "high"
    assert result["signals"][0]["signal"] == "high_risk_exposure"
    assert result["missing_controls"][0]["risk_code"] == "R-01"
    assert result["priorities"][0]["priority"] == "high"


def test_risk_prediction_does_not_claim_future_event():
    result = build_project_risk_prediction(
        {"id": "p1", "name": "Building Project", "status": "active"},
        [{"risk_code": "R-01", "title": "Minor issue", "level": "low", "status": "open"}],
    )
    assert "does not claim that a future event will occur" in result["note"]
