from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .ai_assistant import router as ai_router
from .config import settings
from .db import supabase
from .routes import router

app = FastAPI(
    title="AI Construction OS API",
    version="0.2.0",
    description="AI-first construction management platform API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ai_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ai-construction-os-api",
        "version": app.version,
    }


@app.get("/health/database")
def database_health():
    try:
        result = supabase.table("organizations").select("id").limit(1).execute()
        return {
            "status": "ok",
            "database": "connected",
            "rows_checked": len(result.data or []),
        }
    except Exception as exc:
        return {
            "status": "error",
            "database": "unreachable",
            "detail": str(exc),
        }
