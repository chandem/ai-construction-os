import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function OpsCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Ops Center"
      endpoints={[
        { key: "summary", path: "/api/v1/projects/{id}/ops/summary" },
        { key: "queue", path: "/api/v1/projects/{id}/ops/queue" },
        { key: "health", path: "/api/v1/projects/{id}/ops/health" },
        { key: "cost", path: "/api/v1/projects/{id}/ops/cost" },
      ]}
      actions={[]}
      emptyHint="Ops shows job queue, cost events, and system health. Document processing jobs appear here after uploads."
    />
  );
}
