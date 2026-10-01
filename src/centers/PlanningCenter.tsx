import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function PlanningCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Planning Center"
      endpoints={[
        { key: "summary", path: "/api/v1/projects/{id}/planning/summary" },
        { key: "wbs", path: "/api/v1/projects/{id}/planning/wbs" },
        { key: "schedule", path: "/api/v1/projects/{id}/planning/schedule" },
      ]}
      actions={[
        { path: "/api/v1/projects/{id}/planning/wbs/generate", label: "Generate WBS" },
        { path: "/api/v1/projects/{id}/planning/schedule/generate", label: "Generate schedule" },
      ]}
      emptyHint="WBS and schedule are generated from the estimate / BOQ chain. Complete Design → BOQ → Estimate first, then Generate WBS."
    />
  );
}
