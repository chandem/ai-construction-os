import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function IntegrationsCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Integrations Center"
      endpoints={[
        { key: "connectors", path: "/api/v1/projects/{id}/integrations/connectors" },
        { key: "summary", path: "/api/v1/projects/{id}/integrations/summary" },
      ]}
      actions={[]}
      emptyHint="No connectors configured yet. Integration status and sync health will show here when connectors are registered."
    />
  );
}
