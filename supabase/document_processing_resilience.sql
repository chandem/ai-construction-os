-- Document processing resilience
-- Keep the database status constraint aligned with the processing pipeline.
-- The pipeline uses processing while work is running and partial when
-- extraction succeeded but AI enrichment/indexing is incomplete.

alter table public.ai_knowledge_documents
drop constraint if exists ai_knowledge_documents_status_check;

alter table public.ai_knowledge_documents
add constraint ai_knowledge_documents_status_check
check (
  status = any (
    array[
      'pending'::text,
      'processing'::text,
      'ready'::text,
      'partial'::text,
      'failed'::text
    ]
  )
);
