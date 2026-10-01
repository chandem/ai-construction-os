import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function PredictionCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Prediction Center"
      endpoints={[
        { key: "summary", path: "/api/v1/projects/{id}/prediction/summary" },
      ]}
      actions={[
        {
          path: "/api/v1/projects/{id}/prediction/generate",
          label: "Generate risks & forecasts",
        },
      ]}
      emptyHint="Risks and forecasts need field progress, quality, and schedule signals. Generate after upstream modules have data."
    />
  );
}
