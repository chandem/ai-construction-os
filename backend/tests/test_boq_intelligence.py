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


from app.project_data import build_document_intelligence


def test_document_intelligence_no_documents():
    result = build_document_intelligence([], [], [], [], [])
    assert result["status"] == "no_documents"
    assert result["priority_count"] == 1


def test_document_intelligence_flags_failed_processing():
    documents = [{"id": "doc-1", "name": "BOQ.pdf", "status": "failed"}]
    jobs = [{"document_id": "doc-1", "status": "failed", "created_at": "2026-10-06"}]
    result = build_document_intelligence(documents, [], [], [], jobs)
    assert result["status"] == "needs_review"
    assert "processing_failed" in result["documents"][0]["issues"]


def test_document_intelligence_ready_document():
    documents = [{"id": "doc-1", "name": "contract.pdf", "status": "processed"}]
    knowledge = [{"document_id": "doc-1", "extracted_text": "Contract text", "page_count": 3, "status": "processed"}]
    chunks = [{"document_id": "doc-1"}]
    extractions = [{"document_id": "doc-1", "extraction_type": "document_summary"}]
    result = build_document_intelligence(documents, knowledge, chunks, extractions, [])
    assert result["status"] == "ready"
    assert result["documents"][0]["issues"] == []
