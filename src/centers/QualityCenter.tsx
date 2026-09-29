import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function QualityCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Quality Center"
      endpoints={[{ key: "summary", path: "/api/v1/projects/{id}/quality/summary" },{ key: "inspections", path: "/api/v1/projects/{id}/quality/inspections" },{ key: "ncrs", path: "/api/v1/projects/{id}/quality/ncrs" },{ key: "incidents", path: "/api/v1/projects/{id}/quality/incidents" }]}
      actions={[]}
    />
  );
}
