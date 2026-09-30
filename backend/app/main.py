from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .ai_assistant import router as ai_router
from .config import settings
from .db import supabase
from .engineering_routes import router as engineering_router
from .procurement_routes import router as procurement_router
from .routes import router

app = FastAPI(
    title="AI Construction OS API",
    version="0.3.1",
    description="AI-first construction management platform API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Support Vercel preview/production deployment URLs while retaining
    # credentials for Supabase-authenticated browser requests.
    allow_origin_regex=r"^https://[a-zA-Z0-9-]+\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ai_router)
app.include_router(engineering_router)
app.include_router(procurement_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ai-construction-os-api",
        "version": app.version,
    }


@app.get("/health/cors")
def cors_health():
    """Public list of configured CORS origins (no secrets) for deploy debugging."""
    return {
        "status": "ok",
        "allow_origins": settings.cors_origin_list,
        "hint": "Browser Origin must match one entry exactly (scheme + host, no path).",
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
