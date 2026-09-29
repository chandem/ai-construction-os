import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function OpsCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Ops Center"
      endpoints={[{ key: "summary", path: "/api/v1/projects/{id}/ops/summary" },{ key: "queue", path: "/api/v1/projects/{id}/ops/queue" },{ key: "cost", path: "/api/v1/projects/{id}/ops/cost" },{ key: "health", path: "/api/v1/projects/{id}/ops/health" }]}
      actions={[{ path: "/api/v1/projects/{id}/ops/queue?kind=document_pipeline", label: "Enqueue pipeline job" }]}
    />
  );
}
