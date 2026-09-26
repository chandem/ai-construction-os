# AI Construction OS Backend

FastAPI service for the AI Construction OS.

## Local development

1. Copy `.env.example` to `.env`.
2. Add the Supabase project URL and publishable key.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health endpoints:

- `GET /health`
- `GET /health/database`

Use a publishable key for the application client. Never put a service-role or secret key in frontend code.
