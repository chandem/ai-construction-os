from app.contract_intelligence import build_contract_intelligence


def test_contract_intelligence_reports_missing_register():
    result = build_contract_intelligence(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [],
    )
    assert result["status"] == "insufficient_data"
    assert result["confidence"] == "low"
    assert result["contract_count"] == 0
    assert result["priorities"][0]["priority"] == "high"


def test_contract_intelligence_flags_incomplete_contract():
    result = build_contract_intelligence(
        {"id": "p1", "name": "Road Project", "status": "active"},
        [{
            "name": "Main Contract",
            "contract_number": "C-01",
            "contractor": None,
            "client": "Client",
            "start_date": "2026-01-01",
            "end_date": "2027-01-01",
            "contract_value": 1000000,
            "currency": "ETB",
            "status": "active",
        }],
    )
    assert result["status"] == "analyzable"
    assert result["confidence"] == "low"
    assert result["data_gaps"][0]["missing_fields"] == ["contractor"]


def test_contract_intelligence_does_not_make_legal_conclusions():
    result = build_contract_intelligence(
        {"id": "p1", "name": "Building Project", "status": "active"},
        [{
            "name": "Contract",
            "contract_number": "C-02",
            "contractor": "ABC",
            "client": "Client",
            "start_date": "2026-01-01",
            "end_date": "2027-01-01",
            "contract_value": 500000,
            "currency": "ETB",
            "status": "active",
        }],
    )
    assert "does not determine legal entitlement" in result["note"]
