import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function GisCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="GIS Center"
      endpoints={[{ key: "summary", path: "/api/v1/projects/{id}/gis/summary" }]}
      actions={[{ path: "/api/v1/projects/{id}/gis/assets/from-elements", label: "Assets from elements" }]}
    />
  );
}
