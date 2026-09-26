from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    supabase_url: str
    supabase_publishable_key: str
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

settings = Settings()
