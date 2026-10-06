from app.document_intelligence_v2 import build_document_intelligence, build_project_document_intelligence


def test_empty_text_needs_review():
    result = build_document_intelligence({'id':'1','name':'drawing.pdf'}, {'status':'completed'}, {'extracted_text':'','page_count':5}, None, 0)
    assert result['readiness'] == 'needs_review'


def test_searchable_document_is_ready():
    result = build_document_intelligence({'id':'1','name':'boq.pdf'}, {'status':'completed'}, {'extracted_text':'Concrete quantity '*20,'page_count':2}, {'extraction_type':'boq'}, 3)
    assert result['readiness'] == 'ready'


def test_project_summary():
    result = build_project_document_intelligence([{'readiness':'ready'},{'readiness':'needs_review'}])
    assert result['document_count'] == 2
    assert result['ready_count'] == 1
    assert result['overall_readiness'] == 'partial'
