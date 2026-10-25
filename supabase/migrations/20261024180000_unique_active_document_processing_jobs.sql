-- Enforce at most one active processing job per document.
-- Deliberately fail with a clear message if historical duplicate active jobs
-- exist; operators must inspect them rather than silently deleting or changing jobs.
DO $$
BEGIN
    IF EXISTS (
        SELECT document_id
        FROM public.document_processing_jobs
        WHERE status IN ('queued', 'processing')
        GROUP BY document_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Cannot create unique active-job index: duplicate queued/processing jobs exist. Inspect document_processing_jobs and resolve duplicates manually before retrying this migration.';
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS
    uq_document_processing_jobs_one_active_per_document
ON public.document_processing_jobs (document_id)
WHERE status IN ('queued', 'processing');
