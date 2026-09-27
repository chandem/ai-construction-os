# AI Construction OS

> **AI-first construction management platform** — one intelligent system for projects, documents, costs, procurement, equipment, field operations, quality, safety, and project intelligence.

AI Construction OS treats **project data and documents as the source of truth**. AI is not a generic chatbot: it extracts, retrieves, and answers from real construction records so teams can make faster, evidence-based decisions.

**Live app:** [ai-costruction-os.vercel.app](https://ai-costruction-os.vercel.app)  
**Repository:** [github.com/chandem/ai-construction-os](https://github.com/chandem/ai-construction-os)

---

## Vision

```
Construction Data + Documents → AI Intelligence → Decisions + Automation
```

Reduce fragmented spreadsheets, disconnected tools, manual document review, and delayed project reporting.

### Core principles

- **One construction database** — shared data across project modules
- **AI as the intelligence layer** — grounded in project evidence
- **Documents as evidence** — answers cite source material
- **Human control** — AI recommends; authorized users decide
- **Construction-first design** — real engineering and PM workflows
- **API-first architecture** — modules evolve independently
- **Multi-tenant SaaS** — organizations, projects, and RLS-ready access

---

## What works today (MVP)

### Authentication & workspace
- Email/password sign-up and login (Supabase Auth)
- Automatic personal organization bootstrap on first project
- Create and select projects (name + optional code)
- Project dashboard with live counts and recent activity

### Document intelligence
- Upload construction files (PDF, DOCX, Excel, CSV, TXT)
- Storage in Supabase
- Text extraction, chunking, and embeddings
- AI classification and structured extraction
- Design-asset promotion for drawings/specifications
- Optional visual analysis on PDF drawing pages
- Document status and AI Document Center UI
- Clickable documents open AI extraction viewer

### Construction AI Assistant
- Project-scoped chat
- Retrieval-Augmented Generation (RAG) over project knowledge
- Source citations (document title, page, similarity)
- Conversation history UI with auto-titling
- Conversation and usage logging on the backend

### Design intelligence (early)
- Design assets promoted from drawings/specifications
- Clickable assets with AI review findings and metadata
- Linked document extraction from design assets

### API surface (selected)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Service health |
| `GET` | `/api/v1/projects` | List projects |
| `POST` | `/api/v1/projects` | Create project |
| `GET` | `/api/v1/projects/{id}/documents` | List documents |
| `POST` | `/api/v1/projects/{id}/documents` | Upload & process document |
| `POST` | `/api/v1/projects/{id}/ai/chat` | RAG chat |
| `GET` | `/api/v1/projects/{id}/ai/conversations` | Conversation list |
| `GET` | `/api/v1/ai/conversations/{id}/messages` | Conversation messages |
| `GET` | `/api/v1/projects/{id}/design/assets` | Design assets |
| `GET` | `/api/v1/design/assets/{id}/reviews` | Design asset reviews |
| `GET` | `/api/v1/documents/{id}/status` | Processing status |
| `GET` | `/api/v1/documents/{id}/extraction` | Latest AI extraction |

---

## Architecture

```
                         AI Construction OS
                                |
              +-----------------+-----------------+
              |                 |                 |
          Web App           Mobile/PWA        API Clients
          (React/Vite)                          |
              |                 |                 |
              +-----------------+-----------------+
                                |
                         FastAPI Backend
                                |
                     AI Orchestration Layer
                                |
        +-----------+-----------+-----------+-----------+
        |           |           |           |           |
   Document AI   RAG/KB    Construction AI  Design AI  Vision
        |           |           |           |           |
        +-----------+-----------+-----------+-----------+
                                |
                    Supabase (PostgreSQL + pgvector)
                                |
              Auth · Storage · Projects · Documents · AI
```

---

## Technology stack

| Layer | Stack |
|-------|--------|
| **Frontend** | React 19, TypeScript, Vite, Supabase JS |
| **Backend** | Python, FastAPI, Pydantic, OpenAI |
| **Documents** | pypdf, PyMuPDF, python-docx, openpyxl |
| **Data platform** | Supabase (PostgreSQL, pgvector, Auth, Storage) |
| **Deploy** | GitHub, Vercel (frontend), Render (API intended) |

---

## Local development

### Prerequisites

- Node.js 18+
- Python 3.11+
- A Supabase project with the app schema, storage bucket `construction-documents`, and vector match RPC
- OpenAI API key (for embeddings + chat + extraction)

### 1. Frontend

```bash
cp .env.example .env
# Set:
#   VITE_SUPABASE_URL=
#   VITE_SUPABASE_PUBLISHABLE_KEY=
#   VITE_API_BASE_URL=http://localhost:8000

npm install
npm run dev
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Set:
#   SUPABASE_URL=
#   SUPABASE_PUBLISHABLE_KEY=
#   OPENAI_API_KEY=
#   EMBEDDING_MODEL=text-embedding-3-small
#   CORS_ORIGINS=http://localhost:5173

uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Typical user flow

1. Create an account and sign in  
2. Create a project  
3. Upload a contract, BOQ, specification, or report  
4. Review the project dashboard (documents, design assets, AI chats)  
5. Ask the Construction AI Assistant project-specific questions  
6. Open documents for AI extraction and design assets for review findings  

---

## Planned platform (beyond MVP)

| Domain | Capabilities |
|--------|----------------|
| **Project management** | Contracts, WBS, milestones, dashboards, members/roles |
| **Engineering** | Drawings, BOQ, RFIs, revisions |
| **Cost & commercial** | Estimates, budgets, invoices, variations, cash flow |
| **Procurement** | Suppliers, POs, deliveries, price intelligence |
| **Equipment** | Utilization, fuel, maintenance, downtime |
| **Field operations** | Daily reports, progress, photos, offline |
| **Quality & safety** | Inspections, NCRs, incidents, compliance |
| **Predictive AI** | Delay, cost, equipment, and quality risk signals |

---

## Roadmap status

### Phase 1 — Foundation
- [x] GitHub repository
- [x] Supabase project & core schema
- [x] Vector / embedding support
- [x] RLS foundation
- [x] FastAPI backend structure
- [x] Authentication integration

### Phase 2 — Project workspace
- [x] Organization bootstrap
- [x] Project creation & listing
- [x] Rich project dashboard
- [ ] Project members and roles UI

### Phase 3 — Document intelligence
- [x] Document upload & storage
- [x] Text extraction & processing jobs
- [x] AI classification / structured extraction
- [x] Design asset + review pipeline (early)
- [ ] Full OCR for scanned documents
- [ ] Richer processing status UX

### Phase 4 — AI knowledge base
- [x] Chunking pipeline
- [x] Embedding generation
- [x] Vector search (RAG)
- [x] Source / evidence references
- [ ] Tuning retrieval quality at scale

### Phase 5 — Construction AI Assistant
- [x] Project-aware chat
- [x] Document-grounded answers
- [x] Backend conversation history
- [x] Conversation history UI
- [ ] Direct project-data queries (beyond documents)

### Phase 6 — Construction intelligence
- [ ] Cost, schedule, procurement, equipment intelligence
- [ ] Quality & safety intelligence
- [ ] Predictive analytics

**Evolution path:**  
Project Management → Construction Data Platform → AI Construction Intelligence → AI Construction Operating System

---

## Security

- Supabase Auth and Row Level Security
- Organization / project membership checks on API routes
- Publishable keys only in the frontend; privileged work stays server-side
- Document access scoped to project members
- AI usage and sources logged for auditability

---

## Development status

**Stage:** Early MVP — core loop is live

Users can **sign in → create a project → upload documents → ask grounded AI questions**, with a project dashboard, conversation history, design assets, and AI extraction/review panels.

Next priorities: project members/roles UI, stronger OCR for scanned drawings, retrieval quality tuning, and domain intelligence modules (cost, schedule, quality).

---

## Author

**Chane Eshetu**  
Civil & Software Engineer  

GitHub: [@chandem](https://github.com/chandem)

---

Built with a construction-engineering perspective and an AI-first approach.
