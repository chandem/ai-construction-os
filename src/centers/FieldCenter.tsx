import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function FieldCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Field Center"
      endpoints={[{ key: "summary", path: "/api/v1/projects/{id}/field/summary" },{ key: "diary", path: "/api/v1/projects/{id}/field/diary" },{ key: "progress", path: "/api/v1/projects/{id}/field/progress" }]}
      actions={[]}
    />
  );
}
