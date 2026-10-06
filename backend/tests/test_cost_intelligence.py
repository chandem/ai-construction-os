from app.cost_intelligence import build_project_cost_intelligence


def test_cost_intelligence_reports_missing_baseline_without_inventing_overrun():
    summary = {
        "project": {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        "costs": {"entry_count": 0, "totals_by_currency": {}},
    }

    result = build_project_cost_intelligence(summary)

    assert result["status"] == "insufficient_data"
    assert result["confidence"] == "low"
    assert result["entry_count"] == 0
    assert "No approved project budget or cost baseline is available." in result["data_gaps"]
    assert "overrun" not in " ".join(result["recommendations"]).lower()
    assert "does not create, modify, or approve" in result["note"]


def test_cost_intelligence_flags_multiple_currencies_and_requires_baseline():
    summary = {
        "project": {"id": "p1", "name": "G+2 Building", "status": "active"},
        "costs": {
            "entry_count": 3,
            "totals_by_currency": {"ETB": 1500, "USD": 20},
        },
    }

    result = build_project_cost_intelligence(summary)

    assert result["status"] == "baseline_required"
    assert result["confidence"] == "moderate"
    assert result["entry_count"] == 3
    assert len(result["totals_by_currency"]) == 2
    assert any(item["area"] == "Currency" for item in result["findings"])
    assert result["data_gaps"]
