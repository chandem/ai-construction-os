import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function IntegrationsCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Integrations"
      endpoints={[{ key: "summary", path: "/api/v1/projects/{id}/integrations/summary" }]}
      actions={[]}
    />
  );
}
