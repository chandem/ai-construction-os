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
type DesignAsset = { id: string; name: string; discipline?: string | null; asset_type?: string | null; revision?: string | null; sheet_number?: string | null; status?: string | null; created_at?: string };

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

function App() {
  const [session, setSession] = React.useState<any>(null);
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [projectId, setProjectId] = React.useState("");
  const [documents, setDocuments] = React.useState<Document[]>([]);
  const [designAssets, setDesignAssets] = React.useState<DesignAsset[]>([]);
  const [conversations, setConversations] = React.useState<Conversation[]>([]);
  const [conversationId, setConversationId] = React.useState("");
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [projectsLoading, setProjectsLoading] = React.useState(false);
  const [documentsLoading, setDocumentsLoading] = React.useState(false);
  const [designLoading, setDesignLoading] = React.useState(false);
  const [conversationsLoading, setConversationsLoading] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [creatingProject, setCreatingProject] = React.useState(false);
  const [showCreateProject, setShowCreateProject] = React.useState(false);
  const [newProjectName, setNewProjectName] = React.useState("");
  const [newProjectCode, setNewProjectCode] = React.useState("");
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [showDocuments, setShowDocuments] = React.useState(true);
  const [showDesign, setShowDesign] = React.useState(true);
  const [extraction, setExtraction] = React.useState<any>(null);
  const fileRef = React.useRef<HTMLInputElement>(null);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => subscription.unsubscribe();
  }, []);

  React.useEffect(() => {
    if (session) loadProjects();
    else { setProjects([]); setProjectId(""); }
  }, [session]);

  React.useEffect(() => {
    if (session && projectId) { loadDocuments(); loadConversations(); loadDesignAssets(); }
    else { setDocuments([]); setConversations([]); setDesignAssets([]); setConversationId(""); setMessages([]); setExtraction(null); }
  }, [session, projectId]);

  React.useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  async function loadProjects() {
    if (!session) return;
    if (!API) { setError("API base URL is not configured (VITE_API_BASE_URL)."); return; }
    setProjectsLoading(true); setError("");
    try {
      const r = await fetch(API + "/api/v1/projects", { headers: { Authorization: "Bearer " + session.access_token } });
      if (!r.ok) throw new Error(await readError(r, "Could not load projects."));
      const j = await r.json(); const data = j.data || [];
      setProjects(data);
      if (!projectId && data[0]) setProjectId(data[0].id);
      if (data.length === 0) setShowCreateProject(true);
    } catch (e: any) { setError(e.message || "Could not load projects."); }
    finally { setProjectsLoading(false); }
  }

  async function createProject(e?: React.FormEvent) {
    e?.preventDefault();
    if (!session || creatingProject) return;
    const name = newProjectName.trim();
    if (!name) { setError("Enter a project name."); return; }
    setCreatingProject(true); setError(""); setNotice("");
    try {
      const r = await fetch(API + "/api/v1/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + session.access_token },
        body: JSON.stringify({ name, code: newProjectCode.trim() || null }),
      });
      if (!r.ok) throw new Error(await readError(r, "Could not create project."));
      const j = await r.json(); const created = j.data;
      setProjects((c) => [created, ...c]); setProjectId(created.id);
      setNewProjectName(""); setNewProjectCode(""); setShowCreateProject(false);
      setMessages([]); setConversationId(""); setNotice(`Project "${created.name}" created.`);
    } catch (err: any) { setError(err.message || "Could not create project."); }
    finally { setCreatingProject(false); }
  }

  async function loadDocuments() {
    if (!session || !projectId) return;
    setDocumentsLoading(true);
    try {
      const r = await fetch(API + "/api/v1/projects/" + projectId + "/documents", { headers: { Authorization: "Bearer " + session.access_token } });
      if (!r.ok) throw new Error(await readError(r, "Could not load documents."));
      setDocuments((await r.json()).data || []);
    } catch (e: any) { setError(e.message || "Could not load documents."); }
    finally { setDocumentsLoading(false); }
  }

  async function loadDesignAssets() {
    if (!session || !projectId) return;
    setDesignLoading(true);
    try {
      const r = await fetch(API + "/api/v1/projects/" + projectId + "/design/assets", { headers: { Authorization: "Bearer " + session.access_token } });
      if (!r.ok) throw new Error(await readError(r, "Could not load design assets."));
      setDesignAssets((await r.json()).data || []);
    } catch (e: any) { console.warn(e.message || e); }
    finally { setDesignLoading(false); }
  }

  async function viewExtraction(documentId: string) {
    if (!session || !documentId) return;
    setError(""); setExtraction(null);
    try {
      const r = await fetch(API + "/api/v1/documents/" + documentId + "/extraction", { headers: { Authorization: "Bearer " + session.access_token } });
      if (!r.ok) throw new Error(await readError(r, "No AI extraction available for this document."));
      setExtraction(await r.json());
    } catch (e: any) { setError(e.message || "Could not load extraction."); }
  }

  async function loadConversations() {
    if (!session || !projectId) return;
    setConversationsLoading(true);
    try {
      const r = await fetch(API + "/api/v1/projects/" + projectId + "/ai/conversations", { headers: { Authorization: "Bearer " + session.access_token } });
      if (!r.ok) throw new Error(await readError(r, "Could not load conversations."));
      setConversations((await r.json()).data || []);
    } catch (e: any) { console.warn(e.message || e); }
    finally { setConversationsLoading(false); }
  }

  async function openConversation(id: string) {
    if (!session || !id) return;
    setConversationId(id); setError(""); setLoading(true);
    try {
      const r = await fetch(API + "/api/v1/ai/conversations/" + id + "/messages", { headers: { Authorization: "Bearer " + session.access_token } });
      if (!r.ok) throw new Error(await readError(r, "Could not load messages."));
      const rows = ((await r.json()).data || []) as { role: string; content: string }[];
      setMessages(rows.filter((m) => m.role === "user" || m.role === "assistant").map((m) => ({ role: m.role as "user" | "assistant", content: m.content })));
    } catch (e: any) { setError(e.message || "Could not load conversation."); }
    finally { setLoading(false); }
  }

  function startNewChat() { setConversationId(""); setMessages([]); setError(""); setNotice(""); }

  async function uploadDocument(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; e.target.value = "";
    if (!file || !session || !projectId || uploading) return;
    setUploading(true); setError(""); setNotice("");
    try {
      const form = new FormData(); form.append("file", file);
      const r = await fetch(API + "/api/v1/projects/" + projectId + "/documents", { method: "POST", headers: { Authorization: "Bearer " + session.access_token }, body: form });
      if (!r.ok) throw new Error(await readError(r, "Upload failed."));
      const j = await r.json();
      setNotice(file.name + " uploaded and processed. " + (j.chunks ?? 0) + " knowledge chunks created.");
      await loadDocuments(); await loadDesignAssets();
    } catch (e: any) { setError(e.message || "Document upload failed."); }
    finally { setUploading(false); }
  }

  async function send() {
    if (!input.trim() || !projectId || loading || !session) return;
    const question = input.trim(); setInput(""); setError("");
    setMessages((m) => [...m, { role: "user", content: question }]); setLoading(true);
    try {
      const body: { message: string; conversation_id?: string } = { message: question };
      if (conversationId) body.conversation_id = conversationId;
      const r = await fetch(API + "/api/v1/projects/" + projectId + "/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + session.access_token },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(await readError(r, "AI request failed."));
      const j = await r.json();
      if (j.conversation_id) setConversationId(j.conversation_id);
      setMessages((m) => [...m, { role: "assistant", content: j.answer, sources: j.sources || [] }]);
      if (j.conversation_id && j.title) {
        setConversations((list) => {
          const exists = list.some((c) => c.id === j.conversation_id);
          if (exists) return list.map((c) => (c.id === j.conversation_id ? { ...c, title: j.title } : c));
          return [{ id: j.conversation_id, title: j.title, created_at: new Date().toISOString() }, ...list];
        });
      } else await loadConversations();
    } catch (e: any) { setError(e.message || "AI request failed."); }
    finally { setLoading(false); }
  }

  async function signOut() { await supabase.auth.signOut(); setMessages([]); setConversationId(""); }

  const selectedProject = projects.find((p) => p.id === projectId) || null;
  if (!session) return <AuthScreen />;

  return (
    <div className="app">
      <header>
        <div><strong>AI Construction OS</strong><span>Construction Intelligence Platform</span></div>
        <button onClick={signOut}>Sign out</button>
      </header>
      <main className="workspace">
        <aside>
          <h2>Project</h2>
          <label>Select project</label>
          <select value={projectId} onChange={(e) => { setProjectId(e.target.value); setMessages([]); setConversationId(""); setError(""); setNotice(""); }}>
            <option value="">{projectsLoading ? "Loading projects..." : "Select project"}</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}{p.code ? " · " + p.code : ""}</option>)}
          </select>
          <button className="side-action" type="button" onClick={() => setShowCreateProject((v) => !v)}>{showCreateProject ? "− Hide new project" : "+ New project"}</button>
          {showCreateProject && (
            <form className="create-project" onSubmit={createProject}>
              <label>Project name</label>
              <input type="text" value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} placeholder="e.g. Addis Ring Road Package 2" disabled={creatingProject} />
              <label>Project code (optional)</label>
              <input type="text" value={newProjectCode} onChange={(e) => setNewProjectCode(e.target.value)} placeholder="e.g. ARR-P2" disabled={creatingProject} />
              <button className="button primary compact" disabled={creatingProject || !newProjectName.trim()}>{creatingProject ? "Creating..." : "Create project"}</button>
            </form>
          )}
          {!projectsLoading && projects.length === 0 && (<div className="hint"><b>Get started</b><br />Create your first project, then upload construction documents to build project knowledge.</div>)}
          <div className="chat-history">
            <div className="chat-history-head"><span>Chat history</span><button type="button" onClick={startNewChat} disabled={!projectId}>New</button></div>
            {conversationsLoading && <div className="chat-history-empty">Loading…</div>}
            {!conversationsLoading && conversations.length === 0 && <div className="chat-history-empty">No conversations yet</div>}
            <div className="chat-history-list">
              {conversations.map((c) => (
                <button key={c.id} type="button" className={"chat-history-item" + (c.id === conversationId ? " active" : "")} onClick={() => openConversation(c.id)}>
                  <b>{c.title || "Construction AI chat"}</b>
                  <span>{c.created_at ? new Date(c.created_at).toLocaleString() : ""}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="hint"><b>Construction AI</b><br />Ask about contracts, BOQ, costs, schedules, materials, quality, safety, drawings and project documents.</div>
          <button className="side-action" onClick={() => setShowDocuments((v) => !v)} disabled={!projectId} type="button">📄 {showDocuments ? "Hide" : "Show"} documents</button>
          <button className="side-action" onClick={() => setShowDesign((v) => !v)} disabled={!projectId} type="button">📐 {showDesign ? "Hide" : "Show"} design assets</button>
          <button className="side-action" onClick={() => fileRef.current?.click()} disabled={!projectId || uploading} type="button">⬆ {uploading ? "Uploading..." : "Upload document"}</button>
          <input ref={fileRef} hidden type="file" accept=".pdf,.docx,.xlsx,.xls,.txt,.csv,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain,text/csv" onChange={uploadDocument} />
        </aside>
        <section className="chat">
          <div className="chathead">
            <h1>Construction AI Assistant</h1>
            <p>{conversationId ? "Continuing a saved conversation grounded in project documents." : "Ask questions grounded in the selected project's construction knowledge."}</p>
            {projectId && (
              <div className="project-summary">
                <span><b>{selectedProject?.name || "Project"}</b>{selectedProject?.code ? ` · ${selectedProject.code}` : ""}</span>
                <span>{documents.length} docs</span>
                <span>{designAssets.length} design</span>
                <span>{conversations.length} chats</span>
                <span>{documents.filter((d) => d.status === "processed" || d.status === "completed").length} ready</span>
              </div>
            )}
          </div>
          {showDocuments && (
            <section className="documents-panel">
              <div className="panel-head">
                <div><div className="eyebrow">PROJECT DOCUMENTS</div><h2>AI Document Center</h2><p>{documents.length} document{documents.length === 1 ? "" : "s"} in this project</p></div>
                <button className="upload-button" onClick={() => fileRef.current?.click()} disabled={!projectId || uploading} type="button">{uploading ? "Processing..." : "Upload document"}</button>
              </div>
              {notice && <div className="success">{notice}</div>}
              {documentsLoading ? <div className="document-empty">Loading documents...</div> : documents.length === 0 ? (
                <div className="document-empty"><div className="document-icon">▣</div><b>No project documents yet</b><span>Upload a contract, BOQ, specification, report or other project file to build project knowledge.</span></div>
              ) : (
                <div className="document-list">
                  {documents.map((d) => (
                    <button className="document-row" key={d.id} type="button" onClick={() => viewExtraction(d.id)} title="View AI extraction">
                      <div className="doc-icon">DOC</div>
                      <div className="doc-main"><b>{d.name}</b><span>{d.mime_type || "Document"} · {d.created_at ? new Date(d.created_at).toLocaleDateString() : ""}</span></div>
                      <span className={"status status-" + (d.status || "unknown")}>{d.status || "unknown"}</span>
                    </button>
                  ))}
                </div>
              )}
            </section>
          )}
          {showDesign && (
            <section className="documents-panel design-panel">
              <div className="panel-head"><div><div className="eyebrow">ENGINEERING</div><h2>Design Assets</h2><p>{designAssets.length} asset{designAssets.length === 1 ? "" : "s"} from drawings and specs</p></div></div>
              {designLoading ? <div className="document-empty">Loading design assets...</div> : designAssets.length === 0 ? (
                <div className="document-empty"><div className="document-icon">📐</div><b>No design assets yet</b><span>Upload drawings or specifications and AI will promote them into design assets when detected.</span></div>
              ) : (
                <div className="document-list">
                  {designAssets.map((a) => (
                    <div className="document-row" key={a.id}>
                      <div className="doc-icon">DSN</div>
                      <div className="doc-main"><b>{a.name}</b><span>{[a.discipline, a.asset_type, a.revision ? "Rev " + a.revision : null, a.sheet_number].filter(Boolean).join(" · ")}</span></div>
                      <span className={"status status-" + (a.status || "unknown")}>{a.status || "unknown"}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
          {extraction && (
            <section className="extraction-panel">
              <div className="panel-head">
                <div><div className="eyebrow">AI EXTRACTION</div><h2>{extraction.extraction_type || "Document insights"}</h2><p>{extraction.data?.summary || "Structured facts extracted from the selected document."}</p></div>
                <button className="upload-button" type="button" onClick={() => setExtraction(null)}>Close</button>
              </div>
              {extraction.data && <pre className="extraction-json">{JSON.stringify(extraction.data, null, 2)}</pre>}
            </section>
          )}
          <div className="messages">
            {messages.length === 0 && !loading && (<div className="empty"><div className="spark">✦</div><h3>Ask your project anything</h3><p>Try: “What does the contract say about the completion period?”</p></div>)}
            {messages.map((m, i) => (
              <article key={i} className={"message " + m.role}>
                <div>{m.content}</div>
                {m.sources?.length ? <div className="sources"><b>Sources</b>{m.sources.map((s, n) => <span key={n}>[Source {n + 1}] {s.title || s.document_id}{s.page_number ? " · p." + s.page_number : ""}</span>)}</div> : null}
              </article>
            ))}
            {loading && <article className="message assistant"><div className="typing">Searching project knowledge and generating an answer…</div></article>}
            <div ref={messagesEndRef} />
          </div>
          <div className="composer">
            <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder={projectId ? "Ask a construction question..." : "Select or create a project first"} disabled={!projectId || loading} />
            <button onClick={send} disabled={!projectId || !input.trim() || loading} type="button">{loading ? "Thinking..." : "Ask AI"}</button>
          </div>
          {error && <div className="error">{error}</div>}
        </section>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
