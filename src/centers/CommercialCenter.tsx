import React from "react";
import { CenterPanel } from "./CenterPanel";

type Props = { projectId: string; token: string };

export function CommercialCenter({ projectId, token }: Props) {
  return (
    <CenterPanel
      projectId={projectId}
      token={token}
      title="Commercial Center"
      endpoints={[
        { key: "tender", path: "/api/v1/projects/{id}/tender/packages" },
        { key: "contracts", path: "/api/v1/projects/{id}/contracts" },
      ]}
      actions={[
        {
          path: "/api/v1/projects/{id}/tender/packages/generate",
          label: "Generate tender packages",
        },
      ]}
      emptyHint="Tender packages are built from the estimate. Finish Design → BOQ → Estimate, then Generate tender packages."
    />
  );
}
