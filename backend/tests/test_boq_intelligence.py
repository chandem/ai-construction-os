from app.boq_intelligence import build_boq_intelligence


def test_boq_intelligence_reports_empty_register():
    result = build_boq_intelligence(
        {"id": "p1", "name": "Shakiso-Solomo", "status": "active"},
        [],
    )
    assert result["status"] == "insufficient_data"
    assert result["confidence"] == "low"
    assert result["item_count"] == 0
    assert result["priorities"][0]["priority"] == "high"


def test_boq_intelligence_detects_data_quality_flags():
    result = build_boq_intelligence(
        {"id": "p1", "name": "Building Project", "status": "active"},
        [{
            "code": "1.1",
            "description": "Concrete",
            "unit": "m3",
            "quantity": 0,
            "unit_rate": 100,
            "amount": 0,
            "work_section": "Concrete",
        }],
    )
    assert result["status"] == "analyzable"
    assert result["confidence"] == "low"
    assert result["quality_flags"][0]["issue"] == "missing_or_nonpositive_quantity"


def test_boq_intelligence_summarizes_valid_items():
    result = build_boq_intelligence(
        {"id": "p1", "name": "Road Project", "status": "active"},
        [
            {
                "code": "1.1", "description": "Excavation", "unit": "m3",
                "quantity": 10, "unit_rate": 50, "amount": 500,
                "work_section": "Earthworks",
            },
            {
                "code": "2.1", "description": "Gravel", "unit": "m3",
                "quantity": 20, "unit_rate": 25, "amount": 500,
                "work_section": "Earthworks",
            },
        ],
    )
    assert result["item_count"] == 2
    assert result["total_amount"] == 1000
    assert result["work_section_counts"]["Earthworks"] == 2
    assert result["confidence"] == "moderate"
    assert "does not infer missing quantities" in result["note"]
