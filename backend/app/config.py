from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS = (
    "http://localhost:5173,"
    "https://ai-costruction-os.vercel.app,"
    "https://ai-construction-os.vercel.app"
)

# OpenAI embedding names must never be sent to Gemini embedContent
_OPENAI_EMBEDDING_ALIASES = {
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
    "models/text-embedding-3-small",
    "models/text-embedding-3-large",
}

_DEFAULT_GEMINI_EMBEDDING = "text-embedding-004"


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""

    gemini_api_key: str = ""
    openai_api_key: str = ""

    gemini_chat_model: str = "gemini-2.0-flash"
    # May still be set to an old OpenAI name on Render — normalized below
    embedding_model: str = _DEFAULT_GEMINI_EMBEDDING

    cors_origins: str = ",".join(_DEFAULT_CORS)

    @property
    def supabase_key(self) -> str:
        return self.supabase_publishable_key or self.supabase_anon_key

    @property
    def ai_api_key(self) -> str:
        return (self.gemini_api_key or "").strip()

    @property
    def gemini_embedding_model(self) -> str:
        """Model id safe for Gemini embedContent."""
        raw = (self.embedding_model or "").strip() or _DEFAULT_GEMINI_EMBEDDING
        name = raw.split("/")[-1] if "/" in raw else raw
        if raw.lower() in _OPENAI_EMBEDDING_ALIASES or name.lower() in {
            n.replace("models/", "") for n in _OPENAI_EMBEDDING_ALIASES
        }:
            return _DEFAULT_GEMINI_EMBEDDING
        # Prefer bare id; SDK accepts text-embedding-004
        if raw.startswith("models/"):
            return raw[len("models/") :]
        return raw

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
