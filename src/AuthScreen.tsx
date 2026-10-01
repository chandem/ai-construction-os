import React from "react";
import { supabase, supabaseUrl, supabaseKey } from "./supabaseClient";

const benefits = [
  "Document intelligence for drawings, RFIs, and project records",
  "AI-assisted estimates, planning, and cost visibility",
  "Field, QA, and operations insights from the same project source",
];

export function AuthScreen() {
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
    <main className="center auth-shell">
      <section className="card login auth-panel">
        <div className="auth-hero">
          <div className="logo">AI</div>
          <div>
            <p className="eyebrow small">Construction intelligence platform</p>
            <h1>AI Construction OS</h1>
            <p className="muted hero-copy">
              One command center for project intelligence, document understanding, cost visibility, field reporting, and operational decisions.
            </p>
          </div>
        </div>

        <div className="value-grid">
          {benefits.map((item) => (
            <span key={item} className="feature-chip">{item}</span>
          ))}
        </div>

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
