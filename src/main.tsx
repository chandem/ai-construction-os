import React from "react";
import { createRoot } from "react-dom/client";
import { createClient } from "@supabase/supabase-js";
import "./styles.css";

const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY
);

type Project = {
  id: string;
  name: string;
  code?: string | null;
};

type Source = {
  document_id: string;
  title?: string | null;
  page_number?: number | null;
  similarity?: number | null;
  citation: string;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
};

const API = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function AuthScreen() {
  const [mode, setMode] = React.useState<"login" | "signup">("login");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const [success, setSuccess] = React.useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();

    setError("");
    setSuccess("");

    if (!email.trim() || !password) {
      setError("Please enter your email and password.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);

    try {
      if (mode === "login") {
        const { error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });

        if (error) throw error;
      } else {
        const { error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
        });

        if (error) throw error;

        setSuccess(
          "Account created. Check your email if email confirmation is enabled."
        );
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="center">
      <section className="card login">
        <div className="logo">AI</div>

        <h1>AI Construction OS</h1>

        <p className="muted">
          AI-powered construction project intelligence.
        </p>

        <div className="auth-tabs">
          <button
            className={mode === "login" ? "active" : ""}
            onClick={() => {
              setMode("login");
              setError("");
              setSuccess("");
            }}
            type="button"
          >
            Login
          </button>

          <button
            className={mode === "signup" ? "active" : ""}
            onClick={() => {
              setMode("signup");
              setError("");
              setSuccess("");
            }}
            type="button"
          >
            Create account
          </button>
        </div>

        <form onSubmit={submit} className="auth-form">
          <label>Email</label>

          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
          />

          <label>Password</label>

          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
          />

          {error && <div className="error">{error}</div>}

          {success && <div className="success">{success}</div>}

          <button className="button primary" disabled={loading}>
            {loading
              ? "Please wait..."
              : mode === "login"
              ? "Login"
              : "Create account"}
          </button>
        </form>

        <p className="muted small">
          Your account is securely managed by Supabase Authentication.
        </p>
      </section>
    </main>
  );
}

function App() {
  const [session, setSession] = React.useState<any>(null);
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [projectId, setProjectId] = React.useState("");
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const [projectsLoading, setProjectsLoading] = React.useState(false);

  React.useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => subscription.unsubscribe();
  }, []);

  React.useEffect(() => {
    if (session) {
      loadProjects();
    } else {
      setProjects([]);
      setProjectId("");
    }
  }, [session]);

  async function loadProjects() {
    if (!session) return;

    setError("");
    setProjectsLoading(true);

    try {
      const response = await fetch(`${API}/api/v1/projects`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Could not load projects.");
      }

      const json = await response.json();
      const data = json.data || [];

      setProjects(data);

      if (!projectId && data.length > 0) {
        setProjectId(data[0].id);
      }
    } catch (err: any) {
      setError(err.message || "Could not load projects.");
    } finally {
      setProjectsLoading(false);
    }
  }

  async function send() {
    if (!input.trim() || !projectId || loading || !session) return;

    const question = input.trim();

    setInput("");
    setError("");

    setMessages((current) => [
      ...current,
      {
        role: "user",
        content: question,
      },
    ]);

    setLoading(true);

    try {
      const response = await fetch(
        `${API}/api/v1/projects/${projectId}/ai/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            message: question,
          }),
        }
      );

      const json = await response.json();

      if (!response.ok) {
        throw new Error(json.detail || "AI request failed.");
      }

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: json.answer,
          sources: json.sources || [],
        },
      ]);
    } catch (err: any) {
      setError(err.message || "AI request failed.");
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    await supabase.auth.signOut();
    setMessages([]);
  }

  if (!session) {
    return <AuthScreen />;
  }

  return (
    <div className="app">
      <header>
        <div>
          <strong>AI Construction OS</strong>
          <span>Construction Intelligence Platform</span>
        </div>

        <button onClick={signOut}>Sign out</button>
      </header>

      <main className="workspace">
        <aside>
          <h2>Project</h2>

          <label>Select project</label>

          <select
            value={projectId}
            onChange={(e) => {
              setProjectId(e.target.value);
              setMessages([]);
              setError("");
            }}
          >
            <option value="">
              {projectsLoading ? "Loading projects..." : "Select project"}
            </option>

            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
                {project.code ? ` · ${project.code}` : ""}
              </option>
            ))}
          </select>

          <div className="hint">
            <b>Construction AI</b>
            <br />
            Ask questions about contracts, BOQ, costs, schedules, materials,
            quality, safety, drawings and project documents.
          </div>

          {!projectsLoading && projects.length === 0 && (
            <div className="hint">
              No projects are available for this account yet.
            </div>
          )}
        </aside>

        <section className="chat">
          <div className="chathead">
            <h1>Construction AI Assistant</h1>

            <p>
              AI answers are grounded in the selected project's indexed
              construction documents.
            </p>
          </div>

          <div className="messages">
            {messages.length === 0 && (
              <div className="empty">
                <div className="spark">✦</div>

                <h3>Ask your project anything</h3>

                <p>
                  Example: "What does the contract say about the completion
                  period?"
                </p>
              </div>
            )}

            {messages.map((message, index) => (
              <article
                key={index}
                className={`message ${message.role}`}
              >
                <div>{message.content}</div>

                {message.sources && message.sources.length > 0 && (
                  <div className="sources">
                    <b>Sources</b>

                    {message.sources.map((source, sourceIndex) => (
                      <span key={sourceIndex}>
                        [Source {sourceIndex + 1}]{" "}
                        {source.title || source.document_id}
                        {source.page_number
                          ? ` · p.${source.page_number}`
                          : ""}
                      </span>
                    ))}
                  </div>
                )}
              </article>
            ))}

            {loading && (
              <article className="message assistant">
                <div className="typing">
                  Searching project knowledge and generating an answer…
                </div>
              </article>
            )}
          </div>

          <div className="composer">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder={
                projectId
                  ? "Ask a construction question..."
                  : "Select a project first"
              }
              disabled={!projectId || loading}
            />

            <button
              onClick={send}
              disabled={!projectId || !input.trim() || loading}
            >
              {loading ? "Thinking..." : "Ask AI"}
            </button>
          </div>

          {error && <div className="error">{error}</div>}
        </section>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
