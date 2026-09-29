import React from "react";
import { supabase } from "./supabaseClient";
import { API, apiGet, apiPost, apiUpload } from "./api";
import { AuthScreen } from "./AuthScreen";
import type { Project, Document, Message, Conversation, DesignAsset, WorkspaceView } from "./types";
import { OsHome } from "./centers/OsHome";
import { DesignCenter } from "./centers/DesignCenter";
import { CommercialCenter } from "./centers/CommercialCenter";
import { PlanningCenter } from "./centers/PlanningCenter";
import { ProcurementCenter } from "./centers/ProcurementCenter";
import { FieldCenter } from "./centers/FieldCenter";
import { QualityCenter } from "./centers/QualityCenter";
import { GisCenter } from "./centers/GisCenter";
import { PredictionCenter } from "./centers/PredictionCenter";
import { BrainCenter } from "./centers/BrainCenter";
import { IntegrationsCenter } from "./centers/IntegrationsCenter";
import { OpsCenter } from "./centers/OpsCenter";

const NAV: { id: WorkspaceView; label: string }[] = [
  { id: "os-home", label: "OS Home" },
  { id: "assistant", label: "Assistant" },
  { id: "design-center", label: "Design" },
  { id: "commercial", label: "Commercial" },
  { id: "planning", label: "Planning" },
  { id: "procurement", label: "Procurement" },
  { id: "field", label: "Field" },
  { id: "quality", label: "Quality" },
  { id: "gis", label: "GIS" },
  { id: "prediction", label: "Prediction" },
  { id: "brain", label: "Brain" },
  { id: "integrations", label: "Integrations" },
  { id: "ops", label: "Ops" },
];

export function App() {
  const [session, setSession] = React.useState<any>(null);
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [projectId, setProjectId] = React.useState("");
  const [documents, setDocuments] = React.useState<Document[]>([]);
  const [designAssets, setDesignAssets] = React.useState<DesignAsset[]>([]);
  const [conversations, setConversations] = React.useState<Conversation[]>([]);
  const [conversationId, setConversationId] = React.useState("");
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [view, setView] = React.useState<WorkspaceView>("os-home");
  const [loading, setLoading] = React.useState(false);
  const [projectsLoading, setProjectsLoading] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [creatingProject, setCreatingProject] = React.useState(false);
  const [showCreateProject, setShowCreateProject] = React.useState(false);
  const [newProjectName, setNewProjectName] = React.useState("");
  const [newProjectCode, setNewProjectCode] = React.useState("");
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const fileRef = React.useRef<HTMLInputElement>(null);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const token = session?.access_token || "";

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
    else { setDocuments([]); setConversations([]); setDesignAssets([]); setConversationId(""); setMessages([]); }
  }, [session, projectId]);

  React.useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  async function loadProjects() {
    if (!session) return;
    if (!API) { setError("API base URL is not configured (VITE_API_BASE_URL)."); return; }
    setProjectsLoading(true); setError("");
    try {
      const j = await apiGet("/api/v1/projects", session.access_token);
      const data = j.data || [];
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
      const j = await apiPost("/api/v1/projects", session.access_token, { name, code: newProjectCode.trim() || null });
      const created = j.data;
      setProjects((c) => [created, ...c]); setProjectId(created.id);
      setNewProjectName(""); setNewProjectCode(""); setShowCreateProject(false);
      setMessages([]); setConversationId(""); setNotice(`Project "${created.name}" created.`);
      setView("os-home");
    } catch (err: any) { setError(err.message || "Could not create project."); }
    finally { setCreatingProject(false); }
  }

  async function loadDocuments() {
    if (!session || !projectId) return;
    try {
      const j = await apiGet("/api/v1/projects/" + projectId + "/documents", session.access_token);
      setDocuments(j.data || []);
    } catch (e: any) { setError(e.message || "Could not load documents."); }
  }

  async function loadDesignAssets() {
    if (!session || !projectId) return;
    try {
      const j = await apiGet("/api/v1/projects/" + projectId + "/design/assets", session.access_token);
      setDesignAssets(j.data || []);
    } catch { /* optional */ }
  }

  async function loadConversations() {
    if (!session || !projectId) return;
    try {
      const j = await apiGet("/api/v1/projects/" + projectId + "/ai/conversations", session.access_token);
      setConversations(j.data || []);
    } catch { /* optional */ }
  }

  async function openConversation(id: string) {
    if (!session || !id) return;
    setConversationId(id); setError(""); setLoading(true); setView("assistant");
    try {
      const j = await apiGet("/api/v1/ai/conversations/" + id + "/messages", session.access_token);
      const rows = (j.data || []) as { role: string; content: string }[];
      setMessages(rows.filter((m) => m.role === "user" || m.role === "assistant").map((m) => ({ role: m.role as "user" | "assistant", content: m.content })));
    } catch (e: any) { setError(e.message || "Could not load conversation."); }
    finally { setLoading(false); }
  }

  function startNewChat() { setConversationId(""); setMessages([]); setError(""); setNotice(""); setView("assistant"); }

  async function uploadDocument(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; e.target.value = "";
    if (!file || !session || !projectId || uploading) return;
    setUploading(true); setError(""); setNotice("");
    try {
      const form = new FormData(); form.append("file", file);
      const j = await apiUpload("/api/v1/projects/" + projectId + "/documents", session.access_token, form);
      setNotice(file.name + " uploaded. " + (j.chunks ?? 0) + " knowledge chunks created.");
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
      const j = await apiPost("/api/v1/projects/" + projectId + "/ai/chat", session.access_token, body);
      if (j.conversation_id) setConversationId(j.conversation_id);
      setMessages((m) => [...m, { role: "assistant", content: j.answer, sources: j.sources || [] }]);
      await loadConversations();
    } catch (e: any) { setError(e.message || "AI request failed."); }
    finally { setLoading(false); }
  }

  async function signOut() { await supabase.auth.signOut(); setMessages([]); setConversationId(""); }

  if (!session) return <AuthScreen />;

  const centerProps = { projectId, token };

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
          <select value={projectId} onChange={(e) => { setProjectId(e.target.value); setMessages([]); setConversationId(""); setError(""); setNotice(""); setView("os-home"); }}>
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
          <div className="nav-centers">
            {NAV.map((n) => (
              <button key={n.id} type="button" className={"side-action" + (view === n.id ? " active-nav" : "")} onClick={() => setView(n.id)} disabled={!projectId && n.id !== "assistant"}>
                {n.label}
              </button>
            ))}
          </div>
          <div className="chat-history">
            <div className="chat-history-head"><span>Chat history</span><button type="button" onClick={startNewChat} disabled={!projectId}>New</button></div>
            <div className="chat-history-list">
              {conversations.map((c) => (
                <button key={c.id} type="button" className={"chat-history-item" + (c.id === conversationId ? " active" : "")} onClick={() => openConversation(c.id)}>
                  <b>{c.title || "Construction AI chat"}</b>
                  <span>{c.created_at ? new Date(c.created_at).toLocaleString() : ""}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="hint"><b>Documents</b></div>
          <input ref={fileRef} type="file" hidden onChange={uploadDocument} />
          <button className="side-action" type="button" disabled={!projectId || uploading} onClick={() => fileRef.current?.click()}>{uploading ? "Uploading…" : "Upload document"}</button>
          <ul className="doc-list">
            {documents.slice(0, 8).map((d) => <li key={d.id}>{d.name}</li>)}
          </ul>
        </aside>
        <section className="main-panel">
          {error && <div className="error">{error}</div>}
          {notice && <div className="success">{notice}</div>}
          {!projectId && <div className="empty"><p>Select or create a project to open the Construction OS.</p></div>}
          {projectId && view === "os-home" && <OsHome {...centerProps} />}
          {projectId && view === "assistant" && (
            <>
              <div className="messages">
                {messages.length === 0 && !loading && (
                  <div className="empty"><div className="logo">AI</div><p>Ask about drawings, BOQ, schedule, risks, or site progress.</p></div>
                )}
                {messages.map((m, i) => (
                  <article key={i} className={"message " + m.role}>
                    <div>{m.content}</div>
                    {m.sources?.length ? <div className="sources"><b>Sources</b>{m.sources.map((s, j) => <span key={j}>{s.citation}</span>)}</div> : null}
                  </article>
                ))}
                {loading && <div className="message assistant typing">Thinking…</div>}
                <div ref={messagesEndRef} />
              </div>
              <div className="composer">
                <textarea value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask the construction assistant…" rows={2}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
                <button type="button" onClick={send} disabled={!projectId || loading || !input.trim()}>Send</button>
              </div>
            </>
          )}
          {projectId && view === "design-center" && <DesignCenter {...centerProps} />}
          {projectId && view === "commercial" && <CommercialCenter {...centerProps} />}
          {projectId && view === "planning" && <PlanningCenter {...centerProps} />}
          {projectId && view === "procurement" && <ProcurementCenter {...centerProps} />}
          {projectId && view === "field" && <FieldCenter {...centerProps} />}
          {projectId && view === "quality" && <QualityCenter {...centerProps} />}
          {projectId && view === "gis" && <GisCenter {...centerProps} />}
          {projectId && view === "prediction" && <PredictionCenter {...centerProps} />}
          {projectId && view === "brain" && <BrainCenter {...centerProps} />}
          {projectId && view === "integrations" && <IntegrationsCenter {...centerProps} />}
          {projectId && view === "ops" && <OpsCenter {...centerProps} />}
        </section>
      </main>
    </div>
  );
}
