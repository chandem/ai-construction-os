/** Shared types for AI Construction OS Product UI. */
export type ProjectType = "road" | "building" | "bridge" | "water" | "utilities" | "industrial" | "other";
export const PROJECT_TYPE_OPTIONS: { value: ProjectType; label: string }[] = [
  { value: "road", label: "Road / Highway" },
  { value: "building", label: "Building" },
  { value: "bridge", label: "Bridge" },
  { value: "water", label: "Water / Irrigation" },
  { value: "utilities", label: "Utilities / Drainage" },
  { value: "industrial", label: "Industrial / Facility" },
  { value: "other", label: "Other civil construction" },
];
export type Project = { id: string; name: string; code?: string | null; project_type?: ProjectType | null };
export type Document = { id: string; name: string; mime_type?: string | null; status?: string | null; created_at?: string };
export type Source = { document_id: string; title?: string | null; page_number?: number | null; similarity?: number | null; citation: string };
export type Message = { role: "user" | "assistant"; content: string; sources?: Source[] };
export type Conversation = { id: string; title?: string | null; created_at?: string };
export type DesignAsset = { id: string; name: string; document_id?: string | null; discipline?: string | null; asset_type?: string | null; status?: string | null; created_at?: string };
export type WorkspaceView =
  | "os-home" | "assistant" | "design-center" | "cost-control" | "commercial" | "planning" | "procurement" | "inventory" | "payments"
  | "field" | "quality" | "gis" | "prediction" | "brain" | "integrations" | "ops";
