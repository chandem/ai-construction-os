# AI Construction OS — Backend

FastAPI service for authentication-backed projects, document intelligence, design assets, and the Construction AI Assistant (RAG).

## Requirements

- Python 3.11+
- Supabase project (Auth, Postgres/pgvector, Storage bucket `construction-documents`)
- OpenAI API key

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Configure `.env`:

```env
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
OPENAI_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
CORS_ORIGINS=http://localhost:5173,https://ai-costruction-os.vercel.app
```

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET /health`
- Database: `GET /health/database`
- OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

## Main routes

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/api/v1/auth/me` | Current user |
| `GET` | `/api/v1/projects` | List projects for memberships |
| `POST` | `/api/v1/projects` | Create project (auto-org if needed) |
| `GET` | `/api/v1/projects/{id}/documents` | List documents |
| `POST` | `/api/v1/projects/{id}/documents` | Upload + process |
| `POST` | `/api/v1/projects/{id}/ai/chat` | RAG chat |
| `GET` | `/api/v1/projects/{id}/design/assets` | Design assets |
| `GET` | `/api/v1/documents/{id}/status` | Processing job |
| `GET` | `/api/v1/documents/{id}/extraction` | Latest extraction |

All `/api/v1/*` routes (except health) require `Authorization: Bearer <supabase_access_token>`.

## Tests

```bash
pytest -q
```

## Notes

- Use a **publishable/anon** key in this service when relying on user JWTs + RLS.
- Never expose a service-role key in the frontend.
- Document processing is synchronous on upload for the MVP; large files may need a background worker later.
