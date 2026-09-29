import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function ProcurementCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Procurement Center"
      endpoints={[{ key: "summary", path: "/api/v1/projects/{id}/procurement/summary" }]}
      actions={[{ path: "/api/v1/projects/{id}/procurement/generate", label: "Generate requirements" }]}
    />
  );
}
