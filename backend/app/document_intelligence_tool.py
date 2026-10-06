from .document_intelligence_v2 import build_document_intelligence, build_project_document_intelligence


def make_project_document_intelligence_tool(client, project_id: str):
    def get_project_document_intelligence():
        documents = (
            client.table("documents")
            .select("id,name,mime_type,file_size_bytes,status")
            .eq("project_id", project_id)
            .limit(100)
            .execute()
        ).data or []

        results = []
        for document in documents:
            jobs = (
                client.table("document_processing_jobs")
                .select("status,progress,error_message,created_at")
                .eq("document_id", document["id"])
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            ).data or []
            job = jobs[0] if jobs else None

            knowledge_rows = (
                client.table("ai_knowledge_documents")
                .select("extracted_text,page_count,status")
                .eq("document_id", document["id"])
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            ).data or []
            knowledge = knowledge_rows[0] if knowledge_rows else None

            extraction_rows = (
                client.table("ai_extractions")
                .select("extraction_type,data,created_at")
                .eq("document_id", document["id"])
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            ).data or []
            extraction = extraction_rows[0] if extraction_rows else None

            chunk_rows = (
                client.table("ai_knowledge_chunks")
                .select("id")
                .eq("document_id", document["id"])
                .limit(5000)
                .execute()
            ).data or []

            results.append(
                build_document_intelligence(
                    document,
                    job,
                    knowledge,
                    extraction,
                    len(chunk_rows),
                )
            )

        summary = build_project_document_intelligence(results)
        summary["documents"] = results
        return summary

    return get_project_document_intelligence
