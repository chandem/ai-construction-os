from __future__ import annotations


def build_document_intelligence(document, job, knowledge, extraction, chunk_count):
    status = str((job or {}).get('status') or document.get('status') or 'unknown')
    text = str((knowledge or {}).get('extracted_text') or '')
    page_count = (knowledge or {}).get('page_count')
    extraction_type = (extraction or {}).get('extraction_type')
    confidence = None
    data = (extraction or {}).get('data') or {}
    try:
        confidence = float(data.get('confidence')) if data.get('confidence') is not None else None
    except (TypeError, ValueError):
        confidence = None
    warnings = []
    recommendations = []
    job_error = str((job or {}).get('error_message') or '').strip()
    if status == 'failed':
        warnings.append(job_error or 'Document processing failed.')
        recommendations.append('Reprocess the document after checking the source file and parser compatibility.')
    elif job_error:
        warnings.append(f'AI enrichment was incomplete: {job_error}')
        recommendations.append('Retry AI enrichment when the Gemini service or quota is available; extracted text may still be usable.')
    elif status in {'queued','processing'}:
        warnings.append('Document processing is not complete.')
        recommendations.append('Wait for processing to finish before relying on AI document search.')
    elif not text.strip():
        warnings.append('No extractable text is currently stored.')
        recommendations.append('Check whether the file is scanned or image-only; OCR or a text-based source may be required.')
    elif chunk_count == 0:
        warnings.append('Text was extracted but no searchable chunks are stored.')
        recommendations.append('Reprocess the document to rebuild the searchable knowledge index.')
    if page_count and text.strip():
        try:
            if len(text.strip()) / int(page_count) < 80:
                warnings.append('Very little text was extracted per page; this may indicate a scanned or poorly parsed document.')
                recommendations.append('Review the source visually and consider OCR for pages with missing text.')
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    if confidence is not None and confidence < 0.6:
        warnings.append('AI extraction confidence is below 0.60.')
        recommendations.append('Verify extracted structured fields against the source document.')
    if status in {'queued','processing'}:
        readiness = 'processing'
    elif text.strip() and chunk_count > 0 and not job_error and not warnings:
        readiness = 'ready'
    elif text.strip() and (chunk_count > 0 or status in {'processed','completed'}):
        readiness = 'partial'
    else:
        readiness = 'needs_review'
    if not recommendations:
        recommendations.append('Use the processed document with source-page verification for project decisions.')
    return {'document_id': document.get('id'), 'name': document.get('name'), 'status': status, 'readiness': readiness, 'mime_type': document.get('mime_type'), 'file_size_bytes': document.get('file_size_bytes'), 'page_count': page_count, 'extracted_characters': len(text.strip()), 'chunk_count': chunk_count, 'extraction_type': extraction_type, 'extraction_confidence': confidence, 'warnings': warnings[:10], 'recommendations': recommendations[:10], 'error_message': (job or {}).get('error_message')}


def build_project_document_intelligence(documents):
    counts = {}
    readiness_counts = {}
    attention = []
    for item in documents:
        status = str(item.get('status') or 'unknown')
        readiness = str(item.get('readiness') or 'unknown')
        counts[status] = counts.get(status, 0) + 1
        readiness_counts[readiness] = readiness_counts.get(readiness, 0) + 1
        if readiness != 'ready':
            attention.append({'document_id': item.get('document_id'), 'name': item.get('name'), 'readiness': readiness, 'warnings': item.get('warnings', [])})
    total = len(documents)
    ready = readiness_counts.get('ready', 0)
    overall = 'ready' if total and ready == total else 'partial' if ready else 'needs_review'
    return {'document_count': total, 'status_counts': counts, 'readiness_counts': readiness_counts, 'ready_count': ready, 'overall_readiness': overall, 'documents_needing_attention': attention[:20], 'note': 'Document intelligence evaluates extraction and search readiness. It does not certify technical, contractual, financial, or engineering correctness.'}
