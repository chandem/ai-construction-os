# AI Construction OS

> **AI-first construction management platform** — one intelligent system for projects, documents, costs, commercial, planning, field, quality, GIS, prediction, and ops.

AI Construction OS treats **project data and documents as the source of truth**. AI extracts, retrieves, and answers from real construction records so teams can make faster, evidence-based decisions.

**Live app:** [ai-costruction-os.vercel.app](https://ai-costruction-os.vercel.app)  
**Repository:** [github.com/chandem/ai-construction-os](https://github.com/chandem/ai-construction-os)  
**Roadmap:** [ROADMAP.md](ROADMAP.md) · **Phase 14 notes:** [PHASE14.md](PHASE14.md)

---

## Status

| Area | State |
|------|--------|
| **Phases 1–13 backend** | On `main` (modules, SQL, tests, modular routes) |
| **Phase 14 Product UI** | Modular dashboard on `main` (12 workspace centers) |
| **Live Supabase SQL** | Apply schema files in your project (see below) |
| **Phase 15** | Vision — unified Construction OS product |

---

## Vision

```
Construction Data + Documents → AI Intelligence → Decisions + Automation
```

### Core principles

- **One construction database** — shared data across modules
- **AI as the intelligence layer** — grounded in project evidence
- **Documents as evidence** — answers cite source material
- **Human control** — AI recommends; authorized users decide
- **API-first** — modules evolve independently
- **Multi-tenant SaaS** — organizations, projects, RLS-ready access

---

## What works today

### Auth & workspace
- Email/password (Supabase Auth)
- Create and select projects

### Document intelligence
- Upload (PDF, DOCX, Excel, CSV, TXT)
- Background AI pipeline (`queued` → extract → embed → design assets / elements)
- Job status and reprocess

### Construction AI Assistant
- Project-scoped RAG chat with citations and conversation history

### Domain centers (Product UI)

| Center | Capabilities |
|--------|----------------|
| **Design** | Elements, QTO, BOQ, estimate, design-to-cost |
| **Commercial** | Tender packages, contracts |
| **Planning** | WBS + schedule |
| **Procurement** | Materials, equipment, workforce |
| **Field** | Site diary, progress |
| **Quality** | Inspections, NCRs, incidents |
| **GIS** | Locations, assets from elements |
| **Prediction** | Risks + forecasts |
| **Brain** | Cross-domain insights |
| **Integrations** | Connector catalog / connections |
| **Ops** | Queue, cost events, system health |

---

## Architecture

```
Web App (React/Vite)  →  FastAPI  →  Supabase (Postgres + pgvector + Auth + Storage)
                              ↓
              Modular routes: engineering · commercial · operations
                              field/quality · intelligence · ops
```

### Backend layout (selected)

```
backend/app/
  engineering_routes.py    # mounts phase routers
  routes_helpers.py
  routes_commercial.py     # Phase 4
  routes_operations.py     # Phases 5–6
  routes_field_quality.py  # Phases 7–8
  routes_intelligence.py   # Phases 9–12
  routes_ops.py            # Phase 13
  tender.py … hardening.py # domain logic
supabase/
  *.sql                    # one schema file per phase area
```

### Frontend layout

```
src/
  App.tsx · AuthScreen.tsx · api.ts · types.ts
  centers/                 # Design → Ops panels
```

---

## Technology stack

| Layer | Stack |
|-------|--------|
| **Frontend** | React 19, TypeScript, Vite, Supabase JS |
| **Backend** | Python, FastAPI, Pydantic, OpenAI |
| **Documents** | pypdf, PyMuPDF, python-docx, openpyxl |
| **Data** | Supabase (PostgreSQL, pgvector, Auth, Storage) |
| **Deploy** | GitHub, Vercel (frontend), Render (API) |

---

## Local development

### Prerequisites

- Node.js 18+, Python 3.11+
- Supabase project + OpenAI API key
- Storage bucket `construction-documents` and vector match RPC

### Apply SQL (in order) in Supabase SQL editor

```
engineering_elements.sql → boq_items.sql → estimate_items.sql
tender_packages.sql → contract_packages.sql → planning.sql
procurement.sql → field.sql → quality.sql → gis.sql
prediction.sql → integrations.sql → hardening.sql
```

### Frontend

```bash
cp .env.example .env
npm install
npm run dev
```

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

---

## Security

- Supabase Auth and Row Level Security
- Project membership checks on API routes
- Publishable keys only in the frontend
- Engineering / commercial figures are **proposed** for human review

---

## Author

**Chane Eshetu** — Civil & Software Engineer  
GitHub: [@chandem](https://github.com/chandem)
