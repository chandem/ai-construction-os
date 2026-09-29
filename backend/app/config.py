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
    openai_api_key: str = ""
    # Server-only Supabase secret key. Never expose this to the frontend.
    supabase_secret_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    # Comma-separated. Override on Render with CORS_ORIGINS if needed.
    cors_origins: str = ",".join(_DEFAULT_CORS)

    @property
    def supabase_key(self) -> str:
        return self.supabase_publishable_key or self.supabase_anon_key

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
