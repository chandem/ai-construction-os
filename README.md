# AI Construction OS

> **AI-first construction management platform** — one intelligent system for projects, documents, costs, procurement, equipment, field operations, quality, safety, and project intelligence.

AI Construction OS treats **project data and documents as the source of truth**. AI is not a generic chatbot: it extracts, retrieves, and answers from real construction records so teams can make faster, evidence-based decisions.

**Live app:** [ai-costruction-os.vercel.app](https://ai-costruction-os.vercel.app)  
**Repository:** [github.com/chandem/ai-construction-os](https://github.com/chandem/ai-construction-os)  
**Roadmap:** [ROADMAP.md](ROADMAP.md)

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

### Document intelligence
- Upload construction files (PDF, DOCX, Excel, CSV, TXT)
- Storage in Supabase
- Text extraction, chunking, and embeddings
- AI classification and structured extraction
- Design-asset promotion for drawings/specifications
- Optional visual analysis on PDF drawing pages

### Construction AI Assistant
- Project-scoped chat
- Retrieval-Augmented Generation (RAG) over project knowledge
- Source citations
- Conversation history UI with auto-titling

### Design & engineering (Phase 3)
- Design assets from drawings/specifications
- AI design review findings
- Visual drawing analysis
- **Engineering elements** normalized from extraction + vision into structured project rows

### API surface (selected)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Service health |
| `GET` | `/api/v1/projects` | List projects |
| `POST` | `/api/v1/projects` | Create project |
| `GET` | `/api/v1/projects/{id}/documents` | List documents |
| `POST` | `/api/v1/projects/{id}/documents` | Upload & process document |
| `POST` | `/api/v1/projects/{id}/ai/chat` | RAG chat |
| `GET` | `/api/v1/projects/{id}/design/assets` | Design assets |
| `GET` | `/api/v1/design/assets/{id}/reviews` | Design asset reviews |
| `GET` | `/api/v1/projects/{id}/engineering/elements` | Project engineering elements |
| `GET` | `/api/v1/design/assets/{id}/elements` | Elements for one design asset |
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
         Auth · Storage · Projects · Documents · Elements · AI
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
- Apply `supabase/engineering_elements.sql` for Step 13
- OpenAI API key (for embeddings + chat + extraction)

### 1. Frontend

```bash
cp .env.example .env
npm install
npm run dev
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

---

## Roadmap status

Follow [ROADMAP.md](ROADMAP.md). Current work is **Phase 3 / Step 13**.

### Phase 1 — Foundation
- [x] GitHub repository
- [x] Supabase project & core schema
- [x] Vector / embedding support
- [x] RLS foundation
- [x] FastAPI backend structure
- [x] Authentication integration

### Phase 2 — Documents & AI
- [x] Document upload & storage
- [x] Text extraction, chunking, embeddings
- [x] AI classification / structured extraction
- [x] RAG assistant with sources
- [x] Conversation history UI

### Phase 3 — Design & Engineering
- [x] Design asset + review pipeline
- [x] Visual drawing analysis (early)
- [x] Engineering element model + APIs
- [ ] Quantity extraction
- [ ] BOQ linkage
- [ ] Design Center UI

### Next (locked)
Engineering elements → Quantity extraction → BOQ linkage → Estimate linkage → Design-to-cost → Background jobs → Design Center UI → Tender/Commercial

---

## Security

- Supabase Auth and Row Level Security
- Organization / project membership checks on API routes
- Publishable keys only in the frontend; privileged work stays server-side
- Engineering elements are proposed observations, not design approval

---

## Author

**Chane Eshetu**  
Civil & Software Engineer  

GitHub: [@chandem](https://github.com/chandem)
