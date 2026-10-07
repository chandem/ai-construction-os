-- Document text-search fallback
-- Preserve lexical retrieval when semantic embeddings are unavailable.

create or replace function public.match_ai_knowledge_chunks_text(
  search_query text,
  match_project_id uuid,
  match_count integer default 8
)
returns table (
  id uuid,
  document_id uuid,
  content text,
  page_number integer,
  similarity double precision
)
language sql
stable
set search_path = public
as $function$
  with query as (
    select websearch_to_tsquery('simple', search_query) as q
  )
  select
    c.id,
    c.document_id,
    c.content,
    c.page_number,
    least(
      1.0,
      ts_rank_cd(
        to_tsvector('simple', c.content),
        query.q
      ) * 10
    )::double precision as similarity
  from public.ai_knowledge_chunks c
  join public.ai_knowledge_documents d
    on d.id = c.knowledge_document_id
  cross join query
  where d.project_id = match_project_id
    and c.content is not null
    and query.q @@ to_tsvector('simple', c.content)
  order by similarity desc, c.chunk_index
  limit match_count;
$function$;
