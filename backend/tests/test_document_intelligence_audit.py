from app.document_intelligence_audit import build_document_intelligence

def test_no_documents():
    result=build_document_intelligence([],[],[],[],[])
    assert result["status"]=="no_documents"

def test_failed_and_incomplete_documents():
    docs=[{"id":"1","name":"BOQ.pdf","status":"uploaded"},{"id":"2","name":"Contract.pdf","status":"failed"}]
    knowledge=[{"document_id":"1","extracted_text":"BOQ item 1","page_count":4,"status":"ready"}]
    chunks=[{"document_id":"1","chunk_index":0}]
    jobs=[{"document_id":"2","status":"failed","created_at":"2026-10-01T10:00:00Z"}]
    result=build_document_intelligence(docs,knowledge,chunks,jobs,[])
    assert result["status"]=="attention_required"
    assert result["failed_count"]==1
    assert result["incomplete_count"]==1

def test_ready_document():
    docs=[{"id":"1","name":"Schedule.pdf","status":"processed"}]
    knowledge=[{"document_id":"1","extracted_text":"Activity 1","page_count":2,"status":"ready"}]
    chunks=[{"document_id":"1","chunk_index":0}]
    jobs=[{"document_id":"1","status":"succeeded","created_at":"2026-10-01T10:00:00Z"}]
    extractions=[{"document_id":"1","extraction_type":"schedule"}]
    result=build_document_intelligence(docs,knowledge,chunks,jobs,extractions)
    assert result["status"]=="ready"
    assert result["ready_count"]==1
