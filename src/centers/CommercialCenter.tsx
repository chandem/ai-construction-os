import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function CommercialCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Commercial Center"
      endpoints={[{ key: "summary", path: "/api/v1/projects/{id}/commercial/summary" },{ key: "tenders", path: "/api/v1/projects/{id}/tender/packages" },{ key: "contracts", path: "/api/v1/projects/{id}/contracts" }]}
      actions={[{ path: "/api/v1/projects/{id}/tender/packages/generate", label: "Generate tender packages" }]}
    />
  );
}
