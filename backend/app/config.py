from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS = (
    "http://localhost:5173,"
    "https://ai-costruction-os.vercel.app,"
    "https://ai-construction-os.vercel.app"
)

_OPENAI_EMBEDDING_ALIASES = {
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
    "models/text-embedding-3-small",
    "models/text-embedding-3-large",
}

_DEFAULT_GEMINI_EMBEDDING = "text-embedding-004"
# 3.7 often has more free-tier capacity than 3.8 under high demand
_DEFAULT_GEMINI_CHAT = "gemini-3.7-flash"

_RETIRED_CHAT_MODELS = {
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
    "gemini-pro",
    "models/gemini-2.0-flash",
    "models/gemini-2.0-flash-001",
    "models/gemini-1.5-flash",
}


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""

    gemini_api_key: str = ""
    openai_api_key: str = ""

    gemini_chat_model: str = _DEFAULT_GEMINI_CHAT
    embedding_model: str = _DEFAULT_GEMINI_EMBEDDING

    cors_origins: str = ",".join(_DEFAULT_CORS)

    @property
    def supabase_key(self) -> str:
        return self.supabase_publishable_key or self.supabase_anon_key

    @property
    def ai_api_key(self) -> str:
        return (self.gemini_api_key or "").strip()

    @property
    def resolved_chat_model(self) -> str:
        raw = (self.gemini_chat_model or "").strip() or _DEFAULT_GEMINI_CHAT
        if raw.startswith("models/"):
            raw = raw[len("models/") :]
        if raw.lower() in {m.replace("models/", "") for m in _RETIRED_CHAT_MODELS} or (
            f"models/{raw}".lower() in _RETIRED_CHAT_MODELS
        ):
            return _DEFAULT_GEMINI_CHAT
        return raw

    @property
    def gemini_embedding_model(self) -> str:
        raw = (self.embedding_model or "").strip() or _DEFAULT_GEMINI_EMBEDDING
        name = raw.split("/")[-1] if "/" in raw else raw
        if raw.lower() in _OPENAI_EMBEDDING_ALIASES or name.lower() in {
            n.replace("models/", "") for n in _OPENAI_EMBEDDING_ALIASES
        }:
            return _DEFAULT_GEMINI_EMBEDDING
        if raw.startswith("models/"):
            return raw[len("models/") :]
        return raw

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
