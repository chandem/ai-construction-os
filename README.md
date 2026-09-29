# AI Construction OS

> **AI-first construction management platform** — one intelligent system for projects, documents, costs, commercial, planning, field, quality, GIS, prediction, and ops.

AI Construction OS treats **project data and documents as the source of truth**. AI extracts, retrieves, and answers from real construction records so teams can make faster, evidence-based decisions.

**Live app:** [ai-costruction-os.vercel.app](https://ai-costruction-os.vercel.app)  
**Repository:** [github.com/chandem/ai-construction-os](https://github.com/chandem/ai-construction-os)  
**Deploy guide:** [DEPLOY.md](DEPLOY.md) · **Roadmap:** [ROADMAP.md](ROADMAP.md) · **Phase 15:** [PHASE15.md](PHASE15.md)

---

## Status

| Area | State |
|------|--------|
| **Phases 1–15** | Foundation on `main` |
| **Frontend** | Vercel (Vite) |
| **API** | Render / Docker (`backend/`) |
| **Data** | Supabase — apply `supabase/*.sql` for full modules |

---

## Deploy (short)

1. **Supabase** — apply SQL files in order (see [DEPLOY.md](DEPLOY.md))
2. **Render** — Web Service, root `backend`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Vercel** — set `VITE_SUPABASE_*` and `VITE_API_BASE_URL` → redeploy

Full steps, env tables, CORS, and smoke test: **[DEPLOY.md](DEPLOY.md)**.

---

## What works today

### Auth & workspace
- Email/password (Supabase Auth)
- Create and select projects
- **OS Home** — readiness + recommended actions (Phase 15)

### Document intelligence
- Upload · background AI pipeline · job status / reprocess

### Construction AI Assistant
- Project-scoped RAG chat with citations

### Domain centers

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
| **Integrations** | Connectors |
| **Ops** | Queue, cost events, health |

---

## Architecture

```
Web App (React/Vite)  →  FastAPI  →  Supabase (Postgres + pgvector + Auth + Storage)
                              ↓
              Modular routes: engineering · commercial · operations
                              field/quality · intelligence · ops · construction OS
```

---

## Local development

```bash
# Frontend
cp .env.example .env   # VITE_SUPABASE_* , VITE_API_BASE_URL
npm install && npm run dev

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # SUPABASE_* , OPENAI_API_KEY , CORS_ORIGINS
uvicorn app.main:app --reload --port 8000
```

---

## Security

- Supabase Auth and RLS
- Project membership checks on API routes
- Publishable keys only in the frontend
- Engineering / commercial figures are **proposed** for human review

---

## Author

**Chane Eshetu** — Civil & Software Engineer  
GitHub: [@chandem](https://github.com/chandem)
