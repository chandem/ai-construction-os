import React from "react";
import { openDocumentFile } from "./documentFile";
import type { Document } from "./types";

type Props = {
  documents: Document[];
  documentJobs: Record<string, any>;
  reprocessingDocuments: Record<string, boolean>;
  deletingDocuments: Record<string, boolean>;
  token: string;
  onOpenError: (message: string) => void;
  onViewResults: (document: Document) => void;
  onReprocess: (documentId: string, documentName: string) => void;
  onDelete: (documentId: string, documentName: string) => void;
};

function readinessFor(document: Document, job: any, busy: boolean): string {
  if (busy) return "processing";
  if (job?.is_stalled) return "stalled";
  const statuses = [job?.status, document.status]
    .filter(Boolean)
    .map((value) => String(value).toLowerCase());

  if (statuses.some((status) => ["failed", "error"].includes(status))) return "failed";
  if (
    (Boolean(job?.error_message) && statuses.includes("completed")) ||
    statuses.some((status) => ["partial", "partially_processed", "partial_enrichment"].includes(status))
  ) return "partial";
  if (statuses.some((status) => ["queued", "pending", "processing"].includes(status)) ||
      Boolean(job?.progress && job.progress < 100)) return "processing";
  if (statuses.some((status) => ["completed", "processed", "ready"].includes(status))) return "ready";
  return "uploaded";
}

const LABELS: Record<string, string> = {
  ready: "Ready",
  partial: "Partial",
  processing: "Processing",
  stalled: "Taking longer",
  failed: "Failed",
  uploaded: "Uploaded",
};

function statusGuidance(readiness: string, job: any): string {
  if (readiness === "stalled") return "This job has been processing for over 45 minutes. It may be stalled; check service logs before retrying to avoid overlapping work.";\n  if (readiness === "stalled") return "This job has been processing for over 45 minutes. It may be stalled; check service logs before retrying to avoid overlapping work.";
  if (readiness !== "partial" && readiness !== "failed") return "";
  const detail = typeof job?.error_message === "string" ? job.error_message.trim() : "";
  if (detail) return detail;
  return readiness === "partial"
    ? "Some AI enrichment steps did not finish. Select Reprocess to retry."
    : "Document processing failed. Select Reprocess to try again.";
}

export function DocumentList({
  documents,
  documentJobs,
  reprocessingDocuments,
  deletingDocuments,
  token,
  onOpenError,
  onViewResults,
  onReprocess,
  onDelete,
}: Props) {
  if (!documents.length) {
    return <p className="doc-empty">No documents uploaded yet.</p>;
  }

  return (
    <div className="doc-list">
      {documents.map((d) => {
        const job = documentJobs[d.id];
        const busy = !!reprocessingDocuments[d.id];
        const deleting = !!deletingDocuments[d.id];
        const readiness = readinessFor(d, job, busy);
        const guidance = statusGuidance(readiness, job);
        return (
          <div key={d.id} className="document-row">
            <div className="document-row-main">
              <span className="document-name" title={d.name}>
                {d.name}
              </span>
              <span
                className={"doc-badge doc-badge-" + readiness}
                title={guidance || LABELS[readiness]}
                aria-label={LABELS[readiness] + (guidance ? ": " + guidance : "")}
              >
                {LABELS[readiness] || readiness}
              </span>
            </div>
            {guidance && (
              <p
                className="document-status-detail"
                title={guidance}
                style={{
                  margin: "0 0 8px",
                  color: readiness === "failed" ? "#b42318" : "#805b13",
                  fontSize: "12px",
                  lineHeight: 1.45,
                  overflowWrap: "anywhere",
                }}
              >
                {guidance}
              </p>
            )}
            <div className="document-row-actions">
              <button
                type="button"
                className="document-action"
                onClick={() =>
                  openDocumentFile(d.id, token, d.name).catch((err) =>
                    onOpenError(err.message || "Could not open file")
                  )
                }
              >
                Open
              </button>
              <button type="button" className="document-action" onClick={() => onViewResults(d)}>
                Results
              </button>
              <button
                type="button"
                className="document-action"
                onClick={() => onReprocess(d.id, d.name)}
                disabled={busy || deleting}
              >
                {busy ? "…" : "Reprocess"}
              </button>
              <button
                type="button"
                className="document-action document-action-danger"
                onClick={() => onDelete(d.id, d.name)}
                disabled={busy || deleting || readiness === "processing" || readiness === "stalled"}
                title={readiness === "processing" || readiness === "stalled" ? "Wait for processing to finish or verify the job has stopped before deleting" : "Permanently delete this document"}
                aria-label={"Delete document " + d.name}
              >
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
