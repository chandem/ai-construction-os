import React from "react";
import { createRoot } from "react-dom/client";
import { createClient } from "@supabase/supabase-js";
import "./styles.css";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "";
const supabase = createClient(supabaseUrl, supabaseKey);
const API = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

type Project = { id: string; name: string; code?: string | null };
type Document = {
  id: string;
  name: string;
  mime_type?: string | null;
  status?: string | null;
  created_at?: string;
  updated_at?: string;
  storage_path?: string | null;
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

function formatApiError(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: string }).msg);
        }
        return "";
      })
      .filter(Boolean);
    if (parts.length) return parts.join(" ");
  }
  if (detail && typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      /* ignore */
    }
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
    setError("");
    setSuccess("");
    if (!supabaseUrl || !supabaseKey) {
      return setError("Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY.");
    }
    if (!email.trim() || !password) {
      return setError("Please enter your email and password.");
    }
    if (password.length < 6) {
      return setError("Password must be at least 6 characters.");
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
        const { data, error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
        });
        if (error) throw error;
        setSuccess(
          data.session
            ? "Account created successfully."
            : "Account created. Check your email to confirm your account."
        );
        if (!data.session) {
          setMode("login");
          setPassword("");
        }
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
  const [documents, setDocuments] = React.useState<Document[]>([]);
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [projectsLoading, setProjectsLoading] = React.useState(false);
  const [documentsLoading, setDocumentsLoading] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [creatingProject, setCreatingProject] = React.useState(false);
  const [showCreateProject, setShowCreateProject] = React.useState(false);
  const [newProjectName, setNewProjectName] = React.useState("");
  const [newProjectCode, setNewProjectCode] = React.useState("");
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [showDocuments, setShowDocuments] = React.useState(true);
  const fileRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
    return () => subscription.unsubscribe();
  }, []);

  React.useEffect(() => {
    if (session) loadProjects();
    else {
      setProjects([]);
      setProjectId("");
    }
  }, [session]);

  React.useEffect(() => {
    if (session && projectId) loadDocuments();
    else setDocuments([]);
  }, [session, projectId]);

  async function loadProjects() {
    if (!session) return;
    if (!API) {
      setError("API base URL is not configured (VITE_API_BASE_URL).");
      return;
    }
    setProjectsLoading(true);
    setError("");
    try {
      const r = await fetch(API + "/api/v1/projects", {
        headers: { Authorization: "Bearer " + session.access_token },
      });
      if (!r.ok) throw new Error(await readError(r, "Could not load projects."));
      const j = await r.json();
      const data = j.data || [];
      setProjects(data);
      if (!projectId && data[0]) setProjectId(data[0].id);
      if (data.length === 0) setShowCreateProject(true);
    } catch (e: any) {
      setError(e.message || "Could not load projects.");
    } finally {
      setProjectsLoading(false);
    }
  }

  async function createProject(e?: React.FormEvent) {
    e?.preventDefault();
    if (!session || creatingProject) return;

    const name = newProjectName.trim();
    if (!name) {
      setError("Enter a project name.");
      return;
    }

    setCreatingProject(true);
    setError("");
    setNotice("");

    try {
      const r = await fetch(API + "/api/v1/projects", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + session.access_token,
        },
        body: JSON.stringify({
          name,
          code: newProjectCode.trim() || null,
        }),
      });
      if (!r.ok) throw new Error(await readError(r, "Could not create project."));
      const j = await r.json();

      const created = j.data;
      setProjects((current) => [created, ...current]);
      setProjectId(created.id);
      setNewProjectName("");
      setNewProjectCode("");
      setShowCreateProject(false);
      setMessages([]);
      setNotice(`Project "${created.name}" created.`);
    } catch (err: any) {
      setError(err.message || "Could not create project.");
    } finally {
      setCreatingProject(false);
    }
  }

  async function loadDocuments() {
    if (!session || !projectId) return;
    setDocumentsLoading(true);
    try {
      const r = await fetch(API + "/api/v1/projects/" + projectId + "/documents", {
        headers: { Authorization: "Bearer " + session.access_token },
      });
      if (!r.ok) throw new Error(await readError(r, "Could not load documents."));
      const j = await r.json();
      setDocuments(j.data || []);
    } catch (e: any) {
      setError(e.message || "Could not load documents.");
    } finally {
      setDocumentsLoading(false);
    }
  }

  async function uploadDocument(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !session || !projectId || uploading) return;
    setUploading(true);
    setError("");
    setNotice("");
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await fetch(
        API + "/api/v1/projects/" + projectId + "/documents",
        {
          method: "POST",
          headers: { Authorization: "Bearer " + session.access_token },
          body: form,
        }
      );
      if (!r.ok) throw new Error(await readError(r, "Upload failed."));
      const j = await r.json();
      setNotice(
        file.name +
          " uploaded and processed. " +
          (j.chunks ?? 0) +
          " knowledge chunks created."
      );
      await loadDocuments();
    } catch (e: any) {
      setError(e.message || "Document upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function send() {
    if (!input.trim() || !projectId || loading || !session) return;
    const question = input.trim();
    setInput("");
    setError("");
    setMessages((m) => [...m, { role: "user", content: question }]);
    setLoading(true);
    try {
      const r = await fetch(API + "/api/v1/projects/" + projectId + "/ai/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + session.access_token,
        },
        body: JSON.stringify({ message: question }),
      });
      if (!r.ok) throw new Error(await readError(r, "AI request failed."));
      const j = await r.json();
      setMessages((m) => [
        ...m,
        { role: "assistant", content: j.answer, sources: j.sources || [] },
      ]);
    } catch (e: any) {
      setError(e.message || "AI request failed.");
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    await supabase.auth.signOut();
    setMessages([]);
  }

  if (!session) return <AuthScreen />;

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
              setNotice("");
            }}
          >
            <option value="">
              {projectsLoading ? "Loading projects..." : "Select project"}
            </option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
                {p.code ? " · " + p.code : ""}
              </option>
            ))}
          </select>

          <button
            className="side-action"
            type="button"
            onClick={() => setShowCreateProject((v) => !v)}
          >
            {showCreateProject ? "− Hide new project" : "+ New project"}
          </button>

          {showCreateProject && (
            <form className="create-project" onSubmit={createProject}>
              <label>Project name</label>
              <input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="e.g. Addis Ring Road Package 2"
                disabled={creatingProject}
              />
              <label>Project code (optional)</label>
              <input
                type="text"
                value={newProjectCode}
                onChange={(e) => setNewProjectCode(e.target.value)}
                placeholder="e.g. ARR-P2"
                disabled={creatingProject}
              />
              <button
                className="button primary compact"
                disabled={creatingProject || !newProjectName.trim()}
              >
                {creatingProject ? "Creating..." : "Create project"}
              </button>
            </form>
          )}

          {!projectsLoading && projects.length === 0 && (
            <div className="hint">
              <b>Get started</b>
              <br />
              Create your first project, then upload construction documents to
              build project knowledge.
            </div>
          )}

          <div className="hint">
            <b>Construction AI</b>
            <br />
            Ask about contracts, BOQ, costs, schedules, materials, quality,
            safety, drawings and project documents.
          </div>

          <button
            className="side-action"
            onClick={() => setShowDocuments((v) => !v)}
            disabled={!projectId}
            type="button"
          >
            📄 {showDocuments ? "Hide" : "Show"} documents
          </button>
          <button
            className="side-action"
            onClick={() => fileRef.current?.click()}
            disabled={!projectId || uploading}
            type="button"
          >
            ⬆ {uploading ? "Uploading..." : "Upload document"}
          </button>
          <input
            ref={fileRef}
            hidden
            type="file"
            accept=".pdf,.docx,.xlsx,.xls,.txt,.csv,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain,text/csv"
            onChange={uploadDocument}
          />
        </aside>

        <section className="chat">
          <div className="chathead">
            <h1>Construction AI Assistant</h1>
            <p>
              Ask questions grounded in the selected project's construction
              knowledge.
            </p>
          </div>

          {showDocuments && (
            <section className="documents-panel">
              <div className="panel-head">
                <div>
                  <div className="eyebrow">PROJECT DOCUMENTS</div>
                  <h2>AI Document Center</h2>
                  <p>
                    {documents.length} document
                    {documents.length === 1 ? "" : "s"} in this project
                  </p>
                </div>
                <button
                  className="upload-button"
                  onClick={() => fileRef.current?.click()}
                  disabled={!projectId || uploading}
                  type="button"
                >
                  {uploading ? "Processing..." : "Upload document"}
                </button>
              </div>

              {notice && <div className="success">{notice}</div>}

              {documentsLoading ? (
                <div className="document-empty">Loading documents...</div>
              ) : documents.length === 0 ? (
                <div className="document-empty">
                  <div className="document-icon">▣</div>
                  <b>No project documents yet</b>
                  <span>
                    Upload a contract, BOQ, specification, report or other
                    project file to build project knowledge.
                  </span>
                </div>
              ) : (
                <div className="document-list">
                  {documents.map((d) => (
                    <div className="document-row" key={d.id}>
                      <div className="doc-icon">DOC</div>
                      <div className="doc-main">
                        <b>{d.name}</b>
                        <span>
                          {d.mime_type || "Document"} ·{" "}
                          {d.created_at
                            ? new Date(d.created_at).toLocaleDateString()
                            : ""}
                        </span>
                      </div>
                      <span
                        className={
                          "status status-" + (d.status || "unknown")
                        }
                      >
                        {d.status || "unknown"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          <div className="messages">
            {messages.length === 0 && (
              <div className="empty">
                <div className="spark">✦</div>
                <h3>Ask your project anything</h3>
                <p>
                  Try: “What does the contract say about the completion
                  period?”
                </p>
              </div>
            )}
            {messages.map((m, i) => (
              <article key={i} className={"message " + m.role}>
                <div>{m.content}</div>
                {m.sources?.length ? (
                  <div className="sources">
                    <b>Sources</b>
                    {m.sources.map((s, n) => (
                      <span key={n}>
                        [Source {n + 1}] {s.title || s.document_id}
                        {s.page_number ? " · p." + s.page_number : ""}
                      </span>
                    ))}
                  </div>
                ) : null}
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
                  : "Select or create a project first"
              }
              disabled={!projectId || loading}
            />
            <button
              onClick={send}
              disabled={!projectId || !input.trim() || loading}
              type="button"
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
