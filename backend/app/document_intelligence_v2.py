def build_document_intelligence(document, job, knowledge, extraction, chunk_count):
    status = str((job or {}).get('status') or document.get('status') or 'unknown')
    text = str((knowledge or {}).get('extracted_text') or '')
    warnings = []
    if status == 'failed':
        warnings.append((job or {}).get('error_message') or 'Document processing failed.')
    elif not text.strip():
        warnings.append('No extractable text is currently stored.')
    elif chunk_count == 0:
        warnings.append('Text was extracted but no searchable chunks are stored.')
    readiness = 'ready' if not warnings and status in {'processed','completed'} else 'needs_review'
    return {'document_id': document.get('id'), 'name': document.get('name'), 'status': status, 'readiness': readiness, 'page_count': (knowledge or {}).get('page_count'), 'extracted_characters': len(text.strip()), 'chunk_count': chunk_count, 'extraction_type': (extraction or {}).get('extraction_type'), 'warnings': warnings[:10], 'error_message': (job or {}).get('error_message')}


def build_project_document_intelligence(documents):
    ready = sum(1 for item in documents if item.get('readiness') == 'ready')
    total = len(documents)
    return {'document_count': total, 'ready_count': ready, 'overall_readiness': 'ready' if total and ready == total else 'partial' if ready else 'needs_review', 'documents_needing_attention': [item for item in documents if item.get('readiness') != 'ready'][:20]}
