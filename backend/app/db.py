from supabase import Client, create_client
from .config import settings

if not settings.supabase_key:
    raise RuntimeError("SUPABASE_PUBLISHABLE_KEY is not configured")

# Keep client construction simple. Supabase-py versions with ClientOptions
# have had compatibility regressions around the storage attribute. The
# default options are sufficient for this backend.
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_key,
)


# Trusted server-side client. The secret key bypasses RLS and must remain on Render only.
supabase_admin: Client | None = (
    create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
    )
    if settings.supabase_secret_key
    else None
)
