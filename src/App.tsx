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
import { InventoryCenter } from "./centers/InventoryCenter";
import { CostControlCenter } from "./centers/CostControlCenter";
import { FieldCenter } from "./centers/FieldCenter";
import { QualityCenter } from "./centers/QualityCenter";
import { GisCenter } from "./centers/GisCenter";
import { PredictionCenter } from "./centers/PredictionCenter";
import { BrainCenter } from "./centers/BrainCenter";
import { IntegrationsCenter } from "./centers/IntegrationsCenter";
import { OpsCenter } from "./centers/OpsCenter";

const NAV: { id: WorkspaceView; label: string }[] = [
  { id: "os-home", label: "OS Home" },
  { id: "assistant", label: "AI Assistant" },
  { id: "design-center", label: "Design" },
  { id: "commercial", label: "Commercial" },
  { id: "planning", label: "Planning" },
  { id: "procurement", label: "Procurement" },
  { id: "inventory", label: "Inventory" },
  { id: "cost-control", label: "Cost Control" },
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
  const [token, setToken] = React.useState("");
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [projectId, setProjectId] = React.useState("");
  const [projectsLoading, setProjectsLoading] = React.useState(false);
  const [showCreateProject, setShowCreateProject] = React.useState(false);
  const [newProjectName, setNewProjectName] = React.useState("");
  const [newProjectCode, setNewProjectCode] = React.useState("");
  const [creatingProject, setCreatingProject] = React.useState(false);
  const [documents, setDocuments] = React.useState<Document[]>([]);
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [conversationId, setConversationId] = React.useState("");
  const [conversations, setConversations] = React.useState<Conversation[]>([]);
  const [input, setInput] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [view, setView] = React.useState<WorkspaceView>("os-home");
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [designAssets, setDesignAssets] = React.useState<DesignAsset[]>([]);

  React.useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setToken(data.session?.access_token || "");
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => {
      setSession(s);
      setToken(s?.access_token || "");
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  React.useEffect(() => {
    if (!token) return;
    setProjectsLoading(true);
    apiGet("/api/v1/projects", token)
      .then((r) => setProjects(r.data || []))
      .catch((e) => setError(e.message || "Could not load projects."))
      .finally(() => setProjectsLoading(false));
  }, [token]);

  React.useEffect(() => {
    if (!token || !projectId) {
      setDocuments([]);
      setConversations([]);
      return;
    }
    apiGet("/api/v1/projects/" + projectId + "/documents", token)
      .then((r) => setDocuments(r.data || []))
      .catch(() => setDocuments([]));
    apiGet("/api/v1/projects/" + projectId + "/conversations", token)
      .then((r) => setConversations(r.data || []))
      .catch(() => setConversations([]));
  }, [token, projectId]);

  async function signOut() {
    await supabase.auth.signOut();
    setSession(null);
    setToken("");
  }

  async function createProject(e: React.FormEvent) {
    e.preventDefault();
    if (!newProjectName.trim() || creatingProject) return;
    setCreatingProject(true);
    setError("");
    try {
      const r = await apiPost("/api/v1/projects", token, {
        name: newProjectName.trim(),
        code: newProjectCode.trim() || undefined,
      });
      const p = r.data || r;
      setProjects((prev) => [p, ...prev]);
      setProjectId(p.id);
      setNewProjectName("");
      setNewProjectCode("");
      setShowCreateProject(false);
      setView("os-home");
      setNotice("Project created.");
    } catch (err: any) {
      setError(err.message || "Could not create project.");
    } finally {
      setCreatingProject(false);
    }
  }

  async function uploadDocument(file: File) {
    if (!projectId || !token) return;
    setBusy(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      await apiUpload("/api/v1/projects/" + projectId + "/documents", token, fd);
      const r = await apiGet("/api/v1/projects/" + projectId + "/documents", token);
      setDocuments(r.data || []);
      setNotice("Document uploaded and queued for processing.");
    } catch (err: any) {
      setError(err.message || "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function startNewChat() {
    setConversationId("");
    setMessages([]);
    setView("assistant");
    setSidebarOpen(false);
  }

  async function openConversation(id: string) {
    setConversationId(id);
    setView("assistant");
    setSidebarOpen(false);
    try {
      const r = await apiGet("/api/v1/conversations/" + id + "/messages", token);
      setMessages(r.data || []);
    } catch {
      setMessages([]);
    }
  }

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !projectId || busy) return;
    const text = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    setError("");
    try {
      const r = await apiPost("/api/v1/projects/" + projectId + "/chat", token, {
        message: text,
        conversation_id: conversationId || undefined,
      });
      if (r.conversation_id) setConversationId(r.conversation_id);
      setMessages((m) => [...m, { role: "assistant", content: r.reply || r.message || "(no reply)" }]);
      if (r.conversation_id) {
        const list = await apiGet("/api/v1/projects/" + projectId + "/conversations", token);
        setConversations(list.data || []);
      }
    } catch (err: any) {
      const msg = err.message || "Chat failed.";
      setError(msg);
      if (/high demand|503|unavailable/i.test(msg)) {
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            content: "The AI model is busy right now. Please try again in a moment.",
          },
        ]);
      }
    } finally {
      setBusy(false);
    }
  }

  if (!session) return <AuthScreen />;

  const centerProps = { projectId, token };

  return (
    <div className="app">
      <header>
        <div>
          <strong>AI Construction OS</strong>
          <span>General construction project OS</span>
        </div>
        <div className="header-actions">
          <button
            className="menu-button"
            type="button"
            aria-label={sidebarOpen ? "Close menu" : "Open menu"}
            aria-expanded={sidebarOpen}
            onClick={() => setSidebarOpen((v) => !v)}
          >
            {sidebarOpen ? "✕" : "☰"}
          </button>
          <button type="button" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>
      <main className="workspace">
        {sidebarOpen && (
          <button
            type="button"
            className="sidebar-backdrop"
            aria-label="Close menu"
            onClick={() => setSidebarOpen(false)}
          />
        )}
        <aside className={sidebarOpen ? "sidebar-open" : ""}>
          <div className="sidebar-head">
            <h2>Menu</h2>
            <button
              type="button"
              className="sidebar-close"
              aria-label="Close menu"
              onClick={() => setSidebarOpen(false)}
            >
              Close
            </button>
          </div>
          <h2 className="sidebar-section">Project</h2>
          <label>Select project</label>
          <select
            value={projectId}
            onChange={(e) => {
              setProjectId(e.target.value);
              setMessages([]);
              setConversationId("");
              setError("");
              setNotice("");
              setView("os-home");
            }}
          >
            <option value="">{projectsLoading ? "Loading projects..." : "Select project"}</option>
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
                placeholder="e.g. Office block Package A or Road Package 2"
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
          <div className="nav-centers">
            {NAV.map((n) => (
              <button
                key={n.id}
                type="button"
                className={"side-action" + (view === n.id ? " active-nav" : "")}
                onClick={() => {
                  setView(n.id);
                  setSidebarOpen(false);
                }}
                disabled={!projectId && n.id !== "assistant"}
              >
                {n.label}
              </button>
            ))}
          </div>
          <div className="chat-history">
            <div className="chat-history-head">
              <span>Chat history</span>
              <button type="button" onClick={startNewChat} disabled={!projectId}>
                New
              </button>
            </div>
            <div className="chat-history-list">
              {conversations.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={"chat-history-item" + (c.id === conversationId ? " active" : "")}
                  onClick={() => openConversation(c.id)}
                >
                  <b>{c.title || "Project AI chat"}</b>
                  <span>{c.created_at ? new Date(c.created_at).toLocaleString() : ""}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="hint">
            <b>Documents</b>
            <span> · {documents.length} uploaded</span>
            <input
              type="file"
              style={{ marginTop: 10 }}
              disabled={!projectId || busy}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) uploadDocument(f);
                e.target.value = "";
              }}
            />
          </div>
        </aside>
        <section className="main-panel">
          {error && <div className="error">{error}</div>}
          {notice && <div className="success">{notice}</div>}
          {view === "os-home" && (
            <OsHome
              projectId={projectId}
              token={token}
              onNavigate={(v) => setView(v as WorkspaceView)}
            />
          )}
          {view === "assistant" && (
            <div className="panel">
              <div className="panel-head">
                <h2>AI Assistant</h2>
              </div>
              <div className="messages">
                {messages.length === 0 && (
                  <div className="empty empty-card">
                    <h3>Ask about this project</h3>
                    <p>
                      Upload drawings, specs, or reports for general construction work, then ask about
                      scope, quantities, schedule, or site status.
                    </p>
                  </div>
                )}
                {messages.map((m, i) => (
                  <div key={i} className={"message " + m.role}>
                    {m.content}
                  </div>
                ))}
                {busy && <div className="typing">Thinking…</div>}
              </div>
              <form className="composer" onSubmit={sendMessage}>
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={projectId ? "Ask about this project…" : "Select a project first"}
                  disabled={!projectId || busy}
                />
                <button type="submit" disabled={!projectId || busy || !input.trim()}>
                  Send
                </button>
              </form>
            </div>
          )}
          {projectId && view === "design-center" && <DesignCenter {...centerProps} />}
          {projectId && view === "commercial" && <CommercialCenter {...centerProps} />}
          {projectId && view === "planning" && <PlanningCenter {...centerProps} />}
          {projectId && view === "procurement" && <ProcurementCenter {...centerProps} />}
          {projectId && view === "inventory" && <InventoryCenter {...centerProps} />}
          {projectId && view === "cost-control" && <CostControlCenter {...centerProps} />}
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
