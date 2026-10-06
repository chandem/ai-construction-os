# AI Construction OS

> **AI-powered construction management platform** — one connected operating system for the construction lifecycle.

AI Construction OS is a **general construction platform** for building, road, bridge, industrial, water, utility, infrastructure, and other civil engineering projects. It connects project data, documents, commercial records, planning, procurement, field operations, quality, cost, and AI into one system.

The platform is designed around a connected construction lifecycle:

```
Tender → Contract → Design → BOQ → Schedule → Procurement
→ Materials → Equipment → Site → Progress → Cost
→ Quality → Safety → Documents → Reporting → AI
```

AI Construction OS treats **project data and documents as the source of truth**. AI extracts, retrieves, analyzes, and answers from project records so teams can make faster, evidence-based decisions.

**Repository:** https://github.com/chandem/ai-construction-os  
**Deploy guide:** [DEPLOY.md](DEPLOY.md) · **Roadmap:** [ROADMAP.md](ROADMAP.md)

---

## Current status

| Area | Status |
|------|--------|
| **Core platform** | Active development |
| **AI Assistant** | Project-scoped RAG with citations |
| **Document Intelligence 2.0** | Integrated |
| **Backend API** | Live on Render |
| **Database** | Supabase PostgreSQL + pgvector |
| **Frontend** | Vite/React; deployment verification pending |

The latest backend release includes **AI Document Intelligence 2.0**, which evaluates document processing status, extracted text, page count, extraction confidence, chunk coverage, warnings, recommendations, and project-level processing readiness.

---

## Construction centers

| Center | Purpose |
|--------|---------|
| **Design & Engineering** | Drawings, engineering elements, quantities, BOQ, estimates |
| **Commercial** | Tenders, contracts, commercial records |
| **Planning** | WBS, activities, schedules and project controls |
| **Procurement** | Purchasing, suppliers, materials and equipment |
| **Inventory** | Material receipts, issues, stock and cost |
| **Equipment** | Machinery and equipment management |
| **Field** | Site diary, progress and field records |
| **Cost Control** | Cost events, budgets and project cost intelligence |
| **Quality** | Inspections, NCRs and quality records |
| **Safety** | Safety records, incidents and compliance |
| **Documents** | Project document storage and AI processing |
| **GIS & Infrastructure** | Locations, assets and infrastructure-specific workflows |
| **Prediction** | Risks, forecasts and early warnings |
| **AI Assistant** | Project-aware construction intelligence |
| **Brain / Analytics** | Cross-domain insights and reporting |
| **Integrations** | External systems and synchronization |
| **Operations** | Queues, jobs, health and operational monitoring |

The platform is **project-type aware** rather than road-only. Specialized infrastructure capabilities such as GIS can coexist with building, industrial, structural, MEP, and other construction workflows.

---

## AI capabilities

### AI Document Intelligence
- Document processing readiness assessment
- Extracted text and page analysis
- Chunk coverage and processing status
- Confidence, warnings and recommendations
- Project-level document intelligence summary

### AI Construction Assistant
- Project-scoped conversational AI
- Retrieval-Augmented Generation (RAG)
- Evidence/source citations
- Project document and knowledge retrieval
- Cross-domain construction questions

### AI Engineering
- Drawing and specification intelligence
- Engineering element extraction
- Quantity takeoff support
- BOQ and estimate intelligence
- Design-to-cost workflows

### AI Commercial & Project Controls
- Tender and contract intelligence
- Cost and commercial analysis
- Schedule and progress intelligence
- Risk and forecast support

> AI-generated engineering, quantity, cost, and commercial outputs are **proposed results for professional review**, not automatic approval.

---

## Architecture

```
                     AI CONSTRUCTION OS
                              │
       ┌──────────────────────┼──────────────────────┐
       │                      │                      │
   Web App               FastAPI API             AI Engine
  React / Vite              Backend          RAG · Analytics
       │                      │               Prediction
       └──────────────────────┼──────────────────────┘
                              │
                       Supabase / Postgres
                         pgvector · Auth
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   Project Data          Documents              AI Data
   BOQ · Cost ·          Chunks · Jobs        Conversations
   Schedule · Field      Sources              Insights
```

The architecture is built around connected construction entities so information can flow across the lifecycle:

```
Contract
   ↓
BOQ
   ↓
Schedule
   ↓
Procurement
   ↓
Materials / Equipment
   ↓
Progress
   ↓
Cost
   ↓
Quality / Risk
   ↓
AI Insights
```

---

## Technology stack

### Frontend
- React
- Vite
- TypeScript
- CSS

### Backend
- Python
- FastAPI
- REST API

### Data & authentication
- Supabase
- PostgreSQL
- pgvector
- Supabase Auth
- Row Level Security

### AI
- Gemini-based AI services
- Project-scoped retrieval
- Vector search / RAG
- Document intelligence
- AI engineering and construction workflows

---

## Local development

### Frontend

```bash
cp .env.example .env
npm install
npm run dev
```

Configure:

```
VITE_SUPABASE_URL=
VITE_SUPABASE_PUBLISHABLE_KEY=
VITE_API_BASE_URL=
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Configure the backend environment according to [DEPLOY.md](DEPLOY.md).

---

## Deployment

The production architecture is:

```
Vercel
  ↓
React / Vite frontend

Render
  ↓
FastAPI backend

Supabase
  ↓
PostgreSQL + pgvector + Auth + Storage
```

See [DEPLOY.md](DEPLOY.md) for environment variables, database setup, CORS, deployment, and smoke tests.

---

## Security

- Supabase authentication
- Row Level Security (RLS)
- Project and organization membership checks
- Server-side authorization for protected operations
- Frontend uses publishable Supabase credentials only
- Sensitive service credentials remain server-side
- AI engineering, cost, quantity, and commercial outputs require human review

---

## Project vision

AI Construction OS aims to become a **construction operating system**, not a collection of disconnected tools.

The long-term goal is to connect:

**Tender → Contract → Design → BOQ → Planning → Procurement → Site → Progress → Cost → Quality → Safety → Documents → AI**

so that construction teams can manage projects from one connected data platform and use AI to understand what is happening, what is at risk, and what should happen next.

---

## Author

**Chane Eshetu — Civil & Software Engineer**

GitHub: https://github.com/chandem
