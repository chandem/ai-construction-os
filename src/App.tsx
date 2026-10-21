import React from "react";
import { supabase } from "./supabaseClient";
import { apiGet, apiPost, apiPatch, apiUpload, apiDownload, apiDelete } from "./api";
import { AuthScreen } from "./AuthScreen";
import { MenuButton } from "./MenuButton";
import { DocumentList } from "./DocumentList";
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

const GROUPS: { title: string; items: { id: WorkspaceView; label: string }[] }[] = [
  { title: "Home", items: [{ id: "os-home", label: "OS Home" }, { id: "assistant", label: "AI Assistant" }] },
  { title: "Design", items: [{ id: "design-center", label: "Design" }] },
  { title: "Commercial", items: [{ id: "commercial", label: "Commercial" }, { id: "planning", label: "Planning" }, { id: "procurement", label: "Procurement" }, { id: "inventory", label: "Inventory" }, { id: "cost-control", label: "Cost Control" }] },
  { title: "Delivery", items: [{ id: "field", label: "Field" }, { id: "quality", label: "Quality" }] },
  { title: "Intelligence", items: [{ id: "prediction", label: "Prediction" }, { id: "brain", label: "Brain" }, { id: "gis", label: "GIS" }] },
  { title: "System", items: [{ id: "integrations", label: "Integrations" }, { id: "ops", label: "Ops" }] },
];
const AI_QUICK_ACTIONS = [
  { icon: "⌂", title: "Design & Engineering", prompt: "Review the engineering and design information available for this project. Identify applicable requirements, missing inputs, assumptions, and items that need qualified engineer verification." },
  { icon: "▦", title: "Quantity Surveying", prompt: "Act as a construction quantity surveyor. Review available project BOQs and documents, summarize measurable items, explain any quantity calculations with formulas and units, and flag missing dimensions or assumptions. Cite project evidence where available." },
  { icon: "↗", title: "Cost Estimation", prompt: "Analyze the available project BOQ, rates, budget, and cost documents. Summarize known costs, identify missing rate or quantity inputs, and flag possible cost risks. Separate documented values from assumptions." },
  { icon: "◷", title: "Project Planning", prompt: "Review the available project schedule, progress records, and reports. Identify milestones, possible delays, dependencies, and practical corrective actions. Clearly state which schedule data is missing." },
  { icon: "⚒", title: "Site Supervision", prompt: "Help me supervise this construction project. Review available site reports and progress records, summarize current issues, identify missing evidence, and propose practical follow-up actions." },
  { icon: "✓", title: "Quality & Safety", prompt: "Review available inspection, quality, and safety records. Identify documented nonconformities and potential risks, suggest corrective actions, and flag matters requiring competent professional review." },
  { icon: "▤", title: "Document Analysis", prompt: "Analyze the uploaded documents relevant to this project. Summarize key requirements, quantities, dates, obligations, and unresolved questions. Cite the source documents and pages when available; do not invent information." },
] as const;

const TABS: { id: WorkspaceView | "more"; label: string; icon: string }[] = [
  { id: "os-home", label: "Home", icon: "⌂" },
  { id: "design-center", label: "Design", icon: "◇" },
  { id: "field", label: "Field", icon: "▦" },
  { id: "assistant", label: "AI", icon: "✦" },
  { id: "more", label: "More", icon: "⋯" },
];
export function App() {
  const [session, setSession] = React.useState<any>(null);
  const [token, setToken] = React.useState("");
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [projectId, setProjectId] = React.useState("");
  const [projectsLoading, setProjectsLoading] = React.useState(false);
  const [showCreateProject, setShowCreateProject] = React.useState(false);
  const [editingProject, setEditingProject] = React.useState(false);
  const [editProjectName, setEditProjectName] = React.useState("");
  const [editProjectCode, setEditProjectCode] = React.useState("");
  const [updatingProject, setUpdatingProject] = React.useState(false);
  const [deletingProject, setDeletingProject] = React.useState(false);
  const [newProjectName, setNewProjectName] = React.useState("");
  const [newProjectCode, setNewProjectCode] = React.useState("");
  const [creatingProject, setCreatingProject] = React.useState(false);
  const [documents, setDocuments] = React.useState<Document[]>([]);
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [conversationId, setConversationId] = React.useState("");
  const [conversations, setConversations] = React.useState<Conversation[]>([]);
  const [input, setInput] = React.useState("");
  const [uploading, setUploading] = React.useState(false);
  const [reprocessingDocuments, setReprocessingDocuments] = React.useState<Record<string, boolean>>({});
  const [deletingDocuments, setDeletingDocuments] = React.useState<Record<string, boolean>>({});
  const [documentJobs, setDocumentJobs] = React.useState<Record<string, any>>({});
  const [resultsDocument, setResultsDocument] = React.useState<Document | null>(null);
  const [documentResults, setDocumentResults] = React.useState<any>(null);
  const [resultsLoading, setResultsLoading] = React.useState(false);
  const [resultsError, setResultsError] = React.useState("");
  const [aiBusy, setAiBusy] = React.useState(false);
  const [copiedMessage, setCopiedMessage] = React.useState<number | null>(null);
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

  async function loadProjectDocuments() {
    if (!token || !projectId) {
      setDocuments([]);
      setDocumentJobs({});
      return;
    }
    try {
      const r = await apiGet("/api/v1/projects/" + projectId + "/documents", token);
      const docs = r.data || [];
      setDocuments(docs);
      const statuses = await Promise.all(
        docs.map(async (d: Document) => {
          try {
            return [d.id, await apiGet("/api/v1/documents/" + d.id + "/status", token)] as const;
          } catch {
            return [d.id, null] as const;
          }
        })
      );
      setDocumentJobs(Object.fromEntries(statuses.filter(([, status]) => status)));
    } catch {
      setDocuments([]);
      setDocumentJobs({});
    }
  }

  React.useEffect(() => {
    if (!token || !projectId) {
      setDocuments([]);
      setDocumentJobs({});
      setConversations([]);
      return;
    }
    loadProjectDocuments();
    apiGet("/api/v1/projects/" + projectId + "/conversations", token)
      .then((r) => setConversations(r.data || []))
      .catch(() => setConversations([]));
  }, [token, projectId]);

  function openView(id: WorkspaceView) {
    setView(id);
    setSidebarOpen(false);
  }

  async function signOut() {
    setSidebarOpen(false);
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

  function beginEditProject() {
    const project = projects.find((item) => item.id === projectId);
    if (!project) return;
    setEditProjectName(project.name || "");
    setEditProjectCode(project.code || "");
    setEditingProject(true);
    setError("");
    setNotice("");
  }

  async function updateProject(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !projectId || !editProjectName.trim() || updatingProject) return;
    setUpdatingProject(true);
    setError("");
    setNotice("");
    try {
      const response = await apiPatch("/api/v1/projects/" + projectId, token, {
        name: editProjectName.trim(),
        code: editProjectCode.trim() || null,
      });
      const updated = response.data || response;
      setProjects((current) => current.map((item) => item.id === projectId ? { ...item, ...updated } : item));
      setEditingProject(false);
      setNotice("Project details updated.");
    } catch (err: any) {
      setError(err.message || "Could not update project.");
    } finally {
      setUpdatingProject(false);
    }
  }

  async function deleteProject() {
    const project = projects.find((item) => item.id === projectId);
    if (!token || !project || deletingProject) return;
    const confirmed = window.confirm(
      'Delete project "' + project.name + '"? This cannot be undone. Projects with uploaded documents or linked records cannot be deleted until those records are removed.'
    );
    if (!confirmed) return;
    setDeletingProject(true);
    setError("");
    setNotice("");
    try {
      await apiDelete("/api/v1/projects/" + projectId, token);
      setProjects((current) => current.filter((item) => item.id !== projectId));
      setProjectId("");
      setDocuments([]);
      setDocumentJobs({});
      setConversations([]);
      setConversationId("");
      setMessages([]);
      setResultsDocument(null);
      setDocumentResults(null);
      setEditingProject(false);
      setView("os-home");
      setNotice('Project "' + project.name + '" deleted.');
    } catch (err: any) {
      setError(err.message || "Could not delete project.");
    } finally {
      setDeletingProject(false);
    }
  }

  async function uploadDocument(file: File) {
    if (!projectId || !token) return;
    setUploading(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      await apiUpload("/api/v1/projects/" + projectId + "/documents", token, fd);
      await loadProjectDocuments();
      setNotice("Document uploaded and queued for processing.");
    } catch (err: any) {
      setError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function reprocessDocument(documentId: string, documentName: string) {
    if (!token || reprocessingDocuments[documentId]) return;
    setReprocessingDocuments((current) => ({ ...current, [documentId]: true }));
    setError("");
    setNotice("");
    try {
      await apiPost("/api/v1/documents/" + documentId + "/reprocess", token);
      await loadProjectDocuments();
      setNotice("Reprocessing started for " + documentName + ".");
      for (let attempt = 0; attempt < 80; attempt++) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        let job: any;
        try {
          job = await apiGet("/api/v1/documents/" + documentId + "/status", token);
        } catch (statusError: any) {
          if (attempt < 79) continue;
          throw statusError;
        }
        setDocumentJobs((current) => ({ ...current, [documentId]: job }));
        if (job.status === "completed" || job.status === "failed") {
          await loadProjectDocuments();
          if (job.status === "completed" && job.error_message)
            setNotice(documentName + " is processed, but AI enrichment is partial. " + job.error_message);
          else if (job.status === "completed") setNotice(documentName + " finished processing.");
          else setError(documentName + " processing failed: " + (job.error_message || "Unknown processing error"));
          break;
        }
      }
    } catch (err: any) {
      setError(err.message || "Could not reprocess document.");
    } finally {
      setReprocessingDocuments((current) => {
        const next = { ...current };
        delete next[documentId];
        return next;
      });
    }
  }

  async function deleteDocument(documentId: string, documentName: string) {
    if (!token || deletingDocuments[documentId] || reprocessingDocuments[documentId]) return;
    const confirmed = window.confirm(
      'Delete "' + documentName + '" permanently? This removes the uploaded document and its stored AI processing data for this project.'
    );
    if (!confirmed) return;

    setDeletingDocuments((current) => ({ ...current, [documentId]: true }));
    setError("");
    setNotice("");
    try {
      await apiDelete("/api/v1/documents/" + documentId, token);
      setDocuments((current) => current.filter((document) => document.id !== documentId));
      setDocumentJobs((current) => {
        const next = { ...current };
        delete next[documentId];
        return next;
      });
      if (resultsDocument?.id === documentId) {
        setResultsDocument(null);
        setDocumentResults(null);
      }
      setNotice('Deleted "' + documentName + '".');
    } catch (err: any) {
      setError(err.message || "Could not delete document.");
    } finally {
      setDeletingDocuments((current) => {
        const next = { ...current };
        delete next[documentId];
        return next;
      });
    }
  }

  async function viewDocumentResults(document: Document) {
    if (!token) return;
    setResultsDocument(document);
    setDocumentResults(null);
    setResultsError("");
    setResultsLoading(true);
    try {
      const result = await apiGet("/api/v1/documents/" + document.id + "/results", token);
      setDocumentResults(result);
    } catch (err: any) {
      setResultsError(err.message || "Could not load document results.");
    } finally {
      setResultsLoading(false);
    }
  }

  async function downloadBoqExcel() {
    if (!token || !resultsDocument) return;
    try {
      await apiDownload(
        "/api/v1/documents/" + resultsDocument.id + "/boq.xlsx",
        token,
        resultsDocument.name.replace(/\.[^.]+$/, "") + "-boq-analysis.xlsx",
      );
    } catch (err: any) {
      setResultsError(err.message || "Could not export BOQ to Excel.");
    }
  }

  function downloadExtractedText() {
    const text = documentResults?.knowledge?.extracted_text;
    if (!text || !resultsDocument) return;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement("a");
    link.href = url;
    link.download = resultsDocument.name.replace(/\.[^.]+$/, "") + "-extracted.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function startNewChat() {
    setConversationId("");
    setMessages([]);
    openView("assistant");
  }

  async function openConversation(id: string) {
    setConversationId(id);
    openView("assistant");
    try {
      const r = await apiGet("/api/v1/conversations/" + id + "/messages", token);
      setMessages(r.data || []);
    } catch {
      setMessages([]);
    }
  }

  async function copyAiResponse(index: number, content: string) {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessage(index);
      window.setTimeout(() => setCopiedMessage((current) => (current === index ? null : current)), 1600);
    } catch {
      setError("Could not copy the AI response. Please copy it manually.");
    }
  }

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !projectId || aiBusy) return;
    const text = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setAiBusy(true);
    setError("");
    try {
      const r = await apiPost("/api/v1/projects/" + projectId + "/ai/agent", token, { message: text });
      if (r.conversation_id) setConversationId(r.conversation_id);
      setMessages((m) => [...m, { role: "assistant", content: r.answer || r.reply || r.message || "(no reply)" }]);
      if (r.conversation_id) {
        const list = await apiGet("/api/v1/projects/" + projectId + "/conversations", token);
        setConversations(list.data || []);
      }
    } catch (err: any) {
      const msg = err.message || "Chat failed.";
      setError(msg);
      if (/high demand|503|unavailable/i.test(msg))
        setMessages((m) => [...m, { role: "assistant", content: "The AI model is busy right now. Please try again in a moment." }]);
    } finally {
      setAiBusy(false);
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
          <MenuButton open={sidebarOpen} onClick={() => setSidebarOpen((v) => !v)} />
        </div>
      </header>
      <main className="workspace">
        {sidebarOpen && (
          <button type="button" className="sidebar-backdrop" aria-label="Close menu" onClick={() => setSidebarOpen(false)} />
        )}
        <aside className={sidebarOpen ? "sidebar-open" : ""}>
          <div className="sidebar-scroll">
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
                  {p.name}{p.code ? " - " + p.code : ""}
                </option>
              ))}
            </select>
            <div className="project-actions">
              <button className="project-action-edit" type="button" onClick={beginEditProject} disabled={!projectId || updatingProject || deletingProject}>Edit</button>
              <button className="project-action-delete" type="button" onClick={deleteProject} disabled={!projectId || updatingProject || deletingProject}>{deletingProject ? "Deleting..." : "Delete"}</button>
            </div>
            {editingProject && (
              <form className="create-project" onSubmit={updateProject}>
                <strong>Edit project</strong>
                <label>Project name</label>
                <input type="text" value={editProjectName} onChange={(e) => setEditProjectName(e.target.value)} maxLength={200} disabled={updatingProject} />
                <label>Project code (optional)</label>
                <input type="text" value={editProjectCode} onChange={(e) => setEditProjectCode(e.target.value)} maxLength={50} disabled={updatingProject} />
                <div className="project-edit-actions">
                  <button className="button primary compact" type="submit" disabled={updatingProject || !editProjectName.trim()}>{updatingProject ? "Saving..." : "Save changes"}</button>
                  <button className="project-action-cancel" type="button" onClick={() => setEditingProject(false)} disabled={updatingProject}>Cancel</button>
                </div>
              </form>
            )}
            <button className="side-action" type="button" onClick={() => setShowCreateProject((v) => !v)}>
              {showCreateProject ? "Hide new project" : "+ New project"}
            </button>
            {showCreateProject && (
              <form className="create-project" onSubmit={createProject}>
                <label>Project name</label>
                <input type="text" value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} placeholder="e.g. Office block Package A" disabled={creatingProject} />
                <label>Project code (optional)</label>
                <input type="text" value={newProjectCode} onChange={(e) => setNewProjectCode(e.target.value)} placeholder="e.g. ARR-P2" disabled={creatingProject} />
                <button className="button primary compact" disabled={creatingProject || !newProjectName.trim()}>
                  {creatingProject ? "Creating..." : "Create project"}
                </button>
              </form>
            )}
            {GROUPS.map((group) => (
              <div className="nav-group" key={group.title}>
                <p className="nav-group-label">{group.title}</p>
                {group.items.map((n) => (
                  <button
                    key={n.id}
                    type="button"
                    className={"side-action" + (view === n.id ? " active-nav" : "")}
                    onClick={() => openView(n.id)}
                    disabled={!projectId && n.id !== "assistant" && n.id !== "os-home"}
                  >
                    {n.label}
                  </button>
                ))}
              </div>
            ))}
            <div className="chat-history">
              <div className="chat-history-head">
                <span>Chat history</span>
                <button type="button" onClick={startNewChat} disabled={!projectId}>New</button>
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
              <span> - {documents.length} uploaded</span>
              <label className="file-upload">
                {uploading ? "Uploading..." : "Upload document"}
                <input
                  type="file"
                  id="project-document-upload"
                  disabled={!projectId || uploading || aiBusy}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) uploadDocument(f);
                    e.target.value = "";
                  }}
                />
              </label>
              <DocumentList
                documents={documents}
                documentJobs={documentJobs}
                reprocessingDocuments={reprocessingDocuments}
                deletingDocuments={deletingDocuments}
                token={token}
                onOpenError={(message) => setError(message)}
                onViewResults={viewDocumentResults}
                onReprocess={reprocessDocument}
                onDelete={deleteDocument}
              />
            </div>
          </div>
          <div className="sidebar-footer">
            <button type="button" className="sign-out" onClick={signOut}>Sign out</button>
          </div>
        </aside>
        <section className="main-panel">
          {error && <div className="error">{error}</div>}
          {notice && <div className="success">{notice}</div>}
          {view === "os-home" && (
            <OsHome
              projectId={projectId}
              token={token}
              documentCount={documents.length}
              onNavigate={(v) => openView(v as WorkspaceView)}
              onUploadRequest={() => window.document.getElementById("project-document-upload")?.click()}
            />
          )}
          {view === "assistant" && (
            <div className="panel">
              <div className="panel-head"><h2>AI Construction Engineer</h2><span className="status">Project-aware AI</span></div>
              <p className="ai-assistant-intro">Choose a construction task to prepare a focused prompt. Review or edit it before sending; answers depend on available project records and documents.</p>
              <div className="ai-quick-actions" aria-label="Construction AI quick actions">
                {AI_QUICK_ACTIONS.map((action) => (
                  <button
                    key={action.title}
                    type="button"
                    className="ai-quick-action"
                    onClick={() => {
                      setInput(action.prompt);
                      setError("");
                      setNotice("");
                    }}
                    disabled={!projectId || aiBusy}
                    aria-label={"Prepare prompt for " + action.title}
                  >
                    <span className="ai-quick-action-icon" aria-hidden="true">{action.icon}</span>
                    <span className="ai-quick-action-copy">
                      <b>{action.title}</b>
                      <small>Prepare prompt</small>
                    </span>
                    <span className="ai-quick-action-arrow" aria-hidden="true">↗</span>
                  </button>
                ))}
              </div>
              <div className="messages">
                {messages.length === 0 && (
                  <div className="empty empty-card">
                    <h3>Ask about this project</h3>
                    <p>Ask about uploaded drawings, specs, reports, or BOQs. You can also ask about project status, materials, costs, risks, or construction calculations.</p>
                  </div>
                )}
                {messages.map((m, i) =>
                  m.role === "assistant" ? (
                    <div key={i} className="assistant-message">
                      <div className="message assistant">{m.content}</div>
                      <button type="button" className="copy-response" onClick={() => copyAiResponse(i, m.content)} aria-label="Copy AI response">
                        {copiedMessage === i ? "Copied" : "Copy"}
                      </button>
                    </div>
                  ) : (
                    <div key={i} className="message user">{m.content}</div>
                  )
                )}
                {aiBusy && <div className="typing">AI is thinking...</div>}
              </div>
              <form className="composer" onSubmit={sendMessage}>
                <textarea value={input} onChange={(e) => setInput(e.target.value)} placeholder={projectId ? "Ask about this project..." : "Select a project first"} disabled={!projectId || aiBusy} />
                <button type="submit" disabled={!projectId || aiBusy || !input.trim()}>Send</button>
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
      <nav className="bottom-tabs" aria-label="Primary navigation">
        {TABS.map((t) => {
          const active = t.id === "more" ? sidebarOpen : view === t.id;
          return (
            <button
              key={t.id}
              type="button"
              className={`bottom-tab${active ? " active" : ""}`}
              onClick={() => {
                if (t.id === "more") setSidebarOpen(true);
                else openView(t.id);
              }}
              aria-current={t.id !== "more" && active ? "page" : undefined}
              aria-expanded={t.id === "more" ? sidebarOpen : undefined}
              aria-label={t.label === "AI" ? "AI Assistant" : t.id === "more" ? "More modules, open menu" : t.label}
            >
              <span className="bottom-tab-icon" aria-hidden="true">{t.icon}</span>
              <span className="bottom-tab-label">{t.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
