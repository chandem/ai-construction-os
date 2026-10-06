import { supabase } from "./supabaseClient";

const API = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export async function openDocumentFile(id: string, token: string, name: string) {
  const session = await supabase.auth.getSession();
  const access = session.data.session?.access_token || token;
  const response = await fetch(API + "/api/v1/documents/" + id + "/file", {
    headers: { Authorization: "Bearer " + access },
  });
  if (!response.ok) throw new Error("Could not open " + name);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const opened = window.open(url, "_blank", "noopener");
  if (!opened) {
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
