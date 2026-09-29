import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function DesignCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Design Center"
      endpoints={[{ key: "elements", path: "/api/v1/projects/{id}/engineering/elements" },{ key: "quantities", path: "/api/v1/projects/{id}/engineering/quantities" },{ key: "boq", path: "/api/v1/projects/{id}/engineering/boq" },{ key: "estimate", path: "/api/v1/projects/{id}/engineering/estimate" },{ key: "design_to_cost", path: "/api/v1/projects/{id}/engineering/design-to-cost" }]}
      actions={[{ path: "/api/v1/projects/{id}/engineering/boq/generate", label: "Generate BOQ" },{ path: "/api/v1/projects/{id}/engineering/estimate/generate", label: "Generate estimate" }]}
    />
  );
}
