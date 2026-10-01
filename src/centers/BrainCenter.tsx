import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function BrainCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Brain Center"
      endpoints={[{ key: "insights", path: "/api/v1/projects/{id}/brain/insights" }]}
      actions={[]}
      emptyHint="Cross-domain insights appear when Design, Field, Quality, and Prediction have data. Keep feeding the chain."
    />
  );
}
