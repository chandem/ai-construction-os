# Deploy AI Construction OS

Target layout used by this repo:

| Layer | Host | Notes |
|-------|------|--------|
| **Frontend** | [Vercel](https://vercel.com) | Already linked to `ai-costruction-os.vercel.app` |
| **API** | [Render](https://render.com) (or any Docker host) | FastAPI under `backend/` |
| **Data** | [Supabase](https://supabase.com) | Auth, Postgres, Storage, pgvector |

---

## 0. Prerequisites

- Supabase project with Auth enabled
- Storage bucket: `construction-documents`
- OpenAI API key
- GitHub repo: `chandem/ai-construction-os`

### Apply SQL (Supabase → SQL Editor), in order

```
supabase/engineering_elements.sql
supabase/boq_items.sql
supabase/estimate_items.sql
supabase/tender_packages.sql
supabase/contract_packages.sql
supabase/planning.sql
supabase/procurement.sql
supabase/field.sql
supabase/quality.sql
supabase/gis.sql
supabase/prediction.sql
supabase/integrations.sql
supabase/hardening.sql
```

Also ensure base app tables (organizations, projects, documents, etc.) exist from your original schema.

---

## 1. Backend on Render

1. [Render Dashboard](https://dashboard.render.com) → **New → Web Service**
2. Connect `chandem/ai-construction-os`
3. Settings:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health check:** `/health`
4. Environment variables:

| Key | Value |
|-----|--------|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_PUBLISHABLE_KEY` | `anon` / publishable key |
| `OPENAI_API_KEY` | Your OpenAI key |
| `EMBEDDING_MODEL` | `text-embedding-3-small` |
| `CORS_ORIGINS` | `https://ai-costruction-os.vercel.app` (comma-separate extra origins) |

5. Deploy → note the public URL, e.g. `https://ai-construction-os-api.onrender.com`

### Optional: Docker

```bash
cd backend
docker build -t ai-construction-os-api .
docker run -p 8000:8000 --env-file .env ai-construction-os-api
```

Or use `render.yaml` (Blueprint) from the repo root.

### Verify API

```bash
curl https://YOUR-API-HOST/health
# {"status":"ok","service":"ai-construction-os-api",...}
```

---

## 2. Frontend on Vercel

1. [Vercel](https://vercel.com) → project linked to this repo (or import `chandem/ai-construction-os`)
2. Framework: **Vite** (or use committed `vercel.json`)
3. Environment variables:

| Key | Value |
|-----|--------|
| `VITE_SUPABASE_URL` | Same Supabase URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Same anon key |
| `VITE_API_BASE_URL` | Render API URL **without trailing slash** |

4. Redeploy so Vite bakes env into the build

### Local check of production build

```bash
cp .env.example .env   # fill values
npm install
npm run build && npm run preview
```

---

## 3. CORS and Auth

- Backend `CORS_ORIGINS` must include the exact Vercel origin (https, no trailing slash path)
- Supabase Auth → URL configuration: add Vercel site URL to **Site URL** and **Redirect URLs**

---

## 4. Smoke test after deploy

1. Open the Vercel app → sign up / log in  
2. Create a project  
3. **OS Home** → readiness should load (may show `needs_setup` until SQL is applied)  
4. Upload a PDF → document appears; wait for pipeline  
5. Design Center → Refresh / Generate BOQ  
6. `GET /health` and `GET /health/database` on the API  

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Frontend “API base URL is not configured” | Set `VITE_API_BASE_URL` and **redeploy** Vercel |
| CORS errors in browser | Add Vercel origin to `CORS_ORIGINS` on Render |
| Centers show warnings | Apply matching `supabase/*.sql` |
| Auth fails | Check Supabase URL/key; confirm Site URL / redirects |
| API cold start slow on free Render | First request after idle can take ~30s |

---

## What this agent cannot do for you

Deploy requires **your** Supabase, OpenAI, Vercel, and Render accounts. This guide and the config files in the repo are the deploy surface; secrets stay in those dashboards only.
