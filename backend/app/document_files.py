"""Download an uploaded project file for the signed-in member."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from .auth import get_access_token, get_current_user
from .routes import BUCKET, _authenticated_client, _document_for_member

router = APIRouter(prefix="/api/v1")


@router.get("/documents/{document_id}/file")
def download_document_file(document_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _document_for_member(document_id, user["id"], client)
    document = (
        client.table("documents")
        .select("id,name,mime_type,storage_path")
        .eq("id", document_id)
        .single()
        .execute()
    )
    row = document.data or {}
    storage_path = row.get("storage_path")
    if not storage_path:
        raise HTTPException(status_code=400, detail="Document has no stored file")
    payload = client.storage.from_(BUCKET).download(storage_path)
    if not isinstance(payload, (bytes, bytearray)):
        payload = getattr(payload, "content", b"") or b""
    if not payload:
        raise HTTPException(status_code=404, detail="Stored file is empty")
    name = (row.get("name") or "document").replace("\"", "")
    media = row.get("mime_type") or "application/octet-stream"
    return Response(
        content=bytes(payload),
        media_type=media,
        headers={"Content-Disposition": f'inline; filename="{name}"'},
    )
