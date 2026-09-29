import { supabase } from "./supabaseClient";

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

async function getFreshAccessToken(fallbackToken: string): Promise<string> {
  const { data, error } = await supabase.auth.getSession();
  if (!error && data.session?.access_token) return data.session.access_token;
  return fallbackToken;
}

async function refreshAccessToken(): Promise<string> {
  const { data, error } = await supabase.auth.refreshSession();
  if (error || !data.session?.access_token) {
    throw new Error("Your sign-in session has expired. Please sign in again.");
  }
  return data.session.access_token;
}

async function requestWithAuth(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<Response> {
  let accessToken = await getFreshAccessToken(token);
  let response = await fetch(API + path, {
    ...init,
    headers: {
      ...(init.headers || {}),
      Authorization: "Bearer " + accessToken,
    },
  });

  if (response.status === 401) {
    // The cached access token may have expired. Refresh once, then retry.
    accessToken = await refreshAccessToken();
    response = await fetch(API + path, {
      ...init,
      headers: {
        ...(init.headers || {}),
        Authorization: "Bearer " + accessToken,
      },
    });
  }

  return response;
}

export async function apiGet(path: string, token: string): Promise<any> {
  const r = await requestWithAuth(path, token);
  if (!r.ok) throw new Error(await readError(r, "Request failed"));
  return r.json();
}

export async function apiPost(path: string, token: string, body?: unknown): Promise<any> {
  const r = await requestWithAuth(path, token, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(await readError(r, "Request failed"));
  return r.json();
}

export async function apiUpload(path: string, token: string, body: FormData): Promise<any> {
  const r = await requestWithAuth(path, token, {
    method: "POST",
    body,
  });
  if (!r.ok) throw new Error(await readError(r, "Upload failed."));
  return r.json();
}
