from pydantic_settings import BaseSettings, SettingsConfigDict

# Production frontend (note historical hostname spelling on Vercel)
_DEFAULT_CORS = (
    "http://localhost:5173,"
    "https://ai-costruction-os.vercel.app,"
    "https://ai-construction-os.vercel.app"
)


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str = ""
    supabase_publishable_key: str = ""
    # Server-only Supabase secret key. Never expose this to the frontend.
    supabase_secret_key: str = ""

    # Gemini (primary AI provider — free tier friendly)
    gemini_api_key: str = ""
    # Optional legacy alias; prefer GEMINI_API_KEY
    openai_api_key: str = ""

    # Chat / extraction / vision model
    gemini_chat_model: str = "gemini-2.0-flash"
    # Embeddings — 768 dims (re-process documents after switching from OpenAI 1536)
    embedding_model: str = "text-embedding-004"

    # Comma-separated. Override on Render with CORS_ORIGINS if needed.
    cors_origins: str = ",".join(_DEFAULT_CORS)

    @property
    def supabase_key(self) -> str:
        return self.supabase_publishable_key or self.supabase_anon_key

    @property
    def ai_api_key(self) -> str:
        return (self.gemini_api_key or "").strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
