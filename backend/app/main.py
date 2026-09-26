from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import supabase
from .config import settings

app = FastAPI(
    title="AI Construction OS API",
    version="0.1.0",
    description="AI-first construction management platform API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-construction-os-api"}

@app.get("/health/database")
def database_health():
    result = supabase.table("organizations").select("id").limit(1).execute()
    return {"status": "ok", "database": "connected", "rows_checked": len(result.data or [])}
