"""Read-only document intelligence health audit for construction projects."""
from __future__ import annotations
from typing import Any

MAX_DOCUMENTS = 50
MAX_WARNINGS = 20

def build_document_intelligence(documents:list[dict[str,Any]], knowledge_documents:list[dict[str,Any]], chunks:list[dict[str,Any]], processing_jobs:list[dict[str,Any]], extractions:list[dict[str,Any]])->dict[str,Any]:
    knowledge={str(r.get("document_id")):r for r in knowledge_documents}
    chunk_counts:dict[str,int]={}
    for r in chunks:
        k=str(r.get("document_id")); chunk_counts[k]=chunk_counts.get(k,0)+1
    jobs:dict[str,dict[str,Any]]={}
    for r in processing_jobs:
        k=str(r.get("document_id")); cur=jobs.get(k)
        if cur is None or str(r.get("created_at") or "")>str(cur.get("created_at") or ""): jobs[k]=r
    extraction_counts:dict[str,int]={}
    for r in extractions:
        k=str(r.get("document_id")); extraction_counts[k]=extraction_counts.get(k,0)+1
    status_counts:dict[str,int]={}; type_counts:dict[str,int]={}; warnings=[]; health=[]
    for doc in documents[:MAX_DOCUMENTS]:
        did=str(doc.get("id")); status=str(doc.get("status") or "unknown")
        status_counts[status]=status_counts.get(status,0)+1
        kd=knowledge.get(did,{})
        dtype=str(kd.get("document_type") or doc.get("document_type") or "unclassified")
        type_counts[dtype]=type_counts.get(dtype,0)+1
        text=kd.get("extracted_text") or ""; chunks_n=chunk_counts.get(did,0)
        job=jobs.get(did,{}); job_status=str(job.get("status") or "not_started")
        flags=[]
        if status in {"failed","error"}: flags.append("document_processing_failed")
        if job_status=="failed": flags.append("latest_processing_job_failed")
        if not text.strip(): flags.append("no_extracted_text")
        if chunks_n==0: flags.append("no_search_chunks")
        if extraction_counts.get(did,0)==0: flags.append("no_structured_extraction")
        if kd.get("page_count") is not None and int(kd.get("page_count") or 0)<=0: flags.append("invalid_page_count")
        for flag in flags[:MAX_WARNINGS-len(warnings)]:
            warnings.append({"document":doc.get("name") or "Uploaded document","document_id":did,"issue":flag,"recommended_action":_recommendation(flag)})
        if any(x in flags for x in ("document_processing_failed","latest_processing_job_failed")): h="failed"
        elif "no_extracted_text" in flags or "no_search_chunks" in flags: h="incomplete"
        elif "no_structured_extraction" in flags: h="partially_ready"
        else: h="ready"
        health.append({"document":doc.get("name") or "Uploaded document","document_id":did,"type":dtype,"status":status,"processing_status":job_status,"page_count":kd.get("page_count"),"chunk_count":chunks_n,"extraction_count":extraction_counts.get(did,0),"health":h,"flags":flags})
    failed=sum(r["health"]=="failed" for r in health); incomplete=sum(r["health"]=="incomplete" for r in health); partial=sum(r["health"]=="partially_ready" for r in health); ready=sum(r["health"]=="ready" for r in health)
    if not documents: overall="no_documents"; confidence="low"
    elif failed: overall="attention_required"; confidence="moderate"
    elif incomplete or partial: overall="partially_ready"; confidence="moderate"
    else: overall="ready"; confidence="high"
    priorities=[]
    if failed: priorities.append({"priority":"high","action":"Review failed document-processing jobs and reprocess affected files.","reason":f"{failed} document(s) have failed processing signals."})
    if incomplete: priorities.append({"priority":"high","action":"Complete text extraction and chunk generation before relying on document search.","reason":f"{incomplete} document(s) are missing extracted text or searchable chunks."})
    if partial: priorities.append({"priority":"medium","action":"Run or review structured extraction for documents that are otherwise searchable.","reason":f"{partial} document(s) have text/search data but no structured extraction."})
    if not priorities: priorities.append({"priority":"low","action":"Continue validating important documents against approved source files.","reason":"No document-processing health gap was detected."})
    return {"status":overall,"confidence":confidence,"document_count":len(documents),"ready_count":ready,"failed_count":failed,"incomplete_count":incomplete,"partially_ready_count":partial,"status_counts":status_counts,"type_counts":type_counts,"documents":health,"warnings":warnings,"priorities":priorities,"note":"This is a read-only document-health assessment. It does not certify document completeness or replace review of the approved source file."}

def _recommendation(flag:str)->str:
    return {"document_processing_failed":"Inspect the document-processing error and reprocess the file.","latest_processing_job_failed":"Review the latest processing job error before relying on the file.","no_extracted_text":"Run text extraction or OCR and verify the extracted content.","no_search_chunks":"Generate searchable chunks after successful text extraction.","no_structured_extraction":"Run the appropriate construction-document extraction workflow.","invalid_page_count":"Verify the source file and processing metadata."}.get(flag,"Review the document processing record.")

def make_project_document_intelligence_tool(client, project_id:str):
    def get_project_document_intelligence()->dict[str,Any]:
        """Audit document-processing readiness for the authorized project."""
        documents=(client.table("documents").select("id,name,status,mime_type,file_size_bytes,file_sha256,created_at").eq("project_id",project_id).limit(MAX_DOCUMENTS).execute()).data or []
        if not documents: return build_document_intelligence([],[],[],[],[])
        ids=[r["id"] for r in documents]
        knowledge=(client.table("ai_knowledge_documents").select("document_id,extracted_text,page_count,language,status,updated_at").eq("project_id",project_id).limit(MAX_DOCUMENTS).execute()).data or []
        chunks=(client.table("ai_knowledge_chunks").select("document_id,chunk_index").in_("document_id",ids).limit(5000).execute()).data or []
        jobs=(client.table("document_processing_jobs").select("document_id,status,progress,error_message,created_at,completed_at").in_("document_id",ids).order("created_at",desc=True).limit(200).execute()).data or []
        extractions=(client.table("ai_extractions").select("document_id,extraction_type,created_at").in_("document_id",ids).limit(500).execute()).data or []
        return build_document_intelligence(documents,knowledge,chunks,jobs,extractions)
    return get_project_document_intelligence
