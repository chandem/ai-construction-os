export const API = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export function formatApiError(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && "msg" in item) return String((item as { msg: string }).msg);
      return "";
    }).filter(Boolean);
    if (parts.length) return parts.join(" ");
  }
  return fallback;
}

export async function readError(response: Response, fallback: string): Promise<string> {
  try {
    const json = await response.json();
    return formatApiError(json.detail ?? json.message, fallback);
  } catch {
    return fallback;
  }
}

export async function apiGet(path: string, token: string): Promise<any> {
  const r = await fetch(API + path, { headers: { Authorization: "Bearer " + token } });
  if (!r.ok) throw new Error(await readError(r, "Request failed"));
  return r.json();
}

export async function apiPost(path: string, token: string, body?: unknown): Promise<any> {
  const r = await fetch(API + path, {
    method: "POST",
    headers: {
      Authorization: "Bearer " + token,
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(await readError(r, "Request failed"));
  return r.json();
}
