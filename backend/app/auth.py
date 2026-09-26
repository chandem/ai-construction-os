from fastapi import Header, HTTPException
from .db import supabase

def get_access_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization[7:].strip()

def get_current_user(token: str) -> dict:
    try:
        user = supabase.auth.get_user(token).user
        if not user:
            raise ValueError("No user")
        return {"id": user.id, "email": user.email}
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
