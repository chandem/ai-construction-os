from app.document_intelligence_v2 import build_document_intelligence, build_project_document_intelligence


def test_document_needs_review_when_text_missing():
    result = build_document_intelligence({'id':'1','name':'drawing.pdf'}, {'status':'completed'}, {'extracted_text':'','page_count':5}, None, 0)
    assert result['readiness'] == 'needs_review'


def test_document_is_ready_when_searchable():
    result = build_document_intelligence({'id':'1','name':'boq.pdf'}, {'status':'completed'}, {'extracted_text':'Concrete quantity '*20,'page_count':2}, {'extraction_type':'boq'}, 3)
    assert result['readiness'] == 'ready'


def test_project_summary_counts_attention_items():
    result = build_project_document_intelligence([{'readiness':'ready'},{'readiness':'needs_review'}])
    assert result['document_count'] == 2
    assert result['ready_count'] == 1
    assert result['overall_readiness'] == 'partial'



def test_document_is_partial_when_ai_enrichment_has_error_but_text_is_available():
    result = build_document_intelligence(
        {'id':'1','name':'maintenance.xlsx'},
        {'status':'completed','error_message':'429 RESOURCE_EXHAUSTED'},
        {'extracted_text':'Maintenance plan text '*20,'page_count':4},
        None,
        0,
    )
    assert result['readiness'] == 'partial'
    assert any('429 RESOURCE_EXHAUSTED' in warning for warning in result['warnings'])


def test_document_is_ready_only_when_processing_completed_without_errors():
    result = build_document_intelligence(
        {'id':'1','name':'boq.pdf'},
        {'status':'completed','error_message':'Semantic embeddings unavailable'},
        {'extracted_text':'Concrete quantity '*20,'page_count':2},
        {'extraction_type':'boq'},
        3,
    )
    assert result['readiness'] == 'partial'


def test_document_is_text_searchable_when_embeddings_are_unavailable():
    result = build_document_intelligence(
        {'id':'1','name':'maintenance.xlsx'},
        {'status':'completed','error_message':'Semantic embeddings unavailable: 429 RESOURCE_EXHAUSTED'},
        {'extracted_text':'Maintenance plan text '*20,'page_count':4},
        None,
        0,
    )
    assert result['readiness'] == 'partial'
    assert result['text_searchable'] is True
    assert result['semantic_searchable'] is False
    assert any('text search remains available' in warning for warning in result['warnings'])
