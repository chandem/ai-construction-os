from supabase import Client, create_client
from .config import settings

if not settings.supabase_key:
    raise RuntimeError("SUPABASE_PUBLISHABLE_KEY is not configured")

supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_key,
)
