/** Shared types for AI Construction OS Product UI. */
export type Project = { id: string; name: string; code?: string | null };
export type Document = { id: string; name: string; mime_type?: string | null; status?: string | null; created_at?: string };
export type Source = { document_id: string; title?: string | null; page_number?: number | null; similarity?: number | null; citation: string };
export type Message = { role: "user" | "assistant"; content: string; sources?: Source[] };
export type Conversation = { id: string; title?: string | null; created_at?: string };
export type DesignAsset = { id: string; name: string; document_id?: string | null; discipline?: string | null; asset_type?: string | null; status?: string | null; created_at?: string };
export type WorkspaceView =
  | "assistant" | "design-center" | "commercial" | "planning" | "procurement"
  | "field" | "quality" | "gis" | "prediction" | "brain" | "integrations" | "ops";
