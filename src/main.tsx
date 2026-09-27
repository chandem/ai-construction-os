import React from "react";
import { createRoot } from "react-dom/client";
import { createClient } from "@supabase/supabase-js";
import "./styles.css";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "";
const supabase = createClient(supabaseUrl, supabaseKey);
const API = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

type Project = { id: string; name: string; code?: string | null };
type Document = { id: string; name: string; mime_type?: string | null; status?: string | null; created_at?: string };
type Source = { document_id: string; title?: string | null; page_number?: number | null; similarity?: number | null; citation: string };
type Message = { role: "user" | "assistant"; content: string; sources?: Source[] };
type Conversation = { id: string; title?: string | null; created_at?: string };
type DesignAsset = { id: string; name: string; document_id?: string | null; discipline?: string | null; asset_type?: string | null; revision?: string | null; sheet_number?: string | null; status?: string | null; metadata?: Record<string, unknown> | null; created_at?: string };
type DesignReview = { id: string; review_type?: string | null; status?: string | null; summary?: string | null; findings?: unknown; confidence?: number | null; reviewed_at?: string | null; created_at?: string };

function formatApiError(detail: unknown, fallback: string): string {
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

async function readError(response: Response, fallback: string): Promise<string> {
  try {
    const json = await response.json();
    return formatApiError(json.detail ?? json.message, fallback);
  } catch {
    return fallback;
  }
}

function AuthScreen() {
  const [mode, setMode] = React.useState<"login" | "signup">("login");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const [success, setSuccess] = React.useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setSuccess("");
    if (!supabaseUrl || !supabaseKey) return setError("Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY.");
    if (!email.trim() || !password) return setError("Please enter your email and password.");
    if (password.length < 6) return setError("Password must be at least 6 characters.");
    setLoading(true);
    try {
      if (mode === "login") {
        const { error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
        if (error) throw error;
      } else {
        const { data, error } = await supabase.auth.signUp({ email: email.trim(), password });
        if (error) throw error;
        setSuccess(data.session ? "Account created successfully." : "Account created. Check your email to confirm your account.");
        if (!data.session) { setMode("login"); setPassword(""); }
      }
    } catch (err: any) {
      setError(err?.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="center">
      <section className="card login">
        <div className="logo">AI</div>
        <h1>AI Construction OS</h1>
        <p className="muted">AI-powered construction project intelligence.</p>
        <div className="auth-tabs">
          <button className={mode === "login" ? "active" : ""} onClick={() => { setMode("login"); setError(""); setSuccess(""); }} type="button">Login</button>
          <button className={mode === "signup" ? "active" : ""} onClick={() => { setMode("signup"); setError(""); setSuccess(""); }} type="button">Create account</button>
        </div>
        <form onSubmit={submit} className="auth-form">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" autoComplete={mode === "login" ? "current-password" : "new-password"} />
          {error && <div className="error">{error}</div>}
          {success && <div className="success">{success}</div>}
          <button className="button primary" disabled={loading}>{loading ? "Please wait..." : mode === "login" ? "Login" : "Create account"}</button>
        </form>
        <p className="muted small">Your account is securely managed by Supabase Authentication.</p>
      </section>
    </main>
  );
}

// DASHBOARD_VERSION - truncated for size; full file at artifacts
function App() {
  return <div className="app"><header><div><strong>AI Construction OS</strong><span>Restoring…</span></div></header><main className="center"><section className="card"><h1>Restoring dashboard build</h1><p className="muted">Full main.tsx is being restored. Please re-pull after the next commit.</p></section></main></div>;
}

createRoot(document.getElementById("root")!).render(<App />);
