import React from "react";
import { openDocumentFile } from "./documentFile";
import type { Document } from "./types";

type Props = {
  documents: Document[];
  documentJobs: Record<string, any>;
  reprocessingDocuments: Record<string, boolean>;
  token: string;
  onOpenError: (message: string) => void;
  onViewResults: (document: Document) => void;
  onReprocess: (documentId: string, documentName: string) => void;
};

function readinessFor(document: Document, job: any, busy: boolean): string {
  const jobStatus = String(job?.status || document.status || "uploaded").toLowerCase();
  const partial = jobStatus === "completed" && !!job?.error_message;
  if (busy || jobStatus === "queued" || jobStatus === "processing") return "processing";
  if (jobStatus === "failed") return "failed";
  if (partial) return "partial";
  if (jobStatus === "completed" || jobStatus === "processed" || jobStatus === "ready") return "ready";
  return "uploaded";
}

const LABELS: Record<string, string> = {
  ready: "Ready",
  partial: "Partial",
  processing: "Processing",
  failed: "Failed",
  uploaded: "Uploaded",
};

export function DocumentList({
  documents,
  documentJobs,
  reprocessingDocuments,
  token,
  onOpenError,
  onViewResults,
  onReprocess,
}: Props) {
  if (!documents.length) {
    return <p className="doc-empty">No documents uploaded yet.</p>;
  }

  return (
    <div className="doc-list">
      {documents.map((d) => {
        const job = documentJobs[d.id];
        const busy = !!reprocessingDocuments[d.id];
        const readiness = readinessFor(d, job, busy);
        return (
          <div key={d.id} className="document-row">
            <div className="document-row-main">
              <span className="document-name" title={d.name}>
                {d.name}
              </span>
              <span className={"doc-badge doc-badge-" + readiness}>
                {LABELS[readiness] || readiness}
              </span>
            </div>
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
                disabled={busy}
              >
                {busy ? "…" : "Reprocess"}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
